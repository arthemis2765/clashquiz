"""Écriture en base à la fin d'un match : historique + mise à jour du score."""
import uuid
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app import models
from app.websocket.manager import MatchState

POINTS_PER_WIN = 5


def compute_elo(rating_a: int, rating_b: int, score_a: float) -> tuple[int, int]:
    """Système à points fixes (plus de calcul Elo variable) : le gagnant
    gagne toujours POINTS_PER_WIN points, peu importe le niveau de
    l'adversaire ; le perdant ne perd jamais rien. En cas d'égalité
    (score_a == 0.5, uniquement possible en duel), personne ne gagne ni ne
    perd de points.

    score_a : 1 si A gagne, 0 si A perd, 0.5 en cas d'égalité.
    """
    if score_a == 1.0:
        return rating_a + POINTS_PER_WIN, rating_b
    if score_a == 0.0:
        return rating_a, rating_b + POINTS_PER_WIN
    return rating_a, rating_b


def save_match_result(
    match: MatchState, winner_id: Optional[str], second_id: Optional[str] = None
) -> dict:
    """Persiste le match et TOUS ses participants (2 à 4), met à jour l'Elo.

    Chaque joueur du match obtient une ligne dans match_participants (score,
    vies restantes, rang final) — contrairement à l'ancien schéma qui ne
    conservait que 2 joueurs par match et perdait silencieusement les 3e/4e.

    En duel (2 joueurs), comportement Elo inchangé : toujours mis à jour
    (0.5/0.5 en cas d'égalité). En groupe (3-4 joueurs), l'Elo n'est appliqué
    qu'entre le gagnant et le 2e (dernier éliminé) ; les autres joueurs ne
    gagnent/perdent rien, conformément aux règles du mode groupe.

    Retourne un dict avec les nouveaux scores Elo et le top 10 du classement,
    prêt à être renvoyé dans l'event `match_end`.
    """
    db = SessionLocal()
    try:
        player_order = match.player_order
        is_duel = len(player_order) == 2

        if is_duel:
            record_a_id, record_b_id = player_order
            apply_elo = True
            if winner_id == record_a_id:
                score_a = 1.0
            elif winner_id == record_b_id:
                score_a = 0.0
            else:
                score_a = 0.5
        else:
            apply_elo = bool(winner_id and second_id and winner_id != second_id)
            record_a_id = winner_id or player_order[0]
            record_b_id = second_id or next(
                (pid for pid in player_order if pid != record_a_id), player_order[0]
            )
            score_a = 1.0  # n'est utilisé que si apply_elo est vrai (winner_id == record_a_id alors)

        player_a = db.query(models.Player).get(uuid.UUID(record_a_id)) if record_a_id else None
        player_b = db.query(models.Player).get(uuid.UUID(record_b_id)) if record_b_id else None

        if apply_elo and player_a and player_b:
            new_elo_a, new_elo_b = compute_elo(player_a.elo_score, player_b.elo_score, score_a)
            player_a.elo_score = new_elo_a
            player_b.elo_score = new_elo_b

        # Tous les joueurs du match comptent une partie jouée, qu'ils aient
        # gagné/perdu de l'Elo ou non (3e/4e place en groupe, par exemple).
        players_by_id = {record_a_id: player_a, record_b_id: player_b}
        for pid in player_order:
            p = players_by_id.get(pid) or db.query(models.Player).get(uuid.UUID(pid))
            if p:
                p.games_played += 1

        db_match = models.Match(
            id=uuid.uuid4(),
            category_id=match.category_id,
            winner_id=uuid.UUID(winner_id) if winner_id else None,
            runner_up_id=uuid.UUID(second_id) if second_id else None,
            status=models.MatchStatus.finished,
            player_count=len(player_order),
            finished_at=datetime.utcnow(),
        )
        db.add(db_match)
        db.flush()  # pour obtenir db_match.id utilisable par les participants et les rounds

        # Rang final : 1 = vainqueur, 2 = 2e (dernier éliminé), puis les autres
        # dans l'ordre inverse d'élimination (le plus tôt éliminé = pire rang).
        rank_map: dict[str, int] = {}
        if winner_id:
            rank_map[winner_id] = 1
        if second_id:
            rank_map[second_id] = 2
        remaining = [pid for pid in player_order if pid not in rank_map]
        remaining.sort(
            key=lambda pid: (
                match.elimination_order.index(pid) if pid in match.elimination_order else -1
            ),
            reverse=True,
        )
        for i, pid in enumerate(remaining):
            rank_map[pid] = 3 + i

        for pid in player_order:
            db.add(models.MatchParticipant(
                id=uuid.uuid4(),
                match_id=db_match.id,
                player_id=uuid.UUID(pid),
                score=match.scores.get(pid, 0),
                lives=match.lives.get(pid, 0),
                final_rank=rank_map.get(pid),
            ))

        for entry in match.rounds_log:
            db.add(models.MatchRound(
                id=uuid.uuid4(),
                match_id=db_match.id,
                question_id=entry["question_id"],
                round_number=entry["round_number"],
                winner_id=uuid.UUID(entry["winner_id"]) if entry.get("winner_id") else None,
                timed_out=entry.get("timed_out", False),
                answered_at=datetime.utcnow(),
            ))

        db.commit()

        leaderboard = (
            db.query(models.Player)
            .filter(models.Player.games_played > 0)
            .order_by(models.Player.elo_score.desc())
            .limit(10)
            .all()
        )

        elo_result = {}
        if apply_elo and player_a and player_b:
            elo_result = {
                record_a_id: player_a.elo_score,
                record_b_id: player_b.elo_score,
            }

        return {
            "elo": elo_result,
            "leaderboard": [
                {
                    "rank": i + 1,
                    "player_id": str(p.id),
                    "pseudo": p.pseudo,
                    "elo_score": p.elo_score,
                    "games_played": p.games_played,
                }
                for i, p in enumerate(leaderboard)
            ],
        }
    finally:
        db.close()
