import { useEffect, useState } from "react";
import BackButton from "../components/BackButton";
import { fetchCategories } from "../lib/gameSocket";

export default function PrivateGame({ onCreatePrivate, onJoinPrivate, onBack }) {
  const [categories, setCategories] = useState([]);
  const [joinCode, setJoinCode] = useState("");
  const [joinError, setJoinError] = useState(null);

  useEffect(() => {
    fetchCategories().then(setCategories);
  }, []);

  function handleJoinSubmit(e) {
    e.preventDefault();
    const code = joinCode.trim().toUpperCase();
    if (code.length < 4) {
      setJoinError("Le code doit faire au moins 4 caractères.");
      return;
    }
    setJoinError(null);
    onJoinPrivate(code);
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md flex flex-col gap-6">
        <div className="text-center animate-card-in">
          <p className="font-display text-2xl font-bold">Partie privée</p>
          <p className="text-sm mt-1" style={{ color: "var(--parchment-dim)" }}>
            Crée une partie entre amis, ou rejoins-en une avec un code.
          </p>
        </div>

        <div className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-widest" style={{ color: "var(--parchment-dim)" }}>
            Créer une partie
          </p>
          <div className="flex flex-col gap-3">
            {categories.map((cat) => (
              <button
                key={cat.slug}
                onClick={() => onCreatePrivate(cat)}
                className="flex items-center justify-between px-5 py-4 text-left font-display text-lg font-semibold transition-colors"
                style={{ border: "1px solid var(--line-strong)", background: "var(--bg-panel)" }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--gold)")}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--line-strong)")}
              >
                {cat.name}
                <span style={{ color: "var(--gold)" }}>🔗</span>
              </button>
            ))}
            {categories.length === 0 && (
              <p className="text-sm text-center py-4" style={{ color: "var(--parchment-dim)" }}>
                Chargement des thèmes…
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex-1 h-px" style={{ background: "var(--line)" }} />
          <span className="text-xs uppercase tracking-widest" style={{ color: "var(--parchment-dim)" }}>ou</span>
          <div className="flex-1 h-px" style={{ background: "var(--line)" }} />
        </div>

        <form onSubmit={handleJoinSubmit} className="flex flex-col gap-2">
          <p className="text-sm text-center" style={{ color: "var(--parchment-dim)" }}>
            Un ami t'a donné un code de partie ?
          </p>
          <div className="flex gap-2">
            <input
              value={joinCode}
              onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
              placeholder="Code (ex : K3F9QZ)"
              maxLength={8}
              className="min-w-0 flex-1 px-4 py-3 outline-none uppercase tracking-widest text-center"
              style={{
                background: "rgba(241,234,216,0.04)",
                border: "1px solid var(--line-strong)",
                color: "var(--parchment)",
              }}
            />
            <button
              type="submit"
              className="shrink-0 px-5 font-bold"
              style={{ background: "var(--gold)", color: "#14100a" }}
            >
              Rejoindre
            </button>
          </div>
          {joinError && (
            <p className="text-xs text-center" style={{ color: "var(--coral)" }}>{joinError}</p>
          )}
        </form>

        <BackButton onClick={onBack} />
      </div>
    </div>
  );
}
