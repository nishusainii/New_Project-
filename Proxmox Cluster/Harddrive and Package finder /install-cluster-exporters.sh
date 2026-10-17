#!/usr/bin/env bash

###############################################################################
# PROXMOX CLUSTER PROMETHEUS EXPORTERS INSTALLER & MANAGER
# Author: Nishu Saini
# Version: 1.0.0
#
# Supported Exporters:
#   1. Node Exporter       (Port 9100) - CPU, RAM, Disk, Network, OS
#   2. IPMI Exporter       (Port 9290) - Dell Server Hardware Sensors (Fans, Temp, PSU)
#   3. Smartctl Exporter   (Port 9633) - Drive S.M.A.R.T Health, Temp, Bad Sectors
#   4. Ceph Exporter       (Port 9283) - Native Ceph MGR Prometheus Metrics
#   5. ZFS Exporter        (Port 9134) - ZFS Pool (zfs-ha) Health, ARC, Vdevs
#
# Cluster Nodes:
#   - prox22 (10.31.6.172)
#   - prox23 (10.31.6.173)
#   - prox24 (10.31.6.174)
###############################################################################

set -euo pipefail

# Style definitions
BOLD="\033[1m"
DIM="\033[2m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
RED="\033[1;31m"
CYAN="\033[1;36m"
WHITE="\033[1;37m"
RESET="\033[0m"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${SCRIPT_DIR}/bin"
DEFAULT_NODES=("10.31.6.172" "10.31.6.173" "10.31.6.174")

# ─────────────────────────────────────────────────────────────────────────────
# Root Check
# ─────────────────────────────────────────────────────────────────────────────
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${YELLOW}[!] Re-running with sudo privileges...${RESET}"
        exec sudo bash "$0" "$@"
        exit 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Install Node Exporter (Port 9100)
