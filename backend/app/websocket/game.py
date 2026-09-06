import asyncio
import logging
import secrets
import time
import unicodedata
from collections import deque
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.database import SessionLocal
from app import models
from app.websocket.manager import (
    manager,
    question_cache,
    QueuedPlayer,
    RoundState,
    MatchState,
    TURN_DURATION_SECONDS,
    FAST_ANSWER_THRESHOLD_SECONDS,
    MIN_DIFFICULTY,
    MAX_DIFFICULTY,
    JOKER_CHARGES_PER_PLAYER,
    EXTRA_TIME_BONUS_SECONDS,
    MAX_ANSWER_ATTEMPTS_PER_ROUND,
    ANSWER_ATTEMPT_COOLDOWN_SECONDS,
    WS_EVENT_RATE_MAX,
    WS_EVENT_RATE_WINDOW_SECONDS,
)
from app.websocket.persistence import save_match_result
from app.rate_limit import private_join_limiter, real_client_ip

router = APIRouter()
logger = logging.getLogger(__name__)


def normalize_answer(text: str) -> str:
    """Tolérance orthographique légère : ignore la casse, les accents
    et les espaces superflus, pour éviter la frustration sur les fautes mineures."""
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


async def send_json(ws: WebSocket, event: str, payload: dict):
    try:
        await ws.send_json({"event": event, "payload": payload})
    except Exception:
        # Le socket peut être fermé (déconnexion en cours) : on ignore silencieusement.
        pass


def _verify_device_token_sync(player_id: str, device_token: str) -> Optional[str]:
    """Vérifie le token et renvoie le pseudo réel en base (ou None si invalide).

    On ne fait plus confiance au pseudo envoyé par le client : il est
    seulement utilisé pour retrouver le joueur, le pseudo affiché en partie
    vient toujours de la base, pour empêcher qu'un joueur authentifié se
    fasse passer pour un autre pseudo pendant le match.
    """
    db = SessionLocal()
    try:
        player = db.query(models.Player).filter_by(id=player_id).first()
        if player and device_token and secrets.compare_digest(player.device_token, device_token):
            return player.pseudo
        return None
    finally:
        db.close()


async def verify_device_token(player_id: str, device_token: str) -> Optional[str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _verify_device_token_sync, player_id, device_token)


def _resolve_category_and_questions(slug: str):
    db = SessionLocal()
    try:
        category = db.query(models.Category).filter_by(slug=slug, active=True).first()
        if not category:
            return None, None
        questions = question_cache.get(db, category.id)
        return category, questions
    finally:
        db.close()


async def resolve_category_and_questions(slug: str):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _resolve_category_and_questions, slug)


async def _launch_match(match: MatchState):
    """Prévient tous les joueurs qu'une partie démarre (2 à 4 joueurs) et
    lance la première manche."""
    for pid, p in match.players.items():
        opponents = [
            {"player_id": qid, "pseudo": q.pseudo}
            for qid, q in match.players.items() if qid != pid
        ]
        await send_json(p.websocket, "match_found", {
            "match_id": match.match_id,
            "opponents": opponents,
        })
    await start_round(match)


def _active_players(match: MatchState) -> list[str]:
    """Joueurs encore en vie (non éliminés) dans l'ordre du match."""
    return [pid for pid in match.player_order if match.lives[pid] > 0]


def _match_over_winner(match: MatchState) -> tuple[bool, Optional[str]]:
    """Le match est-il fini (il ne reste plus qu'un joueur en vie, ou zéro) ?

    Fonctionne aussi bien pour un duel (2 joueurs) que pour un groupe à 3-4 :
    on élimine progressivement les joueurs à 0 vie jusqu'à ce qu'il n'en reste
    qu'un, qui remporte le match."""
    active = _active_players(match)
    if len(active) > 1:
        return False, None
    if len(active) == 1:
        return True, active[0]
    # Cas rare : les derniers joueurs actifs tombent tous à 0 vie sur la même
    # manche (ex. timeout à 2 actifs). On départage au score le plus élevé.
    best_score = max(match.scores.values())
    leaders = [pid for pid in match.player_order if match.scores[pid] == best_score]
    return True, (leaders[0] if len(leaders) == 1 else None)


