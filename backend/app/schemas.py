import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator, Field

# Liste volontairement courte de motifs à bloquer : insultes courantes et
# marqueurs de spam (liens, mentions "admin"/"moderateur" pour éviter
# l'usurpation d'autorité). À étendre si besoin, sans viser l'exhaustivité :
# le but est de filtrer le spam grossier, pas de faire de la modération fine.
_PSEUDO_BLACKLIST = [
    "merde", "connard", "connasse", "encule", "enculé", "pute", "salope",
    "nique", "batard", "bâtard", "pd", "negre", "nègre",
    "admin", "moderateur", "modérateur", "staff",
    "http://", "https://", "www.",
]

# Détecte un pseudo composé d'un seul caractère répété (ex: "aaaaaaaa"),
# typique d'un script qui génère des comptes en masse.
_REPEATED_CHAR_RE = re.compile(r"^(.)\1*$")


def _clean_pseudo(value: str) -> str:
    """Validation partagée entre la création et le renommage : mêmes règles
    des deux côtés, pour ne pas laisser un pseudo interdit passer au renommage
    alors qu'il aurait été bloqué à l'inscription."""
    value = value.strip()
    if len(value) < 2:
        raise ValueError("Le pseudo doit contenir au moins 2 caractères.")
    if len(value) > 20:
        raise ValueError("Le pseudo ne peut pas dépasser 20 caractères.")
    # Interdit les caractères de contrôle (retours à la ligne, tabulations, etc.)
    if any(ord(c) < 32 for c in value):
        raise ValueError("Le pseudo contient des caractères non autorisés.")

    lowered = value.lower()
    for pattern in _PSEUDO_BLACKLIST:
        if pattern in lowered:
            raise ValueError("Ce pseudo n'est pas autorisé.")

    if _REPEATED_CHAR_RE.match(value):
        raise ValueError("Ce pseudo n'est pas autorisé.")

    return value


class PlayerCreate(BaseModel):
    pseudo: str = Field(min_length=2, max_length=20)

    @field_validator("pseudo")
    @classmethod
    def pseudo_must_be_clean(cls, value: str) -> str:
        return _clean_pseudo(value)


class PlayerPseudoUpdate(BaseModel):
    """Renommage d'un joueur existant. Le device_token sert d'authentification
    (pas de mot de passe dans ce jeu) : seul l'appareil qui a créé le compte
    peut renommer son propre joueur."""
    device_token: str = Field(min_length=1)
    pseudo: str = Field(min_length=2, max_length=20)

    @field_validator("pseudo")
    @classmethod
    def pseudo_must_be_clean(cls, value: str) -> str:
        return _clean_pseudo(value)


class PlayerOut(BaseModel):
    id: str
    pseudo: str
    device_token: str
    elo_score: int
    games_played: int

    class Config:
        from_attributes = True


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    player_id: str
    device_token: str = Field(min_length=1)
    content: str = Field(min_length=1, max_length=300)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le commentaire ne peut pas être vide.")
        return value


class CommentOut(BaseModel):
    id: str
    pseudo: str
    content: str
    created_at: datetime
    reactions: dict[str, int] = {}
    my_reaction: str | None = None

    class Config:
        from_attributes = True


class CommentPage(BaseModel):
    items: list[CommentOut]
    page: int
    page_size: int
    total: int
    total_pages: int


class ReactionToggle(BaseModel):
    player_id: str
    device_token: str = Field(min_length=1)
    emoji: Literal["heart", "pray", "angry", "thumbsup"]
