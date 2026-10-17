#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# WireGuard Enterprise - Air-Gapped Production Deployment Script
# Designed for production Linux hosts with ZERO internet access.
# ==============================================================================

# ANSI Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo -e "${BLUE}====================================================================${NC}"
echo -e "${CYAN}   WireGuard Enterprise - Air-Gapped Production Installer           ${NC}"
echo -e "${BLUE}====================================================================${NC}"
echo -e "Target Directory: ${ROOT_DIR}\n"

# Step 1: Root Privilege Check
echo -e "${YELLOW}[1/6] Checking administrative privileges...${NC}"
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] Please execute this script as root or using sudo.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Running with root privileges.${NC}"

# Step 2: Kernel and System Prerequisites
echo -e "\n${YELLOW}[2/6] Verifying Linux Kernel & Networking Settings...${NC}"

# 2a. Check/Load WireGuard Kernel Module
if lsmod | grep -qw wireguard; then
    echo -e "${GREEN}[OK] WireGuard kernel module (wireguard.ko) is currently loaded.${NC}"
else
    echo -e "Attempting to load WireGuard kernel module..."
    if modprobe wireguard 2>/dev/null; then
        echo -e "${GREEN}[OK] WireGuard kernel module loaded successfully.${NC}"
    else
        echo -e "${YELLOW}[WARN] 'modprobe wireguard' did not succeed. If using Linux kernel >= 5.6, it will auto-load when interface is created.${NC}"
    fi
fi

# 2b. Enable IPv4 Forwarding
IP_FWD=$(sysctl -n net.ipv4.ip_forward 2>/dev/null || echo 0)
if [ "$IP_FWD" -eq 1 ]; then
    echo -e "${GREEN}[OK] IPv4 forwarding is active (sysctl net.ipv4.ip_forward = 1).${NC}"
else
    echo -e "Enabling IPv4 forwarding in kernel runtime..."
    sysctl -w net.ipv4.ip_forward=1
    # Persist in sysctl.d
    echo "net.ipv4.ip_forward = 1" > /etc/sysctl.d/99-wireguard-forward.conf
    echo -e "${GREEN}[OK] IPv4 forwarding enabled and persisted to /etc/sysctl.d/99-wireguard-forward.conf.${NC}"
fi

# Step 3: Docker & Compose Engine Check
echo -e "\n${YELLOW}[3/6] Verifying Docker runtime...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}[ERROR] 'docker' command not found! In air-gapped mode, Docker must be pre-installed via offline RPM/DEB packages.${NC}"
    exit 1
fi

COMPOSE_CMD=""
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}[ERROR] Neither 'docker compose' nor 'docker-compose' was found.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Docker engine detected ($(${COMPOSE_CMD} version)).${NC}"

# Step 4: Import Offline Docker Image
echo -e "\n${YELLOW}[4/6] Loading pre-packaged Docker image...${NC}"
TAR_IMAGE="${ROOT_DIR}/wireguard-enterprise-image.tar.gz"
UNCOMPRESSED_TAR="${ROOT_DIR}/wireguard-enterprise-image.tar"

if [ -f "${TAR_IMAGE}" ]; then
    echo -e "Found compressed image archive: ${TAR_IMAGE}"
    echo -e "Loading image into Docker daemon..."
    docker load < "${TAR_IMAGE}"
    echo -e "${GREEN}[OK] Offline Docker image loaded successfully.${NC}"
elif [ -f "${UNCOMPRESSED_TAR}" ]; then
    echo -e "Found uncompressed image archive: ${UNCOMPRESSED_TAR}"
    docker load -i "${UNCOMPRESSED_TAR}"
    echo -e "${GREEN}[OK] Offline Docker image loaded successfully.${NC}"
else
    # Check if image already exists locally
    if docker image inspect wireguard-enterprise:latest &> /dev/null; then
        echo -e "${GREEN}[OK] Image 'wireguard-enterprise:latest' is already present in Docker cache.${NC}"
    else
        echo -e "${RED}[ERROR] Offline image archive not found!${NC}"
        echo -e "Expected ${TAR_IMAGE} or local 'wireguard-enterprise:latest' image."
        exit 1
    fi
fi

# Step 5: Environment & Data Store Initialization
echo -e "\n${YELLOW}[5/6] Initializing local environment and storage...${NC}"

