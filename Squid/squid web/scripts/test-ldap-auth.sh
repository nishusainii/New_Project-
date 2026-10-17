#!/usr/bin/env bash
# ==============================================================================
# Innspark Solutions - LDAP & Squid Authentication Diagnostic Script
# Purpose: Validates LDAP connectivity and Squid authentication helpers on Server 2
# Domain: innspark.in
# ==============================================================================

set -e

# Default Configuration (Modify to match your IPs if different)
LDAP_HOST="${LDAP_HOST:-10.31.1.10}"
LDAP_PORT="${LDAP_PORT:-389}"
BASE_DN="${BASE_DN:-dc=innspark,dc=in}"
USER_OU="${USER_OU:-ou=people,dc=innspark,dc=in}"
GROUP_OU="${GROUP_OU:-ou=groups,dc=innspark,dc=in}"
BIND_DN="${BIND_DN:-cn=squidbind,dc=innspark,dc=in}"
PASSWD_FILE="${PASSWD_FILE:-/etc/squid/ldap_password.txt}"

# Colors for terminal output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}  Innspark Squid <-> LDAP Authentication Diagnostics Utility    ${NC}"
echo -e "${BLUE}================================================================${NC}"

# Check 1: Network connectivity to LDAP Server
echo -n "[1/4] Checking TCP connection to LDAP server ($LDAP_HOST:$LDAP_PORT)... "
if nc -z -w 3 "$LDAP_HOST" "$LDAP_PORT" 2>/dev/null; then
    echo -e "${GREEN}PASSED${NC}"
else
    echo -e "${RED}FAILED${NC}"
    echo -e "${YELLOW}Error: Cannot reach $LDAP_HOST on port $LDAP_PORT. Check firewall / network routing.${NC}"
    exit 1
fi

# Check 2: Verify Bind Password File
echo -n "[2/4] Checking LDAP bind credentials file ($PASSWD_FILE)... "
if [ -f "$PASSWD_FILE" ]; then
    echo -e "${GREEN}EXISTS${NC}"
else
    echo -e "${RED}NOT FOUND${NC}"
    echo -e "${YELLOW}Please create $PASSWD_FILE with the password for $BIND_DN${NC}"
    exit 1
fi

# Check 3: Bind and Query LDAP directory
echo -n "[3/4] Testing LDAP bind using $BIND_DN... "
if ldapsearch -x -H "ldap://$LDAP_HOST:$LDAP_PORT" \
    -D "$BIND_DN" \
    -y "$PASSWD_FILE" \
    -b "$BASE_DN" -s base '(objectclass=*)' >/dev/null 2>&1; then
    echo -e "${GREEN}BIND SUCCESSFUL${NC}"
else
    echo -e "${RED}BIND FAILED${NC}"
    echo -e "${YELLOW}Check bind DN and password in $PASSWD_FILE${NC}"
    exit 1
fi

# Check 4: Interactive User Auth & Group Test
echo -e "\n${BLUE}[4/4] Testing Squid LDAP Authentication Helper${NC}"
echo -e "Enter username and password of an LDAP user to test:"
read -rp "Username (e.g., john.doe): " TEST_USER
read -rsp "Password: " TEST_PASS
echo ""

# Test basic_ldap_auth helper
BASIC_HELPER="/usr/lib/squid/basic_ldap_auth"
if [ ! -x "$BASIC_HELPER" ]; then
    echo -e "${RED}Helper not found at $BASIC_HELPER${NC}"
    exit 1
fi

echo -n "Testing Basic Auth for user '$TEST_USER'... "
AUTH_RESULT=$(echo "$TEST_USER $TEST_PASS" | $BASIC_HELPER \
    -b "$USER_OU" \
    -D "$BIND_DN" \
    -W "$PASSWD_FILE" \
    -f "(&(uid=%s)(objectClass=posixAccount))" \
    -H "ldap://$LDAP_HOST:$LDAP_PORT" 2>&1)

if [[ "$AUTH_RESULT" == *"OK"* ]]; then
    echo -e "${GREEN}AUTHENTICATION SUCCESSFUL (OK)${NC}"
else
    echo -e "${RED}AUTHENTICATION FAILED ($AUTH_RESULT)${NC}"
fi

# Test ext_ldap_group_acl helper
GROUP_HELPER="/usr/lib/squid/ext_ldap_group_acl"
if [ -x "$GROUP_HELPER" ]; then
    echo -n "Testing Group Membership in 'proxy_users'... "
    GROUP_RESULT=$(echo "$TEST_USER proxy_users" | $GROUP_HELPER \
        -b "$GROUP_OU" \
        -D "$BIND_DN" \
        -W "$PASSWD_FILE" \
        -f "(&(objectClass=posixGroup)(cn=%g)(memberUid=%u))" \
        -H "ldap://$LDAP_HOST:$LDAP_PORT" 2>&1)

    if [[ "$GROUP_RESULT" == *"OK"* ]]; then
        echo -e "${GREEN}GROUP CHECK PASSED (User is member of proxy_users)${NC}"
    else
        echo -e "${RED}GROUP CHECK FAILED ($GROUP_RESULT)${NC}"
    fi
fi

echo -e "\n${GREEN}Diagnostic completed.${NC}"
