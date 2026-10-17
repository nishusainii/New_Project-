#!/usr/bin/env bash
# ==============================================================================
# Script: test_log_connection.sh
# Purpose: Test reachability and send a test message from KVM VM to Remote Server
# Usage: ./test_log_connection.sh [REMOTE_SERVER_IP] [PORT]
# ==============================================================================

REMOTE_IP="$1"
REMOTE_PORT="$2"

if [ -z "$REMOTE_IP" ]; then
  read -rp "Enter the Remote Log Server IP: " REMOTE_IP
fi

if [ -z "$REMOTE_PORT" ]; then
  read -rp "Enter the Remote Port [default: 514]: " USER_PORT
  REMOTE_PORT="${USER_PORT:-514}"
fi

echo "=========================================================="
echo "1. Testing network ping to $REMOTE_IP..."
if ping -c 2 -W 2 "$REMOTE_IP" >/dev/null 2>&1; then
  echo "Ping to $REMOTE_IP: SUCCESS"
else
  echo "Ping to $REMOTE_IP: FAILED (ICMP may be blocked, testing TCP next)"
fi

echo "2. Testing TCP port $REMOTE_PORT reachability..."
if command -v nc >/dev/null 2>&1; then
  if nc -z -w 3 "$REMOTE_IP" "$REMOTE_PORT" 2>/dev/null; then
    echo "Port $REMOTE_PORT (TCP) is reachable: SUCCESS"
  else
    echo "Port $REMOTE_PORT (TCP) unreachable: FAILED"
  fi
fi

echo "3. Sending test syslog message..."
TEST_MSG="DIAGNOSTIC TEST: VM $(hostname) forwarding check at $(date)"
logger -p local0.info -t "kvm-diag" "$TEST_MSG"
echo "Sent: $TEST_MSG"
echo "=========================================================="
echo "To verify on the remote server, run:"
echo "  sudo tail -f /var/log/remote-nodes/$(hostname)/syslog.log"
echo "  OR: sudo tail -f /var/log/syslog | grep kvm-diag"