def _winner_by_score(match: MatchState) -> Optional[str]:
    best_score = max(match.scores.values())
    leaders = [pid for pid in match.player_order if match.scores[pid] == best_score]
    return leaders[0] if len(leaders) == 1 else None


def _second_place_id(match: MatchState, winner_id: Optional[str]) -> Optional[str]:
    """Le 2e du match (dernier joueur éliminé), utilisé pour le calcul Elo :
    seuls le gagnant et le 2e gagnent/perdent de l'Elo, comme en 1v1."""
    if not winner_id:
        return None
    return match.elimination_order[-1] if match.elimination_order else None


def _eliminate_player(match: MatchState, player_id: str) -> bool:
    """Élimine immédiatement un joueur (vies à 0), typiquement sur déconnexion.
    Retourne True si le joueur vient d'être éliminé (pas déjà à 0)."""
    if match.lives.get(player_id, 0) <= 0:
        return False
    match.lives[player_id] = 0
    match.elimination_order.append(player_id)
    return True


def _round_players_recap(round_state: RoundState, status_for) -> dict:
    """Construit, pour chaque joueur encore actif au début de cette manche, son
    statut (correct / wrong / timeout / skipped) et le texte qu'il a tapé en
    dernier — utilisé pour le récap détaillé affiché en fin de partie (payload
    `match_end`). `status_for(pid)` fournit le statut, propre à chaque façon
    dont une manche peut se terminer. Les joueurs déjà éliminés avant cette
    manche n'y figurent pas."""
    return {
        pid: {"status": status_for(pid), "submitted": round_state.submissions.get(pid)}
        for pid in round_state.active_at_start
    }


def _apply_life_loss(match: MatchState, player_id: str) -> bool:
    """Retire une vie à un joueur encore en vie. Retourne True s'il vient
    d'être éliminé (vie tombée à 0), pour notifier le groupe."""
    if match.lives.get(player_id, 0) <= 0:
        return False
    match.lives[player_id] = max(0, match.lives[player_id] - 1)
    if match.lives[player_id] == 0:
        match.elimination_order.append(player_id)
        return True
    return False


