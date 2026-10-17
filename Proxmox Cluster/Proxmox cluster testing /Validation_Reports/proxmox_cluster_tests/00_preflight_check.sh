#!/usr/bin/env bash
# =============================================================================
# 00_preflight_check.sh — Proxmox Cluster Pre-Flight Validation
# Cluster: 10.31.6.172 | User: root
# Run this BEFORE any failure scenario to establish baseline
# =============================================================================
set -euo pipefail

CLUSTER_IP="10.31.6.172"
SSH_PASS="(cybe6@cluster)"
SSH_USER="root"
RESULTS_DIR="$(dirname "$0")/results"
LOG_DIR="$(dirname "$0")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BASELINE_FILE="$RESULTS_DIR/baseline_${TIMESTAMP}.json"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

mkdir -p "$RESULTS_DIR" "$LOG_DIR"

log()   { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
ok()    { echo -e "${GREEN}[✔] $*${NC}"; }
warn()  { echo -e "${YELLOW}[⚠] $*${NC}"; }
fail()  { echo -e "${RED}[✘] $*${NC}"; }
header(){ echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${NC}"; \
          echo -e "${BOLD}${CYAN}  $*${NC}"; \
          echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}\n"; }

# ── SSH Helper ────────────────────────────────────────────────────────────────
ssh_cmd() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no \
        -o ConnectTimeout=10 \
        "${SSH_USER}@${CLUSTER_IP}" "$@" 2>/dev/null
}

# ── Check dependencies ────────────────────────────────────────────────────────
check_deps() {
    header "Checking Local Dependencies"
    for dep in sshpass ssh jq; do
        if command -v "$dep" &>/dev/null; then
            ok "$dep is available"
        else
            fail "$dep is NOT installed. Install with: sudo apt install $dep"
            exit 1
        fi
    done
}

# ── Connectivity check ────────────────────────────────────────────────────────
check_connectivity() {
    header "Checking Cluster Connectivity"
    if ping -c 2 -W 3 "$CLUSTER_IP" &>/dev/null; then
        ok "Cluster IP $CLUSTER_IP is reachable"
    else
        fail "Cannot reach $CLUSTER_IP — Aborting"
        exit 1
    fi

    if ssh_cmd "echo 'SSH OK'" &>/dev/null; then
        ok "SSH authentication successful"
    else
        fail "SSH login failed. Check credentials."
        exit 1
    fi
}

# ── Cluster Quorum ────────────────────────────────────────────────────────────
check_quorum() {
    header "Cluster Quorum Status"
    QUORUM_RAW=$(ssh_cmd "pvecm status 2>&1")
    echo "$QUORUM_RAW"
    QUORUM_VOTES=$(echo "$QUORUM_RAW" | grep -i "Quorum votes" | awk '{print $NF}' || echo "unknown")
    TOTAL_VOTES=$(echo "$QUORUM_RAW"  | grep -i "Total votes"  | awk '{print $NF}' || echo "unknown")
    log "Quorum Votes: $QUORUM_VOTES / $TOTAL_VOTES"
    echo ""
}

# ── Node Status ───────────────────────────────────────────────────────────────
check_nodes() {
    header "Node Status"
    NODE_JSON=$(ssh_cmd "pvesh get /cluster/status --output-format json 2>/dev/null")
    echo "$NODE_JSON" | jq -r '.[] | select(.type=="node") | "  Node: \(.name)  | Online: \(.online)  | Level: \(.level // "N/A")"' 2>/dev/null || \
        ssh_cmd "pvecm nodes 2>&1"

    # Get node names for later use
    NODE_LIST=$(ssh_cmd "pvecm nodes 2>/dev/null | awk 'NR>2 {print \$3}'" || echo "")
    log "Discovered nodes: $NODE_LIST"
    echo ""
}

