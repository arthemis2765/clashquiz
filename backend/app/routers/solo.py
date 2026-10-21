"""Mode solo : 3 vies, difficulté croissante, 3 jokers à usage unique.

Tout se joue en HTTP (pas de WebSocket) : à chaque appel, le serveur relit
l'état de la partie en base, vérifie le temps avec sa propre horloge et ne
renvoie la bonne réponse qu'une fois la question résolue.

Sécurité / robustesse :
  - chaque réponse porte le numéro de la question à laquelle elle répond : une
    requête rejouée (réponse HTTP perdue puis nouvel essai du client) est
    refusée au lieu de retirer une vie sur la question suivante ;
  - la ligne de la partie est verrouillée (SELECT ... FOR UPDATE) le temps du
    traitement : deux requêtes simultanées ne peuvent plus valider deux fois
    la même question ;
  - le démarrage d'une partie est limité par joueur.
"""
import random
import secrets
import time
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.rate_limit import solo_start_limiter
from app.text_utils import is_correct_answer
from app.websocket.manager import (
    EXTRA_TIME_BONUS_SECONDS,
    MAX_DIFFICULTY,
    MIN_DIFFICULTY,
    question_cache,
)

router = APIRouter(prefix="/api/solo", tags=["solo"])

SOLO_LIVES = 3
SOLO_QUESTION_SECONDS = 15
CORRECT_PER_LEVEL = 3  # la difficulté monte d'un cran toutes les 3 bonnes réponses
NETWORK_GRACE_SECONDS = 1.5  # marge pour la latence réseau sur l'échéance
BLANK_TIMEOUT_MARGIN_SECONDS = 1.0  # une réponse vide proche de l'échéance = temps écoulé
JOKER_TYPES = ("hint", "extra_time", "skip")


# --------------------------------------------------------------------------
# Schémas
# --------------------------------------------------------------------------
class SoloAuth(BaseModel):
    player_id: str = Field(max_length=64)
    device_token: str = Field(min_length=1, max_length=100)


class SoloStart(SoloAuth):
    category_slug: str = Field(max_length=100)


class SoloRunRef(SoloAuth):
    run_id: str = Field(max_length=64)


class SoloAnswer(SoloRunRef):
    # Numéro de la question à laquelle on répond (renvoyé par le serveur avec
    # chaque question) : protège contre les requêtes rejouées ou périmées.
    question_number: int = Field(ge=1, le=100000)
    answer: str = Field(default="", max_length=200)


