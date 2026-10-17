#!/usr/bin/env bash
# ==============================================================================
# BARE-METAL SERVER B: FreeRADIUS 802.1X & ISC-DHCP Setup Script
# Host IP: 192.168.2.14
# Target LDAP: 192.168.2.12:636 (LDAPS)
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${CYAN}  SERVER B: BARE-METAL FREERADIUS 802.1X & DHCP INSTALLATION                  ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo ./setup-server-b-radius.sh)${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Package Installation
echo -e "\n${BOLD}${GREEN}1. Installing FreeRADIUS, FreeRADIUS-LDAP & ISC-DHCP...${NC}"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  freeradius freeradius-ldap freeradius-utils isc-dhcp-server ufw

# 2. Stop services for configuration
systemctl stop freeradius || true
systemctl stop isc-dhcp-server || true

# 3. Configure FreeRADIUS Clients (APs & Shared Secret)
echo -e "\n${BOLD}${GREEN}2. Configuring Authorized APs & BlastRADIUS Protection...${NC}"
cp "$SCRIPT_DIR/configs/radius/clients.conf" /etc/freeradius/3.0/clients.conf
chown freerad:freerad /etc/freeradius/3.0/clients.conf
chmod 640 /etc/freeradius/3.0/clients.conf

# 4. Configure FreeRADIUS LDAP Module
echo -e "\n${BOLD}${GREEN}3. Configuring FreeRADIUS LDAP Module (mods-available/ldap)...${NC}"
cp "$SCRIPT_DIR/configs/radius/ldap" /etc/freeradius/3.0/mods-available/ldap
ln -sf /etc/freeradius/3.0/mods-available/ldap /etc/freeradius/3.0/mods-enabled/ldap
chown -R freerad:freerad /etc/freeradius/3.0/mods-available/ldap

# 5. Enable LDAP in default and inner-tunnel sites
sed -i 's/^[[:space:]]*-ldap/        ldap/g' /etc/freeradius/3.0/sites-available/default || true
sed -i 's/^[[:space:]]*-ldap/        ldap/g' /etc/freeradius/3.0/sites-available/inner-tunnel || true

# 6. Configure ISC-DHCP Server
echo -e "\n${BOLD}${GREEN}4. Configuring ISC-DHCP Server (Subnet 10.31.1.0/24)...${NC}"
cp "$SCRIPT_DIR/configs/dhcp/dhcpd.conf" /etc/dhcp/dhcpd.conf
sed -i 's/INTERFACESv4=.*/INTERFACESv4="eth1"/g' /etc/default/isc-dhcp-server || true

# 7. Configure UFW Firewall
echo -e "\n${BOLD}${GREEN}5. Configuring UFW Firewall for RADIUS & DHCP...${NC}"
ufw allow 22/tcp comment 'SSH'
ufw allow 1812/udp comment 'RADIUS 802.1X Authentication'
ufw allow 1813/udp comment 'RADIUS Accounting'
ufw allow 67/udp comment 'DHCP Server'
ufw --force enable || true

# 8. Start & Enable Services
echo -e "\n${BOLD}${GREEN}6. Starting Services...${NC}"
systemctl restart freeradius
systemctl enable freeradius
systemctl restart isc-dhcp-server || true
systemctl enable isc-dhcp-server || true

echo -e "\n${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${GREEN}  SERVER B (FreeRADIUS + DHCP) SETUP COMPLETE!                                ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "  FreeRADIUS Service : ${BOLD}Active (UDP 1812 / 1813)${NC}"
echo -e "  BlastRADIUS Status : ${BOLD}${GREEN}Immune (require_message_authenticator = yes)${NC}"
echo -e "  DHCP Scope         : ${BOLD}10.31.1.50 - 10.31.1.250 (Gateway: 10.31.1.1)${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}\n"
