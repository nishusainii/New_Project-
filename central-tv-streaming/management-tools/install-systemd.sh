#!/usr/bin/env bash
# ==============================================================================
# Bare-Metal Native Systemd Installer for Central TV Streaming Platform
# Supports: Ubuntu, Debian, Raspberry Pi OS (x86_64, ARM64, ARMv7)
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./install-systemd.sh)"
  exit 1
fi

INSTALL_DIR="/opt/central-tv-streaming"
APP_USER="${SUDO_USER:-$USER}"

echo "========================================================"
echo "Installing Central TV Streaming on Native System (Bare-Metal)"
echo "Installation Directory: ${INSTALL_DIR}"
echo "Running as User: ${APP_USER}"
echo "========================================================"

# 1. Install System Dependencies
apt-get update
apt-get install -y curl tar wget

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "Installing Node.js 20.x..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

# 2. Detect System Architecture for MediaMTX binary
ARCH=$(uname -m)
case "$ARCH" in
    x86_64)  MTX_ARCH="linux_amd64" ;;
    aarch64) MTX_ARCH="linux_arm64v8" ;;
    armv7l)  MTX_ARCH="linux_armv7" ;;
    *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

echo "Detected architecture: $ARCH (MediaMTX target: $MTX_ARCH)"

# 3. Create App Directory and Copy Files
mkdir -p "${INSTALL_DIR}"
cp -r ./* "${INSTALL_DIR}/" || true
chown -R "${APP_USER}:${APP_USER}" "${INSTALL_DIR}"

# 4. Download Precompiled MediaMTX Binary
MTX_VERSION="v1.9.3"
MTX_URL="https://github.com/bluenviron/mediamtx/releases/download/${MTX_VERSION}/mediamtx_${MTX_VERSION}_${MTX_ARCH}.tar.gz"

echo "Downloading MediaMTX ${MTX_VERSION} from ${MTX_URL}..."
wget -qO /tmp/mediamtx.tar.gz "${MTX_URL}" || {
    echo "Failed to download MediaMTX. Continuing with local binaries if present..."
}
if [ -f /tmp/mediamtx.tar.gz ]; then
    tar -xzf /tmp/mediamtx.tar.gz -C /usr/local/bin/ mediamtx
    chmod +x /usr/local/bin/mediamtx
    rm /tmp/mediamtx.tar.gz
fi

# 5. Install Node.js Dependencies
cd "${INSTALL_DIR}"
sudo -u "${APP_USER}" npm install --omit=dev

# 6. Create Systemd Service for MediaMTX
cat <<EOF > /etc/systemd/system/tv-mediamtx.service
[Unit]
Description=Central TV MediaMTX Core Streaming Server
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/local/bin/mediamtx ${INSTALL_DIR}/mediamtx.yml
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 7. Create Systemd Service for TV Streaming Manager (Node.js)
cat <<EOF > /etc/systemd/system/tv-manager.service
[Unit]
Description=Central TV Streaming Manager & Controller
After=network.target tv-mediamtx.service

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${INSTALL_DIR}
Environment=HTTP_PORT=8080
Environment=HTTPS_PORT=8443
ExecStart=/usr/bin/node ${INSTALL_DIR}/server.js
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 8. Reload & Enable Services
systemctl daemon-reload
systemctl enable tv-mediamtx.service
systemctl enable tv-manager.service
systemctl restart tv-mediamtx.service
systemctl restart tv-manager.service

echo "========================================================"
echo "Central TV Streaming installed and running successfully!"
echo "System Services:"
echo "  • tv-mediamtx.service (Streaming engine on ports 8889, 8888, 8554)"
echo "  • tv-manager.service  (Web console & API on port 8080)"
echo ""
echo "Open in browser: http://$(hostname -I | awk '{print $1}'):8080"
echo "========================================================"