@router.websocket("/ws/game")
async def game_socket(websocket: WebSocket):
    await websocket.accept()
    player_id = None
    category_slug = None
    event_timestamps: deque = deque()

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            # Anti-flood générique : au-delà du débit autorisé (tous events
            # confondus), on ferme la connexion plutôt que de continuer à
            # traiter un client qui spamme (bot, script de triche, DoS léger).
            now = time.time()
            event_timestamps.append(now)
            while event_timestamps and now - event_timestamps[0] > WS_EVENT_RATE_WINDOW_SECONDS:
                event_timestamps.popleft()
            if len(event_timestamps) > WS_EVENT_RATE_MAX:
                await send_json(websocket, "error", {
                    "message": "Trop de requêtes, connexion fermée.", "fatal": True,
                })
                await websocket.close(code=1008)
                break

            try:
                if event == "join_queue":
                    player_id = data["player_id"]
                    category_slug = data["category_slug"]
                    device_token = data.get("device_token", "")

                    pseudo = await verify_device_token(player_id, device_token)
                    if not pseudo:
                        await send_json(websocket, "error", {
                            "message": "Authentification invalide. Reconnecte-toi.",
                        })
                        continue

                    category, questions_by_difficulty = await resolve_category_and_questions(category_slug)
                    if category is None:
                        await send_json(websocket, "error", {"message": f"Catégorie inconnue : {category_slug}"})
                        continue
                    if not questions_by_difficulty or not any(questions_by_difficulty.values()):
                        await send_json(websocket, "error", {
                            "message": "Aucune question disponible pour cette catégorie pour le moment.",
                        })
                        continue

                    queued = QueuedPlayer(
                        player_id=player_id,
                        pseudo=pseudo,
                        category_slug=category_slug,
                        category_id=category.id,
                        websocket=websocket,
                    )
                    await send_json(websocket, "queue_joined", {"category_slug": category_slug})
                    # Matchmaking à 3-4 joueurs : le lancement de la partie est
                    # asynchrone (fenêtre d'attente d'un 4e joueur), voir manager.py.
                    joined = await manager.join_queue(queued, questions_by_difficulty, on_ready=_launch_match)
                    if not joined:
                        # Ce joueur a déjà une entrée active ailleurs (reconnexion en
                        # rafale côté client, ex. double montage React en dev) : on
                        # ignore cette tentative en trop plutôt que de risquer de le
                        # dupliquer dans deux matchs différents.
                        await send_json(websocket, "error", {
                            "message": "Tu as déjà une recherche de partie en cours.", "fatal": False,
                        })

                elif event == "create_private_match":
                    player_id = data["player_id"]
                    category_slug = data["category_slug"]
                    device_token = data.get("device_token", "")

                    pseudo = await verify_device_token(player_id, device_token)
                    if not pseudo:
                        await send_json(websocket, "error", {
                            "message": "Authentification invalide. Reconnecte-toi.",
                        })
                        continue

                    category, questions_by_difficulty = await resolve_category_and_questions(category_slug)
                    if category is None:
                        await send_json(websocket, "error", {"message": f"Catégorie inconnue : {category_slug}"})
                        continue
                    if not questions_by_difficulty or not any(questions_by_difficulty.values()):
                        await send_json(websocket, "error", {
                            "message": "Aucune question disponible pour cette catégorie pour le moment.",
                        })
                        continue

                    queued = QueuedPlayer(
                        player_id=player_id,
                        pseudo=pseudo,
                        category_slug=category_slug,
                        category_id=category.id,
                        websocket=websocket,
                    )
                    code = await manager.create_private_match(queued, questions_by_difficulty)
                    if not code:
                        await send_json(websocket, "error", {
                            "message": "Tu as déjà une partie en cours.", "fatal": False,
                        })
                        continue
                    await send_json(websocket, "private_match_created", {
                        "code": code,
                        "category_slug": category_slug,
                    })

                elif event == "join_private_match":
                    player_id = data["player_id"]
                    code = str(data.get("code", "")).strip().upper()
                    device_token = data.get("device_token", "")

                    pseudo = await verify_device_token(player_id, device_token)
                    if not pseudo:
                        await send_json(websocket, "error", {
                            "message": "Authentification invalide. Reconnecte-toi.",
                        })
                        continue

                    if not code:
                        await send_json(websocket, "error", {"message": "Code de partie manquant."})
                        continue

                    fallback_ip = websocket.client.host if websocket.client else "unknown"
                    client_ip = real_client_ip(websocket.headers, fallback_ip)
                    if not private_join_limiter.allow(client_ip):
                        await send_json(websocket, "error", {
                            "message": "Trop de tentatives, réessaie dans une minute.",
                        })
                        continue

                    queued = QueuedPlayer(
                        player_id=player_id,
                        pseudo=pseudo,
                        category_slug="",
                        category_id=0,
                        websocket=websocket,
                    )
                    match = await manager.join_private_match(code, queued)
                    if not match:
                        await send_json(websocket, "error", {
                            "message": "Ce code de partie est invalide, expiré, ou déjà utilisé.",
                        })
                        continue

                    category_slug = match.category_slug  # pour le nettoyage en cas de déconnexion
                    await _launch_match(match)

                elif event == "submit_answer":
                    match = manager.get_match(player_id) if player_id else None
                    if not match or not match.current_round or match.current_round.resolved:
                        continue

                    if match.lives.get(player_id, 0) <= 0:
                        continue  # joueur déjà éliminé (groupe à 3-4)

                    round_state = match.current_round
                    if round_state.turn_order[round_state.turn_index] != player_id:
                        # Ce n'est pas son tour : on ignore silencieusement (l'UI
                        # ne devrait normalement pas permettre l'envoi dans ce cas).
                        continue
                    if player_id in round_state.opted_out:
                        continue

                    now = time.time()
                    last_attempt = round_state.last_attempt_at.get(player_id, 0.0)
                    if now - last_attempt < ANSWER_ATTEMPT_COOLDOWN_SECONDS:
                        continue  # tentatives trop rapprochées, probablement un bot
                    round_state.last_attempt_at[player_id] = now

                    attempts = round_state.answer_attempts.get(player_id, 0) + 1
                    round_state.answer_attempts[player_id] = attempts
                    if attempts > MAX_ANSWER_ATTEMPTS_PER_ROUND:
                        await send_json(websocket, "error", {
                            "message": "Trop de tentatives sur ce tour.", "fatal": False,
                        })
                        continue

                    # Cappé comme le pseudo : évite qu'un client malveillant envoie une
                    # chaîne énorme, stockée puis rediffusée à tous les joueurs du match.
                    submitted_raw = str(data.get("answer", ""))[:100]
                    round_state.submissions[player_id] = submitted_raw
                    answer = normalize_answer(submitted_raw)
                    correct = normalize_answer(round_state.question["answer"])

                    if answer != correct:
                        # Mauvaise réponse : le joueur peut retenter tant que son
                        # tour n'est pas terminé (timeout ou tentatives épuisées).
                        await send_json(websocket, "wrong_answer", {
                            "round_number": round_state.round_number,
                            "submitted": submitted_raw,
                        })
                        continue

                    if match.round_timer_task:
                        match.round_timer_task.cancel()
                    eliminated = await _resolve_turn(match, round_state, player_id, "correct")
                    for p in match.players.values():
                        await send_json(p.websocket, "turn_result", {
                            "round_number": round_state.round_number,
                            "player_id": player_id,
                            "status": "correct",
                            "scores": match.scores,
                            "lives": match.lives,
                        })
                    await _advance_turn(match, round_state, eliminated)

                elif event == "use_joker":
                    await handle_use_joker(websocket, player_id, data.get("joker_type"))
            except Exception:
                # On isole l'erreur à cet event précis : la connexion reste ouverte et
                # les deux joueurs sont prévenus plutôt que de rester bloqués sans
                # explication (voir aussi le blindage de _turn_timeout_watcher plus bas).
                logger.exception("Erreur lors du traitement de l'event '%s'", event)
                await send_json(websocket, "error", {
                    "message": "Un problème est survenu, merci de réessayer.",
                })

    except WebSocketDisconnect:
        if player_id:
            if category_slug:
                await manager.leave_queue(player_id, category_slug)
            await manager.cancel_private_matches_for_player(player_id)
            match = manager.get_match(player_id)
            if match:
                _eliminate_player(match, player_id)
                for pid, p in match.players.items():
                    if pid != player_id:
                        await send_json(p.websocket, "player_disconnected", {
                            "player_id": player_id,
                        })
                over, winner = _match_over_winner(match)
                if over:
                    if match.round_timer_task:
                        match.round_timer_task.cancel()
                    round_state = match.current_round
                    if round_state and not round_state.resolved:
                        _finalize_round(match, round_state)
                    await end_match(match, winner_id=winner)
                else:
                    # Le match continue (groupe à 3-4, il reste plusieurs joueurs actifs).
                    # Si c'était le tour du joueur qui vient de partir, on ne fait pas
                    # attendre les autres jusqu'au timeout complet : on enchaîne tout de suite.
                    round_state = match.current_round
                    if (
                        round_state
                        and not round_state.resolved
                        and round_state.turn_order[round_state.turn_index] == player_id
                    ):
                        if match.round_timer_task:
                            match.round_timer_task.cancel()
                        round_state.turn_status[player_id] = "timeout"
                        await _advance_turn(match, round_state, eliminated_this_turn=[])


