import { useEffect, useRef, useState } from "react";
import { connectGameSocket } from "../lib/gameSocket";

function Hearts({ count, max = 3, color }) {
  return (
    <div className="flex gap-1 justify-center">
      {Array.from({ length: max }).map((_, i) => (
        <span
          key={i}
          className="text-lg leading-none"
          style={{ color: i < count ? color : "rgba(241,234,216,0.15)" }}
        >
          ♥
        </span>
      ))}
    </div>
  );
}

function JokerBar({ charges, optedOut, disabled, onUse }) {
  const jokers = [
    { type: "hint", label: "💡 Indice", disabledExtra: false },
    { type: "extra_time", label: "⏱️ +15s", disabledExtra: false },
    { type: "skip", label: "⏭️ Passer", disabledExtra: optedOut },
  ];

  return (
    <div className="flex gap-2 w-full max-w-sm">
      {jokers.map((j) => (
        <button
          key={j.type}
          type="button"
          onClick={() => onUse(j.type)}
          disabled={disabled || charges <= 0 || j.disabledExtra}
          className="flex-1 py-2 text-xs sm:text-sm font-semibold border transition-opacity disabled:opacity-30"
          style={{ borderColor: "var(--line-strong)", color: "var(--parchment)", background: "transparent" }}
        >
          {j.label}
        </button>
      ))}
      <span
        className="font-mono-score text-xs shrink-0 flex items-center px-2"
        style={{ color: "var(--parchment-dim)" }}
        title="Jokers restants"
      >
        {charges}
      </span>
    </div>
  );
}

