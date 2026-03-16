# Session State

*Mise a jour : 2026-03-16 13:34 GST*

## Tache en cours
Deblocage final de la chaine MiniMax prod: worker et auth sont corriges, mais il restait une perte de fichier source video avant telechargement par le worker.

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
8. Cause racine courante: la video de job MiniMax etait stockee hors disque persistant web; un redeploiement la rendait indisponible avant fetch worker.

## Plan actif
1. Basculer le stockage media job vers `/app/state/media` quand le disque persistant Render est disponible.
2. Couvrir ce routage stockage par tests.
3. Push + deploy.
4. Revalider sur une nouvelle video que le worker recupere bien le media et va au bout.

## Prochaine action immediate
Pousser le correctif storage persistant puis attendre le redeploy pour le prochain test reel.
