#!/usr/bin/env bash
# ==============================================================================
# SINGLE SERVER BARE-METAL SETUP: OpenLDAP + FreeRADIUS + Web Admin + DHCP
# Deploys the entire production Wi-Fi authentication stack on a single Ubuntu host.
# Organization: Innspark Technologies (P) Ltd.
# Domain: dc=innspark,dc=in
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${CYAN}  INSPARK TECHNOLOGIES - SINGLE SERVER BARE-METAL DEPLOYMENT                  ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root: sudo ./setup-single-server.sh${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-AdminPassword123!}"

# 1. Install all system dependencies
echo -e "\n${BOLD}${GREEN}1. Installing System Packages...${NC}"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  slapd ldap-utils freeradius freeradius-ldap freeradius-utils \
  isc-dhcp-server python3 python3-pip python3-venv openssl ufw

# 2. Configure OpenLDAP
echo -e "\n${BOLD}${GREEN}2. Configuring OpenLDAP Directory (dc=innspark,dc=in)...${NC}"
sed -i 's|^SLAPD_SERVICES=.*|SLAPD_SERVICES="ldap://127.0.0.1:389 ldapi:///"|g' /etc/default/slapd
systemctl restart slapd
systemctl enable slapd

# Seed OUs and users
ldapadd -c -x -H ldapi:/// -D "cn=admin,dc=innspark,dc=in" -w "$LDAP_ADMIN_PASSWORD" \
  -f "$SCRIPT_DIR/configs/ldap/users.ldif" || true

# 3. Configure FreeRADIUS
echo -e "\n${BOLD}${GREEN}3. Configuring FreeRADIUS with BlastRADIUS Immunity...${NC}"
cp "$SCRIPT_DIR/configs/radius/clients.conf" /etc/freeradius/3.0/clients.conf
cp "$SCRIPT_DIR/configs/radius/ldap" /etc/freeradius/3.0/mods-available/ldap

# Set LDAP host to localhost for single server
sed -i "s/server = '192.168.2.12'/server = '127.0.0.1'/g" /etc/freeradius/3.0/mods-available/ldap
sed -i "s/port = 636/port = 389/g" /etc/freeradius/3.0/mods-available/ldap

ln -sf /etc/freeradius/3.0/mods-available/ldap /etc/freeradius/3.0/mods-enabled/ldap
chown -R freerad:freerad /etc/freeradius/3.0/

systemctl restart freeradius
systemctl enable freeradius

# 4. Deploy Web Admin Management Console
echo -e "\n${BOLD}${GREEN}4. Deploying Web Admin Management Console (/opt/innspark/web-admin)...${NC}"
chmod +x "$SCRIPT_DIR/setup-web-admin.sh"
"$SCRIPT_DIR/setup-web-admin.sh"

# 5. Open Firewall Ports
echo -e "\n${BOLD}${GREEN}5. Configuring UFW Firewall...${NC}"
ufw allow 22/tcp comment 'SSH'
ufw allow 8088/tcp comment 'Innspark Web Console'
ufw allow 1812/udp comment 'FreeRADIUS Auth'
ufw allow 1813/udp comment 'FreeRADIUS Acct'
ufw allow 67/udp comment 'DHCP Server'
ufw --force enable || true

# 6. Verification
echo -e "\n${BOLD}${GREEN}6. Testing 802.1X Authentication...${NC}"
radtest john.doe WifiPassword2026! 127.0.0.1 0 "H@rd3n3d-L0c4l-S3cr3t-2026#V9"

echo -e "\n${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${GREEN}  SINGLE SERVER BARE-METAL SETUP COMPLETE!                                    ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "  Web Console      : ${BOLD}${CYAN}http://localhost:8088${NC}"
echo -e "  Login Identity   : ${BOLD}admin${NC} / ${BOLD}AdminPassword123!${NC}"
echo -e "  FreeRADIUS Port  : ${BOLD}UDP 1812${NC}"
echo -e "  Directory Server : ${BOLD}OpenLDAP 127.0.0.1:389 (dc=innspark,dc=in)${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}\n"
