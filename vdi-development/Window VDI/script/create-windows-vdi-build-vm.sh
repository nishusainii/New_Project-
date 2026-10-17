#!/usr/bin/env bash
# ==============================================================================
# Script: create-windows-vdi-build-vm.sh
# Purpose: Idempotent, non-destructive deployment of Windows 10/11 VDI Build VM
#          on Proxmox VE with VirtIO drivers, vTPM 2.0, UEFI OVMF, and QEMU Agent.
# Target: Proxmox VE Host Shell (as root)
# Safety: Strict pre-flight checks, explicit prompt, stops before template conversion.
# ==============================================================================

set -euo pipefail

# --- Configuration Variables (Adjust according to your environment) ---
VM_ID="${VM_ID:-9100}"
WINDOWS_VERSION="${WINDOWS_VERSION:-win11}"     # win11 or win10
VM_NAME="${VM_NAME:-windows-${WINDOWS_VERSION}-vdi-gold-build}"
STORAGE="${STORAGE:-local-lvm}"                 # VM disk storage pool (supports 'images')
ISO_STORAGE="${ISO_STORAGE:-local}"             # ISO storage pool (supports 'iso')
BRIDGE="${BRIDGE:-vmbr0}"                       # Network bridge
VLAN_ID="${VLAN_ID:-}"                          # Optional 802.1Q VLAN tag (e.g. 20 or empty)
CORES="${CORES:-4}"                             # CPU Cores (minimum 4 recommended for Windows VDI)
MEMORY="${MEMORY:-8192}"                        # RAM in MB (8GB recommended for Win10/11)
BALLOON="${BALLOON:-0}"                         # 0 disables ballooning for consistent VDI latency
DISK_SIZE="${DISK_SIZE:-64G}"                   # 64GB - 80GB recommended for Windows Gold Image
ISO_DIR="${ISO_DIR:-/var/lib/vz/template/iso}"  # Local directory for ISOs under ISO_STORAGE

# Windows Installation ISO details
WIN_ISO_NAME="${WIN_ISO_NAME:-Win11_23H2_English_x64.iso}"
WIN_ISO_PATH="${ISO_DIR}/${WIN_ISO_NAME}"
WIN_ISO_VOLID="${ISO_STORAGE}:iso/${WIN_ISO_NAME}"

# Fedora VirtIO Driver ISO details (Official Red Hat / Fedora stable build)
VIRTIO_ISO_NAME="${VIRTIO_ISO_NAME:-virtio-win.iso}"
VIRTIO_ISO_PATH="${ISO_DIR}/${VIRTIO_ISO_NAME}"
VIRTIO_ISO_VOLID="${ISO_STORAGE}:iso/${VIRTIO_ISO_NAME}"
VIRTIO_ISO_URL="${VIRTIO_ISO_URL:-https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso}"

LOG_FILE="/var/log/pve-windows-vdi-builder-$(date +'%Y%m%d-%H%M%S').log"

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

# Verify root privileges
if [[ "${EUID}" -ne 0 ]]; then
    fail "This script must be run directly on the Proxmox VE host as root."
fi

# Verify required Proxmox & utility binaries
for cmd in qm pvesm curl wget awk grep sha256sum; do
    command -v "${cmd}" &>/dev/null || fail "Required command '${cmd}' is missing."
done

# Validate Windows Version selection
if [[ "${WINDOWS_VERSION}" != "win11" && "${WINDOWS_VERSION}" != "win10" ]]; then
    fail "Invalid WINDOWS_VERSION '${WINDOWS_VERSION}'. Supported options: 'win11' or 'win10'."
fi

# Verify VM ID is unused
if qm status "${VM_ID}" &>/dev/null; then
    fail "VM ID ${VM_ID} already exists! Please select an unused VM ID."
fi

# Verify VM disk storage pool exists and is active
if ! pvesm status -storage "${STORAGE}" &>/dev/null; then
    fail "Target disk storage pool '${STORAGE}' does not exist or is inactive."
fi

# Check VM storage content capability for images
STORAGE_CONTENT=$(pvesm status -storage "${STORAGE}" | awk 'NR>1 {print $3}')
if [[ "${STORAGE_CONTENT}" != *"images"* ]]; then
    fail "Storage '${STORAGE}' does not support VM disk images (content: ${STORAGE_CONTENT})."
fi

# Verify ISO storage pool exists and is active
if ! pvesm status -storage "${ISO_STORAGE}" &>/dev/null; then
    fail "ISO storage pool '${ISO_STORAGE}' does not exist or is inactive."
fi

# Verify bridge interface exists
if ! ip link show dev "${BRIDGE}" &>/dev/null; then
    fail "Network bridge interface '${BRIDGE}' does not exist on this host."
fi

# Ensure ISO directory exists
mkdir -p "${ISO_DIR}"

# Step 1: Check / Download VirtIO Driver ISO
if [[ ! -f "${VIRTIO_ISO_PATH}" ]]; then
    log "[*] VirtIO driver ISO not found at ${VIRTIO_ISO_PATH}."
    log "[*] Downloading official stable VirtIO driver ISO from: ${VIRTIO_ISO_URL} ..."
    wget -O "${VIRTIO_ISO_PATH}" "${VIRTIO_ISO_URL}" || fail "Failed to download VirtIO driver ISO."
    log "[+] VirtIO driver ISO successfully downloaded to ${VIRTIO_ISO_PATH}."
