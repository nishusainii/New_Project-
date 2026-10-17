#!/usr/bin/env bash
# ==============================================================================
# INNSPARK ENTERPRISE CCTV DASHBOARD - AUTOMATED LINUX PRODUCTION INSTALLER
# Tested on: Ubuntu 22.04 / 24.04 LTS, Debian 12, RHEL / Rocky Linux 9
# ==============================================================================

set -euo pipefail

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "[-] ERROR: Please run this installer as root (e.g. sudo bash deploy/setup-server.sh)"
  exit 1
fi

echo "======================================================================"
echo " Starting Innspark Enterprise CCTV Surveillance Dashboard Installation"
echo "======================================================================"

INSTALL_DIR="/opt/inncctv"
SERVICE_USER="inncctv"

# 1. Update package lists and install system prerequisites
echo "[+] Step 1: Installing system prerequisites (curl, ffmpeg, ufw, tar)..."
if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y curl ffmpeg ufw tar nginx
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y curl ffmpeg ufw tar nginx
fi

# 2. Verify or Install Node.js LTS (v20+)
echo "[+] Step 2: Checking Node.js environment..."
if ! command -v node >/dev/null 2>&1; then
    echo "[+] Installing Node.js LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi
echo "[+] Node.js version: $(node -v)"
echo "[+] NPM version: $(npm -v)"

# 3. Create non-root dedicated system service user
echo "[+] Step 3: Configuring dedicated system user ($SERVICE_USER)..."
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
    useradd -r -s /usr/sbin/nologin -d "$INSTALL_DIR" "$SERVICE_USER"
    echo "[+] Created service user: $SERVICE_USER"
else
    echo "[+] Service user $SERVICE_USER already exists."
fi

# 4. Prepare /opt/inncctv directory
echo "[+] Step 4: Deploying application to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Copy files
cp -r "$SCRIPT_DIR/bin" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/config" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/server" "$INSTALL_DIR/"
cp -r "$SCRIPT_DIR/public" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/package.json" "$INSTALL_DIR/"
if [ -f "$SCRIPT_DIR/start.sh" ]; then
    cp "$SCRIPT_DIR/start.sh" "$INSTALL_DIR/"
fi

# 5. Install Node.js production dependencies
echo "[+] Step 5: Installing production Node.js dependencies..."
cd "$INSTALL_DIR"
npm install --omit=dev

# 6. Ensure binary permissions and folder ownership
echo "[+] Step 6: Setting file permissions and security boundaries..."
chmod +x "$INSTALL_DIR/bin/mediamtx"
if [ -f "$INSTALL_DIR/start.sh" ]; then
    chmod +x "$INSTALL_DIR/start.sh"
fi
chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"

# 7. Configure Systemd Service
echo "[+] Step 7: Configuring Systemd service..."
cp "$SCRIPT_DIR/deploy/inncctv.service" /etc/systemd/system/inncctv.service
systemctl daemon-reload
systemctl enable inncctv.service
systemctl restart inncctv.service

# 8. Configure Linux UFW Firewall
echo "[+] Step 8: Configuring Linux Firewall (UFW)..."
if command -v ufw >/dev/null 2>&1; then
    ufw allow 3000/tcp comment "Innspark CCTV Web Dashboard" || true
    ufw allow 80/tcp comment "HTTP Web Proxy" || true
    ufw allow 443/tcp comment "HTTPS Web Proxy" || true
    ufw allow 8554/tcp comment "MediaMTX RTSP Gateway" || true
    ufw allow 8889/tcp comment "MediaMTX WebRTC TCP" || true
    ufw allow 8189/udp comment "MediaMTX WebRTC UDP ICE" || true
    ufw allow 8888/tcp comment "MediaMTX HLS Gateway" || true
fi

# 9. Health Check
echo "[+] Step 9: Verifying service health..."
sleep 3
if systemctl is-active --quiet inncctv.service; then
    echo "======================================================================"
    echo " [✔] INSTALLATION SUCCESSFUL! INNSPARK CCTV IS RUNNING 24/7"
    echo "======================================================================"
    echo " Dashboard URL:    http://$(hostname -I | awk '{print $1}'):3000"
    echo " Service Status:   systemctl status inncctv.service"
    echo " View Live Logs:   journalctl -u inncctv.service -f"
    echo " Default Admin:    admin / innspark@2026"
    echo "======================================================================"
else
    echo "[-] Warning: Service started but check status with: systemctl status inncctv.service"
fi
