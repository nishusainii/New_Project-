#!/usr/bin/env bash
# ==============================================================================
# BARE-METAL SERVER A: Dedicated Hardened OpenLDAP Setup Script
# Host IP: 192.168.2.12 (or designated LDAP server IP)
# Domain : dc=innspark,dc=in
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${CYAN}  SERVER A: BARE-METAL HARDENED OPENLDAP INSTALLATION & CONFIGURATION         ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo ./setup-server-a-ldap.sh)${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LDAP_ADMIN_PASSWORD="${LDAP_ADMIN_PASSWORD:-AdminPassword123!}"

# 1. Package Installation
echo -e "\n${BOLD}${GREEN}1. Installing OpenLDAP & Security Tools...${NC}"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y slapd ldap-utils openssl gnutls-bin ssl-cert ufw

# 2. TLS Certificate Generation for LDAPS
echo -e "\n${BOLD}${GREEN}2. Configuring TLS/LDAPS Certificates...${NC}"
chmod +x "$SCRIPT_DIR/configs/ldap/cert-gen.sh"
"$SCRIPT_DIR/configs/ldap/cert-gen.sh" "192.168.2.12"

# 3. Configure slapd to listen on LDAPS
echo -e "\n${BOLD}${GREEN}3. Enabling slapd LDAPS (Port 636)...${NC}"
sed -i 's|^SLAPD_SERVICES=.*|SLAPD_SERVICES="ldap:/// ldaps:/// ldapi:///"|g' /etc/default/slapd

# 4. Import TLS Config into slapd
cat << EOF > /tmp/tls-config.ldif
dn: cn=config
changetype: modify
replace: olcTLSCACertificateFile
olcTLSCACertificateFile: /etc/ssl/openldap/ldap-ca.pem
-
replace: olcTLSCertificateFile
olcTLSCertificateFile: /etc/ssl/openldap/ldap-server.pem
-
replace: olcTLSCertificateKeyFile
olcTLSCertificateKeyFile: /etc/ssl/openldap/ldap-server.key
-
replace: olcTLSVerifyClient
olcTLSVerifyClient: never
EOF

ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/tls-config.ldif || true
rm -f /tmp/tls-config.ldif

# 5. Disable Anonymous Binds
echo -e "\n${BOLD}${GREEN}4. Enforcing Strict Disallow of Anonymous Binds...${NC}"
ldapmodify -Y EXTERNAL -H ldapi:/// -f "$SCRIPT_DIR/configs/ldap/disable-anon.ldif" || true

# 6. Apply Hardened ACLs
echo -e "\n${BOLD}${GREEN}5. Applying Granular Hardened ACLs...${NC}"
ldapmodify -Y EXTERNAL -H ldapi:/// -f "$SCRIPT_DIR/configs/ldap/slapd-hardened-acls.ldif" || true

# 7. Restart OpenLDAP
systemctl restart slapd
systemctl enable slapd

# 8. Seed Organizational Units & Wi-Fi Users
echo -e "\n${BOLD}${GREEN}6. Seeding Directory Structure (OUs, cn=wifi-users, employees)...${NC}"
ldapadd -c -x -H ldapi:/// -D "cn=admin,dc=innspark,dc=in" -w "$LDAP_ADMIN_PASSWORD" \
  -f "$SCRIPT_DIR/configs/ldap/users.ldif" || true

# 9. Configure UFW Firewall
echo -e "\n${BOLD}${GREEN}7. Hardening UFW Firewall for LDAP Server...${NC}"
ufw allow 22/tcp comment 'SSH'
ufw allow from 192.168.2.14 to any port 636 proto tcp comment 'RADIUS Server LDAPS'
ufw allow from 192.168.2.14 to any port 389 proto tcp comment 'RADIUS Server LDAP'
ufw --force enable || true

echo -e "\n${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${GREEN}  SERVER A (OpenLDAP) SETUP COMPLETE!                                         ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "  LDAPS Server Address : ${BOLD}ldaps://192.168.2.12:636${NC}"
echo -e "  Base DN              : ${BOLD}dc=innspark,dc=in${NC}"
echo -e "  Admin Bind DN        : ${BOLD}cn=admin,dc=innspark,dc=in${NC}"
echo -e "  FreeRADIUS Service DN: ${BOLD}cn=radius-bind,ou=Services,dc=innspark,dc=in${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}\n"
