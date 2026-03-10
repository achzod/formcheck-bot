#!/bin/sh
set -eu

MODE="${FORMCHECK_SERVICE_MODE:-web}"

if [ "$MODE" = "worker" ]; then
  exec xvfb-run -a -s "-screen 0 1920x1080x24" python -m app.minimax_remote_worker
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"