def _build_turn_order(match: MatchState) -> list[str]:
    """Ordre de passage pour la manche à venir : les joueurs actifs, en
    faisant tourner le point de départ à chaque manche (le dernier à avoir
    joué la manche précédente passe en premier cette fois-ci)."""
    active = _active_players(match)
    if not active:
        return []
    offset = match.turn_rotation % len(active)
    order = active[offset:] + active[:offset]
    match.turn_rotation += 1
    return order


def _finalize_round(match: MatchState, round_state: RoundState):
    """Construit l'entrée rounds_log et notifie tout le monde une fois que
    tous les tours de la manche ont été joués (ou que le match s'est terminé
    en cours de manche)."""
    round_state.resolved = True
    match.rounds_log.append({
        "question_id": round_state.question["id"],
        "round_number": round_state.round_number,
        "prompt_label": round_state.question["prompt_label"],
        "correct_answer": round_state.question["answer"],
        "timed_out": False,
        "players": _round_players_recap(
            round_state,
            lambda pid: round_state.turn_status.get(pid, "timeout"),
        ),
    })


async def _broadcast_round_result(match: MatchState, round_state: RoundState, eliminated: list[str]):
    """Résultat FINAL de la manche (tous les tours joués) : révèle la bonne réponse."""
    for p in match.players.values():
        await send_json(p.websocket, "round_result", {
            "round_number": round_state.round_number,
            "turn_status": round_state.turn_status,
            "answer": round_state.question["answer"],
            "scores": match.scores,
            "lives": match.lives,
            "eliminated": eliminated,
        })


