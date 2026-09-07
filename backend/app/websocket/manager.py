import asyncio
import random
import secrets
import string
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List, Optional, Set, Tuple

from fastapi import WebSocket
from sqlalchemy.orm import Session

ROUNDS_TOTAL_LIVES = 3
TURN_DURATION_SECONDS = 10  # temps de réflexion individuel, par joueur, par tour
FAST_ANSWER_THRESHOLD_SECONDS = 5  # réponse rapide sur son tour -> difficulté +1
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5
START_DIFFICULTY = 2

JOKER_CHARGES_PER_PLAYER = 3  # pool total, mixable librement entre les 3 types
EXTRA_TIME_BONUS_SECONDS = 15  # s'ajoute au temps restant du tour EN COURS du joueur qui l'utilise

PRIVATE_CODE_ALPHABET = string.ascii_uppercase + string.digits
PRIVATE_CODE_LENGTH = 6

# Anti-bruteforce sur submit_answer : un joueur humain n'a pas besoin de plus
# de quelques tentatives par tour, et encore moins de les envoyer à moins
# de 300ms d'écart. Un bot qui teste des réponses en boucle est ainsi bloqué
# sans gêner un joueur normal qui se corrige.
MAX_ANSWER_ATTEMPTS_PER_ROUND = 6
ANSWER_ATTEMPT_COOLDOWN_SECONDS = 0.3

# Anti-flood générique sur la connexion WebSocket : au-delà de ce débit
# d'events (tous types confondus), la connexion est fermée.
WS_EVENT_RATE_MAX = 25
WS_EVENT_RATE_WINDOW_SECONDS = 5.0

# Matchmaking public (hors parties privées) : groupe de 3 à 4 joueurs.
# On démarre dès que 3 joueurs sont réunis, en laissant une courte fenêtre
# pour qu'un 4e rejoigne avant de lancer la partie.
MATCHMAKING_MIN_PLAYERS = 3
MATCHMAKING_MAX_PLAYERS = 4
MATCHMAKING_GRACE_SECONDS = 6
# Si la file reste bloquée à 2 joueurs (aucun 3e ne se présente), on ne les
# fait pas patienter indéfiniment : on lance un duel classique après ce délai.
MATCHMAKING_FALLBACK_SECONDS = 10


@dataclass
class QueuedPlayer:
    player_id: str
    pseudo: str
    category_slug: str
    category_id: int
    websocket: WebSocket


@dataclass
class RoundState:
    round_number: int
    question: dict
    started_at: float
    turn_order: List[str] = field(default_factory=list)  # ordre de passage pour CETTE manche (joueurs actifs uniquement)
    turn_index: int = 0  # index, dans turn_order, du joueur dont c'est le tour
    turn_started_at: float = 0.0  # instant de départ du tour EN COURS
    resolved: bool = False  # True quand tous les tours de la manche sont joués (ou le match terminé en cours de manche)
    opted_out: Set[str] = field(default_factory=set)  # joueurs ayant "passé" leur propre tour
    extended_by: Set[str] = field(default_factory=set)  # joueurs ayant déjà utilisé "Temps supplémentaire" cette manche
    answer_attempts: Dict[str, int] = field(default_factory=dict)  # nb de tentatives par joueur sur cette manche
    last_attempt_at: Dict[str, float] = field(default_factory=dict)  # timestamp dernière tentative par joueur
    submissions: Dict[str, str] = field(default_factory=dict)  # dernier texte tapé par joueur sur cette manche (pour le récap de fin de partie)
    turn_status: Dict[str, str] = field(default_factory=dict)  # pid -> "correct" / "wrong" / "timeout" / "skipped", rempli au fil des tours
    eliminated_this_round: List[str] = field(default_factory=list)  # cumulé sur TOUS les tours de la manche
    active_at_start: List[str] = field(default_factory=list)  # joueurs en vie au lancement de cette manche (pour le récap de fin de partie)


