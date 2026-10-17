#!/usr/bin/env bash
# ==============================================================================
# Wi-Fi RADIUS & LDAP Authentication Test Script
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting Wi-Fi RADIUS Authentication Test ===${NC}"

# Check if containers are running
if [ -z "$(docker ps -q -f name=wifi-freeradius)" ]; then
    echo -e "${RED}Error: wifi-freeradius container is not running.${NC}"
    echo "Please start the containers first: docker compose up -d"
    exit 1
fi

echo -e "${BLUE}1. Testing LDAP User Authentication: john.doe${NC}"
echo "Running: radtest john.doe WifiPassword2026! 127.0.0.1 0 \"H@rd3n3d-L0c4l-S3cr3t-2026#V9\""

RESULT=$(docker exec -i wifi-freeradius radtest john.doe WifiPassword2026! 127.0.0.1 0 "H@rd3n3d-L0c4l-S3cr3t-2026#V9" 2>&1)

echo "$RESULT"

if echo "$RESULT" | grep -q "Access-Accept"; then
    echo -e "${GREEN}===> SUCCESS: User 'john.doe' authenticated successfully via LDAP!${NC}"
else
    echo -e "${RED}===> FAILED: Authentication was rejected.${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}2. Testing Invalid Password Rejection (Security Check)${NC}"
echo "Running: radtest john.doe WrongPassword! 127.0.0.1 0 \"H@rd3n3d-L0c4l-S3cr3t-2026#V9\""

REJECT_RESULT=$(docker exec -i wifi-freeradius radtest john.doe WrongPassword! 127.0.0.1 0 "H@rd3n3d-L0c4l-S3cr3t-2026#V9" 2>&1 || true)
echo "$REJECT_RESULT"

if echo "$REJECT_RESULT" | grep -q "Access-Reject"; then
    echo -e "${GREEN}===> SUCCESS: Rogue / invalid password was properly REJECTED!${NC}"
else
    echo -e "${RED}===> WARNING: Expected rejection but got unexpected output.${NC}"
fi

echo ""
echo -e "${GREEN}=== All RADIUS <-> LDAP Tests Completed ===${NC}"
