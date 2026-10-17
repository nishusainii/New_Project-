#!/usr/bin/env bash
# ==============================================================================
# Script: verify-windows-clone-uniqueness.sh
# Purpose: Compare two deployed Windows VDI clone VMs on Proxmox VE to verify
#          that all machine, network, and security identities (especially SID)
#          are strictly unique and QEMU Guest Agent is functional.
# Target: Run on Proxmox VE host as root.
# Usage: ./verify-windows-clone-uniqueness.sh <VM_ID_1> <VM_ID_2>
# ==============================================================================

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <VM_ID_1> <VM_ID_2>"
    echo "Example: $0 9101 9102"
    exit 1
fi

VM1="$1"
VM2="$2"

echo "======================================================================"
echo "          WINDOWS VDI MULTI-CLONE UNIQUENESS VERIFICATION             "
echo "======================================================================"
echo " VM 1 ID: ${VM1}"
echo " VM 2 ID: ${VM2}"
echo "======================================================================"

FAILURES=0

# Ensure both VMs are running
for vmid in "${VM1}" "${VM2}"; do
    STATUS=$(qm status "${vmid}" 2>/dev/null | awk '{print $2}' || true)
    if [[ "${STATUS}" != "running" ]]; then
        echo "[-] ERROR: VM ${vmid} is not running (Current status: ${STATUS:-not found})."
        echo "    Both VMs must be powered on and booted into Windows."
        exit 1
    fi
done

# Helper function to execute PowerShell inside guest via QEMU Guest Agent
guest_exec_ps() {
    local vmid="$1"
    local script="$2"
    
    # Run guest-exec command
    local pid_json
    pid_json=$(qm guest exec "${vmid}" -- powershell.exe -NoProfile -NonInteractive -Command "${script}" 2>/dev/null || true)
    local pid
    pid=$(echo "${pid_json}" | grep -o '"pid":[0-9]*' | awk -F: '{print $2}' || true)
    
    if [[ -z "${pid}" ]]; then
        echo ""
        return
    fi

    # Poll for completion (up to 15 seconds)
    local count=0
    while [[ ${count} -lt 15 ]]; do
        local status_json
        status_json=$(qm guest exec-status "${vmid}" "${pid}" 2>/dev/null || true)
        if echo "${status_json}" | grep -q '"exited":1'; then
            local out_b64
            out_b64=$(echo "${status_json}" | grep -o '"out-data":"[^"]*"' | sed 's/"out-data":"//;s/"$//' || true)
            if [[ -n "${out_b64}" ]]; then
                echo "${out_b64}" | base64 -d 2>/dev/null | tr -d '\r\n'
            fi
            return
        fi
        sleep 1
        count=$((count + 1))
    done
    echo ""
}

compare_metric() {
    local label="$1"
    local val1="$2"
    local val2="$3"
    
    echo -n "[*] Checking ${label}... "
    if [[ -z "${val1}" || -z "${val2}" ]]; then
        echo "FAILED (Unable to retrieve value from one or both VMs. Is QEMU agent responding?)"
        FAILURES=$((FAILURES + 1))
        return
    fi

    if [[ "${val1}" == "${val2}" ]]; then
        echo "COLLISION DETECTED!"
        echo "    Clone ${VM1}: ${val1}"
        echo "    Clone ${VM2}: ${val2}"
        echo "    [!] CRITICAL ERROR: ${label} must be strictly unique across VDI instances."
        FAILURES=$((FAILURES + 1))
    else
        echo "PASSED (Unique)"
        echo "    Clone ${VM1}: ${val1}"
        echo "    Clone ${VM2}: ${val2}"
    fi
}

echo -e "\n--- Phase 1: Hypervisor & QEMU Guest Agent Connectivity ---"
for vmid in "${VM1}" "${VM2}"; do
    echo -n "[*] Pinging QEMU Guest Agent on VM ${vmid}... "
    if qm guest ping "${vmid}" 2>/dev/null; then
        echo "ONLINE"
    else
        echo "OFFLINE (Agent not running or driver missing)"
        FAILURES=$((FAILURES + 1))
    fi
done

echo -e "\n--- Phase 2: Windows Operating System & Machine Hostname ---"
HN1=$(guest_exec_ps "${VM1}" "\$env:COMPUTERNAME")
HN2=$(guest_exec_ps "${VM2}" "\$env:COMPUTERNAME")
compare_metric "Windows ComputerName" "${HN1}" "${HN2}"

echo -e "\n--- Phase 3: Windows Security Identifier (SID) ---"
# Check Machine / Domain Account SID
SID1=$(guest_exec_ps "${VM1}" "([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.AccountDomainSid.Value")
SID2=$(guest_exec_ps "${VM2}" "([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.AccountDomainSid.Value")

# Fallback to User SID if DomainSid is null (standalone workgroup)
if [[ -z "${SID1}" ]]; then
    SID1=$(guest_exec_ps "${VM1}" "([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value")
fi
if [[ -z "${SID2}" ]]; then
    SID2=$(guest_exec_ps "${VM2}" "([System.Security.Principal.WindowsIdentity]::GetCurrent()).User.Value")
fi
compare_metric "Machine Security Identifier (SID)" "${SID1}" "${SID2}"

echo -e "\n--- Phase 4: Network MAC & IP Address Assignments ---"
MAC1=$(qm config "${VM1}" | grep -E '^net[0-9]:' | grep -o 'virtio=[a-fA-F0-9:]*' | cut -d= -f2 || true)
MAC2=$(qm config "${VM2}" | grep -E '^net[0-9]:' | grep -o 'virtio=[a-fA-F0-9:]*' | cut -d= -f2 || true)
compare_metric "Hardware MAC Address" "${MAC1}" "${MAC2}"

IP1=$(guest_exec_ps "${VM1}" "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { \$_.InterfaceAlias -notlike '*Loopback*' }).IPAddress | Select-Object -First 1")
IP2=$(guest_exec_ps "${VM2}" "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { \$_.InterfaceAlias -notlike '*Loopback*' }).IPAddress | Select-Object -First 1")
compare_metric "IPv4 Network Address" "${IP1}" "${IP2}"

echo -e "\n--- Phase 5: Remote Desktop Protocol (RDP) Listener Status ---"
RDP1=$(guest_exec_ps "${VM1}" "(Get-NetTCPConnection -LocalPort 3389 -State Listen -ErrorAction SilentlyContinue).State")
RDP2=$(guest_exec_ps "${VM2}" "(Get-NetTCPConnection -LocalPort 3389 -State Listen -ErrorAction SilentlyContinue).State")
echo "[*] VM ${VM1} RDP Port 3389 Status: ${RDP1:-Not Listening}"
echo "[*] VM ${VM2} RDP Port 3389 Status: ${RDP2:-Not Listening}"

echo -e "\n======================================================================"
if [[ "${FAILURES}" -eq 0 ]]; then
    echo " RESULT: ALL WINDOWS VDI UNIQUENESS CHECKS PASSED."
    echo " Sysprep successfully generalized SIDs, Hostnames, and network identities."
    exit 0
else
    echo " RESULT: ${FAILURES} VERIFICATION CHECK(S) FAILED."
    echo " Please review the errors above before deploying to end users."
    exit 1
fi
