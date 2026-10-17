#!/usr/bin/env bash
# ==============================================================================
# Bare-Metal Setup for Innspark Web Admin Console
# Installs Python virtual environment, dependencies, and systemd service unit.
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}Deploying Web Admin Console to /opt/innspark/web-admin...${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo ./setup-web-admin.sh${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="/opt/innspark/web-admin"

# 1. Create target directory
mkdir -p "$TARGET_DIR"
cp -r "$SCRIPT_DIR/configs/web-admin/"* "$TARGET_DIR/"

# 2. Setup Python Virtual Environment
echo "Setting up Python virtual environment..."
apt-get install -y python3-venv python3-pip
python3 -m venv "$TARGET_DIR/venv"
"$TARGET_DIR/venv/bin/pip" install --upgrade pip
"$TARGET_DIR/venv/bin/pip" install -r "$TARGET_DIR/requirements.txt"

# 3. Install and start systemd service
echo "Configuring systemd service (innspark-web-admin.service)..."
cp "$TARGET_DIR/innspark-web-admin.service" /etc/systemd/system/
systemctl daemon-reload
systemctl restart innspark-web-admin.service
systemctl enable innspark-web-admin.service

echo -e "${GREEN}✔ Web Admin service running on port 8088!${NC}"
