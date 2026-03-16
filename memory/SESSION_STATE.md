# Session State

*Mise a jour : 2026-03-16 13:58 GST*

## Tache en cours
Deblocage final de la chaine MiniMax prod: worker, auth, stockage video et profil Chromium sont corriges; le dernier defaut identifie est un overlay promo MiniMax `MaxClaw Team Mode` qui apparait apres l envoi.

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
10. Verification post-fix du dernier test utilisateur:
   - inbound video `2026-03-16 10:07:18`
   - `analysis_id=17`
   - `job_id=8`
   - job bien claim par le worker Render
   - echec final `MiniMax global analysis timeout reached` a `2026-03-16 10:13:17`
11. Les logs worker actuels montrent des `POST /internal/minimax/jobs/claim 200` en boucle, donc plus de blocage queue/claim.
12. Nouveau test utilisateur `2026-03-16 10:53:03`:
   - `analysis_id=18`, `job_id=9`
   - video telechargee correctement par le worker
   - logs worker `10:53:24`: overlay promo MiniMax `MaxClaw Team Mode is here`
   - la suppression DOM locale etait trop specifique et la boucle post-send ne purgeait pas cet overlay

## Plan actif
1. Push + deploy le fix overlay `MaxClaw Team Mode`.
2. Recontroler le prochain run utilisateur sur la prod.
3. Si un timeout subsiste apres overlay fix, reprendre l audit sur budget timeout ou strategie d attente.

## Prochaine action immediate
Pousser le fix overlay puis surveiller le prochain run `job_id > 9`.
