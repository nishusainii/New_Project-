#!/usr/bin/env bash
# =============================================================================
# run_all_tests.sh — Master Orchestrator
# Runs all 3 Proxmox cluster failure scenarios in sequence
# Cluster: 10.31.6.172 | root | cybe6@cluster
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
ok()   { echo -e "${GREEN}[✔] $*${NC}"; }
warn() { echo -e "${YELLOW}[⚠] $*${NC}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
clear
echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                                                              ║${NC}"
echo -e "${BOLD}${CYAN}║    PROXMOX CLUSTER FAILURE & RECOVERY TEST SUITE            ║${NC}"
echo -e "${BOLD}${CYAN}║    Cluster: 10.31.6.172  |  3 Nodes  |  Ceph: nic3          ║${NC}"
echo -e "${BOLD}${CYAN}║                                                              ║${NC}"
echo -e "${BOLD}${CYAN}║    Scenario 1: Dual Node Hardware Shutdown                  ║${NC}"
echo -e "${BOLD}${CYAN}║    Scenario 2: Single Node Network Isolation                ║${NC}"
echo -e "${BOLD}${CYAN}║    Scenario 3: Full Ceph Network Outage                     ║${NC}"
echo -e "${BOLD}${CYAN}║                                                              ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}  ⚠  WARNING: This will cause real disruption to the cluster!${NC}"
echo -e "${YELLOW}  ⚠  Ensure NO PRODUCTION workloads are running before proceeding.${NC}"
echo ""

# ── Dependency check ──────────────────────────────────────────────────────────
echo -e "${BOLD}Checking required tools...${NC}"
MISSING=0
for dep in sshpass ssh jq ping; do
    if ! command -v "$dep" &>/dev/null; then
        echo -e "  ${RED}[✘] $dep — NOT FOUND${NC}"
        MISSING=1
    else
        echo -e "  ${GREEN}[✔] $dep${NC}"
    fi
done

if [ "$MISSING" = "1" ]; then
    echo ""
    echo -e "${RED}Install missing tools:${NC}"
    echo -e "  sudo apt update && sudo apt install -y sshpass jq iputils-ping"
    exit 1
fi

echo ""
echo -e "${BOLD}Scripts:${NC}"
for f in 00_preflight_check.sh 01_dual_node_shutdown.sh 02_node_network_down.sh 03_ceph_network_outage.sh generate_report.sh; do
    if [ -f "$SCRIPT_DIR/$f" ]; then
        chmod +x "$SCRIPT_DIR/$f"
        echo -e "  ${GREEN}[✔] $f${NC}"
    else
        echo -e "  ${RED}[✘] $f — NOT FOUND${NC}"
    fi
done

echo ""
echo -e "${BOLD}Select what to run:${NC}"
echo "  [1] Pre-flight check only"
echo "  [2] All 3 scenarios in sequence (full test)"
echo "  [3] Scenario 1 only — Dual node shutdown"
echo "  [4] Scenario 2 only — Network isolation"
echo "  [5] Scenario 3 only — Ceph outage"
echo "  [6] Generate report from existing results"
echo "  [0] Exit"
echo ""
echo -n "Enter choice: "
read -r CHOICE

case "$CHOICE" in
    1)
        bash "$SCRIPT_DIR/00_preflight_check.sh"
        ;;
    2)
        echo ""
        warn "Full test suite selected. Scenarios will run with 2-minute breaks between them."
        echo -n "Final confirmation — type 'RUN ALL' to proceed: "
        read -r FINAL
        if [ "$FINAL" != "RUN ALL" ]; then
            echo "Aborted."; exit 0
        fi
        
        log "═══ PHASE 0: PRE-FLIGHT ═══"
        bash "$SCRIPT_DIR/00_preflight_check.sh"
        echo ""
        
        log "═══ PHASE 1: DUAL NODE SHUTDOWN ═══"
        bash "$SCRIPT_DIR/01_dual_node_shutdown.sh"
        
        echo ""
        log "Waiting 3 minutes before next scenario..."
        sleep 180

        log "═══ PHASE 2: NODE NETWORK ISOLATION ═══"
        bash "$SCRIPT_DIR/02_node_network_down.sh"

        echo ""
        log "Waiting 3 minutes before next scenario..."
        sleep 180

        log "═══ PHASE 3: CEPH NETWORK OUTAGE ═══"
        bash "$SCRIPT_DIR/03_ceph_network_outage.sh"

        echo ""
        log "═══ GENERATING FINAL REPORT ═══"
        bash "$SCRIPT_DIR/generate_report.sh"
        ;;
    3)
        bash "$SCRIPT_DIR/01_dual_node_shutdown.sh"
        bash "$SCRIPT_DIR/generate_report.sh"
        ;;
    4)
        bash "$SCRIPT_DIR/02_node_network_down.sh"
        bash "$SCRIPT_DIR/generate_report.sh"
        ;;
    5)
        bash "$SCRIPT_DIR/03_ceph_network_outage.sh"
        bash "$SCRIPT_DIR/generate_report.sh"
        ;;
    6)
        bash "$SCRIPT_DIR/generate_report.sh"
        ;;
    0)
        echo "Exited."
        ;;
    *)
        echo -e "${RED}Invalid choice.${NC}"
        exit 1
        ;;
esac

echo ""
ok "Test run complete. Check results/ directory for JSON + HTML report."
echo ""
