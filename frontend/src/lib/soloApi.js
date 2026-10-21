const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const NETWORK_ERROR_MESSAGE = "Impossible de joindre le serveur. Vérifie ta connexion et réessaie.";
const GENERIC_ERROR_MESSAGE = "Erreur de connexion au serveur.";

// Erreur enrichie : `status` (HTTP) et `code` (ex. "stale_question") permettent
// à l'écran de jeu de réagir autrement qu'en affichant simplement le texte.
export class SoloError extends Error {
  constructor(message, { status = null, code = null, network = false } = {}) {
    super(message);
    this.name = "SoloError";
    this.status = status;
    this.code = code;
    this.network = network;
  }
}

async function request(path, options) {
  let res;
  try {
    res = await fetch(`${API_URL}/api/solo/${path}`, options);
  } catch {
    throw new SoloError(NETWORK_ERROR_MESSAGE, { network: true });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    const message =
      typeof detail === "string" ? detail : typeof detail?.message === "string" ? detail.message : GENERIC_ERROR_MESSAGE;
    throw new SoloError(message, { status: res.status, code: detail?.code ?? null });
  }
  return data;
}

function post(path, body) {
  return request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function auth(player) {
  return { player_id: player.id, device_token: player.device_token };
}

export function startSolo(player, categorySlug) {
  return post("start", { ...auth(player), category_slug: categorySlug });
}

// `questionNumber` : numéro de la question affichée (fourni par le serveur).
// Le serveur refuse (409 « stale_question ») une réponse déjà traitée.
export function answerSolo(player, runId, questionNumber, answer) {
  return post("answer", { ...auth(player), run_id: runId, question_number: questionNumber, answer });
}

export function jokerSolo(player, runId, jokerType) {
  return post("joker", { ...auth(player), run_id: runId, joker_type: jokerType });
}

// Resynchronisation après une réponse perdue : état exact + question en cours.
export function currentSolo(player, runId) {
  return post("current", { ...auth(player), run_id: runId });
}

// Clôt la partie quand le joueur la quitte : son score est enregistré tout de suite.
export function abandonSolo(player, runId) {
  return post("abandon", { ...auth(player), run_id: runId });
}

export function fetchSoloLeaderboard({ categorySlug = null, playerId = null, limit = 20 } = {}) {
  const params = new URLSearchParams({ limit });
  if (categorySlug) params.set("category_slug", categorySlug);
  if (playerId) params.set("player_id", playerId);
  return request(`leaderboard?${params}`);
}
