#!/usr/bin/env bash
# ==============================================================================
# CiSai Squid Management Portal - Local Node One-Click Installer
# ==============================================================================
# Run directly on the target Squid proxy server:
#     sudo bash install_local_portal.sh
# ==============================================================================

set -e

PORTAL_DIR="/opt/innspark-squid-portal"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=5000
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-admin@123}"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "================================================================================"
echo "   ______  _  _____         _ "
echo "  / ____/ (_)/ ___/ ____ _ (_)"
echo " / /     / / \__ \ / __ \`// / "
echo "/ /___  / / ___/ // /_/ // /  "
echo "\____/ /_/ /____/ \__,_//_/   "
echo "  SQUID PROXY MANAGEMENT PORTAL - LOCAL NODE INSTALLER"
echo "================================================================================"
echo -e "${NC}"

# 1. Check Root Privileges
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[✘] Error: This script must be run as root (sudo bash install_local_portal.sh)${NC}"
    exit 1
fi

echo -e "\n${CYAN}[1/5] Pre-flight System Verification...${NC}"

# Detect Host IP
HOST_IP=$(hostname -I | awk '{print $1}')
if [ -z "$HOST_IP" ]; then
    HOST_IP="127.0.0.1"
fi
echo -e "  ✓ Detected Host Primary IP: ${GREEN}${HOST_IP}${NC}"

# Check Squid Installation
if command -v squid &> /dev/null; then
    SQUID_VER=$(squid -v | head -n 1)
    echo -e "  ✓ Squid installed: ${GREEN}${SQUID_VER}${NC}"
