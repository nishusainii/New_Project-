#!/usr/bin/env bash
# =============================================================================
# 01_dual_node_shutdown.sh — Scenario 1: 2-Node Hardware Shutdown Test
# Cluster: 10.31.6.172 | Tests quorum loss & HA VM failover behavior
# =============================================================================
set -uo pipefail

CLUSTER_IP="10.31.6.172"
SSH_PASS="cybe6@cluster"
SSH_USER="root"
RESULTS_DIR="$(dirname "$0")/results"
LOG_DIR="$(dirname "$0")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULT_FILE="$RESULTS_DIR/scenario_01_dual_shutdown_${TIMESTAMP}.json"
LOG_FILE="$LOG_DIR/scenario_01_${TIMESTAMP}.log"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

mkdir -p "$RESULTS_DIR" "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

log()    { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
ok()     { echo -e "${GREEN}[✔] $*${NC}"; }
warn()   { echo -e "${YELLOW}[⚠] $*${NC}"; }
fail()   { echo -e "${RED}[✘] $*${NC}"; }
timer()  { echo -e "${BLUE}[⏱] $*${NC}"; }
header() { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${NC}"; \
           echo -e "${BOLD}${CYAN}  $*${NC}"; \
           echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}\n"; }

ssh_cmd() {
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no \
        -o ConnectTimeout=15 "${SSH_USER}@${CLUSTER_IP}" "$@" 2>/dev/null
}

ssh_node() {
    local ip="$1"; shift
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no \
        -o ConnectTimeout=15 "${SSH_USER}@${ip}" "$@" 2>/dev/null
}

now_epoch() { date +%s; }
elapsed()   { echo $(( $(now_epoch) - $1 )); }

# ── Discover Cluster Nodes ────────────────────────────────────────────────────
get_node_ips() {
    header "Discovering Cluster Nodes"
    # Get node names and IPs from cluster
    NODE_DATA=$(ssh_cmd "pvesh get /cluster/status --output-format json 2>/dev/null | \
        jq -r '.[] | select(.type==\"node\") | .name + \":\" + (.ip // \"unknown\")'")
    
    if [ -z "$NODE_DATA" ]; then
        # Fallback: scan /etc/hosts on cluster
        NODE_DATA=$(ssh_cmd "cat /etc/hosts 2>/dev/null | grep -v '^#' | grep -v localhost | awk '{print \$2\":\"\$1}' | head -10")
    fi
    
    log "Raw node data: $NODE_DATA"
    
    # Also try corosync for IPs
    COROSYNC_NODES=$(ssh_cmd "corosync-cfgtool -s 2>/dev/null | grep 'ip =' | awk '{print \$NF}'" || echo "")
    log "Corosync IPs: $COROSYNC_NODES"
    
    # Get all node IPs (excluding management node which we use to SSH in)
    ALL_NODE_IPS=$(ssh_cmd "pvecm nodes 2>/dev/null | grep -v 'Nodeid' | awk '{print \$3}' | grep -v '^0$'" || echo "")
    log "All node IPs from pvecm: $ALL_NODE_IPS"
    
    # Map hostnames to IPs via /etc/hosts
    MANAGEMENT_NODE=$(ssh_cmd "hostname 2>/dev/null")
    log "Management node (we are connected through): $MANAGEMENT_NODE"
    
    # Get IPs of all nodes except management
    TARGET_NODES=$(ssh_cmd "pvecm nodes 2>/dev/null | grep -v 'Nodeid\|Name' | grep -v 'local\|^\s*$'" | head -5)
    log "Target nodes: $TARGET_NODES"
}

# ── Record VM Baseline ────────────────────────────────────────────────────────
record_vm_baseline() {
    header "Recording VM Baseline Before Shutdown"
    VM_BASELINE=$(ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | \
        jq '[.[] | select(.status==\"running\") | {vmid:.vmid, name:.name, node:.node, status:.status}]'")
    log "Running VMs (baseline):"
    echo "$VM_BASELINE" | jq -r '.[] | "  VM \(.vmid) [\(.name)] → \(.node) — \(.status)"' 2>/dev/null || echo "  (none running)"
    VM_COUNT=$(echo "$VM_BASELINE" | jq 'length' 2>/dev/null || echo "0")
    log "Total running VMs: $VM_COUNT"
}

# ── Ceph Baseline ─────────────────────────────────────────────────────────────
record_ceph_baseline() {
    header "Ceph Status Before Shutdown"
    ssh_cmd "ceph -s 2>&1"
    CEPH_PRE=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNKNOWN")
    log "Ceph health before: $CEPH_PRE"
}

# ── Shutdown Target Nodes ─────────────────────────────────────────────────────
shutdown_two_nodes() {
    header "SCENARIO 1 — Initiating 2-Node Hardware Shutdown"

    warn "═══════════════════════════════════════════"
    warn "  ⚠  ABOUT TO SHUT DOWN 2 CLUSTER NODES  ⚠"
    warn "═══════════════════════════════════════════"
    echo ""
    echo -e "${YELLOW}This will cause quorum loss and VM disruption.${NC}"
    echo -n "Type 'CONFIRM' to proceed: "
    read -r CONFIRM
    if [ "$CONFIRM" != "CONFIRM" ]; then
        fail "Aborted by user."
        exit 1
    fi

    # Get the two non-management nodes
    log "Fetching node list from cluster..."
    
    # Get all nodes with their IP and status
    NODE_JSON=$(ssh_cmd "pvesh get /cluster/status --output-format json 2>/dev/null | jq -r '.[] | select(.type==\"node\") | \"\(.name) \(.ip // \"unknown\") \(.online)\"'" || echo "")
    
    log "All cluster nodes:"
    echo "$NODE_JSON"
    
    # Get nodes to shut down (all except the one we're SSHing into)
    MGMT_HOST=$(ssh_cmd "hostname")
    log "Management/gateway node: $MGMT_HOST"
    
    # Identify 2 shutdown targets
    SHUTDOWN_NODE1=""
    SHUTDOWN_NODE2=""
    SHUTDOWN_IP1=""
    SHUTDOWN_IP2=""
    
    while IFS= read -r line; do
        NAME=$(echo "$line" | awk '{print $1}')
        IP=$(echo "$line" | awk '{print $2}')
        ONLINE=$(echo "$line" | awk '{print $3}')
        if [ "$NAME" != "$MGMT_HOST" ] && [ "$ONLINE" = "1" ]; then
            if [ -z "$SHUTDOWN_NODE1" ]; then
                SHUTDOWN_NODE1="$NAME"
                SHUTDOWN_IP1="$IP"
            elif [ -z "$SHUTDOWN_NODE2" ]; then
                SHUTDOWN_NODE2="$NAME"
                SHUTDOWN_IP2="$IP"
            fi
        fi
    done <<< "$NODE_JSON"

    if [ -z "$SHUTDOWN_NODE1" ] || [ -z "$SHUTDOWN_NODE2" ]; then
        fail "Could not identify 2 non-management nodes. Cluster may have <3 nodes."
        log "Attempting fallback: get node IPs from pvecm..."
        ALL_IPS=$(ssh_cmd "pvecm nodes 2>/dev/null | awk 'NR>2{print \$4}'" | grep -v "$CLUSTER_IP" | head -2)
        log "Fallback IPs: $ALL_IPS"
        
        SHUTDOWN_IP1=$(echo "$ALL_IPS" | sed -n '1p')
        SHUTDOWN_IP2=$(echo "$ALL_IPS" | sed -n '2p')
        SHUTDOWN_NODE1="node2"
        SHUTDOWN_NODE2="node3"
    fi

    log "▶ Node 1 to shutdown: $SHUTDOWN_NODE1 ($SHUTDOWN_IP1)"
    log "▶ Node 2 to shutdown: $SHUTDOWN_NODE2 ($SHUTDOWN_IP2)"

    # ── Record T0 ──────────────────────────────────────────────────────────────
    T0=$(now_epoch)
    T0_STR=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    log "T0 = $T0_STR — Initiating simultaneous shutdown"

    # Shutdown both nodes simultaneously (background)
    log "Issuing poweroff on $SHUTDOWN_NODE1 ($SHUTDOWN_IP1)..."
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "${SSH_USER}@${SHUTDOWN_IP1}" "nohup poweroff -f &>/dev/null &" 2>/dev/null &
    PID1=$!

    log "Issuing poweroff on $SHUTDOWN_NODE2 ($SHUTDOWN_IP2)..."
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
        "${SSH_USER}@${SHUTDOWN_IP2}" "nohup poweroff -f &>/dev/null &" 2>/dev/null &
    PID2=$!

    wait $PID1 $PID2 2>/dev/null || true
    ok "Shutdown commands issued to both nodes"

    # ── Monitor ─────────────────────────────────────────────────────────────
    T_QUORUM_LOST=""
    T_FENCE_TRIGGERED=""
    T_VM_RESTARTED=""
    T_CEPH_DEGRADED=""

    header "Monitoring Cluster Recovery"
    log "Polling every 10 seconds for up to 15 minutes..."
    echo ""

    PREV_STATUS=""
    for i in $(seq 1 90); do
        sleep 10
        SECS=$(elapsed $T0)
        MINS=$(( SECS / 60 ))

        CLUSTER_STATUS=$(ssh_cmd "pvecm status 2>&1" || echo "SSH_FAILED")
        CEPH_STATUS=$(ssh_cmd "ceph health 2>/dev/null" || echo "CEPH_UNKNOWN")
        VM_STATUS=$(ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | jq '[.[] | select(.status==\"running\")] | length'" || echo "0")

        echo -e "${BLUE}┌─── T+${MINS}m${SECS}s ─────────────────────────────────────────────┐${NC}"
        echo -e "${BLUE}│${NC} Cluster: $(echo "$CLUSTER_STATUS" | head -3 | tr '\n' ' ' | cut -c1-60)"
        echo -e "${BLUE}│${NC} Ceph:    $CEPH_STATUS"
        echo -e "${BLUE}│${NC} Running VMs: $VM_STATUS"
        echo -e "${BLUE}└───────────────────────────────────────────────────────────┘${NC}"

        # Detect quorum loss
        if [ -z "$T_QUORUM_LOST" ] && echo "$CLUSTER_STATUS" | grep -qi "no quorum\|quorum.*0\|SSH_FAILED"; then
            T_QUORUM_LOST=$(elapsed $T0)
            timer "T+${T_QUORUM_LOST}s — QUORUM LOST detected"
        fi

        # Detect fence trigger
        if [ -z "$T_FENCE_TRIGGERED" ] && echo "$CLUSTER_STATUS" | grep -qi "fence\|isolat"; then
            T_FENCE_TRIGGERED=$(elapsed $T0)
            timer "T+${T_FENCE_TRIGGERED}s — HA FENCE triggered"
        fi

        # Detect Ceph degradation
        if [ -z "$T_CEPH_DEGRADED" ] && echo "$CEPH_STATUS" | grep -qi "HEALTH_WARN\|HEALTH_ERR\|degraded\|OSD_DOWN"; then
            T_CEPH_DEGRADED=$(elapsed $T0)
            timer "T+${T_CEPH_DEGRADED}s — Ceph degraded"
        fi

        # Detect VM restart on survivor
        if [ -z "$T_VM_RESTARTED" ] && [ "$VM_STATUS" = "$VM_COUNT" ] 2>/dev/null; then
            T_VM_RESTARTED=$(elapsed $T0)
            timer "T+${T_VM_RESTARTED}s — VMs restored ($VM_STATUS/$VM_COUNT)"
        fi
    done

    T_TOTAL_FAIL=$(elapsed $T0)
    timer "Monitoring phase: ${T_TOTAL_FAIL}s total"

    # ── Power Nodes Back On ────────────────────────────────────────────────────
    header "Recovery Phase — Restoring Nodes"
    warn "If nodes do NOT auto-power-on, you must physically/manually power them on."
    warn "Waiting 30 seconds then checking if nodes are back online..."
    sleep 30

    T_RECOVERY_START=$(now_epoch)
    for attempt in $(seq 1 12); do
        sleep 15
        SECS_R=$(elapsed $T_RECOVERY_START)
        NODE1_ONLINE=$(ping -c 1 -W 3 "$SHUTDOWN_IP1" &>/dev/null && echo "UP" || echo "DOWN")
        NODE2_ONLINE=$(ping -c 1 -W 3 "$SHUTDOWN_IP2" &>/dev/null && echo "UP" || echo "DOWN")
        CEPH_POST=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNREACHABLE")
        
        log "Recovery T+${SECS_R}s | $SHUTDOWN_NODE1: $NODE1_ONLINE | $SHUTDOWN_NODE2: $NODE2_ONLINE | Ceph: $CEPH_POST"
        
        if [ "$NODE1_ONLINE" = "UP" ] && [ "$NODE2_ONLINE" = "UP" ] && echo "$CEPH_POST" | grep -q "HEALTH_OK"; then
            T_FULL_RECOVERY=$(elapsed $T0)
            ok "FULL RECOVERY ACHIEVED at T+${T_FULL_RECOVERY}s"
            break
        fi
    done

    T_TOTAL=$(elapsed $T0)
}

# ── Generate Results ──────────────────────────────────────────────────────────
save_results() {
    header "Saving Scenario 1 Results"
    cat > "$RESULT_FILE" << EOF
{
  "scenario": "01_dual_node_hardware_shutdown",
  "timestamp_start": "$T0_STR",
  "cluster_ip": "$CLUSTER_IP",
  "nodes_shutdown": ["$SHUTDOWN_NODE1", "$SHUTDOWN_NODE2"],
  "timings": {
    "t_quorum_lost_sec":      ${T_QUORUM_LOST:-null},
    "t_fence_triggered_sec":  ${T_FENCE_TRIGGERED:-null},
    "t_ceph_degraded_sec":    ${T_CEPH_DEGRADED:-null},
    "t_vm_restarted_sec":     ${T_VM_RESTARTED:-null},
    "t_full_recovery_sec":    ${T_FULL_RECOVERY:-null},
    "t_total_test_sec":       $T_TOTAL
  },
  "result": "$([ -n "${T_FULL_RECOVERY:-}" ] && echo 'PASS' || echo 'PARTIAL')",
  "log_file": "$LOG_FILE"
}
EOF
    ok "Results saved to $RESULT_FILE"
    cat "$RESULT_FILE" | jq . 2>/dev/null || cat "$RESULT_FILE"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}${RED}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${RED}║   SCENARIO 1: DUAL NODE HARDWARE SHUTDOWN        ║${NC}"
    echo -e "${BOLD}${RED}║   Target Cluster: $CLUSTER_IP                  ║${NC}"
    echo -e "${BOLD}${RED}╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    get_node_ips
    record_vm_baseline
    record_ceph_baseline
    shutdown_two_nodes
    save_results

    echo ""
    echo -e "${BOLD}${GREEN}  Scenario 1 Complete. Results: $RESULT_FILE${NC}"
    echo ""
}

main "$@"
