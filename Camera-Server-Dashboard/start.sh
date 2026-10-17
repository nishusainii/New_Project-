#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

echo "=========================================================="
echo " Starting INNCCTV 24-Camera Surveillance Operations Center"
echo "=========================================================="

# Check if node dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Ensure bin/mediamtx is executable
if [ -f "bin/mediamtx" ]; then
    chmod +x bin/mediamtx
fi

# Start the node server (which automatically manages MediaMTX)
node server/index.js
