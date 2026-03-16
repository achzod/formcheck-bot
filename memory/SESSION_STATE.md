# Session State

*Mise a jour : 2026-03-16 13:10 GST*

## Tache en cours
Deblocage final de la queue MiniMax prod: le worker Render live est sain, mais son claim est refuse par le web avec `Invalid internal token`.

## Contexte immediat
1. Le worker local Mac est maintenant bloque cote serveur par le filtre `worker_id`.
2. Le worker Render derive maintenant correctement un `worker_id` de type `srv-*` quand son env vaut `auto`.
3. Les deploys Render live au moment du diagnostic:
   - worker `8374f41` live
   - web `8374f41` encore en `update_in_progress`
4. Le shell worker Render confirme:
   - `DERIVED_ID=srv-d6o382rh46gs73a59h8g-8644669cc5-jgc2l-29`
   - claim manuel => `403 {"detail":"Invalid internal token"}`
5. Cause racine courante: le web n accepte qu un seul token interne effectif, alors que l architecture supporte a la fois `MINIMAX_REMOTE_WORKER_TOKEN` et `RENDER_API_KEY`.

## Plan actif
1. Autoriser cote web tous les tokens internes valides configures.
2. Couvrir le drift token par tests.
3. Push + deploy.
4. Revalider depuis le shell worker puis verifier que le job queue passe en `processing` ou `completed`.

## Prochaine action immediate
Attendre le deploy du correctif token, puis retester le `claim` depuis le shell worker Render.