@dataclass
class MatchState:
    match_id: str
    category_id: int
    category_slug: str
    players: Dict[str, QueuedPlayer]
    player_order: List[str]
    scores: Dict[str, int] = field(default_factory=dict)
    lives: Dict[str, int] = field(default_factory=dict)
    joker_charges: Dict[str, int] = field(default_factory=dict)
    difficulty: int = START_DIFFICULTY
    question_pool: Optional["MatchQuestionPool"] = None
    current_round: Optional[RoundState] = None
    round_number: int = 0
    round_timer_task: Optional[asyncio.Task] = None  # tâche du timer du TOUR en cours (pas de la manche entière)
    rounds_log: List[dict] = field(default_factory=list)
    # Ordre chronologique des joueurs éliminés (0 vie), utile pour désigner le
    # 2e (dernier éliminé) en fin de match à 3-4 joueurs.
    elimination_order: List[str] = field(default_factory=list)
    # Fait tourner le joueur qui commence chaque manche : le dernier à avoir
    # joué son tour la manche précédente passe en premier à la suivante.
    turn_rotation: int = 0


@dataclass
class PendingGroup:
    """Groupe de joueurs réunis pour le matchmaking public, en attente du
    lancement de la partie (démarre à 3, laisse une fenêtre pour un 4e)."""
    players: List[QueuedPlayer]
    timer_task: Optional[asyncio.Task] = None
    # Instant (time.time()) où la fenêtre de grâce a démarré, pour calculer la
    # deadline envoyée aux joueurs dans queue_update.
    grace_started_at: Optional[float] = None


class MatchQuestionPool:
    """Tire des questions par difficulté, sans répétition, propre à un match.

    Chaque match reçoit sa propre copie mélangée : deux matchs simultanés sur
    la même catégorie ne tirent donc (presque) jamais les mêmes drapeaux dans
    le même ordre.
    """

    def __init__(self, questions_by_difficulty: Dict[int, List[dict]]):
        self.by_difficulty: Dict[int, List[dict]] = {
            d: list(qs) for d, qs in questions_by_difficulty.items()
        }
        for bag in self.by_difficulty.values():
            random.shuffle(bag)

    def _search_order(self, difficulty: int) -> List[int]:
        """Ordre de repli si la difficulté demandée n'a plus de questions :
        on cherche d'abord tout autour, en s'écartant progressivement."""
        order = [difficulty]
        offset = 1
        while len(order) < (MAX_DIFFICULTY - MIN_DIFFICULTY + 1):
            if difficulty - offset >= MIN_DIFFICULTY:
                order.append(difficulty - offset)
            if difficulty + offset <= MAX_DIFFICULTY:
                order.append(difficulty + offset)
            offset += 1
        return order

    def draw(self, difficulty: int) -> Optional[dict]:
        for d in self._search_order(difficulty):
            bag = self.by_difficulty.get(d)
            if bag:
                return bag.pop()
        return None

    def is_empty(self) -> bool:
        return all(not bag for bag in self.by_difficulty.values())


class QuestionCache:
    """Cache en mémoire des questions par catégorie, pour ne pas refaire une
    requête DB à chaque nouveau match."""

    def __init__(self):
        self._by_category: Dict[int, Dict[int, List[dict]]] = {}
        # `get()` est appelé depuis un threadpool (executor), potentiellement
        # par plusieurs joueurs en même temps sur une catégorie pas encore en
        # cache : sans verrou, le check-then-act + la relecture pour le
        # `return` peuvent se chevaucher entre threads.
        self._load_lock = threading.Lock()

    def get(self, db: Session, category_id: int) -> Dict[int, List[dict]]:
        cached = self._by_category.get(category_id)
        if cached is not None:
            return cached
        with self._load_lock:
            # Un autre thread a pu charger la catégorie pendant qu'on attendait le verrou.
            cached = self._by_category.get(category_id)
            if cached is None:
                cached = self._load(db, category_id)
                self._by_category[category_id] = cached
            return cached

    def invalidate(self, category_id: Optional[int] = None):
        if category_id is None:
            self._by_category.clear()
        else:
            self._by_category.pop(category_id, None)

    @staticmethod
    def _load(db: Session, category_id: int) -> Dict[int, List[dict]]:
        from app import models  # import local pour éviter tout souci d'ordre d'import

        rows = db.query(models.Question).filter_by(category_id=category_id).all()
        by_difficulty: Dict[int, List[dict]] = {}
        for q in rows:
            hint_type = q.hint_type.value if hasattr(q.hint_type, "value") else q.hint_type
            by_difficulty.setdefault(q.difficulty, []).append({
                "id": q.id,
                "answer": q.answer,
                "prompt_label": q.prompt_label,
                "hint_type": hint_type,
                "hint_url": q.hint_url,
                "difficulty": q.difficulty,
            })
        return by_difficulty


