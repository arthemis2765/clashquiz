ClashQuiz

ClashQuiz est un jeu de competition multijoueur de culture générale.joue avec des amis ou des inconnus. affronte les meilleurs joueurs de ClashQuiz à travers le monde et grimpe dans le classement général.


## Fonctionnalités

- Joueurs connectés en temps réel.
- Catégories : **Géographie**, **Sport**, **Culture Générale**, **Cuisine**
- Parties privées avec code.
- Classement global et historique des parties.
- Score Elo.
- Système de Jokers : **Indice**, **Passer le tour**, **+15 secondes**

## Prérequis

- [Node.js](https://nodejs.org/) 
- [npm](https://www.npmjs.com/)

## Installation

1. **Cloner le dépôt** (si vous ne l'avez pas déjà):
   ```bash
   git clone <repository-url>
   cd frontend
   ```

2. **Installer les dépendances**:
   ```bash
   npm install
   ```

3. **Configuration de l'environnement**:
   Créez un fichier `.env` à la racine du répertoire `frontend` (ou copiez `.env.example`):
   ```bash
   cp .env.example .env
   ```

   Modifiez le fichier `.env` et configurez l'URL de l'API backend :
   ```env
   VITE_API_URL=http://localhost:8000/api
   VITE_WS_URL=ws://localhost:8000/ws/game
   ```

## Utilisation

Démarrer le serveur de développement:

```bash
npm run dev
```

L'application sera disponible à `http://localhost:5173`.

## Création de production

Pour créer une version de production de l'application :

```bash
npm run build
```

## Stack technique

- **Framework**: [React](https://reactjs.org/)
- **Build Tool**: [Vite](https://vitejs.dev/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **State Management**: React Context
- **Routing**: TanStack Router
- **HTTP Client**: Axios

## Licence

Ce projet est sous licence [MIT License](LICENSE).

## React + Vite

Ce template fournit une configuration minimale pour obtenir React fonctionnel dans Vite avec HMR et quelques règles Oxlint.

Actuellement, deux plugins officiels sont disponibles:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) utilise [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) utilise [SWC](https://swc.rs/)

## Compiler React

Le Compiler React n'est pas activé sur ce template en raison de son impact sur les performances de développement et de construction. Pour l'activer, consultez [cette documentation](https://react.dev/learn/react-compiler/installation).

## Développer avec TypeScript

Si vous développez une application de production, nous vous recommandons d'utiliser TypeScript avec des règles de linting sensibles au type activées. Consultez le [template TS](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) pour plus d'informations sur l'intégration de TypeScript et des règles de TypeScript d'Oxlint dans votre projet.
