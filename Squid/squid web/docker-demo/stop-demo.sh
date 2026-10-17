#!/usr/bin/env bash
# ==============================================================================
# Innspark Solutions - Stop Docker Demo Environment
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping Innspark Demo containers..."
docker compose down
echo "Demo environment stopped."
