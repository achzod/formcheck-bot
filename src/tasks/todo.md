# Todo

## Current Task
- [x] Investigate why production reports `remote_worker_enabled=false`.
- [x] Audit config loading and runtime feature gating around MiniMax remote worker mode.
- [x] Implement a robust fix if the mismatch can be solved in code.
- [x] Add regression coverage.
- [x] Re-run tests, push, and re-check production endpoints.

## Review
- Root cause: the likely issue is config drift between Render blueprint intent and the runtime boolean env on the web service.
- Fix applied:
  - added `minimax_remote_worker_effective_enabled()` in [app/config.py](/Users/achzod/clawd/src/app/config.py)
  - web service now treats remote worker mode as effectively enabled when the deployment is clearly in strict browser-only MiniMax mode and already has an internal worker token configured
  - handlers and internal worker endpoints now use the effective flag instead of the raw boolean only
  - `/health/debug`, queue stats and debug settings now expose both raw and effective remote worker state
- Validation:
  - `pytest -q tests/test_runtime_config.py tests/test_remote_minimax_worker_flow.py tests/test_minimax_motion_coach.py` -> `105 passed`
  - `pytest -q` -> `151 passed, 2 skipped`
