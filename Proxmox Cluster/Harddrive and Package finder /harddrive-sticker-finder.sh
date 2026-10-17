#!/usr/bin/env bash

###############################################################################
# PROXMOX DRIVE STICKER & STORAGE ROLE FINDER
# Author: Nishu Saini
# Version: 1.0.0
#
# Purpose:
# Scans all physical storage drives across Proxmox VE nodes and accurately
# identifies:
#   1. Ceph OSD Disks (OSD ID, BlueStore DB/WAL, status)
#   2. ZFS Pool Disks (Pool name, vdev type, mirror/raidz)
#   3. Proxmox OS / Root / Boot Disks (pve-root, EFI, local-lvm)
#   4. Other LVM / Raw Filesystem Disks
#   5. Free / Available / Unassigned Disks
#
# Physical Matching Helpers:
#   - Serial Number (printed on physical drive label)
#   - Model & Capacity (HDD vs SSD vs NVMe)
#   - Physical Slot / Bay / PCI Path
#   - Physical LED Blinking (via ledctl enclosure LED or active read pulsing)
#
# Output formats:
#   - Formatted Terminal Color Table
#   - Printable Sticker Labels (Text / Cut-out format)
#   - Visual HTML Sticker Sheet & Front Chassis Bay Layout
#   - CSV Export for Excel & Label Printers (Brother, Zebra, Dymo)
#   - Cluster-wide scan via SSH
###############################################################################

set -o pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Color & Style Definitions
# ─────────────────────────────────────────────────────────────────────────────
BOLD="\033[1m"
DIM="\033[2m"
RED="\033[1;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
CYAN="\033[1;36m"
WHITE="\033[1;37m"
ORANGE="\033[38;5;208m"
RESET="\033[0m"

HOSTNAME=$(hostname -s 2>/dev/null || hostname)
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

# ─────────────────────────────────────────────────────────────────────────────
# Root Check
# ─────────────────────────────────────────────────────────────────────────────
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${YELLOW}[!] Warning:${RESET} This script requires root privileges to query disk serial numbers, Ceph LVM tags, and ZFS status."
        echo -e "    Attempting to re-run with sudo...\n"
        exec sudo bash "$0" "$@"
        exit 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# Required & Optional Package Check
