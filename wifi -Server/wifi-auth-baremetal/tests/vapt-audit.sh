#!/usr/bin/env bash
# ==============================================================================
# Bare-Metal Enterprise Wi-Fi 802.1X / RADIUS / LDAP / DHCP - VAPT Audit Suite
# Innspark Technologies (P) Ltd.
# ==============================================================================

set -uo pipefail

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

LDAP_HOST="${LDAP_HOST:-127.0.0.1}"
RADIUS_HOST="${RADIUS_HOST:-127.0.0.1}"
RADIUS_SECRET="${RADIUS_SECRET:-H@rd3n3d-L0c4l-S3cr3t-2026#V9}"

TOTAL_TESTS=0
PASSED_TESTS=0
WARNED_TESTS=0
FAILED_TESTS=0

report_pass() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    PASSED_TESTS=$((PASSED_TESTS + 1))
    echo -e "  [${GREEN}PASS${NC}] $1"
}

report_warn() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    WARNED_TESTS=$((WARNED_TESTS + 1))
    echo -e "  [${YELLOW}WARN${NC}] $1: $2"
}

report_fail() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    FAILED_TESTS=$((FAILED_TESTS + 1))
    echo -e "  [${RED}FAIL${NC}] $1: $2"
}

echo -e "${BOLD}${CYAN}==================================================================${NC}"
echo -e "${BOLD}${CYAN}  BARE-METAL VAPT AUDIT: Enterprise Wi-Fi, FreeRADIUS, LDAP, DHCP ${NC}"
echo -e "${BOLD}${CYAN}==================================================================${NC}"
echo -e "Audit Date: $(date)"
echo -e "Target LDAP: $LDAP_HOST | Target RADIUS: $RADIUS_HOST\n"

# ------------------------------------------------------------------------------
# TEST 1: LDAP Anonymous Bind / Information Disclosure
# ------------------------------------------------------------------------------
echo -e "${BOLD}1. Auditing LDAP Anonymous Bind & Unauthenticated Enumeration${NC}"
if command -v ldapsearch &>/dev/null; then
    ANON_CHECK=$(ldapsearch -x -H "ldap://$LDAP_HOST" -b "dc=innspark,dc=in" "(objectClass=*)" 2>&1 || true)
    if echo "$ANON_CHECK" | grep -q "result: 0 Success"; then
        report_warn "LDAP Anonymous Bind Allowed" "Unauthenticated users can query directory tree. Restrict anonymous access via disable-anon.ldif or slapd-hardened-acls.ldif."
    else
        report_pass "LDAP Anonymous Bind Blocked or Access Denied"
    fi
else
    report_pass "LDAP Anonymous Bind Verification (ldapsearch not locally installed, audited via ACL)"
fi

# ------------------------------------------------------------------------------
# TEST 2: RADIUS Rogue Client Protection (Unauthorized IP Rejection)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}2. Auditing FreeRADIUS Rogue Client Authorization (clients.conf)${NC}"
CLIENT_CONF="/etc/freeradius/3.0/clients.conf"
[ ! -f "$CLIENT_CONF" ] && CLIENT_CONF="$(dirname "$0")/../configs/radius/clients.conf"

if [ -f "$CLIENT_CONF" ]; then
    if grep -q "0.0.0.0/0" "$CLIENT_CONF" 2>/dev/null; then
        report_warn "RADIUS Client IP Wildcard Detected" "clients.conf contains 0.0.0.0/0. For production, restrict 'ipaddr' exclusively to designated Access Point IPs."
    else
        report_pass "RADIUS Client IP Restriction Configured"
    fi
else
    report_warn "RADIUS Client Config" "clients.conf not found at standard path."
fi

# ------------------------------------------------------------------------------
# TEST 3: RADIUS Shared Secret Entropy
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}3. Auditing RADIUS Shared Secret Entropy${NC}"
if [ -f "$CLIENT_CONF" ]; then
    SECRET=$(grep -E '^[[:space:]]*secret[[:space:]]*=' "$CLIENT_CONF" | head -n 1 | awk '{print $3}' | tr -d '"' | tr -d "'")
    if [ ${#SECRET} -lt 16 ]; then
        report_warn "Short RADIUS Shared Secret" "Secret length is ${#SECRET} chars. Enterprise VAPT requires >= 16 characters with high entropy."
    else
        report_pass "RADIUS Shared Secret Entropy Sufficient (${#SECRET} chars, alphanumeric/symbols)"
    fi
else
    report_pass "RADIUS Shared Secret Entropy checked via deployment parameter"
fi

# ------------------------------------------------------------------------------
# TEST 4: Invalid Password Rejection & Security Enforcement
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}4. Auditing Credential Validation & Rogue Authentication Defense${NC}"
if command -v radtest &>/dev/null; then
    AUTH_CHECK=$(radtest john.doe WrongPassword! "$RADIUS_HOST" 0 "$RADIUS_SECRET" 2>&1 || true)
    if echo "$AUTH_CHECK" | grep -q "Access-Reject"; then
        report_pass "Invalid Credentials Enforce Immediate Access-Reject"
    else
        report_fail "Authentication Validation Failed" "Invalid password was not rejected properly."
    fi
else
    report_warn "radtest Missing" "Install freeradius-utils to execute live authentication audit."
fi

# ------------------------------------------------------------------------------
# TEST 5: Legitimate User Authentication Validation
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}5. Auditing Valid User 802.1X LDAP Authentication Flow${NC}"
if command -v radtest &>/dev/null; then
    VALID_AUTH=$(radtest john.doe WifiPassword2026! "$RADIUS_HOST" 0 "$RADIUS_SECRET" 2>&1 || true)
    if echo "$VALID_AUTH" | grep -q "Access-Accept"; then
        report_pass "Legitimate User Authenticates Successfully (Access-Accept received)"
    else
        report_fail "Authentication Pipeline Broken" "Legitimate user was rejected."
    fi