else
    echo -e "  ${YELLOW}[!] Warning: Squid binary not found in standard PATH.${NC}"
    read -p "      Continue installation anyway? [y/N]: " SQUID_CONT
    if [[ ! "$SQUID_CONT" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Squid Service Status
if systemctl is-active --quiet squid; then
    echo -e "  ✓ Squid Service: ${GREEN}ACTIVE (Undisturbed)${NC}"
else
    echo -e "  ${YELLOW}[!] Squid service is currently inactive or not installed as systemd unit.${NC}"
fi

# 2. Install Dependencies
echo -e "\n${CYAN}[2/5] Installing Portal Dependencies (Python3, Flask, htpasswd)...${NC}"
if command -v apt-get &> /dev/null; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-flask apache2-utils curl tar gzip
elif command -v dnf &> /dev/null; then
    dnf install -y -q python3 python3-pip httpd-tools curl tar gzip
    pip3 install -q flask "werkzeug<3.0.0" || true
elif command -v yum &> /dev/null; then
    yum install -y -q python3 python3-pip httpd-tools curl tar gzip
    pip3 install -q flask "werkzeug<3.0.0" || true
elif command -v zypper &> /dev/null; then
    zypper --non-interactive install python3 python3-pip apache2-utils curl tar gzip
    pip3 install -q flask "werkzeug<3.0.0" || true
else
    echo -e "  ${YELLOW}[!] Unknown package manager. Ensuring python3 and flask are installed via pip...${NC}"
    pip3 install -q flask "werkzeug<3.0.0" || true
fi

# Ensure Flask and Werkzeug are compatible (fixes url_quote error if Werkzeug 3.x is in /usr/local)
if ! python3 -c "import flask" &>/dev/null; then
    echo -e "  ${YELLOW}[!] Resolving Flask / Werkzeug version compatibility...${NC}"
    pip3 install -q "werkzeug<3.0.0" 2>/dev/null || pip3 install --break-system-packages -q "werkzeug<3.0.0" 2>/dev/null || true
fi
echo -e "  ✓ Dependencies verified."

# 3. Create Portal & ACL Directories
echo -e "\n${CYAN}[3/5] Setting Up Directory Structures...${NC}"
mkdir -p "${PORTAL_DIR}"
mkdir -p "${PORTAL_DIR}/data"
mkdir -p /etc/squid/acl/users
mkdir -p /etc/squid/acl/domains
mkdir -p /etc/squid/acl/ips
mkdir -p /etc/squid/squid_backups/portal_backups
mkdir -p /etc/squid/squid_backups/portal_archives

# Copy Portal Codebase
echo -e "  ✓ Copying portal files to ${PORTAL_DIR}..."
cp -r "${SCRIPT_DIR}/app.py" "${PORTAL_DIR}/"
cp -r "${SCRIPT_DIR}/config.py" "${PORTAL_DIR}/"
cp -r "${SCRIPT_DIR}/auth.py" "${PORTAL_DIR}/"
cp -r "${SCRIPT_DIR}/squid_manager.py" "${PORTAL_DIR}/"
cp -r "${SCRIPT_DIR}/innspark-squid-portal.service" "${PORTAL_DIR}/"
cp -r "${SCRIPT_DIR}/requirements.txt" "${PORTAL_DIR}/"
cp -r "${SCRIPT_DIR}/templates" "${PORTAL_DIR}/"
cp -r "${SCRIPT_DIR}/static" "${PORTAL_DIR}/"
if [ -d "${SCRIPT_DIR}/data" ]; then cp -rn "${SCRIPT_DIR}/data" "${PORTAL_DIR}/" 2>/dev/null || true; fi

# 4. Initialize Credentials
echo -e "\n${CYAN}[4/5] Configuring Portal Credentials...${NC}"
CREDS_FILE="${PORTAL_DIR}/data/admin_creds.json"
if [ ! -f "$CREDS_FILE" ]; then
    echo -e "  Initializing default admin user: ${GREEN}${ADMIN_USER}${NC}"
    python3 - <<EOF
import json
from werkzeug.security import generate_password_hash
creds = {
    "username": "${ADMIN_USER}",
    "password_hash": generate_password_hash("${ADMIN_PASS}", method="pbkdf2:sha256")
}
with open("${CREDS_FILE}", "w") as f:
    json.dump(creds, f, indent=2)
EOF
    echo -e "  ✓ Admin credentials created (User: ${ADMIN_USER})"
else
    echo -e "  ✓ Existing credentials retained in ${CREDS_FILE}"
fi

# Set Permissions
chown -R root:root "${PORTAL_DIR}"
chmod -R 750 "${PORTAL_DIR}"

# 5. Systemd Service Registration
echo -e "\n${CYAN}[5/5] Registering Systemd Service & Starting Portal...${NC}"
cp "${PORTAL_DIR}/innspark-squid-portal.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable innspark-squid-portal.service
systemctl restart innspark-squid-portal.service
echo -e "  ✓ Service 'innspark-squid-portal.service' registered and started."

# Verification
sleep 2
echo -e "\n${CYAN}[✔] Verifying Portal Health & Endpoint...${NC}"
SVC_STATUS=$(systemctl is-active innspark-squid-portal.service || true)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:${PORT}/login || echo "FAIL")

echo "================================================================================"
if [ "$SVC_STATUS" = "active" ] && [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN} [SUCCESS] CiSai Squid Management Portal is LIVE!${NC}"
    echo -e " Portal URL    : ${CYAN}http://${HOST_IP}:${PORT}${NC}"
    echo -e " Username      : ${GREEN}${ADMIN_USER}${NC}"
    echo -e " Password      : ${GREEN}${ADMIN_PASS}${NC}"
    echo -e " Service Name  : innspark-squid-portal.service"
    echo "================================================================================"
    echo -e "\nManagement Commands:"
    echo -e "  • Check Status : sudo systemctl status innspark-squid-portal"
    echo -e "  • Restart      : sudo systemctl restart innspark-squid-portal"
    echo -e "  • View Logs    : sudo journalctl -u innspark-squid-portal -f\n"
else
    echo -e "${RED} [!] Notice: Service status is '${SVC_STATUS}' and HTTP check returned '${HTTP_CODE}'.${NC}"
    echo -e " Check journal logs: sudo journalctl -u innspark-squid-portal -n 50 --no-pager"
    echo "================================================================================"
fi
