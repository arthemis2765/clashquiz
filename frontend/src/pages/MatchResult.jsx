import { useState } from "react";

const STATUS_LABEL = {
  correct: { icon: "✅", color: "var(--teal)" },
  wrong: { icon: "❌", color: "var(--coral)" },
  timeout: { icon: "⏱️", color: "var(--parchment-dim)" },
  skipped: { icon: "⏭️", color: "var(--parchment-dim)" },
};

export default function MatchResult({ player, category, matchResult, onRejouer, onHome }) {
  const {
    winner_id: winnerId,
    scores = {},
    lives = {},
    elo = {},
    leaderboard = [],
    players = [],
    rounds_log: roundsLog = [],
    eloBefore,
  } = matchResult;
  const [showRounds, setShowRounds] = useState(false);
  const pseudoFor = (id) => (id === player.id ? "Toi" : players.find((p) => p.id === id)?.pseudo ?? "Un joueur");

  const won = winnerId === player.id;
  const lost = !!winnerId && winnerId !== player.id;
  const isDraw = winnerId === null || winnerId === undefined;

  const title = won ? "Victoire !" : lost ? "Défaite" : isDraw ? "Match nul" : "Fin de partie";

  const newElo = elo[player.id];
  const eloDelta = typeof newElo === "number" && typeof eloBefore === "number" ? newElo - eloBefore : null;

  // Classement de fin de partie : vainqueur en tête, puis par nombre de vies
  // restantes, puis par score — cohérent avec l'élimination progressive.
  const ranked = [...players].sort((a, b) => {
    if (a.id === winnerId) return -1;
    if (b.id === winnerId) return 1;
    const liveDiff = (lives[b.id] ?? 0) - (lives[a.id] ?? 0);
    if (liveDiff !== 0) return liveDiff;
    return (scores[b.id] ?? 0) - (scores[a.id] ?? 0);
  });

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md flex flex-col gap-6">
        <div className="text-center flex flex-col gap-2">
          <h2 className="font-display text-3xl font-black">{title}</h2>
          {typeof newElo === "number" && (
            <p className="font-mono-score text-sm" style={{ color: "var(--parchment-dim)" }}>
              Score Elo : {newElo}
              {eloDelta !== null && (
                <span style={{ color: eloDelta >= 0 ? "var(--teal)" : "var(--coral)" }}>
                  {" "}({eloDelta >= 0 ? "+" : ""}{eloDelta})
                </span>
              )}
            </p>
          )}
        </div>

        <div
          className="border flex flex-col divide-y"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}
        >
          {ranked.map((p, i) => {
            const isSelf = p.id === player.id;
            const isWinner = p.id === winnerId;
            return (
              <div
                key={p.id}
                className="flex items-center justify-between gap-3 px-4 py-3"
                style={{ borderColor: "var(--line)", background: isSelf ? "rgba(232,178,59,0.06)" : "transparent" }}
              >
                <span className="flex items-center gap-3 min-w-0">
                  <span className="font-mono-score text-xs shrink-0 w-4" style={{ color: "var(--parchment-dim)" }}>
                    {i + 1}
                  </span>
                  <span className="font-semibold truncate" style={{ color: isSelf ? "var(--gold)" : "var(--parchment)" }}>
                    {p.pseudo}{isSelf && " (toi)"}{isWinner && " 🏆"}
                  </span>
                </span>
                <span className="flex items-center gap-3 shrink-0 font-mono-score text-sm" style={{ color: "var(--parchment-dim)" }}>
                  <span>{scores[p.id] ?? 0} pts</span>
                  <span>{lives[p.id] ?? 0} ♥</span>
                </span>
              </div>
            );
          })}
        </div>

        {roundsLog.length > 0 && (
          <div className="border" style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}>
            <button
              type="button"
              onClick={() => setShowRounds((v) => !v)}
              className="w-full flex items-center justify-between px-4 py-3"
            >
              <span className="font-display font-bold text-sm uppercase tracking-widest" style={{ color: "var(--gold)" }}>
                Détail des manches
              </span>
              <span style={{ color: "var(--parchment-dim)" }}>{showRounds ? "▲" : "▼"}</span>
            </button>
            {showRounds && (
              <div className="flex flex-col divide-y" style={{ borderColor: "var(--line)" }}>
                {roundsLog.map((r) => (
                  <div key={r.round_number} className="px-4 py-3 flex flex-col gap-2" style={{ borderColor: "var(--line)" }}>
                    <div className="flex items-center justify-between gap-2 text-sm">
                      <span className="font-semibold truncate">Manche {r.round_number} — {r.prompt_label}</span>
                      {r.timed_out && (
                        <span className="font-mono-score text-xs shrink-0" style={{ color: "var(--parchment-dim)" }}>
                          Temps écoulé
                        </span>
                      )}
                    </div>
                    <p className="text-xs" style={{ color: "var(--parchment-dim)" }}>
                      Bonne réponse : <span className="font-semibold" style={{ color: "var(--parchment)" }}>{r.correct_answer}</span>
                    </p>
                    <div className="flex flex-col gap-1">
                      {Object.entries(r.players ?? {}).map(([pid, info]) => {
                        const meta = STATUS_LABEL[info.status] ?? STATUS_LABEL.wrong;
                        return (
                          <div key={pid} className="flex items-center justify-between gap-2 text-xs">
                            <span className="flex items-center gap-2 min-w-0">
                              <span>{meta.icon}</span>
                              <span className="truncate" style={{ color: pid === player.id ? "var(--gold)" : "var(--parchment)" }}>
                                {pseudoFor(pid)}
                              </span>
                            </span>
                            {info.status !== "correct" && info.status !== "skipped" && (
                              <span className="font-mono-score truncate" style={{ color: meta.color }}>
                                {info.submitted ? `« ${info.submitted} »` : "Aucune réponse"}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {leaderboard.length > 0 && (
          <div className="border" style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}>
            <div className="px-4 py-3 border-b" style={{ borderColor: "var(--line)" }}>
              <span className="font-display font-bold text-sm uppercase tracking-widest" style={{ color: "var(--gold)" }}>
                Classement général
              </span>
            </div>
            <div className="flex flex-col">
              {leaderboard.map((entry) => {
                const isMe = entry.player_id === player.id;
                return (
                  <div
                    key={entry.player_id}
                    className="flex items-center justify-between px-4 py-2 text-sm"
                    style={{
                      borderBottom: "1px solid var(--line)",
                      background: isMe ? "rgba(232,178,59,0.08)" : "transparent",
                    }}
                  >
                    <span className="flex items-center gap-3 min-w-0">
                      <span className="font-mono-score shrink-0" style={{ color: "var(--parchment-dim)", width: "1.5rem", display: "inline-block" }}>
                        #{entry.rank}
                      </span>
                      <span className="font-semibold truncate" style={{ color: isMe ? "var(--gold)" : "var(--parchment)" }}>
                        {entry.pseudo}
                      </span>
                    </span>
                    <span className="font-mono-score shrink-0 pl-2" style={{ color: "var(--parchment-dim)" }}>
                      {entry.elo_score} pts
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <p className="text-center font-display italic" style={{ color: "var(--parchment-dim)" }}>
          Envie de rejouer{category ? ` en ${category.name}` : ""}, ou de changer de jeu ?
        </p>

        <div className="flex gap-3">
          <button
            onClick={onRejouer}
            className="flex-1 py-3 font-bold tracking-wide"
            style={{ background: "var(--gold)", color: "#14100a" }}
          >
            Rejouer
          </button>
          <button
            onClick={onHome}
            className="flex-1 py-3 font-bold tracking-wide border flex items-center justify-center gap-2"
            style={{ borderColor: "var(--line-strong)", color: "var(--parchment)", background: "transparent" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Accueil
          </button>
        </div>
      </div>
    </div>
  );
}
