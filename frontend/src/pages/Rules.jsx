import { useState } from "react";
import BackButton from "../components/BackButton";

const RULES = [
  {
    emoji: "🎮",
    title: "Le but du jeu",
    text: "Tu joues contre 1, 2 ou 3 autres joueurs. À chaque question, il faut deviner un pays grâce à son drapeau, ou répondre à une question de sport, de culture ou de cuisine. Celui qui gagne le plus de manches remporte la partie !",
  },
  {
    emoji: "🗂️",
    title: "4 catégories au choix",
    text: "Avant de jouer, tu choisis une catégorie : 🌍 Géographie (deviner un pays à partir de son drapeau), ⚽ Sport, 🧠 Culture générale, ou 🍽️ Cuisine & Gastronomie. Tous les joueurs de la partie répondent aux questions de la même catégorie. Plus tu réponds vite juste, plus les prochaines questions deviennent difficiles !",
  },
  {
    emoji: "⏳",
    title: "Chacun son tour",
    text: "Ce n'est pas la course ! Chaque joueur joue l'un après l'autre, et pas en même temps. Quand c'est ton tour, tu as 10 secondes pour répondre — un petit chrono s'affiche pour t'aider à ne pas trop réfléchir. Quand ce n'est pas ton tour, tu regardes et tu attends gentiment.",
  },
  {
    emoji: "❤️",
    title: "Tes 3 cœurs de vie",
    text: "Tu commences avec 3 cœurs. Si tu te trompes sur ton tour, ou si les 10 secondes se terminent sans réponse, tu perds un cœur. Attention : si tu réponds juste, tu ne perds rien du tout ! Quand tu n'as plus de cœur, tu es éliminé. Le dernier joueur avec au moins un cœur gagne la partie.",
  },
  {
    emoji: "⭐",
    title: "Tes 3 super-pouvoirs (jokers)",
    text: "Tu as 3 jokers à utiliser quand tu veux, seulement pendant TON tour, et tu peux les mélanger comme tu veux entre les 3 types : 💡 Indice (te montre les 2 premières lettres de la réponse), 🙈 Passer (tu sautes ton tour sans perdre de cœur, mais sans gagner de point non plus), ⏰ +15 secondes (te donne un peu plus de temps pour réfléchir, utilisable une seule fois par manche).",
  },
  {
    emoji: "👥",
    title: "Jouer entre amis",
    text: "Tu ne veux pas tomber sur des inconnus ? Crée une partie privée : un code à 6 caractères s'affiche, il te suffit de le partager à tes amis pour qu'ils te rejoignent directement. La partie ne démarre que quand tout le monde est là.",
  },
  {
    emoji: "🏆",
    title: "Le classement",
    text: "Chaque joueur a un score qui démarre à 0. Seuls le gagnant et le 2ème de chaque partie voient leur score bouger : le gagnant gagne toujours 5 points, peu importe l'adversaire, et le perdant n'en perd aucun. Attention : changer de pseudo remet ton score à 0, comme si tu recommençais à zéro.",
  },
];

/** Construit la liste des numéros de page à afficher, avec des "..." pour
 * les pages éloignées de la page courante. Reste lisible même si RULES
 * s'allonge beaucoup plus tard (pas juste pour les 7 règles actuelles). */
function getPageNumbers(current, total) {
  const delta = 1;
  const range = [];
  for (let i = 1; i <= total; i++) {
    if (i === 1 || i === total || (i >= current - delta && i <= current + delta)) {
      range.push(i);
    }
  }
  const withEllipsis = [];
  let prev = null;
  for (const page of range) {
    if (prev !== null && page - prev > 1) withEllipsis.push("...");
    withEllipsis.push(page);
    prev = page;
  }
  return withEllipsis;
}

export default function Rules({ onBack }) {
  const [page, setPage] = useState(1);
  const total = RULES.length;
  const rule = RULES[page - 1];

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md flex flex-col gap-6 animate-card-in">
        <div className="text-center">
          <h2 className="font-display text-3xl font-black">
            Règles du <span style={{ color: "var(--gold)" }}>jeu</span>
          </h2>
        </div>

        <div
          className="border rounded-xl px-5 py-4 min-h-[180px]"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}
        >
          <p className="font-display font-bold text-sm uppercase tracking-widest mb-1.5" style={{ color: "var(--gold)" }}>
            {rule.emoji} {rule.title}
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--parchment-dim)" }}>
            {rule.text}
          </p>
        </div>

        <div className="flex items-center justify-center gap-1.5">
          {getPageNumbers(page, total).map((p, i) =>
            p === "..." ? (
              <span key={`ellipsis-${i}`} className="text-sm px-1" style={{ color: "var(--parchment-dim)" }}>
                …
              </span>
            ) : (
              <button
                key={p}
                onClick={() => setPage(p)}
                className="w-7 h-7 rounded-lg text-sm font-semibold transition-colors"
                style={{
                  border: `1px solid ${p === page ? "var(--gold)" : "var(--line-strong)"}`,
                  background: p === page ? "rgba(232,178,59,0.15)" : "transparent",
                  color: p === page ? "var(--gold)" : "var(--parchment-dim)",
                }}
              >
                {p}
              </button>
            )
          )}
        </div>

        <BackButton onClick={onBack} />
      </div>
    </div>
  );
}
