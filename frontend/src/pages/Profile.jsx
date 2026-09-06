import { useState } from "react";
import BackButton from "../components/BackButton";
import { updatePseudo } from "../lib/gameSocket";

export default function Profile({ player, onBack, onPseudoChanged }) {
  const [editing, setEditing] = useState(false);
  const [newPseudo, setNewPseudo] = useState(player.pseudo);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const stats = [
    { label: "Pseudo", value: player.pseudo },
    { label: "Score", value: player.elo_score ?? 0 },
    { label: "Parties jouées", value: player.games_played ?? 0 },
  ];

  function startEditing() {
    setNewPseudo(player.pseudo);
    setError(null);
    setEditing(true);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = newPseudo.trim();
    if (!trimmed || trimmed === player.pseudo) {
      setEditing(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const updated = await updatePseudo(player.id, player.device_token, trimmed);
      // La redirection vers l'écran des thèmes est gérée par le parent (App),
      // qui remet aussi à zéro le reste de la navigation (menuView, etc.).
      onPseudoChanged(updated);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm flex flex-col gap-6 animate-card-in">
        <div className="text-center flex flex-col items-center gap-3">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center font-display text-2xl font-black"
            style={{ background: "rgba(232,178,59,0.12)", color: "var(--gold)", border: "1px solid rgba(232,178,59,0.35)" }}
          >
            {player.pseudo.slice(0, 2).toUpperCase()}
          </div>
          <h2 className="font-display text-2xl font-black">{player.pseudo}</h2>
        </div>

        <div className="border rounded-xl overflow-hidden" style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}>
          {stats.map((s, i) => (
            <div
              key={s.label}
              className="flex items-center justify-between px-5 py-4"
              style={{ borderBottom: i < stats.length - 1 ? "1px solid var(--line)" : "none" }}
            >
              <span className="text-sm" style={{ color: "var(--parchment-dim)" }}>{s.label}</span>
              <span className="font-mono-score font-semibold" style={{ color: "var(--parchment)" }}>{s.value}</span>
            </div>
          ))}
        </div>

        {!editing && (
          <button
            type="button"
            onClick={startEditing}
            className="py-3 font-bold tracking-wide border rounded-lg transition-colors"
            style={{ borderColor: "var(--line-strong)", color: "var(--parchment)", background: "transparent" }}
            onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--gold)")}
            onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--line-strong)")}
          >
            Changer de pseudo
          </button>
        )}

        {editing && (
          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-3 rounded-xl px-4 py-4"
            style={{ border: "1px solid var(--coral)", background: "rgba(231,111,81,0.06)" }}
          >
            <p className="text-sm leading-snug" style={{ color: "var(--coral)" }}>
              ⚠️ Changer de pseudo réinitialise ton score et ta position au classement.
            </p>
            <input
              value={newPseudo}
              onChange={(e) => setNewPseudo(e.target.value)}
              maxLength={20}
              autoFocus
              disabled={loading}
              className="px-4 py-3 rounded-lg outline-none"
              style={{
                background: "rgba(241,234,216,0.04)",
                border: "1px solid var(--line-strong)",
                color: "var(--parchment)",
              }}
            />
            {error && (
              <p className="text-xs" style={{ color: "var(--coral)" }}>{error}</p>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setEditing(false)}
                disabled={loading}
                className="flex-1 py-2 text-sm font-semibold border rounded-lg disabled:opacity-50"
                style={{ borderColor: "var(--line-strong)", color: "var(--parchment)", background: "transparent" }}
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={loading || !newPseudo.trim() || newPseudo.trim() === player.pseudo}
                className="flex-1 py-2 text-sm font-bold rounded-lg disabled:opacity-50"
                style={{ background: "var(--gold)", color: "#14100a" }}
              >
                {loading ? "…" : "Modifier"}
              </button>
            </div>
          </form>
        )}

        <BackButton onClick={onBack} />
      </div>
    </div>
  );
}
