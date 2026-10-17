#!/usr/bin/env bash
# =============================================================================
# 03_ceph_network_outage.sh — Scenario 3: Full Ceph Network Outage Test
# Brings down the Ceph cluster network (nic3) on ALL nodes simultaneously
# Measures: OSD eviction time, PG degradation, VM I/O freeze, recovery timeline
# Cluster: 10.31.6.172
# =============================================================================
set -uo pipefail

CLUSTER_IP="10.31.6.172"
SSH_PASS="cybe6@cluster"
SSH_USER="root"
CEPH_IFACE="nic3"        # Ceph cluster network interface
RESULTS_DIR="$(dirname "$0")/results"
LOG_DIR="$(dirname "$0")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULT_FILE="$RESULTS_DIR/scenario_03_ceph_outage_${TIMESTAMP}.json"
LOG_FILE="$LOG_DIR/scenario_03_${TIMESTAMP}.log"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BLUE='\033[0;34m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'; NC='\033[0m'

mkdir -p "$RESULTS_DIR" "$LOG_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

log()     { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
ok()      { echo -e "${GREEN}[✔] $*${NC}"; }
warn()    { echo -e "${YELLOW}[⚠] $*${NC}"; }
fail()    { echo -e "${RED}[✘] $*${NC}"; }
timer()   { echo -e "${BLUE}[⏱] $*${NC}"; }
ceph_log(){ echo -e "${MAGENTA}[CEPH] $*${NC}"; }
header()  { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${NC}"; \
            echo -e "${BOLD}${CYAN}  $*${NC}"; \
            echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}\n"; }

ssh_cmd() {
    if [ -f "/tmp/proxmox_test_key" ]; then
        ssh -i /tmp/proxmox_test_key -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes "${SSH_USER}@${CLUSTER_IP}" "$@" 2>/dev/null
    else
        sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no \
            -o ConnectTimeout=15 "${SSH_USER}@${CLUSTER_IP}" "$@" 2>/dev/null
    fi
}

ssh_node() {
    local ip="$1"; shift
    if [ -f "/tmp/proxmox_test_key" ]; then
        ssh -i /tmp/proxmox_test_key -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes "${SSH_USER}@${ip}" "$@" 2>/dev/null
    else
        sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no \
            -o ConnectTimeout=10 "${SSH_USER}@${ip}" "$@" 2>/dev/null
    fi
}

now_epoch() { date +%s; }
elapsed()   { echo $(( $(now_epoch) - $1 )); }

# ── Discover All Node IPs ─────────────────────────────────────────────────────
discover_nodes() {
    header "Discovering All Cluster Nodes for Ceph Network Test"

    # Get all node IPs from cluster
    ALL_NODES_JSON=$(ssh_cmd "pvesh get /cluster/status --output-format json 2>/dev/null | \
        jq -r '.[] | select(.type==\"node\") | \"\(.name):\(.ip // \"unknown\"):\(.online)\"'" || echo "")
    
    log "Discovered nodes: $ALL_NODES_JSON"
    
    NODE_IPS=()
    NODE_NAMES=()

    while IFS= read -r line; do
        NAME=$(echo "$line" | cut -d: -f1)
        IP=$(echo "$line" | cut -d: -f2)
        ONLINE=$(echo "$line" | cut -d: -f3)
        if [ "$ONLINE" = "1" ] && [ "$IP" != "unknown" ]; then
            NODE_NAMES+=("$NAME")
            NODE_IPS+=("$IP")
            log "  → $NAME @ $IP"
        fi
    done <<< "$ALL_NODES_JSON"

    NODE_COUNT="${#NODE_IPS[@]}"
    log "Total online nodes: $NODE_COUNT"

    if [ "$NODE_COUNT" -lt 2 ]; then
        fail "Need at least 2 nodes for Ceph outage test. Found: $NODE_COUNT"
        exit 1
    fi
}

# ── Verify Ceph Interface Exists ──────────────────────────────────────────────
verify_ceph_interface() {
    header "Verifying Ceph Interface ($CEPH_IFACE) on All Nodes"
    
    for i in "${!NODE_IPS[@]}"; do
        IP="${NODE_IPS[$i]}"
        NAME="${NODE_NAMES[$i]}"
        IF_STATUS=$(ssh_node "$IP" "ip link show $CEPH_IFACE 2>&1 | head -1" || echo "NOT FOUND")
        
        if echo "$IF_STATUS" | grep -qi "state UP\|LOWER_UP"; then
            ok "$NAME ($IP): $CEPH_IFACE is UP"
        elif echo "$IF_STATUS" | grep -qi "does not exist\|NOT FOUND"; then
            fail "$NAME ($IP): $CEPH_IFACE NOT FOUND"
            warn "Available interfaces on $NAME:"
            ssh_node "$IP" "ip link show 2>&1 | grep '^[0-9]' | awk '{print \$2}'" || true
        else
            warn "$NAME ($IP): $CEPH_IFACE — $IF_STATUS"
        fi
    done
}

# ── Full Ceph Status Snapshot ─────────────────────────────────────────────────
ceph_snapshot() {
    local label="$1"
    header "Ceph Status Snapshot — $label"
    ssh_cmd "ceph -s 2>&1"
    ssh_cmd "ceph osd stat 2>&1"
    ssh_cmd "ceph pg stat 2>&1"
}

# ── Measure Ceph I/O Latency Before ──────────────────────────────────────────
measure_ceph_io() {
    header "Measuring Ceph I/O Baseline (rados bench)"
    log "Running 10-second write benchmark on Ceph pool..."
    POOL=$(ssh_cmd "ceph osd lspools 2>/dev/null | awk '{print \$2}' | grep -v 'rbd\|.mgr' | head -1" || echo "rbd")
    log "Using pool: $POOL"
    
    ssh_cmd "rados bench -p $POOL 10 write --no-cleanup 2>&1 | tail -10" || warn "rados bench not available or pool empty"
    ssh_cmd "rados bench -p $POOL 10 seq 2>&1 | tail -5" 2>/dev/null || true
    ssh_cmd "rados -p $POOL cleanup 2>/dev/null" || true
}

# ── Take Down Ceph Network on ALL Nodes ──────────────────────────────────────
take_down_ceph_network() {
    header "SCENARIO 3 — Bringing Down Ceph Network ($CEPH_IFACE) on ALL Nodes"

    warn "═════════════════════════════════════════════════════"
    warn "  ⚠  ABOUT TO DISABLE CEPH NETWORK ON ALL 3 NODES  ⚠"
    warn "  Interface: $CEPH_IFACE will be brought DOWN"
    warn "  This will cause ALL Ceph I/O to freeze immediately"
    warn "═════════════════════════════════════════════════════"
    echo ""
    if [ "${AUTO_CONFIRM:-0}" != "1" ]; then
        echo -n "Type 'CONFIRM' to proceed: "
        read -r CONFIRM
        if [ "$CONFIRM" != "CONFIRM" ]; then
            fail "Aborted."
            exit 1
        fi
    else
        log "AUTO_CONFIRM=1 set — proceeding with Ceph network outage"
    fi

    T0=$(now_epoch)
    T0_STR=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    log "Issuing 'ip link set $CEPH_IFACE down' on all nodes simultaneously..."

    for i in "${!NODE_IPS[@]}"; do
        IP="${NODE_IPS[$i]}"
        NAME="${NODE_NAMES[$i]}"
        # Schedule auto-restore in 3 minutes (safety fallback)
        ssh_node "$IP" "
            nohup bash -c 'sleep 180; ip link set $CEPH_IFACE up 2>/dev/null; \
                echo \"Auto-restored nic3 at \$(date)\" >> /tmp/ceph_restore.log' \
                > /tmp/ceph_auto_restore.log 2>&1 &
            ip link set $CEPH_IFACE down 2>&1
        " &>/dev/null &
        log "  → Sent DOWN command to $NAME ($IP)"
    done

    wait
    ok "Ceph network DOWN commands issued at T0 = $T0_STR"

    # ── Monitoring Loop ───────────────────────────────────────────────────────
    T_OSD_FIRST_DOWN=""
    T_ALL_OSDS_DOWN=""
    T_PG_INACTIVE=""
    T_IO_FROZEN=""
    T_VM_IO_BLOCK=""

    declare -A OSD_DOWN_TIMES

    header "Monitoring Ceph Degradation"
    log "Polling every 5 seconds for up to 5 minutes..."

    PREV_OSD_UP=999
    PREV_PG_ACT=999

    for i in $(seq 1 60); do
        sleep 5
        SECS=$(elapsed $T0)
        MINS=$(( SECS / 60 ))

        CEPH_H=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNREACHABLE")
        CEPH_OSD_STAT=$(ssh_cmd "ceph osd stat 2>/dev/null" || echo "UNREACHABLE")
        CEPH_PG_STAT=$(ssh_cmd "ceph pg stat 2>/dev/null" || echo "UNREACHABLE")
        
        OSD_UP_NOW=$(echo "$CEPH_OSD_STAT" | grep -oP '\d+ up' | awk '{print $1}' || echo "?")
        OSD_TOTAL=$(echo "$CEPH_OSD_STAT" | awk '{print $1}' || echo "?")
        PG_ACT_NOW=$(echo "$CEPH_PG_STAT" | grep -oP '\d+ active' | awk '{print $1}' || echo "?")
        PG_TOTAL=$(echo "$CEPH_PG_STAT" | grep -oP '\d+ pgs' | awk '{print $1}' || echo "?")

        echo -e "${MAGENTA}┌─── CEPH T+${MINS}m${SECS}s ──────────────────────────────────────────┐${NC}"
        echo -e "${MAGENTA}│${NC} Health: $CEPH_H"
        echo -e "${MAGENTA}│${NC} OSDs: $OSD_UP_NOW up / $OSD_TOTAL total"
        echo -e "${MAGENTA}│${NC} PGs: $PG_ACT_NOW active / $PG_TOTAL total"
        echo -e "${MAGENTA}└────────────────────────────────────────────────────────────┘${NC}"

        # First OSD going down
        if [ -z "$T_OSD_FIRST_DOWN" ] && [ "$OSD_UP_NOW" != "?" ] && [ "$OSD_UP_NOW" -lt "$PREV_OSD_UP" ] 2>/dev/null; then
            T_OSD_FIRST_DOWN=$(elapsed $T0)
            timer "T+${T_OSD_FIRST_DOWN}s — FIRST OSD went DOWN (was $PREV_OSD_UP, now $OSD_UP_NOW)"
        fi

        # All OSDs down
        if [ -z "$T_ALL_OSDS_DOWN" ] && echo "$CEPH_H" | grep -qi "HEALTH_ERR\|all osd\|no osd"; then
            T_ALL_OSDS_DOWN=$(elapsed $T0)
            timer "T+${T_ALL_OSDS_DOWN}s — ALL/MOST OSDs down"
        fi

        # PGs inactive
        if [ -z "$T_PG_INACTIVE" ] && [ "$PG_ACT_NOW" != "?" ] && [ "$PG_ACT_NOW" -lt "$PREV_PG_ACT" ] 2>/dev/null; then
            T_PG_INACTIVE=$(elapsed $T0)
            timer "T+${T_PG_INACTIVE}s — PGs becoming inactive ($PG_ACT_NOW active)"
        fi

        PREV_OSD_UP="${OSD_UP_NOW:-999}"
        PREV_PG_ACT="${PG_ACT_NOW:-999}"

        # Fault captured: if OSDs down or PGs inactive detected, wait to hit 45s, then proceed
        if [ -n "$T_OSD_FIRST_DOWN" ] && [ "$SECS" -ge 45 ]; then
            timer "Fault state confirmed ($SECS s) — proceeding to restoration"
            break
        fi

        if [ "$SECS" -ge 60 ]; then
            timer "60s fault window reached — proceeding to restoration"
            break
        fi
    done

    T_FAULT_DURATION=$(elapsed $T0)
    timer "Total fault duration: ${T_FAULT_DURATION}s"
}

# ── Restore Ceph Network ──────────────────────────────────────────────────────
restore_ceph_network() {
    header "Restoring Ceph Network ($CEPH_IFACE) on All Nodes"

    T_RESTORE=$(now_epoch)
    log "Bringing $CEPH_IFACE UP on all nodes..."

    for i in "${!NODE_IPS[@]}"; do
        IP="${NODE_IPS[$i]}"
        NAME="${NODE_NAMES[$i]}"
        ssh_node "$IP" "ip link set $CEPH_IFACE up 2>&1; echo '$CEPH_IFACE restored on $NAME'" 2>/dev/null &
        log "  → Sent UP command to $NAME ($IP)"
    done
    wait

    ok "Ceph network restored — monitoring recovery..."

    # ── Recovery Monitoring ───────────────────────────────────────────────────
    T_OSD_FIRST_UP=""
    T_ALL_OSDS_UP=""
    T_PG_CLEAN=""
    T_IO_RESTORED=""
    T_FULL_RECOVERY=""

    EXPECTED_OSDs=$(ssh_cmd "ceph osd stat 2>/dev/null | awk '{print \$1}'" || echo "?")

    for attempt in $(seq 1 60); do
        sleep 10
        SECS_R=$(elapsed $T_RESTORE)
        SECS_TOTAL=$(elapsed $T0)

        CEPH_H=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNREACHABLE")
        OSD_STAT=$(ssh_cmd "ceph osd stat 2>/dev/null" || echo "")
        PG_STAT=$(ssh_cmd "ceph pg stat 2>/dev/null" || echo "")

        OSD_UP=$(echo "$OSD_STAT" | grep -oP '\d+ up' | awk '{print $1}' || echo "0")
        OSD_TOT=$(echo "$OSD_STAT" | awk '{print $1}' || echo "?")
        PG_ACT=$(echo "$PG_STAT" | grep -oP '\d+ active' | awk '{print $1}' || echo "0")
        PG_CLEAN=$(echo "$PG_STAT" | grep -oP '\d+ clean' | awk '{print $1}' || echo "0")
        PG_TOTAL=$(echo "$PG_STAT" | grep -oP '\d+ pgs' | awk '{print $1}' || echo "?")

        echo -e "${GREEN}┌─── RECOVERY T+${SECS_R}s (Total: T+${SECS_TOTAL}s) ────────────────────┐${NC}"
        echo -e "${GREEN}│${NC} Ceph Health: $CEPH_H"
        echo -e "${GREEN}│${NC} OSDs Up: $OSD_UP / $OSD_TOT"
        echo -e "${GREEN}│${NC} PGs Active: $PG_ACT | Clean: $PG_CLEAN / $PG_TOTAL"
        echo -e "${GREEN}└────────────────────────────────────────────────────────────┘${NC}"

        # First OSD re-joining
        if [ -z "$T_OSD_FIRST_UP" ] && [ "$OSD_UP" != "0" ] && [ "$OSD_UP" != "" ]; then
            T_OSD_FIRST_UP=$(elapsed $T0)
            timer "T+${T_OSD_FIRST_UP}s — First OSD back UP ($OSD_UP up)"
        fi

        # All OSDs back
        if [ -z "$T_ALL_OSDS_UP" ] && [ "$OSD_UP" = "$OSD_TOT" ] && [ "$OSD_TOT" != "?" ]; then
            T_ALL_OSDS_UP=$(elapsed $T0)
            timer "T+${T_ALL_OSDS_UP}s — ALL OSDs UP ($OSD_UP / $OSD_TOT)"
        fi

        # PGs clean
        if [ -z "$T_PG_CLEAN" ] && [ "$PG_CLEAN" = "$PG_TOTAL" ] && [ "$PG_TOTAL" != "?" ]; then
            T_PG_CLEAN=$(elapsed $T0)
            timer "T+${T_PG_CLEAN}s — ALL PGs CLEAN ($PG_CLEAN / $PG_TOTAL)"
        fi

        # Ceph fully healthy
        if echo "$CEPH_H" | grep -q "HEALTH_OK"; then
            T_FULL_RECOVERY=$(elapsed $T0)
            T_RECOVERY_FROM_RESTORE=$SECS_R
            ok "CEPH FULLY RECOVERED at T+${T_FULL_RECOVERY}s (from network restore: +${SECS_R}s)"
            break
        fi
    done

    T_TOTAL=$(elapsed $T0)
    warn "Note: Total test duration = ${T_TOTAL}s"
}

# ── Save Results ──────────────────────────────────────────────────────────────
save_results() {
    header "Saving Scenario 3 Results"

    FAULT_DURATION="${T_FAULT_DURATION:-null}"
    
    cat > "$RESULT_FILE" << EOF
{
  "scenario": "03_full_ceph_network_outage",
  "timestamp_start": "$T0_STR",
  "cluster_ip": "$CLUSTER_IP",
  "ceph_interface": "$CEPH_IFACE",
  "nodes_affected": ${#NODE_IPS[@]},
  "fault_phase": {
    "t_first_osd_down_sec":   ${T_OSD_FIRST_DOWN:-null},
    "t_all_osds_down_sec":    ${T_ALL_OSDS_DOWN:-null},
    "t_pg_inactive_sec":      ${T_PG_INACTIVE:-null},
    "fault_duration_sec":     $FAULT_DURATION
  },
  "recovery_phase": {
    "t_first_osd_up_sec":     ${T_OSD_FIRST_UP:-null},
    "t_all_osds_up_sec":      ${T_ALL_OSDS_UP:-null},
    "t_pgs_clean_sec":        ${T_PG_CLEAN:-null},
    "t_full_recovery_sec":    ${T_FULL_RECOVERY:-null},
    "t_recovery_from_restore_sec": ${T_RECOVERY_FROM_RESTORE:-null}
  },
  "result": "$([ -n "${T_FULL_RECOVERY:-}" ] && echo 'PASS' || echo 'PARTIAL')",
  "t_total_test_sec": $T_TOTAL,
  "log_file": "$LOG_FILE"
}
EOF
    cp -f "$RESULT_FILE" "$RESULTS_DIR/scenario_03_ceph_outage_FINAL.json"
    ok "Results saved to $RESULT_FILE and $RESULTS_DIR/scenario_03_ceph_outage_FINAL.json"
    cat "$RESULT_FILE" | jq . 2>/dev/null || cat "$RESULT_FILE"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}${MAGENTA}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${MAGENTA}║   SCENARIO 3: FULL CEPH NETWORK OUTAGE           ║${NC}"
    echo -e "${BOLD}${MAGENTA}║   Interface: $CEPH_IFACE on ALL nodes                  ║${NC}"
    echo -e "${BOLD}${MAGENTA}╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    discover_nodes
    verify_ceph_interface
    ceph_snapshot "PRE-OUTAGE BASELINE"
    measure_ceph_io
    take_down_ceph_network
    restore_ceph_network
    ceph_snapshot "POST-RECOVERY FINAL"
    save_results

    echo ""
    echo -e "${BOLD}${GREEN}  Scenario 3 Complete. Results: $RESULT_FILE${NC}"
    echo ""
}

main "$@"
