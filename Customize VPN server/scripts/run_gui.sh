#!/usr/bin/env bash
# =========================================================================
# SSL VPN Web Portal Background Runner Script
# Usage:
#   bash scripts/run_gui.sh start [--port 8080]
#   bash scripts/run_gui.sh stop
#   bash scripts/run_gui.sh status
#   bash scripts/run_gui.sh restart
#   bash scripts/run_gui.sh logs
# =========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PID_FILE="$BASE_DIR/gui.pid"
LOG_FILE="$BASE_DIR/gui.log"
DEFAULT_PORT=8080
PORT="${2:-$DEFAULT_PORT}"

cd "$BASE_DIR"

is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid="$(cat "$PID_FILE" 2>/dev/null || echo "")"
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
    fi
    return 1
}

start() {
    if is_running; then
        local pid
        pid="$(cat "$PID_FILE")"
        echo "SSL VPN Web Portal is ALREADY RUNNING (PID $pid) at http://localhost:$PORT"
        return 0
    fi

    echo "==> Starting SSL VPN Web Portal on port $PORT in background..."
    python3 -c "import subprocess; p = subprocess.Popen(['python3', 'vpn_web_gui.py', '--host', '0.0.0.0', '--port', '$PORT'], start_new_session=True, stdin=subprocess.DEVNULL, stdout=open('$LOG_FILE', 'a'), stderr=subprocess.STDOUT); open('$PID_FILE', 'w').write(str(p.pid))"

    # Wait for service to initialize
    sleep 1.5

    if is_running; then
        local new_pid
        new_pid="$(cat "$PID_FILE")"
        echo "==> SSL VPN Web Portal started successfully!"
        echo "    PID: $new_pid"
        echo "    URL: http://localhost:$PORT"
        echo "    Logs: $LOG_FILE"
    else
        echo "!! Failed to start Web Portal. Check logs:"
        cat "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi
}

stop() {
    if ! is_running; then
        echo "SSL VPN Web Portal is not running."
        rm -f "$PID_FILE"
        return 0
    fi

    local pid
    pid="$(cat "$PID_FILE")"
    echo "==> Stopping SSL VPN Web Portal (PID $pid)..."
    kill "$pid" 2>/dev/null || true

    for _ in {1..10}; do
        if ! kill -0 "$pid" 2>/dev/null; then
            break
        fi
        sleep 0.5
    done

    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo "==> Web Portal stopped."
}

status() {
    if is_running; then
        local pid
        pid="$(cat "$PID_FILE")"
        echo "SSL VPN Web Portal: ACTIVE"
        echo "  PID:  $pid"
        echo "  URL:  http://localhost:$PORT"
        echo "  Logs: $LOG_FILE"
    else
        echo "SSL VPN Web Portal: STOPPED"
    fi
}

logs() {
    if [[ -f "$LOG_FILE" ]]; then
        tail -n 50 -f "$LOG_FILE"
    else
        echo "No log file found at $LOG_FILE"
    fi
}

case "${1:-status}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
