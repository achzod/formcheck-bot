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

- [x] Confirm worker redeploy on `ce42e32` and plan bump to Pro Plus.
- [ ] Observe a full `job 12` completion or explicit fail callback after redeploy; current state is steady processing with heartbeats and no OOM.

- [x] Identify user-visible 'analyse indispo' root cause from live logs: hard timeout at 480s, not a fresh OOM.
- [x] Raise shared MiniMax effective timeout defaults to 900s and worker hard cap/grace to 1200s/120s.
- [x] Validate locally with targeted tests and py_compile.
- [ ] Push and verify Render redeploy on worker/web.

## 2026-03-19 MiniMax browser latency audit

- [x] Inspect the MiniMax browser send/upload/extract flow and identify the exact over-wait path
- [x] Return the first substantive MiniMax response instead of waiting for over-strict completion markers
- [x] Validate with focused tests and compile checks
- [ ] Push the fix and prepare prod verification on the next live WhatsApp run

Review:
- Root cause 1 confirmed: browser flow waited for `chat_status != 1` or repeated stable rounds even when MiniMax had already produced a valid final report.
- Root cause 2 confirmed: if MiniMax emitted `get_chat_detail` during `_upload_and_send_via_browser`, the run still had `sent=False`, so that first valid answer was misclassified as baseline traffic and discarded.
- Fix applied: browser flow now validates each candidate immediately and exits on the first valid final MiniMax output, with metadata showing the winning source.
- Latency fix applied: active sent-chat refresh now triggers sooner and skips unnecessary `networkidle` waiting on refresh navigations.
- Validation completed: targeted browser regression tests passed, `python3 -m py_compile` passed, and worker/runtime suites remain green (`40 passed`).

## 2026-03-19 MiniMax auth-seed mismatch triage

- [x] Verify the live job state directly in `/app/state/formcheck.db`
- [x] Confirm whether the latest failures are infra crashes or browser-side hard timeouts
- [x] Inspect worker runtime env and compare configured MiniMax email vs injected browser seed identity
- [x] Add a code guardrail to reject mismatched explicit browser auth seeds
- [x] Shorten the default MiniMax prompt to reduce avoidable task overhead
- [ ] Update the worker MiniMax auth seed on Render so it matches `achzodyt@gmail.com`
- [ ] Run a fresh end-to-end WhatsApp test after the Render env fix

Review:
- The latest failed jobs are `12`, `13`, and `14`; all ended with hard timeout and empty `result_payload`.
- Web service is healthy; delivery is not the current bottleneck.
- Worker env mismatch confirmed in prod: `MINIMAX_BROWSER_EMAIL=achzodyt@gmail.com` while the injected `MINIMAX_BROWSER_LOCAL_STORAGE_JSON` still identifies `coaching@achzodcoaching.com`.
- This mismatch is now guarded in code so an explicit stale auth seed is no longer silently accepted as valid browser auth.
- Prompt size was reduced, but the main remaining prod action is operational: replace the Render worker auth seed with a coherent `achzodyt@gmail.com` MiniMax browser seed and retest.

## 2026-03-20 Direct AI Motion Coach smoke

- [x] Verify that the local browser automation can open the exact AI Motion Coach expert chat
- [x] Verify whether the composer is genuinely ready on that page
- [x] Verify whether attaching a real mp4 stays authenticated or triggers a login wall
- [x] Record the exact failure point for the next fix pass

Review:
- The exact expert page `https://agent.minimax.io/expert/chat/362683345551702` opens successfully under the referenced local Chrome profile.
- Initial page state is healthy: composer ready, no anti bot challenge, no login modal.
- The failure appears only when a real file is attached.
- Upload only smoke on `tmp/minimax_prepared/twilio_fail_latest_minimax_639fc778.mp4` showed:
  - file input present
  - file selection returns immediately
  - a `Welcome to MiniMax / Continue with Google` modal appears after attachment
  - the attached filename does not bind into the visible chat state
- Therefore the blocking issue is not expert discovery or initial page access. The blocking issue is attach/send auth escalation inside AI Motion Coach.

## 2026-03-20 Attach/send auth fix

- [in_progress] Locate the currently valid MiniMax auth state in the real local Chrome profile
- [pending] Extract the minimum durable auth material needed for attach/send
- [pending] Rebuild the local MiniMax worker seed from that auth state
- [pending] Re-run direct browser smoke on expert open + attach + send
- [pending] If green locally, document the exact Render env/session update required for prod

## 2026-03-20 MiniMax auth fallback hardening

- [x] Finalize storage seed fallback logic in `analysis/minimax_motion_coach.py`
- [x] Ensure explicit mismatched storage seeds fall back to profile-derived storage instead of silently failing
- [x] Keep profile clone enabled when auth still depends on seeded browser profile state
- [x] Add targeted tests for profile fallback and injection behavior
- [x] Re-run targeted browser auth/config suites
- [ ] Re-prove a full direct attach/send smoke without manually forcing storage JSON

Review:
- Code fix completed: browser auth availability and storage injection now share the same effective source resolver (`explicit -> profile -> none`).
- Safety fix completed: broken symlinks inside the seed profile are skipped during workspace clone.
- Test coverage added for profile fallback when explicit seed mismatches and when explicit storage is absent.
- Validation completed:
  - `python3 -m py_compile analysis/minimax_motion_coach.py tests/test_minimax_motion_coach.py`
  - `pytest -q tests/test_minimax_motion_coach.py -k 'validate_settings or inject_browser_storage or effective_browser_storage_dumps'` -> `9 passed`
  - `pytest -q tests/test_minimax_motion_coach.py -k 'MiniMaxBrowserAuthFlowTests or MiniMaxBrowserConfigValidationTests'` -> `34 passed`
- Remaining gap: on the real local MiniMax seed profile, automatic extraction from on-disk profile files still recovered only `tab_device_id`, not the full `_token` + `user_detail_agent` pair. So the direct no-manual-JSON smoke is not yet proven.
- What is proven separately: a coherent explicit storage dump for `achzodyt@gmail.com` removes the login modal on attach and lets the filename bind correctly. The remaining production action is still to supply the worker with a coherent explicit MiniMax storage seed for the correct account.
