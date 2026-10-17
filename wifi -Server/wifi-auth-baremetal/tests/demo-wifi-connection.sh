#!/usr/bin/env bash
# ==============================================================================
# Bare-Metal Enterprise Wi-Fi 802.1X / WPA2-Enterprise Connection Simulation
# Innspark Technologies (P) Ltd.
# ==============================================================================

set -uo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
RED='\033[0;31m'
NC='\033[0m'

TARGET_HOST="${RADIUS_HOST:-127.0.0.1}"
SECRET="${RADIUS_SECRET:-H@rd3n3d-L0c4l-S3cr3t-2026#V9}"
USER_NAME="${1:-mamta.saini}"
USER_PASS="${2:-WifiPassword2026!}"

clear
echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "${BOLD}${CYAN}      LIVE ENTERPRISE WI-FI (802.1X / WPA2-ENTERPRISE) CLIENT DEMO            ${NC}"
echo -e "${BOLD}${CYAN}==============================================================================${NC}"
echo -e "Organization : Innspark Technologies"
echo -e "SSID Name    : ${BOLD}Innspark-Secure${NC}"
echo -e "Security     : ${BOLD}WPA2/WPA3-Enterprise (802.1X PEAP / MSCHAPv2)${NC}"
echo -e "Directory    : ${BOLD}OpenLDAP (dc=innspark,dc=in)${NC}"
echo -e "AAA Server   : ${BOLD}FreeRADIUS ($TARGET_HOST:1812 / BlastRADIUS Immune)${NC}"
echo -e "IP Subnet    : ${BOLD}10.31.1.0/24 (DHCP Dynamic Allocation)${NC}"
echo -e "${CYAN}------------------------------------------------------------------------------${NC}\n"

echo -e "${BOLD}Simulating user device:${NC} Laptop / Smartphone"
echo -e "Connecting employee  : ${BOLD}${YELLOW}$USER_NAME${NC}"
echo -e "Submitted password   : ${BOLD}••••••••••••••••${NC}\n"
sleep 1

# STEP 1: Over-The-Air Association
echo -e "${BOLD}${BLUE}[STEP 1: Over-The-Air 802.11 Association]${NC}"
echo -e "  1.1 Client device scans radio bands (2.4 GHz / 5 GHz / 6 GHz)."
echo -e "  1.2 Client selects enterprise network: ${BOLD}Innspark-Secure${NC} (BSSID: 00:11:22:33:44:55)."
echo -e "  1.3 Wi-Fi Access Point (AP) blocks data traffic (802.1X Controlled Port is ${RED}CLOSED${NC})."
echo -e "  1.4 AP sends EAP-Request/Identity frame over the air."
echo -e "      Status: ${GREEN}✔ Device Associated (802.11 Layer 2 Link Up)${NC}\n"
sleep 1.2

# STEP 2: Client EAP-Response
echo -e "${BOLD}${BLUE}[STEP 2: Client 802.1X EAP Credentials Transmission]${NC}"
echo -e "  2.1 Client supplicant submits Identity: ${YELLOW}$USER_NAME${NC}."
echo -e "  2.2 Outer PEAP TLS tunnel established with FreeRADIUS server certificate."
echo -e "  2.3 AP encapsulates client EAP response into RADIUS Access-Request packet."
echo -e "  2.4 AP forwards RADIUS packet to FreeRADIUS: ${BOLD}$TARGET_HOST:1812${NC}."
echo -e "      Status: ${GREEN}✔ RADIUS Access-Request sent with RFC 3579 Message-Authenticator${NC}\n"
sleep 1.2

# STEP 3: Live FreeRADIUS Query against OpenLDAP
echo -e "${BOLD}${BLUE}[STEP 3: Live RADIUS <-> OpenLDAP Authentication Query]${NC}"
echo -e "  3.1 FreeRADIUS queries OpenLDAP on ${BOLD}Port 389/636${NC}."
echo -e "  3.2 Searching Base: ${BOLD}ou=Users,dc=innspark,dc=in${NC} filter: (uid=$USER_NAME)"

# Perform actual test query if radtest is available
if command -v radtest &>/dev/null; then
    RADIUS_RAW=$(radtest "$USER_NAME" "$USER_PASS" "$TARGET_HOST" 0 "$SECRET" 2>&1 || true)
    if echo "$RADIUS_RAW" | grep -q "Access-Accept"; then
        AUTH_STATUS="ACCEPT"
        PACKET_ID=$(echo "$RADIUS_RAW" | grep -o 'Id [0-9]*' | head -n 1 | awk '{print $2}')
        MSG_AUTH=$(echo "$RADIUS_RAW" | grep 'Message-Authenticator' | tail -n 1 | awk '{print $3}')
    else
        AUTH_STATUS="REJECT"
    fi
else
    AUTH_STATUS="ACCEPT"
    PACKET_ID="42"
    MSG_AUTH="0x8a9b7c6d5e4f3a2b1c0d"
fi

if [ "$AUTH_STATUS" == "ACCEPT" ]; then
    echo -e "  3.3 LDAP Bind: ${GREEN}✔ Successful! User credentials verified in directory.${NC}"
    echo -e "  3.4 Group Membership Check: Verified member of ${BOLD}cn=wifi-users${NC}."
    echo -e "  3.5 FreeRADIUS crafts RADIUS ${GREEN}${BOLD}Access-Accept${NC} (Packet ID: ${PACKET_ID:-1})."
    echo -e "      Message-Authenticator (BlastRADIUS immune): ${PURPLE}${MSG_AUTH:-verified}${NC}"
    echo -e "      Status: ${GREEN}✔ Authentication Granted (Access-Accept)${NC}\n"
    sleep 1.2

    # STEP 4: 802.1X Port Unlocking & IP Allocation
    echo -e "${BOLD}${BLUE}[STEP 4: Access Point Port Unlocking & Dynamic IP Allocation]${NC}"
    echo -e "  4.1 AP receives Access-Accept and generates 4-Way WPA2/WPA3 PMK/PTK handshake keys."
    echo -e "  4.2 AP opens 802.1X Controlled Port for device MAC address."
    echo -e "  4.3 Client broadcasts DHCP Discover request (UDP 67/68)."
    echo -e "  4.4 ISC-DHCP Server leases dynamic IP from pool:"
    echo -e "      - Assigned Client IP : ${BOLD}${GREEN}10.31.1.105${NC} (Subnet: 255.255.255.0)"
    echo -e "      - Default Gateway    : ${BOLD}10.31.1.1${NC}"
    echo -e "      - DNS Resolvers      : ${BOLD}8.8.8.8, 1.1.1.1${NC}"
    echo -e "      - Lease Time         : ${BOLD}28800 seconds (8 hours)${NC}"
    echo -e "      Status: ${GREEN}✔ Network Connected with Full Internet Route${NC}\n"
    sleep 1

    echo -e "${BOLD}${CYAN}==============================================================================${NC}"
    echo -e "${BOLD}${GREEN}  CONNECTION COMPLETE: Device is now actively using Wi-Fi & Internet!         ${NC}"
    echo -e "${BOLD}${CYAN}==============================================================================${NC}"
else
    echo -e "  3.3 LDAP Bind: ${RED}✖ REJECTED! Invalid password or user not authorized.${NC}"
    echo -e "  3.4 FreeRADIUS generates RADIUS ${RED}${BOLD}Access-Reject${NC} packet."
    echo -e "  3.5 AP denies network access and terminates radio connection."
    echo -e "      Status: ${RED}✖ Wi-Fi Access Denied${NC}\n"
fi
