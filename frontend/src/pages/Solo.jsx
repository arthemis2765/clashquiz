import { useCallback, useEffect, useRef, useState } from "react";
import { startSolo, answerSolo, jokerSolo, currentSolo, abandonSolo } from "../lib/soloApi";
// constantes pour la partie solo 
const MAX_LIVES = 3;
const MAX_DIFFICULTY = 5;
const FEEDBACK_MS = 1400;
// constantes pour les jokers 
const JOKERS = [
  { type: "hint", label: "💡 Indice" },
  { type: "extra_time", label: "⏱️ +10 s" },
  { type: "skip", label: "⏭️ Passer" },
];
// fonction pour afficher les coeurs restants 
function Hearts({ lives }) {
  return (
    <div className="flex justify-center gap-1 text-lg" aria-label={`${lives} vies restantes`}>
      {Array.from({ length: MAX_LIVES }).map((_, i) => (
        <span key={i} style={{ color: i < lives ? "var(--teal)" : "rgba(241,234,216,0.2)" }}>♥</span>
      ))}
    </div>
  );
}
// fonction pour afficher les résultats finaux de la partie solo
function ResultScreen({ category, summary, onReplay, onChangeTheme, onShowLeaderboard }) {
  const record = summary.record ?? 0;
  const progress = record > 0 ? Math.min(100, Math.round((summary.score / record) * 100)) : 100;

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md flex flex-col gap-5 animate-card-in">
        <div className="text-center">
          <h1 className="font-display text-3xl font-bold">Partie terminée</h1>
          <p className="text-sm mt-1" style={{ color: "var(--parchment-dim)" }}>
            {category.name} · solo
          </p>
        </div>

        <div className="text-center">
          <p className="font-display text-7xl font-bold" style={{ color: "var(--gold)" }}>{summary.score}</p>
          <p style={{ color: "var(--parchment-dim)" }}>
            {summary.score > 1 ? "bonnes réponses" : "bonne réponse"}
          </p>
          {summary.new_record && (
            <p className="mt-2 font-display italic" style={{ color: "var(--gold)" }}>Nouveau record !</p>
          )}
        </div>

        <div className="p-4" style={{ background: "var(--bg-panel)" }}>
          <div className="flex justify-between text-sm" style={{ color: "var(--parchment-dim)" }}>
            <span>Record</span>
            <span className="font-mono-score" style={{ color: "var(--parchment)" }}>{record}</span>
          </div>
          <div className="mt-3 h-1.5 w-full" style={{ background: "rgba(241,234,216,0.1)" }}>
            <div className="h-full" style={{ width: `${progress}%`, background: "var(--teal)" }} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="p-4" style={{ background: "var(--bg-panel)" }}>
            <p className="text-sm" style={{ color: "var(--parchment-dim)" }}>Difficulté max</p>
            <p className="font-mono-score text-xl mt-1">{summary.max_difficulty}/{MAX_DIFFICULTY}</p>
          </div>
          <div className="p-4" style={{ background: "var(--bg-panel)" }}>
            <p className="text-sm" style={{ color: "var(--parchment-dim)" }}>Jokers utilisés</p>
            <p className="font-mono-score text-xl mt-1">{summary.jokers_used}/3</p>
          </div>
        </div>

        <div className="flex flex-col gap-2 mt-2">
          <button
            onClick={onReplay}
            className="py-3 font-bold"
            style={{ background: "var(--gold)", color: "#14100a" }}
          >
            ↻ Rejouer
          </button>
          {onShowLeaderboard && (
            <button
              onClick={onShowLeaderboard}
              className="py-3 font-semibold border"
              style={{ borderColor: "var(--gold)", color: "var(--gold)" }}
            >
              🏆 Voir le classement solo
            </button>
          )}
          <button
            onClick={onChangeTheme}
            className="py-3 font-semibold border"
            style={{ borderColor: "var(--line-strong)", color: "var(--parchment)" }}
          >
            Changer de thème
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Solo({ player, category, onQuit, onShowLeaderboard }) {
  const [status, setStatus] = useState("loading"); // loading | playing | feedback | finished | error
  const [state, setState] = useState(null);
  const [question, setQuestion] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState(null); // { result, correct_answer }
  const [hintText, setHintText] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [shake, setShake] = useState(false);

  const deadlineRef = useRef(0);
  const busyRef = useRef(false);
  const timerRef = useRef(null);
  const runRef = useRef(null);
  const numberRef = useRef(0); // numéro de la question affichée, renvoyé avec chaque réponse
  const startedRef = useRef(false); // évite le double démarrage de React.StrictMode en dev
  const startingRef = useRef(false); // ignore un « Rejouer » pendant qu'un démarrage est en cours
  const finishedRef = useRef(false);

  // Fusionne l'état renvoyé par le serveur avec l'état local : les réponses
  // intermédiaires n'incluent pas le record, qu'on garde du démarrage.
  const mergeState = useCallback((next) => setState((prev) => ({ ...(prev ?? {}), ...next })), []);

  const finishRun = useCallback(
    (finalState) => {
      finishedRef.current = true;
      mergeState(finalState);
      setSummary(finalState);
      setStatus("finished");
    },
    [mergeState],
  );

  const loadQuestion = useCallback((q) => {
    numberRef.current = q.number;
    setQuestion(q);
    setAnswer("");
    setHintText(null);
    setNotice(null);
    deadlineRef.current = Date.now() + q.seconds_left * 1000;
    setSecondsLeft(Math.ceil(q.seconds_left));
    setStatus("playing");
  }, []);

  const startRun = useCallback(async () => {
    if (startingRef.current) return;
    startingRef.current = true;
    setStatus("loading");
    setError(null);
    setSummary(null);
    setFeedback(null);
    setNotice(null);
    finishedRef.current = false;
    busyRef.current = false;
    try {
      const data = await startSolo(player, category.slug);
      runRef.current = data.state.run_id;
      setState(data.state);
      loadQuestion(data.question);
    } catch (e) {
      setError(e.message);
      setStatus("error");
    } finally {
      startingRef.current = false;
    }
  }, [player, category.slug, loadQuestion]);

  useEffect(() => {
    // StrictMode (dev) monte, démonte puis remonte le composant : sans ce garde,
    // deux parties seraient créées et la réponse de la première pourrait écraser
    // celle de la seconde (déjà clôturée côté serveur).
    if (!startedRef.current) {
      startedRef.current = true;
      startRun();
    }
    return () => clearTimeout(timerRef.current);
  }, [startRun]);

  // Après une réponse perdue (réseau coupé au mauvais moment) : on redemande au
  // serveur où en est la partie plutôt que de rejouer une requête périmée.
  const resync = useCallback(async () => {
    const res = await currentSolo(player, runRef.current);
    if (res.finished) {
      finishRun(res.state);
      return;
    }
    mergeState(res.state);
    loadQuestion(res.question);
  }, [player, finishRun, mergeState, loadQuestion]);

  const submit = useCallback(
    async (text) => {
      if (busyRef.current || !runRef.current) return;
      busyRef.current = true;
      try {
        const res = await answerSolo(player, runRef.current, numberRef.current, text);
        mergeState(res.state);
        setFeedback({ result: res.result, correct_answer: res.correct_answer });
        setStatus("feedback");
        if (res.result !== "correct") {
          setShake(true);
          setTimeout(() => setShake(false), 400);
        }
        timerRef.current = setTimeout(() => {
          if (res.finished) {
            finishRun(res.state);
          } else {
            loadQuestion(res.question);
          }
          busyRef.current = false;
        }, FEEDBACK_MS);
      } catch (e) {
        if (e.code === "stale_question") {
          // Cette question a déjà été traitée (réponse précédente perdue) : on se resynchronise.
          try {
            await resync();
            setNotice("Connexion rétablie, on continue.");
          } catch (syncError) {
            setNotice(syncError.message);
          }
        } else if (e.status === 409 || e.status === 404) {
          // Partie introuvable ou close (ex. relancée dans un autre onglet).
          setError(e.message);
          setStatus("error");
        } else {
          setNotice(e.message);
          // Réponse automatique en échec (réseau coupé) : on retente dans 3 s au lieu de boucler.
          // Sans risque : le numéro de question empêche de compter la réponse deux fois.
          if (!text) deadlineRef.current = Date.now() + 3000;
        }
        busyRef.current = false;
      }
    },
    [player, mergeState, finishRun, loadQuestion, resync],
  );

  // Décompte local ; à 0 on envoie une réponse vide (le serveur tranche avec son horloge).
  useEffect(() => {
    if (status !== "playing") return undefined;
    const id = setInterval(() => {
      const left = Math.max(0, Math.ceil((deadlineRef.current - Date.now()) / 1000));
      setSecondsLeft(left);
      if (left <= 0) submit("");
    }, 250);
    return () => clearInterval(id);
  }, [status, submit]);

  async function handleJoker(type) {
    if (busyRef.current || status !== "playing" || state?.jokers?.[type]) return;
    busyRef.current = true;
    try {
      const res = await jokerSolo(player, runRef.current, type);
      mergeState(res.state);
      if (type === "hint") setHintText(res.hint);
      if (type === "extra_time") {
        deadlineRef.current = Date.now() + res.seconds_left * 1000;
        setSecondsLeft(Math.ceil(res.seconds_left));
      }
      if (type === "skip") {
        if (res.finished) {
          finishRun(res.state);
        } else {
          loadQuestion(res.question);
        }
      }
    } catch (e) {
      setNotice(e.message);
    } finally {
      busyRef.current = false;
    }
  }

  // Quitter en cours de partie : on la clôture côté serveur (best effort) pour que
  // le score déjà acquis compte tout de suite au record et au classement.
  function handleQuit() {
    if (runRef.current && !finishedRef.current) {
      abandonSolo(player, runRef.current).catch(() => {});
    }
    onQuit();
  }

  function handleShowLeaderboard() {
    onShowLeaderboard?.(category);
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (status !== "playing" || !answer.trim()) return;
    submit(answer);
  }

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="font-display italic" style={{ color: "var(--parchment-dim)" }}>Préparation de la partie…</p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="flex flex-col items-center gap-3 text-center">
          <p className="font-display italic" style={{ color: "var(--coral)" }}>{error}</p>
          <button onClick={startRun} className="px-4 py-2 font-bold" style={{ background: "var(--gold)", color: "#14100a" }}>
            Réessayer
          </button>
          <button onClick={onQuit} className="px-4 py-2 text-sm border" style={{ borderColor: "var(--line-strong)", color: "var(--parchment)" }}>
            Retour aux thèmes
          </button>
        </div>
      </div>
    );
  }

  if (status === "finished" && summary) {
    return (
      <ResultScreen
        category={category}
        summary={summary}
        onReplay={startRun}
        onChangeTheme={onQuit}
        onShowLeaderboard={onShowLeaderboard ? handleShowLeaderboard : undefined}
      />
    );
  }

  const inFeedback = status === "feedback";
  const lowTime = secondsLeft <= 5 && !inFeedback;

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md flex flex-col gap-5 animate-card-in">
        <div className="flex items-baseline justify-between">
          <p className="font-display text-xl font-bold">
            Clash<span className="italic" style={{ color: "var(--gold)" }}>Quiz</span>
          </p>
          <p className="text-sm font-mono-score" style={{ color: lowTime ? "var(--coral)" : "var(--parchment-dim)" }}>
            Difficulté {question?.difficulty}/{MAX_DIFFICULTY} · {inFeedback ? "–" : `${secondsLeft} s`}
          </p>
        </div>

        <div className="text-center flex flex-col items-center gap-1">
          <p className="text-sm font-semibold">{player.pseudo} <span style={{ color: "var(--parchment-dim)" }}>(toi)</span></p>
          <p className="font-display text-4xl font-bold" style={{ color: "var(--teal)" }}>{state?.score ?? 0}</p>
          <Hearts lives={state?.lives ?? 0} />
          <p className="text-xs font-mono-score" style={{ color: "var(--parchment-dim)" }}>
            Record : {Math.max(state?.record ?? 0, state?.score ?? 0)}
          </p>
          <p className="text-[10px] uppercase tracking-wide font-bold mt-1" style={{ color: "var(--gold)" }}>▶ à toi</p>
        </div>

        <div className="flex flex-col items-center gap-3">
          {question?.hint_type === "flag" && (
            <>
              <div
                className="w-full max-w-[16rem] aspect-[3/2] border flex items-center justify-center overflow-hidden"
                style={{ borderColor: "var(--line-strong)", background: "#0A0F1C" }}
              >
                <img src={question.hint_url} alt="Drapeau à deviner" className="w-full h-full object-cover" />
              </div>
              <p style={{ color: "var(--parchment-dim)" }}>Quel est ce pays ?</p>
            </>
          )}

          {question?.hint_type === "photo" && (
            <div
              className="w-full max-w-sm aspect-[4/3] border flex items-center justify-center overflow-hidden"
              style={{ borderColor: "var(--line-strong)", background: "#0A0F1C" }}
            >
              <img src={question.hint_url} alt="Devine ce que c'est" className="w-full h-full object-cover" />
            </div>
          )}

          {question?.hint_type === "text" && (
            <div
              className="w-full border px-5 py-5 text-center"
              style={{ borderColor: "var(--line-strong)", background: "rgba(241,234,216,0.03)" }}
            >
              <p className="font-display text-lg font-semibold">{question.prompt_label}</p>
            </div>
          )}

          {hintText && !inFeedback && (
            <p className="text-sm" style={{ color: "var(--gold)" }}>
              Indice : la réponse commence par <b>{hintText}</b>
            </p>
          )}

          {inFeedback && feedback && (
            <p className="font-display italic text-center" style={{ color: feedback.result === "correct" ? "var(--teal)" : "var(--coral)" }}>
              {feedback.result === "correct" && "Bonne réponse !"}
              {feedback.result === "wrong" && <>Raté ! C'était <b>{feedback.correct_answer}</b>.</>}
              {feedback.result === "timeout" && <>Temps écoulé ! C'était <b>{feedback.correct_answer}</b>.</>}
            </p>
          )}

          {notice && (
            <p className="text-sm text-center" style={{ color: "var(--coral)" }}>{notice}</p>
          )}
        </div>

        <div className="flex gap-2">
          {JOKERS.map((j) => (
            <button
              key={j.type}
              type="button"
              onClick={() => handleJoker(j.type)}
              disabled={inFeedback || state?.jokers?.[j.type]}
              className="flex-1 py-2 text-sm font-semibold border transition-opacity disabled:opacity-30"
              style={{ borderColor: "var(--line-strong)", color: "var(--parchment)", background: "transparent" }}
            >
              {j.label}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Ta réponse…"
            disabled={inFeedback}
            autoFocus
            maxLength={200}
            className={`min-w-0 flex-1 px-4 py-3 outline-none transition-transform ${shake ? "animate-shake" : ""}`}
            style={{
              background: "rgba(241,234,216,0.04)",
              border: shake ? "1px solid var(--coral)" : "1px solid var(--line-strong)",
              color: "var(--parchment)",
            }}
          />
          <button
            type="submit"
            disabled={inFeedback}
            className="shrink-0 px-5 font-bold disabled:opacity-50"
            style={{ background: "var(--gold)", color: "#14100a" }}
          >
            Valider
          </button>
        </form>

        <button
          onClick={handleQuit}
          className="text-xs self-center underline"
          style={{ color: "var(--parchment-dim)" }}
        >
          Abandonner
        </button>
      </div>
    </div>
  );
}
