import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Enum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class MatchStatus(str, enum.Enum):
    waiting = "waiting"
    playing = "playing"
    finished = "finished"


class HintType(str, enum.Enum):
    flag = "flag"
    map = "map"
    logo = "logo"
    photo = "photo"
    text = "text"


class ReactionEmoji(str, enum.Enum):
    heart = "heart"
    pray = "pray"
    angry = "angry"
    thumbsup = "thumbsup"


class Player(Base):
    __tablename__ = "players"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pseudo = Column(String, nullable=False)
    device_token = Column(String, unique=True, nullable=False, index=True)
    elo_score = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    active = Column(Boolean, default=True)

    questions = relationship("Question", back_populates="category")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    prompt_label = Column(String, nullable=False)
    answer = Column(String, nullable=False)
    hint_type = Column(Enum(HintType), nullable=False)
    hint_url = Column(String, nullable=True)
    difficulty = Column(Integer, nullable=False, default=1)  # 1 à 5

    category = relationship("Category", back_populates="questions")


class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    winner_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)
    runner_up_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)
    status = Column(Enum(MatchStatus), default=MatchStatus.waiting)
    player_count = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    participants = relationship("MatchParticipant", back_populates="match")


class MatchParticipant(Base):
    """Une ligne par joueur ayant participé à un match : remplace les anciennes
    colonnes player_a_id/player_b_id, player_a_score/player_b_score, etc. qui
    étaient codées en dur pour exactement 2 joueurs. Fonctionne pour 2, 3 ou 4."""
    __tablename__ = "match_participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False)
    score = Column(Integer, default=0)
    lives = Column(Integer, default=3)
    # Rang final : 1 = vainqueur, 2 = 2e (dernier éliminé), etc. NULL si non déterminé
    # (ex. match nul entre les deux derniers, ou joueur non classé).
    final_rank = Column(Integer, nullable=True)

    match = relationship("Match", back_populates="participants")


class MatchRound(Base):
    __tablename__ = "match_rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    winner_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=True)
    timed_out = Column(Boolean, default=False)
    answered_at = Column(DateTime, nullable=True)


class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    player = relationship("Player")


class CommentReaction(Base):
    """Une réaction par joueur et par commentaire : la contrainte unique force
    un upsert (changer d'emoji remplace l'ancien plutôt que d'en ajouter un)
    au lieu de laisser un joueur accumuler plusieurs réactions sur le même
    commentaire."""
    __tablename__ = "comment_reactions"
    __table_args__ = (
        UniqueConstraint("comment_id", "player_id", name="uq_comment_reaction_player"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=False)
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"), nullable=False)
    emoji = Column(Enum(ReactionEmoji), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
