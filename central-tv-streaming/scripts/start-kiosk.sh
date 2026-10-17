#!/usr/bin/env bash
# ==============================================================================
# TV Receiver Kiosk Launcher
# For Raspberry Pi OS or Ubuntu Desktop connected to TV via HDMI
# ==============================================================================

# Replace with your Central Server LAN or VPN IP address
SERVER_HOST="${1:-10.10.1.10:8080}"
SITE_NAME="${2:-Headquarters}"
DEVICE_NAME="${3:-TV-Display}"

echo "Starting TV Kiosk Player..."
echo "Connecting to Server: http://${SERVER_HOST}"
echo "Site Location: ${SITE_NAME}"

# Disable screen blanking & sleep
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor when inactive (optional, requires unclutter)
if command -v unclutter &> /dev/null; then
    unclutter -idle 0.5 -root &
fi

# Detect available Chromium browser binary
if command -v chromium-browser &> /dev/null; then
    CHROME_BIN="chromium-browser"
elif command -v google-chrome &> /dev/null; then
    CHROME_BIN="google-chrome"
elif command -v chromium &> /dev/null; then
    CHROME_BIN="chromium"
else
    echo "Error: Chromium or Google Chrome is not installed."
    exit 1
fi

TARGET_URL="http://${SERVER_HOST}/player.html?site=${SITE_NAME}&name=${DEVICE_NAME}"

# Launch Chromium in dedicated full-screen kiosk mode
exec $CHROME_BIN \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --check-for-update-interval=31536000 \
    --autoplay-policy=no-user-gesture-required \
    --enable-features=OverlayScrollbar \
    --hide-scrollbars \
    --app="${TARGET_URL}"
