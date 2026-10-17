#!/usr/bin/env bash
# ==============================================================================
# Script: create-ubuntu-vdi-build-vm.sh
# Purpose: Idempotent, non-destructive deployment of Ubuntu 24.04 LTS VDI Build VM
#          on Proxmox VE from the official Cloud Image.
# Target: Proxmox VE Host Shell (as root)
# Safety: Strict pre-flight checks, explicit prompt, stops before template conversion.
# ==============================================================================

set -euo pipefail

# --- Configuration Variables (Adjust according to your environment) ---
VM_ID="${VM_ID:-9000}"
VM_NAME="${VM_NAME:-ubuntu-2404-vdi-gold-build}"
STORAGE="${STORAGE:-local-lvm}"
SNIPPET_STORAGE="${SNIPPET_STORAGE:-local}"
BRIDGE="${BRIDGE:-vmbr0}"
VLAN_ID="${VLAN_ID:-}"                        # Leave empty for untagged, or specify e.g. 20
CORES="${CORES:-4}"
MEMORY="${MEMORY:-4096}"                      # In MB
BALLOON="${BALLOON:-0}"                       # 0 disables ballooning for consistent VDI latency
DISK_SIZE="${DISK_SIZE:-32G}"
IMAGE_DIR="${IMAGE_DIR:-/var/lib/vz/template/iso}"
UBUNTU_RELEASE="${UBUNTU_RELEASE:-noble}"
UBUNTU_IMAGE_NAME="${UBUNTU_IMAGE_NAME:-noble-server-cloudimg-amd64.img}"
IMAGE_PATH="${IMAGE_DIR}/${UBUNTU_IMAGE_NAME}"
IMAGE_URL="${IMAGE_URL:-https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img}"
IMAGE_SHA256_URL="${IMAGE_SHA256_URL:-https://cloud-images.ubuntu.com/noble/current/SHA256SUMS}"

CI_USER="${CI_USER:-vdiadmin}"
SSH_KEY_FILE="${SSH_KEY_FILE:-/root/.ssh/id_ed25519.pub}"
DNS_SERVER="${DNS_SERVER:-10.31.0.1}"
DNS_DOMAIN="${DNS_DOMAIN:-internal.vdi}"
IP_CONFIG="${IP_CONFIG:-ip=dhcp}"             # Or e.g., 'ip=10.31.1.200/23,gw=10.31.0.1'

LOG_FILE="/var/log/pve-vdi-builder-$(date +'%Y%m%d-%H%M%S').log"

# --- Guardrail Functions ---
log() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "${LOG_FILE}"
}

fail() {
    echo -e "\n[-] ERROR: $*" | tee -a "${LOG_FILE}" >&2
    exit 1
}

# --- Step 0: Pre-flight Validations ---
log "[*] Executing Pre-flight Safety Validations..."

# Verify root
if [[ "${EUID}" -ne 0 ]]; then
    fail "This script must be run directly on the Proxmox VE host as root."
fi

# Verify required Proxmox binaries
for cmd in qm pvesm sha256sum curl wget awk grep; do
    command -v "${cmd}" &>/dev/null || fail "Required command '${cmd}' is missing."
done

# Verify VM ID is unused
if qm status "${VM_ID}" &>/dev/null; then
    fail "VM ID ${VM_ID} already exists! Please select an unused VM ID."
fi

# Verify storage pools exist and are active
if ! pvesm status -storage "${STORAGE}" &>/dev/null; then
    fail "Target disk storage pool '${STORAGE}' does not exist or is inactive."
fi

# Check storage content capability for images
STORAGE_CONTENT=$(pvesm status -storage "${STORAGE}" | awk 'NR>1 {print $3}')
if [[ "${STORAGE_CONTENT}" != *"images"* ]]; then
    fail "Storage '${STORAGE}' does not support disk images (content: ${STORAGE_CONTENT})."
fi

# Verify bridge interface exists
if ! ip link show dev "${BRIDGE}" &>/dev/null; then
    fail "Network bridge interface '${BRIDGE}' does not exist on this host."
fi

# Verify SSH Public Key
if [[ ! -f "${SSH_KEY_FILE}" ]]; then
    fail "SSH public key file '${SSH_KEY_FILE}' not found. Generate one with 'ssh-keygen -t ed25519' first."
fi

# --- Step 1: Download & Verify Ubuntu Cloud Image ---
mkdir -p "${IMAGE_DIR}"

if [[ ! -f "${IMAGE_PATH}" ]]; then
    log "[*] Downloading Ubuntu 24.04 Cloud Image from: ${IMAGE_URL}"
    wget -O "${IMAGE_PATH}" "${IMAGE_URL}"
    wget -O "${IMAGE_DIR}/SHA256SUMS" "${IMAGE_SHA256_URL}"
fi

log "[*] Verifying SHA256 checksum of cloud image..."
EXPECTED_HASH=$(grep "${UBUNTU_IMAGE_NAME}" "${IMAGE_DIR}/SHA256SUMS" | awk '{print $1}')
ACTUAL_HASH=$(sha256sum "${IMAGE_PATH}" | awk '{print $1}')

if [[ -z "${EXPECTED_HASH}" ]]; then
    fail "Could not determine expected SHA256 checksum from SHA256SUMS file."
fi

