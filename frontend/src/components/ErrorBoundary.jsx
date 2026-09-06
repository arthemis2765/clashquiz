import { Component } from "react";

/**
 * Filet de sécurité : sans ça, une exception non rattrapée pendant le rendu
 * (ex: conflit DOM provoqué par une extension navigateur, comme le crash
 * "removeChild" observé après déconnexion/reconnexion) fait disparaître
 * TOUTE l'appli et ne laisse que le fond de la page — sans aucun message
 * pour l'utilisateur ni moyen de s'en sortir sans recharger manuellement.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Log console pour le debug ; pas d'appel réseau ici, on ne veut pas
    // ajouter une dépendance à un service externe dans ce garde-fou.
    console.error("Erreur non rattrapée dans l'app :", error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center px-4">
          <div
            className="w-full max-w-sm p-8 flex flex-col items-center gap-4 text-center rounded-2xl"
            style={{ border: "1px solid var(--line-strong)", background: "var(--bg-panel)" }}
          >
            <h2 className="font-display text-2xl font-black">
              Oups, un problème est survenu
            </h2>
            <p className="text-sm" style={{ color: "var(--parchment-dim)" }}>
              Une erreur inattendue a interrompu l'affichage. Si tu utilises
              une extension de navigateur (traduction, bloqueur de pub,
              gestionnaire de mots de passe…), essaie de la désactiver sur ce
              site — c'est la cause la plus fréquente de ce type d'écran.
            </p>
            <button
              onClick={this.handleReload}
              className="px-6 py-3 font-bold tracking-wide rounded-lg"
              style={{ background: "var(--gold)", color: "#14100a" }}
            >
              Recharger la page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
