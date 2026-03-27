#!/bin/bash
# FormCheck Worker Watchdog
# Keeps simple_worker.py alive. Run with: nohup bash watchdog.sh &
# Logs to /tmp/watchdog.log

WORKER_DIR="/Users/achzod/clawd/src"
WORKER_CMD="python3 tmp/simple_worker.py"
LOG="/tmp/simple_worker.log"
WATCHDOG_LOG="/tmp/watchdog.log"

echo "[$(date)] Watchdog started" >> "$WATCHDOG_LOG"

while true; do
    # Check if worker is running
    if ! pgrep -f "simple_worker.py" > /dev/null 2>&1; then
        echo "[$(date)] Worker DOWN — restarting..." >> "$WATCHDOG_LOG"
        cd "$WORKER_DIR"
        $WORKER_CMD >> "$LOG" 2>&1 &
        echo "[$(date)] Worker restarted (PID: $!)" >> "$WATCHDOG_LOG"
    fi
    sleep 30
done
