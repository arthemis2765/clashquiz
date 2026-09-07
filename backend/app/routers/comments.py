import secrets
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.rate_limit import comment_limiter

router = APIRouter(prefix="/api/comments", tags=["comments"])


def _serialize_comments(db: Session, comments: list[models.Comment], viewer_id: Optional[uuid.UUID]) -> list[schemas.CommentOut]:
    """Sérialise une liste de commentaires avec le décompte des réactions par
    emoji et, si viewer_id est fourni, la réaction de ce joueur sur chacun.
    Fait 1-2 requêtes groupées au lieu d'une par commentaire (évite le N+1)."""
    if not comments:
        return []

    comment_ids = [c.id for c in comments]

    counts_by_comment: dict[uuid.UUID, dict[str, int]] = {cid: {} for cid in comment_ids}
    rows = (
        db.query(models.CommentReaction.comment_id, models.CommentReaction.emoji, func.count())
        .filter(models.CommentReaction.comment_id.in_(comment_ids))
        .group_by(models.CommentReaction.comment_id, models.CommentReaction.emoji)
        .all()
    )
    for comment_id, emoji, count in rows:
        counts_by_comment[comment_id][emoji.value] = count

    my_reactions: dict[uuid.UUID, str] = {}
    if viewer_id is not None:
        mine = (
            db.query(models.CommentReaction.comment_id, models.CommentReaction.emoji)
            .filter(
                models.CommentReaction.comment_id.in_(comment_ids),
                models.CommentReaction.player_id == viewer_id,
            )
            .all()
        )
        my_reactions = {comment_id: emoji.value for comment_id, emoji in mine}

    return [
        schemas.CommentOut(
            id=str(c.id),
            pseudo=c.player.pseudo,
            content=c.content,
            created_at=c.created_at,
            reactions=counts_by_comment.get(c.id, {}),
            my_reaction=my_reactions.get(c.id),
        )
        for c in comments
    ]


@router.get("", response_model=schemas.CommentPage)
def list_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    player_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    viewer_id = None
    if player_id:
        try:
            viewer_id = uuid.UUID(player_id)
        except ValueError:
            viewer_id = None  # id mal formé : on renvoie juste la liste sans "my_reaction"

    total = db.query(func.count(models.Comment.id)).scalar()
    total_pages = max(1, (total + page_size - 1) // page_size)

    rows = (
        db.query(models.Comment)
        .options(joinedload(models.Comment.player))
        .order_by(models.Comment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return schemas.CommentPage(
        items=_serialize_comments(db, rows, viewer_id),
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.post("", response_model=schemas.CommentOut, status_code=201)
def create_comment(payload: schemas.CommentCreate, db: Session = Depends(get_db)):
    try:
        pid = uuid.UUID(payload.player_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Authentification invalide.")

    player = db.query(models.Player).filter_by(id=pid).first()
    if not player or not secrets.compare_digest(player.device_token, payload.device_token):
        raise HTTPException(status_code=401, detail="Authentification invalide.")

    if not comment_limiter.allow(str(player.id)):
        raise HTTPException(
            status_code=429,
            detail="Un peu de patience avant de publier un nouveau commentaire.",
        )

    comment = models.Comment(player_id=player.id, content=payload.content)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment.player = player  # évite un aller-retour DB dans _serialize_comments

    return _serialize_comments(db, [comment], viewer_id=None)[0]


@router.put("/{comment_id}/reactions", response_model=schemas.CommentOut)
def toggle_reaction(comment_id: str, payload: schemas.ReactionToggle, db: Session = Depends(get_db)):
    """Bascule la réaction d'un joueur sur un commentaire : même emoji ->
    retire la réaction, emoji différent -> la remplace, pas de réaction ->
    la crée. Un joueur n'a jamais plus d'une réaction par commentaire."""
    try:
        cid = uuid.UUID(comment_id)
        pid = uuid.UUID(payload.player_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Commentaire introuvable.")

    player = db.query(models.Player).filter_by(id=pid).first()
    if not player or not secrets.compare_digest(player.device_token, payload.device_token):
        raise HTTPException(status_code=401, detail="Authentification invalide.")

    comment = (
        db.query(models.Comment)
        .options(joinedload(models.Comment.player))
        .filter_by(id=cid)
        .first()
    )
    if not comment:
        raise HTTPException(status_code=404, detail="Commentaire introuvable.")

    new_emoji = models.ReactionEmoji(payload.emoji)
    existing = (
        db.query(models.CommentReaction)
        .filter_by(comment_id=cid, player_id=pid)
        .first()
    )
    if existing and existing.emoji == new_emoji:
        db.delete(existing)
    elif existing:
        existing.emoji = new_emoji
    else:
        db.add(models.CommentReaction(comment_id=cid, player_id=pid, emoji=new_emoji))
    db.commit()

    return _serialize_comments(db, [comment], viewer_id=pid)[0]
