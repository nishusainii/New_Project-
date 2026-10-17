#!/usr/bin/env bash
# ==============================================================================
# StorCLI Storage Diagnostics, Health Auditing & Administration Tool
# Target Hardware: LSI / Broadcom MegaRAID / SAS Storage Controllers
# Supported OS: Linux (Debian, Ubuntu, Proxmox VE, RHEL, Rocky, Alma, CentOS)
# ==============================================================================

set -eo pipefail

# --- Color Definitions ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

REPORT_DIR="./storcli_reports"

# --- Detect StorCLI Executable ---
find_storcli() {
    local candidates=(
        "storcli"
        "storcli64"
        "/opt/MegaRAID/storcli/storcli64"
        "/opt/MegaRAID/storcli/storcli"
        "/usr/local/bin/storcli64"
        "/usr/local/bin/storcli"
        "/usr/bin/storcli64"
        "/usr/bin/storcli"
        "/opt/storcli/storcli64"
        "/opt/storcli/storcli"
    )

    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" >/dev/null 2>&1; then
            echo "$cmd"
            return 0
        elif [ -x "$cmd" ]; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

STORCLI_BIN=$(find_storcli || true)

check_storcli() {
    if [ -z "$STORCLI_BIN" ]; then
        echo -e "${RED}[ERROR]${NC} StorCLI executable not found in system PATH or standard /opt/ locations."
        echo -e "${YELLOW}[TIP]${NC} Please install StorCLI or verify the installation path:"
        echo -e "       - Debian/Ubuntu/Proxmox: dpkg -i storcli_*.deb"
        echo -e "       - RHEL/CentOS/Rocky:    rpm -ivh storcli-*.rpm"
        echo -e "       - Standard Path:        /opt/MegaRAID/storcli/storcli64"
        exit 1
    fi
}

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${YELLOW}[WARNING]${NC} Running as non-root user. StorCLI hardware queries usually require sudo / root privileges."
    fi
}

# --- Header Banner ---
print_banner() {
    echo -e "${BLUE}==============================================================================${NC}"
    echo -e "${BOLD}${CYAN}   StorCLI Storage Diagnostics & Administration Tool${NC}"
    echo -e "${BLUE}==============================================================================${NC}"
    echo -e " StorCLI Binary : ${GREEN}${STORCLI_BIN:-NOT FOUND}${NC}"
    echo -e " Host System    : $(hostname) ($(uname -r))"
    echo -e " Execution Time : $(date '+%Y-%m-%d %H:%M:%S %Z')"
    echo -e "${BLUE}------------------------------------------------------------------------------${NC}"
}

