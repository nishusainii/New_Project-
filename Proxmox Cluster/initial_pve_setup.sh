#!/bin/bash
# ==============================================================================
# Script Name : initial_pve_setup.sh
# Purpose     : Automated initial post-installation setup for Proxmox VE (Steps 1 to 6)
# Target OS   : Proxmox VE 8.x (Debian Bookworm)
# ==============================================================================

set -euo pipefail

# Text colors for clean UI output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}====================================================${NC}"
echo -e "${CYAN}    PROXMOX VE INITIAL SETUP SCRIPT (STEPS 1 - 6)   ${NC}"
echo -e "${CYAN}====================================================${NC}\n"

# Verify script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[ERROR] This script must be run as root.${NC}"
  exit 1
fi

# Detect Debian Codename (default to bookworm for PVE 8)
CODENAME=$(grep "VERSION_CODENAME" /etc/os-release | cut -d'=' -f2 || echo "bookworm")
if [ -z "$CODENAME" ]; then
    CODENAME="bookworm"
fi

# ------------------------------------------------------------------------------
# STEP 1: Verify Hostname & Web GUI Access URL
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[Step 1/6] Detecting Hostname & Web Management IP...${NC}"
HOST_NAME=$(hostname)
DEFAULT_IP=$(hostname -I | awk '{print $1}')

echo -e "  - Node Hostname : ${GREEN}${HOST_NAME}${NC}"
echo -e "  - Management IP : ${GREEN}${DEFAULT_IP}${NC}"
echo -e "  - Web GUI URL   : ${GREEN}https://${DEFAULT_IP}:8006${NC}"
echo -e "${GREEN}[DONE] Web GUI access detected.${NC}\n"

# ------------------------------------------------------------------------------
# STEP 2: Configure Repositories (Disable Enterprise, Enable No-Subscription)
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[Step 2/6] Configuring APT Repositories...${NC}"

# A. Disable PVE Enterprise Repo
if [ -f /etc/apt/sources.list.d/pve-enterprise.list ]; then
    sed -i 's/^deb /#deb /' /etc/apt/sources.list.d/pve-enterprise.list
    echo -e "  - Disabled pve-enterprise.list"
fi

# B. Disable Ceph Enterprise Repo (if present)
if [ -f /etc/apt/sources.list.d/ceph.list ]; then
    sed -i 's/^deb /#deb /' /etc/apt/sources.list.d/ceph.list
    echo -e "  - Disabled enterprise ceph.list"
fi

# C. Add PVE No-Subscription Repository to /etc/apt/sources.list if not already present
PVE_NO_SUB_ENTRY="deb http://download.proxmox.com/debian/pve ${CODENAME} pve-no-subscription"
if grep -q "pve-no-subscription" /etc/apt/sources.list; then
    echo -e "  - pve-no-subscription repository already configured."
else
    echo -e "\n# Proxmox VE No-Subscription Repository" >> /etc/apt/sources.list
    echo "${PVE_NO_SUB_ENTRY}" >> /etc/apt/sources.list
    echo -e "  - Added ${GREEN}pve-no-subscription${NC} repository."
fi

echo -e "${GREEN}[DONE] Repositories configured successfully.${NC}\n"

# ------------------------------------------------------------------------------
# STEP 3: Update & Upgrade System Packages
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[Step 3/6] Refreshing APT cache and updating packages...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt update
apt dist-upgrade -y

echo -e "${GREEN}[DONE] System package upgrade completed.${NC}\n"

# ------------------------------------------------------------------------------
# STEP 4: Remove "No Valid Subscription" Web GUI Nag
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[Step 4/6] Disabling 'No Subscription' Web GUI popup...${NC}"
PVE_JS_FILE="/usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js"

if [ -f "$PVE_JS_FILE" ]; then
    # Create backup if not already present
    if [ ! -f "${PVE_JS_FILE}.bak" ]; then
        cp "$PVE_JS_FILE" "${PVE_JS_FILE}.bak"
    fi
    sed -Ezi.bak "s/(Ext.Msg.show\(\{\s+title: gettext\('No valid sub)/void\(\{ \/\/\1/g" "$PVE_JS_FILE"
    systemctl restart pveproxy.service
    echo -e "  - Patched proxmoxlib.js and restarted pveproxy."
else
    echo -e "  - [WARN] proxmoxlib.js not found, skipping."
fi

echo -e "${GREEN}[DONE] Subscription nag removed.${NC}\n"

# ------------------------------------------------------------------------------
# STEP 5: Timezone & NTP Time Synchronization
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[Step 5/6] Verifying Timezone & NTP Synchronization...${NC}"
TARGET_TZ="Asia/Kolkata"

# Set timezone
timedatectl set-timezone "$TARGET_TZ"
# Ensure NTP is enabled
timedatectl set-ntp true

echo -e "  - Timezone set to: ${GREEN}${TARGET_TZ}${NC}"
echo -e "  - Current Time   : $(date)"
echo -e "  - NTP Status     :"
timedatectl status | grep -E "Time zone|System clock synchronized|NTP service" | sed 's/^/    /'

echo -e "${GREEN}[DONE] Time and NTP verified.${NC}\n"

# ------------------------------------------------------------------------------
# STEP 6: Network Interfaces & Connectivity Health Check
# ------------------------------------------------------------------------------
echo -e "${YELLOW}[Step 6/6] Checking Network Interfaces & Gateway Connectivity...${NC}"
echo -e "  - Network Interface Status (ip -br a):"
ip -br a | sed 's/^/    /'

echo ""
# Test Gateway connectivity
DEFAULT_GW=$(ip route | grep default | awk '{print $3}' | head -n 1 || echo "")
if [ -n "$DEFAULT_GW" ]; then
    echo -e "  - Testing ping to default gateway (${DEFAULT_GW})..."
    if ping -c 2 -W 2 "$DEFAULT_GW" >/dev/null 2>&1; then
        echo -e "    ${GREEN}[OK] Gateway ping reachable.${NC}"
    else
        echo -e "    ${RED}[WARN] Default gateway ping failed or blocked.${NC}"
    fi
else
    echo -e "    ${YELLOW}[WARN] No default gateway detected.${NC}"
fi

# Test Internet DNS / Connectivity
if ping -c 2 -W 2 1.1.1.1 >/dev/null 2>&1; then
    echo -e "    ${GREEN}[OK] Internet connectivity reachable.${NC}"
else
    echo -e "    ${YELLOW}[WARN] Internet ping not reachable (check DNS/Firewall if offline environment).${NC}"
fi

echo -e "${GREEN}[DONE] Network check completed.${NC}\n"

# ------------------------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------------------------
echo -e "${CYAN}====================================================${NC}"
echo -e "${GREEN}   INITIAL SETUP COMPLETED SUCCESSFULLY!            ${NC}"
echo -e "${CYAN}====================================================${NC}"
echo -e "Web Interface : ${CYAN}https://${DEFAULT_IP}:8006${NC}"
echo -e "Status        : Repositories configured, system upgraded, nag removed, NTP in sync."
echo -e "Next Action   : Ready for Disk Storage / Ceph / Cluster configuration."