class ConnectionManager:
    def __init__(self):
        self.queues: Dict[str, List[QueuedPlayer]] = {}
        self.pending_groups: Dict[str, PendingGroup] = {}
        self.queue_fallback_timers: Dict[str, asyncio.Task] = {}
        # Instant (time.time()) où le timer de repli en duel (file bloquée à 2)
        # a démarré, par catégorie — pour calculer la deadline envoyée aux
        # joueurs dans queue_update.
        self.queue_fallback_started_at: Dict[str, float] = {}
        self.matches: Dict[str, MatchState] = {}
        self.player_to_match: Dict[str, str] = {}
        # code partie privée -> (créateur en attente, questions déjà résolues pour sa catégorie)
        self.private_matches: Dict[str, Tuple[QueuedPlayer, Dict[int, List[dict]]]] = {}
        self._lock = asyncio.Lock()

    def _is_player_busy(self, player_id: str) -> bool:
        """Un joueur ne doit jamais pouvoir occuper deux places en même temps
        (file d'attente, groupe en formation, partie privée en attente, ou
        match actif). Sans ce garde-fou, une reconnexion involontaire côté
        client (ex. double montage React en dev, onglet dupliqué, reco réseau)
        peut faire atterrir le même joueur dans deux matchs différents —
        chacun avec sa propre question — ce qui casse la partie pour tout le
        monde. On rejette la nouvelle tentative plutôt que de la laisser créer
        un doublon silencieux.
        """
        if player_id in self.player_to_match:
            return True
        for queue in self.queues.values():
            if any(p.player_id == player_id for p in queue):
                return True
        for pending in self.pending_groups.values():
            if any(p.player_id == player_id for p in pending.players):
                return True
        for creator, _ in self.private_matches.values():
            if creator.player_id == player_id:
                return True
        return False

    async def _broadcast_queue_state(self, category_slug: str):
        """Prévient tous les joueurs en attente (file + groupe en formation) du
        nombre actuel de joueurs pour cette catégorie, pour qu'aucun ne se
        demande s'il attend tout seul dans le vide.

        Inclut aussi la deadline (timestamp Unix, en secondes) du timer de
        lancement automatique en cours, si un est actif : fenêtre de grâce
        pour un 4e joueur (groupe déjà à 3), ou repli en duel classique si
        aucun 3e ne se présente (file à 2). On envoie un timestamp absolu
        plutôt qu'un nombre de secondes restantes pour que le compte à
        rebours affiché reste juste côté client même si ce message met du
        temps à arriver (latence réseau) : `null` si aucun timer n'est actif
        pour l'instant (ex: file à 1 seul joueur)."""
        queue = self.queues.get(category_slug, [])
        pending = self.pending_groups.get(category_slug)
        waiting_players = list(queue) + (list(pending.players) if pending else [])
        count = len(waiting_players)

        deadline = None
        if pending and pending.timer_task and pending.grace_started_at:
            deadline = pending.grace_started_at + MATCHMAKING_GRACE_SECONDS
        else:
            fallback_started_at = self.queue_fallback_started_at.get(category_slug)
            if fallback_started_at:
                deadline = fallback_started_at + MATCHMAKING_FALLBACK_SECONDS

        for p in waiting_players:
            try:
                await p.websocket.send_json({
                    "event": "queue_update",
                    "payload": {
                        "waiting": count,
                        "min_players": MATCHMAKING_MIN_PLAYERS,
                        "max_players": MATCHMAKING_MAX_PLAYERS,
                        "deadline": deadline,
                    },
                })
            except Exception:
                # Le socket peut être fermé (déconnexion en cours) : on ignore.
                pass

    async def join_queue(
        self,
        player: QueuedPlayer,
        questions_by_difficulty: Dict[int, List[dict]],
        on_ready: Callable[[MatchState], Awaitable[None]],
    ) -> bool:
        """Matchmaking public à 3-4 joueurs.

        Dès que 3 joueurs sont réunis pour une catégorie, on ouvre une courte
        fenêtre (MATCHMAKING_GRACE_SECONDS) pendant laquelle un 4e peut encore
        rejoindre. Le lancement de la partie (`on_ready`) est donc toujours
        asynchrone, contrairement à l'ancien duel qui démarrait instantanément.

        Retourne False (sans rien faire) si ce joueur est déjà engagé ailleurs
        (file, groupe en formation, ou match actif) : voir `_is_player_busy`.
        """
        async with self._lock:
            if self._is_player_busy(player.player_id):
                return False

            pending = self.pending_groups.get(player.category_slug)
            if pending:
                pending.players.append(player)
                if len(pending.players) >= MATCHMAKING_MAX_PLAYERS:
                    if pending.timer_task:
                        pending.timer_task.cancel()
                    del self.pending_groups[player.category_slug]
                    match = self._create_match(pending.players, questions_by_difficulty)
                    asyncio.create_task(on_ready(match))
                else:
                    await self._broadcast_queue_state(player.category_slug)
                return True

            queue = self.queues.setdefault(player.category_slug, [])
            queue.append(player)
            if len(queue) >= MATCHMAKING_MIN_PLAYERS:
                group_players = queue[:MATCHMAKING_MIN_PLAYERS]
                self.queues[player.category_slug] = queue[MATCHMAKING_MIN_PLAYERS:]
                # On a atteint le seuil normal (3) : un éventuel timer de
                # repli à 2 joueurs pour cette catégorie devient obsolète.
                fallback_task = self.queue_fallback_timers.pop(player.category_slug, None)
                self.queue_fallback_started_at.pop(player.category_slug, None)
                if fallback_task:
                    fallback_task.cancel()
                pending = PendingGroup(players=group_players, grace_started_at=time.time())
                self.pending_groups[player.category_slug] = pending
                pending.timer_task = asyncio.create_task(
                    self._finalize_after_grace(player.category_slug, questions_by_difficulty, on_ready)
                )
                await self._broadcast_queue_state(player.category_slug)
            else:
                if len(queue) == 2 and player.category_slug not in self.queue_fallback_timers:
                    # Seulement 2 joueurs en attente pour l'instant : plutôt que
                    # de les faire patienter indéfiniment un 3e qui ne vient
                    # peut-être jamais, on programme un repli en duel classique.
                    self.queue_fallback_started_at[player.category_slug] = time.time()
                    self.queue_fallback_timers[player.category_slug] = asyncio.create_task(
                        self._finalize_fallback_duel(player.category_slug, questions_by_difficulty, on_ready)
                    )
                await self._broadcast_queue_state(player.category_slug)
            return True

    async def _finalize_after_grace(
        self,
        category_slug: str,
        questions_by_difficulty: Dict[int, List[dict]],
        on_ready: Callable[[MatchState], Awaitable[None]],
    ):
        try:
            await asyncio.sleep(MATCHMAKING_GRACE_SECONDS)
        except asyncio.CancelledError:
            return  # un 4e joueur a rejoint entre-temps : déjà géré par join_queue

        async with self._lock:
            pending = self.pending_groups.pop(category_slug, None)
        if pending:
            match = self._create_match(pending.players, questions_by_difficulty)
            await on_ready(match)

    async def _finalize_fallback_duel(
        self,
        category_slug: str,
        questions_by_difficulty: Dict[int, List[dict]],
        on_ready: Callable[[MatchState], Awaitable[None]],
    ):
        try:
            await asyncio.sleep(MATCHMAKING_FALLBACK_SECONDS)
        except asyncio.CancelledError:
            return  # un 3e joueur a rejoint entre-temps : déjà géré par join_queue

        async with self._lock:
            self.queue_fallback_timers.pop(category_slug, None)
            self.queue_fallback_started_at.pop(category_slug, None)
            queue = self.queues.get(category_slug, [])
            if len(queue) < 2:
                return  # un des deux a quitté la file entre-temps
            group_players = queue[:2]
            self.queues[category_slug] = queue[2:]
            match = self._create_match(group_players, questions_by_difficulty)
        await on_ready(match)

    def _generate_private_code(self) -> str:
        """C'est un token d'accès (donne droit de rejoindre la partie) : on utilise
        `secrets`, prévu pour ça, plutôt que `random` qui n'est pas conçu pour
        résister à un adversaire cherchant à prédire les valeurs générées."""
        while True:
            code = "".join(secrets.choice(PRIVATE_CODE_ALPHABET) for _ in range(PRIVATE_CODE_LENGTH))
            if code not in self.private_matches:
                return code

    async def create_private_match(
        self, player: QueuedPlayer, questions_by_difficulty: Dict[int, List[dict]]
    ) -> Optional[str]:
        async with self._lock:
            if self._is_player_busy(player.player_id):
                return None
            code = self._generate_private_code()
            self.private_matches[code] = (player, questions_by_difficulty)
            return code

    async def join_private_match(self, code: str, player: QueuedPlayer) -> Optional[MatchState]:
        async with self._lock:
            entry = self.private_matches.get(code)
            if not entry:
                return None
            creator, questions_by_difficulty = entry
            if creator.player_id == player.player_id:
                # on ne peut pas rejoindre sa propre partie
                return None
            if self._is_player_busy(player.player_id):
                return None
            del self.private_matches[code]
            return self._create_match([creator, player], questions_by_difficulty)

    async def cancel_private_matches_for_player(self, player_id: str):
        async with self._lock:
            stale_codes = [
                code for code, (creator, _) in self.private_matches.items()
                if creator.player_id == player_id
            ]
            for code in stale_codes:
                del self.private_matches[code]

    def _create_match(
        self,
        players: List[QueuedPlayer],
        questions_by_difficulty: Dict[int, List[dict]],
    ) -> MatchState:
        match_id = str(uuid.uuid4())
        order = [p.player_id for p in players]
        match = MatchState(
            match_id=match_id,
            category_id=players[0].category_id,
            category_slug=players[0].category_slug,
            players={p.player_id: p for p in players},
            player_order=order,
            scores={pid: 0 for pid in order},
            lives={pid: ROUNDS_TOTAL_LIVES for pid in order},
            joker_charges={pid: JOKER_CHARGES_PER_PLAYER for pid in order},
            question_pool=MatchQuestionPool(questions_by_difficulty),
        )
        self.matches[match_id] = match
        for pid in order:
            self.player_to_match[pid] = match_id
        return match

    async def leave_queue(self, player_id: str, category_slug: str):
        async with self._lock:
            queue = self.queues.get(category_slug, [])
            self.queues[category_slug] = [p for p in queue if p.player_id != player_id]
            pending = self.pending_groups.get(category_slug)
            if pending:
                pending.players = [p for p in pending.players if p.player_id != player_id]
            if len(self.queues[category_slug]) < 2:
                fallback_task = self.queue_fallback_timers.pop(category_slug, None)
                self.queue_fallback_started_at.pop(category_slug, None)
                if fallback_task:
                    fallback_task.cancel()
            await self._broadcast_queue_state(category_slug)

    def get_match(self, player_id: str) -> Optional[MatchState]:
        match_id = self.player_to_match.get(player_id)
        return self.matches.get(match_id) if match_id else None

    def end_match(self, match_id: str):
        match = self.matches.pop(match_id, None)
        if match:
            for pid in match.players:
                self.player_to_match.pop(pid, None)


manager = ConnectionManager()
question_cache = QuestionCache()
