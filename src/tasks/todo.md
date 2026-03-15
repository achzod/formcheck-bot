# Todo

## Current Task
- [x] Audit the MiniMax integration path end-to-end.
- [x] Verify that MiniMax remains the analytical source of truth.
- [x] Remove local semantic overrides from the MiniMax result mapping path.
- [x] Block local post-analysis augmentation when `minimax_strict_source=true`.
- [x] Prove the behavior with targeted regression tests.
- [x] Run the full test suite.
- [x] Push the fix to `main`.

## Review
- Root cause: the code still allowed two non-source-first behaviors after MiniMax returned:
  - local semantic reinterpretation of the exercise label
  - optional local metric augmentation after MiniMax analysis
- Fix applied in [analysis/pipeline.py](/Users/achzod/clawd/src/analysis/pipeline.py):
  - MiniMax mapping is now conservative and source-first
  - report text no longer overrides MiniMax exercise semantics
  - strict-source mode now skips local augmentation even if that flag is enabled
- Regression coverage added in [tests/test_minimax_motion_coach.py](/Users/achzod/clawd/src/tests/test_minimax_motion_coach.py)
- Verification:
  - targeted tests passed
  - full suite passed: `142 passed, 2 skipped`
  - commit pushed: `e8fec25`

