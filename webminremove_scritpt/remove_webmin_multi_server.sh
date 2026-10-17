#!/usr/bin/env bash
# ==============================================================================
# Script Name : remove_webmin_multi_server.sh
# Description : Launcher for multi-server Webmin removal (no local sudo needed).
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="${SCRIPT_DIR}/remove_webmin_multi_server.py"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 is required to run this script."
    exit 1
fi

exec python3 "$PYTHON_SCRIPT" "$@"
