# Todo

## Current Task
- [x] Audit the MiniMax flow end-to-end: intake, prep, upload, browser run, parse, validation, delivery.
- [x] Verify browser-only execution remains enforced in code paths that matter.
- [x] Remove or harden any behavior that can crash, invent content, or silently degrade MiniMax analysis.
- [x] Add regression tests for critical MiniMax failure modes.
- [x] Run targeted tests and full suite.
- [x] Push production-ready fixes.

## Review
- Root causes fixed:
  - parser still accepted fallback/unstructured MiniMax outputs and could validate them as final
  - browser DOM fallback could still grab unstructured page text instead of a true final report
  - cached runs could reuse older, weaker parser-contract results
  - browser auth validation was stricter than necessary for persisted OAuth/browser sessions
- Fixes applied:
  - MiniMax parser now marks `parse_mode` and rejects `fallback` outputs as final in [analysis/minimax_motion_coach.py](/Users/achzod/clawd/src/analysis/minimax_motion_coach.py)
  - browser page-report fallback no longer accepts unstructured text; it waits for structured final output
  - candidate filter no longer accepts bare metric summaries as analysis
  - cache contract bumped to `v12_minimax_strict_final_output`
  - config validation now accepts persisted browser auth seeds without forcing email/password when not needed
- Verification:
  - `pytest -q tests/test_minimax_motion_coach.py` -> `90 passed`
  - `pytest -q tests/test_html_report_personalized.py tests/test_remote_minimax_worker_flow.py tests/test_minimax_motion_coach.py` -> `109 passed`
  - `pytest -q` -> `146 passed, 2 skipped`
