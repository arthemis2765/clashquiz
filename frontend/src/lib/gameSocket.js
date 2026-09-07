const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/game";
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function getStoredPlayer() {
  const raw = localStorage.getItem("clashquiz_player");
  return raw ? JSON.parse(raw) : null;
}

export function clearStoredPlayer() {
  localStorage.removeItem("clashquiz_player");
}

export async function registerPlayer(pseudo) {
  const res = await fetch(`${API_URL}/api/players/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pseudo }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Impossible de créer le joueur.");
  }
  const player = await res.json();
  localStorage.setItem("clashquiz_player", JSON.stringify(player));
  return player;
}

export async function fetchCategories() {
  const res = await fetch(`${API_URL}/api/categories`);
  return res.json();
}

export async function fetchLeaderboard(limit = 10) {
  const res = await fetch(`${API_URL}/api/leaderboard?limit=${limit}`);
  return res.json();
}

export async function updatePseudo(playerId, deviceToken, pseudo) {
  const res = await fetch(`${API_URL}/api/players/${playerId}/pseudo`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ device_token: deviceToken, pseudo }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Impossible de modifier le pseudo.");
  }
  const player = await res.json();
  localStorage.setItem("clashquiz_player", JSON.stringify(player));
  return player;
}

export function updateStoredPlayer(updates) {
  const player = getStoredPlayer();
  if (!player) return null;
  const updated = { ...player, ...updates };
  localStorage.setItem("clashquiz_player", JSON.stringify(updated));
  return updated;
}

export function connectGameSocket({ onEvent }) {
  const socket = new WebSocket(WS_URL);

  socket.onmessage = (msg) => {
    const data = JSON.parse(msg.data);
    onEvent(data.event, data.payload);
  };

  return {
    raw: socket,
    joinQueue({ playerId, pseudo, categorySlug, deviceToken }) {
      socket.send(JSON.stringify({
        event: "join_queue",
        player_id: playerId,
        pseudo,
        category_slug: categorySlug,
        device_token: deviceToken,
      }));
    },
    createPrivateMatch({ playerId, pseudo, categorySlug, deviceToken }) {
      socket.send(JSON.stringify({
        event: "create_private_match",
        player_id: playerId,
        pseudo,
        category_slug: categorySlug,
        device_token: deviceToken,
      }));
    },
    joinPrivateMatch({ playerId, pseudo, code, deviceToken }) {
      socket.send(JSON.stringify({
        event: "join_private_match",
        player_id: playerId,
        pseudo,
        code,
        device_token: deviceToken,
      }));
    },
    submitAnswer(answer) {
      socket.send(JSON.stringify({ event: "submit_answer", answer }));
    },
    useJoker(jokerType) {
      socket.send(JSON.stringify({ event: "use_joker", joker_type: jokerType }));
    },
    close() {
      socket.close();
    },
  };
}

export async function fetchComments(page = 1, pageSize = 20, viewerId = null) {
  const params = new URLSearchParams({ page, page_size: pageSize });
  if (viewerId) params.set("player_id", viewerId);
  const res = await fetch(`${API_URL}/api/comments?${params}`);
  return res.json();
}

export async function postComment(playerId, deviceToken, content) {
  const res = await fetch(`${API_URL}/api/comments`, {
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
  const res = await fetch(`${API_URL}/api/comments/${commentId}/reactions`, {
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