# --- 1. Full Storage Health Audit ---
run_full_audit() {
    check_storcli
    mkdir -p "$REPORT_DIR"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local report_file="${REPORT_DIR}/storcli_health_audit_${timestamp}.log"

    echo -e "\n${BOLD}${CYAN}=== STARTING FULL STORAGE HEALTH AUDIT ===${NC}"
    echo "Starting full StorCLI storage health audit at $(date)" > "$report_file"

    # Enumerate Controllers
    echo -e "\n${BOLD}[1/7] Scanning RAID Controllers...${NC}"
    local ctrl_count=$($STORCLI_BIN show J 2>/dev/null | grep -o '"Number of Controllers" : [0-9]*' | awk '{print $NF}' || echo "0")
    
    if [ "$ctrl_count" = "0" ] || [ -z "$ctrl_count" ]; then
        # Fallback query
        ctrl_output=$($STORCLI_BIN show 2>&1 || true)
        echo "$ctrl_output" >> "$report_file"
        echo -e "${YELLOW}[INFO] Controller List:${NC}"
        echo "$ctrl_output" | grep -E "Number of Controllers|Controller =" || echo "No controller info returned."
    else
        echo -e "${GREEN}[OK]${NC} Detected ${BOLD}${ctrl_count}${NC} MegaRAID Controller(s)."
    fi

    # Query Controller Details (Assume /c0 if not specified)
    local ctrl_idx=0
    echo -e "\n${BOLD}[2/7] Checking Controller Health & Temperature (/c${ctrl_idx})...${NC}"
    local ctrl_health=$($STORCLI_BIN /c${ctrl_idx} show health 2>&1 || true)
    echo "$ctrl_health" >> "$report_file"
    echo "$ctrl_health" | grep -E "Controller Health|Status|Controller =" || true

    local ctrl_status=$($STORCLI_BIN /c${ctrl_idx} show status 2>&1 || true)
    echo "$ctrl_status" >> "$report_file"
    echo "$ctrl_status" | grep -E "ROC temperature|Controller Status|Memory Size|BIOS Version|FW Version" || true

    # Check Battery Backup / CacheVault
    echo -e "\n${BOLD}[3/7] Checking Battery Backup Unit (BBU) / CacheVault (CV)...${NC}"
    local cv_status=$($STORCLI_BIN /c${ctrl_idx}/cv show all 2>&1 || true)
    local bbu_status=$($STORCLI_BIN /c${ctrl_idx}/bbu show all 2>&1 || true)
    echo "$cv_status" >> "$report_file"
    echo "$bbu_status" >> "$report_file"

    if echo "$cv_status" | grep -iq "Cachevault_Info\|Temperature\|State"; then
        echo -e "${GREEN}[INFO] CacheVault Module Detected:${NC}"
        echo "$cv_status" | grep -E "Temperature|State|Replacement required|SuperCap" || true
    elif echo "$bbu_status" | grep -iq "BatteryType\|Temperature\|State"; then
        echo -e "${GREEN}[INFO] BBU Module Detected:${NC}"
        echo "$bbu_status" | grep -E "Temperature|State|Battery State|Relative State of Health|Learn Cycle" || true
    else
        echo -e "${YELLOW}[INFO]${NC} No active BBU / CacheVault module reported or feature not present."
    fi

    # Check Virtual Drives (VDs)
    echo -e "\n${BOLD}[4/7] Checking Virtual Drive (VD / RAID Array) Integrity...${NC}"
    local vd_output=$($STORCLI_BIN /c${ctrl_idx}/vall show 2>&1 || true)
    echo "$vd_output" >> "$report_file"
    echo "$vd_output"

    # Analyze VD Degraded / Offline states
    if echo "$vd_output" | grep -iE "Dgrd|Degraded|Offline|PdFail"; then
        echo -e "${RED}${BOLD}[CRITICAL ALERT] One or more Virtual Drives are DEGRADED, OFFLINE, or FAILING!${NC}"
    else
        echo -e "${GREEN}[HEALTHY] All Virtual Drives are in Optimal state.${NC}"
    fi

    # Check Physical Drives (PDs)
    echo -e "\n${BOLD}[5/7] Checking Physical Drives (PD) Health & Error Counters...${NC}"
    local pd_output=$($STORCLI_BIN /c${ctrl_idx}/eall/sall show 2>&1 || true)
    echo "$pd_output" >> "$report_file"
    echo "$pd_output"

    # Analyze Physical Drive Health Counters
    echo -e "\n${BOLD}[6/7] Deep Sector & SMART Diagnostics Scan across Physical Drives...${NC}"
    local pd_errors_found=0
    
    # Query all drives detailed info
    local pd_all=$($STORCLI_BIN /c${ctrl_idx}/eall/sall show all 2>&1 || true)
    echo "$pd_all" >> "$report_file"

    # Check for Media Errors, Other Errors, Predictive Failures
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
    echo -e "${BOLD}Slot / Drive      Media Errors    Other Errors    Pred Failure    State${NC}"
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"

    # Parse PD slots and counters
    awk '
    /Drive \/c/ { drive=$0 }
    /Media Error Count =/ { media=$NF }
    /Other Error Count =/ { other=$NF }
    /Predictive Failure Count =/ { pred=$NF }
    /Firmware state =/ { 
        state=$NF; 
        if (drive != "") {
            printf "%-17s %-15s %-15s %-15s %s\n", drive, media, other, pred, state;
            if (media > 0 || other > 0 || pred > 0 || state ~ /UBad|Failed|PdFail/) {
                # Issue detected
            }
        }
    }' "$report_file" || true

    # Check Background Tasks (Rebuild, Consistency Check, Init)
    echo -e "\n${BOLD}[7/7] Checking Active Background Operations (Rebuild / CC / Init)...${NC}"
    local rb_output=$($STORCLI_BIN /c${ctrl_idx}/eall/sall show rebuild 2>&1 || true)
    local cc_output=$($STORCLI_BIN /c${ctrl_idx}/vall show cc 2>&1 || true)
    local init_output=$($STORCLI_BIN /c${ctrl_idx}/vall show init 2>&1 || true)
    
    echo "$rb_output" >> "$report_file"
    echo "$cc_output" >> "$report_file"
    echo "$init_output" >> "$report_file"

    local bg_active=0
    if echo "$rb_output" | grep -iE "Rebuild Progress|In Progress"; then
        echo -e "${YELLOW}[ACTIVE] Rebuild Operation in Progress:${NC}"
        echo "$rb_output" | grep -E "Rebuild Progress|Progress|State|Drive"
        bg_active=1
    fi

    if echo "$cc_output" | grep -iE "Consistency Check|In Progress|Progress"; then
        echo -e "${YELLOW}[ACTIVE] Consistency Check in Progress:${NC}"
        echo "$cc_output" | grep -E "Consistency Check|Progress|State"
        bg_active=1
    fi

    if [ "$bg_active" -eq 0 ]; then
        echo -e "${GREEN}[IDLE]${NC} No active background rebuild or consistency check operations."
    fi

    # Check Foreign Configurations
    local frgn_output=$($STORCLI_BIN /c${ctrl_idx}/fall show 2>&1 || true)
    echo "$frgn_output" >> "$report_file"
    if echo "$frgn_output" | grep -iq "Foreign Configuration"; then
        echo -e "\n${YELLOW}${BOLD}[NOTICE] Foreign RAID Configurations detected on controller ${ctrl_idx}!${NC}"
        echo "$frgn_output"
    fi

    echo -e "\n${GREEN}==============================================================================${NC}"
    echo -e "${BOLD}${GREEN}Audit Complete! Full diagnostic report saved to:${NC}"
    echo -e "${CYAN}${report_file}${NC}"
    echo -e "${GREEN}==============================================================================${NC}"
}