# ─────────────────────────────────────────────────────────────────────────────
check_packages() {
    echo -e "${BOLD}${CYAN}=== Checking Required & Recommended Packages ===${RESET}"
    local pkgs=("lsblk" "udevadm" "blkid" "findmnt")
    local opt_pkgs=("smartctl:smartmontools" "ledctl:ledmon" "lsscsi:lsscsi" "zpool:zfsutils-linux" "ceph-volume:ceph-common" "nvme:nvme-cli")
    
    echo -e "${DIM}Core Linux utilities:${RESET}"
    for cmd in "${pkgs[@]}"; do
        if command -v "$cmd" &>/dev/null; then
            echo -e "  [${GREEN}✓ OK${RESET}] $cmd"
        else
            echo -e "  [${RED}MISSING${RESET}] $cmd (Critical: please install coreutils/util-linux)"
        fi
    done
    
    echo -e "\n${DIM}Storage & Hardware Diagnostics tools:${RESET}"
    local missing_opts=()
    for item in "${opt_pkgs[@]}"; do
        cmd="${item%%:*}"
        pkg="${item##*:}"
        if command -v "$cmd" &>/dev/null; then
            echo -e "  [${GREEN}✓ OK${RESET}] $cmd (${DIM}$pkg${RESET})"
        else
            echo -e "  [${YELLOW}OPTIONAL${RESET}] $cmd is not installed (Package: ${CYAN}$pkg${RESET})"
            missing_opts+=("$pkg")
        fi
    done
    
    if ((${#missing_opts[@]} > 0)); then
        echo -e "\n${YELLOW}To install all recommended diagnostic tools, run:${RESET}"
        echo -e "  ${BOLD}apt-get update && apt-get install -y ${missing_opts[*]}${RESET}\n"
    else
        echo -e "\n${GREEN}All diagnostic and storage utilities are present!${RESET}\n"
    fi
}

install_packages() {
    echo -e "${BOLD}${CYAN}Installing recommended diagnostic packages (smartmontools, ledmon, lsscsi, nvme-cli)...${RESET}"
    apt-get update -y && apt-get install -y smartmontools ledmon lsscsi nvme-cli
    echo -e "${GREEN}Done.${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# Helper: Detect Dell PERC / MegaRAID physical slots and locate targets
# ─────────────────────────────────────────────────────────────────────────────
declare -A PERCCLI_SLOT_MAP
declare -A PERCCLI_LOCATE_MAP
PERCCLI_BIN=""

load_perccli_info() {
    PERCCLI_SLOT_MAP=()
    PERCCLI_LOCATE_MAP=()
    PERCCLI_BIN=""
    if [[ -x /opt/MegaRAID/perccli/perccli64 ]]; then
        PERCCLI_BIN="/opt/MegaRAID/perccli/perccli64"
    elif command -v perccli64 &>/dev/null; then
        PERCCLI_BIN="perccli64"
    elif command -v perccli &>/dev/null; then
        PERCCLI_BIN="perccli"
    elif [[ -x /opt/MegaRAID/storcli/storcli64 ]]; then
        PERCCLI_BIN="/opt/MegaRAID/storcli/storcli64"
    fi
    
    if [[ -n "$PERCCLI_BIN" ]]; then
        while read -r sn slot; do
            if [[ -n "$sn" && -n "$slot" ]]; then
                PERCCLI_SLOT_MAP["$sn"]="Slot $slot"
                PERCCLI_LOCATE_MAP["$sn"]="/c0/e252/s$slot"
            fi
        done < <($PERCCLI_BIN /c0 /e252 /sall show all 2>/dev/null | awk '/Drive \/c0\/e252\/s[0-9]+/ {match($0, /s[0-9]+/); slot=substr($0, RSTART+1, RLENGTH-1)} /SN =/ {print $3, slot}' || true)
    fi
}

get_disk_slot() {
    local dev="$1" # e.g. /dev/sda
    local dev_sn="${2:-}" # optional serial number
    local devname="${dev##*/}"
    local slot=""
    
    # 0. Check PERCCLI hardware slot mapping if serial is known
    if [[ -n "$dev_sn" && -n "${PERCCLI_SLOT_MAP[$dev_sn]:-}" ]]; then
        echo "${PERCCLI_SLOT_MAP[$dev_sn]}"
        return
    fi
    
    # 1. Check sysfs enclosure services
    if [[ -d /sys/class/enclosure ]]; then
        for enc_slot in /sys/class/enclosure/*/*; do
            if [[ -d "$enc_slot/device" ]]; then
                local real_target
                real_target=$(readlink -f "$enc_slot/device" 2>/dev/null)
                if [[ "$real_target" =~ $devname ]]; then
                    slot="Bay $(basename "$enc_slot")"
                    break
                fi
            fi
        done
    fi
    
    # 2. Check /dev/disk/by-path
    if [[ -z "$slot" && -d /dev/disk/by-path ]]; then
        for path_link in /dev/disk/by-path/*; do
            if [[ -L "$path_link" && ! "$path_link" =~ -part[0-9]+$ ]]; then
                if [[ "$(readlink -f "$path_link")" == "$dev" ]]; then
                    local base_path
                    base_path=$(basename "$path_link")
                    if [[ "$base_path" =~ -phy([0-9]+) ]]; then
                        slot="SAS Port ${BASH_REMATCH[1]}"
                    elif [[ "$base_path" =~ -ata-([0-9]+) ]]; then
                        slot="SATA Port ${BASH_REMATCH[1]}"
                    elif [[ "$base_path" =~ scsi-0:2:([0-9]+):0 ]]; then
                        # Target 16..27 corresponds to Bay 0..11 on Dell H755 backplane
                        local scsi_t="${BASH_REMATCH[1]}"
                        if (( scsi_t >= 16 && scsi_t <= 27 )); then
                            slot="Slot $((scsi_t - 16))"
                        else
                            slot="Target $scsi_t"
                        fi
                    elif [[ "$base_path" =~ target([0-9]+:[0-9]+:[0-9]+) ]]; then
                        slot="SCSI ${BASH_REMATCH[1]}"
                    elif [[ "$base_path" =~ nvme-([0-9]+) ]]; then
                        slot="NVMe Slot ${BASH_REMATCH[1]}"
                    fi
                    break
                fi
            fi
        done
    fi
    
    # 3. Fallback to SCSI Host:Channel:Target:Lun from sysfs
    if [[ -z "$slot" && -d "/sys/block/$devname/device" ]]; then
        local scsi_addr
        scsi_addr=$(basename "$(readlink -f "/sys/block/$devname/device" 2>/dev/null)" 2>/dev/null)
        if [[ "$scsi_addr" =~ ^0:2:([0-9]+):0$ ]]; then
            local scsi_t="${BASH_REMATCH[1]}"
            if (( scsi_t >= 16 && scsi_t <= 27 )); then
                slot="Slot $((scsi_t - 16))"
            else
                slot="Bus $scsi_addr"
            fi
        elif [[ "$scsi_addr" =~ ^[0-9]+:[0-9]+:[0-9]+:[0-9]+$ ]]; then
            slot="Bus $scsi_addr"
        fi
    fi
    
    [[ -z "$slot" ]] && slot="Direct / Unk"
    echo "$slot"
}

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Collect All Storage Role Metadata
# ─────────────────────────────────────────────────────────────────────────────
declare -A DISK_ROLES        # CEPH, ZFS, OS, LVM, FREE, OTHER
declare -A DISK_ROLE_DETAILS # "OSD.0 (up/in)", "Pool: tank (raidz2)", "pve-root, boot"
declare -A DISK_SERIALLIST
declare -A DISK_MODELLIST
declare -A DISK_SIZELIST
declare -A DISK_TYPELIST     # HDD, SSD, NVMe
declare -A DISK_SLOTLIST
declare -A DISK_WWNLIST

# Load Ceph LVM mappings if available
declare -A CEPH_DEV_MAP
load_ceph_info() {
    CEPH_DEV_MAP=()
    
    # 1. Check ceph device ls (Most accurate mapping on Ceph clusters)
    if command -v ceph &>/dev/null; then
        while read -r host_dev daemons; do
            if [[ "$host_dev" =~ ^${HOSTNAME}:([a-zA-Z0-9_]+) ]]; then
                local short_d="${BASH_REMATCH[1]}"
                local dev_p="/dev/$short_d"
                if [[ "$daemons" =~ (osd\.[0-9]+) ]]; then
                    local osd_name="${BASH_REMATCH[1]}"
                    CEPH_DEV_MAP["$dev_p"]="CEPH ${osd_name^^} (BlueStore block)"
                fi
            fi
        done < <(ceph device ls 2>/dev/null | awk 'NR>1 {print $2, $3}' || true)
    fi

    # 2. Check LVM tags
    if command -v lvs &>/dev/null; then
        while IFS= read -r line; do
            local lv_name vg_name devices tags
            vg_name=$(echo "$line" | awk '{print $1}')
            lv_name=$(echo "$line" | awk '{print $2}')
            devices=$(echo "$line" | awk '{print $3}')
            tags=$(echo "$line" | awk '{$1=$2=$3=""; print $0}' | sed 's/^[ \t]*//')
            
            if [[ "$tags" =~ ceph\.osd_id=([0-9]+) ]]; then
                local osd_id="${BASH_REMATCH[1]}"
                local ceph_type="block"
                if [[ "$tags" =~ ceph\.type=([a-zA-Z0-9_-]+) ]]; then
                    ceph_type="${BASH_REMATCH[1]}"
                fi
                for d in ${devices//,/ }; do
                    local real_d
                    real_d=$(readlink -f "${d%%(*}" 2>/dev/null || echo "${d%%(*}")
                    local parent_d
                    parent_d=$(lsblk -no PKNAME "$real_d" 2>/dev/null || echo "")
                    [[ -n "$parent_d" ]] && parent_d="/dev/$parent_d" || parent_d="$real_d"
                    CEPH_DEV_MAP["$parent_d"]="CEPH OSD.$osd_id ($ceph_type)"
                done
            fi
        done < <(lvs --noheadings -o vg_name,lv_name,devices,lv_tags 2>/dev/null || true)
    fi
}

# Load ZFS pool mappings if available
declare -A ZFS_DEV_MAP
load_zfs_info() {
    ZFS_DEV_MAP=()
    if command -v zpool &>/dev/null; then
        local current_pool=""
        local current_vdev=""
        while IFS= read -r line; do
            # Detect pool: <name>
            if [[ "$line" =~ ^[[:space:]]*pool:[[:space:]]+([a-zA-Z0-9_.-]+) ]]; then
                current_pool="${BASH_REMATCH[1]}"
                current_vdev="stripe"
            fi
            # Detect vdev types (mirror, raidz, raidz1, raidz2, raidz3, special, log, cache, spare)
            if [[ "$line" =~ ^[[:space:]]*(mirror-[0-9]+|raidz[1-3]?-[0-9]+|logs|cache|spares) ]]; then
                current_vdev="${BASH_REMATCH[1]}"
            fi
            # Detect device entries
            if [[ -n "$current_pool" && "$line" =~ ^[[:space:]]+(/dev/[^[:space:]]+|[a-zA-Z0-9_-]+)[[:space:]]+(ONLINE|DEGRADED|FAULTED|AVAIL) ]]; then
                local dev_entry="${BASH_REMATCH[1]}"
                local dev_state="${BASH_REMATCH[2]}"
                local full_dev=""
                if [[ "$dev_entry" =~ ^/dev/ ]]; then
                    full_dev=$(readlink -f "$dev_entry")
                elif [[ -e "/dev/disk/by-id/$dev_entry" ]]; then
                    full_dev=$(readlink -f "/dev/disk/by-id/$dev_entry")
                elif [[ -e "/dev/$dev_entry" ]]; then
                    full_dev=$(readlink -f "/dev/$dev_entry")
                fi
                if [[ -n "$full_dev" && -b "$full_dev" ]]; then
                    local parent_d
                    parent_d=$(lsblk -no PKNAME "$full_dev" 2>/dev/null || echo "")
                    [[ -n "$parent_d" ]] && parent_d="/dev/$parent_d" || parent_d="$full_dev"
                    ZFS_DEV_MAP["$parent_d"]="ZFS: ${current_pool} (${current_vdev}, ${dev_state})"
                fi
            fi
        done < <(zpool status -P -v 2>/dev/null || zpool status -v 2>/dev/null || true)
    fi
}

# Identify role for a single block device
classify_disk() {
    local dev="$1" # /dev/sda
    local devname="${dev##*/}"
    
    # 1. Check Ceph Map
    if [[ -n "${CEPH_DEV_MAP[$dev]:-}" ]]; then
        DISK_ROLES["$dev"]="CEPH"
        DISK_ROLE_DETAILS["$dev"]="${CEPH_DEV_MAP[$dev]}"
        return
    fi
    
    # 2. Check ZFS Map
    if [[ -n "${ZFS_DEV_MAP[$dev]:-}" ]]; then
        DISK_ROLES["$dev"]="ZFS"
        DISK_ROLE_DETAILS["$dev"]="${ZFS_DEV_MAP[$dev]}"
        return
    fi
    
    # 3. Check for Ceph signatures via blkid / lsblk
    local fstypes
    fstypes=$(lsblk -no FSTYPE "$dev" 2>/dev/null | tr '\n' ' ' || true)
    local partlabels
    partlabels=$(lsblk -no PARTLABEL "$dev" 2>/dev/null | tr '\n' ' ' || true)
    
    if [[ "$fstypes" =~ ceph_bluestore || "$partlabels" =~ (ceph[[:space:]]+block|ceph[[:space:]]+data|ceph[[:space:]]+db) ]]; then
        DISK_ROLES["$dev"]="CEPH"
        DISK_ROLE_DETAILS["$dev"]="Ceph BlueStore OSD (detected signature)"
        return
    fi
    
    # 4. Check for ZFS signatures via blkid
    if [[ "$fstypes" =~ zfs_member ]]; then
        local zpool_hint="ZFS Member"
        if command -v zdb &>/dev/null; then
            for part in /dev/"$devname"[0-9]* "$dev"; do
                if [[ -b "$part" ]]; then
                    local zpool_name
                    zpool_name=$(zdb -l "$part" 2>/dev/null | awk -F"'" '/^[[:space:]]*name:[[:space:]]*/ {print $2; exit}' || true)
                    if [[ -n "$zpool_name" ]]; then
                        zpool_hint="ZFS Pool: $zpool_name"
                        break
                    fi
                fi
            done
        fi
        DISK_ROLES["$dev"]="ZFS"
        DISK_ROLE_DETAILS["$dev"]="$zpool_hint"
        return
    fi
    
    # 5. Check if OS / Root / Boot Disk
    local mounts
    mounts=$(lsblk -no MOUNTPOINTS "$dev" 2>/dev/null | tr '\n' ' ' || true)
    local lv_names
    lv_names=$(lsblk -no LABEL,NAME "$dev" 2>/dev/null | tr '\n' ' ' || true)
    
    # Check if root filesystem resides here
    local root_src
    root_src=$(findmnt -n -o SOURCE / 2>/dev/null || true)
    local is_root_disk=0
    if [[ -n "$root_src" ]]; then
        local root_parent
        root_parent=$(lsblk -no PKNAME "$root_src" 2>/dev/null || echo "")
        [[ -n "$root_parent" ]] && root_parent="/dev/$root_parent"
        if [[ "$root_parent" == "$dev" || "$root_src" =~ $devname ]]; then
            is_root_disk=1
        fi
        if [[ $is_root_disk -eq 0 ]] && command -v pvs &>/dev/null; then
            local pve_pvs
            pve_pvs=$(pvs --noheadings -o pv_name,vg_name 2>/dev/null | awk '$2 ~ /pve/ {print $1}' || true)
            for pv in $pve_pvs; do
                local pv_parent
                pv_parent=$(lsblk -no PKNAME "$pv" 2>/dev/null || echo "")
                [[ -n "$pv_parent" ]] && pv_parent="/dev/$pv_parent"
                if [[ "$pv" == "$dev" || "$pv_parent" == "$dev" ]]; then
                    is_root_disk=1
                    break
                fi
            done
        fi
    fi
    
    if [[ $is_root_disk -eq 1 || "$mounts" =~ [[:space:]]/([[:space:]]|$) || "$mounts" =~ /boot ]]; then
        DISK_ROLES["$dev"]="PVE-OS"
        local os_details="Proxmox VE Host OS ("
        local items=()
        [[ "$mounts" =~ [[:space:]]/([[:space:]]|$) ]] && items+=("root /")
        [[ "$mounts" =~ /boot/efi ]] && items+=("EFI")
        [[ "$mounts" =~ /boot ]] && items+=("boot")
        [[ "$lv_names" =~ pve-data ]] && items+=("local-lvm")
        [[ "$lv_names" =~ pve-swap ]] && items+=("swap")
        if ((${#items[@]} == 0)); then
            items+=("System Root/Boot")
        fi
        local joined
        joined=$(IFS=", "; echo "${items[*]}")
        DISK_ROLE_DETAILS["$dev"]="${os_details}${joined})"
        return
    fi
    
    # 6. Check other LVM Volume Groups
    if command -v pvs &>/dev/null; then
        local vg_name
        vg_name=$(pvs --noheadings -o vg_name "$dev" 2>/dev/null | tr -d ' ' || true)
        if [[ -z "$vg_name" ]]; then
            for part in /dev/"$devname"[0-9]*; do
                if [[ -b "$part" ]]; then
                    vg_name=$(pvs --noheadings -o vg_name "$part" 2>/dev/null | tr -d ' ' || true)
                    [[ -n "$vg_name" ]] && break
                fi
            done
        fi
        if [[ -n "$vg_name" ]]; then
            DISK_ROLES["$dev"]="LVM"
            DISK_ROLE_DETAILS["$dev"]="LVM VG: $vg_name"
            return
        fi
    fi
    
    # 7. Check if active mount exists
    local non_empty_mounts
    non_empty_mounts=$(lsblk -no MOUNTPOINTS "$dev" 2>/dev/null | grep -v '^$' | tr '\n' ',' | sed 's/,$//' || true)
    if [[ -n "$non_empty_mounts" ]]; then
        DISK_ROLES["$dev"]="MOUNTED"
        DISK_ROLE_DETAILS["$dev"]="Mounted on: $non_empty_mounts"
        return
    fi
    
    # 8. Check if completely free / unpartitioned
    local part_count
    part_count=$(lsblk -no TYPE "$dev" 2>/dev/null | grep -c "part" || true)
    if (( part_count == 0 )) && [[ -z "$fstypes" ]]; then
        DISK_ROLES["$dev"]="FREE"
        DISK_ROLE_DETAILS["$dev"]="Unused / Raw Disk (Ready for Ceph/ZFS)"
        return
    elif (( part_count > 0 )) && [[ -z "$fstypes" ]]; then
        DISK_ROLES["$dev"]="UNASSIGNED"
        DISK_ROLE_DETAILS["$dev"]="$part_count Partition(s), No active FS (Check wipefs)"
        return
    fi
    
    DISK_ROLES["$dev"]="OTHER"
    DISK_ROLE_DETAILS["$dev"]="FS: ${fstypes:-Unknown/Raw}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Hardware & Storage Scan Engine
# ─────────────────────────────────────────────────────────────────────────────
scan_system_disks() {
    load_perccli_info
    load_ceph_info
    load_zfs_info
    
    # Get all disk block devices (exclude loop 7, ram 1)
    local disks_raw
    disks_raw=$(lsblk -dn -o NAME,TYPE -e 7,1 2>/dev/null | awk '$2 ~ /disk/ {print $1}')
    
    for devname in $disks_raw; do
        local dev="/dev/$devname"
        [[ ! -b "$dev" ]] && continue
        # Exclude ZFS zvols, dm devices, ram/loop
        [[ "$devname" =~ ^(zd|dm-|loop|ram) ]] && continue
        
        # Hardware properties
        local size model serial rota tran
        size=$(lsblk -dno SIZE "$dev" 2>/dev/null | tr -d ' ')
        model=$(lsblk -dno MODEL "$dev" 2>/dev/null | sed 's/^[ \t]*//;s/[ \t]*$//')
        serial=$(lsblk -dno SERIAL "$dev" 2>/dev/null | tr -d ' ')
        rota=$(lsblk -dno ROTA "$dev" 2>/dev/null | tr -d ' ')
        tran=$(lsblk -dno TRAN "$dev" 2>/dev/null | tr -d ' ')
        
        # Fallback query via udevadm if serial or model empty
        if [[ -z "$serial" || "$serial" == "-" || -z "$model" ]]; then
            local udev_props
            udev_props=$(udevadm info --query=property --name="$dev" 2>/dev/null || true)
            [[ -z "$serial" ]] && serial=$(echo "$udev_props" | grep -E '^ID_SERIAL_SHORT=' | head -1 | cut -d'=' -f2)
            [[ -z "$serial" ]] && serial=$(echo "$udev_props" | grep -E '^ID_SERIAL=' | head -1 | cut -d'=' -f2)
            [[ -z "$model" ]] && model=$(echo "$udev_props" | grep -E '^ID_MODEL=' | head -1 | cut -d'=' -f2 | tr '_' ' ')
        fi
        
        if [[ -z "$serial" ]] && command -v smartctl &>/dev/null; then
            serial=$(smartctl -i "$dev" 2>/dev/null | awk -F':' '/Serial Number|Serial number/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}' || true)
        fi
        
        # Determine media type
        local media="HDD"
        if [[ "$devname" =~ ^nvme ]]; then
            media="NVMe SSD"
        elif [[ "$rota" == "0" ]]; then
            media="SATA/SAS SSD"
        fi
        
        # WWN
        local wwn
        wwn=$(udevadm info --query=property --name="$dev" 2>/dev/null | grep -E '^ID_WWN=' | head -1 | cut -d'=' -f2 || true)
        [[ -z "$wwn" ]] && wwn="-"
        
        # Slot / Bay
        local slot
        slot=$(get_disk_slot "$dev" "$serial")
        
        DISK_SERIALLIST["$dev"]="${serial:-UNKNOWN_SN}"
        DISK_MODELLIST["$dev"]="${model:-Generic Disk}"
        DISK_SIZELIST["$dev"]="${size:-Unknown}"
        DISK_TYPELIST["$dev"]="$media"
        DISK_SLOTLIST["$dev"]="$slot"
        DISK_WWNLIST["$dev"]="$wwn"
        
        # Classify storage role
        classify_disk "$dev"
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# Terminal Color Table Output
# ─────────────────────────────────────────────────────────────────────────────
display_terminal_table() {
    echo ""
    echo -e "${BOLD}====================================================================================================${RESET}"
    echo -e "       ${BOLD}${WHITE}PROXMOX PHYSICAL HARD DRIVE & STORAGE ROLE INVENTORY${RESET}"
    echo -e "       ${CYAN}Node: ${BOLD}${HOSTNAME}${RESET}  |  ${CYAN}Scanned at: ${BOLD}${TIMESTAMP}${RESET}"
    echo -e "${BOLD}====================================================================================================${RESET}"
    printf "${BOLD}%-15s %-10s %-18s %-9s %-12s %-14s %-25s${RESET}\n" \
        "BAY / BUS" "DEVICE" "SERIAL NUMBER" "SIZE" "TYPE" "STORAGE ROLE" "ROLE DETAILS / POOL / OSD"
    echo -e "${DIM}----------------------------------------------------------------------------------------------------${RESET}"
    
    local sorted_devs
    sorted_devs=$(printf '%s\n' "${!DISK_ROLES[@]}" | sort)
    
    for dev in $sorted_devs; do
        local role="${DISK_ROLES[$dev]}"
        local details="${DISK_ROLE_DETAILS[$dev]}"
        local serial="${DISK_SERIALLIST[$dev]}"
        local size="${DISK_SIZELIST[$dev]}"
        local type="${DISK_TYPELIST[$dev]}"
        local slot="${DISK_SLOTLIST[$dev]}"
        
        local role_color="$WHITE"
        case "$role" in
            "CEPH")       role_color="$ORANGE" ;;
            "ZFS")        role_color="$CYAN" ;;
            "PVE-OS")     role_color="$GREEN" ;;
            "FREE")       role_color="$GREEN" ;;
            "LVM")        role_color="$MAGENTA" ;;
            "UNASSIGNED") role_color="$YELLOW" ;;
            *)            role_color="$WHITE" ;;
        esac
        
        printf "%-15s %-10s ${BOLD}%-18s${RESET} %-9s %-12s ${role_color}${BOLD}%-14s${RESET} %-25s\n" \
            "$slot" "$dev" "$serial" "$size" "$type" "$role" "$details"
    done
    echo -e "${BOLD}====================================================================================================${RESET}"
    echo -e "${BOLD}Role Summary:${RESET} "
    echo -e "  ${ORANGE}■ CEPH${RESET}   = Used for Ceph Storage OSDs (Distributed RBD)"
    echo -e "  ${CYAN}■ ZFS${RESET}    = Used for ZFS Storage Pool (Mirror / RAID-Z)"
    echo -e "  ${GREEN}■ PVE-OS${RESET} = Proxmox Host Operating System (pve-root, boot, local-lvm)"
    echo -e "  ${GREEN}■ FREE${RESET}   = Completely empty / raw disk (Available to add to Ceph or ZFS)"
    echo -e "${DIM}Tip: Check the physical SERIAL NUMBER on the drive tray or use Option 5 (LED Blink) to verify.${RESET}\n"
}

# ─────────────────────────────────────────────────────────────────────────────
# Printable Text Sticker Generator
# ─────────────────────────────────────────────────────────────────────────────
generate_text_stickers() {
    local outfile="${1:-${OUTPUT_DIR}/harddrive_stickers_${HOSTNAME}.txt}"
    mkdir -p "$(dirname "$outfile")"
    
    local sorted_devs
    sorted_devs=$(printf '%s\n' "${!DISK_ROLES[@]}" | sort)
    
    {
        echo "================================================================================"
        echo "                 PHYSICAL HARD DRIVE STICKER CUT-OUT LABELS"
        echo "  Node: $HOSTNAME | Generated: $TIMESTAMP"
        echo "  Instructions: Cut along the dotted lines and paste onto the drive caddy/tray."
        echo "================================================================================"
        echo ""
        
        for dev in $sorted_devs; do
            local role="${DISK_ROLES[$dev]}"
            local details="${DISK_ROLE_DETAILS[$dev]}"
            local serial="${DISK_SERIALLIST[$dev]}"
            local model="${DISK_MODELLIST[$dev]}"
            local size="${DISK_SIZELIST[$dev]}"
            local type="${DISK_TYPELIST[$dev]}"
            local slot="${DISK_SLOTLIST[$dev]}"
            local wwn="${DISK_WWNLIST[$dev]}"
            
            echo "+------------------------------------------------------------------------------+"
            printf "| %-35s  |  %-36s |\n" "NODE: $HOSTNAME" "LOCATION: $slot"
            echo "+------------------------------------------------------------------------------+"
            printf "| STICKER ROLE: %-60s |\n" "$role - $details"
            printf "| DEVICE PATH : %-20s  |  CAPACITY : %-22s |\n" "$dev" "$size ($type)"
            printf "| SERIAL NO   : %-20s  |  MODEL    : %-22s |\n" "$serial" "$model"
            printf "| WWN / ID    : %-60s |\n" "$wwn"
            echo "+------------------------------------------------------------------------------+"
            echo ""
        done
        
        echo "================================================================================"
        echo "                             END OF STICKER LABELS"
        echo "================================================================================"
    } > "$outfile"
    
    echo -e "${GREEN}✓ Text sticker labels saved to:${RESET} ${BOLD}$outfile${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# CSV Export for Label Printers (Brother P-touch, Dymo, Zebra, Excel)
# ─────────────────────────────────────────────────────────────────────────────
generate_csv_export() {
    local outfile="${1:-${OUTPUT_DIR}/harddrive_stickers_${HOSTNAME}.csv}"
    mkdir -p "$(dirname "$outfile")"
    
    local sorted_devs
    sorted_devs=$(printf '%s\n' "${!DISK_ROLES[@]}" | sort)
    
    {
        echo "Node,Bay_Slot,Device,Role,Role_Details,Serial_Number,Capacity,Media_Type,Model,WWN,Sticker_Top_Line,Sticker_Bottom_Line"
        for dev in $sorted_devs; do
            local role="${DISK_ROLES[$dev]}"
            local details="${DISK_ROLE_DETAILS[$dev]}"
            local serial="${DISK_SERIALLIST[$dev]}"
            local model="${DISK_MODELLIST[$dev]}"
            local size="${DISK_SIZELIST[$dev]}"
            local type="${DISK_TYPELIST[$dev]}"
            local slot="${DISK_SLOTLIST[$dev]}"
            local wwn="${DISK_WWNLIST[$dev]}"
            
            # Escape quotes in fields
            details="${details//\"/\"\"}"
            model="${model//\"/\"\"}"
            
            local top_line="${HOSTNAME} | ${slot} | ${role}"
            local bot_line="S/N: ${serial} (${size})"
            
            echo "\"$HOSTNAME\",\"$slot\",\"$dev\",\"$role\",\"$details\",\"$serial\",\"$size\",\"$type\",\"$model\",\"$wwn\",\"$top_line\",\"$bot_line\""
        done
    } > "$outfile"
    
    echo -e "${GREEN}✓ CSV export saved to:${RESET} ${BOLD}$outfile${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Visual HTML Sticker Sheet & Front Chassis Bay Layout Generator
# ─────────────────────────────────────────────────────────────────────────────
generate_html_sheet() {
    local outfile="${1:-${OUTPUT_DIR}/harddrive_stickers_${HOSTNAME}.html}"
    mkdir -p "$(dirname "$outfile")"
    
    local sorted_devs
    sorted_devs=$(printf '%s\n' "${!DISK_ROLES[@]}" | sort)
    
    # Calculate counts
    local ceph_count=0 zfs_count=0 os_count=0 free_count=0 other_count=0
    for dev in $sorted_devs; do
        case "${DISK_ROLES[$dev]}" in
            "CEPH") ((ceph_count++)) ;;
            "ZFS")  ((zfs_count++)) ;;
            "PVE-OS") ((os_count++)) ;;
            "FREE") ((free_count++)) ;;
            *)      ((other_count++)) ;;
        esac
    done
    
    cat << 'EOF_HTML_HEAD' > "$outfile"
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Proxmox Hard Drive Sticker Sheet</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
    
    :root {
      --bg: #0b1120;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f1f5f9;
      --muted: #94a3b8;
      --ceph-color: #f97316;
      --ceph-bg: rgba(249, 115, 22, 0.15);
      --zfs-color: #0ea5e9;
      --zfs-bg: rgba(14, 165, 233, 0.15);
      --os-color: #10b981;
      --os-bg: rgba(16, 185, 129, 0.15);
      --free-color: #a855f7;
      --free-bg: rgba(168, 85, 247, 0.15);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      padding: 30px 20px;
      line-height: 1.5;
    }

    .container { max-width: 1200px; margin: 0 auto; }
    
    /* Header */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 25px;
      border-bottom: 2px solid var(--border);
      margin-bottom: 30px;
      flex-wrap: wrap;
      gap: 15px;
    }
    .header-title h1 {
      font-size: 26px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: #fff;
    }
    .header-title p {
      color: var(--muted);
      font-size: 14px;
      margin-top: 4px;
    }
    .badge-bar {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .badge {
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .badge-ceph { background: var(--ceph-bg); color: var(--ceph-color); border: 1px solid var(--ceph-color); }
    .badge-zfs { background: var(--zfs-bg); color: var(--zfs-color); border: 1px solid var(--zfs-color); }
    .badge-os { background: var(--os-bg); color: var(--os-color); border: 1px solid var(--os-color); }
    .badge-free { background: var(--free-bg); color: var(--free-color); border: 1px solid var(--free-color); }

    /* Print Controls */
    .print-bar {
      background: #1e293b;
      padding: 15px 20px;
      border-radius: 12px;
      margin-bottom: 30px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border: 1px solid var(--border);
    }
    .btn-print {
      background: #2563eb;
      color: #fff;
      border: none;
      padding: 10px 20px;
      font-size: 14px;
      font-weight: 700;
      border-radius: 8px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-print:hover { background: #1d4ed8; }

    /* Sticker Grid */
    .sticker-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
      margin-bottom: 40px;
    }

    /* Individual Sticker Card */
    .sticker-card {
      background: #111827;
      border: 2px dashed #475569;
      border-radius: 10px;
      padding: 18px;
      position: relative;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
      page-break-inside: avoid;
    }
    .sticker-card.ceph { border-color: var(--ceph-color); }
    .sticker-card.zfs { border-color: var(--zfs-color); }
    .sticker-card.os { border-color: var(--os-color); }
    .sticker-card.free { border-color: var(--free-color); }

    .sticker-top {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
      margin-bottom: 12px;
    }
    .sticker-node {
      font-size: 12px;
      font-weight: 700;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 1px;
    }
    .sticker-bay {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 700;
      background: #374151;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .sticker-role {
      font-size: 18px;
      font-weight: 800;
      margin-bottom: 4px;
      letter-spacing: -0.3px;
    }
    .role-ceph { color: var(--ceph-color); }
    .role-zfs { color: var(--zfs-color); }
    .role-os { color: var(--os-color); }
    .role-free { color: var(--free-color); }

    .sticker-role-detail {
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 14px;
      min-height: 20px;
    }

    .sticker-sn-box {
      background: #000;
      padding: 10px;
      border-radius: 6px;
      text-align: center;
      margin-bottom: 12px;
      border: 1px solid #374151;
    }
    .sticker-sn-label {
      font-size: 10px;
      color: #9ca3af;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 2px;
    }
    .sticker-sn-val {
      font-family: 'JetBrains Mono', monospace;
      font-size: 19px;
      font-weight: 700;
      letter-spacing: 2px;
      color: #38bdf8;
    }

    .sticker-meta {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      font-size: 11px;
      color: #94a3b8;
    }
    .sticker-meta-item span {
      display: block;
      color: #e2e8f0;
      font-weight: 600;
      font-size: 12px;
    }

    /* Print Styles */
    @media print {
      body {
        background: #fff !important;
        color: #000 !important;
        padding: 0;
      }
      .print-bar { display: none; }
      .sticker-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: 15px;
      }
      .sticker-card {
        background: #fff !important;
        border: 2px dashed #000 !important;
        box-shadow: none !important;
        color: #000 !important;
      }
      .sticker-sn-box {
        background: #f1f5f9 !important;
        border: 1px solid #000 !important;
      }
      .sticker-sn-val { color: #000 !important; }
      .role-ceph { color: #c2410c !important; }
      .role-zfs { color: #0369a1 !important; }
      .role-os { color: #047857 !important; }
      .sticker-node, .sticker-role-detail, .sticker-meta { color: #475569 !important; }
      .sticker-meta-item span { color: #000 !important; }
      .sticker-bay { background: #e2e8f0 !important; color: #000 !important; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="header-title">
        <h1>Physical Drive Sticker Sheet</h1>
EOF_HTML_HEAD

    cat << EOF_HTML_META >> "$outfile"
        <p>Proxmox Node: <strong>${HOSTNAME}</strong> &bull; Generated: ${TIMESTAMP}</p>
      </div>
      <div class="badge-bar">
        <span class="badge badge-ceph">&bull; CEPH OSDs: ${ceph_count}</span>
        <span class="badge badge-zfs">&bull; ZFS Disks: ${zfs_count}</span>
        <span class="badge badge-os">&bull; Host OS: ${os_count}</span>
        <span class="badge badge-free">&bull; Free / Raw: ${free_count}</span>
      </div>
    </div>

    <div class="print-bar">
      <div>
        <strong>Ready to paste stickers?</strong> Click <em>Print Stickers</em>, select <em>Save as PDF</em> or print to standard sticker paper.
      </div>
      <button class="btn-print" onclick="window.print()">🖨️ Print Stickers</button>
    </div>

    <div class="sticker-grid">
EOF_HTML_META

    for dev in $sorted_devs; do
        local role="${DISK_ROLES[$dev]}"
        local details="${DISK_ROLE_DETAILS[$dev]}"
        local serial="${DISK_SERIALLIST[$dev]}"
        local model="${DISK_MODELLIST[$dev]}"
        local size="${DISK_SIZELIST[$dev]}"
        local type="${DISK_TYPELIST[$dev]}"
        local slot="${DISK_SLOTLIST[$dev]}"
        local wwn="${DISK_WWNLIST[$dev]}"
        
        local card_class="other"
        local role_class="role-other"
        case "$role" in
            "CEPH")   card_class="ceph"; role_class="role-ceph" ;;
            "ZFS")    card_class="zfs";  role_class="role-zfs" ;;
            "PVE-OS") card_class="os";   role_class="role-os" ;;
            "FREE")   card_class="free"; role_class="role-free" ;;
        esac
        
        cat << EOF_CARD >> "$outfile"
      <div class="sticker-card ${card_class}">
        <div class="sticker-top">
          <span class="sticker-node">Node: ${HOSTNAME}</span>
          <span class="sticker-bay">${slot}</span>
        </div>
        <div class="sticker-role ${role_class}">${role}</div>
        <div class="sticker-role-detail">${details}</div>
        <div class="sticker-sn-box">
          <div class="sticker-sn-label">Physical Serial Number (Verify on Drive)</div>
          <div class="sticker-sn-val">${serial}</div>
        </div>
        <div class="sticker-meta">
          <div class="sticker-meta-item">Device: <span>${dev}</span></div>
          <div class="sticker-meta-item">Size & Type: <span>${size} (${type})</span></div>
          <div class="sticker-meta-item">Model: <span>${model}</span></div>
          <div class="sticker-meta-item">WWN: <span>${wwn:0:18}...</span></div>
        </div>
      </div>
EOF_CARD
    done

    cat << 'EOF_HTML_FOOT' >> "$outfile"
    </div>
  </div>
</body>
</html>
EOF_HTML_FOOT

    echo -e "${GREEN}✓ HTML visual sticker sheet generated:${RESET} ${BOLD}$outfile${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Physical Drive LED Blinking / Locator
# ─────────────────────────────────────────────────────────────────────────────
blink_drive_led() {
    local target="$1" # /dev/sda or serial number
    local duration="${2:-15}" # seconds
    
    if [[ -z "$target" ]]; then
        echo -e "${RED}Error: Please specify a device name (e.g. /dev/sda) or serial number to blink.${RESET}"
        return 1
    fi
    
    # Resolve target if serial number was given
    local target_dev="$target"
    if [[ ! -b "$target" ]]; then
        for d in "${!DISK_SERIALLIST[@]}"; do
            if [[ "${DISK_SERIALLIST[$d]}" == "$target" ]]; then
                target_dev="$d"
                break
            fi
        done
    fi
    
    if [[ ! -b "$target_dev" ]]; then
        echo -e "${RED}Error: Block device '$target_dev' not found on this system.${RESET}"
        return 1
    fi
    
    local sn="${DISK_SERIALLIST[$target_dev]:-Unknown}"
    local slot="${DISK_SLOTLIST[$target_dev]:-Unknown}"
    local role="${DISK_ROLES[$target_dev]:-Unknown}"
    
    echo -e "\n${BOLD}${CYAN}=== PHYSICAL DRIVE LOCATOR (LED BLINK) ===${RESET}"
    echo -e "  Target Device : ${WHITE}${BOLD}$target_dev${RESET}"
    echo -e "  Serial Number : ${CYAN}${BOLD}$sn${RESET}"
    echo -e "  Chassis Slot  : ${WHITE}$slot${RESET}"
    echo -e "  Storage Role  : ${ORANGE}${BOLD}$role${RESET}"
    echo -e "  Blink Duration: ${WHITE}${BOLD}$duration seconds${RESET}\n"
    
    echo -e "${YELLOW}>> Look at your physical server chassis front drive bays now! <<${RESET}"
    
    # 1. If PERCCLI is available, activate hardware locate LED on Dell backplane
    local used_perccli=0
    local perc_target="${PERCCLI_LOCATE_MAP[$sn]:-}"
    if [[ -n "$PERCCLI_BIN" && -n "$perc_target" ]]; then
        echo -e "  [1/3] Activating Dell hardware drive tray LED via ${CYAN}$PERCCLI_BIN $perc_target start locate${RESET}..."
        $PERCCLI_BIN "$perc_target" start locate &>/dev/null && used_perccli=1 || true
    fi

    # 2. If ledctl is available, turn on enclosure fault/locate LED
    local used_ledctl=0
    if command -v ledctl &>/dev/null; then
        echo -e "  [2/3] Activating enclosure locate LED via ${CYAN}ledctl locate=$target_dev${RESET}..."
        ledctl "locate=$target_dev" 2>/dev/null && used_ledctl=1 || true
    fi
    
    # 3. Activity LED pulsing via safe, non-destructive direct read
    echo -e "  [3/3] Pulsing drive activity LED with non-destructive read burst..."
    local end_time=$((SECONDS + duration))
    while (( SECONDS < end_time )); do
        dd if="$target_dev" of=/dev/null bs=1M count=100 iflag=direct status=none 2>/dev/null || \
        dd if="$target_dev" of=/dev/null bs=512 count=1000 status=none 2>/dev/null || true
        sleep 0.2
        printf "."
    done
    echo ""
    
    # Turn off hardware LEDs
    if [[ $used_perccli -eq 1 ]]; then
        echo -e "  Turning off Dell hardware locate LED via ${CYAN}$PERCCLI_BIN $perc_target stop locate${RESET}..."
        $PERCCLI_BIN "$perc_target" stop locate &>/dev/null || true
    fi
    if [[ $used_ledctl -eq 1 ]]; then
        echo -e "  Turning off enclosure locate LED via ${CYAN}ledctl locate_off=$target_dev${RESET}..."
        ledctl "locate_off=$target_dev" 2>/dev/null || true
    fi
    
    echo -e "\n${GREEN}✓ Blink completed!${RESET} Did you locate the drive bay? You can now paste the sticker on that slot."
}

# ─────────────────────────────────────────────────────────────────────────────
# Cluster-Wide Scan via SSH / Proxmox Cluster
# ─────────────────────────────────────────────────────────────────────────────
run_cluster_scan() {
    echo -e "\n${BOLD}${CYAN}=== CLUSTER-WIDE HARD DRIVE SCANNER ===${RESET}"
    local nodes=()
    
    # Check if this is a Proxmox cluster node
    if command -v pvecm &>/dev/null; then
        while read -r n; do
            [[ -n "$n" ]] && nodes+=("$n")
        done < <(pvecm nodes 2>/dev/null | awk 'NR>2 {print $3}' || true)
    fi
    
    # Fallback to configured cluster IPs
    if ((${#nodes[@]} == 0)); then
        echo -e "${DIM}Using default cluster node IPs: 10.31.6.172, 10.31.6.173, 10.31.6.174${RESET}"
        read -r -p "Enter nodes/IPs or press Enter for defaults [10.31.6.172 10.31.6.173 10.31.6.174]: " user_nodes
        if [[ -n "$user_nodes" ]]; then
            for un in $user_nodes; do
                nodes+=("$un")
            done
        else
            nodes=("10.31.6.172" "10.31.6.173" "10.31.6.174")
        fi
    fi
    
    if ((${#nodes[@]} == 0)); then
        echo -e "${RED}No nodes specified. Aborting cluster scan.${RESET}"
        return 1
    fi
    
    echo -e "Target Cluster Nodes: ${BOLD}${nodes[*]}${RESET}\n"
    
    local cluster_html="${OUTPUT_DIR}/harddrive_stickers_ALL_NODES.html"
    local cluster_csv="${OUTPUT_DIR}/harddrive_stickers_ALL_NODES.csv"
    mkdir -p "$OUTPUT_DIR"
    
    echo "Node,Bay_Slot,Device,Role,Role_Details,Serial_Number,Capacity,Media_Type,Model,WWN,Sticker_Top_Line,Sticker_Bottom_Line" > "$cluster_csv"
    
    for node in "${nodes[@]}"; do
        echo -e "${BOLD}${CYAN}────────────────────────────────────────────────────────────────────${RESET}"
        echo -e "${BOLD}Scanning Node: ${WHITE}$node${RESET}..."
        
        if [[ "$node" == "$HOSTNAME" || "$node" == "localhost" ]]; then
            scan_system_disks
            display_terminal_table
            generate_csv_export "${OUTPUT_DIR}/harddrive_stickers_${node}.csv"
            generate_html_sheet "${OUTPUT_DIR}/harddrive_stickers_${node}.html"
            tail -n +2 "${OUTPUT_DIR}/harddrive_stickers_${node}.csv" >> "$cluster_csv" 2>/dev/null || true
        else
            # Copy and execute script remotely via SSH
            echo -e "Connecting to $node via SSH..."
            if ssh -o ConnectTimeout=5 -o BatchMode=yes "root@$node" "true" 2>/dev/null; then
                ssh "root@$node" "bash -s -- --csv-remote" < "$0" > "${OUTPUT_DIR}/remote_${node}.csv" 2>/dev/null
                if [[ -s "${OUTPUT_DIR}/remote_${node}.csv" ]]; then
                    tail -n +2 "${OUTPUT_DIR}/remote_${node}.csv" >> "$cluster_csv"
                    echo -e "${GREEN}✓ Received scan results from $node${RESET}"
                else
                    echo -e "${YELLOW}[!] Warning: No CSV returned from $node. Ensure root SSH key is configured.${RESET}"
                fi
            else
                echo -e "${RED}[!] SSH connection to root@$node failed or requires password.${RESET}"
            fi
        fi
    done
    
    echo -e "\n${GREEN}${BOLD}✓ Cluster scan complete! Combined CSV saved to: $cluster_csv${RESET}\n"
}

# ─────────────────────────────────────────────────────────────────────────────
# Interactive Menu Mode
# ─────────────────────────────────────────────────────────────────────────────
interactive_menu() {
    check_root
    scan_system_disks
    
    while true; do
        clear
        echo -e "${BOLD}${CYAN}======================================================================${RESET}"
        echo -e "       ${BOLD}${WHITE}PROXMOX HARD DRIVE STICKER & STORAGE FINDER${RESET}"
        echo -e "       ${DIM}Identify Ceph, ZFS, OS & Unused drives for physical labeling${RESET}"
        echo -e "${BOLD}${CYAN}======================================================================${RESET}"
        echo -e "  Current Host : ${WHITE}${BOLD}$HOSTNAME${RESET}"
        echo -e "  Total Disks  : ${WHITE}${BOLD}${#DISK_ROLES[@]}${RESET}"
        echo -e "${CYAN}----------------------------------------------------------------------${RESET}"
        echo -e "  ${BOLD}1)${RESET}  View Storage Role & Serial Number Table (Live Scan)"
        echo -e "  ${BOLD}2)${RESET}  Generate Printable Sticker Cut-Out Labels (.txt)"
        echo -e "  ${BOLD}3)${RESET}  Generate Visual HTML Sticker Sheet (.html)"
        echo -e "  ${BOLD}4)${RESET}  Export to CSV (for Excel / Label Printers)"
        echo -e "  ${BOLD}5)${RESET}  ${YELLOW}Blink Drive LED / Physical Bay Locator${RESET} (Verify before pasting!)"
        echo -e "  ${BOLD}6)${RESET}  Run Cluster-Wide Scan (All Proxmox Nodes)"
        echo -e "  ${BOLD}7)${RESET}  Check / Install Missing Helper Packages"
        echo -e "  ${BOLD}8)${RESET}  Exit"
        echo -e "${CYAN}----------------------------------------------------------------------${RESET}"
        read -r -p "Select an option [1-8]: " choice
        
        case "$choice" in
            1)
                scan_system_disks
                display_terminal_table
                read -r -p "Press Enter to return to menu..."
                ;;
            2)
                scan_system_disks
                generate_text_stickers
                echo ""
                read -r -p "Press Enter to return to menu..."
                ;;
            3)
                scan_system_disks
                generate_html_sheet
                echo ""
                read -r -p "Press Enter to return to menu..."
                ;;
            4)
                scan_system_disks
                generate_csv_export
                echo ""
                read -r -p "Press Enter to return to menu..."
                ;;
            5)
                echo ""
                echo -e "${BOLD}Select a drive to blink its physical chassis LED:${RESET}"
                local idx=1
                local dev_indices=()
                for d in $(printf '%s\n' "${!DISK_ROLES[@]}" | sort); do
                    printf "  ${BOLD}%2d)${RESET} %-10s | S/N: %-16s | %-12s | %s\n" \
                        "$idx" "$d" "${DISK_SERIALLIST[$d]}" "${DISK_ROLES[$d]}" "${DISK_ROLE_DETAILS[$d]}"
                    dev_indices+=("$d")
                    ((idx++))
                done
                echo ""
                read -r -p "Enter number [1-$((idx-1))] or drive path: " sel
                local chosen=""
                if [[ "$sel" =~ ^[0-9]+$ ]] && (( sel >= 1 && sel < idx )); then
                    chosen="${dev_indices[$((sel-1))]}"
                elif [[ -b "$sel" ]]; then
                    chosen="$sel"
                fi
                
                if [[ -n "$chosen" ]]; then
                    read -r -p "Enter blink duration in seconds [default 15]: " dur
                    dur="${dur:-15}"
                    blink_drive_led "$chosen" "$dur"
                else
                    echo -e "${RED}Invalid selection.${RESET}"
                fi
                echo ""
                read -r -p "Press Enter to return to menu..."
                ;;
            6)
                run_cluster_scan
                read -r -p "Press Enter to return to menu..."
                ;;
            7)
                check_packages
                read -r -p "Install optional tools now? (y/N): " install_ans
                if [[ "$install_ans" =~ ^[yY]$ ]]; then
                    install_packages
                fi
                read -r -p "Press Enter to return to menu..."
                ;;
            8|q|Q)
                echo -e "\n${GREEN}Exiting. Good luck with your drive stickers!${RESET}\n"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option.${RESET}"
                sleep 1
                ;;
        esac
    done
}

# ─────────────────────────────────────────────────────────────────────────────
# CLI Entrypoint & Argument Handling
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
    cat << EOF
PROXMOX DRIVE STICKER & STORAGE ROLE FINDER
Usage: $0 [OPTIONS]

Options:
  -h, --help                 Show this help message and exit
  -s, --scan                 Scan all drives and display formatted terminal table
  -t, --stickers [FILE]      Generate text cut-out sticker sheet (default: output/harddrive_stickers_<node>.txt)
  -H, --html [FILE]          Generate visual HTML sticker sheet (default: output/harddrive_stickers_<node>.html)
  -c, --csv [FILE]           Export drives to CSV for Excel / label printers
  -b, --blink <DEV|SN> [SEC] Blink physical drive chassis LED (e.g. -b /dev/sda 15)
  -C, --cluster              Scan all nodes across the Proxmox cluster
  -p, --check-pkgs           Check for required and recommended diagnostic packages
  --install-pkgs             Install recommended tools (smartmontools, ledmon, lsscsi)
  --csv-remote               Output pure CSV to stdout (used by cluster SSH scan)

If run with no arguments, launches the Interactive Menu.
EOF
}

main() {
    mkdir -p "$OUTPUT_DIR"
    
    if [[ $# -eq 0 ]]; then
        interactive_menu
        exit 0
    fi
    
    case "$1" in
        -h|--help)
            show_help
            ;;
        -s|--scan)
            check_root
            scan_system_disks
            display_terminal_table
            ;;
        -t|--stickers)
            check_root
            scan_system_disks
            generate_text_stickers "${2:-}"
            ;;
        -H|--html)
            check_root
            scan_system_disks
            generate_html_sheet "${2:-}"
            ;;
        -c|--csv)
            check_root
            scan_system_disks
            generate_csv_export "${2:-}"
            ;;
        -b|--blink)
            if [[ -z "${2:-}" ]]; then
                echo -e "\033[1;31mError: --blink requires a drive path (e.g. /dev/sda) or serial number.\033[0m"
                echo "Usage: $0 -b /dev/sda [duration_seconds]"
                exit 1
            fi
            check_root
            scan_system_disks
            blink_drive_led "$2" "${3:-15}"
            ;;
        -C|--cluster)
            check_root
            run_cluster_scan
            ;;
        -p|--check-pkgs)
            check_packages
            ;;
        --install-pkgs)
            check_root
            install_packages
            ;;
        --csv-remote)
            check_root
            scan_system_disks
            local sorted_devs
            sorted_devs=$(printf '%s\n' "${!DISK_ROLES[@]}" | sort)
            echo "Node,Bay_Slot,Device,Role,Role_Details,Serial_Number,Capacity,Media_Type,Model,WWN,Sticker_Top_Line,Sticker_Bottom_Line"
            for dev in $sorted_devs; do
                local role="${DISK_ROLES[$dev]}"
                local details="${DISK_ROLE_DETAILS[$dev]//\"/\"\"}"
                local serial="${DISK_SERIALLIST[$dev]}"
                local model="${DISK_MODELLIST[$dev]//\"/\"\"}"
                local size="${DISK_SIZELIST[$dev]}"
                local type="${DISK_TYPELIST[$dev]}"
                local slot="${DISK_SLOTLIST[$dev]}"
                local wwn="${DISK_WWNLIST[$dev]}"
                local top_line="${HOSTNAME} | ${slot} | ${role}"
                local bot_line="S/N: ${serial} (${size})"
                echo "\"$HOSTNAME\",\"$slot\",\"$dev\",\"$role\",\"$details\",\"$serial\",\"$size\",\"$type\",\"$model\",\"$wwn\",\"$top_line\",\"$bot_line\""
            done
            ;;
        *)
            echo -e "${RED}Unknown argument: $1${RESET}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
