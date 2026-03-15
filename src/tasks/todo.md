# Todo

- [x] Reconstituer le symptome prod MiniMax (logs/runtime/endpoints)
- [x] Auditer la queue job -> worker -> MiniMax browser -> livraison WhatsApp
- [x] Identifier la cause racine du dernier echec
- [x] Corriger le code ou la configuration minimale necessaire
- [x] Verifier par tests + checks prod + audit final

## Review
- Cause racine prouvee en prod:
  - la video WhatsApp est bien recue
  - le job `minimax_remote_jobs` est bien cree
  - le worker Render echoue avant analyse MiniMax
  - erreur exacte en base prod: Playwright headed sans X server (`DISPLAY` absent)
  - shell worker prod: PID 1 = `python -m app.minimax_remote_worker`, pas `xvfb-run`
- Correctif applique:
  - ajout d une auto-recuperation dans [app/minimax_remote_worker.py](/Users/achzod/clawd/src/app/minimax_remote_worker.py)
  - si mode headed et `DISPLAY` absent, le worker se re-exec lui-meme sous `xvfb-run`
  - cela couvre les derives Render ou un start command qui bypass le Docker CMD
- Validation:
  - `pytest -q tests/test_remote_minimax_worker_flow.py tests/test_runtime_config.py tests/test_minimax_motion_coach.py` -> `108 passed`
  - `pytest -q` -> `154 passed, 2 skipped`
  - `python3 -m py_compile app/minimax_remote_worker.py tests/test_remote_minimax_worker_flow.py` -> OK
