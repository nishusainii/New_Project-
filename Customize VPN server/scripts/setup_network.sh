#!/usr/bin/env bash
# Prepare the host for the SSL VPN server (requires root):
#   - enables IP forwarding
#   - NAT (MASQUERADE) for the VPN subnet via iptables
# The TUN device itself is created by the server on startup.
#
# Usage:  sudo ./scripts/setup_network.sh [wan_interface]
# Example: sudo ./scripts/setup_network.sh enp44s0

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WAN="${1:-}"
VPN_SUBNET="${VPN_SUBNET:-10.8.0.0/24}"
TUN_IFACE="ssl0"

if [[ $EUID -ne 0 ]]; then
    echo "run with sudo: sudo $0 [wan_interface]" >&2
    exit 1
fi

if [[ -z "$WAN" ]]; then
    WAN="$(ip route show default | awk '/default/ {for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -1)"
fi
if [[ -z "$WAN" ]]; then
    echo "could not detect the WAN interface; pass it explicitly" >&2
    exit 1
fi

echo "==> enabling IP forwarding"
sysctl -w net.ipv4.ip_forward=1 >/dev/null
sysctl -w net.ipv6.conf.all.forwarding=1 >/dev/null

echo "==> configuring NAT for $VPN_SUBNET via $WAN"
iptables -t nat -C POSTROUTING -s "$VPN_SUBNET" -o "$WAN" -j MASQUERADE 2>/dev/null \
    || iptables -t nat -A POSTROUTING -s "$VPN_SUBNET" -o "$WAN" -j MASQUERADE
iptables -C FORWARD -i "${TUN_IFACE}+" -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -i "${TUN_IFACE}+" -j ACCEPT
iptables -C FORWARD -o "${TUN_IFACE}+" -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -o "${TUN_IFACE}+" -m state --state RELATED,ESTABLISHED -j ACCEPT

echo "==> network ready:"
echo "    WAN:        $WAN"
echo "    VPN subnet: $VPN_SUBNET"
echo "    TUN iface:  ${TUN_IFACE} (created by the server on start)"
echo
echo "start the server with:  python3 vpn_server.py start"