import { useState } from "react";
import { registerPlayer } from "../lib/gameSocket";

export default function Home({ onRegistered }) {
  const [pseudo, setPseudo] = useState("");
  const [loading, setLoading] = useState(false);
  const [focused, setFocused] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();
    if (!pseudo.trim()) return;
    setLoading(true);
    setError("");
    try {
      const player = await registerPlayer(pseudo.trim());
      onRegistered(player);
    } catch (err) {
      setError(err.message || "Impossible de créer le joueur. Réessaie.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="relative w-full max-w-sm">
        {/* Halo doré discret derrière la carte */}
        <div
          className="absolute inset-0 blur-2xl opacity-30 -z-10"
          style={{ background: "radial-gradient(closest-side, var(--gold), transparent)" }}
        />
        <form
          onSubmit={handleSubmit}
          className="animate-card-in w-full p-8 flex flex-col gap-5 rounded-2xl shadow-2xl"
          style={{ border: "1px solid var(--line-strong)", background: "var(--bg-panel)" }}
        >
          <div className="flex flex-col items-center gap-2">
            <h1 className="font-display text-4xl font-black text-center">
              <span style={{ color: "var(--gold)", fontStyle: "italic", fontWeight: 600 }}>Quiz</span>Clash
            </h1>
            <div
              className="h-[2px] w-10 rounded-full"
              style={{ background: "linear-gradient(90deg, var(--gold), var(--teal))" }}
            />
          </div>

          <p className="text-center text-sm" style={{ color: "var(--parchment-dim)" }}>
            Choisis ton pseudo pour affronter un adversaire en direct.
          </p>

          <div className="relative">
            <svg
              className="absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none"
              width="18" height="18" viewBox="0 0 24 24" fill="none"
              stroke={focused ? "var(--gold)" : "var(--parchment-dim)"}
              strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
              style={{ transition: "stroke 0.15s ease" }}
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            <input
              type="text"
              value={pseudo}
              onChange={(e) => setPseudo(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              placeholder="Ton pseudo…"
              maxLength={20}
              autoFocus
              className="w-full pl-10 pr-4 py-3 rounded-lg outline-none"
              style={{
                background: "rgba(241,234,216,0.04)",
                border: `1px solid ${focused ? "var(--gold)" : "var(--line-strong)"}`,
                color: "var(--parchment)",
                boxShadow: focused ? "0 0 0 3px rgba(232,178,59,0.15)" : "none",
                transition: "border-color 0.15s ease, box-shadow 0.15s ease",
              }}
            />
          </div>

          {error && (
            <p className="text-center text-sm" style={{ color: "#e07a5f" }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !pseudo.trim()}
            className="group relative py-3 font-bold tracking-wide rounded-lg flex items-center justify-center gap-2 overflow-hidden transition-transform active:scale-[0.98] disabled:opacity-60 disabled:active:scale-100"
            style={{
              background: "var(--gold)",
              color: "#14100a",
              boxShadow: "0 4px 14px rgba(232,178,59,0.35)",
            }}
          >
            {loading ? (
              <>
                <span
                  className="animate-spin-slow w-4 h-4 rounded-full border-2"
                  style={{ borderColor: "rgba(20,16,10,0.3)", borderTopColor: "#14100a" }}
                />
                Connexion…
              </>
            ) : (
              <>
                Jouer
                <svg
                  width="16" height="16" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                  className="transition-transform group-hover:translate-x-0.5"
                >
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
