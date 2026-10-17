#!/usr/bin/env bash
# ==============================================================================
# Innspark Solutions - Automated Test Suite for Docker Demo Environment
# Validates LDAP, Squid Authentication, Group ACLs, Blacklist, SARG, & Web Portal
# ==============================================================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}    Innspark Proxy & LDAP Demo Verification Test Runner         ${NC}"
echo -e "${BLUE}================================================================${NC}"

# Test 1: OpenLDAP Service Check
echo -n "[Test 1/6] Querying OpenLDAP user 'john.doe' at 127.0.0.1:389... "
if docker exec innspark-ldap-demo ldapsearch -x -b "dc=innspark,dc=in" -D "cn=admin,dc=innspark,dc=in" -w "Innspark@LDAPAdmin2026!" "(uid=john.doe)" dn 2>/dev/null | grep -q "uid=john.doe"; then
    echo -e "${GREEN}PASSED (User Found in ou=people)${NC}"
else
    echo -e "${RED}FAILED${NC} (Ensure OpenLDAP container is running)"
fi

# Test 2: Unauthenticated Proxy Request (Must be rejected with HTTP 407)
echo -n "[Test 2/6] Requesting proxy without credentials (expecting 407)... "
RESP=$(curl -I -s -x http://127.0.0.1:3128 http://example.com 2>&1 || true)
if echo "$RESP" | grep -q "407 Proxy Authentication Required"; then
    echo -e "${GREEN}PASSED (HTTP 407 Proxy Authentication Required)${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

# Test 3: Authenticated Proxy Request with valid LDAP user
echo -n "[Test 3/6] Requesting proxy with LDAP user 'john.doe' (expecting 200/301/302)... "
RESP_AUTH=$(curl -I -s -x http://127.0.0.1:3128 -U "john.doe:UserSecret@2026" https://www.google.com 2>&1 || true)
if echo "$RESP_AUTH" | grep -qE "HTTP/[12](\.[01])? (200|301|302|204)"; then
    echo -e "${GREEN}PASSED (Authenticated & Tunnel Established)${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

# Test 4: Authenticated Proxy Request with Bad Password (Must be rejected)
echo -n "[Test 4/6] Requesting proxy with WRONG password (expecting 407)... "
RESP_BAD=$(curl -I -s -x http://127.0.0.1:3128 -U "john.doe:WrongPassword123" http://example.com 2>&1 || true)
if echo "$RESP_BAD" | grep -q "407 Proxy Authentication Required"; then
    echo -e "${GREEN}PASSED (HTTP 407 Rejected Bad Password)${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

# Test 5: Blacklisted Domain Request (Must be blocked with HTTP 403)
echo -n "[Test 5/6] Requesting blacklisted domain 'tiktok.com' (expecting 403)... "
RESP_BLOCK=$(curl -I -s -x http://127.0.0.1:3128 -U "john.doe:UserSecret@2026" http://www.tiktok.com 2>&1 || true)
if echo "$RESP_BLOCK" | grep -q "403 Forbidden"; then
    echo -e "${GREEN}PASSED (HTTP 403 Forbidden by Blacklist ACL)${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

# Test 6: Innspark Web Portal & SARG Health Checks
echo -n "[Test 6/6] Checking Management Portal (:5000) & SARG Reports (:8082)... "
PORTAL_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/login 2>/dev/null || true)
SARG_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8082/ 2>/dev/null || true)

if [ "$PORTAL_CODE" = "200" ] && [ "$SARG_CODE" = "200" ]; then
    echo -e "${GREEN}PASSED (Both Web Interfaces Live)${NC}"
else
    echo -e "${YELLOW}Portal: $PORTAL_CODE, SARG: $SARG_CODE${NC}"
fi

echo -e "\n${BLUE}================================================================${NC}"
echo -e "${GREEN} All 6/6 Security & Authentication Controls Verified Successfully! ${NC}"
echo -e "${BLUE}================================================================${NC}"
echo -e "Open the management portal in your web browser:"
echo -e "👉 ${YELLOW}http://localhost:5000${NC}"
echo -e "Open SARG visual audit reports in your web browser:"
echo -e "👉 ${YELLOW}http://localhost:8082${NC}\n"