# --- 2. Locate / Blink Drive LED ---
locate_drive() {
    check_storcli
    local ctrl=${1:-}
    local enc=${2:-}
    local slot=${3:-}

    if [ -z "$ctrl" ] || [ -z "$enc" ] || [ -z "$slot" ]; then
        read -rp "Enter Controller ID (e.g. 0): " ctrl
        read -rp "Enter Enclosure ID (e.g. 252 or eall): " enc
        read -rp "Enter Slot ID (e.g. 0): " slot
    fi

    echo -e "\n${BOLD}${CYAN}Sending command to BLINK drive activity LED: /c${ctrl}/e${enc}/s${slot}${NC}"
    $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" start locate
    echo -e "${GREEN}[OK] Locator LED is now blinking on /c${ctrl}/e${enc}/s${slot}.${NC}"
}

# --- 3. Stop Locate LED ---
stop_locate_drive() {
    check_storcli
    local ctrl=${1:-}
    local enc=${2:-}
    local slot=${3:-}

    if [ -z "$ctrl" ] || [ -z "$enc" ] || [ -z "$slot" ]; then
        read -rp "Enter Controller ID (e.g. 0): " ctrl
        read -rp "Enter Enclosure ID (e.g. 252 or eall): " enc
        read -rp "Enter Slot ID (e.g. 0): " slot
    fi

    echo -e "\n${BOLD}${CYAN}Stopping locator LED on /c${ctrl}/e${enc}/s${slot}${NC}"
    $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" stop locate
    echo -e "${GREEN}[OK] Locator LED turned off.${NC}"
}