if [[ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]]; then
    fail "Checksum mismatch for ${IMAGE_PATH}!\nExpected: ${EXPECTED_HASH}\nActual:   ${ACTUAL_HASH}"
fi
log "[+] Checksum successfully verified: ${ACTUAL_HASH}"

# --- Display Proposed Plan & Seek Operator Confirmation ---
echo "======================================================================"
echo "               PROXMOX VE VDI BUILD VM SPECIFICATION                 "
echo "======================================================================"
echo " VM ID:              ${VM_ID}"
echo " VM Name:            ${VM_NAME}"
echo " Architecture:       q35 / OVMF (UEFI)"
echo " CPU:                ${CORES} cores (type=host)"
echo " Memory:             ${MEMORY} MB (balloon=${BALLOON})"
echo " Storage Pool:       ${STORAGE}"
echo " Disk Size:          ${DISK_SIZE}"
echo " Network:            VirtIO on ${BRIDGE} (VLAN: ${VLAN_ID:-untagged})"
echo " Cloud-init User:    ${CI_USER}"
echo " SSH Key:            ${SSH_KEY_FILE}"
echo " Network Config:     ${IP_CONFIG}"
echo " DNS:                ${DNS_SERVER} (${DNS_DOMAIN})"
echo "======================================================================"
read -r -p "Proceed with creating this build VM on Proxmox VE? [y/N]: " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
    log "[-] Aborted by operator. No VM created."
    exit 0
fi

# --- Step 2: Create Base VM ---
log "[+] Creating base VM ${VM_ID} (${VM_NAME})..."
NET_PARAMS="virtio,bridge=${BRIDGE}"
if [[ -n "${VLAN_ID}" ]]; then
    NET_PARAMS="${NET_PARAMS},tag=${VLAN_ID}"
fi

qm create "${VM_ID}" \
    --name "${VM_NAME}" \
    --machine q35 \
    --bios ovmf \
    --cpu host \
    --cores "${CORES}" \
    --sockets 1 \
    --memory "${MEMORY}" \
    --balloon "${BALLOON}" \
    --scsihw virtio-scsi-single \
    --net0 "${NET_PARAMS}" \
    --agent enabled=1,fstrim_cloned_disks=1 \
    --vga serial0 \
    --serial0 socket \
    --ostype l26

# --- Step 3: Configure EFI Disk ---
log "[+] Adding OVMF EFI disk..."
qm set "${VM_ID}" --efidisk0 "${STORAGE}:0,pre-enrolled-keys=1,efitype=4m"

# --- Step 4: Import Cloud Image as SCSI System Disk ---
log "[+] Importing cloud image disk to storage '${STORAGE}'..."
IMPORTED_DISK=$(qm importdisk "${VM_ID}" "${IMAGE_PATH}" "${STORAGE}" | grep -o "unused[0-9]" | head -n1 || true)

if [[ -z "${IMPORTED_DISK}" ]]; then
    # Fallback search for unused disk
    IMPORTED_DISK=$(qm config "${VM_ID}" | grep -o "unused[0-9]" | head -n1)
fi

log "[+] Attaching imported disk as scsi0 with discard and SSD emulation..."
qm set "${VM_ID}" --scsi0 "${STORAGE}:${VM_ID}/vm-${VM_ID}-disk-1.raw,discard=on,ssd=1,iothread=1" 2>/dev/null || \
qm set "${VM_ID}" --scsi0 "${STORAGE}:${IMPORTED_DISK},discard=on,ssd=1,iothread=1"

# --- Step 5: Resize System Disk ---
log "[+] Resizing system disk to ${DISK_SIZE}..."
qm disk resize "${VM_ID}" scsi0 "${DISK_SIZE}"

# --- Step 6: Attach Cloud-Init Drive ---
log "[+] Configuring cloud-init drive..."
qm set "${VM_ID}" --ide2 "${STORAGE}:cloudinit"

# --- Step 7: Configure Boot Order & Cloud-Init Parameters ---
log "[+] Setting boot order and cloud-init metadata..."
qm set "${VM_ID}" --boot order=scsi0
qm set "${VM_ID}" --ciuser "${CI_USER}"
qm set "${VM_ID}" --sshkeys "${SSH_KEY_FILE}"
qm set "${VM_ID}" --nameserver "${DNS_SERVER}"
qm set "${VM_ID}" --searchdomain "${DNS_DOMAIN}"
qm set "${VM_ID}" --ipconfig0 "${IP_CONFIG}"

log "[+] Build VM ${VM_ID} configuration complete!"
echo "----------------------------------------------------------------------"
qm config "${VM_ID}"
echo "----------------------------------------------------------------------"
log "[*] Next steps for the operator:"
log " 1. Start the VM: qm start ${VM_ID}"
log " 2. Wait for cloud-init: qm guest exec ${VM_ID} -- cloud-init status --wait"
log " 3. SSH into the build VM: ssh ${CI_USER}@<ASSIGNED_IP>"
log " 4. Run Section 7, 8, 9 package installations (XFCE, LightDM, xrdp)."
log " 5. Perform application baseline, optimization, and security validation."
log " 6. Execute /root/seal-ubuntu-vdi.sh inside the guest."
log " 7. Convert to template via: qm template ${VM_ID}"
log "[*] Finished."
