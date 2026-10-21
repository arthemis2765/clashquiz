import { useEffect, useState } from "react";
import { fetchCategories, fetchLeaderboard } from "../lib/gameSocket";
import { fetchSoloLeaderboard } from "../lib/soloApi";
import BackButton from "../components/BackButton";

const TABS = [
  { key: "duel", label: "Multijoueur" },
  { key: "solo", label: "Solo" },
];

function chipStyle(active) {
  return {
    border: `1px solid ${active ? "var(--gold)" : "var(--line-strong)"}`,
    background: active ? "rgba(232,178,59,0.12)" : "transparent",
    color: active ? "var(--gold)" : "var(--parchment-dim)",
  };
}

// Normalise les deux classements dans le même format d'affichage.
function fromDuel(data, playerId) {
  return {
    entries: data.map((e) => ({
      key: e.player_id,
      rank: e.rank,
      pseudo: e.pseudo,
      isMe: e.player_id === playerId,
      detail: `${e.games_played} parties`,
      score: `${e.elo_score} pts`,
    })),
    me: null,
  };
}

function fromSolo(data, showThemes) {
  return {
    entries: data.entries.map((e, index) => ({
      key: `${index}-${e.pseudo}`,
      rank: e.rank,
      pseudo: e.pseudo,
      isMe: e.is_me,
      detail: showThemes ? `${e.themes} thème${e.themes > 1 ? "s" : ""}` : null,
      score: `${e.score} rép.`,
    })),
    me: data.me,
  };
}

export default function Leaderboard({ player, onBack, initialTab = "duel", initialCategory = null }) {
  const [tab, setTab] = useState(initialTab);
  const [soloCategory, setSoloCategory] = useState(initialCategory); // slug, ou null = tous les thèmes
  const [categories, setCategories] = useState([]);
  const [board, setBoard] = useState(null); // { entries, me }
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchCategories()
      .then((data) => {
        if (!cancelled) setCategories(data);
      })
      .catch(() => {}); // les onglets de thème sont facultatifs : le classement reste affiché sans
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setBoard(null);
    setError(null);
    const request =
      tab === "duel"
        ? fetchLeaderboard(20).then((data) => fromDuel(data, player.id))
        : fetchSoloLeaderboard({ categorySlug: soloCategory, playerId: player.id, limit: 20 }).then((data) =>
            fromSolo(data, !soloCategory),
          );
    request
      .then((result) => {
        if (!cancelled) setBoard(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [tab, soloCategory, reloadKey, player.id]);

  const entries = board?.entries ?? null;
  const me = board?.me ?? null;
  const meInList = entries?.some((e) => e.isMe) ?? false;
  const categoryName = categories.find((c) => c.slug === soloCategory)?.name;

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md flex flex-col gap-6 animate-card-in">
        <div className="text-center">
          <h2 className="font-display text-3xl font-black">
            <span style={{ color: "var(--gold)" }}>Classement</span> {tab === "solo" ? "solo" : "général"}
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--parchment-dim)" }}>
            {tab === "solo"
              ? soloCategory
                ? `Meilleur nombre de bonnes réponses en ${categoryName ?? "ce thème"}`
                : "Somme de ton meilleur score dans chaque thème"
              : "Les meilleurs scores de ClashQuiz"}
          </p>
        </div>

        <div className="flex gap-2" role="tablist" aria-label="Type de classement">
          {TABS.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => setTab(t.key)}
              className="flex-1 py-2 text-sm font-semibold rounded-lg"
              style={chipStyle(tab === t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "solo" && categories.length > 0 && (
          <div className="flex flex-wrap gap-2 justify-center">
            <button
              onClick={() => setSoloCategory(null)}
              className="px-3 py-1 text-xs rounded-full"
              style={chipStyle(soloCategory === null)}
            >
              Tous les thèmes
            </button>
            {categories.map((c) => (
              <button
                key={c.slug}
                onClick={() => setSoloCategory(c.slug)}
                className="px-3 py-1 text-xs rounded-full"
                style={chipStyle(soloCategory === c.slug)}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}

        <div className="border rounded-xl overflow-hidden" style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}>
          {entries === null && !error && (
            <div className="px-4 py-8 text-center text-sm" style={{ color: "var(--parchment-dim)" }}>
              Chargement…
            </div>
          )}
          {error && (
            <div
              className="px-4 py-8 text-center text-sm flex flex-col items-center gap-3"
              style={{ color: "var(--coral)" }}
            >
              <span>{error}</span>
              <button
                onClick={() => setReloadKey((k) => k + 1)}
                className="px-3 py-1 rounded-lg text-xs"
                style={{ border: "1px solid var(--line-strong)", color: "var(--parchment-dim)" }}
              >
                Réessayer
              </button>
            </div>
          )}
          {entries?.length === 0 && (
            <div className="px-4 py-8 text-center text-sm" style={{ color: "var(--parchment-dim)" }}>
              {tab === "solo" ? "Aucune partie solo pour l'instant. Sois le premier !" : "Aucune partie jouée pour l'instant."}
            </div>
          )}
          {entries?.map((entry) => {
            const medal = entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : null;
            return (
              <div
                key={entry.key}
                className="flex items-center justify-between px-4 py-3 text-sm"
                style={{
                  borderBottom: "1px solid var(--line)",
                  background: entry.isMe ? "rgba(232,178,59,0.08)" : "transparent",
                }}
              >
                <span className="flex items-center gap-3 min-w-0">
                  <span
                    className="font-mono-score shrink-0 text-center"
                    style={{ color: "var(--parchment-dim)", width: "1.75rem", display: "inline-block" }}
                  >
                    {medal ?? `#${entry.rank}`}
                  </span>
                  <span className="font-semibold truncate" style={{ color: entry.isMe ? "var(--gold)" : "var(--parchment)" }}>
                    {entry.pseudo}
                    {entry.isMe && " (toi)"}
                  </span>
                </span>
                <span className="flex items-center gap-3 shrink-0 font-mono-score" style={{ color: "var(--parchment-dim)" }}>
                  {entry.detail && <span>{entry.detail}</span>}
                  <span style={{ color: "var(--gold)" }}>{entry.score}</span>
                </span>
              </div>
            );
          })}
          {me && !meInList && (
            <div
              className="flex items-center justify-between px-4 py-3 text-sm"
              style={{ background: "rgba(232,178,59,0.08)", borderTop: "1px solid var(--line-strong)" }}
            >
              <span className="font-semibold" style={{ color: "var(--gold)" }}>
                Ton rang : #{me.rank}
              </span>
              <span className="font-mono-score" style={{ color: "var(--gold)" }}>
                {me.score} rép.
              </span>
            </div>
          )}
        </div>

        <BackButton onClick={onBack} />
      </div>
    </div>
  );
}