else
    log "[+] VirtIO driver ISO found at: ${VIRTIO_ISO_PATH}"
fi

# Step 2: Check Windows ISO existence
if [[ ! -f "${WIN_ISO_PATH}" ]]; then
    echo "----------------------------------------------------------------------"
    echo "[!] WARNING: Windows ISO not found at: ${WIN_ISO_PATH}"
    echo "    Please copy your Windows 10 or 11 Enterprise/Pro ISO to:"
    echo "    ${WIN_ISO_PATH}"
    echo "    Alternatively, set WIN_ISO_NAME or WIN_ISO_PATH before running."
    echo "----------------------------------------------------------------------"
    fail "Windows ISO image is required to build the golden image."
else
    log "[+] Windows ISO verified at: ${WIN_ISO_PATH}"
fi

# --- Display Proposed Plan & Seek Operator Confirmation ---
echo "======================================================================"
echo "          PROXMOX VE WINDOWS VDI BUILD VM SPECIFICATION               "
echo "======================================================================"
echo " VM ID:              ${VM_ID}"
echo " VM Name:            ${VM_NAME}"
echo " Target OS:          Windows ${WINDOWS_VERSION^^} (ostype=${WINDOWS_VERSION})"
echo " Architecture:       q35 / OVMF (UEFI) + 4MB EFI Disk"
echo " vTPM:               v2.0 (Dedicated virtual TPM state)"
echo " CPU:                ${CORES} cores (type=host for native AVX2/SSE4.2)"
echo " Memory:             ${MEMORY} MB (Fixed RAM, balloon=${BALLOON})"
echo " Storage Pool:       ${STORAGE}"
echo " Disk Size:          ${DISK_SIZE} (VirtIO SCSI Single, Discard/TRIM=on, SSD=1, IOThread=1)"
echo " Network:            VirtIO on ${BRIDGE} (VLAN: ${VLAN_ID:-untagged})"
echo " Display / GPU:      SPICE QXL (64MB) + ich9-intel-hda Audio"
echo " Guest Agent:        QEMU Guest Agent enabled"
echo " Windows ISO:        ${WIN_ISO_VOLID}"
echo " VirtIO ISO:         ${VIRTIO_ISO_VOLID}"
echo "======================================================================"
read -r -p "Proceed with creating this Windows VDI build VM on Proxmox VE? [y/N]: " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
    log "[-] Aborted by operator. No VM created."
    exit 0
fi

# --- Step 3: Create Base VM ---
log "[+] Creating base Windows VM ${VM_ID} (${VM_NAME})..."
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
    --vga qxl,memory=64 \
    --audio0 device=ich9-intel-hda,driver=spice \
    --ostype "${WINDOWS_VERSION}"

# --- Step 4: Configure OVMF EFI Disk ---
log "[+] Adding OVMF EFI disk with pre-enrolled SecureBoot keys..."
qm set "${VM_ID}" --efidisk0 "${STORAGE}:0,pre-enrolled-keys=1,efitype=4m"

# --- Step 5: Add Virtual TPM 2.0 ---
log "[+] Configuring virtual TPM 2.0 (swtpm) for Windows security / BitLocker..."
qm set "${VM_ID}" --tpmstate0 "${STORAGE}:0,version=v2.0"

# --- Step 6: Create Primary VirtIO SCSI System Disk ---
log "[+] Provisioning primary system disk (${DISK_SIZE}) with discard/TRIM and SSD emulation..."
qm set "${VM_ID}" --scsi0 "${STORAGE}:${DISK_SIZE},discard=on,ssd=1,iothread=1"

# --- Step 7: Attach Windows Install ISO and VirtIO Drivers ISO ---
log "[+] Attaching Windows ISO (IDE 0) and VirtIO Drivers ISO (IDE 2)..."
qm set "${VM_ID}" --ide0 "${WIN_ISO_VOLID},media=cdrom"
qm set "${VM_ID}" --ide2 "${VIRTIO_ISO_VOLID},media=cdrom"

# --- Step 8: Set Boot Order ---
log "[+] Setting boot order: Windows ISO (ide0) first, then SCSI Disk (scsi0)..."
qm set "${VM_ID}" --boot "order=ide0;scsi0"

log "[+] Windows VDI Build VM ${VM_ID} configuration complete!"
echo "----------------------------------------------------------------------"
qm config "${VM_ID}"
echo "----------------------------------------------------------------------"
log "[*] Next steps for the operator:"
log " 1. Start the VM: qm start ${VM_ID}"
log " 2. Open Proxmox Console (SPICE or noVNC)."
log " 3. When Windows Setup prompts 'Where do you want to install Windows?':"
log "    a. Click 'Load driver' -> Browse -> CD Drive (virtio-win) -> vioscsi -> ${WINDOWS_VERSION^^} -> amd64"
log "    b. Select 'Red Hat VirtIO SCSI controller' -> Click Next -> The 64GB drive appears!"
log "    c. Select Drive 0 Unallocated Space and click Next to begin installation."
log " 4. Complete Windows Setup into desktop."
log " 5. Open CD Drive (virtio-win) inside Windows and run 'virtio-win-guest-tools.exe'."
log "    This installs NetKVM (Ethernet), Balloon Service, and QEMU Guest Agent."
log " 6. Run the PowerShell script 'optimize-and-seal-windows-vdi.ps1' as Administrator."
log " 7. Sysprep will automatically seal and shut down the machine."
log " 8. Convert to template via: qm template ${VM_ID}"
log "[*] Finished."
