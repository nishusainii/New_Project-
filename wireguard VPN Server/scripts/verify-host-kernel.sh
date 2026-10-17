#!/usr/bin/env bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== WireGuard Enterprise Host Environment Audit ===${NC}"

# 1. Check Root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[FAIL] This script must be run as root (or with sudo).${NC}"
   exit 1
fi
echo -e "${GREEN}[OK] Running with root administrative privileges.${NC}"

# 2. Kernel Version
KERNEL_VER=$(uname -r)
echo -e "${BLUE}[INFO] Host Kernel Version: ${KERNEL_VER}${NC}"

# 3. WireGuard Kernel Module
echo -n "Checking WireGuard kernel module (wireguard.ko)... "
if modprobe wireguard 2>/dev/null; then
    echo -e "${GREEN}[OK] wireguard.ko loaded successfully.${NC}"
else
    echo -e "${YELLOW}[WARN] modprobe wireguard failed. Checking if built into kernel...${NC}"
    if grep -q "wireguard" /proc/modules 2>/dev/null || [ -d "/sys/module/wireguard" ]; then
        echo -e "${GREEN}[OK] WireGuard is in-tree and active in kernel.${NC}"
    else
        echo -e "${RED}[FAIL] WireGuard module not found. Kernel 5.6+ or wireguard-dkms required.${NC}"
    fi
fi

# 4. IP Forwarding
echo -n "Checking IPv4 Forwarding (net.ipv4.ip_forward)... "
IP_FWD=$(sysctl -n net.ipv4.ip_forward)
if [[ "${IP_FWD}" == "1" ]]; then
    echo -e "${GREEN}[OK] IP forwarding is already enabled (value: 1).${NC}"
else
    echo -e "${YELLOW}[ACTION] Enabling IP forwarding...${NC}"
    sysctl -w net.ipv4.ip_forward=1
    echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-wireguard-forward.conf
    echo -e "${GREEN}[OK] IP forwarding enabled and persisted to /etc/sysctl.d/99-wireguard-forward.conf.${NC}"
fi

# 5. NFTables Availability
echo -n "Checking NFTables userspace utility (nft)... "
if command -v nft >/dev/null 2>&1; then
    NFT_VER=$(nft --version)
    echo -e "${GREEN}[OK] ${NFT_VER}${NC}"
else
    echo -e "${YELLOW}[WARN] nft command not found on host. The container provides nftables, but host-side nft is recommended for boot loading.${NC}"
fi

# 6. Docker & Docker Compose
echo -n "Checking Docker daemon... "
if command -v docker >/dev/null 2>&1; then
    DOCKER_VER=$(docker --version)
    echo -e "${GREEN}[OK] ${DOCKER_VER}${NC}"
else
    echo -e "${RED}[FAIL] Docker is not installed on this host.${NC}"
fi

echo -n "Checking Docker Compose... "
if docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1; then
    echo -e "${GREEN}[OK] Docker Compose is available.${NC}"
else
    echo -e "${RED}[FAIL] Docker Compose is not available.${NC}"
fi

echo -e "${GREEN}=== Pre-requisite Audit Complete ===${NC}"
