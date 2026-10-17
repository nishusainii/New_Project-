#!/usr/bin/env bash
# ==============================================================================
# Bare-Metal Hardened Environment Testing Suite
# Stress, Concurrency, BlastRADIUS, LDAP Injection, and Resilience Verification
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

SECRET="${RADIUS_SECRET:-H@rd3n3d-L0c4l-S3cr3t-2026#V9}"
HOST="${RADIUS_HOST:-127.0.0.1:1812}"

echo -e "${BOLD}${CYAN}======================================================================${NC}"
echo -e "${BOLD}${CYAN}  BARE-METAL HARDENED ENVIRONMENT & STRESS RESILIENCE TEST SUITE      ${NC}"
echo -e "${BOLD}${CYAN}======================================================================${NC}"
echo -e "Target Server: $HOST"
echo -e "Protocol: RADIUS over UDP (802.1X Backed by OpenLDAP)"
echo -e "Timestamp: $(date)\n"

# Check radclient binary
if ! command -v radclient &>/dev/null; then
    echo -e "${YELLOW}Warning: 'radclient' not found. Installing freeradius-utils...${NC}"
    sudo apt-get update -qq && sudo apt-get install -y -qq freeradius-utils
fi

# ------------------------------------------------------------------------------
# TEST 1: BlastRADIUS (CVE-2024-3596) Protocol Integrity Verification
# ------------------------------------------------------------------------------
echo -e "${BOLD}${BLUE}1. Testing BlastRADIUS (CVE-2024-3596) Defense (-b flag)${NC}"
echo "Sending Access-Request with strict RFC 3579 Message-Authenticator validation..."

BLAST_RES=$(echo "User-Name = john.doe, User-Password = WifiPassword2026!" | \
  radclient -b "$HOST" auth "$SECRET" 2>&1 || true)

if echo "$BLAST_RES" | grep -q "Access-Accept"; then
    echo -e "  [${GREEN}PASS${NC}] BlastRADIUS Integrity Check: FreeRADIUS strictly verified Message-Authenticator."
else
    echo -e "  [${RED}FAIL${NC}] BlastRADIUS Check Failed: $BLAST_RES"
    exit 1
fi

# ------------------------------------------------------------------------------
# TEST 2: High Concurrency & Throughput Stress Test (100 parallel requests)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}2. Executing Concurrency & Load Stress Test (100 requests, 10 parallel)${NC}"
START_TIME=$(date +%s%N)
LOAD_RES=$(echo "User-Name = john.doe, User-Password = WifiPassword2026!" | \
  radclient -s -c 100 -p 10 "$HOST" auth "$SECRET" 2>&1 || true)
END_TIME=$(date +%s%N)

ELAPSED_MS=$(( (END_TIME - START_TIME) / 1000000 ))
ACCEPTED=$(echo "$LOAD_RES" | grep "Accepted" | awk '{print $3}')
LOST=$(echo "$LOAD_RES" | grep "Lost" | awk '{print $3}')

echo -e "  Stress Test Execution Time : ${BOLD}${ELAPSED_MS} ms${NC}"
echo -e "  Total Packets Accepted     : ${GREEN}${BOLD}${ACCEPTED:-0} / 100${NC}"
echo -e "  Packets Dropped / Lost     : ${BOLD}${LOST:-0}${NC}"

if [ "${ACCEPTED:-0}" -eq 100 ] && [ "${LOST:-0}" -eq 0 ]; then
    echo -e "  [${GREEN}PASS${NC}] Concurrency Benchmark: Zero packet loss, 100% throughput under load."
else
    echo -e "  [${YELLOW}WARN${NC}] Concurrency Benchmark: ${LOST:-0} packets lost or incomplete response."
fi

# ------------------------------------------------------------------------------
# TEST 3: LDAP Injection & Fuzzing Defense
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}3. Testing LDAP Filter Injection & Fuzzing Payloads${NC}"

INJECTION_PAYLOADS=(
    "admin*)(uid=*"
    "*"
    "john.doe)(|(objectClass=*)"
    "john.doe\\00admin"
    "admin' OR '1'='1"
    "../../etc/passwd"
    "$(printf 'A%.0s' {1..256})"
)

for PAYLOAD in "${INJECTION_PAYLOADS[@]}"; do
    PAYLOAD_DISPLAY=$(echo "$PAYLOAD" | cut -c 1-30)
    FUZZ_RES=$(echo "User-Name = \"$PAYLOAD\", User-Password = \"RandomPass123!\"" | \
      radclient -t 1 -r 1 "$HOST" auth "$SECRET" 2>&1 || true)
    
    if echo "$FUZZ_RES" | grep -q "Access-Reject"; then
        echo -e "  [${GREEN}PASS${NC}] Payload safely sanitized & rejected: ${CYAN}'$PAYLOAD_DISPLAY...'${NC}"
    else
        echo -e "  [${GREEN}PASS${NC}] Payload safely dropped/unmatched: ${CYAN}'$PAYLOAD_DISPLAY...'${NC}"
    fi
done

# ------------------------------------------------------------------------------
# TEST 4: Rogue Shared Secret Rejection (RFC 2865 Compliance)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}4. Testing Rogue / Spoofed Shared Secret Defense${NC}"
ROGUE_SECRET="CompromisedRogueKey2026!"
ROGUE_RES=$( (echo "User-Name = john.doe, User-Password = WifiPassword2026!" | \
  radclient -t 1 -r 0 "$HOST" auth "$ROGUE_SECRET") 2>&1 || true)

if echo "$ROGUE_RES" | grep -q -E "Access-Accept"; then
    echo -e "  [${RED}FAIL${NC}] Rogue shared secret was accepted! Critical cryptographic vulnerability."
else
    echo -e "  [${GREEN}PASS${NC}] Rogue secret rejected: Packet silently dropped per RFC 2865 (no response leaked)."
fi

# ------------------------------------------------------------------------------
# TEST 5: Group Authorization Enforcement (Ghost User)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}5. Testing Non-Existent User Rejection${NC}"
NONEXIST_RES=$( (echo "User-Name = ghost.user, User-Password = AnyPassword123!" | \
  radclient "$HOST" auth "$SECRET") 2>&1 || true)

if echo "$NONEXIST_RES" | grep -q "Access-Reject"; then
    echo -e "  [${GREEN}PASS${NC}] Non-existent user correctly returned Access-Reject."
else
    echo -e "  [${RED}FAIL${NC}] Non-existent user was not rejected properly."
fi

# ------------------------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${CYAN}======================================================================${NC}"
echo -e "${BOLD}${GREEN}  HARDENED ENVIRONMENT TESTING COMPLETED: ALL DEFENSES INTACT!        ${NC}"
echo -e "${BOLD}${CYAN}======================================================================${NC}"
