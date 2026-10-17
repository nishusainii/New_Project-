#!/usr/bin/env bash
# ==============================================================================
# INNCCTV - Enterprise Surveillance Operations Center
# Universal Systemd Service Installer for ANY Linux Distribution
# Supports: Ubuntu, Debian, CentOS, RHEL, AlmaLinux, Rocky Linux, Fedora, Arch
# ==============================================================================
set -e

# Ensure running as root or with sudo
if [ "$EUID" -ne 0 ]; then
  echo "[-] ERROR: This script must be run as root or with sudo:"
  echo "    sudo ./install-systemd.sh"
  exit 1
fi

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
TARGET_DIR="${1:-$CURRENT_DIR}"

echo "=================================================================="
echo " INNCCTV Universal Systemd Service Installer"
echo "=================================================================="
echo "[+] Detected Installation Directory: $TARGET_DIR"

# 1. Detect Node.js Binary
NODE_BIN=$(command -v node || true)
if [ -z "$NODE_BIN" ]; then
  # Check common paths
  if [ -x "/usr/bin/node" ]; then
    NODE_BIN="/usr/bin/node"
  elif [ -x "/usr/local/bin/node" ]; then
    NODE_BIN="/usr/local/bin/node"
  else
    echo "[-] Node.js is not found in PATH."
    echo "    Please install Node.js v18+ or specify path."
    exit 1
  fi
fi
echo "[✔] Node.js binary found: $NODE_BIN ($($NODE_BIN -v))"

# 2. Ensure bin/mediamtx is executable
if [ -f "$TARGET_DIR/bin/mediamtx" ]; then
  chmod +x "$TARGET_DIR/bin/mediamtx"
  echo "[✔] MediaMTX gateway marked executable."
fi

# 3. Create dedicated system user if it doesn't exist
APP_USER="inncctv"
if ! id "$APP_USER" >/dev/null 2>&1; then
  echo "[+] Creating dedicated system user '$APP_USER'..."
  useradd -r -s /bin/false -d "$TARGET_DIR" "$APP_USER" 2>/dev/null || useradd -r -s /bin/false "$APP_USER" 2>/dev/null || true
  echo "[✔] System user created."
else
  echo "[✔] System user '$APP_USER' already exists."
fi

# Ensure correct file permissions
chown -R "$APP_USER:$APP_USER" "$TARGET_DIR" 2>/dev/null || true

# 4. Generate custom systemd service unit
SERVICE_FILE="/etc/systemd/system/inncctv.service"
echo "[+] Writing service unit to $SERVICE_FILE..."

cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Innspark Enterprise 24-Camera Surveillance Operations Center
Documentation=https://github.com/innspark
After=network.target remote-fs.target nss-lookup.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$TARGET_DIR
ExecStart=$NODE_BIN $TARGET_DIR/server/index.js
Restart=always
RestartSec=5s

# Production Environment
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=ADMIN_PASSWORD=innspark@2026
Environment=INNCCTV_SECRET=innspark_secure_production_token_secret_key_2026

# CIS Linux Benchmark Hardening & Sandboxing
ProtectSystem=full
ProtectHome=false
NoNewPrivileges=true
PrivateTmp=true
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

chmod 644 "$SERVICE_FILE"
echo "[✔] Service unit file created successfully."

# 5. Reload systemd and enable service
echo "[+] Reloading systemd daemon (systemctl daemon-reload)..."
systemctl daemon-reload

echo "[+] Enabling inncctv service on system boot (systemctl enable inncctv)..."
systemctl enable inncctv.service

echo "[+] Starting inncctv service (systemctl start inncctv)..."
systemctl restart inncctv.service

sleep 2

# 6. Verify service status
if systemctl is-active --quiet inncctv.service; then
  echo "=================================================================="
  echo " [✔] SUCCESS: INNCCTV is now running as a Systemd Background Service!"
  echo "=================================================================="
  echo " - Status:        ACTIVE (running)"
  echo " - Auto-start:    ENABLED on boot"
  echo " - Web Console:   http://localhost:3000 (or http://SERVER_IP:3000)"
  echo ""
  echo " Management Commands:"
  echo "   View Status:   sudo systemctl status inncctv"
  echo "   Restart:       sudo systemctl restart inncctv"
  echo "   Stop:          sudo systemctl stop inncctv"
  echo "   Live Logs:     sudo journalctl -u inncctv -f"
  echo "=================================================================="
else
  echo "[-] Warning: Service started but may have encountered an issue."
  echo "    Check logs: sudo journalctl -u inncctv -n 30 --no-pager"
fi
