import { useEffect, useState } from "react";

const DISMISS_KEY = "clashquiz_install_dismissed";

function readDismissed() {
  try {
    return localStorage.getItem(DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

function isStandalone() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

function isIos() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent);
}

export default function InstallPrompt() {
  const [installEvent, setInstallEvent] = useState(null);
  const [hidden, setHidden] = useState(() => readDismissed() || isStandalone());
  const showIosHint = !hidden && !installEvent && isIos();

  useEffect(() => {
    function onBeforeInstall(e) {
      e.preventDefault();
      setInstallEvent(e);
    }
    function onInstalled() {
      setInstallEvent(null);
      setHidden(true);
    }
    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onBeforeInstall);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  function dismiss() {
    try {
      localStorage.setItem(DISMISS_KEY, "1");
    } catch {
      /* stockage indisponible : on masque seulement pour cette session */
    }
    setHidden(true);
  }

  async function install() {
    if (!installEvent) return;
    installEvent.prompt();
    await installEvent.userChoice.catch(() => null);
    setInstallEvent(null);
    setHidden(true);
  }

  if (hidden || (!installEvent && !showIosHint)) return null;

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-50 flex justify-center px-4 pb-4"
      role="dialog"
      aria-label="Installer l'application"
    >
      <div
        className="w-full max-w-md flex items-center gap-3 border px-4 py-3"
        style={{ background: "var(--bg-panel)", borderColor: "var(--gold)" }}
      >
        <p className="flex-1 text-sm" style={{ color: "var(--parchment)" }}>
          {installEvent
            ? "Installe ClashQuiz sur ton écran d'accueil."
            : "Pour installer : touche Partager, puis « Sur l'écran d'accueil »."}
        </p>
        {installEvent && (
          <button
            onClick={install}
            className="shrink-0 px-3 py-1.5 text-sm font-bold"
            style={{ background: "var(--gold)", color: "#14100a" }}
          >
            Installer
          </button>
        )}
        <button
          onClick={dismiss}
          aria-label="Fermer"
          className="shrink-0 px-2 text-sm"
          style={{ color: "var(--parchment-dim)" }}
        >
          {installEvent ? "Plus tard" : "OK"}
        </button>
      </div>
    </div>
  );
}
