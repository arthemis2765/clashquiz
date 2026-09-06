import { useEffect, useState } from "react";
import Home from "./pages/Home";
import CategorySelect from "./pages/CategorySelect";
import PrivateGame from "./pages/PrivateGame";
import Duel from "./pages/Duel";
import MatchResult from "./pages/MatchResult";
import Leaderboard from "./pages/Leaderboard";
import Profile from "./pages/Profile";
import Rules from "./pages/Rules";
import Menu from "./components/Menu";
import { getStoredPlayer, clearStoredPlayer, updateStoredPlayer } from "./lib/gameSocket";

export default function App() {
  const [player, setPlayer] = useState(getStoredPlayer());
  const [category, setCategory] = useState(null);
  const [mode, setMode] = useState(null); // "queue" | "create_private" | "join_private"
  const [privateCode, setPrivateCode] = useState(null);
  const [matchResult, setMatchResult] = useState(null);
  const [menuView, setMenuView] = useState(null); // "leaderboard" | "profile" | "rules" | "private"

  // Lien d'invitation reçu d'un ami (?match=CODE) : on le capture une fois au
  // chargement, on nettoie l'URL, puis on rejoint automatiquement la partie
  // dès qu'un pseudo est disponible.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("match");
    if (code) {
      setPrivateCode(code.toUpperCase());
      setMode("join_private");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  function resetToMenu() {
    setMatchResult(null);
    setCategory(null);
    setMode(null);
    setPrivateCode(null);
    setMenuView(null);
  }

  function handleMenuNavigate(key) {
    if (key === "logout") {
      clearStoredPlayer();
      resetToMenu();
      setPlayer(null);
      return;
    }
    // "private", "leaderboard", "profile", "rules" ouvrent chacun leur propre
    // écran dédié via menuView (cf. les branches ci-dessous dans le render).
    setMenuView(key);
  }

  function handleMatchEnd(payload) {
    const newElo = payload.elo?.[player.id];
    const eloBefore = player.elo_score;

    if (typeof newElo === "number") {
      const updated = updateStoredPlayer({
        elo_score: newElo,
        games_played: (player.games_played ?? 0) + 1,
      });
      if (updated) setPlayer(updated);
    }

    setMatchResult({ ...payload, eloBefore });
  }

  function handleRejouer() {
    setMatchResult(null);
    if (category) {
      // Repart en recherche aléatoire dans la même catégorie (un code privé
      // ne se réutilise pas).
      setMode("queue");
      setPrivateCode(null);
    } else {
      resetToMenu();
    }
  }

  if (!player) {
    return <Home onRegistered={setPlayer} />;
  }

  if (menuView === "leaderboard") {
    return <Leaderboard player={player} onBack={() => setMenuView(null)} />;
  }

  if (menuView === "profile") {
    return (
      <Profile
        player={player}
        onBack={() => setMenuView(null)}
        onPseudoChanged={(updatedPlayer) => {
          setPlayer(updatedPlayer);
          // Stats/classement réinitialisés côté serveur : on ramène le joueur
          // à l'écran de choix de thème plutôt que de le laisser sur son profil.
          resetToMenu();
        }}
      />
    );
  }

  if (menuView === "rules") {
    return <Rules onBack={() => setMenuView(null)} />;
  }

  if (menuView === "private") {
    return (
      <PrivateGame
        onBack={() => setMenuView(null)}
        onCreatePrivate={(cat) => {
          setCategory(cat);
          setMode("create_private");
          setMenuView(null);
        }}
        onJoinPrivate={(code) => {
          setPrivateCode(code);
          setMode("join_private");
          setMenuView(null);
        }}
      />
    );
  }

  if (matchResult) {
    return (
      <>
        <Menu onNavigate={handleMenuNavigate} />
        <MatchResult
          player={player}
          category={category}
          matchResult={matchResult}
          onRejouer={handleRejouer}
          onHome={resetToMenu}
        />
      </>
    );
  }

  if (mode) {
    return (
      <Duel
        player={player}
        category={category}
        mode={mode}
        privateCode={privateCode}
        onMatchEnd={handleMatchEnd}
        onAbandon={resetToMenu}
      />
    );
  }

  return (
    <>
      <Menu onNavigate={handleMenuNavigate} />
      <CategorySelect
        player={player}
        onSelect={(cat) => {
          setCategory(cat);
          setMode("queue");
        }}
        onCreatePrivate={(cat) => {
          setCategory(cat);
          setMode("create_private");
        }}
        onJoinPrivate={(code) => {
          setPrivateCode(code);
          setMode("join_private");
        }}
      />
    </>
  );
}
