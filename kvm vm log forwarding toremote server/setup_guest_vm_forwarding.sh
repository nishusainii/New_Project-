#!/usr/bin/env bash
# ==============================================================================
# Script: setup_guest_vm_forwarding.sh
# Purpose: Configure KVM Guest VM (behind NAT) to forward all logs to remote server
# Usage: sudo ./setup_guest_vm_forwarding.sh [REMOTE_SERVER_IP] [PORT]
# ==============================================================================

set -e

if [ "$EUID" -ne 0 ]; then
  echo "Error: This script must be run as root (use sudo)."
  exit 1
fi

REMOTE_IP="$1"
REMOTE_PORT="$2"

echo "=========================================================="
echo "   KVM Guest VM Log Forwarding Setup"
echo "=========================================================="

# Prompt for Remote IP if not provided
if [ -z "$REMOTE_IP" ]; then
  while [ -z "$REMOTE_IP" ]; do
    read -rp "Enter the Remote Log Server IP: " REMOTE_IP
  done
fi

# Prompt for Port if not provided
if [ -z "$REMOTE_PORT" ]; then
  read -rp "Enter the Remote Port [default: 514]: " USER_PORT
  REMOTE_PORT="${USER_PORT:-514}"
fi

CURRENT_HOST=$(hostname)
echo ""
echo "Configuration Summary:"
echo "  Target Server IP : $REMOTE_IP"
echo "  Target Port      : $REMOTE_PORT (TCP)"
echo "  VM Hostname      : $CURRENT_HOST"
echo "=========================================================="

echo "--- 1. Testing network reachability to $REMOTE_IP:$REMOTE_PORT ---"
if command -v nc >/dev/null 2>&1; then
  if nc -z -w 3 "$REMOTE_IP" "$REMOTE_PORT" 2>/dev/null; then
    echo "Connection test: SUCCESS (Port $REMOTE_PORT is reachable)."
  else
    echo "Notice: Port $REMOTE_PORT could not be reached right now. Forwarding will still be configured and queued until the server is reachable."
  fi
else
  echo "Netcat (nc) not installed, proceeding with setup."
fi

echo "--- 2. Ensuring Rsyslog is installed ---"
if ! command -v rsyslogd >/dev/null 2>&1; then
  echo "Installing rsyslog package..."
  apt-get update && apt-get install -y rsyslog || yum install -y rsyslog || dnf install -y rsyslog
fi

echo "--- 3. Configuring Rsyslog Disk-Assisted Spool Queue and Forwarding ---"
cat <<RSYSLOG_CONF > /etc/rsyslog.d/60-remote-forward.conf
# Disk-assisted spool queue in case remote server is temporarily unreachable
\$ActionQueueFileName fwdRule1
\$ActionQueueMaxDiskSpace 1g
\$ActionQueueSaveOnShutdown on
\$ActionQueueType LinkedList
\$ActionResumeRetryCount -1

# Forward all system logs to remote server over TCP
*.* @@${REMOTE_IP}:${REMOTE_PORT}
RSYSLOG_CONF

echo "--- 4. Ensuring systemd-journald forwards to syslog ---"
if [ -f /etc/systemd/journald.conf ]; then
  if grep -q "^#*ForwardToSyslog=" /etc/systemd/journald.conf; then
    sed -i 's/^#*ForwardToSyslog=.*/ForwardToSyslog=yes/' /etc/systemd/journald.conf
  else
    echo "ForwardToSyslog=yes" >> /etc/systemd/journald.conf
  fi
  systemctl restart systemd-journald 2>/dev/null || true
fi

echo "--- 5. Restarting and Enabling Rsyslog ---"
systemctl restart rsyslog
systemctl enable rsyslog

echo "--- 6. Sending verification log entry ---"
logger -t "kvm-log-test" "Test log from KVM VM [$CURRENT_HOST] to remote server $REMOTE_IP:$REMOTE_PORT"

echo "=========================================================="
echo "SUCCESS: Log forwarding is active."
echo "All logs from [$CURRENT_HOST] are forwarded to $REMOTE_IP:$REMOTE_PORT via TCP."
echo "=========================================================="
