#!/bin/bash
LOG_STDOUT="claude_stdout.log"
LOG_STDERR="claude_debug.log"
TRIPS_LOG="watchdog_trips.log"

log_trip() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$TRIPS_LOG"
}

PROMPT="$1"

if [ -z "$PROMPT" ]; then
    echo "Usage: $0 <prompt>"
    exit 1
fi

log_trip "Starting watchdog with prompt: $PROMPT"

while true; do
    log_trip "Starting Claude process as 'openclaw' user..."
    
    # script -q -c tricks Claude into thinking it has a terminal for real-time output
    # sudo -u openclaw runs it as a non-root user to disable root paranoia
    # --dangerously-skip-permissions is now allowed because we aren't root
    script -q -c "sudo -u openclaw -i bash -c \"cd $PWD && claude -p '$PROMPT' --dangerously-skip-permissions --output-format stream-json --verbose\"" /dev/null >> "$LOG_STDOUT" 2>> "$LOG_STDERR"
    
    EXIT_CODE=$?
    log_trip "Claude exited with code $EXIT_CODE"
    
    if [ $EXIT_CODE -eq 0 ]; then
        log_trip "Task completed successfully. Watchdog exiting."
        exit 0
    fi
    
    log_trip "Process crashed with code $EXIT_CODE. Restarting in 10 seconds..."
    sleep 10
done
