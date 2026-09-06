import { useEffect, useState } from "react";
import { fetchCategories } from "../lib/gameSocket";

export default function CategorySelect({ player, onSelect, onCreatePrivate, onJoinPrivate }) {
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
          <p className="font-display text-2xl font-bold">
            Bienvenue, <span style={{ color: "var(--gold)" }}>{player.pseudo}</span> !
          </p>
          <p className="text-sm mt-1" style={{ color: "var(--parchment-dim)" }}>
            Choisis un thème pour démarrer.
          </p>
        </div>

        <div className="flex flex-col gap-3">
          {categories.map((cat) => (
            <div
              key={cat.slug}
              className="flex items-stretch gap-2"
              style={{ border: "1px solid var(--line-strong)", background: "var(--bg-panel)" }}
            >
              <button
                onClick={() => onSelect(cat)}
                className="flex-1 text-left px-5 py-4 font-display text-lg font-semibold transition-colors"
                onMouseEnter={(e) => (e.currentTarget.parentElement.style.borderColor = "var(--gold)")}
                onMouseLeave={(e) => (e.currentTarget.parentElement.style.borderColor = "var(--line-strong)")}
              >
                {cat.name}
              </button>
              <button
                onClick={() => onCreatePrivate(cat)}
                title="Inviter un ami"
                className="px-4 flex items-center justify-center text-lg"
                style={{ color: "var(--gold)", borderLeft: "1px solid var(--line)" }}
              >
                🔗
              </button>
            </div>
          ))}
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
      </div>
    </div>
  );
}
