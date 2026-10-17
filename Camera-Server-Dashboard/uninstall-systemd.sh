#!/usr/bin/env bash
# ==============================================================================
# INNCCTV - Enterprise Surveillance Operations Center
# Universal Systemd Service Uninstaller
# ==============================================================================
set -e

if [ "$EUID" -ne 0 ]; then
  echo "[-] ERROR: This script must be run as root or with sudo:"
  echo "    sudo ./uninstall-systemd.sh"
  exit 1
fi

echo "=================================================================="
echo " Uninstalling INNCCTV Systemd Service"
echo "=================================================================="

if systemctl list-unit-files | grep -q inncctv.service; then
  echo "[+] Stopping inncctv service..."
  systemctl stop inncctv.service || true

  echo "[+] Disabling inncctv service from auto-boot..."
  systemctl disable inncctv.service || true

  echo "[+] Removing /etc/systemd/system/inncctv.service..."
  rm -f /etc/systemd/system/inncctv.service

  echo "[+] Reloading systemd daemon..."
  systemctl daemon-reload
  systemctl reset-failed || true

  echo "[✔] INNCCTV systemd service successfully uninstalled."
else
  echo "[-] Service inncctv.service is not installed."
fi
