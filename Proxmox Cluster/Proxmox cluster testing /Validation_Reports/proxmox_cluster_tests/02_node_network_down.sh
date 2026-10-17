#!/usr/bin/env bash
# =============================================================================
# 02_node_network_down.sh — Scenario 2: Single Node Network Isolation Test
# Simulates complete network failure on one node using iptables
# Cluster: 10.31.6.172 | Measures HA fence time, VM failover time
# =============================================================================
set -uo pipefail

CLUSTER_IP="10.31.6.172"
SSH_PASS="cybe6@cluster"
SSH_USER="root"
RESULTS_DIR="$(dirname "$0")/results"
LOG_DIR="$(dirname "$0")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
RESULT_FILE="$RESULTS_DIR/scenario_02_network_down_${TIMESTAMP}.json"
LOG_FILE="$LOG_DIR/scenario_02_${TIMESTAMP}.log"

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
            -o ConnectTimeout=15 "${SSH_USER}@${ip}" "$@" 2>/dev/null
    fi
}

now_epoch() { date +%s; }
elapsed()   { echo $(( $(now_epoch) - $1 )); }

# ── Discover & Select Target Node ────────────────────────────────────────────
select_target_node() {
    header "Selecting Target Node for Network Isolation"

    MGMT_HOST=$(ssh_cmd "hostname")
    log "Management node (running tests from): $MGMT_HOST"

    NODE_JSON=$(ssh_cmd "pvesh get /cluster/status --output-format json 2>/dev/null | \
        jq -r '.[] | select(.type==\"node\") | \"\(.name) \(.ip // \"unknown\") \(.online)\"'" || echo "")
    
    log "Cluster nodes:"
    echo "$NODE_JSON"

    # Pick target node (allow TARGET_NODE override or pick first non-management node with VMs)
    TARGET_NAME="${TARGET_NODE:-}"
    TARGET_IP=""

    if [ -n "$TARGET_NAME" ]; then
        TARGET_IP=$(echo "$NODE_JSON" | grep "^$TARGET_NAME " | awk '{print $2}')
    fi

    if [ -z "$TARGET_NAME" ] || [ -z "$TARGET_IP" ]; then
        # Default to prox24 (which hosts VMs) or first online non-mgmt node
        while IFS= read -r line; do
            NAME=$(echo "$line" | awk '{print $1}')
            IP=$(echo "$line" | awk '{print $2}')
            ONLINE=$(echo "$line" | awk '{print $3}')
            if [ "$NAME" != "$MGMT_HOST" ] && [ "$ONLINE" = "1" ] && [ -z "$TARGET_NAME" ]; then
                TARGET_NAME="$NAME"
                TARGET_IP="$IP"
            fi
        done <<< "$NODE_JSON"
    fi

    if [ -z "$TARGET_NAME" ]; then
        fail "Cannot auto-detect target node IP."
        echo -n "Enter target node IP manually: "
        read -r TARGET_IP
        TARGET_NAME="manual_node"
    fi

    ok "Target node for isolation: $TARGET_NAME ($TARGET_IP)"
    log "VMs on target node:"
    ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | \
        jq -r '.[] | select(.node==\"'$TARGET_NAME'\" and .status==\"running\") | \"  VM \(.vmid) [\(.name)] on \(.node)\"'" 2>/dev/null || \
        ssh_node "$TARGET_IP" "qm list 2>&1" || true
}