export default function Duel({ player, category, mode = "queue", privateCode, onMatchEnd, onAbandon }) {
  const [status, setStatus] = useState("queue"); // queue | playing | round_end | finished
  const [opponents, setOpponents] = useState([]); // [{player_id, pseudo}, ...] — 1 à 3 adversaires
  const [round, setRound] = useState(null); // question de la manche en cours (round_start)
  const [activePlayerId, setActivePlayerId] = useState(null); // qui joue son tour actuellement
  const [turnStatus, setTurnStatus] = useState({}); // pid -> "correct"/"wrong-en-cours"/"timeout"/"skipped", au fil de la manche
  const [scores, setScores] = useState({});
  const [lives, setLives] = useState({});
  const [answer, setAnswer] = useState("");
  const [lastResult, setLastResult] = useState(null);
  const [eliminatedNames, setEliminatedNames] = useState([]);
  const [disconnectNotice, setDisconnectNotice] = useState(null);
  const [shake, setShake] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [toastError, setToastError] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(null);
  const [stuck, setStuck] = useState(false);
  const [waitingCode, setWaitingCode] = useState(null);
  const [queueInfo, setQueueInfo] = useState(null); // {waiting, min_players} — matchmaking public en cours
  const [jokerCharges, setJokerCharges] = useState({});
  const [hintText, setHintText] = useState(null);
  const [optedOut, setOptedOut] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);
  const socketRef = useRef(null);
  const timerRef = useRef(null);
  const lastActivityRef = useRef(Date.now());
  // Le handler WS ci-dessous est créé une seule fois (effet à deps []) : on garde
  // aussi cette valeur dans une ref pour éviter de lire un état figé (stale
  // closure) au moment de l'event match_end.
  const opponentsRef = useRef([]);

  // Tous les joueurs de la partie (moi + adversaires), pour retrouver un
  // pseudo à partir d'un id (scores/lives/eliminated sont keyés par id).
  const allPlayers = [{ id: player.id, pseudo: player.pseudo }, ...opponents.map((o) => ({ id: o.player_id, pseudo: o.pseudo }))];
  const pseudoFor = (id) => allPlayers.find((p) => p.id === id)?.pseudo ?? "Un joueur";
  const isYourTurn = status === "playing" && activePlayerId === player.id;

  function startCountdown(seconds) {
    clearInterval(timerRef.current);
    setSecondsLeft(seconds);
    timerRef.current = setInterval(() => {
      setSecondsLeft((s) => {
        if (s === null || s <= 1) {
          clearInterval(timerRef.current);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  }

  useEffect(() => {
    // Garde contre le double-montage de React.StrictMode en dev (mount ->
    // cleanup -> remount quasi instantané) : sans ça, le premier socket peut
    // avoir le temps de s'ouvrir et d'envoyer join_queue avant que close()
    // ne prenne effet, ce qui inscrit le même joueur deux fois côté serveur
    // et peut le faire atterrir dans deux matchs différents.
    let cancelled = false;
    const socket = connectGameSocket({
      onEvent: (event, payload) => {
        if (cancelled) return;
        lastActivityRef.current = Date.now();
        setStuck(false);

        if (event === "queue_update") {
          // Un joueur vient de rejoindre (ou quitter) la file de matchmaking
          // public : on affiche le compteur pour rassurer le premier arrivé,
          // qui sinon ne sait pas si quelqu'un d'autre est bien en train de
          // chercher une partie de son côté.
          setQueueInfo({ waiting: payload.waiting, minPlayers: payload.min_players });
        }
        if (event === "match_found") {
          opponentsRef.current = payload.opponents ?? [];
          setOpponents(payload.opponents ?? []);
          setWaitingCode(null);
          setQueueInfo(null);
        }
        if (event === "private_match_created") {
          setWaitingCode(payload.code);
        }
        if (event === "joker_hint") {
          setHintText(payload.hint);
          setJokerCharges((prev) => ({ ...prev, [player.id]: payload.remaining }));
        }
        if (event === "joker_extra_time") {
          setSecondsLeft((s) => (s === null ? s : s + payload.bonus_seconds));
          if (payload.used_by === player.id) {
            setJokerCharges((prev) => ({
              ...prev,
              [player.id]: (prev[player.id] ?? 1) - 1,
            }));
          }
        }
        if (event === "round_start") {
          // Nouvelle question pour la manche : tout le monde la voit, mais
          // seul le joueur actif (annoncé juste après par "turn_start") peut
          // répondre. On ne connaît pas encore qui commence ici.
          setStatus("playing");
          setRound(payload);
          setScores(payload.scores);
          setLives(payload.lives);
          setAnswer("");
          setLastResult(null);
          setEliminatedNames([]);
          setHintText(null);
          setOptedOut(false);
          setTurnStatus({});
          setActivePlayerId(null);
          if (payload.joker_charges) setJokerCharges(payload.joker_charges);
        }
        if (event === "turn_start") {
          setStatus("playing");
          setActivePlayerId(payload.active_player_id);
          setAnswer("");
          setHintText(null);
          if (payload.active_player_id === player.id) setOptedOut(false);
          setScores(payload.scores);
          setLives(payload.lives);
          if (payload.joker_charges) setJokerCharges(payload.joker_charges);
          startCountdown(payload.timer_seconds);
        }
        if (event === "turn_result") {
          // Un joueur (correct ou "passer") vient de finir son tour : mise à
          // jour légère, le prochain "turn_start" arrive dans la foulée.
          setTurnStatus((prev) => ({ ...prev, [payload.player_id]: payload.status }));
          setScores(payload.scores);
          setLives(payload.lives);
          clearInterval(timerRef.current);
        }
        if (event === "turn_timeout") {
          setTurnStatus((prev) => ({ ...prev, [payload.player_id]: "timeout" }));
          setScores(payload.scores);
          setLives(payload.lives);
          clearInterval(timerRef.current);
          if (payload.eliminated?.length) {
            setEliminatedNames((prev) => [
              ...prev,
              ...payload.eliminated.map((id) => (id === player.id ? "Toi" : pseudoFor(id))),
            ]);
          }
        }
        if (event === "player_eliminated_mid_round") {
          // Élimination en cours de manche : d'autres tours restent à jouer,
          // la bonne réponse n'est pas encore révélée.
          setScores(payload.scores);
          setLives(payload.lives);
          if (payload.eliminated?.length) {
            setEliminatedNames((prev) => [
              ...prev,
              ...payload.eliminated.map((id) => (id === player.id ? "Toi" : pseudoFor(id))),
            ]);
          }
        }
        if (event === "round_result") {
          // Fin de manche : tous les tours ont été joués, la bonne réponse est révélée.
          setStatus("round_end");
          setScores(payload.scores);
          setLives(payload.lives);
          setTurnStatus(payload.turn_status ?? {});
          setLastResult(payload);
          if (payload.eliminated?.length) {
            setEliminatedNames(payload.eliminated.map((id) =>
              id === player.id ? "Toi" : pseudoFor(id)
            ));
          }
          clearInterval(timerRef.current);
        }
        if (event === "match_end") {
          setStatus("finished");
          clearInterval(timerRef.current);
          onMatchEnd({
            ...payload,
            players: [
              { id: player.id, pseudo: player.pseudo },
              ...opponentsRef.current.map((o) => ({ id: o.player_id, pseudo: o.pseudo })),
            ],
          });
        }
        if (event === "player_disconnected") {
          const name = opponentsRef.current.find((o) => o.player_id === payload.player_id)?.pseudo ?? "Un joueur";
          setDisconnectNotice(`${name} s'est déconnecté(e).`);
          setTimeout(() => setDisconnectNotice(null), 4000);
        }
        if (event === "wrong_answer") {
          setShake(true);
          setTimeout(() => setShake(false), 400);
        }
        if (event === "error") {
          if (payload.fatal === false) {
            // Erreur récupérable (ex : joker déjà utilisé) : simple bandeau
            // temporaire, la partie continue normalement pour tout le monde.
            setToastError(payload.message);
            setTimeout(() => setToastError(null), 3500);
          } else {
            setErrorMessage(payload.message);
          }
        }
      },
    });

    socket.raw.onopen = () => {
      if (cancelled) {
        socket.close();
        return;
      }
      if (mode === "join_private") {
        socket.joinPrivateMatch({
          playerId: player.id,
          pseudo: player.pseudo,
          code: privateCode,
          deviceToken: player.device_token,
        });
      } else if (mode === "create_private") {
        socket.createPrivateMatch({
          playerId: player.id,
          pseudo: player.pseudo,
          categorySlug: category.slug,
          deviceToken: player.device_token,
        });
      } else {
        socket.joinQueue({
          playerId: player.id,
          pseudo: player.pseudo,
          categorySlug: category.slug,
          deviceToken: player.device_token,
        });
      }
    };

    socketRef.current = socket;
    return () => {
      cancelled = true;
      clearInterval(timerRef.current);
      socket.close();
    };
  }, []);

  useEffect(() => {
    // Filet de sécurité : si plus aucun event n'arrive pendant 45s en pleine
    // partie (bug serveur, coupure réseau...), on propose de sortir plutôt que
    // de laisser l'écran figé indéfiniment.
    const watchdog = setInterval(() => {
      const isActive = status === "playing" || status === "round_end";
      if (isActive && Date.now() - lastActivityRef.current > 45000) {
        setStuck(true);
      }
    }, 5000);
    return () => clearInterval(watchdog);
  }, [status]);

  function handleSubmit(e) {
    e.preventDefault();
    if (!answer.trim()) return;
    socketRef.current.submitAnswer(answer.trim());
  }

  if (errorMessage) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 px-4">
        <p className="font-display italic text-lg text-center" style={{ color: "var(--coral)" }}>
          {errorMessage}
        </p>
        <button
          onClick={onAbandon}
          className="px-4 py-2 text-sm font-bold border"
          style={{ borderColor: "var(--line-strong)", color: "var(--parchment)" }}
        >
          Retour à l'accueil
        </button>
      </div>
    );
  }

  function handleCopyLink() {
    const link = `${window.location.origin}${window.location.pathname}?match=${waitingCode}`;
    navigator.clipboard?.writeText(link).then(() => {
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    });
  }

  if (status === "queue") {
    if (mode === "create_private") {
      if (!waitingCode) {
        return (
          <div className="min-h-screen flex items-center justify-center">
            <p className="font-display italic text-lg" style={{ color: "var(--parchment-dim)" }}>
              Création de la partie…
            </p>
          </div>
        );
      }
      const link = `${window.location.origin}${window.location.pathname}?match=${waitingCode}`;
      return (
        <div className="min-h-screen flex items-center justify-center px-4">
          <div className="w-full max-w-sm flex flex-col items-center gap-5 text-center">
            <p className="font-display italic text-lg" style={{ color: "var(--parchment-dim)" }}>
              Partage ce code ou ce lien avec ton ami pour jouer en {category?.name} :
            </p>
            <div
              className="font-mono-score text-3xl tracking-[0.3em] px-6 py-4 w-full"
              style={{ border: "1px solid var(--line-strong)", background: "var(--bg-panel)", color: "var(--gold)" }}
            >
              {waitingCode}
            </div>
            <button
              onClick={handleCopyLink}
              className="w-full py-3 font-bold"
              style={{ background: "var(--gold)", color: "#14100a" }}
            >
              {linkCopied ? "Lien copié !" : "Copier le lien d'invitation"}
            </button>
            <p className="text-xs break-all" style={{ color: "var(--parchment-dim)" }}>{link}</p>
            <p className="font-display italic text-sm" style={{ color: "var(--parchment-dim)" }}>
              En attente de ton ami…
            </p>
            <button
              onClick={onAbandon}
              className="text-sm underline"
              style={{ color: "var(--parchment-dim)" }}
            >
              Annuler
            </button>
          </div>
        </div>
      );
    }

    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-5 px-4">
        <div className="flex items-center gap-2">
          <span
            className="w-2 h-2 rounded-full animate-pulse"
            style={{ background: "var(--teal)" }}
          />
          <p className="font-display italic text-lg text-center" style={{ color: "var(--parchment-dim)" }}>
            {mode === "join_private"
              ? "Connexion à la partie de ton ami…"
              : `Recherche de joueurs en ${category?.name}…`}
          </p>
        </div>
        {mode === "queue" && (
          <p className="text-sm text-center" style={{ color: "var(--gold)" }}>
            {queueInfo
              ? queueInfo.waiting > 1
                ? `${queueInfo.waiting} joueurs connectés — en attente d'encore un peu de monde…`
                : "Tu es le premier ! On attend d'autres joueurs pour lancer la partie…"
              : "Connexion en cours…"}
          </p>
        )}
        {mode === "queue" && (
          <button
            onClick={onAbandon}
            className="text-sm underline"
            style={{ color: "var(--parchment-dim)" }}
          >
            Changer de catégorie
          </button>
        )}
      </div>
    );
  }

  const timeCritical = secondsLeft !== null && secondsLeft <= 5;

  return (
    <div className="min-h-screen w-full flex items-center justify-center px-3 sm:px-4 py-6 overflow-x-hidden">
      <div className="w-full max-w-2xl border" style={{ borderColor: "var(--line-strong)", background: "var(--bg-panel)" }}>
        <div
          className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-3 sm:px-6 py-3 sm:py-4 border-b"
          style={{ borderColor: "var(--line)" }}
        >
          <span className="font-display font-black text-lg sm:text-xl shrink-0">
            Clash<span style={{ color: "var(--gold)", fontStyle: "italic" }}>Quiz</span>
          </span>
          <div className="flex items-center gap-2 sm:gap-4 min-w-0 shrink-0">
            {round?.difficulty && (
              <span
                className="font-mono-score text-[10px] sm:text-xs uppercase tracking-wide sm:tracking-widest whitespace-nowrap"
                style={{ color: "var(--parchment-dim)" }}
              >
                Difficulté {round.difficulty}/5
              </span>
            )}
            <span
              className="font-mono-score text-[10px] sm:text-xs uppercase tracking-wide sm:tracking-widest px-2 py-1 whitespace-nowrap"
              style={{
                color: timeCritical ? "#14100a" : "var(--parchment-dim)",
                background: timeCritical ? "var(--coral)" : "transparent",
              }}
            >
              {status === "playing" ? `${secondsLeft ?? "-"}s` : "—"}
            </span>
          </div>
        </div>

        <div className={`grid grid-cols-2 gap-x-2 gap-y-4 px-3 sm:px-6 py-4 sm:py-6`}>
          {allPlayers.map((p) => {
            const isSelf = p.id === player.id;
            const pLives = lives[p.id] ?? 3;
            const pScore = scores[p.id] ?? 0;
            const eliminated = pLives <= 0;
            const isTurn = status === "playing" && activePlayerId === p.id;
            const pStatus = turnStatus[p.id];
            const color = isSelf ? "var(--teal)" : "var(--coral)";
            return (
              <div
                key={p.id}
                className="text-center min-w-0 transition-opacity"
                style={{
                  opacity: eliminated ? 0.35 : isTurn ? 1 : 0.6,
                  outline: isTurn ? `1px solid ${color}` : "none",
                  padding: isTurn ? "4px" : "0",
                }}
              >
                <div className="font-semibold text-sm sm:text-base truncate px-1">
                  {p.pseudo}{isSelf && " (toi)"}
                </div>
                <div className="font-mono-score text-xl sm:text-2xl" style={{ color }}>
                  {pScore}
                </div>
                <Hearts count={pLives} color={color} />
                {eliminated ? (
                  <div className="text-[10px] uppercase tracking-wide" style={{ color: "var(--coral)" }}>
                    Éliminé
                  </div>
                ) : isTurn ? (
                  <div className="text-[10px] uppercase tracking-wide font-bold" style={{ color: "var(--gold)" }}>
                    ▶ à {isSelf ? "toi" : "son tour"}
                  </div>
                ) : pStatus === "correct" ? (
                  <div className="text-[10px] uppercase tracking-wide" style={{ color: "var(--teal)" }}>✓ trouvé</div>
                ) : pStatus === "timeout" ? (
                  <div className="text-[10px] uppercase tracking-wide" style={{ color: "var(--coral)" }}>✗ temps écoulé</div>
                ) : pStatus === "skipped" ? (
                  <div className="text-[10px] uppercase tracking-wide" style={{ color: "var(--parchment-dim)" }}>passé</div>
                ) : status === "playing" ? (
                  <div className="text-[10px] uppercase tracking-wide" style={{ color: "var(--parchment-dim)" }}>en attente</div>
                ) : null}
              </div>
            );
          })}
        </div>

        <div className="px-3 sm:px-6 pb-6 flex flex-col items-center gap-4">
          {round?.hint_type === "flag" && (
            <div
              className="w-full max-w-[16rem] sm:max-w-[12rem] aspect-[3/2] border flex items-center justify-center overflow-hidden"
              style={{ borderColor: "var(--line-strong)", background: "#0A0F1C" }}
            >
              <img src={round.hint_url} alt="Indice" className="w-full h-full object-cover" />
            </div>
          )}

          {round?.hint_type === "photo" && (
            <div
              className="w-full max-w-sm aspect-[4/3] border flex items-center justify-center overflow-hidden"
              style={{ borderColor: "var(--line-strong)", background: "#0A0F1C" }}
            >
              <img
                src={round.hint_url}
                alt="Devine ce que c'est"
                className="w-full h-full object-cover"
                onError={(e) => { e.currentTarget.style.display = "none"; }}
              />
            </div>
          )}

          {round?.hint_type === "text" && round?.prompt_label && (
            <div
              className="w-full max-w-sm border px-4 sm:px-5 py-4 sm:py-5 text-center"
              style={{ borderColor: "var(--line-strong)", background: "rgba(241,234,216,0.03)" }}
            >
              <p className="font-display text-base sm:text-lg font-semibold" style={{ color: "var(--parchment)" }}>
                {round.prompt_label}
              </p>
            </div>
          )}

          {hintText && (
            <p className="text-sm" style={{ color: "var(--gold)" }}>
              Indice : le pays commence par <b>{hintText}</b>
            </p>
          )}

          {optedOut && status === "playing" && isYourTurn && (
            <p className="text-sm font-display italic" style={{ color: "var(--parchment-dim)" }}>
              Tu as passé ton tour — en attente du résultat…
            </p>
          )}

          {status === "playing" && !isYourTurn && activePlayerId && (
            <p className="text-sm font-display italic" style={{ color: "var(--parchment-dim)" }}>
              Au tour de <b style={{ color: "var(--gold)" }}>{pseudoFor(activePlayerId)}</b> — patiente un instant…
            </p>
          )}

          {disconnectNotice && (
            <p className="font-display italic text-center text-sm" style={{ color: "var(--coral)" }}>
              {disconnectNotice}
            </p>
          )}

          {toastError && (
            <p className="font-display italic text-center text-sm" style={{ color: "var(--coral)" }}>
              {toastError}
            </p>
          )}

          {status === "round_end" && lastResult && (
            <div className="text-center flex flex-col gap-1">
              <p className="font-display italic" style={{ color: "var(--parchment-dim)" }}>
                Réponse : <b style={{ color: "var(--gold)" }}>{lastResult.answer}</b>
              </p>
              <div className="flex flex-wrap justify-center gap-x-3 gap-y-0.5 text-sm">
                {Object.entries(lastResult.turn_status ?? {}).map(([pid, st]) => (
                  <span key={pid} style={{ color: st === "correct" ? "var(--teal)" : "var(--parchment-dim)" }}>
                    {pid === player.id ? "Toi" : pseudoFor(pid)}{" "}
                    {st === "correct" ? "✓" : st === "timeout" ? "✗ (temps écoulé)" : "— passé"}
                  </span>
                ))}
              </div>
              {eliminatedNames.length > 0 && (
                <p className="text-sm" style={{ color: "var(--coral)" }}>
                  🔻 {eliminatedNames.join(", ")} {eliminatedNames.length > 1 ? "sont éliminés" : "est éliminé(e)"} !
                </p>
              )}
            </div>
          )}

          {stuck && (
            <div className="flex flex-col items-center gap-2 text-center">
              <p className="font-display italic" style={{ color: "var(--coral)" }}>
                La partie semble bloquée.
              </p>
              <button
                onClick={onAbandon}
                className="px-4 py-2 text-sm font-bold border"
                style={{ borderColor: "var(--line-strong)", color: "var(--parchment)" }}
              >
                Retour à l'accueil
              </button>
            </div>
          )}

          <JokerBar
            charges={jokerCharges[player.id] ?? 3}
            optedOut={optedOut}
            disabled={!isYourTurn}
            onUse={(type) => {
              if (type === "skip") setOptedOut(true); // feedback instantané, confirmé par "turn_result" juste après
              socketRef.current.useJoker(type);
            }}
          />

          <form onSubmit={handleSubmit} className="flex gap-2 w-full max-w-sm">
            <input
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder={isYourTurn ? "Ta réponse…" : "Ce n'est pas ton tour…"}
              disabled={!isYourTurn || optedOut}
              className={`min-w-0 flex-1 px-3 sm:px-4 py-3 outline-none transition-transform ${shake ? "animate-shake" : ""}`}
              style={{
                background: "rgba(241,234,216,0.04)",
                border: shake ? "1px solid var(--coral)" : "1px solid var(--line-strong)",
                color: "var(--parchment)",
              }}
            />
            <button
              type="submit"
              disabled={!isYourTurn || optedOut}
              className="shrink-0 px-4 sm:px-5 font-bold"
              style={{ background: "var(--gold)", color: "#14100a" }}
            >
              Valider
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