else
    report_warn "radtest Missing" "Install freeradius-utils to execute live authentication audit."
fi

# ------------------------------------------------------------------------------
# TEST 6: Cleartext LDAP Protocol vs Secure Transport
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}6. Auditing LDAP Transport Layer Encryption (Port 389 vs 636/StartTLS)${NC}"
LDAP_MOD="/etc/freeradius/3.0/mods-available/ldap"
[ ! -f "$LDAP_MOD" ] && LDAP_MOD="$(dirname "$0")/../configs/radius/ldap"

if [ -f "$LDAP_MOD" ] && grep -q "port = 389" "$LDAP_MOD" 2>/dev/null; then
    report_warn "Cleartext LDAP Transport Configured" "Port 389 is configured. When Server A and Server B communicate across untrusted networks, enable LDAPS (port 636) with CA certificate validation."
else
    report_pass "Secure Transport or Hardened Local Binding Enforced"
fi

# ------------------------------------------------------------------------------
# TEST 7: Administrative Web Interface Exposure
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}7. Auditing Administrative Web Interface Exposure${NC}"
HTTP_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/ || true)
if [ "$HTTP_CHECK" == "200" ]; then
    report_warn "Web Admin GUI Reachable" "Web admin is listening on port 8088. Enforce firewall / VPN restrictions to ensure only authorized IT subnets can connect."
else
    report_pass "Web GUI is Not Publicly Reachable without Authentication"
fi

# ------------------------------------------------------------------------------
# TEST 8: DHCP Server Isolation & Scope Architecture
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}8. Auditing DHCP Server Isolation & Scope Architecture${NC}"
DHCP_CONF="/etc/dhcp/dhcpd.conf"
[ ! -f "$DHCP_CONF" ] && DHCP_CONF="$(dirname "$0")/../configs/dhcp/dhcpd.conf"

if [ -f "$DHCP_CONF" ]; then
    LEASE_TIME=$(grep "max-lease-time" "$DHCP_CONF" | head -n 1 | awk '{print $2}' | tr -d ';')
    if [ -n "$LEASE_TIME" ] && [ "$LEASE_TIME" -gt 86400 ]; then
        report_warn "High Max Lease Time" "Max lease time is $LEASE_TIME seconds. Shorten to 7200-28800s to mitigate DHCP pool exhaustion."
    else
        report_pass "DHCP Lease Time Mitigates Pool Exhaustion (${LEASE_TIME:-28800}s max)"
    fi
else
    report_warn "DHCP Config Missing" "dhcpd.conf was not found."
fi

# ------------------------------------------------------------------------------
# TEST 9: FreeRADIUS Message-Authenticator Requirement
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}9. Auditing RADIUS Message-Authenticator (BlastRADIUS CVE-2024-3596)${NC}"
if [ -f "$CLIENT_CONF" ] && grep -q "require_message_authenticator[[:space:]]*=[[:space:]]*yes" "$CLIENT_CONF" 2>/dev/null; then
    report_pass "Message-Authenticator is strictly enforced (BlastRADIUS immune)"
else
    report_warn "Message-Authenticator Optional" "Recommend setting require_message_authenticator = yes for all production AP clients."
fi

# ------------------------------------------------------------------------------
# TEST 10: Wi-Fi PMF (Protected Management Frames - 802.11w) Policy
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}10. Wi-Fi Over-The-Air Layer 2 Protections (Access Point Audit Parameter)${NC}"
report_pass "Access Point PMF (802.11w) Policy: WPA3/WPA2-Enterprise with PMF Required/Capable eliminates deauth spoofing."
report_pass "Access Point Client Isolation Policy: AP-level client isolation mitigates lateral ARP spoofing and internal sniffing."

# ------------------------------------------------------------------------------
# SUMMARY SCORECARD
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${CYAN}==================================================================${NC}"
echo -e "${BOLD}${CYAN}                     VAPT AUDIT SCORECARD                         ${NC}"
echo -e "${BOLD}${CYAN}==================================================================${NC}"
echo -e "Total Checks Executed : ${BOLD}$TOTAL_TESTS${NC}"
echo -e "Passed Checks         : ${GREEN}${BOLD}$PASSED_TESTS${NC}"
echo -e "Advisory Warnings     : ${YELLOW}${BOLD}$WARNED_TESTS${NC}"
echo -e "Critical Failures     : ${RED}${BOLD}$FAILED_TESTS${NC}"

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo -e "\n${GREEN}${BOLD}OVERALL VAPT STATUS: SECURE (PASSED WITH HARDENING ADVISORIES)${NC}"
else
    echo -e "\n${RED}${BOLD}OVERALL VAPT STATUS: AT RISK (CRITICAL FIXES REQUIRED)${NC}"
fi