class SoloJoker(SoloRunRef):
    joker_type: str = Field(max_length=20)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _parse_uuid(value: str, detail: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(status_code=404, detail=detail)


def _auth_player(db: Session, player_id: str, device_token: str) -> models.Player:
    pid = _parse_uuid(player_id, "Joueur introuvable.")
    player = db.query(models.Player).filter_by(id=pid).first()
    if not player or not secrets.compare_digest(player.device_token, device_token or ""):
        raise HTTPException(status_code=401, detail="Authentification invalide.")
    return player


def _get_run(db: Session, player: models.Player, run_id: str) -> models.SoloRun:
    """Charge la partie du joueur en verrouillant sa ligne jusqu'au commit."""
    rid = _parse_uuid(run_id, "Partie introuvable.")
    run = (
        db.query(models.SoloRun)
        .filter_by(id=rid, player_id=player.id)
        .with_for_update()
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="Partie introuvable.")
    return run


def _get_active_run(db: Session, player: models.Player, run_id: str) -> models.SoloRun:
    run = _get_run(db, player, run_id)
    if run.finished:
        raise HTTPException(status_code=409, detail="Cette partie est terminée.")
    return run


def _question_number(run: models.SoloRun) -> int:
    """Numéro (1, 2, 3…) de la question en cours : chaque question tirée est
    ajoutée à used_question_ids, donc sa longueur sert de compteur, sans
    nouvelle colonne en base."""
    return len(run.used_question_ids or [])


def _target_difficulty(score: int) -> int:
    return min(MAX_DIFFICULTY, MIN_DIFFICULTY + score // CORRECT_PER_LEVEL)


def _search_order(difficulty: int) -> list[int]:
    """Difficulté demandée d'abord, puis les plus proches si elle est épuisée."""
    order = [difficulty]
    offset = 1
    while len(order) < (MAX_DIFFICULTY - MIN_DIFFICULTY + 1):
        if difficulty - offset >= MIN_DIFFICULTY:
            order.append(difficulty - offset)
        if difficulty + offset <= MAX_DIFFICULTY:
            order.append(difficulty + offset)
        offset += 1
    return order


def _draw_question(db: Session, run: models.SoloRun) -> Optional[dict]:
    by_difficulty = question_cache.get(db, run.category_id)
    used = set(run.used_question_ids or [])
    for d in _search_order(_target_difficulty(run.score)):
        candidates = [q for q in by_difficulty.get(d, []) if q["id"] not in used]
        if candidates:
            return random.choice(candidates)
    return None


def _set_question(run: models.SoloRun, question: dict) -> None:
    run.current_question_id = question["id"]
    run.used_question_ids = [*(run.used_question_ids or []), question["id"]]
    run.question_deadline = time.time() + SOLO_QUESTION_SECONDS
    run.max_difficulty = max(run.max_difficulty or 1, question["difficulty"])


def _best_score(db: Session, player_id, category_id, exclude_run_id=None) -> int:
    """Meilleur score du joueur dans ce thème. Les parties abandonnées (onglet
    fermé) comptent aussi : le score obtenu est réel, il est validé côté serveur."""
    query = db.query(func.max(models.SoloRun.score)).filter(
        models.SoloRun.player_id == player_id,
        models.SoloRun.category_id == category_id,
    )
    if exclude_run_id is not None:
        query = query.filter(models.SoloRun.id != exclude_run_id)
    return query.scalar() or 0


def _question_payload(run: models.SoloRun, question: Optional[dict]) -> Optional[dict]:
    if question is None:
        return None
    seconds_left = max(0.0, (run.question_deadline or 0) - time.time())
    return {
        "number": _question_number(run),
        "prompt_label": question["prompt_label"],
        "hint_type": question["hint_type"],
        "hint_url": question["hint_url"],
        "difficulty": question["difficulty"],
        "seconds_left": round(seconds_left, 1),
    }


def _current_question_dict(db: Session, run: models.SoloRun) -> Optional[dict]:
    if run.current_question_id is None:
        return None
    q = db.get(models.Question, run.current_question_id)
    if not q:
        return None
    hint_type = q.hint_type.value if hasattr(q.hint_type, "value") else q.hint_type
    return {
        "id": q.id, "answer": q.answer, "prompt_label": q.prompt_label,
        "hint_type": hint_type, "hint_url": q.hint_url, "difficulty": q.difficulty,
    }


def _state(run: models.SoloRun, record: Optional[int] = None) -> dict:
    used = run.jokers or {}
    state = {
        "run_id": str(run.id),
        "score": run.score,
        "lives": run.lives,
        "max_difficulty": run.max_difficulty,
        "jokers": {j: bool(used.get(j)) for j in JOKER_TYPES},
        "jokers_used": sum(1 for j in JOKER_TYPES if used.get(j)),
    }
    if record is not None:
        state["record"] = record
    return state


def _finish(db: Session, run: models.SoloRun) -> dict:
    previous_best = _best_score(db, run.player_id, run.category_id, exclude_run_id=run.id)
    run.finished = True
    run.finished_at = datetime.utcnow()
    run.current_question_id = None
    run.question_deadline = None
    db.commit()
    summary = _state(run, max(previous_best, run.score))
    summary["new_record"] = run.score > previous_best and run.score > 0
    return summary


# --------------------------------------------------------------------------
# Routes de jeu
# --------------------------------------------------------------------------
@router.post("/start")
def start_run(payload: SoloStart, db: Session = Depends(get_db)):
    player = _auth_player(db, payload.player_id, payload.device_token)
    if not solo_start_limiter.allow(str(player.id)):
        raise HTTPException(
            status_code=429,
            detail="Trop de parties lancées en peu de temps, réessaie dans quelques minutes.",
        )

    category = db.query(models.Category).filter_by(slug=payload.category_slug, active=True).first()
    if not category:
        raise HTTPException(status_code=404, detail="Thème introuvable.")

    # Une seule partie en cours par joueur : les anciennes sont clôturées
    # (le score déjà acquis reste valable pour le record).
    stale = db.query(models.SoloRun).filter_by(player_id=player.id, finished=False).all()
    for old in stale:
        old.finished = True
        old.finished_at = datetime.utcnow()
        old.current_question_id = None
        old.question_deadline = None

    run = models.SoloRun(
        player_id=player.id, category_id=category.id, lives=SOLO_LIVES,
        score=0, max_difficulty=MIN_DIFFICULTY, jokers={}, used_question_ids=[],
    )
    question = _draw_question(db, run)
    if question is None:
        db.rollback()
        raise HTTPException(status_code=404, detail="Aucune question disponible pour ce thème.")
    _set_question(run, question)
    db.add(run)
    db.commit()
    db.refresh(run)

    record = _best_score(db, player.id, category.id, exclude_run_id=run.id)
    return {"state": _state(run, record), "question": _question_payload(run, question)}


@router.post("/answer")
def answer(payload: SoloAnswer, db: Session = Depends(get_db)):
    player = _auth_player(db, payload.player_id, payload.device_token)
    run = _get_run(db, player, payload.run_id)

    if run.finished or payload.question_number != _question_number(run):
        # Requête rejouée ou périmée (ou partie déjà terminée par la réponse
        # précédente dont la réponse HTTP s'est perdue) : le client se
        # resynchronise via /current au lieu de perdre une vie injustement.
        raise HTTPException(
            status_code=409,
            detail={
                "code": "stale_question",
                "message": "Cette question a déjà été traitée.",
            },
        )

    question = _current_question_dict(db, run)
    if question is None:
        raise HTTPException(status_code=409, detail="Aucune question en cours.")

    now = time.time()
    deadline = run.question_deadline or 0
    blank = not payload.answer.strip()
    # Le client envoie une réponse vide quand son chrono atteint 0 : tant que
    # c'est proche de l'échéance, c'est bien un « temps écoulé » et non une
    # mauvaise réponse (avant, la marge réseau le faisait passer pour « wrong »).
    timed_out = now > deadline + NETWORK_GRACE_SECONDS or (
        blank and now >= deadline - BLANK_TIMEOUT_MARGIN_SECONDS
    )
    correct = (not timed_out) and is_correct_answer(payload.answer, question["answer"])

    if correct:
        result = "correct"
        run.score += 1
    else:
        result = "timeout" if timed_out else "wrong"
        run.lives -= 1

    summary = None
    next_question = None
    if run.lives <= 0:
        summary = _finish(db, run)
    else:
        next_question = _draw_question(db, run)
        if next_question is None:  # toutes les questions du thème ont été jouées
            summary = _finish(db, run)
        else:
            _set_question(run, next_question)
            db.commit()

    return {
        "result": result,
        "correct_answer": question["answer"],
        "finished": summary is not None,
        "state": summary or _state(run),
        "question": _question_payload(run, next_question),
    }


@router.post("/joker")
def use_joker(payload: SoloJoker, db: Session = Depends(get_db)):
    player = _auth_player(db, payload.player_id, payload.device_token)
    run = _get_active_run(db, player, payload.run_id)
    if payload.joker_type not in JOKER_TYPES:
        raise HTTPException(status_code=400, detail="Joker inconnu.")

    used = dict(run.jokers or {})
    if used.get(payload.joker_type):
        raise HTTPException(status_code=409, detail="Ce joker a déjà été utilisé.")

    question = _current_question_dict(db, run)
    if question is None:
        raise HTTPException(status_code=409, detail="Aucune question en cours.")
    if time.time() > (run.question_deadline or 0) + NETWORK_GRACE_SECONDS:
        raise HTTPException(status_code=409, detail="Le temps est écoulé.")

    used[payload.joker_type] = True
    run.jokers = used

    if payload.joker_type == "hint":
        db.commit()
        return {"hint": question["answer"].strip()[:2].upper(), "state": _state(run)}

    if payload.joker_type == "extra_time":
        run.question_deadline = (run.question_deadline or time.time()) + EXTRA_TIME_BONUS_SECONDS
        db.commit()
        return {
            "bonus_seconds": EXTRA_TIME_BONUS_SECONDS,
            "seconds_left": round(max(0.0, run.question_deadline - time.time()), 1),
            "state": _state(run),
        }

    # skip : on passe la question sans perdre de vie ni gagner de point
    next_question = _draw_question(db, run)
    if next_question is None:
        summary = _finish(db, run)
        return {"finished": True, "state": summary, "question": None}
    _set_question(run, next_question)
    db.commit()
    return {"finished": False, "state": _state(run), "question": _question_payload(run, next_question)}


@router.post("/current")
def current_state(payload: SoloRunRef, db: Session = Depends(get_db)):
    """Renvoie l'état exact de la partie et sa question en cours : permet au
    client de se resynchroniser après une réponse HTTP perdue."""
    player = _auth_player(db, payload.player_id, payload.device_token)
    run = _get_run(db, player, payload.run_id)
    if run.finished:
        record = _best_score(db, player.id, run.category_id)
        return {"finished": True, "state": _state(run, record), "question": None}

    question = _current_question_dict(db, run)
    if question is None:
        raise HTTPException(status_code=409, detail="Aucune question en cours.")
    return {"finished": False, "state": _state(run), "question": _question_payload(run, question)}


@router.post("/abandon")
def abandon(payload: SoloRunRef, db: Session = Depends(get_db)):
    """Clôt la partie quand le joueur quitte : le score acquis est enregistré
    tout de suite (sans attendre la prochaine partie). Sans effet si elle est
    déjà terminée."""
    player = _auth_player(db, payload.player_id, payload.device_token)
    run = _get_run(db, player, payload.run_id)
    if run.finished:
        record = _best_score(db, player.id, run.category_id)
        return {"finished": True, "state": _state(run, record)}
    return {"finished": True, "state": _finish(db, run)}


# --------------------------------------------------------------------------
# Classement solo
# --------------------------------------------------------------------------
@router.get("/leaderboard")
def solo_leaderboard(
    category_slug: Optional[str] = Query(default=None, max_length=100),
    player_id: Optional[str] = Query(default=None, max_length=64),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Classement solo.

    - avec `category_slug` : meilleur score de chaque joueur dans ce thème ;
    - sans : somme des meilleurs scores de chaque joueur sur tous les thèmes
      actifs (jouer plusieurs thèmes est donc récompensé).

    Les identifiants des joueurs ne sont pas exposés : si `player_id` est fourni,
    la ligne du joueur est simplement marquée `is_me`, et `me` donne son rang
    même hors du top.
    """
    category = None
    if category_slug:
        category = db.query(models.Category).filter_by(slug=category_slug, active=True).first()
        if not category:
            raise HTTPException(status_code=404, detail="Thème introuvable.")

    best_query = (
        db.query(
            models.SoloRun.player_id.label("player_id"),
            models.SoloRun.category_id.label("category_id"),
            func.max(models.SoloRun.score).label("best"),
        )
        .join(models.Category, models.Category.id == models.SoloRun.category_id)
        .filter(models.SoloRun.score > 0, models.Category.active.is_(True))
    )
    if category is not None:
        best_query = best_query.filter(models.SoloRun.category_id == category.id)
    best = best_query.group_by(models.SoloRun.player_id, models.SoloRun.category_id).subquery()

    totals = (
        db.query(
            best.c.player_id.label("player_id"),
            func.sum(best.c.best).label("total"),
            func.count().label("themes"),
        )
        .group_by(best.c.player_id)
        .subquery()
    )

    viewer_id = None
    if player_id:
        try:
            viewer_id = uuid.UUID(player_id)
        except ValueError:
            viewer_id = None

    rows = (
        db.query(models.Player.id, models.Player.pseudo, totals.c.total, totals.c.themes)
        .join(totals, totals.c.player_id == models.Player.id)
        .order_by(totals.c.total.desc(), models.Player.pseudo.asc(), models.Player.id.asc())
        .limit(limit)
        .all()
    )

    entries = []
    previous_total, previous_rank = None, 0
    for index, row in enumerate(rows):
        total = int(row.total)
        rank = previous_rank if total == previous_total else index + 1  # ex æquo = même rang
        previous_total, previous_rank = total, rank
        entries.append({
            "rank": rank,
            "pseudo": row.pseudo,
            "score": total,
            "themes": int(row.themes),
            "is_me": viewer_id is not None and row.id == viewer_id,
        })

    me = None
    if viewer_id is not None:
        my_total = db.query(totals.c.total).filter(totals.c.player_id == viewer_id).scalar()
        if my_total is not None:
            ahead = db.query(func.count()).select_from(totals).filter(totals.c.total > my_total).scalar()
            me = {"rank": int(ahead) + 1, "score": int(my_total)}

    return {"category": category.slug if category else None, "entries": entries, "me": me}
