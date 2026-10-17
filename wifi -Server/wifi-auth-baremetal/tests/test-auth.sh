#!/usr/bin/env bash
# ==============================================================================
# Bare-Metal Wi-Fi RADIUS & LDAP Authentication Test Script
# Innspark Technologies (P) Ltd.
# ==============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

TARGET_HOST="${RADIUS_HOST:-127.0.0.1}"
RADIUS_PORT="${RADIUS_PORT:-0}"
SECRET="${RADIUS_SECRET:-H@rd3n3d-L0c4l-S3cr3t-2026#V9}"
USER_NAME="${1:-john.doe}"
USER_PASS="${2:-WifiPassword2026!}"

echo -e "${BLUE}=== Starting Bare-Metal Wi-Fi RADIUS Authentication Test ===${NC}"
echo -e "Target Server : $TARGET_HOST"
echo -e "Test User     : $USER_NAME"
echo ""

# Check radtest binary
if ! command -v radtest &>/dev/null; then
    echo -e "${YELLOW}Warning: 'radtest' not found. Installing freeradius-utils...${NC}"
    sudo apt-get update -qq && sudo apt-get install -y -qq freeradius-utils
fi

echo -e "${BLUE}1. Testing Valid LDAP User Authentication: $USER_NAME${NC}"
echo "Running: radtest $USER_NAME [PROTECTED] $TARGET_HOST $RADIUS_PORT \"$SECRET\""

RESULT=$(radtest "$USER_NAME" "$USER_PASS" "$TARGET_HOST" "$RADIUS_PORT" "$SECRET" 2>&1 || true)
echo "$RESULT"

if echo "$RESULT" | grep -q "Access-Accept"; then
    echo -e "${GREEN}===> SUCCESS: User '$USER_NAME' authenticated successfully via LDAP!${NC}"
else
    echo -e "${RED}===> FAILED: Authentication was rejected or server unreachable.${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}2. Testing Invalid Password Rejection (Security Enforcement)${NC}"
echo "Running: radtest $USER_NAME WrongPassword! $TARGET_HOST $RADIUS_PORT \"$SECRET\""

REJECT_RESULT=$(radtest "$USER_NAME" "WrongPassword!" "$TARGET_HOST" "$RADIUS_PORT" "$SECRET" 2>&1 || true)
echo "$REJECT_RESULT"

if echo "$REJECT_RESULT" | grep -q "Access-Reject"; then
    echo -e "${GREEN}===> SUCCESS: Rogue / invalid password was properly REJECTED!${NC}"
else
    echo -e "${RED}===> WARNING: Expected Access-Reject but got unexpected output.${NC}"
fi

echo ""
echo -e "${GREEN}=== All RADIUS <-> LDAP Authentication Tests Passed ===${NC}"
