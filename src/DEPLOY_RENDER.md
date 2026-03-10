# Deploy Render (Web + Worker MiniMax)

## Objectif
Faire tourner le bot 24/7 sans machine locale:
- `formcheck-bot` (webhook WhatsApp + queue + rapports)
- `formcheck-minimax-worker` (navigateur MiniMax AI Motion Coach)

Le blueprint versionne est dans [`render.yaml`](/Users/achzod/clawd/render.yaml).

## Etapes
1. Render Dashboard -> `Blueprints` -> `New Blueprint`.
2. Selectionner ce repo et appliquer `render.yaml`.
3. Verifier que les 2 services sont crees:
   - `formcheck-bot` (Web Service)
   - `formcheck-minimax-worker` (Background Worker)

## Variables critiques (obligatoires)
Configurer ces secrets sur Render:
- `MINIMAX_REMOTE_WORKER_TOKEN` (meme valeur sur web et worker)
- `RENDER_API_KEY` (web, pour admin/debug interne)
- `MINIMAX_BROWSER_EMAIL` (worker)
- Une source d'auth navigateur MiniMax sur le worker:
  - soit `MINIMAX_BROWSER_PASSWORD`
  - soit `MINIMAX_COOKIE` (+ idealement `MINIMAX_BROWSER_LOCAL_STORAGE_JSON`)

## Verification production
1. Web alive:
- `GET /health`
- `GET /health/debug`

2. Queue interne:
- `GET /internal/minimax/queue/stats?token=<RENDER_API_KEY>`

3. Admin:
- `/admin?token=<RENDER_API_KEY>`
- section `Queue MiniMax (worker)` doit bouger pendant un test video

## Notes importantes
- Le worker demarre via `xvfb-run` pour permettre le mode navigateur headed sur Render.
- L'analyse reste source MiniMax stricte (`MINIMAX_STRICT_SOURCE=true`, fallback local desactive).
- Si le worker est down, les jobs restent en queue puis sont repris quand il remonte.
