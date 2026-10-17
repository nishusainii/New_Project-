#!/usr/bin/env bash
# ==============================================================================
# Script: setup_remote_log_server.sh
# Purpose: Configure Remote Log Server to receive logs from KVM VMs and separate them by hostname
# Usage: sudo ./setup_remote_log_server.sh [PORT]
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (use sudo)."
  exit 1
fi

LISTEN_PORT="$1"

echo "=========================================================="
echo "   Remote Log Receiver Setup"
echo "=========================================================="

if [ -z "$LISTEN_PORT" ]; then
  read -rp "Enter the listening port for Rsyslog [default: 514]: " USER_PORT
  LISTEN_PORT="${USER_PORT:-514}"
fi

LOG_DIR="/var/log/remote-nodes"

echo ""
echo "Configuration Summary:"
echo "  Listening Port : $LISTEN_PORT (TCP)"
echo "  Log Directory  : $LOG_DIR/<HOSTNAME>/"
echo "=========================================================="

echo "--- 1. Ensuring Rsyslog is installed ---"
if ! command -v rsyslogd >/dev/null 2>&1; then
  apt-get update && apt-get install -y rsyslog || yum install -y rsyslog || dnf install -y rsyslog
fi

mkdir -p "$LOG_DIR"
chown -R syslog:adm "$LOG_DIR" 2>/dev/null || chown -R root:root "$LOG_DIR"
chmod 755 "$LOG_DIR"

echo "--- 2. Creating Rsyslog receiver configuration ---"
cat <<RSYSLOG_RECEIVER > /etc/rsyslog.d/10-remote-receiver.conf
# Enable TCP Syslog Reception on port ${LISTEN_PORT}
module(load="imtcp")
input(type="imtcp" port="${LISTEN_PORT}")

# Separate incoming logs into folders by Hostname and program name
template(name="RemoteNodesByProgram" type="string" string="${LOG_DIR}/%HOSTNAME%/%PROGRAMNAME%.log")
template(name="RemoteNodesFullSyslog" type="string" string="${LOG_DIR}/%HOSTNAME%/syslog.log")

# Route remote logs (skip localhost)
if (\$fromhost-ip != "127.0.0.1") then {
    action(type="omfile" dynaFile="RemoteNodesFullSyslog")
    action(type="omfile" dynaFile="RemoteNodesByProgram")
    stop
}
RSYSLOG_RECEIVER

echo "--- 3. Opening firewall for port ${LISTEN_PORT}/tcp ---"
if command -v ufw >/dev/null 2>&1; then
  ufw allow "${LISTEN_PORT}/tcp" || true
fi
if command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --add-port="${LISTEN_PORT}/tcp" --permanent || true
  firewall-cmd --reload || true
fi

echo "--- 4. Restarting Rsyslog ---"
systemctl restart rsyslog
systemctl enable rsyslog

echo "--- 5. Verifying listening port ---"
if ss -tulpn | grep -q ":${LISTEN_PORT} "; then
  echo "Verified: Rsyslog is actively listening on TCP port ${LISTEN_PORT}."
else
  echo "Notice: Checking status..."
fi

echo "=========================================================="
echo "SUCCESS: Remote Log Server is ready."
echo "Incoming VM logs will be stored in: ${LOG_DIR}/<HOSTNAME>/"
echo "=========================================================="
