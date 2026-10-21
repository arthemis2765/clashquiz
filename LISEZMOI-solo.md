# ClashQuiz — mode solo amélioré + durées + bug du compte à rebours

Copie ces fichiers par-dessus ton projet (mêmes chemins). Aucune migration de base : le schéma n'a pas changé.

## Backend
| Fichier | Changement |
|---|---|
| `app/routers/solo.py` | réécrit (voir ci-dessous) |
| `app/text_utils.py` | **nouveau** : comparaison des réponses partagée solo + multijoueur |
| `app/websocket/game.py` | utilise `text_utils` au lieu de sa propre `normalize_answer` |
| `app/rate_limit.py` | limiteur `solo_start_limiter` + purge des clés inactives (fuite mémoire) |
| `tests/`, `requirements-dev.txt` | **nouveau** : 50 tests (`pip install -r requirements-dev.txt && pytest`) |

### Corrections
- **Réponse rejouée** : chaque réponse porte `question_number`. Si la réponse HTTP se perd et que le client réessaie, le serveur répond 409 `stale_question` au lieu de retirer une vie sur la question suivante. Nouvelle route `POST /api/solo/current` pour se resynchroniser.
- **Course** : la ligne de la partie est verrouillée (`SELECT … FOR UPDATE`) pendant le traitement.
- **« Temps écoulé »** : une réponse vide envoyée à l'échéance est maintenant bien un `timeout` (avant : `wrong`).
- **Record** : les parties abandonnées comptent (avant : seulement les parties « terminées »).
- **Réponses** : accents, casse, tirets et ponctuation ignorés (« etats unis » = « États-Unis ») ; le texte entre parenthèses est facultatif (« ADN » accepté pour « ADN (acide désoxyribonucléique) »). Pas de tolérance de fautes de frappe volontairement (Irlande/Islande, Zambie/Gambie).

### Sécurité
- Limite de 30 démarrages de partie / 10 min / joueur (429 au-delà).
- Tailles maximales sur tous les champs (`player_id`, `device_token`, `run_id`…).
- Le classement n'expose aucun identifiant de joueur (champ `is_me` à la place).

### Classement solo
`GET /api/solo/leaderboard?category_slug=&player_id=&limit=` : meilleur score par thème, ou somme des meilleurs scores sur tous les thèmes actifs. Ex æquo = même rang, et `me` donne ton rang même hors du top.
`POST /api/solo/abandon` : clôt la partie quand on quitte (le score compte tout de suite).

## Frontend
| Fichier | Changement |
|---|---|
| `src/lib/soloApi.js` | erreurs typées (`SoloError`), `currentSolo`, `abandonSolo`, `fetchSoloLeaderboard` |
| `src/pages/Solo.jsx` | numéro de question, resynchronisation, abandon, record affiché, bouton « Voir le classement solo », plus de double démarrage en StrictMode |
| `src/pages/Leaderboard.jsx` | onglets Multijoueur / Solo + filtre par thème + ton rang |
| `src/App.jsx` | ouverture du classement solo depuis l'écran de fin |

## Durées (demande du 21 oct.)
- **15 s par tour** en multijoueur (avant : 10 s) : `TURN_DURATION_SECONDS` dans `app/websocket/manager.py`.
- **Joker temps : +10 s** (avant : +15 s) : `EXTRA_TIME_BONUS_SECONDS`, même fichier. Le solo utilise la même constante, donc son joker passe aussi à +10 s (la question solo reste à 15 s).
- Libellés mis à jour : `Duel.jsx`, `Solo.jsx` et les règles (`Rules.jsx`).
- Le seuil « réponse rapide » (difficulté +1) reste à 5 s.

## Bug « duel va commencer 3737 s »
Cause : le serveur envoyait une heure absolue (`deadline`) et le navigateur la comparait à l'horloge du PC. Un PC décalé d'environ 1 h affichait 3737 s. Correction : le serveur envoie `seconds_left` (calculé avec SON horloge) et `Duel.jsx` en déduit une échéance locale. Testé avec une horloge volontairement décalée de 62 min : le compteur affiche « duel dans 9s ». Le texte « duel va commence » est aussi corrigé.
Au passage : `game.py` ne plante plus si le `player_id` reçu n'est pas un UUID valide.

## Optionnel
Si `solo_runs` devient grosse : `CREATE INDEX IF NOT EXISTS ix_solo_runs_cat_score ON solo_runs (category_id, score DESC);`

## À supprimer (anciennes copies, jamais utilisées par le Procfile)
`backend/main.py`, `backend/models.py`, `backend/seed.py`, `backend/routers/`, `backend/data/`, `frontend/src/src/`.
