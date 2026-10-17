#!/usr/bin/env bash
# =============================================================================
# ssh_helper.sh — Common SSH configuration (sourced by all test scripts)
# Uses key-based auth — no sshpass required
# =============================================================================

CLUSTER_IP="10.31.6.172"
SSH_USER="root"
SSH_KEY="/tmp/proxmox_test_key"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15 -o BatchMode=yes"

RESULTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/results"
LOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/logs"
mkdir -p "$RESULTS_DIR" "$LOG_DIR"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BLUE='\033[0;34m'; MAGENTA='\033[0;35m'; BOLD='\033[1m'; NC='\033[0m'

log()     { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
ok()      { echo -e "${GREEN}[✔] $*${NC}"; }
warn()    { echo -e "${YELLOW}[⚠] $*${NC}"; }
fail()    { echo -e "${RED}[✘] $*${NC}"; }
timer()   { echo -e "${BLUE}[⏱] $*${NC}"; }
ceph_log(){ echo -e "${MAGENTA}[CEPH] $*${NC}"; }
header()  { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════════${NC}";
            echo -e "${BOLD}${CYAN}  $*${NC}";
            echo -e "${BOLD}${CYAN}══════════════════════════════════════════${NC}\n"; }

# SSH to management node
ssh_cmd() {
    ssh $SSH_OPTS "${SSH_USER}@${CLUSTER_IP}" "$@" 2>/dev/null
}

# SSH to any node by IP
ssh_node() {
    local ip="$1"; shift
    ssh $SSH_OPTS "${SSH_USER}@${ip}" "$@" 2>/dev/null
}

now_epoch() { date +%s; }
elapsed()   { echo $(( $(now_epoch) - $1 )); }
sec_fmt()   {
    local s="${1:-0}"
    [ "$s" = "null" ] || [ -z "$s" ] && echo "N/A" && return
    echo "$((s/60))m $((s%60))s"
}
