#!/usr/bin/env bash
# Reverts both Pi ethernet interfaces back to DHCP
# Run this directly on the Pi if the static IP made it unreachable

set -e

echo "=== REVERTING TO DHCP ON BOTH INTERFACES ==="

sudo tee /etc/netplan/50-cloud-init.yaml << 'NETPLAN_EOF'
network:
  version: 2
  renderer: networkd
  ethernets:
    # Built-in Ethernet Port (eth0) - DHCP
    eth0:
      dhcp4: true
      dhcp6: false
      nameservers:
        addresses:
          - 10.31.4.1
          - 10.31.4.3

    # USB Ethernet Adapter - DHCP
    enx207bd28aa480:
      match:
        macaddress: 20:7b:d2:8a:a4:80
      set-name: enx207bd28aa480
      dhcp4: true
      dhcp6: false
      nameservers:
        addresses:
          - 10.31.4.1
          - 10.31.4.3
NETPLAN_EOF

sudo chmod 600 /etc/netplan/50-cloud-init.yaml
echo "Applying Netplan (DHCP on both interfaces)..."
sudo netplan apply

echo "Waiting 5 seconds for DHCP leas.."
sleep 5

echo "=== CURRENT IP ADDRESSES ==="
ip -4 addr show eth0 || true
ip -4 addr show enx207bd28aa480 || true
echo "=== DONE ==="
