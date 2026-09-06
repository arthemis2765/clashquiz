import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.rate_limit import register_limiter, real_client_ip

router = APIRouter(prefix="/api/players", tags=["players"])


def _to_player_out(player: models.Player) -> schemas.PlayerOut:
    return schemas.PlayerOut(
        id=str(player.id),
        pseudo=player.pseudo,
        device_token=player.device_token,
        elo_score=player.elo_score,
        games_played=player.games_played,
    )


@router.post("/register", response_model=schemas.PlayerOut)
def register_player(payload: schemas.PlayerCreate, request: Request, db: Session = Depends(get_db)):
    """Crée un joueur à partir d'un simple pseudo, sans mot de passe ni email."""
    fallback_ip = request.client.host if request.client else "unknown"
    client_ip = real_client_ip(request.headers, fallback_ip)
    if not register_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Trop de comptes créés récemment, réessaie plus tard.")

    device_token = str(uuid.uuid4())
    player = models.Player(pseudo=payload.pseudo, device_token=device_token)
    db.add(player)
    db.commit()
    db.refresh(player)
    return _to_player_out(player)


@router.patch("/{player_id}/pseudo", response_model=schemas.PlayerOut)
def update_pseudo(player_id: str, payload: schemas.PlayerPseudoUpdate, db: Session = Depends(get_db)):
    """Renomme un joueur. Changer de pseudo réinitialise son score Elo et son
    nombre de parties jouées : on considère que c'est un nouveau départ, pour
    éviter qu'un joueur mal classé se refasse une image sous un autre nom tout
    en gardant son historique de victoires."""
    try:
        pid = uuid.UUID(player_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Joueur introuvable.")

    player = db.query(models.Player).filter_by(id=pid).first()
    if not player or not secrets.compare_digest(player.device_token, payload.device_token):
        # Message volontairement générique (joueur inconnu vs token invalide) :
        # pas besoin de distinguer les deux côté client, et ça évite de confirmer
        # l'existence d'un player_id à un tiers qui devine des UUID au hasard.
        raise HTTPException(status_code=401, detail="Authentification invalide.")

    if payload.pseudo != player.pseudo:
        player.pseudo = payload.pseudo
        player.elo_score = 0
        player.games_played = 0
        db.commit()
        db.refresh(player)

    return _to_player_out(player)
