#!/usr/bin/env bash
# ==============================================================================
# WireGuard Enterprise - Host Preparation & Kernel Setup Script
# Target: Ubuntu 22.04+ / Debian 11+ / RHEL 9+
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  WireGuard Enterprise - Host Initialization Script   ${NC}"
echo -e "${BLUE}======================================================${NC}"

# Check for root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root (use sudo).${NC}"
   exit 1
fi

echo -e "${GREEN}[1/6] Installing Essential Host Dependencies...${NC}"
apt-get update -y
apt-get install -y wireguard wireguard-tools nftables iptables-persistent docker.io docker-compose curl git jq ca-certificates

echo -e "${GREEN}[2/6] Enabling Kernel IP Forwarding & PMTU Clamping...${NC}"
cat << 'EOF' > /etc/sysctl.d/99-wireguard-enterprise.conf
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.conf.all.proxy_arp = 0
net.ipv4.tcp_syncookies = 1
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.conf.all.rp_filter = 2
net.ipv4.conf.default.rp_filter = 2
EOF

sysctl --system > /dev/null
echo -e "${GREEN}✓ Kernel sysctl configured: net.ipv4.ip_forward = 1${NC}"

echo -e "${GREEN}[3/6] Loading Kernel Modules...${NC}"
modprobe wireguard || true
echo "wireguard" >> /etc/modules-load.d/wireguard.conf || true

echo -e "${GREEN}[4/6] Creating Secure Directory Structure...${NC}"
mkdir -p /etc/wireguard /etc/wireguard/archive
mkdir -p /etc/nftables
mkdir -p /opt/wireguard-enterprise/app
mkdir -p /opt/wireguard-enterprise/data

chmod 700 /etc/wireguard
chmod 755 /etc/nftables
chmod 750 /opt/wireguard-enterprise

echo -e "${GREEN}[5/6] Initializing Host Firewall (NFTables)...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f /etc/nftables/acl.nft ]]; then
    if [[ -f "${SCRIPT_DIR}/acl.nft.template" ]]; then
        cp "${SCRIPT_DIR}/acl.nft.template" /etc/nftables/acl.nft
    else
        touch /etc/nftables/acl.nft
    fi
    chmod 644 /etc/nftables/acl.nft
fi

if [[ -f "${SCRIPT_DIR}/nftables.conf.template" ]]; then
    # Backup current nftables.conf if it exists
    if [[ -f /etc/nftables.conf ]]; then
        cp /etc/nftables.conf "/etc/nftables.conf.bak-$(date +%Y%m%d%H%M%S)"
    fi
    cp "${SCRIPT_DIR}/nftables.conf.template" /etc/nftables.conf
fi

# Validate and reload nftables
nft -c -f /etc/nftables.conf
nft -f /etc/nftables.conf
systemctl enable nftables.service
systemctl restart nftables.service
echo -e "${GREEN}✓ NFTables loaded and persistent service enabled.${NC}"

echo -e "${GREEN}[6/6] Docker Service Health Check...${NC}"
systemctl enable docker
systemctl start docker
echo -e "${GREEN}✓ Docker is running.${NC}"

echo -e "${BLUE}======================================================${NC}"
echo -e "${GREEN}  Host Initialization Complete! Ready for Deployment. ${NC}"
echo -e "${BLUE}======================================================${NC}"
