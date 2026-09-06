import { useEffect, useState } from "react";
import { fetchLeaderboard } from "../lib/gameSocket";

export default function MatchEnd({ player, matchResult, onReplay }) {
  const [leaderboard, setLeaderboard] = useState(null);
  const [leaderboardError, setLeaderboardError] = useState(false);

  useEffect(() => {
    fetchLeaderboard(10)
      .then(setLeaderboard)
      .catch(() => setLeaderboardError(true));
  }, []);

  const { scores = {}, winner_id, is_draw, opponent } = matchResult;
  const myScore = scores[player.id] ?? 0;
  const opponentScore = opponent ? scores[opponent.id] ?? 0 : 0;

  let title = "Match terminé";
  let titleColor = "var(--parchment)";
  if (is_draw) {
    title = "Égalité !";
    titleColor = "var(--gold)";
  } else if (winner_id === player.id) {
    title = "Victoire !";
    titleColor = "var(--teal)";
  } else {
    title = "Défaite";
    titleColor = "var(--coral)";
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg flex flex-col gap-8 items-center">
        <div className="text-center flex flex-col gap-2">
          <h2 className="font-display text-4xl font-black" style={{ color: titleColor }}>
            {title}
          </h2>
        </div>

        <div
          className="w-full flex items-center justify-between border px-6 py-5"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}
        >
          <div className="text-left">
            <div className="font-semibold">{player.pseudo}</div>
            <div className="font-mono-score text-3xl" style={{ color: "var(--teal)" }}>
              {myScore}
            </div>
          </div>
          <div className="font-mono-score text-2xl" style={{ color: "var(--gold)" }}>—</div>
          <div className="text-right">
            <div className="font-semibold">{opponent?.pseudo ?? "Adversaire"}</div>
            <div className="font-mono-score text-3xl" style={{ color: "var(--coral)" }}>
              {opponentScore}
            </div>
          </div>
        </div>

        <div className="w-full border" style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}>
          <div className="px-6 py-4 border-b" style={{ borderColor: "var(--line)" }}>
            <h3 className="font-display text-lg font-semibold">
              Classement <span style={{ color: "var(--gold)", fontStyle: "italic" }}>général</span>
            </h3>
            <p className="text-xs" style={{ color: "var(--parchment-dim)" }}>
              Tous joueurs, toutes catégories confondues
            </p>
          </div>

          <div className="px-2 py-2">
            {leaderboardError && (
              <p className="text-center text-sm py-4" style={{ color: "var(--coral)" }}>
                Classement indisponible pour le moment.
              </p>
            )}

            {!leaderboardError && leaderboard === null && (
              <p className="text-center text-sm py-4" style={{ color: "var(--parchment-dim)" }}>
                Chargement…
              </p>
            )}

            {!leaderboardError && leaderboard && leaderboard.length === 0 && (
              <p className="text-center text-sm py-4" style={{ color: "var(--parchment-dim)" }}>
                Aucun classement pour l'instant.
              </p>
            )}

            {!leaderboardError && leaderboard && leaderboard.length > 0 && (
              <ol className="flex flex-col">
                {leaderboard.map((entry, index) => {
                  const isMe = entry.id === player.id;
                  return (
                    <li
                      key={entry.id}
                      className="flex items-center justify-between px-4 py-2 text-sm"
                      style={{
                        background: isMe ? "rgba(232,178,59,0.12)" : "transparent",
                        color: isMe ? "var(--gold)" : "var(--parchment)",
                      }}
                    >
                      <span className="flex items-center gap-3">
                        <span className="font-mono-score" style={{ color: "var(--parchment-dim)" }}>
                          {index + 1}
                        </span>
                        <span className="font-semibold">{entry.pseudo}</span>
                      </span>
                      <span className="flex items-center gap-4 font-mono-score">
                        <span>{entry.elo_score} pts</span>
                        <span style={{ color: "var(--parchment-dim)" }}>
                          {entry.games_played} parties
                        </span>
                      </span>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        </div>

        <button
          onClick={onReplay}
          className="px-8 py-3 font-bold tracking-wide"
          style={{ background: "var(--gold)", color: "#14100a" }}
        >
          Rejouer
        </button>
      </div>
    </div>
  );
}