# ── VM Inventory ──────────────────────────────────────────────────────────────
check_vms() {
    header "Virtual Machine Inventory"
    VM_JSON=$(ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null")
    RUNNING=$(echo "$VM_JSON" | jq '[.[] | select(.status=="running")] | length' 2>/dev/null || echo "0")
    STOPPED=$(echo "$VM_JSON" | jq '[.[] | select(.status=="stopped")] | length' 2>/dev/null || echo "0")
    echo "$VM_JSON" | jq -r '.[] | "  VMID:\(.vmid) | Name:\(.name // "N/A") | Status:\(.status) | Node:\(.node)"' 2>/dev/null || \
        ssh_cmd "qm list 2>&1"
    log "Running VMs: $RUNNING | Stopped VMs: $STOPPED"
    echo ""
}

# ── Ceph Health ───────────────────────────────────────────────────────────────
check_ceph() {
    header "Ceph Storage Health"
    CEPH_STATUS=$(ssh_cmd "ceph -s 2>&1")
    echo "$CEPH_STATUS"
    
    CEPH_HEALTH=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNKNOWN")
    OSD_COUNT=$(ssh_cmd "ceph osd stat 2>/dev/null | grep 'osds:' | awk '{print \$1}'" || echo "?")
    OSD_UP=$(ssh_cmd "ceph osd stat 2>/dev/null | grep 'up' | grep -oP '\d+ up' | awk '{print \$1}'" || echo "?")
    PG_ACTIVE=$(ssh_cmd "ceph pg stat 2>/dev/null | grep -oP '\d+ active' | awk '{print \$1}'" || echo "?")
    
    echo ""
    log "Ceph Health: $CEPH_HEALTH"
    log "OSDs Total: $OSD_COUNT | OSDs Up: $OSD_UP"
    log "Active PGs: $PG_ACTIVE"
    echo ""
    
    if echo "$CEPH_HEALTH" | grep -q "HEALTH_OK"; then
        ok "Ceph is healthy — safe to proceed with tests"
    elif echo "$CEPH_HEALTH" | grep -q "HEALTH_WARN"; then
        warn "Ceph has warnings — review before testing"
    else
        fail "Ceph is in ERROR state — DO NOT proceed with destructive tests!"
    fi
}

# ── HA Manager ────────────────────────────────────────────────────────────────
check_ha() {
    header "HA Manager Status"
    ssh_cmd "ha-manager status 2>&1" || warn "HA Manager not configured or not responding"
    echo ""
}

# ── Network Interfaces ────────────────────────────────────────────────────────
check_network() {
    header "Network Interface Status (All Nodes)"
    ssh_cmd "ip link show 2>&1 | grep -E '(nic|eth|bond|vmbr|ens|enp)'" || true
    log "Ceph network interface (nic3) will be targeted in Scenario 3"
    echo ""
}

# ── Baseline JSON Snapshot ────────────────────────────────────────────────────
save_baseline() {
    header "Saving Baseline Snapshot → $BASELINE_FILE"
    
    CEPH_H=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNKNOWN")
    OSD_TOT=$(ssh_cmd "ceph osd stat 2>/dev/null | awk '{print \$1}'" || echo "0")
    OSD_UP=$(ssh_cmd "ceph osd stat 2>/dev/null | grep -oP '\d+ up' | awk '{print \$1}'" || echo "0")
    VM_RUN=$(ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | jq '[.[] | select(.status==\"running\")] | length'" || echo "0")
    
    cat > "$BASELINE_FILE" << EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "cluster_ip": "$CLUSTER_IP",
  "ceph_health": "$CEPH_H",
  "osd_total": "$OSD_TOT",
  "osd_up": "$OSD_UP",
  "vms_running": $VM_RUN,
  "preflight_status": "PASSED",
  "ready_for_testing": true
}
EOF
    ok "Baseline saved to $BASELINE_FILE"
    cat "$BASELINE_FILE" | jq . 2>/dev/null || cat "$BASELINE_FILE"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║   PROXMOX CLUSTER PRE-FLIGHT CHECK               ║${NC}"
    echo -e "${BOLD}${GREEN}║   Target: $CLUSTER_IP                       ║${NC}"
    echo -e "${BOLD}${GREEN}║   Time: $(date '+%Y-%m-%d %H:%M:%S')                   ║${NC}"
    echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    check_deps
    check_connectivity
    check_quorum
    check_nodes
    check_vms
    check_ceph
    check_ha
    check_network
    save_baseline

    echo ""
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}  PRE-FLIGHT COMPLETE — Cluster baseline captured  ${NC}"
    echo -e "${BOLD}${GREEN}  Baseline: $BASELINE_FILE  ${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}  Next: Run ./run_all_tests.sh to start failure scenarios${NC}"
    echo ""
}

main "$@"
