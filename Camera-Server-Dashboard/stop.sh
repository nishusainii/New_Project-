#!/usr/bin/env bash
# ==========================================================
# Stop Script for INNCCTV Surveillance Operations Center
# ==========================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=========================================================="
echo " Stopping INNCCTV 24-Camera Surveillance Operations Center"
echo "=========================================================="

# 1. Stop Node Server
if pgrep -f "node server/index.js" >/dev/null 2>&1; then
    echo "[+] Stopping Node.js Dashboard Server..."
    pkill -TERM -f "node server/index.js" || true
    sleep 1
    # Force kill if still lingering
    if pgrep -f "node server/index.js" >/dev/null 2>&1; then
        pkill -KILL -f "node server/index.js" || true
    fi
    echo "[✔] Node.js server stopped."
else
    echo "[-] Node.js server was not running."
fi

# 2. Stop MediaMTX Streaming Gateway
if pgrep -f "mediamtx" >/dev/null 2>&1; then
    echo "[+] Stopping MediaMTX Streaming Gateway..."
    pkill -TERM -f "mediamtx" || true
    sleep 1
    # Force kill if still lingering
    if pgrep -f "mediamtx" >/dev/null 2>&1; then
        pkill -KILL -f "mediamtx" || true
    fi
    echo "[✔] MediaMTX gateway stopped."
else
    echo "[-] MediaMTX gateway was not running."
fi

# 3. Verify ports are released
echo "[+] Checking port statuses (3000, 8554, 8888, 8889, 9997)..."
if command -v ss >/dev/null 2>&1; then
    active_ports=$(ss -tuln | grep -E ':(3000|8554|8888|8889|9997)' || true)
    if [ -z "$active_ports" ]; then
        echo "[✔] All surveillance ports are clean and released."
    else
        echo "[!] Warning: The following ports are still bound:"
        echo "$active_ports"
    fi
fi

echo "=========================================================="
echo " INNCCTV Services Successfully Stopped."
echo "=========================================================="