# --- 4. Fix Unconfigured Bad Drive ---
fix_ubad_drive() {
    check_storcli
    read -rp "Enter Controller ID (e.g. 0): " ctrl
    read -rp "Enter Enclosure ID (e.g. 252): " enc
    read -rp "Enter Slot ID (e.g. 1): " slot

    echo -e "\n${YELLOW}Setting drive /c${ctrl}/e${enc}/s${slot} from Unconfigured Bad (UBad) to Good (UGood)...${NC}"
    $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" set good force
    echo -e "\n${GREEN}[OK] Drive state updated. Verifying status:${NC}"
    $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" show
}

# --- 5. Start / Monitor Rebuild ---
manage_rebuild() {
    check_storcli
    echo -e "\n${BOLD}${CYAN}Rebuild Management:${NC}"
    echo "1) Start manual rebuild on drive"
    echo "2) Show live rebuild progress"
    echo "3) Pause rebuild"
    echo "4) Resume rebuild"
    echo "5) Set rebuild rate % (priority)"
    read -rp "Select option [1-5]: " opt

    case "$opt" in
        1)
            read -rp "Controller ID (e.g. 0): " ctrl
            read -rp "Enclosure ID (e.g. 252): " enc
            read -rp "Slot ID (e.g. 1): " slot
            $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" start rebuild
            ;;
        2)
            read -rp "Controller ID (e.g. 0): " ctrl
            echo -e "${CYAN}Press Ctrl+C to stop live monitor...${NC}"
            while true; do
                clear
                print_banner
                echo -e "${BOLD}Current Rebuild Status on Controller ${ctrl}:${NC}\n"
                $STORCLI_BIN /c"${ctrl}"/eall/sall show rebuild || true
                sleep 5
            done
            ;;
        3)
            read -rp "Controller ID (e.g. 0): " ctrl
            read -rp "Enclosure ID (e.g. 252): " enc
            read -rp "Slot ID (e.g. 1): " slot
            $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" pause rebuild
            ;;
        4)
            read -rp "Controller ID (e.g. 0): " ctrl
            read -rp "Enclosure ID (e.g. 252): " enc
            read -rp "Slot ID (e.g. 1): " slot
            $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" resume rebuild
            ;;
        5)
            read -rp "Controller ID (e.g. 0): " ctrl
            read -rp "Rebuild Rate (1-100%, recommended 30-50): " rate
            $STORCLI_BIN /c"${ctrl}" set rebuildrate="${rate}"
            ;;
        *)
            echo -e "${RED}Invalid option.${NC}"
            ;;
    esac
}

# --- 6. Foreign Configuration Management ---
manage_foreign() {
    check_storcli
    read -rp "Controller ID (e.g. 0): " ctrl
    echo -e "\n${BOLD}${CYAN}Foreign Configuration Operations for /c${ctrl}:${NC}"
    echo "1) Scan & Show Foreign Configurations (/c${ctrl}/fall show)"
    echo "2) Preview Foreign Array Layout (/c${ctrl}/fall preview)"
    echo "3) IMPORT Foreign Array (Data Recovery / Migration)"
    echo "4) CLEAR Foreign Metadata (Wipe Header to Reuse Disks)"
    read -rp "Select option [1-4]: " fopt

    case "$fopt" in
        1)
            $STORCLI_BIN /c"${ctrl}"/fall show
            ;;
        2)
            $STORCLI_BIN /c"${ctrl}"/fall preview
            ;;
        3)
            echo -e "${YELLOW}[CONFIRMATION] You are about to IMPORT the foreign array onto controller ${ctrl}.${NC}"
            read -rp "Are you sure? (y/N): " confirm
            if [[ "$confirm" =~ ^[Yy]$ ]]; then
                $STORCLI_BIN /c"${ctrl}"/fall import
            else
                echo "Operation cancelled."
            fi
            ;;
        4)
            echo -e "${RED}${BOLD}[DANGER] Clearing foreign configuration WIPES the RAID headers permanently!${NC}"
            read -rp "Type 'CLEAR' to confirm: " confirm
            if [ "$confirm" = "CLEAR" ]; then
                $STORCLI_BIN /c"${ctrl}"/fall clear
            else
                echo "Operation cancelled."
            fi
            ;;
        *)
            echo -e "${RED}Invalid option.${NC}"
            ;;
    esac
}

