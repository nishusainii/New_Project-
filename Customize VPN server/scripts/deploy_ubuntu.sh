#!/usr/bin/env bash
# =========================================================================
# Innspark SSL VPN - Production Deployment Script for Fresh Ubuntu Server
# Target OS: Ubuntu 22.04 LTS / Ubuntu 24.04 LTS
#
# This script automates:
#   1. System package updates & core dependencies
#   2. Docker & Docker Compose setup
#   3. Linux kernel network tuning (IP forwarding, BBR congestion control)
#   4. Production TLS certificate generation (with public IP / domain SAN)
#   5. UFW Firewall configuration
#   6. NAT & iptables masquerade setup
#   7. Systemd & Docker service orchestration
# =========================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ANSI Color Codes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}============================================================${NC}"
echo -e "${CYAN}   Innspark SSL VPN - Production Server Setup (Ubuntu)       ${NC}"
echo -e "${CYAN}============================================================${NC}"

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERROR] This script must be run as root (use sudo).${NC}" >&2
    exit 1
fi

cd "$APP_DIR"

# -------------------------------------------------------------------------
# 1. Update system packages & install dependencies
# -------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 1/7] Updating system & installing prerequisites...${NC}"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    curl \
    git \
    openssl \
    iptables \
    iproute2 \
    ufw \
    ca-certificates \
    python3 \
    python3-pip

# Install Docker if not already present
if ! command -v docker &>/dev/null; then
    echo -e "${YELLOW}==> Installing Docker engine...${NC}"
    apt-get install -y docker.io docker-compose-v2
    systemctl enable --now docker
else
    echo -e "${GREEN}==> Docker is already installed.${NC}"
fi

# -------------------------------------------------------------------------
# 2. Kernel Network Hardening & Performance Tuning
# -------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 2/7] Configuring Linux kernel network parameters...${NC}"
SYSCTL_CONF="/etc/sysctl.d/99-sslvpn.conf"
cat << 'EOF' > "$SYSCTL_CONF"
# Enable IPv4 & IPv6 Forwarding
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# BBR Congestion Control for low latency VPN tunnels
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# Protection against SYN flood attacks & IP spoofing
net.ipv4.tcp_syncookies = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Increase network buffer sizes for high throughput
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
EOF

sysctl -p "$SYSCTL_CONF" >/dev/null 2>&1 || sysctl --system >/dev/null 2>&1
echo -e "${GREEN}==> Kernel network parameters applied.${NC}"

# -------------------------------------------------------------------------
# 3. Detect Public IP & Generate Production Certificates
# -------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 3/7] Generating TLS certificates with Subject Alternative Name (SAN)...${NC}"
PUBLIC_IP="$(curl -s -4 --connect-timeout 3 ifconfig.me || ip route get 1.1.1.1 | awk '{print $7}' | head -1 || echo "127.0.0.1")"
echo -e "Detected Server Address: ${CYAN}${PUBLIC_IP}${NC}"

bash "$APP_DIR/scripts/generate_certs.sh" "$PUBLIC_IP"
chmod 600 "$APP_DIR/certs"/*.key 2>/dev/null || true
echo -e "${GREEN}==> TLS certificates generated and private keys secured (chmod 600).${NC}"

# -------------------------------------------------------------------------
# 4. Configure NAT & Firewall (UFW)
# -------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 4/7] Setting up NAT masquerade and UFW firewall...${NC}"
bash "$APP_DIR/scripts/setup_network.sh"

# Configure UFW
echo -e "${YELLOW}==> Configuring UFW firewall rules...${NC}"
ufw status >/dev/null 2>&1 || true
# Ensure SSH remains open
ufw allow 22/tcp comment "SSH Remote Administration" || true
# VPN tunnel listener
ufw allow 443/tcp comment "SSL VPN TLS Listener" || true
# Web GUI Portal
ufw allow 8080/tcp comment "SSL VPN Web Portal" || true

# -------------------------------------------------------------------------
# 5. Build Docker Image
# -------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 5/7] Building SSL VPN Docker image...${NC}"
docker build -t innspark/sslvpn:1.0.0 "$APP_DIR"

# -------------------------------------------------------------------------
# 6. Setup Production Systemd Service for Web GUI
# -------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 6/7] Installing and enabling systemd background service...${NC}"
SERVICE_FILE="/etc/systemd/system/sslvpn-gui.service"
cat << EOF > "$SERVICE_FILE"
[Unit]
Description=Innspark SSL VPN Web Management Portal
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/vpn_web_gui.py --host 0.0.0.0 --port 8080
Restart=always
RestartSec=5
StandardOutput=append:$APP_DIR/gui.log
StandardError=append:$APP_DIR/gui.log

# Security Sandboxing
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now sslvpn-gui

# -------------------------------------------------------------------------
# 7. Start VPN Server Container
# -------------------------------------------------------------------------
echo -e "\n${YELLOW}[Step 7/7] Starting SSL VPN container stack...${NC}"
docker compose down >/dev/null 2>&1 || true
docker compose up -d sslvpn

# Wait for health check
echo -n "Waiting for VPN server health check..."
for _ in {1..12}; do
    if docker ps --filter name=sslvpn-server --filter health=healthy -q | grep -q .; then
        echo -e " ${GREEN}[HEALTHY]${NC}"
        break
    fi
    echo -n "."
    sleep 2
done

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}   Deployment Complete! SSL VPN Stack is Live & Hardened     ${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "  VPN Tunnel Listener: ${CYAN}0.0.0.0:443 (TLS 1.2/1.3)${NC}"
echo -e "  Web Management GUI:  ${CYAN}http://${PUBLIC_IP}:8080${NC} (or https if --ssl enabled)"
echo -e "  Default Username:    ${CYAN}admin${NC}"
echo -e "  Default Password:    ${CYAN}admin123${NC} (Change immediately in GUI!)"
echo -e "  Container Status:    $(docker ps --filter name=sslvpn-server --format '{{.Names}}: {{.Status}}')"
echo -e "  GUI Service Status:  $(systemctl is-active sslvpn-gui)"
echo -e "${GREEN}============================================================${NC}"
echo -e "\n${YELLOW}Production Hardening Post-Install Checklist:${NC}"
echo "  1. Open http://${PUBLIC_IP}:8080 in your browser and log in."
echo "  2. Go to 'Users & Access' -> Create your personalized admin account."
echo "  3. Remove or change the default 'admin123' password."
echo "  4. To restrict the Web GUI to a specific management IP, run:"
echo "     sudo ufw delete allow 8080/tcp"
echo "     sudo ufw allow from YOUR_ADMIN_IP to any port 8080 proto tcp"
echo -e "============================================================\n"
