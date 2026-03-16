# Session State

*Mise a jour : 2026-03-16 13:24 GST*

## Tache en cours
Deblocage final de la queue MiniMax prod: l auth interne est corrigee, mais le wrapper `xvfb-run` laisse le service worker `live` sans vrai process Python consommateur.

## Contexte immediat
1. Le worker local Mac est maintenant bloque cote serveur par le filtre `worker_id`.
2. Le worker Render derive maintenant correctement un `worker_id` de type `srv-*` quand son env vaut `auto`.
3. Le shell worker Render a confirme:
   - `DERIVED_ID=srv-d6o382rh46gs73a59h8g-8644669cc5-jgc2l-29`
   - claim manuel => `403 {"detail":"Invalid internal token"}`
4. Correctif auth pousse et deploye via `38351e8`: le worker peut maintenant claim en `200`.
5. Nouveau diagnostic runtime: dans le shell worker, on observe seulement `/bin/sh /usr/bin/xvfb-run ... python -m app.minimax_remote_worker` et `Xvfb`, mais pas de process Python worker long vivant.
6. Cause racine courante: le reexec `xvfb-run` est trop fragile sur Render et peut laisser un conteneur `live` sans consumer MiniMax actif.

## Plan actif
1. Remplacer le reexec `xvfb-run` par un demarrage direct d `Xvfb` depuis Python.
2. Couvrir ce bootstrap par tests.
3. Push + deploy.
4. Revalider que le job queue est repris automatiquement par le worker Render live.

## Prochaine action immediate
Pousser le correctif Xvfb direct puis verifier que la queue quitte `queued` sans claim manuel.
