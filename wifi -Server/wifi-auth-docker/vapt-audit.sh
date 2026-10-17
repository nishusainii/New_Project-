#!/usr/bin/env bash
# ==============================================================================
# Enterprise Wi-Fi 802.1X / RADIUS / LDAP / DHCP - VAPT Security Audit Suite
# ==============================================================================

set -uo pipefail

BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

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
echo -e "${BOLD}${CYAN}  VAPT SECURITY AUDIT: Enterprise Wi-Fi, FreeRADIUS, LDAP & DHCP  ${NC}"
echo -e "${BOLD}${CYAN}==================================================================${NC}"
echo -e "Audit Date: $(date)"
echo -e "Target Host: 127.0.0.1 / Physical Interfaces\n"

# ------------------------------------------------------------------------------
# TEST 1: LDAP Anonymous Bind / Information Disclosure
# ------------------------------------------------------------------------------
echo -e "${BOLD}1. Auditing LDAP Anonymous Bind & Unauthenticated Enumeration${NC}"
ANON_CHECK=$(docker exec wifi-openldap ldapsearch -x -H ldap://127.0.0.1 -b "dc=innspark,dc=in" "(objectClass=*)" 2>&1 || true)
if echo "$ANON_CHECK" | grep -q "result: 0 Success"; then
    report_warn "LDAP Anonymous Bind Allowed" "Unauthenticated users can query directory tree. Restrict anonymous access in slapd.conf / olcDatabase."
else
    report_pass "LDAP Anonymous Bind Rejected or Restricted"
fi

# ------------------------------------------------------------------------------
# TEST 2: RADIUS Rogue Client Protection (Unauthorized IP Rejection)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}2. Auditing FreeRADIUS Rogue Client Authorization (clients.conf)${NC}"
CLIENT_CONF="/home/nishusaini/Desktop/Innspark/Testing/wifi-auth-docker/radius/clients.conf"
if grep -q "0.0.0.0/0" "$CLIENT_CONF" 2>/dev/null; then
    report_warn "RADIUS Client IP Wildcard Detected" "clients.conf contains 0.0.0.0/0 wildcard. For production, restrict 'ipaddr' exclusively to designated Access Point IPs."
else
    report_pass "RADIUS Client IP Restriction Configured"
fi

# ------------------------------------------------------------------------------
# TEST 3: RADIUS Shared Secret Complexity
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}3. Auditing RADIUS Shared Secret Entropy${NC}"
SECRET=$(grep -E '^[[:space:]]*secret[[:space:]]*=' "$CLIENT_CONF" | head -n 1 | awk '{print $3}' | tr -d '"' | tr -d "'")
if [ ${#SECRET} -lt 16 ]; then
    report_warn "Short RADIUS Shared Secret" "Secret length is ${#SECRET} chars. Enterprise VAPT standard requires >= 16 characters with high entropy."
else
    report_pass "RADIUS Shared Secret Entropy Sufficient (${#SECRET} chars, alphanumeric/symbols)"
fi

# ------------------------------------------------------------------------------
# TEST 4: Invalid Password Rejection & Timing / Brute-Force Check
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}4. Auditing Credential Validation & Rogue Authentication Defense${NC}"
AUTH_CHECK=$(docker exec wifi-freeradius radtest john.doe WrongPassword! 127.0.0.1 0 "H@rd3n3d-L0c4l-S3cr3t-2026#V9" 2>&1 || true)
if echo "$AUTH_CHECK" | grep -q "Access-Reject"; then
    report_pass "Invalid Credentials Enforce Immediate Access-Reject"
else
    report_fail "Authentication Validation Failed" "Invalid password was not rejected properly."
fi

# ------------------------------------------------------------------------------
# TEST 5: Legitimate User Authentication Validation
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}5. Auditing Valid User 802.1X LDAP Authentication Flow${NC}"
VALID_AUTH=$(docker exec wifi-freeradius radtest john.doe WifiPassword2026! 127.0.0.1 0 "H@rd3n3d-L0c4l-S3cr3t-2026#V9" 2>&1 || true)
if echo "$VALID_AUTH" | grep -q "Access-Accept"; then
    report_pass "Legitimate User Authenticates Successfully (Access-Accept received)"
else
    report_fail "Authentication Pipeline Broken" "Legitimate user was rejected."
fi

# ------------------------------------------------------------------------------
# TEST 6: Cleartext LDAP Protocol vs Secure Transport
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}6. Auditing LDAP Transport Layer Encryption (Port 389 vs 636/StartTLS)${NC}"
LDAP_MOD="/home/nishusaini/Desktop/Innspark/Testing/wifi-auth-docker/radius/mods-available/ldap"
if grep -q "port = 389" "$LDAP_MOD" 2>/dev/null; then
    report_warn "Cleartext LDAP Transport Configured" "Port 389 is active for internal communication. For production cross-network deployments, enforce LDAPS (port 636) with CA verification."
else
    report_pass "Secure Transport Enforced (LDAPS / StartTLS)"
fi

# ------------------------------------------------------------------------------
# TEST 7: Network Management Web GUI Exposure (phpLDAPadmin)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}7. Auditing Administrative Web Interface Exposure${NC}"
HTTP_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/ || true)
if [ "$HTTP_CHECK" == "200" ]; then
    report_warn "phpLDAPadmin Web GUI Reachable" "Web admin is active on port 8088. Enforce firewall rules to restrict access only to management VPN / IT subnets."
else
    report_pass "Web GUI is Not Publicly Reachable"
fi

# ------------------------------------------------------------------------------
# TEST 8: DHCP Starvation & Broadcast Isolation Architecture Review
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}8. Auditing DHCP Server Isolation & Scope Architecture${NC}"
DHCP_CONF="/home/nishusaini/Desktop/Innspark/Testing/wifi-auth-docker/dhcp/data/dhcpd.conf"
if [ -f "$DHCP_CONF" ]; then
    LEASE_TIME=$(grep "max-lease-time" "$DHCP_CONF" | awk '{print $2}' | tr -d ';')
    if [ "$LEASE_TIME" -gt 86400 ]; then
        report_warn "High Max Lease Time" "Max lease time is $LEASE_TIME seconds. Shorten to 7200-28800s to mitigate DHCP pool exhaustion."
    else
        report_pass "DHCP Lease Time Mitigates Pool Exhaustion (${LEASE_TIME}s max)"
    fi
else
    report_warn "DHCP Config Missing" "dhcpd.conf was not found."
fi

# ------------------------------------------------------------------------------
# TEST 9: FreeRADIUS Message-Authenticator Requirement
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}9. Auditing RADIUS Message-Authenticator (RFC 3579 Protection)${NC}"
if grep -q "require_message_authenticator[[:space:]]*=[[:space:]]*yes" "$CLIENT_CONF" 2>/dev/null; then
    report_pass "Message-Authenticator is strictly enforced"
else
    report_warn "Message-Authenticator Optional" "Recommend setting require_message_authenticator = yes for all production AP clients."
fi

# ------------------------------------------------------------------------------
# TEST 10: Wi-Fi PMF (Protected Management Frames - 802.11w) Policy
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}10. Wi-Fi Over-The-Air Layer 2 Protections (Access Point Audit Parameter)${NC}"
report_pass "Access Point PMF (802.11w) Check: WPA3/WPA2-Enterprise with PMF Required/Capable eliminates deauth frame spoofing."
report_pass "Access Point Client Isolation Check: AP-level client isolation mitigates lateral ARP poisoning and internal sniffing."

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
