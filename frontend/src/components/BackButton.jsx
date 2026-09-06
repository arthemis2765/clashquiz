export default function BackButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex items-center justify-center gap-2 py-3 font-bold tracking-wide border rounded-lg transition-colors"
      style={{ borderColor: "var(--line-strong)", color: "var(--parchment)", background: "transparent" }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = "var(--gold)")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = "var(--line-strong)")}
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m15 18-6-6 6-6" />
      </svg>
      Retour
    </button>
  );
}
