const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/game";
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const STORAGE_KEY = "clashquiz_player";
const NETWORK_ERROR_MESSAGE = "Impossible de joindre le serveur. Vérifie ta connexion et réessaie.";
const SERVER_ERROR_MESSAGE = "Le serveur a rencontré un problème. Réessaie dans un instant.";

function removeStoredPlayer() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // stockage indisponible (navigation privée stricte, quota...) : rien à nettoyer
  }
}

export function getStoredPlayer() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const player = JSON.parse(raw);
    if (player && typeof player === "object" && player.id && player.device_token) {
      return player;
    }
  } catch {
    // JSON illisible ou stockage inaccessible : on retombe sur le nettoyage ci-dessous
  }
  // Valeur corrompue ou incomplète : on la supprime pour que l'appli redémarre
  // sur l'écran d'inscription au lieu de replanter à chaque rechargement.
  removeStoredPlayer();
  return null;
}

export function clearStoredPlayer() {
  removeStoredPlayer();
}

// Enveloppe fetch : une coupure réseau lève une erreur en français plutôt que
// le "Failed to fetch" brut du navigateur, directement affichable à l'écran.
async function apiFetch(path, options) {
  try {
    return await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error(NETWORK_ERROR_MESSAGE);
  }
}

// GET JSON qui lève une erreur sur toute réponse non-2xx : sans ça, un corps
// d'erreur ({"detail": ...}) était pris pour des données valides par l'appelant.
async function getJson(path) {
  const res = await apiFetch(path);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : SERVER_ERROR_MESSAGE);
  }
  return res.json();
}

export async function registerPlayer(pseudo) {
  const res = await apiFetch("/api/players/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pseudo }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Impossible de créer le joueur.");
  }
  const player = await res.json();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(player));
  return player;
}

export function fetchCategories() {
  return getJson("/api/categories");
}

export function fetchLeaderboard(limit = 10) {
  return getJson(`/api/leaderboard?limit=${limit}`);
}

export async function updatePseudo(playerId, deviceToken, pseudo) {
  const res = await apiFetch(`/api/players/${playerId}/pseudo`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_token: deviceToken, pseudo }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Impossible de modifier le pseudo.");
  }
  const player = await res.json();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(player));
  return player;
}

export function updateStoredPlayer(updates) {
  const player = getStoredPlayer();
  if (!player) return null;
  const updated = { ...player, ...updates };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return updated;
}

export function connectGameSocket({ onEvent, onClose }) {
  const socket = new WebSocket(WS_URL);

  socket.onmessage = (msg) => {
    let data;
    try {
      data = JSON.parse(msg.data);
    } catch {
      return; // message illisible : on l'ignore plutôt que de casser le handler
    }
    if (!data || typeof data.event !== "string") return;
    onEvent(data.event, data.payload);
  };

  // `onclose` est toujours appelé après une erreur de connexion, donc il suffit
  // à couvrir à la fois "impossible de se connecter" et "connexion perdue".
  socket.onclose = (event) => {
    if (onClose) onClose(event);
  };

  // Évite l'exception InvalidStateError si on envoie sur un socket fermé ou
  // pas encore ouvert. Retourne true si le message est bien parti.
  function send(message) {
    if (socket.readyState !== WebSocket.OPEN) return false;
    socket.send(JSON.stringify(message));
    return true;
  }

  return {
    raw: socket,
    joinQueue({ playerId, pseudo, categorySlug, deviceToken }) {
      return send({
        event: "join_queue",
        player_id: playerId,
        pseudo,
        category_slug: categorySlug,
        device_token: deviceToken,
      });
    },
    createPrivateMatch({ playerId, pseudo, categorySlug, deviceToken }) {
      return send({
        event: "create_private_match",
        player_id: playerId,
        pseudo,
        category_slug: categorySlug,
        device_token: deviceToken,
      });
    },
    joinPrivateMatch({ playerId, pseudo, code, deviceToken }) {
      return send({
        event: "join_private_match",
        player_id: playerId,
        pseudo,
        code,
        device_token: deviceToken,
      });
    },
    submitAnswer(answer) {
      return send({ event: "submit_answer", answer });
    },
    useJoker(jokerType) {
      return send({ event: "use_joker", joker_type: jokerType });
    },
    close() {
      socket.close();
    },
  };
}

export function fetchComments(page = 1, pageSize = 20, viewerId = null) {
  const params = new URLSearchParams({ page, page_size: pageSize });
  if (viewerId) params.set("player_id", viewerId);
  return getJson(`/api/comments?${params}`);
}

export async function postComment(playerId, deviceToken, content) {
  const res = await apiFetch("/api/comments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player_id: playerId, device_token: deviceToken, content }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Impossible d'envoyer le commentaire.");
  }
  return res.json();
}

export async function toggleReaction(commentId, playerId, deviceToken, emoji) {
  const res = await apiFetch(`/api/comments/${commentId}/reactions`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player_id: playerId, device_token: deviceToken, emoji }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Impossible d'enregistrer la réaction.");
  }
  return res.json();
}
