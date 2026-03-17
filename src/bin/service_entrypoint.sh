#!/bin/sh
set -eu

MODE="${FORMCHECK_SERVICE_MODE:-web}"

if [ "$MODE" = "worker" ]; then
  # Let the Python worker own PID 1. It self-manages Xvfb when DISPLAY is missing.
  exec python -m app.minimax_remote_worker
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"
