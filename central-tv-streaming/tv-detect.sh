#!/usr/bin/env bash

# Central TV Network Detector & Automatic Launcher
# Discovers Smart TVs on LAN or Wi-Fi, triggers on-screen prompt if new,
# and automatically displays the central video streaming player.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed or not in PATH."
    exit 1
fi

node "$SCRIPT_DIR/scripts/tv-network-detector.js" "$@"