async def _broadcast_elimination_update(match: MatchState, round_state: RoundState, eliminated: list[str]):
    """Notif intermédiaire (un joueur vient d'être éliminé en cours de manche,
    d'autres tours restent à jouer) : ne révèle PAS la bonne réponse, pour ne
    pas avantager les joueurs qui n'ont pas encore joué leur tour."""
    for p in match.players.values():
        await send_json(p.websocket, "player_eliminated_mid_round", {
            "round_number": round_state.round_number,
            "scores": match.scores,
            "lives": match.lives,
            "eliminated": eliminated,
        })


async def _resolve_turn(
    match: MatchState,
    round_state: RoundState,
    player_id: str,
    status: str,
) -> list[str]:
    """Clôt le tour du joueur `player_id` (correct / wrong-implicite via timeout / skipped)
    et applique la perte de vie si besoin. Retourne la liste des joueurs
    nouvellement éliminés par cette résolution (0 ou 1 joueur ici)."""
    round_state.turn_status[player_id] = status
    eliminated = []

    if status == "correct":
        match.scores[player_id] += 1
        elapsed = time.time() - round_state.turn_started_at
        if elapsed < FAST_ANSWER_THRESHOLD_SECONDS:
            match.difficulty = min(MAX_DIFFICULTY, match.difficulty + 1)
    elif status == "timeout":
        if _apply_life_loss(match, player_id):
            eliminated.append(player_id)
            round_state.eliminated_this_round.append(player_id)
        match.difficulty = max(MIN_DIFFICULTY, match.difficulty - 1)
    # "skipped" : ni score ni perte de vie, comme avant.

    return eliminated


