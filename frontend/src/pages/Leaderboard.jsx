import { useEffect, useState } from "react";
import { fetchLeaderboard } from "../lib/gameSocket";
import BackButton from "../components/BackButton";

export default function Leaderboard({ player, onBack }) {
  const [entries, setEntries] = useState(null);

  useEffect(() => {
    fetchLeaderboard(20).then(setEntries);
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md flex flex-col gap-6 animate-card-in">
        <div className="text-center">
          <h2 className="font-display text-3xl font-black">
            <span style={{ color: "var(--gold)" }}>Classement</span> général
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--parchment-dim)" }}>
            Les meilleurs scores de ClashQuiz
          </p>
        </div>

        <div className="border rounded-xl overflow-hidden" style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}>
          {entries === null && (
            <div className="px-4 py-8 text-center text-sm" style={{ color: "var(--parchment-dim)" }}>
              Chargement…
            </div>
          )}
          {entries?.length === 0 && (
            <div className="px-4 py-8 text-center text-sm" style={{ color: "var(--parchment-dim)" }}>
              Aucune partie jouée pour l'instant.
            </div>
          )}
          {entries?.map((entry) => {
            const isMe = entry.player_id === player.id;
            const medal = entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : null;
            return (
              <div
                key={entry.player_id}
                className="flex items-center justify-between px-4 py-3 text-sm"
                style={{
                  borderBottom: "1px solid var(--line)",
                  background: isMe ? "rgba(232,178,59,0.08)" : "transparent",
                }}
              >
                <span className="flex items-center gap-3 min-w-0">
                  <span
                    className="font-mono-score shrink-0 text-center"
                    style={{ color: "var(--parchment-dim)", width: "1.75rem", display: "inline-block" }}
                  >
                    {medal ?? `#${entry.rank}`}
                  </span>
                  <span className="font-semibold truncate" style={{ color: isMe ? "var(--gold)" : "var(--parchment)" }}>
                    {entry.pseudo}{isMe && " (toi)"}
                  </span>
                </span>
                <span className="flex items-center gap-3 shrink-0 font-mono-score" style={{ color: "var(--parchment-dim)" }}>
                  <span>{entry.games_played} parties</span>
                  <span style={{ color: "var(--gold)" }}>{entry.elo_score} pts</span>
                </span>
              </div>
            );
          })}
        </div>

        <BackButton onClick={onBack} />
      </div>
    </div>
  );
}
