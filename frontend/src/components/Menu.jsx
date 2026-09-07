import { useEffect, useRef, useState } from "react";

const ITEMS = [
  {
    key: "leaderboard",
    label: "Classement",
    icon: (
      <path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM7 6H4a2 2 0 0 0 2 4M17 6h3a2 2 0 0 1-2 4" />
    ),
  },
  {
    key: "profile",
    label: "Mon profil",
    icon: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21c0-4 4-6 8-6s8 2 8 6" />
      </>
    ),
  },
  {
    key: "private",
    label: "Partie privée",
    icon: <path d="M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1" />,
  },
  {
    key: "rules",
    label: "Règles du jeu",
    icon: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.5-2 1.75-2 3.5M12 17h.01" />
      </>
    ),
  },
  {
    key: "comments",
    label: "Commentaires",
    icon: <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
  },
];

export default function Menu({ onNavigate }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={ref} className="fixed top-4 right-4 z-20">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Menu"
        className="w-10 h-10 flex items-center justify-center rounded-lg transition-colors"
        style={{
          background: "var(--bg-panel)",
          border: "1px solid var(--line-strong)",
          color: "var(--parchment)",
        }}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {open ? <path d="M18 6 6 18M6 6l12 12" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
        </svg>
      </button>

      {open && (
        <div
          className="animate-card-in absolute right-0 mt-2 w-52 rounded-xl overflow-hidden shadow-2xl"
          style={{ background: "var(--bg-panel)", border: "1px solid var(--line-strong)" }}
        >
          {ITEMS.map((item) => (
            <button
              key={item.key}
              onClick={() => {
                setOpen(false);
                onNavigate(item.key);
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-left transition-colors"
              style={{ color: "var(--parchment)" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(241,234,216,0.05)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                {item.icon}
              </svg>
              {item.label}
            </button>
          ))}
          <div style={{ borderTop: "1px solid var(--line)" }}>
            <button
              onClick={() => {
                setOpen(false);
                onNavigate("logout");
              }}
              className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-left transition-colors"
              style={{ color: "var(--coral)" }}
              onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(231,111,81,0.08)")}
              onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <path d="M16 17l5-5-5-5M21 12H9" />
              </svg>
              Déconnexion
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
