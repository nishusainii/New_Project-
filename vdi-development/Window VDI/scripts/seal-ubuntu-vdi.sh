#!/usr/bin/env bash
# ==============================================================================
# Script: seal-ubuntu-vdi.sh
# Purpose: Clean, generalize, and seal an Ubuntu 24.04 LTS VDI golden image
#          prior to Proxmox VE template conversion.
# Target OS: Ubuntu Server 24.04 LTS with XFCE & xrdp
# Execution: Run inside the build VM as root.
# Safety: set -euo pipefail, confirmation prompt, non-destructive to system binaries.
# ==============================================================================

set -euo pipefail

# --- Preflight Checks ---
if [[ "${EUID}" -ne 0 ]]; then
    echo "[-] ERROR: This script must be run as root (use sudo -i)." >&2
    exit 1
fi

echo "======================================================================"
echo "          UBUNTU 24.04 LTS VDI GOLDEN IMAGE SEALING SCRIPT            "
echo "======================================================================"
echo "This script will perform the following operations on THIS virtual machine:"
echo " 1. Terminate active non-root user graphical and remote desktop sessions."
echo " 2. Stop desktop management and remote desktop services (xrdp, lightdm)."
echo " 3. Safely purge temporary build/test user accounts and home directories."
echo " 4. Purge APT package caches and residual deb packages."
echo " 5. Reset cloud-init artifacts, instance state, and seed data."
echo " 6. Truncate /etc/machine-id and remove D-Bus machine-id for auto-regeneration."
echo " 7. Remove SSH host keys so clones generate unique host key pairs."
echo " 8. Purge DHCP client leases and persistent network identifiers."
echo " 9. Clean desktop, thumbnail, and temporary session caches."
echo "10. Truncate systemd journal logs to minimize image storage size."
echo "11. Clear shell histories for root."
echo "12. Execute filesystem sync and issue system poweroff."
echo "======================================================================"
echo "WARNING: Once sealed, this VM must NOT be booted before being converted"
echo "         into a Proxmox template, or machine-id will regenerate early."
echo "======================================================================"

read -r -p "Are you sure you want to seal this VM for template conversion? [y/N]: " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
    echo "[*] Aborted by operator. No changes made."
    exit 0
fi

LOG_FILE="/var/log/vdi-seal-$(date +'%Y%m%d-%H%M%S').log"
echo "[*] Starting sealing process at $(date)... Logging to ${LOG_FILE}"
exec > >(tee -a "${LOG_FILE}") 2>&1

# 1. Stop Desktop & Remote Desktop Services
echo "[+] Step 1/11: Stopping desktop and remote desktop daemons..."
systemctl stop xrdp.service || true
systemctl stop xrdp-sesman.service || true
if systemctl is-active --quiet lightdm.service; then
    systemctl stop lightdm.service || true
fi

# 2. Terminate any stray non-root user processes
echo "[+] Step 2/11: Checking for active user sessions..."
for user_id in $(loginctl list-users --no-legend | awk '$1 >= 1000 {print $1}'); do
    echo "    Terminating user session ID: ${user_id}"
    loginctl terminate-user "${user_id}" || true
done
sleep 2

# 3. Clean Known Test User Accounts (if defined by build operator)
# NOTE: Set TEST_ACCOUNTS_TO_PURGE="vdi-test user1" if temporary test users were created.
TEST_ACCOUNTS_TO_PURGE=("vdi-test" "testuser")
echo "[+] Step 3/11: Purging build test accounts (if any exist)..."
for test_user in "${TEST_ACCOUNTS_TO_PURGE[@]}"; do
    if id "${test_user}" &>/dev/null; then
        echo "    Removing temporary test user: ${test_user}"
        userdel -r -f "${test_user}" 2>/dev/null || true
    fi
done

# 4. Clean APT Package Manager Caches
echo "[+] Step 4/11: Cleaning package manager caches and dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get autoremove -y --purge
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -rf /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/*

# 5. Reset cloud-init State
echo "[+] Step 5/11: Purging cloud-init instance cache and logs..."
if command -v cloud-init &>/dev/null; then
    cloud-init clean --logs --seed
    rm -rf /var/lib/cloud/instances/*
    rm -rf /var/lib/cloud/instance
    rm -rf /var/lib/cloud/data/*
fi

# 6. Reset System Machine Identity (machine-id)
echo "[+] Step 6/11: Resetting system machine-id..."
# In systemd, /etc/machine-id must exist as an empty file for systemd-machine-id-commit to re-init
truncate -s 0 /etc/machine-id
if [[ -f /var/lib/dbus/machine-id ]]; then
    rm -f /var/lib/dbus/machine-id
    # Link to /etc/machine-id for standard D-Bus integration
    ln -sf /etc/machine-id /var/lib/dbus/machine-id
fi

# 7. Remove SSH Host Keys
echo "[+] Step 7/11: Purging SSH host key pairs..."
# These will be re-generated on first clone boot via cloud-init or ssh-keygen
rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub

# 8. Reset Network Leases and Machine-Specific Network Identifiers
echo "[+] Step 8/11: Purging DHCP leases and dynamic network states..."
rm -f /var/lib/dhcp/* 2>/dev/null || true
rm -f /var/lib/NetworkManager/*.lease 2>/dev/null || true
rm -f /var/lib/systemd/netif/leases/* 2>/dev/null || true
# Reset persistent udev net rules if present
rm -f /etc/udev/rules.d/70-persistent-net.rules 2>/dev/null || true

# 9. Clean Temporary Files and Desktop Session Residue
echo "[+] Step 9/11: Removing session locks, sockets, and temporary files..."
find /tmp -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
find /var/tmp -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
rm -rf /tmp/.X* /tmp/.xrdp* /var/run/xrdp/* 2>/dev/null || true

# Clean thumbnail caches in /root and skel
rm -rf /root/.cache/thumbnails/* 2>/dev/null || true
rm -rf /etc/skel/.cache/thumbnails/* 2>/dev/null || true

# 10. Trim System Logs
echo "[+] Step 10/11: Truncating systemd journal and rotate logs..."
if command -v journalctl &>/dev/null; then
    journalctl --rotate
    journalctl --vacuum-time=1s
fi
find /var/log -type f -name "*.gz" -delete
find /var/log -type f -name "*.1" -delete
find /var/log -type f -name "*.old" -delete
truncate -s 0 /var/log/wtmp /var/log/btmp /var/log/lastlog 2>/dev/null || true

# 11. Clear Shell History and Power Off
echo "[+] Step 11/11: Clearing shell history and synchronizing disk..."
unset HISTFILE
rm -f /root/.bash_history
history -c 2>/dev/null || true

echo "[+] Sealing completed successfully at $(date)."
echo "[*] Synchronizing filesystems..."
sync
sync

echo "[*] Initiating VM shutdown. Do not power this VM back on before converting to template!"
shutdown -h now
