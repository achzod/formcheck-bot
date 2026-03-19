- [x] Verifier l etat exact du dernier run prod utilisateur (Twilio -> analyse -> job -> delivery)
- [x] Lire les logs worker du run courant et identifier la panne active exacte
- [x] Corriger uniquement la cause racine confirmee si le code est en cause
- [x] Valider par tests puis verifier le nouvel etat prod
- [x] Corriger la surveillance worker pour ne plus considerer un faux navigateur vivant quand seul le driver ou crashpad reste lance
- [x] Ajouter un heartbeat de job MiniMax pour qu un crash worker redevienne reclaimable rapidement sans faux stale sur analyses longues
- [x] Mettre a jour le blueprint Render et le service worker vers un plan memoire adapte
- [x] Verifier en prod le deploiement code + infra, puis auditer l etat final avant nouveau test utilisateur

Review:
- Cause 1 confirmee: un run MiniMax inline pouvait figer le worker principal.
- Cause 2 confirmee: un sous process d analyse peut rester vivant sans navigateur actif ni payload, puis faire monter l instance jusqu a l OOM.
- Cause 3 corrigee: la detection de navigateur vivant ne compte plus le driver Playwright ni `chrome_crashpad_handler` comme un vrai browser actif.
- Gap de resilience corrige: un worker en cours d analyse envoie maintenant un heartbeat periodique; le reclaim stale peut donc redescendre a 180s sans risquer de dupliquer une analyse longue saine.
- Infra corrigee: worker Render passe de Standard 2 GB a Pro 4 GB, et le blueprint versionne est aligne.
- Validation locale: py_compile OK, `33 passed` sur les suites worker/runtime/endpoint impactees.
- Validation prod: web `live` sur `2684491`, worker `live` sur `2684491`, `/health` et `/health/debug` repondent `200 OK`.
- Risque residuel: il manque encore un nouveau run video WhatsApp reel pour cloturer la verification fonctionnelle bout en bout apres cette passe code + infra.

## 2026-03-17 Incident worker bloque

- [x] Verifier la queue MiniMax en prod et confirmer le symptome exact
- [x] Tracer les logs worker et les evenements Render pour identifier la panne active
- [x] Verifier directement les processus vivants dans le shell worker
- [x] Corriger la cause racine de non consommation de queue
- [x] Valider localement les suites impactees
- [ ] Deployer et verifier en prod que la queue stale se vide

Review:
- Queue prod confirmee bloquee avec `processing=1` et `stale_processing=1`.
- Evenements Render confirment un OOM et des redemarrages.
- Verification shell worker: PID 1 etait `xvfb-run` et il ne restait plus aucun process `python -m app.minimax_remote_worker`; seul `Xvfb` tournait.
- Cause racine corrigee: `bin/service_entrypoint.sh` lance maintenant le worker Python directement en PID 1, sans wrapper `xvfb-run` persistant.
- Validation locale: `pytest -q tests/test_remote_minimax_worker_flow.py tests/test_runtime_config.py` -> `33 passed`.

## 2026-03-17 Incident job MiniMax interminable

- [x] Verifier les logs worker en live et confirmer le pattern de blocage
- [x] Corriger le timeout effectif maximal pour empecher les jobs qui restent en heartbeat sans fin utile
- [x] Propager le plafond de timeout via le contexte web -> worker
- [x] Aligner la config Render (web + worker) sur le nouveau plafond
- [x] Executer les tests unitaires impactes
- [x] Deployer et verifier l etat runtime (health + logs worker)

Review:
- Logs Render confirms: job `11` reste en `heartbeat` continu sans `complete`/`fail` pendant de longues minutes.
- Correctif code: timeout effectif MiniMax passe par defaut a `420s`, grace worker reduite a `60s`, et hard-cap worker ajoute (`MINIMAX_REMOTE_JOB_MAX_TIMEOUT_S`, defaut `540s`).
- Correctif orchestration: web transmet maintenant aussi `minimax_max_effective_timeout_s` au worker par job context.
- Correctif infra: `render.yaml` aligne web+worker avec `MINIMAX_MAX_EFFECTIVE_TIMEOUT_S=420`, et worker avec `MINIMAX_REMOTE_JOB_TIMEOUT_GRACE_S=60` + `MINIMAX_REMOTE_JOB_MAX_TIMEOUT_S=540`.
- Validation locale: `pytest -q tests/test_remote_minimax_worker_flow.py tests/test_runtime_config.py` -> `33 passed`.
- Validation prod: web et worker `live` sur `5254f0a`; `/health` et `/health/debug` renvoient `200`; logs worker montrent un polling `claim` sain en continu apres redeploy (plus de job zombie en heartbeat infini apres restart).

## 2026-03-19 Audit live test utilisateur

- [x] Charger le contexte workspace et relire les traces de la passe precedente
- [x] Verifier le run utilisateur courant via logs web
- [x] Recroiser avec les logs worker pour confirmer claim, analyse et livraison
- [x] Corriger uniquement la cause racine si un nouvel echec est confirme
- [ ] Revalider localement et reverifier le runtime Render
- [ ] Auditer le rapport final recu apres le run

Review:
- Cause racine confirmee sur le run courant: le worker Render redemarre pendant `job_id=12` a cause de plusieurs OOM consecutifs (>4 GB), avant tout callback `complete` ou `fail`.
- Signal cle de confirmation: logs worker avec `runtime context applied`, `GET /internal/minimax/jobs/12/video`, un unique heartbeat, puis evenements Render `Instance failed ... Ran out of memory (used over 4GB)` suivis de nouveaux bootstraps et reclaims du meme job.
- Correctif code applique: le browser MiniMax ne clone plus un profil Chromium complet quand l auth est deja injectee par cookie ou storage; en mode profile-only, les caches lourds sont exclus du clone.
- Correctif infra versionne: blueprint worker passe de `Pro 4 GB` a `Pro Plus 8 GB`.
