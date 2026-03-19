# Lessons

## 2026-03-15

- When the user says "MiniMax does the analysis, local code only formats it", treat that as a hard architectural contract.
- Do not rely on environment flags alone for source-first behavior. Enforce the contract in code and protect it with tests.
- Do not add local semantic overrides on top of a third-party analysis engine unless the user explicitly asks for that layer.
- For non-trivial tasks, write the execution plan to `tasks/todo.md` before implementation and finish with a review section.
- After a user correction about process or quality expectations, capture the pattern immediately in `tasks/lessons.md`.
- When the user says MiniMax must receive and analyze videos perfectly, audit the entire transport chain (download, video prep, browser upload, response validation, delivery), not only the report renderer.
- Do not trust blueprint intent alone for operational readiness. Verify runtime flags from the running service and close config mismatches in code when feasible.
- On Render workers, do not assume Docker CMD/entrypoint is the actual PID 1. Verify `/proc/1/cmdline` in prod when browser/Xvfb behavior matters.
- When prod uses a shared internal worker token, do not trust any claimant by token alone. Gate MiniMax job claims by an allowed Render worker identity pattern, otherwise stale local workers can steal prod jobs.
- Treat sentinel env values like `auto` as part of runtime contract, not as literal identities. When a worker id env is meant to say "derive automatically", normalize it before security checks rely on it.
- If the web and worker both support `MINIMAX_REMOTE_WORKER_TOKEN` and `RENDER_API_KEY`, the web must accept any configured valid internal token, not only the first one. Otherwise a Render env drift can freeze the queue with `Invalid internal token` even when both services are healthy.
- On Render, do not rely on `xvfb-run` re-exec as the only headed-browser strategy for long-lived workers. A wrapper can stay alive while the real Python consumer is gone, leaving the service marked live but the queue frozen. Prefer starting `Xvfb` directly from the Python worker process so process lifetime and queue consumption stay coupled.
- Any media required by a background worker after the webhook request returns must live on persistent storage, not under a relative app path. On Render web+worker, store queued job media under `/app/state/...` (or a configurable persistent root) so redeploys do not cause `404 Video not found` on internal worker fetches.
- Do not launch MiniMax Playwright runs directly on a shared persistent Chromium profile. Use the persistent profile only as a seed, clone it into a per-run temporary workspace, scrub `Singleton*` locks, and launch Chromium on that isolated workspace to avoid `profile appears to be in use` failures across deploys or stale browser exits.
- If the worker already receives MiniMax auth through cookies and storage payloads, do not also clone the full Chromium profile by default. That doubles browser state, drags caches into each run, and can push Render workers into OOM for no auth gain.
- When a Render worker handling browser automation restarts mid-job, always cross-check Events, not only Logs. Repeated `bootstrap` lines plus `Instance failed: Ran out of memory` is the decisive signal that the upstream provider is not the primary failure.
- When a user says a run is still blocked, verify whether a new inbound video actually created a job, whether that job was claimed, and whether it failed later. Do not conflate queue starvation with downstream MiniMax timeout once claims are healthy.
- On third-party browser automations, re-check post-send UI states continuously. A promo/modal that appears after the task starts can block result extraction even if pre-send checks were clean.
- On third-party browser automations for long uploads, fixed waits are not enough. Scale attachment/send waits with file size and actively reopen the exact destination chat when the UI stops emitting signals, otherwise healthy jobs degrade into false global timeouts.
- Before changing the analysis pipeline again, prove that a fresh user attempt actually reached the upstream provider and created a new job. If Twilio and the app show no new inbound after the reported test, the failure is upstream of Formcheck and a pipeline fix would be cargo cult.
- Quand un outil tiers expose une page expert specialisee, ne jamais supposer qu un `chat_id` generique renvoie au meme flux. Rester sur la surface expert validee tant qu une preuve contraire n existe pas, sinon on cree nous-memes des timeouts artificiels.
- Promo overlays from third-party UIs that reappear via client-side rendering must be handled with a persistent DOM killer (observer + CSS), not only a one-shot close/remove attempt.

- When a third-party browser automation can hang inside Playwright/Chromium, do not run it inline in the long-lived worker process. Isolate each job in a killable subprocess with a hard timeout so one frozen run cannot block the whole queue.
- When a browser watchdog reasons about live descendants, do not count Playwright driver or Chrome crashpad helper as a live browser. Only a real Chromium process should keep the run alive.
- If a background worker can crash under load, add explicit job heartbeats before tightening stale reclaim. Faster reclaim without heartbeats risks duplicate long analyses; heartbeats let you shorten recovery time safely.
- When a blueprint-managed Render service needs an urgent infra fix, apply the dashboard change immediately if authorized, then push the same change into render.yaml so prod and repo do not drift.
- On Render worker services, never keep `xvfb-run` as PID 1 in the entrypoint. If the Python child dies, `xvfb-run` and `Xvfb` can remain alive, the service looks healthy, but the queue is dead. PID 1 must be the Python worker, and Xvfb must be managed inside the worker.
- For MiniMax browser automation in production, never allow extremely long effective timeouts without a worker-level hard cap. A single hung run can monopolize the queue even when heartbeats are healthy; enforce both a bounded effective timeout and a subprocess wall-clock cap.
- MiniMax remote failures can look like generic 'analyse indispo' even when infra is healthy; always check for worker-side hard timeout before chasing Render OOM again.

- In browser-driven MiniMax flows, mark the send phase as active before the upload/send helper returns; otherwise early `get_chat_detail` responses can be misclassified as baseline traffic and the first valid analysis is lost.
- Do not wait for chat status transitions or repeated stable rounds once MiniMax has already emitted a parseable final report. Exit on the first valid final output and keep UI refreshes lightweight.
- When a third-party browser session is seeded through localStorage/sessionStorage, verify that the seeded identity matches the configured account before treating it as valid auth. A stale seed from another account can silently keep the browser alive while every job times out.
- If prod jobs time out with zero `result_payload`, inspect the job table directly before touching Twilio or report rendering. That pattern means the failure is upstream of delivery and often inside browser auth/session state.
