import { useEffect, useRef, useState } from "react";
import { fetchComments, postComment, toggleReaction } from "../lib/gameSocket";
import BackButton from "../components/BackButton";

const MAX_LENGTH = 300;

const REACTIONS = [
  { key: "heart", emoji: "❤️" },
  { key: "pray", emoji: "🙏🏻" },
  { key: "angry", emoji: "😡" },
  { key: "thumbsup", emoji: "👍🏻" },
];

function ReactionButton({ comment, player, onReacted }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  async function handlePick(emojiKey) {
    setOpen(false);
    const updated = await toggleReaction(comment.id, player.id, player.device_token, emojiKey);
    onReacted(updated);
  }

  const mine = REACTIONS.find((r) => r.key === comment.my_reaction);
  // Total de TOUTES les réactions sur ce commentaire, tous joueurs confondus
  // (pas seulement la mienne) : sans ça, un joueur ne voit jamais que
  // d'autres ont réagi tant qu'il n'a pas réagi lui-même.
  const totalReactions = Object.values(comment.reactions ?? {}).reduce((sum, n) => sum + n, 0);
  // Emojis présents, triés par nombre décroissant, pour l'aperçu compact affiché
  // sur le bouton fermé (ex: "😡 3" même si "mine" est un autre emoji ou vide).
  const topEmojis = REACTIONS
    .filter(({ key }) => (comment.reactions?.[key] ?? 0) > 0)
    .sort((a, b) => (comment.reactions[b.key] ?? 0) - (comment.reactions[a.key] ?? 0));

  return (
    <div ref={ref} className="relative inline-block mt-2">
      {open ? (
        <div
          className="inline-flex items-center gap-1 rounded-full"
          style={{ background: "var(--bg-deep)", border: "1px solid var(--line-strong)", padding: "6px" }}
        >
          {REACTIONS.map(({ key, emoji }) => {
            const count = comment.reactions?.[key] ?? 0;
            return (
              <button
                key={key}
                onClick={() => handlePick(key)}
                aria-label={key}
                className="relative w-8 h-8 rounded-full flex items-center justify-center text-base transition-transform"
                style={{ background: comment.my_reaction === key ? "rgba(232,178,59,0.15)" : "transparent" }}
              >
                {emoji}
                {count > 0 && (
                  <span
                    className="absolute -bottom-1 -right-1 text-[9px] leading-none rounded-full px-1"
                    style={{ background: "var(--bg-panel)", border: "1px solid var(--line-strong)", color: "var(--parchment-dim)" }}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs transition-colors"
          style={{
            border: `1px solid ${mine ? "var(--gold)" : "var(--line-strong)"}`,
            background: mine ? "rgba(232,178,59,0.12)" : "transparent",
            color: mine ? "var(--gold)" : "var(--parchment-dim)",
          }}
        >
          {totalReactions > 0 ? (
            <>
              {topEmojis.slice(0, 3).map(({ key, emoji }) => (
                <span key={key}>{emoji}</span>
              ))}
              <span>{totalReactions}</span>
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="9" />
                <path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01" />
              </svg>
              Réagir
            </>
          )}
        </button>
      )}
    </div>
  );
}

export default function Comments({ player, onBack }) {
  const [comments, setComments] = useState([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchComments(1, 20, player.id).then((data) => {
      setComments(data.items);
      setTotalPages(data.total_pages);
      setLoading(false);
    });
  }, [player.id]);

  async function handleLoadMore() {
    setLoadingMore(true);
    const nextPage = page + 1;
    const data = await fetchComments(nextPage, 20, player.id);
    setComments((prev) => [...prev, ...data.items]);
    setPage(nextPage);
    setTotalPages(data.total_pages);
    setLoadingMore(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) return;
    setSending(true);
    setError(null);
    try {
      const created = await postComment(player.id, player.device_token, trimmed);
      setComments((prev) => [created, ...prev]);
      setText("");
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  function handleReacted(updatedComment) {
    setComments((prev) => prev.map((c) => (c.id === updatedComment.id ? updatedComment : c)));
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md flex flex-col gap-6 animate-card-in">
        <div className="text-center">
          <h2 className="font-display text-3xl font-black">
            <span style={{ color: "var(--gold)" }}>Commentaires</span>
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--parchment-dim)" }}>
            Vos avis nous aident à améliorer ClashQuiz
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, MAX_LENGTH))}
            placeholder="Un avis pour améliorer ClashQuiz ?"
            rows={3}
            className="w-full rounded-lg px-3 py-2 text-sm resize-none outline-none"
            style={{
              background: "var(--bg-deep)",
              border: "1px solid var(--line-strong)",
              color: "var(--parchment)",
            }}
          />
          <div className="flex items-center justify-between">
            <span className="text-xs" style={{ color: "var(--parchment-dim)" }}>
              {text.length}/{MAX_LENGTH}
            </span>
            <button
              type="submit"
              disabled={sending || !text.trim()}
              className="px-4 py-2 rounded-lg text-sm font-semibold transition-opacity"
              style={{
                background: "var(--gold)",
                color: "var(--bg-deep)",
                opacity: sending || !text.trim() ? 0.6 : 1,
              }}
            >
              {sending ? "Envoi…" : "Envoyer"}
            </button>
          </div>
          {error && (
            <p className="text-xs" style={{ color: "var(--coral)" }}>{error}</p>
          )}
        </form>

        <div className="border rounded-xl overflow-hidden" style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}>
          {loading && (
            <div className="px-4 py-8 text-center text-sm" style={{ color: "var(--parchment-dim)" }}>
              Chargement…
            </div>
          )}
          {!loading && comments.length === 0 && (
            <div className="px-4 py-8 text-center text-sm" style={{ color: "var(--parchment-dim)" }}>
              Aucun commentaire pour l'instant. Sois le premier !
            </div>
          )}
          {comments.map((c) => (
            <div
              key={c.id}
              className="flex flex-col gap-1 px-4 py-3 text-sm"
              style={{ borderBottom: "1px solid var(--line)" }}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold" style={{ color: "var(--teal)" }}>{c.pseudo}</span>
                <span className="text-xs" style={{ color: "var(--parchment-dim)" }}>
                  {new Date(c.created_at).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}
                </span>
              </div>
              <p style={{ color: "var(--parchment-dim)" }}>{c.content}</p>
              <ReactionButton comment={c} player={player} onReacted={handleReacted} />
            </div>
          ))}
        </div>

        {!loading && page < totalPages && (
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="self-center text-sm px-4 py-2 rounded-lg"
            style={{ border: "1px solid var(--line-strong)", color: "var(--parchment-dim)" }}
          >
            {loadingMore ? "Chargement…" : "Charger plus"}
          </button>
        )}

        <BackButton onClick={onBack} />
      </div>
    </div>
  );
}