async def _advance_turn(match: MatchState, round_state: RoundState, eliminated_this_turn: list[str]):
    """Passe au tour suivant, ou termine la manche si tout le monde a joué,
    ou termine le match si la partie est décidée."""
    over, winner = _match_over_winner(match)
    if over:
        _finalize_round(match, round_state)
        await _broadcast_round_result(match, round_state, round_state.eliminated_this_round)
        await end_match(match, winner)
        return

    round_state.turn_index += 1
    if round_state.turn_index >= len(round_state.turn_order):
        _finalize_round(match, round_state)
        await _broadcast_round_result(match, round_state, round_state.eliminated_this_round)
        await start_round(match)
        return

    if eliminated_this_turn:
        # On prévient quand même du résultat partiel si un joueur vient
        # d'être éliminé en cours de manche, avant d'enchaîner sur le tour
        # suivant — sans révéler la bonne réponse (d'autres tours restent).
        await _broadcast_elimination_update(match, round_state, eliminated_this_turn)

    await _start_turn(match, round_state)


async def _start_turn(match: MatchState, round_state: RoundState):
    active_player_id = round_state.turn_order[round_state.turn_index]
    round_state.turn_started_at = time.time()

    for pid, p in match.players.items():
        await send_json(p.websocket, "turn_start", {
            "round_number": round_state.round_number,
            "turn_index": round_state.turn_index,
            "total_turns": len(round_state.turn_order),
            "active_player_id": active_player_id,
            "is_your_turn": pid == active_player_id,
            "timer_seconds": TURN_DURATION_SECONDS,
            "scores": match.scores,
            "lives": match.lives,
            "joker_charges": match.joker_charges,
        })

    match.round_timer_task = asyncio.create_task(
        _turn_timeout_watcher(match, round_state.round_number, active_player_id, TURN_DURATION_SECONDS)
    )


async def _turn_timeout_watcher(match: MatchState, round_number: int, expected_player_id: str, delay: float):
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return

    try:
        if manager.get_match(match.player_order[0]) is None:
            return  # le match est déjà terminé entre-temps

        round_state = match.current_round
        if not round_state or round_state.round_number != round_number or round_state.resolved:
            return
        if round_state.turn_order[round_state.turn_index] != expected_player_id:
            return  # ce tour a déjà été résolu autrement (ex: skip, déconnexion)

        eliminated = await _resolve_turn(match, round_state, expected_player_id, "timeout")

        for p in match.players.values():
            await send_json(p.websocket, "turn_timeout", {
                "round_number": round_state.round_number,
                "player_id": expected_player_id,
                "scores": match.scores,
                "lives": match.lives,
                "eliminated": eliminated,
            })

        await _advance_turn(match, round_state, eliminated)
    except Exception:
        # Cette fonction tourne en tâche de fond (asyncio.create_task) : une exception
        # non rattrapée ici serait avalée en silence par asyncio et bloquerait la
        # partie indéfiniment côté joueurs, sans aucun message d'erreur. On logge et
        # on prévient les deux joueurs plutôt que de les laisser fixer un écran figé.
        logger.exception(
            "Erreur lors du traitement du timeout de tour (manche %s, match %s)",
            round_number, match.match_id,
        )
        for p in match.players.values():
            await send_json(p.websocket, "error", {
                "message": "Un problème est survenu pendant la partie. Retourne à l'accueil pour relancer une partie.",
            })


async def start_round(match: MatchState):
    question = match.question_pool.draw(match.difficulty)
    if question is None:
        # Plus aucun drapeau disponible dans cette catégorie : on termine sur le score actuel.
        await end_match(match, _winner_by_score(match))
        return

    match.round_number += 1
    turn_order = _build_turn_order(match)
    round_state = RoundState(
        round_number=match.round_number,
        question=question,
        started_at=time.time(),
        turn_order=turn_order,
        active_at_start=list(turn_order),
    )
    match.current_round = round_state

    for p in match.players.values():
        await send_json(p.websocket, "round_start", {
            "round_number": match.round_number,
            "prompt_label": question["prompt_label"],
            "hint_type": question["hint_type"],
            "hint_url": question["hint_url"],
            "difficulty": question["difficulty"],
            "turn_order": turn_order,
            "scores": match.scores,
            "lives": match.lives,
            "joker_charges": match.joker_charges,
        })

    await _start_turn(match, round_state)