# --- 7. Toggle Drive Mode (JBOD / UGood) ---
toggle_jbod_mode() {
    check_storcli
    read -rp "Controller ID (e.g. 0): " ctrl
    read -rp "Enclosure ID (e.g. 252): " enc
    read -rp "Slot ID (e.g. 0): " slot
    echo "1) Set to JBOD (Pass-Through mode for ZFS/Ceph)"
    echo "2) Set to Unconfigured Good (UGood mode for Hardware RAID)"
    read -rp "Select target mode [1-2]: " mopt

    case "$mopt" in
        1)
            $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" set jbod
            ;;
        2)
            $STORCLI_BIN /c"${ctrl}"/e"${enc}"/s"${slot}" set good force
            ;;
        *)
            echo "Invalid option."
            ;;
    esac
}

# --- 8. Silence Alarm ---
silence_alarm() {
    check_storcli
    read -rp "Controller ID (e.g. 0): " ctrl
    $STORCLI_BIN /c"${ctrl}" set alarm=silence
    echo -e "${GREEN}[OK] Audible hardware buzzer silenced on /c${ctrl}.${NC}"
}

# --- 9. Export Logs & Config ---
export_logs_config() {
    check_storcli
    mkdir -p "$REPORT_DIR"
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    read -rp "Controller ID (e.g. 0): " ctrl
    
    local log_file="${REPORT_DIR}/storcli_events_c${ctrl}_${timestamp}.txt"
    local termlog_file="${REPORT_DIR}/storcli_termlog_c${ctrl}_${timestamp}.txt"
    local cfg_file="${REPORT_DIR}/storcli_config_backup_c${ctrl}_${timestamp}.xml"

    echo -e "\n${CYAN}Dumping controller event log...${NC}"
    $STORCLI_BIN /c"${ctrl}" show events file="${log_file}" || true

    echo -e "${CYAN}Dumping firmware terminal diagnostics log...${NC}"
    $STORCLI_BIN /c"${ctrl}" show termlog > "${termlog_file}" 2>&1 || true

    echo -e "${CYAN}Dumping controller XML configuration backup...${NC}"
    $STORCLI_BIN /c"${ctrl}" dump file="${cfg_file}" || true

    echo -e "\n${GREEN}[SUCCESS] Diagnostics and backups saved:${NC}"
    echo " - Events Log: $log_file"
    echo " - Termlog:    $termlog_file"
    echo " - Config XML: $cfg_file"
}

