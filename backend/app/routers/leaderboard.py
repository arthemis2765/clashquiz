from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("")
def get_leaderboard(limit: int = Query(default=10, ge=1, le=100), db: Session = Depends(get_db)):
    """Classement global de tous les joueurs, tous jeux confondus, trié par score Elo."""
    players = (
        db.query(models.Player)
        .filter(models.Player.games_played > 0)
        .order_by(models.Player.elo_score.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "rank": i + 1,
            "player_id": str(p.id),
            "pseudo": p.pseudo,
            "elo_score": p.elo_score,
            "games_played": p.games_played,
        }
        for i, p in enumerate(players)
    ]
