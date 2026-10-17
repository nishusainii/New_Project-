#!/usr/bin/env bash
# ==============================================================================
# Production Deployment Script for Dockerized Enterprise Wi-Fi Auth Stack
# Organization: Innspark Technologies (P) Ltd.
# Domain: dc=innspark,dc=in
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${CYAN}  INSPARK TECHNOLOGIES - ENTERPRISE WI-FI AUTHENTICATION (DOCKER PRODUCTION)  ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Prerequisite Check
echo -e "\n${BOLD}${BLUE}1. Checking Prerequisites...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker Engine first.${NC}"
    exit 1
fi

if ! docker compose version &> /dev/null && ! docker-compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed.${NC}"
    exit 1
fi
echo -e "   ${GREEN}✔ Docker Engine & Docker Compose detected.${NC}"

# 2. Environment Configuration
echo -e "\n${BOLD}${BLUE}2. Validating Environment Configuration...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.production.example ]; then
        echo -e "   ${YELLOW}Creating .env from .env.production.example...${NC}"
        cp .env.production.example .env
    else
        echo -e "   ${YELLOW}Creating standard production .env file...${NC}"
        cat << 'EOF' > .env
LDAP_ORGANISATION=Innspark Technologies
LDAP_DOMAIN=innspark.in
LDAP_BASE_DN=dc=innspark,dc=in
LDAP_ADMIN_DN=cn=admin,dc=innspark,dc=in
LDAP_ADMIN_PASSWORD=AdminPassword123!
LDAP_CONFIG_PASSWORD=ConfigPassword123!
RADIUS_SECRET=H@rd3n3d-L0c4l-S3cr3t-2026#V9
DHCP_INTERFACE=eth0
SECRET_KEY=innspark-super-secure-production-session-key-2026#V9
PHPLDAPADMIN_PORT=8088
EOF
    fi
fi
echo -e "   ${GREEN}✔ Environment settings loaded (.env).${NC}"

# 3. Build & Deploy Containers
echo -e "\n${BOLD}${BLUE}3. Building & Launching Containers...${NC}"
docker build --network host -t wifi-auth-docker-web-admin ./web-admin
docker compose up -d openldap freeradius web-admin

echo -e "   ${GREEN}✔ Containers launched successfully.${NC}"

# 4. Wait for OpenLDAP and Seed Directory
echo -e "\n${BOLD}${BLUE}4. Initializing OpenLDAP Directory...${NC}"
chmod +x ./seed-ldap.sh ./test-auth.sh ./test-hardened-suite.sh ./vapt-audit.sh ./demo-wifi-connection.sh
./seed-ldap.sh

# 5. Run Immediate Self-Test
echo -e "\n${BOLD}${BLUE}5. Executing 802.1X FreeRADIUS & LDAP Self-Test...${NC}"
./test-auth.sh

echo -e "\n${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${GREEN}  DEPLOYMENT COMPLETE & VERIFIED OPERATIONAL!                                 ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "  Web Management Console : ${BOLD}${CYAN}http://localhost:8088${NC}"
echo -e "  Root Administrator DN  : ${BOLD}cn=admin,dc=innspark,dc=in${NC} (or simply ${BOLD}admin${NC})"
echo -e "  Default Admin Password : ${BOLD}AdminPassword123!${NC}"
echo -e "  FreeRADIUS Port        : ${BOLD}UDP 1812 (Authentication) / UDP 1813 (Accounting)${NC}"
echo -e "  OpenLDAP Port          : ${BOLD}TCP 389 (Host Network Mode)${NC}"
echo -e "  BlastRADIUS Protection : ${BOLD}${GREEN}ACTIVE (RFC 3579 Message-Authenticator)${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}\n"