async def handle_use_joker(websocket: WebSocket, player_id: Optional[str], joker_type: Optional[str]):
    match = manager.get_match(player_id) if player_id else None
    if not match or not match.current_round or match.current_round.resolved:
        return
    if match.lives.get(player_id, 0) <= 0:
        await send_json(websocket, "error", {
            "message": "Tu es éliminé, tu ne peux plus jouer.", "fatal": False,
        })
        return

    if joker_type not in ("hint", "skip", "extra_time"):
        await send_json(websocket, "error", {"message": "Joker inconnu.", "fatal": False})
        return

    if match.joker_charges.get(player_id, 0) <= 0:
        await send_json(websocket, "error", {"message": "Plus de jokers disponibles.", "fatal": False})
        return

    round_state = match.current_round
    if round_state.turn_order[round_state.turn_index] != player_id:
        await send_json(websocket, "error", {"message": "Ce n'est pas ton tour.", "fatal": False})
        return

    if joker_type == "hint":
        match.joker_charges[player_id] -= 1
        cleaned_answer = round_state.question["answer"].strip()
        first_letters = cleaned_answer[:2].upper()
        await send_json(websocket, "joker_hint", {
            "round_number": round_state.round_number,
            "hint": first_letters,
            "remaining": match.joker_charges[player_id],
        })

    elif joker_type == "skip":
        match.joker_charges[player_id] -= 1
        round_state.opted_out.add(player_id)

        if match.round_timer_task:
            match.round_timer_task.cancel()
        eliminated = await _resolve_turn(match, round_state, player_id, "skipped")
        for p in match.players.values():
            await send_json(p.websocket, "turn_result", {
                "round_number": round_state.round_number,
                "player_id": player_id,
                "status": "skipped",
                "scores": match.scores,
                "lives": match.lives,
            })
        await _advance_turn(match, round_state, eliminated)

    elif joker_type == "extra_time":
        if player_id in round_state.extended_by:
            await send_json(websocket, "error", {
                "message": "Tu as déjà utilisé le temps supplémentaire ce tour.",
                "fatal": False,
            })
            return

        match.joker_charges[player_id] -= 1
        round_state.extended_by.add(player_id)

        if match.round_timer_task:
            match.round_timer_task.cancel()
        elapsed = time.time() - round_state.turn_started_at
        remaining = max(0.0, TURN_DURATION_SECONDS - elapsed) + EXTRA_TIME_BONUS_SECONDS
        match.round_timer_task = asyncio.create_task(
            _turn_timeout_watcher(match, round_state.round_number, player_id, remaining)
        )

        for p in match.players.values():
            await send_json(p.websocket, "joker_extra_time", {
                "round_number": round_state.round_number,
                "used_by": player_id,
                "bonus_seconds": EXTRA_TIME_BONUS_SECONDS,
                "new_timer_seconds": round(remaining),
            })


async def end_match(match: MatchState, winner_id: Optional[str]):
    second_id = _second_place_id(match, winner_id)
    result = {"elo": {}, "leaderboard": []}
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, save_match_result, match, winner_id, second_id)
    except Exception:
        # Même si l'écriture en base (historique, Elo) échoue, les joueurs doivent
        # quand même recevoir l'écran de fin de match — sinon la partie reste
        # bloquée indéfiniment sans aucun signal côté client.
        logger.exception("Échec de la persistance du match %s", match.match_id)

    for p in match.players.values():
        await send_json(p.websocket, "match_end", {
            "winner_id": winner_id,
            "scores": match.scores,
            "lives": match.lives,
            "elo": result.get("elo", {}),
            "leaderboard": result.get("leaderboard", []),
            "rounds_log": match.rounds_log,
        })

    manager.end_match(match.match_id)
