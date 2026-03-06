# SESSION STATE — 2026-03-06

## Dernière action
Debug live du blocage `analyse en cours` sur WhatsApp. Le webhook Render reçoit bien la vidéo et la prod est configurée en `MiniMax browser-only` strict avec `remote_worker_enabled=true`, mais aucun process `app.minimax_remote_worker` n'était lancé sur la machine locale pour consommer la queue interne.

## Validation effectuée
- `GET /health/debug`: `browser_only=true`, `strict_source=true`, `fallback_to_local=false`, `remote_worker_enabled=true`
- Dashboard Render `Environment`: variables critiques présentes côté prod, notamment `MINIMAX_REMOTE_WORKER_TOKEN`, `MINIMAX_BROWSER_EMAIL`, `MINIMAX_BROWSER_PASSWORD`
- Vérification locale des process: aucun worker MiniMax en cours
- Vérification locale des artefacts browser: profils Playwright et dumps `localStorage`/`sessionStorage` MiniMax disponibles dans `tmp/`

## Cause retenue
Le statut reste bloqué sur `analyse en cours` parce que la web app publie des jobs MiniMax distants, mais aucun worker browser-only ne les réclame et ne les traite actuellement.

## Travail en cours
1. Démarrer un worker local persistant relié à Render avec le token interne.
2. Le configurer avec le compte MiniMax navigateur et le profil Playwright déjà validé.
3. Vérifier dans les logs qu'il consomme le job en attente et débloque la réponse WhatsApp.

## Fichiers de contexte
- `app/minimax_remote_worker.py`
- `analysis/minimax_motion_coach.py`
- `../memory/2026-03-06.md`
