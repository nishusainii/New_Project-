#!/usr/bin/env bash
# ==============================================================================
# Script: verify-clone-uniqueness.sh
# Purpose: Compare two deployed Ubuntu VDI clone VMs to verify that all
#          system, network, and security identities are strictly unique.
# Target: Run on Proxmox host or management workstation with SSH access to clones.
# ==============================================================================

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <CLONE1_IP_OR_VMID> <CLONE2_IP_OR_VMID> [SSH_USER]"
    echo "Example: $0 10.31.1.201 10.31.1.202 vdiadmin"
    exit 1
fi

TARGET1="$1"
TARGET2="$2"
SSH_USER="${3:-vdiadmin}"

echo "======================================================================"
echo "          UBUNTU VDI MULTI-CLONE UNIQUENESS VERIFICATION               "
echo "======================================================================"
echo " Clone 1: ${TARGET1}"
echo " Clone 2: ${TARGET2}"
echo " SSH User: ${SSH_USER}"
echo "======================================================================"

FAILURES=0

run_remote() {
    local target="$1"
    local cmd="$2"
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=5 "${SSH_USER}@${target}" "${cmd}" 2>/dev/null
}

compare_metric() {
    local label="$1"
    local val1="$2"
    local val2="$3"
    
    echo -n "[*] Checking ${label}... "
    if [[ -z "${val1}" || -z "${val2}" ]]; then
        echo "FAILED (Unable to retrieve value from one or both clones)"
        FAILURES=$((FAILURES + 1))
        return
    fi

    if [[ "${val1}" == "${val2}" ]]; then
        echo "COLLISION DETECTED!"
        echo "    Clone 1: ${val1}"
        echo "    Clone 2: ${val2}"
        echo "    [!] ERROR: ${label} must be unique across all VDI instances."
        FAILURES=$((FAILURES + 1))
    else
        echo "PASSED (Unique)"
        echo "    Clone 1: ${val1}"
        echo "    Clone 2: ${val2}"
    fi
}

echo -e "\n--- Phase 1: Operating System & Machine Identity ---"
HOSTNAME1=$(run_remote "${TARGET1}" "hostname")
HOSTNAME2=$(run_remote "${TARGET2}" "hostname")
compare_metric "Hostname" "${HOSTNAME1}" "${HOSTNAME2}"

MID1=$(run_remote "${TARGET1}" "cat /etc/machine-id")
MID2=$(run_remote "${TARGET2}" "cat /etc/machine-id")
compare_metric "/etc/machine-id" "${MID1}" "${MID2}"

echo -e "\n--- Phase 2: Network & Link Identity ---"
MAC1=$(run_remote "${TARGET1}" "ip link show \$(ip route show default | awk '{print \$5}') | awk '/ether/ {print \$2}'")
MAC2=$(run_remote "${TARGET2}" "ip link show \$(ip route show default | awk '{print \$5}') | awk '/ether/ {print \$2}'")
compare_metric "MAC Address" "${MAC1}" "${MAC2}"

IP1=$(run_remote "${TARGET1}" "hostname -I | awk '{print \$1}'")
IP2=$(run_remote "${TARGET2}" "hostname -I | awk '{print \$1}'")
compare_metric "IP Address" "${IP1}" "${IP2}"

echo -e "\n--- Phase 3: Cryptographic Identity (SSH Host Keys) ---"
SSH_ED1=$(run_remote "${TARGET1}" "ssh-keygen -l -f /etc/ssh/ssh_host_ed25519_key.pub 2>/dev/null | awk '{print \$2}'")
SSH_ED2=$(run_remote "${TARGET2}" "ssh-keygen -l -f /etc/ssh/ssh_host_ed25519_key.pub 2>/dev/null | awk '{print \$2}'")
compare_metric "SSH Host Key (ed25519)" "${SSH_ED1}" "${SSH_ED2}"

SSH_RSA1=$(run_remote "${TARGET1}" "ssh-keygen -l -f /etc/ssh/ssh_host_rsa_key.pub 2>/dev/null | awk '{print \$2}'")
SSH_RSA2=$(run_remote "${TARGET2}" "ssh-keygen -l -f /etc/ssh/ssh_host_rsa_key.pub 2>/dev/null | awk '{print \$2}'")
compare_metric "SSH Host Key (rsa)" "${SSH_RSA1}" "${SSH_RSA2}"

echo -e "\n--- Phase 4: Remote Desktop (xrdp) & Service Status ---"
XRDP1=$(run_remote "${TARGET1}" "systemctl is-active xrdp.service")
XRDP2=$(run_remote "${TARGET2}" "systemctl is-active xrdp.service")
echo "[*] Clone 1 xrdp service status: ${XRDP1}"
echo "[*] Clone 2 xrdp service status: ${XRDP2}"

echo -e "\n======================================================================"
if [[ "${FAILURES}" -eq 0 ]]; then
    echo " RESULT: ALL UNIQUENESS VERIFICATIONS PASSED."
    echo " The golden image correctly generates independent identities."
    exit 0
else
    echo " RESULT: ${FAILURES} VERIFICATION CHECK(S) FAILED OR DETECTED COLLISIONS."
    echo " REJECT THIS GOLDEN IMAGE TEMPLATE. DO NOT DEPLOY TO PRODUCTION."
    exit 1
fi
