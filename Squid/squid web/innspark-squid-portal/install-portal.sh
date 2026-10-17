#!/usr/bin/env bash
# ==============================================================================
# Innspark Solutions - Automated Installer for Squid & LDAP Management Portal
# Target: Run on Server 2 (proxy.innspark.in)
# ==============================================================================

set -e

APP_DIR="/opt/innspark-squid-portal"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== Innspark Portal: Starting Installation on Server 2 ==="

# 1. Install prerequisites (Python 3, venv, pip)
echo "[1/6] Installing Python3 and development tools..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# 2. Deploy application files to /opt
echo "[2/6] Deploying application to $APP_DIR..."
sudo mkdir -p "$APP_DIR"
sudo cp -r "$SCRIPT_DIR/"* "$APP_DIR/"

# 3. Create Python virtual environment
echo "[3/6] Setting up virtual environment..."
cd "$APP_DIR"
sudo python3 -m venv venv
sudo "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# 4. Install systemd service
echo "[4/6] Configuring systemd service..."
sudo cp "$APP_DIR/innspark-portal.service" /etc/systemd/system/innspark-portal.service
sudo systemctl daemon-reload
sudo systemctl enable innspark-portal.service

# 5. Configure firewall for Portal port 5000
echo "[5/6] Updating firewall rules..."
sudo ufw allow from 10.31.0.0/16 to any port 5000 proto tcp comment "Innspark Web Portal" || true

# 6. Start the portal service
echo "[6/6] Starting Innspark Portal service..."
sudo systemctl restart innspark-portal.service

# Verify
sleep 2
if sudo systemctl is-active --quiet innspark-portal.service; then
    echo "======================================================================"
    echo " [SUCCESS] Innspark Squid & LDAP Portal is active and running!"
    echo " Access URL: http://$(hostname -I | awk '{print $1}'):5000"
    echo "======================================================================"
else
    echo "======================================================================"
    echo " [WARNING] Service failed to start. Checking journal logs:"
    sudo journalctl -u innspark-portal.service -n 20 --no-pager
    echo "======================================================================"
fi