# 5a. Create .env if missing
if [ ! -f "${ROOT_DIR}/.env" ]; then
    if [ -f "${ROOT_DIR}/.env.example" ]; then
        echo -e "Copying default configuration from .env.example to .env..."
        cp "${ROOT_DIR}/.env.example" "${ROOT_DIR}/.env"
        # Generate random SECRET_KEY
        NEW_SECRET=$(head -c 32 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 32 || openssl rand -hex 16)
        sed -i "s/SECRET_KEY=change-this-in-production/SECRET_KEY=${NEW_SECRET}/g" "${ROOT_DIR}/.env"
    fi
fi

# 5b. Ensure secure data directory exists
mkdir -p "${ROOT_DIR}/data"
chmod 700 "${ROOT_DIR}/data"

# 5c. Ensure host NFTables configuration (/etc/nftables.conf) exists
NFT_CONF="/etc/nftables.conf"
if [ ! -f "${NFT_CONF}" ]; then
    echo -e "Initializing baseline ${NFT_CONF}..."
    cat << 'CONFEOF' > "${NFT_CONF}"
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input { type filter hook input priority 0; policy accept; }
    chain forward { type filter hook forward priority 0; policy accept; }
    chain output { type filter hook output priority 0; policy accept; }
}

table inet wiregate {
    chain input {
        type filter hook input priority filter; policy accept;
        ct state established,related accept comment "Allow established traffic"
        iif "lo" accept comment "Allow loopback"
        udp dport 443 accept comment "WireGuard Inbound Tunnel"
    }

    chain forward {
        type filter hook forward priority filter; policy accept;
        ct state established,related accept comment "Allow established forwarding"
        iifname "wg0" oifname != "wg0" accept comment "WireGuard Outbound Internet"
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        ip saddr 172.29.250.0/24 oifname != "wg0" masquerade comment "WireGuard NAT Masquerade"
    }
}
CONFEOF
    chmod 0755 "${NFT_CONF}"
else
    # Remove any legacy includes from /etc/nftables.conf
    sed -i '/include "\/etc\/nftables\/acl.nft"/d' "${NFT_CONF}" 2>/dev/null || true
    sed -i '/include "\/etc\/nftables.acl.nft"/d' "${NFT_CONF}" 2>/dev/null || true

    # Ensure table inet wiregate exists
    if ! grep -q "table inet wiregate" "${NFT_CONF}"; then
        echo -e "Adding WireGuard table to ${NFT_CONF}..."
        cat << 'WGEOF' >> "${NFT_CONF}"

table inet wiregate {
    chain input {
        type filter hook input priority filter; policy accept;
        ct state established,related accept comment "Allow established traffic"
        iif "lo" accept comment "Allow loopback"
        udp dport 443 accept comment "WireGuard Inbound Tunnel"
    }

    chain forward {
        type filter hook forward priority filter; policy accept;
        ct state established,related accept comment "Allow established forwarding"
        iifname "wg0" oifname != "wg0" accept comment "WireGuard Outbound Internet"
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        ip saddr 172.29.250.0/24 oifname != "wg0" masquerade comment "WireGuard NAT Masquerade"
    }
}
WGEOF
    fi
fi

echo -e "${GREEN}[OK] Environment and storage initialized securely.${NC}"

# Step 6: Launch Control Center
echo -e "\n${YELLOW}[6/6] Starting WireGuard Enterprise services...${NC}"
cd "${ROOT_DIR}"
${COMPOSE_CMD} down 2>/dev/null || true
${COMPOSE_CMD} up -d

echo -e "\nWaiting for service startup..."
sleep 4

# Health Check Probe
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/login || echo "000")

if [ "${HTTP_STATUS}" = "200" ] || [ "${HTTP_STATUS}" = "302" ]; then
    echo -e "${GREEN}====================================================================${NC}"
    echo -e "${GREEN}   DEPLOYMENT SUCCESSFUL - SERVICE OPERATIONAL (HTTP ${HTTP_STATUS})             ${NC}"
    echo -e "${GREEN}====================================================================${NC}"
    echo -e "Access URL:      http://<SERVER_IP>:8000"
    echo -e "Admin Username:  admin"
    echo -e "Admin Password:  adminpassword123 (or value configured in .env)"
    echo -e "\nManagement Commands:"
    echo -e "  View Logs:      ${COMPOSE_CMD} logs -f"
    echo -e "  Stop Service:   ${COMPOSE_CMD} down"
    echo -e "  Restart:        ${COMPOSE_CMD} restart"
    echo -e "====================================================================\n"
else
    echo -e "${YELLOW}[WARN] Service started, but HTTP probe returned status: ${HTTP_STATUS}.${NC}"
    echo -e "Inspect container logs with: ${COMPOSE_CMD} logs"
fi
