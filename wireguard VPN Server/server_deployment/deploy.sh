#!/usr/bin/env bash
# ==============================================================================
# WireGuard Enterprise - Automated Container Deployment Script
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  Deploying WireGuard Enterprise Container Service     ${NC}"
echo -e "${BLUE}======================================================${NC}"

# Check for root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}[ERROR] This script must be run as root (use sudo).${NC}"
   exit 1
fi

# Ensure host setup was executed
if [[ ! -d /opt/wireguard-enterprise ]]; then
    echo -e "${YELLOW}Host directories not found. Running setup_host.sh first...${NC}"
    bash "${SCRIPT_DIR}/setup_host.sh"
fi

echo -e "${GREEN}[1/4] Synchronizing Application Code & Assets...${NC}"
if [[ -d "${PROJECT_ROOT}/app" ]]; then
    cp -ru "${PROJECT_ROOT}/app" /opt/wireguard-enterprise/
    echo -e "${GREEN}✓ Application files synced to /opt/wireguard-enterprise/app${NC}"
fi

# Check for offline image tarball or build
if [[ -f "${PROJECT_ROOT}/wireguard-enterprise-image.tar.gz" ]]; then
    echo -e "${GREEN}[2/4] Loading Pre-Packaged Docker Image...${NC}"
    docker load -i "${PROJECT_ROOT}/wireguard-enterprise-image.tar.gz" || true
elif [[ -f "${PROJECT_ROOT}/Dockerfile" ]]; then
    echo -e "${GREEN}[2/4] Building Docker Image from Dockerfile...${NC}"
    docker build -t wireguard-enterprise:latest "${PROJECT_ROOT}"
fi

echo -e "${GREEN}[3/4] Launching wireguard-manager Container...${NC}"
cd "${SCRIPT_DIR}"

if command -v docker-compose &> /dev/null; then
    docker-compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d --force-recreate
else
    docker compose -f "${SCRIPT_DIR}/docker-compose.yml" up -d --force-recreate
fi

echo -e "${GREEN}[4/4] Verifying Service Health...${NC}"
sleep 3

if docker ps -f name=wireguard-manager | grep -q wireguard-manager; then
    echo -e "${GREEN}✓ Container wireguard-manager is UP and running.${NC}"
else
    echo -e "${RED}✗ Container failed to start. Showing logs:${NC}"
    docker logs --tail 30 wireguard-manager
    exit 1
fi

echo -e "${BLUE}======================================================${NC}"
echo -e "${GREEN}  WireGuard Enterprise Deployment Successful!         ${NC}"
echo -e "${BLUE}======================================================${NC}"
echo -e "Web Portal:  ${BLUE}http://<SERVER_IP>:8000${NC}"
echo -e "Default User:${GREEN} admin${NC}"
echo -e "Default Pass:${GREEN} admin@123${NC}"
echo -e "Interface:   ${YELLOW}wg0 (Port 443/UDP)${NC}"
echo -e "Firewall:    ${YELLOW}/etc/nftables.conf & /etc/nftables/acl.nft${NC}"
echo -e "${BLUE}======================================================${NC}"