# ─────────────────────────────────────────────────────────────────────────────
install_node_exporter() {
    echo -e "\n${BOLD}${CYAN}▶ [1/5] Installing Node Exporter (Port 9100)...${RESET}"
    if ! command -v prometheus-node-exporter &>/dev/null && ! command -v node_exporter &>/dev/null; then
        apt-get update -y && apt-get install -y prometheus-node-exporter
    fi
    systemctl enable --now prometheus-node-exporter || systemctl restart prometheus-node-exporter
    echo -e "${GREEN}✓ Node Exporter is active on port 9100.${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# 2. Install IPMI Exporter (Port 9290)
# ─────────────────────────────────────────────────────────────────────────────
install_ipmi_exporter() {
    echo -e "\n${BOLD}${CYAN}▶ [2/5] Installing IPMI Exporter for Dell PowerEdge (Port 9290)...${RESET}"
    apt-get update -y && apt-get install -y prometheus-ipmi-exporter freeipmi-tools ipmitool
    
    # Ensure ipmi kernel modules are loaded
    modprobe ipmi_si 2>/dev/null || true
    modprobe ipmi_devintf 2>/dev/null || true
    
    # Create /etc/modules-load.d/ipmi.conf for persistence
    cat << 'EOF' > /etc/modules-load.d/ipmi.conf
ipmi_si
ipmi_devintf
EOF

    # Configure IPMI exporter to use local in-band monitoring (/etc/prometheus/ipmi_local.yml)
    if [[ -f /etc/default/prometheus-ipmi-exporter ]]; then
        sed -i 's/ipmi_remote\.yml/ipmi_local\.yml/' /etc/default/prometheus-ipmi-exporter
    fi

    # Configure IPMI exporter systemd to run as root for /dev/ipmi0 access if needed
    if [[ -f /lib/systemd/system/prometheus-ipmi-exporter.service ]]; then
        sed -i 's/^User=prometheus/User=root/' /lib/systemd/system/prometheus-ipmi-exporter.service 2>/dev/null || true
        systemctl daemon-reload
    fi

    systemctl enable --now prometheus-ipmi-exporter || systemctl restart prometheus-ipmi-exporter
    echo -e "${GREEN}✓ IPMI Exporter is active on port 9290.${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. Install Smartctl Exporter (Port 9633)
# ─────────────────────────────────────────────────────────────────────────────
install_smartctl_exporter() {
    echo -e "\n${BOLD}${CYAN}▶ [3/5] Installing Smartctl Exporter (Port 9633)...${RESET}"
    apt-get update -y && apt-get install -y smartmontools
    
    # Deploy binary if present in local bin or download
    if [[ -f "${BIN_DIR}/smartctl_exporter" ]]; then
        install -m 755 "${BIN_DIR}/smartctl_exporter" /usr/local/bin/smartctl_exporter
        echo -e "${DIM}✓ Deployed from local ${BIN_DIR}/smartctl_exporter${RESET}"
    elif ! command -v smartctl_exporter &>/dev/null; then
        echo "Downloading smartctl_exporter binary..."
        local tmp=$(mktemp -d)
        local asset="smartctl_exporter-0.13.0.linux-amd64"
        curl -fsSL "https://github.com/prometheus-community/smartctl_exporter/releases/download/v0.13.0/${asset}.tar.gz" -o "$tmp/smartctl.tar.gz"
        tar -xzf "$tmp/smartctl.tar.gz" -C "$tmp"
        install -m 755 "$tmp/${asset}/smartctl_exporter" /usr/local/bin/smartctl_exporter
        rm -rf "$tmp"
    else
        echo -e "${DIM}✓ smartctl_exporter already present at $(command -v smartctl_exporter)${RESET}"
    fi
    
    # Create systemd service
    cat << 'EOF' > /etc/systemd/system/smartctl_exporter.service
[Unit]
Description=Prometheus Smartctl Exporter (Drive Health & Temps)
Documentation=https://github.com/prometheus-community/smartctl_exporter
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/smartctl_exporter --web.listen-address=:9633 --smartctl.device-exclude=sdm
Restart=always
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable --now smartctl_exporter
    echo -e "${GREEN}✓ Smartctl Exporter is active on port 9633.${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Enable Native Ceph Prometheus Exporter (Port 9283)
# ─────────────────────────────────────────────────────────────────────────────
enable_ceph_exporter() {
    echo -e "\n${BOLD}${CYAN}▶ [4/5] Enabling Native Ceph MGR Prometheus Module (Port 9283)...${RESET}"
    if command -v ceph &>/dev/null; then
        ceph mgr module enable prometheus || true
        # Default server port is 9283
        ceph config set mgr mgr/prometheus/server_port 9283 || true
        echo -e "${GREEN}✓ Ceph Prometheus module enabled on port 9283.${RESET}"
    else
        echo -e "${YELLOW}[!] Ceph CLI not found on this node. Skipping Ceph module enable.${RESET}"
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 5. Install ZFS Exporter (Port 9134)
# ─────────────────────────────────────────────────────────────────────────────
install_zfs_exporter() {
    echo -e "\n${BOLD}${CYAN}▶ [5/5] Installing ZFS Exporter for 'zfs-ha' Pool (Port 9134)...${RESET}"
    
    # Deploy binary if present in local bin or download
    if [[ -f "${BIN_DIR}/zfs_exporter" ]]; then
        install -m 755 "${BIN_DIR}/zfs_exporter" /usr/local/bin/zfs_exporter
        echo -e "${DIM}✓ Deployed from local ${BIN_DIR}/zfs_exporter${RESET}"
    elif ! command -v zfs_exporter &>/dev/null; then
        echo "Downloading zfs_exporter binary..."
        local tmp=$(mktemp -d)
        local asset="zfs_exporter-2.3.4.linux-amd64"
        curl -fsSL "https://github.com/pdf/zfs_exporter/releases/download/v2.3.4/${asset}.tar.gz" -o "$tmp/zfs.tar.gz"
        tar -xzf "$tmp/zfs.tar.gz" -C "$tmp"
        install -m 755 "$tmp/${asset}/zfs_exporter" /usr/local/bin/zfs_exporter
        rm -rf "$tmp"
    else
        echo -e "${DIM}✓ zfs_exporter already present at $(command -v zfs_exporter)${RESET}"
    fi

    # Create systemd service
    cat << 'EOF' > /etc/systemd/system/zfs_exporter.service
[Unit]
Description=Prometheus ZFS Exporter (zfs-ha Pool & ARC Stats)
Documentation=https://github.com/pdf/zfs_exporter
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/zfs_exporter --web.listen-address=:9134
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable --now zfs_exporter
    echo -e "${GREEN}✓ ZFS Exporter is active on port 9134.${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Status & Verification Check
# ─────────────────────────────────────────────────────────────────────────────
check_exporters_status() {
    local host="${1:-localhost}"
    echo -e "\n${BOLD}======================================================================${RESET}"
    echo -e "       ${BOLD}${WHITE}PROMETHEUS EXPORTERS HEALTH CHECK${RESET} (Target: ${CYAN}${host}${RESET})"
    echo -e "${BOLD}======================================================================${RESET}"
    printf "${BOLD}%-24s %-8s %-12s %-28s${RESET}\n" "EXPORTER NAME" "PORT" "STATUS" "METRICS COUNT"
    echo -e "${DIM}----------------------------------------------------------------------${RESET}"

    local services=(
        "Node Exporter:9100"
        "IPMI Exporter:9290"
        "Smartctl Exporter:9633"
        "Ceph Exporter:9283"
        "ZFS Exporter:9134"
    )

    for item in "${services[@]}"; do
        local name="${item%%:*}"
        local port="${item##*:}"
        local count=0
        local status="${RED}OFFLINE${RESET}"
        local metrics_label="0 metrics"
        
        # Test HTTP endpoint
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://${host}:${port}/metrics" 2>/dev/null || echo "000")

        if [[ "$http_code" == "200" ]]; then
            local res
            res=$(curl -s --connect-timeout 3 "http://${host}:${port}/metrics" 2>/dev/null || true)
            if [[ -n "$res" ]]; then
                count=$(echo "$res" | grep -v '^#' | grep -c . || true)
            fi

            if [[ "$count" -gt 0 ]]; then
                status="${GREEN}ONLINE${RESET}"
                if [[ "$port" == "9283" ]]; then
                    metrics_label="${count} metrics (Active MGR)"
                else
                    metrics_label="${count} metrics"
                fi
            elif [[ "$port" == "9283" ]]; then
                # Ceph Manager runs in Active/Standby. Standby daemons return HTTP 200 with 0 metrics.
                local active_mgr=""
                if command -v ceph &>/dev/null; then
                    active_mgr=$(ceph mgr stat 2>/dev/null | grep -o '"active_name": *"[^"]*"' | cut -d'"' -f4 || true)
                fi
                if [[ -z "$active_mgr" ]]; then
                    # Fallback to query the HTML link from the root endpoint
                    active_mgr=$(curl -s --connect-timeout 2 "http://${host}:${port}/" 2>/dev/null | grep -o 'http://[^:/]*' | cut -d'/' -f3 || true)
                fi
                status="${CYAN}STANDBY${RESET}"
                if [[ -n "$active_mgr" ]]; then
                    metrics_label="0 metrics (Active: ${active_mgr})"
                else
                    metrics_label="0 metrics (Standby MGR)"
                fi
            else
                status="${GREEN}ONLINE${RESET}"
                metrics_label="0 metrics"
            fi
        fi
        
        printf "%-24s %-8s %-20b %-28s\n" "$name" "$port" "$status" "$metrics_label"
    done
    echo -e "${BOLD}======================================================================${RESET}"
    echo -e "${DIM}ℹ Note: Ceph Exporter is managed cluster-wide by 'ceph-mgr' in Active/Standby mode.${RESET}"
    echo -e "${DIM}  Only the Active MGR serves metrics. Standby nodes automatically take over upon failover.${RESET}\n"
}

# ─────────────────────────────────────────────────────────────────────────────
# Deploy to Entire Cluster via SSH
# ─────────────────────────────────────────────────────────────────────────────
deploy_to_cluster() {
    echo -e "\n${BOLD}${CYAN}=== DEPLOYING EXPORTERS TO ENTIRE PROXMOX CLUSTER ===${RESET}"
    echo -e "Target Nodes: ${BOLD}${DEFAULT_NODES[*]}${RESET}\n"

    for node in "${DEFAULT_NODES[@]}"; do
        echo -e "${BOLD}${WHITE}────────────────────────────────────────────────────────────${RESET}"
        echo -e "${BOLD}▶ Setting up node: ${CYAN}${node}${RESET}..."
        
        # 1. Copy local binaries if available
        ssh "root@$node" "mkdir -p /root/exporter_install/bin /usr/local/bin"
        if [[ -d "$BIN_DIR" ]]; then
            scp -q "${BIN_DIR}/smartctl_exporter" "${BIN_DIR}/zfs_exporter" "root@$node:/usr/local/bin/" 2>/dev/null || true
        fi
        
        # 2. Copy and execute installer remotely
        scp -q "$0" "root@$node:/root/exporter_install/install-cluster-exporters.sh"
        ssh "root@$node" "bash /root/exporter_install/install-cluster-exporters.sh --local-all"
        
        # 3. Check status
        check_exporters_status "$node"
    done

    echo -e "\n${GREEN}${BOLD}✓ All exporters deployed and running across all 3 nodes!${RESET}\n"
}

# ─────────────────────────────────────────────────────────────────────────────
# Prometheus Configuration Generator (prometheus.yml)
# ─────────────────────────────────────────────────────────────────────────────
generate_prometheus_config() {
    local outfile="${SCRIPT_DIR}/prometheus_proxmox_cluster.yml"
    cat << 'EOF' > "$outfile"
# ==============================================================================
# PROMETHEUS SCRAPE CONFIGURATION — 3-NODE PROXMOX CLUSTER
# Target Nodes:
#   prox22 : 10.31.6.172
#   prox23 : 10.31.6.173
#   prox24 : 10.31.6.174
# ==============================================================================

scrape_configs:
  # 1. Proxmox OS & System Metrics (CPU, RAM, Disk IO, Network)
  - job_name: 'proxmox-node-exporter'
    scrape_interval: 15s
    static_configs:
      - targets:
          - '10.31.6.172:9100'
          - '10.31.6.173:9100'
          - '10.31.6.174:9100'
        labels:
          cluster: 'cisai-pve'

  # 2. Dell Server Hardware Sensors (Fans RPM, Temperatures, Power Supplies)
  - job_name: 'proxmox-ipmi'
    scrape_interval: 30s
    static_configs:
      - targets:
          - '10.31.6.172:9290'
          - '10.31.6.173:9290'
          - '10.31.6.174:9290'
        labels:
          cluster: 'cisai-pve'

  # 3. Hard Drive S.M.A.R.T Health (Temps, Bad Sectors, Wear Levels)
  - job_name: 'proxmox-smartctl'
    scrape_interval: 60s
    static_configs:
      - targets:
          - '10.31.6.172:9633'
          - '10.31.6.173:9633'
          - '10.31.6.174:9633'
        labels:
          cluster: 'cisai-pve'

  # 4. Ceph Cluster & OSD Metrics (Scraped from Active Ceph MGR)
  - job_name: 'ceph-mgr'
    scrape_interval: 15s
    static_configs:
      - targets:
          - '10.31.6.172:9283'
          - '10.31.6.173:9283'
          - '10.31.6.174:9283'
        labels:
          cluster: 'ceph'

  # 5. ZFS Pool Health & ARC Metrics ('zfs-ha' RAID-Z2 Pool)
  - job_name: 'proxmox-zfs'
    scrape_interval: 30s
    static_configs:
      - targets:
          - '10.31.6.172:9134'
          - '10.31.6.173:9134'
          - '10.31.6.174:9134'
        labels:
          cluster: 'cisai-pve'
EOF

    echo -e "${GREEN}✓ Prometheus configuration snippet generated at:${RESET} ${BOLD}${outfile}${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Main Entrypoint
# ─────────────────────────────────────────────────────────────────────────────
show_help() {
    cat << EOF
PROMETHEUS CLUSTER EXPORTERS INSTALLER
Usage: $0 [OPTIONS]

Options:
  -h, --help            Show this help message
  --all                 Install all 5 exporters on current local node
  --cluster             Deploy all 5 exporters across all cluster nodes (10.31.6.172, 173, 174)
  --status [HOST]       Check exporters status (default: localhost or specified IP)
  --node                Install Node Exporter only (Port 9100)
  --ipmi                Install IPMI Exporter only (Port 9290)
  --smartctl            Install Smartctl Exporter only (Port 9633)
  --ceph                Enable Ceph Native Prometheus Module only (Port 9283)
  --zfs                 Install ZFS Exporter only (Port 9134)
  --config              Generate Prometheus scrape config (prometheus_proxmox_cluster.yml)
EOF
}

main() {
    if [[ $# -eq 0 ]]; then
        check_root
        echo -e "${BOLD}${CYAN}======================================================================${RESET}"
        echo -e "       ${BOLD}${WHITE}PROXMOX PROMETHEUS EXPORTERS INSTALLATION WIZARD${RESET}"
        echo -e "${BOLD}${CYAN}======================================================================${RESET}"
        echo -e "  ${BOLD}1)${RESET} Install All 5 Exporters on This Local Node"
        echo -e "  ${BOLD}2)${RESET} Deploy All 5 Exporters Across ENTIRE Cluster (prox22, prox23, prox24)"
        echo -e "  ${BOLD}3)${RESET} Check Exporters Health Status"
        echo -e "  ${BOLD}4)${RESET} Generate Prometheus Scrape Configuration (prometheus.yml)"
        echo -e "  ${BOLD}5)${RESET} Exit"
        echo -e "${CYAN}----------------------------------------------------------------------${RESET}"
        read -r -p "Select an option [1-5]: " opt
        case "$opt" in
            1)
                install_node_exporter
                install_ipmi_exporter
                install_smartctl_exporter
                enable_ceph_exporter
                install_zfs_exporter
                check_exporters_status "localhost"
                ;;
            2)
                deploy_to_cluster
                ;;
            3)
                check_exporters_status "localhost"
                ;;
            4)
                generate_prometheus_config
                ;;
            5|q|Q)
                exit 0
                ;;
            *)
                echo "Invalid option."
                ;;
        esac
        exit 0
    fi

    case "$1" in
        -h|--help)
            show_help
            ;;
        --local-all|--all)
            check_root
            install_node_exporter
            install_ipmi_exporter
            install_smartctl_exporter
            enable_ceph_exporter
            install_zfs_exporter
            check_exporters_status "localhost"
            ;;
        --cluster)
            deploy_to_cluster
            ;;
        --status)
            if [[ "$2" == "cluster" || "$2" == "all" ]]; then
                for n in "${DEFAULT_NODES[@]}"; do
                    check_exporters_status "$n"
                done
            else
                check_exporters_status "${2:-localhost}"
            fi
            ;;
        --node)
            check_root
            install_node_exporter
            ;;
        --ipmi)
            check_root
            install_ipmi_exporter
            ;;
        --smartctl)
            check_root
            install_smartctl_exporter
            ;;
        --ceph)
            check_root
            enable_ceph_exporter
            ;;
        --zfs)
            check_root
            install_zfs_exporter
            ;;
        --config)
            generate_prometheus_config
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
