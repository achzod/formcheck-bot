# Session State

*Mise a jour : 2026-03-16 13:58 GST*

## Tache en cours
Deblocage final de la chaine MiniMax prod: worker, auth et stockage video sont corriges; le dernier defaut trouve est un lock du profil Chromium MiniMax partage.

## Contexte immediat
1. Le worker local Mac est maintenant bloque cote serveur par le filtre `worker_id`.
2. Le worker Render derive maintenant correctement un `worker_id` de type `srv-*` quand son env vaut `auto`.
3. Le shell worker Render a confirme:
   - `DERIVED_ID=srv-d6o382rh46gs73a59h8g-8644669cc5-jgc2l-29`
   - claim manuel => `403 {"detail":"Invalid internal token"}`
4. Correctif auth pousse et deploye via `38351e8`: le worker peut maintenant claim en `200`.
5. Correctif Xvfb pousse et deploye via `73b4e5e`: le worker a bien repris automatiquement la queue.
6. Le job `id=6` a alors echoue avec `404 /internal/minimax/jobs/6/video`.
7. Diagnostic web shell: `video_path='media/videos/e168cb58-1b27-4ffe-8d01-2662d3fcffdf.mp4'` et `EXISTS False`.
8. Cause racine suivante confirmee sur le job `id=7`: Chromium echoue avec `The profile appears to be in use by another Chromium process`.
9. Le profil Playwright MiniMax est partage et persistant (`/app/worker-state/minimax_browser_profile`), donc vulnerable aux locks stale entre runs/deploys.

## Plan actif
1. Lancer chaque run MiniMax sur un workspace profil temporaire clone depuis le seed persistant.
2. Purger les locks Chromium `Singleton*` dans ce workspace.
3. Couvrir le comportement par tests.
4. Push + deploy.
5. Revalider sur une nouvelle video que le worker va au bout.

## Prochaine action immediate
Pousser le correctif workspace profil temporaire puis attendre le redeploy pour le prochain test reel.