# --- Interactive Main Menu ---
interactive_menu() {
    while true; do
        clear
        print_banner
        echo -e "${BOLD}${CYAN}STORAGE MANAGEMENT & DIAGNOSTICS MENU:${NC}"
        echo -e "  ${BOLD}1)${NC} ${GREEN}Run Full Storage Health Audit & Generate Report${NC}"
        echo -e "  ${BOLD}2)${NC} Quick Summary Dashboard (Controllers, VDs, PDs, BBU)"
        echo -e "  ${BOLD}3)${NC} Blink Drive Activity LED (Locate Physical Drive in Chassis)"
        echo -e "  ${BOLD}4)${NC} Stop Blinking Drive LED"
        echo -e "  ${BOLD}5)${NC} Fix Unconfigured Bad (UBad -> UGood Force)"
        echo -e "  ${BOLD}6)${NC} Manage Rebuild (Start, Monitor, Pause, Set Priority Rate)"
        echo -e "  ${BOLD}7)${NC} Foreign Configuration (Scan, Preview, Import, Clear)"
        echo -e "  ${BOLD}8)${NC} Toggle Drive Mode (JBOD Pass-Through <-> RAID UGood)"
        echo -e "  ${BOLD}9)${NC} Silence Active Controller Alarm Buzzer"
        echo -e " ${BOLD}10)${NC} Dump Controller Event Logs & Backup XML Config"
        echo -e " ${BOLD}11)${NC} Run Consistency Check (CC) on Virtual Drive"
        echo -e "  ${BOLD}0)${NC} Exit"
        echo -e "${BLUE}------------------------------------------------------------------------------${NC}"
        read -rp "Select an option [0-11]: " choice

        case "$choice" in
            1) run_full_audit; read -rp "Press Enter to continue..." ;;
            2) 
                check_storcli
                $STORCLI_BIN show
                $STORCLI_BIN /c0/vall show || true
                $STORCLI_BIN /c0/eall/sall show || true
                read -rp "Press Enter to continue..." 
                ;;
            3) locate_drive; read -rp "Press Enter to continue..." ;;
            4) stop_locate_drive; read -rp "Press Enter to continue..." ;;
            5) fix_ubad_drive; read -rp "Press Enter to continue..." ;;
            6) manage_rebuild; read -rp "Press Enter to continue..." ;;
            7) manage_foreign; read -rp "Press Enter to continue..." ;;
            8) toggle_jbod_mode; read -rp "Press Enter to continue..." ;;
            9) silence_alarm; read -rp "Press Enter to continue..." ;;
            10) export_logs_config; read -rp "Press Enter to continue..." ;;
            11)
                check_storcli
                read -rp "Controller ID (e.g. 0): " ctrl
                read -rp "Virtual Drive ID (e.g. 0): " vd
                echo "Starting Consistency Check on /c${ctrl}/v${vd}..."
                $STORCLI_BIN /c"${ctrl}"/v"${vd}" start cc
                $STORCLI_BIN /c"${ctrl}"/v"${vd}" show cc
                read -rp "Press Enter to continue..."
                ;;
            0) echo "Exiting StorCLI Tool. Goodbye!"; exit 0 ;;
            *) echo -e "${RED}Invalid selection.${NC}"; sleep 1 ;;
        esac
    done
}

# --- CLI Argument Parsing ---
case "${1:-}" in
    --audit|-a)
        print_banner
        run_full_audit
        ;;
    --locate)
        locate_drive "${2:-}" "${3:-}" "${4:-}"
        ;;
    --stop-locate)
        stop_locate_drive "${2:-}" "${3:-}" "${4:-}"
        ;;
    --silence)
        silence_alarm "${2:-0}"
        ;;
    --rebuild-status)
        check_storcli
        $STORCLI_BIN /c"${2:-0}"/eall/sall show rebuild
        ;;
    --help|-h)
        print_banner
        echo "Usage: $(basename "$0") [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  (no args)             Launch interactive terminal management menu"
        echo "  --audit, -a           Run automated storage health audit and generate report"
        echo "  --locate <c> <e> <s>  Blink drive LED in chassis (e.g. --locate 0 252 0)"
        echo "  --stop-locate <c> <e> <s> Stop blinking drive LED"
        echo "  --silence <c>         Silence controller hardware alarm buzzer"
        echo "  --rebuild-status <c>  Show active rebuild progress on controller"
        echo "  --help, -h            Show this help reference"
        ;;
    *)
        interactive_menu
        ;;
esac