# ── Pre-Test Baselines ────────────────────────────────────────────────────────
record_baselines() {
    header "Recording Pre-Test Baselines"

    VMS_PRE=$(ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | \
        jq '[.[] | select(.status==\"running\") | {vmid:.vmid, name:.name, node:.node}]'")
    VM_COUNT=$(echo "$VMS_PRE" | jq 'length' 2>/dev/null || echo "0")
    log "Running VMs: $VM_COUNT"
    echo "$VMS_PRE" | jq -r '.[] | "  VM \(.vmid) [\(.name)] → \(.node)"' 2>/dev/null || true

    CEPH_PRE=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNKNOWN")
    log "Ceph health: $CEPH_PRE"

    HA_PRE=$(ssh_cmd "ha-manager status 2>/dev/null" || echo "N/A")
    log "HA Manager status captured"

    # Get VMs specifically on target node
    VMS_ON_TARGET=$(ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | \
        jq '[.[] | select(.node==\"'$TARGET_NAME'\" and .status==\"running\") | .vmid]'" || echo "[]")
    log "VMs on target ($TARGET_NAME): $VMS_ON_TARGET"
}

# ── Isolate Node Network ──────────────────────────────────────────────────────
isolate_node_network() {
    header "SCENARIO 2 — Isolating Network on $TARGET_NAME ($TARGET_IP)"

    warn "═════════════════════════════════════════════════════"
    warn "  ⚠  ABOUT TO DROP ALL NETWORK ON $TARGET_NAME  ⚠"
    warn "  Node: $TARGET_IP will lose all connectivity"
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
        log "AUTO_CONFIRM=1 set — proceeding with isolation"
    fi

    # Install iptables rule on target to block ALL traffic (self-inflicted blackhole)
    # We use nohup and a sleep-based restore to avoid permanent lockout
    log "Applying iptables DROP rules on $TARGET_IP..."
    log "Auto-restore will happen via scheduled script in 2 minutes (safety net)"

    # Drop all inbound AND outbound except already-established connections used for our command
    ssh_node "$TARGET_IP" "
        # Schedule auto-restore in 120 seconds (safety fallback)
        nohup bash -c 'sleep 120; iptables -F INPUT; iptables -F OUTPUT; iptables -F FORWARD; \
            iptables -P INPUT ACCEPT; iptables -P OUTPUT ACCEPT; iptables -P FORWARD ACCEPT; \
            ip link set nic3 up 2>/dev/null; echo \"Auto-restored at \$(date)\" >> /tmp/network_restore.log' \
            > /tmp/auto_restore.log 2>&1 &
        
        # Now drop ALL traffic (this will kill our SSH connection too)
        iptables -I INPUT 1 -j DROP
        iptables -I OUTPUT 1 -j DROP
        iptables -I FORWARD 1 -j DROP
    " 2>/dev/null || true

    T0=$(now_epoch)
    T0_STR=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    ok "Network isolation applied at T0 = $T0_STR"

    # ── Monitor Phase ─────────────────────────────────────────────────────────
    T_NODE_UNREACHABLE=""
    T_FENCE_TRIGGERED=""
    T_VM_FAILOVER=""
    T_CEPH_OSD_DOWN=""
    T_CEPH_DEGRADED=""

    header "Monitoring — Cluster response to node isolation"
    log "Polling every 5 seconds for up to 10 minutes..."

    for i in $(seq 1 120); do
        sleep 5
        SECS=$(elapsed $T0)
        MINS=$(( SECS / 60 ))

        # Can we still ping the target?
        if ping -c 1 -W 2 "$TARGET_IP" &>/dev/null; then
            NODE_REACH="REACHABLE"
        else
            NODE_REACH="UNREACHABLE"
            if [ -z "$T_NODE_UNREACHABLE" ]; then
                T_NODE_UNREACHABLE=$(elapsed $T0)
                timer "T+${T_NODE_UNREACHABLE}s — Node $TARGET_NAME confirmed UNREACHABLE"
            fi
        fi

        # Check cluster quorum and node status
        CLUSTER_STATUS=$(ssh_cmd "pvecm status 2>&1" | head -5 || echo "MGMT_ERROR")

        # Check HA status
        HA_STATUS=$(ssh_cmd "ha-manager status 2>/dev/null | grep -i 'fence\|migrat\|request\|$TARGET_NAME'" || echo "")

        # Check Ceph
        CEPH_H=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNREACHABLE")
        CEPH_OSD=$(ssh_cmd "ceph osd stat 2>/dev/null" || echo "")

        # Check running VMs
        VM_RUN=$(ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | \
            jq '[.[] | select(.status==\"running\")] | length'" || echo "?")

        echo -e "${BLUE}┌─── T+${MINS}m${SECS}s ─────────────────────────────────────────────┐${NC}"
        echo -e "${BLUE}│${NC} Target ($TARGET_NAME): $NODE_REACH"
        echo -e "${BLUE}│${NC} Running VMs: $VM_RUN / $VM_COUNT"
        echo -e "${BLUE}│${NC} Ceph: $CEPH_H"
        echo -e "${BLUE}│${NC} HA Events: ${HA_STATUS:-none}"
        echo -e "${BLUE}└───────────────────────────────────────────────────────────┘${NC}"

        # Detect fence
        if [ -z "$T_FENCE_TRIGGERED" ] && echo "$HA_STATUS" | grep -qi "fence\|fencing"; then
            T_FENCE_TRIGGERED=$(elapsed $T0)
            timer "T+${T_FENCE_TRIGGERED}s — HA FENCE triggered for $TARGET_NAME"
        fi

        # Detect VM failover
        if [ -z "$T_VM_FAILOVER" ]; then
            # Check if VMs that were on target are now running on other nodes
            VMS_MIGRATED=$(ssh_cmd "pvesh get /cluster/resources --type vm --output-format json 2>/dev/null | \
                jq -r '.[] | select(.status==\"running\" and .node!=\"'$TARGET_NAME'\") | .vmid'" 2>/dev/null || echo "")
            for VMID in $(echo "$VMS_ON_TARGET" | jq -r '.[]' 2>/dev/null); do
                if echo "$VMS_MIGRATED" | grep -q "^$VMID$"; then
                    T_VM_FAILOVER=$(elapsed $T0)
                    timer "T+${T_VM_FAILOVER}s — VM $VMID has failed over to another node"
                    break
                fi
            done
        fi

        # Detect Ceph OSD down
        if [ -z "$T_CEPH_OSD_DOWN" ] && echo "$CEPH_H" | grep -qi "OSD_DOWN\|HEALTH_WARN\|HEALTH_ERR"; then
            T_CEPH_OSD_DOWN=$(elapsed $T0)
            timer "T+${T_CEPH_OSD_DOWN}s — Ceph OSDs down detected"
        fi

        # Stop monitoring once we have VM failover (max 10 min)
        if [ -n "$T_VM_FAILOVER" ] && [ "$SECS" -gt 60 ]; then
            ok "VM failover confirmed — moving to restore phase"
            break
        fi
    done

    T_MONITOR_END=$(elapsed $T0)
    timer "Fault monitoring phase: ${T_MONITOR_END}s"
}

# ── Restore Network ───────────────────────────────────────────────────────────
restore_network() {
    header "Restoring Network on $TARGET_NAME ($TARGET_IP)"

    T_RESTORE_START=$(now_epoch)
    log "Flushing iptables rules on $TARGET_IP..."

    # Try to SSH and flush rules — may succeed once iptables locks expire or if some traffic gets through
    for attempt in $(seq 1 5); do
        if ssh_node "$TARGET_IP" "iptables -F INPUT; iptables -F OUTPUT; iptables -F FORWARD; iptables -P INPUT ACCEPT; iptables -P OUTPUT ACCEPT; iptables -P FORWARD ACCEPT" 2>/dev/null; then
            ok "iptables rules cleared on $TARGET_IP (attempt $attempt)"
            break
        else
            warn "Attempt $attempt: Cannot SSH to isolated node yet, waiting 10s..."
            sleep 10
        fi
    done

    # Monitor re-join
    T_NODE_REJOIN=""
    T_CEPH_RECOVER=""
    T_FULL_RECOVERY=""

    for attempt in $(seq 1 30); do
        sleep 10
        SECS_R=$(elapsed $T_RESTORE_START)

        NODE_REACH=$(ping -c 1 -W 2 "$TARGET_IP" &>/dev/null && echo "UP" || echo "DOWN")
        CEPH_R=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNREACHABLE")
        QUORUM=$(ssh_cmd "pvecm status 2>/dev/null | grep 'Quorum'" || echo "UNKNOWN")

        log "Recovery T+${SECS_R}s | $TARGET_NAME: $NODE_REACH | Ceph: $CEPH_R | $QUORUM"

        if [ "$NODE_REACH" = "UP" ]; then
            # Ensure iptables are definitely clear
            ssh_node "$TARGET_IP" "iptables -F INPUT; iptables -F OUTPUT; iptables -F FORWARD; iptables -P INPUT ACCEPT; iptables -P OUTPUT ACCEPT; iptables -P FORWARD ACCEPT" 2>/dev/null || true
            
            if [ -z "$T_NODE_REJOIN" ]; then
                T_NODE_REJOIN=$(elapsed $T0)
                timer "T+${T_NODE_REJOIN}s — Node $TARGET_NAME REJOINED cluster"
            fi

            # If Ceph only complains about clock skew, step chrony to resolve immediately
            if echo "$CEPH_R" | grep -qi "clock skew" && ! echo "$CEPH_R" | grep -qi "down\|degraded\|undersized"; then
                log "Resolving transient mon clock skew on $TARGET_NAME..."
                ssh_node "$TARGET_IP" "chronyc makestep; systemctl restart ceph-mon@$TARGET_NAME" &>/dev/null || true
                sleep 2
                CEPH_R=$(ssh_cmd "ceph health 2>/dev/null" || echo "UNREACHABLE")
            fi
        fi

        if echo "$CEPH_R" | grep -q "HEALTH_OK" && [ -z "$T_CEPH_RECOVER" ]; then
            T_CEPH_RECOVER=$(elapsed $T0)
            timer "T+${T_CEPH_RECOVER}s — Ceph fully recovered"
        fi

        if [ "$NODE_REACH" = "UP" ] && echo "$CEPH_R" | grep -q "HEALTH_OK"; then
            T_FULL_RECOVERY=$(elapsed $T0)
            ok "FULL RECOVERY at T+${T_FULL_RECOVERY}s"
            break
        fi
    done

    T_TOTAL=$(elapsed $T0)
}

# ── Save Results ──────────────────────────────────────────────────────────────
save_results() {
    header "Saving Scenario 2 Results"
    cat > "$RESULT_FILE" << EOF
{
  "scenario": "02_single_node_network_isolation",
  "timestamp_start": "$T0_STR",
  "cluster_ip": "$CLUSTER_IP",
  "isolated_node": "$TARGET_NAME",
  "isolated_node_ip": "$TARGET_IP",
  "timings": {
    "t_node_unreachable_sec":   ${T_NODE_UNREACHABLE:-null},
    "t_fence_triggered_sec":    ${T_FENCE_TRIGGERED:-null},
    "t_vm_failover_sec":        ${T_VM_FAILOVER:-null},
    "t_ceph_osd_down_sec":      ${T_CEPH_OSD_DOWN:-null},
    "t_node_rejoin_sec":        ${T_NODE_REJOIN:-null},
    "t_ceph_recover_sec":       ${T_CEPH_RECOVER:-null},
    "t_full_recovery_sec":      ${T_FULL_RECOVERY:-null},
    "t_total_test_sec":         $T_TOTAL
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
    echo -e "${BOLD}${YELLOW}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${YELLOW}║   SCENARIO 2: SINGLE NODE NETWORK ISOLATION      ║${NC}"
    echo -e "${BOLD}${YELLOW}║   Method: iptables DROP all traffic              ║${NC}"
    echo -e "${BOLD}${YELLOW}╚══════════════════════════════════════════════════╝${NC}"
    echo ""

    select_target_node
    record_baselines
    isolate_node_network
    restore_network
    save_results

    echo ""
    echo -e "${BOLD}${GREEN}  Scenario 2 Complete. Results: $RESULT_FILE${NC}"
    echo ""
}

main "$@"
