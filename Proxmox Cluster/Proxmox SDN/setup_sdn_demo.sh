#!/usr/bin/env bash
# ==============================================================================
# Script: setup_sdn_demo.sh
# Purpose: Automate Proxmox SDN Configuration via CLI
# Usage: Run as root on any Proxmox VE node in the cluster
# ==============================================================================

set -euo pipefail

echo "========================================================"
echo "    PROXMOX VE SDN AUTOMATED CLI SETUP SCRIPT"
echo "========================================================"

# 1. Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run this script as root."
  exit 1
fi

# 2. Install SDN packages & dependencies
echo "[*] Step 1: Installing SDN packages & dependencies..."
apt update -y
apt install -y libpve-network-perl ifupdown2 dnsmasq frr-pythontools frr

# Stop & disable systemd-resolved to prevent DNS/DHCP conflict on port 53
systemctl disable --now systemd-resolved 2>/dev/null || true

# 3. Create a VLAN Zone (using physical bridge vmbr0)
ZONE_NAME="vlan-zone"
echo "[*] Step 2: Creating SDN VLAN Zone: ${ZONE_NAME}..."
if pvesdn zone list | grep -qw "${ZONE_NAME}"; then
  echo "    Zone '${ZONE_NAME}' already exists. Skipping creation."
else
  pvesdn zone create "${ZONE_NAME}" --type vlan --bridge vmbr0 --ipam pve
  echo "    Zone '${ZONE_NAME}' created."
fi

# 4. Create a Virtual Network (VNet)
VNET_NAME="vnet100"
VLAN_TAG=100
echo "[*] Step 3: Creating VNet: ${VNET_NAME} with Tag: ${VLAN_TAG}..."
if pvesdn vnet list | grep -qw "${VNET_NAME}"; then
  echo "    VNet '${VNET_NAME}' already exists. Skipping creation."
else
  pvesdn vnet create "${VNET_NAME}" --zone "${ZONE_NAME}" --tag "${VLAN_TAG}" --alias "Production VLAN 100"
  echo "    VNet '${VNET_NAME}' created."
fi

# 5. Create a Subnet with Gateway & DHCP Range
SUBNET_CIDR="10.100.0.0/24"
GATEWAY_IP="10.100.0.1"
DHCP_START="10.100.0.50"
DHCP_END="10.100.0.200"

echo "[*] Step 4: Configuring Subnet: ${SUBNET_CIDR}..."
if pvesdn subnet list "${VNET_NAME}" 2>/dev/null | grep -qw "${SUBNET_CIDR}"; then
  echo "    Subnet '${SUBNET_CIDR}' already exists. Skipping creation."
else
  pvesdn subnet create "${VNET_NAME}" "${SUBNET_CIDR}" \
    --gateway "${GATEWAY_IP}" \
    --snat 1 \
    --dhcp-range "start-address=${DHCP_START},end-address=${DHCP_END}" \
    --dhcp-dns-server "1.1.1.1"
  echo "    Subnet '${SUBNET_CIDR}' created with DHCP & SNAT."
fi

# 6. Apply SDN Changes cluster-wide
echo "[*] Step 5: Applying & Reloading SDN configuration..."
pvesdn reload

# 7. Print Status
echo ""
echo "========================================================"
echo "    SDN CONFIGURATION APPLIED SUCCESSFULLY!"
echo "========================================================"
pvesdn status
echo ""
echo "To attach a VM (e.g. VMID 100) to this VNet:"
echo "  qm set 100 --net0 virtio,bridge=${VNET_NAME},firewall=1"
echo ""
echo "To attach an LXC container (e.g. CTID 200) with DHCP:"
echo "  pct set 200 --net0 name=eth0,bridge=${VNET_NAME},ip=dhcp,firewall=1"
echo "========================================================"
