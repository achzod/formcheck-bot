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
