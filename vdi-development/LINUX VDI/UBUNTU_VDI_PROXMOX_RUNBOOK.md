# Production Runbook: Ubuntu 24.04 LTS VDI Golden Image on Proxmox VE

This document is an end-to-end, enterprise-grade engineering runbook for designing, building, hardening, validating, sealing, and lifecycle-managing an **Ubuntu Server 24.04 LTS Virtual Desktop Infrastructure (VDI) Golden Image** in **Proxmox Virtual Environment (PVE)**.

---

## 1. Intended Architecture

### 1.1 Architectural Rationale
Virtual Desktop Infrastructure (VDI) running on Linux provides lightweight, highly dense, cost-effective, and secure workstations. Rather than deploying a bloated desktop operating system directly, this architecture builds upon **Ubuntu Server 24.04 LTS (Noble Numbat)** as the minimal operating-system base. 

On top of this clean base:
- **XFCE Desktop Environment** is installed: XFCE delivers a modern, fully functional graphical user interface with an exceptionally low memory footprint (~350MB–500MB idle RAM vs. 1.8GB+ for GNOME), fast rendering over virtual display transports, and minimal CPU overhead.
- **xrdp with xorgxrdp** is deployed: xrdp enables industry-standard RDP (Remote Desktop Protocol) client connectivity from Windows, macOS, Linux, and thin clients.
- **Alternative transports**: SPICE (via Proxmox Web UI or native `remote-viewer`), NoMachine, or enterprise brokers (e.g., OpenUDS, Apache Guacamole, ThinLinc, Leostream) can be integrated seamlessly.

```
+-----------------------------------------------------------------------------------+
|                            Remote Clients (Thin / PC)                             |
|          [ Windows RDP Client / Remmina / Guacamole Web / SPICE Viewer ]          |
+-----------------------------------------------------------------------------------+
                                         │  (RDP Port 3389 / SPICE / TLS)
                                         ▼
+-----------------------------------------------------------------------------------+
|                         Proxmox VE Hypervisor Host                                |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                 Ubuntu 24.04 LTS VDI Guest Virtual Machine                  |  |
|  |                                                                             |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  XFCE Graphical Session (xfce4-session, thunar, xfce4-terminal)        |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  Display & Session Manager: xrdp / xorgxrdp (sesman) [Opt: LightDM]   |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  Core OS Services: systemd, Polkit, AppArmor, cloud-init, UFW         |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  QEMU Guest Agent (qemu-ga) & VirtIO Drivers (SCSI, Net, Balloon)     |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  Minimal Kernel: Ubuntu Server 24.04 LTS Kernel 6.8+                  |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  Hypervisor Layer: q35 Chipset | OVMF (UEFI) | VirtIO-SCSI-Single | Discard/TRIM  |
|  Storage Layer: ZFS / Ceph / LVM-Thin / NFS Datastore                             |
+-----------------------------------------------------------------------------------+
```

### 1.2 Specification Summary
- **Hypervisor**: Proxmox VE 8.x (Linux 6.8+ PVE kernel)
- **Base OS**: Ubuntu Server 24.04 LTS (`noble-server-cloudimg-amd64.img`)
- **VM Machine Type**: `q35` (PCIe modern bus architecture)
- **Firmware**: OVMF (UEFI) with dedicated 4MB EFI Disk and pre-enrolled SecureBoot keys
- **Storage Controller**: VirtIO SCSI Single (`virtio-scsi-single`) with `iothread=1`
- **System Disk**: SCSI disk with `discard=on` (TRIM support) and SSD emulation (`ssd=1`)
- **Network Interface**: VirtIO (`virtio`) with bridge binding and VLAN segmentation
- **Guest Agent**: QEMU Guest Agent (`qemu-guest-agent`) enabled for hypervisor sync, freeze/thaw, and IP reporting
- **Cloud Provisioning**: `cloud-init` via attached virtual NoCloud CD-ROM (`cloudinit`)
- **Remote Access Transport**: `xrdp` + `xorgxrdp` on TCP 3389; SPICE QXL display optional
- **Safety Policy**: Strictly non-destructive to existing hypervisor resources, VMs, and templates

---

## 2. Assumptions and Limitations

### 2.1 Environmental Assumptions
1. Proxmox VE is installed, reachable via network, and managed by an authorized administrator.
2. An active storage pool supporting VM disk images (`images`) exists (e.g., `local-lvm`, `ceph-pool`, `zfs-pool`, or `NFS-Storage`).
3. An active network bridge (e.g., `vmbr0`) exists on the host with connectivity to a provisioning DHCP service or routed subnet.
4. Target VM IDs and Template IDs are reserved and confirmed unused prior to execution.

### 2.2 Proxmox Template vs. Complete VDI Brokering Platform
A **Proxmox VM Template** is an immutable master disk image and virtual hardware definition. Proxmox natively provides:
- Fast clone provisioning (linked clones in seconds, full independent clones in minutes)
- Live execution, snapshots, backups, and hypervisor resource scheduling

**What Proxmox Does NOT Provide Out-of-the-Box:**
- User-to-desktop entitlement brokering (e.g., matching a logged-in directory user to an available desktop)
- Ephemeral pool lifecycle automation (powering on on-demand, destroying on logoff)
- Dynamic session reconnection across multiple physical hosts
- Centralized user profile virtualization (profile containers)

If multi-tenant desktop pooling, dynamic user assignment, and HTML5 browser gateways are required, Proxmox must be paired with an enterprise VDI connection broker:
- **OpenUDS**: Open-source, multi-platform VDI connection broker with native Proxmox VE connector
- **Apache Guacamole**: Clientless HTML5 remote desktop gateway supporting RDP and VNC
- **Leostream**: Enterprise connection broker supporting Proxmox clusters, active directory pools, and multi-factor authentication
- **ThinLinc**: High-performance Linux VDI server based on TigerVNC and SSH

### 2.3 Persistent vs. Non-Persistent VDI Models
| Dimension | Persistent VDI | Non-Persistent VDI |
| :--- | :--- | :--- |
| **Clone Type** | Full Clone (`--full 1`) | Linked Clone (`--full 0`) |
| **Storage Dependency**| Fully independent; can be moved to any storage | Hard dependency on parent template base disks |
| **State Retention** | Changes, packages, and files persist across reboots | Changes discarded on rebuild; VM reset to golden state |
| **User Data** | Stored locally in `/home/$USER` | Stored in network home directories (NFS/CIFS) or object storage |
| **Use Case** | Power users, developers, persistent custom tools | Task workers, call centers, kiosk workstations, lab training |

---

## 3. Read-Only Environment Discovery

All commands in this section are strictly **READ-ONLY**. They execute non-intrusive queries against the Proxmox host to determine available resources and identify existing configurations without altering any state.

```bash
# ==============================================================================
# READ-ONLY DISCOVERY SCRIPT (Execute on Proxmox VE Host Shell)
# ==============================================================================

# [READ-ONLY] 1. Inspect Proxmox VE Version and Kernel
pveversion -v

# [READ-ONLY] 2. Inspect Node Hostname and Hardware Architecture
hostname -f
uname -a
lscpu | grep -E "Model name|Socket|Thread|NUMA|CPU\(s\)"

# [READ-ONLY] 3. Inspect Memory Allocation and Free Capacity
free -h

# [READ-ONLY] 4. Inspect Proxmox Cluster Status
pvecm status 2>/dev/null || echo "[*] Standalone Node (No cluster configured)"

# [READ-ONLY] 5. List All Existing Virtual Machines and Templates
qm list

# [READ-ONLY] 6. Identify Highest and In-Use VM IDs
echo "=== Current VM IDs in Use ==="
qm list | awk 'NR>1 {print $1, $2, $3}' | sort -n

# [READ-ONLY] 7. Inspect Storage Pools, Types, and Assigned Content Types
pvesm status

# [READ-ONLY] 8. Inspect Raw Storage Definitions
cat /etc/pve/storage.cfg

# [READ-ONLY] 9. Inspect Snippets-Enabled Storage (for Cloud-Init Vendor Snippets)
grep -E "snippets|dir:|nfs:" /etc/pve/storage.cfg

# [READ-ONLY] 10. List ISO and Template Storage Inventory
pvesm list local --content iso 2>/dev/null || true
pvesm list NFS-Storage --content iso 2>/dev/null || true

# [READ-ONLY] 11. Inspect Linux Network Bridges and Physical Uplinks
ip -brief link show
cat /etc/network/interfaces

# [READ-ONLY] 12. Check for VLAN-Aware Bridges
grep -E "bridge-vlan-aware|iface vmbr" /etc/network/interfaces

# [READ-ONLY] 13. Inspect Backup Storage Locations
pvesm status -content backup

# [READ-ONLY] 14. Check for Existing Ubuntu Templates
qm list | grep -i ubuntu || echo "[*] No existing Ubuntu templates found."
```

---

## 4. Configuration Variables

Before executing build actions, define standard shell environment variables. All values below use clear placeholders. Customize them according to your organization's naming and networking policy:

```bash
# ==============================================================================
# PROXMOX VDI BUILD ENVIRONMENT VARIABLES
# ==============================================================================
export VM_ID="9000"                              # Unused ID for the initial build VM
export VM_NAME="ubuntu-2404-vdi-gold-build"      # Descriptive build VM hostname
export TEMPLATE_NAME="ubuntu-vdi-2404-gold-v2026.1" # Immutable template tag
export TEMPLATE_VERSION="2026.1.0"               # Semantic image version
export UBUNTU_RELEASE="noble"                    # Ubuntu 24.04 LTS codename
export UBUNTU_IMAGE="noble-server-cloudimg-amd64.img"
export IMAGE_DIR="/var/lib/vz/template/iso"      # Local directory for cached images
export IMAGE_PATH="${IMAGE_DIR}/${UBUNTU_IMAGE}"
export STORAGE="local-lvm"                       # Storage pool supporting VM disk images
export SNIPPET_STORAGE="local"                   # Storage pool supporting snippets
export BACKUP_STORAGE="local"                    # Storage pool for compressed vzdump archives
export BRIDGE="vmbr0"                            # Target network bridge
export VLAN_ID=""                                # Optional 802.1Q VLAN Tag (e.g. 100 or empty)
export CORES="4"                                 # vCPU cores allocated for build
export MEMORY="4096"                             # RAM in MB (4GB)
export DISK_SIZE="32G"                           # Target primary disk size
export CI_USER="vdiadmin"                        # Cloud-init baseline administrative user
export SSH_PUBLIC_KEY_FILE="/root/.ssh/id_ed25519.pub" # Admin SSH public key on PVE
export DNS_SERVER="10.31.0.1"                    # Recursive DNS Resolver
export DNS_DOMAIN="internal.vdi"                 # Search domain
export IP_CONFIG="ip=dhcp"                       # DHCP or static e.g. "ip=10.31.1.250/23,gw=10.31.0.1"
export TIME_ZONE="UTC"                           # Standard system timezone
export LOCALE="en_US.UTF-8"                      # System locale
export KEYBOARD_LAYOUT="us"                      # Default X11 and console keymap
export DESKTOP_ENVIRONMENT="xfce"                # Lightweight desktop
export REMOTE_DESKTOP_SERVICE="xrdp"             # Standard RDP service daemon
```

---

## 5. Image Creation Approaches

### 5.1 Comparison: Cloud Image (Method A) vs. ISO Install (Method B)

| Feature | Method A: Official Cloud Image (Preferred) | Method B: Interactive ISO Installation |
| :--- | :--- | :--- |
| **Build Speed** | Under 3 minutes to base VM; fully automatable | 15–30 minutes manual installer interaction |
| **Reproducibility** | 100% deterministic, scripted, idempotent | Prone to human variance during installer prompts |
| **Initial Footprint** | Minimal OS kernel (~1.8GB raw disk footprint) | Standard server install packages often include clutter |
| **Cloud-Init** | Pre-integrated, optimized for hypervisors | Must be retrofitted or configured via Subiquity autoinstall |
| **Disk Partitions** | Cloud standard single GPT partition; auto-expands | Custom LVM or partition layout possible |
| **Recommended For** | **Standard production golden image pipelines** | Air-gapped networks without cloud image download access |

---

## 6. Create the Proxmox Build VM

### 6.1 Web Interface (GUI) Step-by-Step Procedure
1. Navigate to **Proxmox Web GUI** (`https://<pve-node>:8006`).
2. Click **Create VM** (top right corner):
   - **General**: Node: `<target-node>`, VM ID: `9000`, Name: `ubuntu-2404-vdi-gold-build`. Check *Advanced*.
   - **OS**: Select *Do not use any media*. Guest OS Type: `Linux`, Version: `6.x - 2.6 Kernel`.
   - **System**: Machine: `q35`, BIOS: `OVMF (UEFI)`. Check *Add EFI Disk*, Storage: `<target-storage>`, check *Pre-Enrolled Keys*. SCSI Controller: `VirtIO SCSI Single`. Check *QEMU Agent*.
   - **Disks**: Delete the default IDE/SCSI disk created by the wizard (a pre-formatted cloud disk will be imported via CLI).
   - **CPU**: Sockets: `1`, Cores: `4`, Type: `host` (optimal for multimedia rendering and desktop responsiveness).
   - **Memory**: Memory: `4096`, uncheck *Ballooning Device* (or set Shares high) to maintain fixed desktop RAM timing.
   - **Network**: Bridge: `vmbr0`, Model: `VirtIO (paravirtualized)`. Set VLAN Tag if required.
   - **Confirm**: Verify summary and click **Finish** (do not start the VM yet).
3. Under VM `9000` -> **Hardware**:
   - Add **CloudInit Drive**: Storage: `<target-storage>`.
   - Add **Serial Port**: Port `0`.
   - Change **Display**: Default or `Serial terminal 0` (or `SPICE (qxl)` if SPICE access is required).
4. Under VM `9000` -> **Cloud-Init**:
   - Specify User, Password/SSH Public Key, DNS, and IP Config (DHCP).

---

### 6.2 Equivalent CLI Deployment (Reproducible & Scripted)

Execute on the Proxmox host shell:

```bash
# ==============================================================================
# CHANGE COMMANDS: Download, Verify, and Provision Build VM
# ==============================================================================

# 1. Pre-flight Verification
if qm status "${VM_ID}" &>/dev/null; then
    echo "[-] ERROR: VM ID ${VM_ID} already exists!" >&2
    exit 1
fi

pvesm status -storage "${STORAGE}" >/dev/null || { echo "[-] Storage ${STORAGE} invalid!"; exit 1; }
ip link show dev "${BRIDGE}" >/dev/null || { echo "[-] Bridge ${BRIDGE} invalid!"; exit 1; }

# 2. Download Official Ubuntu 24.04 Cloud Image and SHA256SUMS
mkdir -p "${IMAGE_DIR}"
cd "${IMAGE_DIR}"

if [[ ! -f "${UBUNTU_IMAGE}" ]]; then
    echo "[+] Downloading Ubuntu 24.04 Cloud Image..."
    wget -q --show-progress "https://cloud-images.ubuntu.com/noble/current/${UBUNTU_IMAGE}"
    wget -q "https://cloud-images.ubuntu.com/noble/current/SHA256SUMS"
fi

# 3. Cryptographic Verification
echo "[+] Verifying SHA256 Checksum..."
EXPECTED_HASH=$(grep "${UBUNTU_IMAGE}" SHA256SUMS | awk '{print $1}')
ACTUAL_HASH=$(sha256sum "${UBUNTU_IMAGE}" | awk '{print $1}')

if [[ "${EXPECTED_HASH}" != "${ACTUAL_HASH}" ]]; then
    echo "[-] FATAL: Checksum mismatch for ${UBUNTU_IMAGE}!" >&2
    echo "    Expected: ${EXPECTED_HASH}" >&2
    echo "    Actual:   ${ACTUAL_HASH}" >&2
    exit 1
fi
echo "[+] Checksum Verified: ${ACTUAL_HASH}"

# 4. Create Base VM with q35, OVMF, VirtIO-SCSI-Single, and QEMU Guest Agent
echo "[+] Initializing VM ${VM_ID}..."
qm create "${VM_ID}" \
    --name "${VM_NAME}" \
    --machine q35 \
    --bios ovmf \
    --cpu host \
    --cores "${CORES}" \
    --sockets 1 \
    --memory "${MEMORY}" \
    --balloon 0 \
    --scsihw virtio-scsi-single \
    --net0 "virtio,bridge=${BRIDGE}${VLAN_ID:+,tag=${VLAN_ID}}" \
    --agent enabled=1,fstrim_cloned_disks=1 \
    --vga serial0 \
    --serial0 socket \
    --ostype l26

# 5. Allocate OVMF EFI Disk
echo "[+] Allocating EFI Disk..."
qm set "${VM_ID}" --efidisk0 "${STORAGE}:0,pre-enrolled-keys=1,efitype=4m"

# 6. Import Cloud Image Disk into Target Storage
echo "[+] Importing system disk..."
qm importdisk "${VM_ID}" "${IMAGE_DIR}/${UBUNTU_IMAGE}" "${STORAGE}"

# Retrieve the imported volume identifier
IMPORTED_VOL=$(qm config "${VM_ID}" | grep -o "unused[0-9]" | head -n1)

# 7. Attach as Boot SCSI Disk with TRIM (discard=on) and SSD Emulation
qm set "${VM_ID}" --scsi0 "${STORAGE}:${IMPORTED_VOL},discard=on,ssd=1,iothread=1"

# 8. Resize Disk to Desired Baseline Capacity
qm disk resize "${VM_ID}" scsi0 "${DISK_SIZE}"

# 9. Attach Cloud-Init Drive
qm set "${VM_ID}" --ide2 "${STORAGE}:cloudinit"

# 10. Configure Boot Order & Cloud-Init Provisioning Parameters
qm set "${VM_ID}" --boot order=scsi0
qm set "${VM_ID}" --ciuser "${CI_USER}"
qm set "${VM_ID}" --sshkeys "${SSH_PUBLIC_KEY_FILE}"
qm set "${VM_ID}" --ipconfig0 "${IP_CONFIG}"
qm set "${VM_ID}" --nameserver "${DNS_SERVER}"
qm set "${VM_ID}" --searchdomain "${DNS_DOMAIN}"

# 11. Optional SPICE Audio (Only if audio redirection is required)
# qm set "${VM_ID}" --audio0 device=intel-hda,driver=spice

echo "[+] Build VM ${VM_ID} successfully created."
qm config "${VM_ID}"
```

---

## 7. Base Ubuntu Configuration

Boot the VM and connect via SSH using the configured `CI_USER`:

```bash
# On Proxmox Host: Start VM
qm start 9000

# Wait for IP address via QEMU Guest Agent
BUILD_IP=""
while [[ -z "${BUILD_IP}" ]]; do
    echo "[*] Waiting for guest agent to report IP..."
    sleep 3
    BUILD_IP=$(qm guest cmd 9000 network-get-interfaces 2>/dev/null | jq -r '.[].["ip-addresses"][]? | select(.["ip-address-type"]=="ipv4" and .["ip-address"]!="127.0.0.1") | .["ip-address"]' | head -n1 || true)
done
echo "[+] Build VM active at: ${BUILD_IP}"

# Connect to the guest
ssh -i /root/.ssh/id_ed25519 vdiadmin@${BUILD_IP}
```

### 7.1 System Baseline & Package Management (Guest Shell)

Run inside the Ubuntu VM as root (`sudo -i`):

```bash
# [CHANGE] 1. Update Package Indices and Upgrade Core Packages
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get dist-upgrade -y

# [CHANGE] 2. Install Baseline Utilities and Agent Drivers
apt-get install -y --no-install-recommends \
    qemu-guest-agent \
    openssh-server \
    ca-certificates \
    curl \
    wget \
    vim \
    nano \
    bash-completion \
    chrony \
    unattended-upgrades \
    policykit-1 \
    dbus-x11 \
    net-tools \
    iproute2 \
    dnsutils \
    htop \
    software-properties-common

# [CHANGE] 3. Configure Time Synchronization (Chrony)
systemctl enable --now chrony
chronyc tracking

# [CHANGE] 4. Configure Unattended Security Upgrades
cat <<'EOF' > /etc/apt/apt.conf.d/50unattended-upgrades
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::Package-Blacklist {
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::InstallOnShutdown "false";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
EOF

cat <<'EOF' > /etc/apt/apt.conf.d/20auto-upgrades
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

# [VALIDATION] Verify Services
systemctl is-active qemu-guest-agent
systemctl is-active chrony
systemctl is-active unattended-upgrades
```

---

## 8. Graphical Desktop Installation (XFCE)

### 8.1 Package Selection Strategy
Avoid installing heavy default metapackages:
- `xubuntu-desktop`: Installs games, LibreOffice, multimedia players, Thunderbird, and desktop bloat.
- **Recommended Minimal Set**: Install `xfce4`, `xfce4-terminal`, `xfce4-session`, `thunar`, and standard fonts. This produces a lean, responsive build under 2.2GB total filesystem size.

```bash
# [CHANGE] 1. Install Minimal XFCE and Core Display Components
apt-get install -y --no-install-recommends \
    xorg \
    x11-xserver-utils \
    xfce4 \
    xfce4-session \
    xfce4-panel \
    xfce4-terminal \
    xfce4-appfinder \
    thunar \
    thunar-volman \
    xfwm4 \
    xfconf \
    desktop-file-utils \
    shared-mime-info \
    fonts-dejavu-core \
    fonts-liberation \
    xterm

# [CHANGE] 2. Set Default Target to Graphical
systemctl set-default graphical.target

# [VALIDATION]
systemctl get-default
# Expected: graphical.target
```

---

## 9. Remote Desktop Configuration (xrdp)

### 9.1 xrdp and xorgxrdp Setup
`xorgxrdp` provides superior performance compared to legacy VNC backends by directly interfacing with Xorg display drivers.

```bash
# [CHANGE] 1. Install xrdp and xorgxrdp
apt-get install -y --no-install-recommends xrdp xorgxrdp

# [CHANGE] 2. Add xrdp user to ssl-cert group (required to read /etc/ssl/private/ssl-cert-snakeoil.key)
adduser xrdp ssl-cert

# [CHANGE] 3. Configure Default X Session for xrdp Users
# Set system-wide default X session to xfce4-session
update-alternatives --set x-session-manager /usr/bin/xfce4-session

# Create system-wide fallback in /etc/skel for future user profiles
cat <<'EOF' > /etc/skel/.xsession
#!/bin/sh
export GNOME_SHELL_SESSION_MODE=xfce
export XDG_CURRENT_DESKTOP=XFCE
export XDG_SESSION_DESKTOP=xfce
exec /usr/bin/xfce4-session
EOF
chmod +x /etc/skel/.xsession

# [CHANGE] 4. Configure /etc/xrdp/startwm.sh to Prevent Session Conflicts
# Ensure window managers do not fail or spawn competing GNOME/Wayland processes
cat <<'EOF' > /etc/xrdp/startwm.sh
#!/bin/sh
if [ -r /etc/default/locale ]; then
    . /etc/default/locale
    export LANG LANGUAGE
fi

# Terminate existing dbus daemon to avoid conflicts
unset DBUS_SESSION_BUS_ADDRESS
unset XDG_RUNTIME_DIR

export XDG_CURRENT_DESKTOP=XFCE
export XDG_SESSION_DESKTOP=xfce
exec /usr/bin/xfce4-session
EOF
chmod +x /etc/xrdp/startwm.sh

# [CHANGE] 5. Optimize xrdp Session Configuration (/etc/xrdp/sesman.ini)
# Prevent session disconnect zombie leaks and ensure single-session per user
sed -i 's/^KillDisconnected=.*/KillDisconnected=false/' /etc/xrdp/sesman.ini
sed -i 's/^DisconnectedTimeLimit=.*/DisconnectedTimeLimit=0/' /etc/xrdp/sesman.ini
sed -i 's/^IdleTimeLimit=.*/IdleTimeLimit=0/' /etc/xrdp/sesman.ini
sed -i 's/^MaxSessions=.*/MaxSessions=50/' /etc/xrdp/sesman.ini

# [CHANGE] 6. Resolve Color Manager Polkit Popups
# Desktop environments via xrdp prompt for "Authentication is required to create a color managed device"
mkdir -p /etc/polkit-1/localauthority/50-local.d/
cat <<'EOF' > /etc/polkit-1/localauthority/50-local.d/45-allow-colord.pkla
[Allow Colord for all users]
Identity=unix-user:*
Action=org.freedesktop.color-manager.create-device;org.freedesktop.color-manager.create-profile;org.freedesktop.color-manager.delete-device;org.freedesktop.color-manager.delete-profile;org.freedesktop.color-manager.modify-device;org.freedesktop.color-manager.modify-profile
ResultAny=no
ResultInactive=no
ResultActive=yes
EOF

cat <<'EOF' > /etc/polkit-1/localauthority/50-local.d/46-allow-networkmanager.pkla
[Allow Network Control for all users]
Identity=unix-user:*
Action=org.freedesktop.NetworkManager.network-control
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF

# [CHANGE] 7. Restart and Enable xrdp
systemctl daemon-reload
systemctl enable --now xrdp
systemctl enable --now xrdp-sesman

# [VALIDATION] Verify Listening Ports
ss -tlpn | grep -E "3389|xrdp"
# Expected: LISTEN 0 50 127.0.0.1:3350 (sesman) and LISTEN 0 2 0.0.0.0:3389 (xrdp)
```

---

## 10. VDI User and Profile Strategy

### 10.1 Architecture Recommendations
1. **Never store production user profiles inside the golden image.**
2. **Persistent VDI**: Local user home directories (`/home/<username>`) reside on the clone's virtual disk. User state persists across reboots. Standard VM backup solutions (`vzdump` / PBS) protect the VM.
3. **Non-Persistent VDI**: Virtual disks are rolled back or destroyed on session logoff. Profiles must be mounted from central NFS/SMB shares:
   - Configure `/etc/fstab` or automount (`autofs`) to map `/home/<username>` to an enterprise NFS export.
   - Enforce POSIX ACLs and consistent UID/GID mapping across the fleet via SSSD/LDAP.

### 10.2 Temporary Testing Account (To be purged before sealing)
```bash
# [CHANGE] Create isolated test account
useradd -m -s /bin/bash -c "VDI Test User" vdi-test
echo "vdi-test:TemporaryTestPass123!" | chpasswd
usermod -aG ssl-cert vdi-test

# Copy session template
cp /etc/skel/.xsession /home/vdi-test/.xsession
chown vdi-test:vdi-test /home/vdi-test/.xsession

# [VALIDATION] Perform test RDP login from client workstation to:
#   RDP Server: <BUILD_VM_IP>:3389
#   Username: vdi-test
#   Password: TemporaryTestPass123!
# Verify: XFCE desktop loads, terminal opens, clipboard functions.
```

---

## 11. Directory Integration (Active Directory / SSSD)

> [!IMPORTANT]
> **Golden Image Boundary Principle**: Do **NOT** run `realm join` or join Active Directory inside the golden image! If enrolled inside the template, every cloned VM will share the same machine account and Kerberos keytab, causing immediate Active Directory trust failures.

### 11.1 Pre-Install Directory Integration Packages in Golden Image
Install required binaries inside the build VM so clones do not require package downloads at first boot:

```bash
# [CHANGE] Install realmd and SSSD client packages
apt-get install -y --no-install-recommends \
    realmd \
    sssd \
    sssd-tools \
    adcli \
    samba-common-bin \
    oddjob \
    oddjob-mkhomedir \
    packagekit \
    libpam-sss \
    libnss-sss

# Enable automatic home directory creation on first login
pam-auth-update --enable mkhomedir
```

### 11.2 Post-Clone Join Procedure (To be executed via Cloud-Init or First-Boot Script)
When a clone is deployed, it executes this domain enrollment script with its unique hostname:

```bash
# [POST-CLONE ONLY] Execute on cloned VM:
realm discover internal.domain.com
echo "<SERVICE_ACCOUNT_PASSWORD>" | realm join \
    --user=<JOIN_SERVICE_ACCOUNT> \
    --computer-ou="OU=VDI-Desktops,DC=internal,DC=domain,DC=com" \
    internal.domain.com

# Configure SSSD for desktop performance
sed -i 's/use_fully_qualified_names = True/use_fully_qualified_names = False/' /etc/sssd/sssd.conf
systemctl restart sssd
```

---

## 12. VDI Application Baseline

Install approved organizational applications while maintaining image cleanliness:

| Application Category | In Golden Image? | Post-Clone? | Unique Identity? | Clone Cleanup Required? |
| :--- | :--- | :--- | :--- | :--- |
| **Web Browser (Firefox ESR / Chrome)** | Yes | No | Profile-dependent | Yes (clean default profiles) |
| **PDF Viewer (Evince)** | Yes | No | No | No |
| **Productivity (LibreOffice)** | Yes | No | No | No |
| **Terminal & Text Editor** | Yes | No | No | No |
| **Enterprise VPN (OpenVPN / WireGuard)**| Binaries only | Config post-clone | Yes (Tunnel Keys) | Remove private keys/tunnels |
| **Security Agent (CrowdStrike / Defender)**| Binaries pre-staged | Register on boot | Yes (AID / Machine UUID) | **Mandatory sealing flags** |
| **Monitoring (Zabbix / Datadog)** | Binaries pre-staged | Register on boot | Yes (Host UUID) | Truncate Host UUID configs |

### 12.1 Installing Approved Desktop Applications
```bash
# [CHANGE] Install Standard Enterprise Utilities
apt-get install -y --no-install-recommends \
    evince \
    file-roller \
    p7zip-full \
    curl \
    traceroute

# Install Firefox ESR (avoid snap packages for VDI images to optimize startup latency and memory)
add-apt-repository -y ppa:mozillateam/ppa
cat <<'EOF' > /etc/apt/preferences.d/mozilla-firefox
Package: *
Pin: release o=LP-PPA-mozillateam
Pin-Priority: 1001

Package: firefox*
Pin: release o=Ubuntu*
Pin-Priority: -1
EOF
apt-get update
apt-get install -y --no-install-recommends firefox-esr
```

---

## 13. VDI Optimization

Apply conservative, reversible optimizations to minimize CPU cycles, memory thrashing, and unnecessary I/O on the hypervisor datastore.

```bash
# [CHANGE] 1. Reduce VM Swappiness
# Virtual desktops perform poorly when memory pages are aggressively paged out
echo "vm.swappiness=10" > /etc/sysctl.d/99-vdi-performance.conf
echo "vm.vfs_cache_pressure=50" >> /etc/sysctl.d/99-vdi-performance.conf
sysctl --system

# [CHANGE] 2. Enable Systemd Periodic TRIM (fstrim)
# Reclaims thin-provisioned storage space on Proxmox automatically
systemctl enable fstrim.timer

# [CHANGE] 3. Disable Ubuntu Apport Crash Reporting Daemon
# Eliminates background crash popup overhead and CPU spikes
systemctl mask apport.service

# [CHANGE] 4. Restrict Systemd Journal Size
# Prevents log accumulation across golden image clones
mkdir -p /etc/systemd/journald.conf.d/
cat <<'EOF' > /etc/systemd/journald.conf.d/size-limit.conf
[Journal]
SystemMaxUse=100M
RuntimeMaxUse=50M
MaxRetentionSec=1month
EOF
systemctl restart systemd-journald

# [CHANGE] 5. Disable Screen Blanking and DPMS in XFCE (handled by RDP client)
cat <<'EOF' > /etc/xdg/autostart/disable-dpms.desktop
[Desktop Entry]
Type=Application
Name=Disable DPMS
Exec=xset s off -dpms
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

---

## 14. Security Hardening

Implement defense-in-depth controls tailored for virtual desktops without breaking desktop user sessions:

```bash
# [CHANGE] 1. SSH Hardening (/etc/ssh/sshd_config.d/99-vdi-hardening.conf)
cat <<'EOF' > /etc/ssh/sshd_config.d/99-vdi-hardening.conf
PermitRootLogin prohibit-password
PasswordAuthentication no
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
EOF
systemctl restart ssh

# [CHANGE] 2. Host Firewall (UFW)
# Default Deny Incoming, Allow SSH from admin networks, Allow RDP from trusted subnets
ufw default deny incoming
ufw default allow outgoing
ufw allow from 10.31.0.0/23 to any port 22 proto tcp comment "Admin SSH"
ufw allow from 10.31.0.0/23 to any port 3389 proto tcp comment "VDI RDP Client Subnet"
ufw --force enable

# [CHANGE] 3. Verify AppArmor is Enforcing
aa-status

# [CHANGE] 4. Restrict Polkit Shutdown and Reboot from Remote Sessions
cat <<'EOF' > /etc/polkit-1/localauthority/50-local.d/47-restrict-power.pkla
[Disable Shutdown and Reboot for standard users]
Identity=unix-user:*
Action=org.freedesktop.login1.power-off;org.freedesktop.login1.power-off-multiple-sessions;org.freedesktop.login1.reboot;org.freedesktop.login1.reboot-multiple-sessions
ResultAny=no
ResultInactive=no
ResultActive=no
EOF
```

---

## 15. Clone-Safety Cleanup & Generalization

Before converting a VM into a template, all machine-specific identifiers must be safely removed so that cloned instances generate unique cryptographic and networking identities.

### 15.1 Generalization Matrix

| Component | Target Location | Regeneration Trigger | Consequence of Failure |
| :--- | :--- | :--- | :--- |
| **Machine ID** | `/etc/machine-id` | Truncate to 0 bytes; regenerated by `systemd` on boot | Duplicate IP from DHCP, D-Bus collision, journal corruption |
| **D-Bus ID** | `/var/lib/dbus/machine-id` | Symlink to `/etc/machine-id` | Desktop application IPC conflicts |
| **SSH Host Keys** | `/etc/ssh/ssh_host_*` | Removed; generated by `cloud-init` / `ssh-keygen -A` | Man-in-the-middle vulnerability; duplicate SSH host fingerprint |
| **Cloud-Init State** | `/var/lib/cloud/*` | Purged via `cloud-init clean --logs --seed` | Clones will NOT execute cloud-init on first boot |
| **DHCP Leases** | `/var/lib/dhcp/*`, netif | Removed; requested afresh on link up | IP address collisions across clones |
| **Temporary Test Accounts**| `/home/vdi-test` | Explicit `userdel -r` | Stale credentials left in production images |

---

## 16. Golden-Image Sealing Script

The script below has been written to `/home/nishusaini/Desktop/Innspark/vdi-development/scripts/seal-ubuntu-vdi.sh`.

```bash
#!/usr/bin/env bash
# ==============================================================================
# Script: seal-ubuntu-vdi.sh
# Purpose: Generalize and seal Ubuntu 24.04 LTS VDI build VM before template conversion
# ==============================================================================
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "[-] ERROR: Must be executed as root." >&2
    exit 1
fi

echo "[*] Stopping graphical and remote desktop services..."
systemctl stop xrdp xrdp-sesman lightdm 2>/dev/null || true

echo "[*] Terminating all active user sessions..."
for uid in $(loginctl list-users --no-legend | awk '$1 >= 1000 {print $1}'); do
    loginctl terminate-user "${uid}" || true
done

echo "[*] Purging build test user accounts..."
for test_user in "vdi-test" "testuser"; do
    if id "${test_user}" &>/dev/null; then
        userdel -r -f "${test_user}" 2>/dev/null || true
    fi
done

echo "[*] Purging APT caches and leftover packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get autoremove -y --purge
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -rf /var/cache/apt/archives/*.deb /var/cache/apt/archives/partial/*

echo "[*] Resetting cloud-init instance artifacts..."
cloud-init clean --logs --seed
rm -rf /var/lib/cloud/instances/*
rm -rf /var/lib/cloud/instance
rm -rf /var/lib/cloud/data/*

echo "[*] Resetting machine-id..."
truncate -s 0 /etc/machine-id
rm -f /var/lib/dbus/machine-id
ln -sf /etc/machine-id /var/lib/dbus/machine-id

echo "[*] Purging SSH host keys..."
rm -f /etc/ssh/ssh_host_*_key /etc/ssh/ssh_host_*_key.pub

echo "[*] Purging network state and DHCP client leases..."
rm -f /var/lib/dhcp/* /var/lib/NetworkManager/*.lease /var/lib/systemd/netif/leases/* 2>/dev/null || true
rm -f /etc/udev/rules.d/70-persistent-net.rules 2>/dev/null || true

echo "[*] Purging temporary files and desktop session caches..."
find /tmp -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
find /var/tmp -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
rm -rf /root/.cache/* /etc/skel/.cache/* 2>/dev/null || true

echo "[*] Vacuuming system logs..."
journalctl --rotate 2>/dev/null || true
journalctl --vacuum-time=1s 2>/dev/null || true
truncate -s 0 /var/log/wtmp /var/log/btmp /var/log/lastlog 2>/dev/null || true

echo "[*] Clearing shell history..."
unset HISTFILE
rm -f /root/.bash_history
history -c 2>/dev/null || true

echo "[+] Sealing completed. Synchronizing disks and powering off..."
sync
sync
shutdown -h now
```

---

## 17. Pre-Template Validation

Before converting VM `9000` to a template, verify on the Proxmox host:

```bash
# [READ-ONLY] 1. Confirm VM has completely shut down
qm status 9000
# Expected: status: stopped

# [READ-ONLY] 2. Verify VM Configuration Integrity
qm config 9000

# Key Parameters to verify:
# - boot: order=scsi0
# - scsihw: virtio-scsi-single
# - scsi0: ...,discard=on,ssd=1
# - efidisk0: ...
# - ide2: <storage>:cloudinit
# - agent: 1
```

---

## 18. Backup and Rollback

### 18.1 Concepts
- **Snapshot**: Quick, copy-on-write differential state on the active storage. Used for rollback during building. Snapshots on templates can restrict certain storage operations.
- **Backup (`vzdump`)**: Compressed standalone archive stored on backup storage. Independent of hypervisor storage pools; essential disaster-recovery artifact.
- **Proxmox Template**: Sealed, immutable disk image flagged with `template: 1`. Cannot be started. Serves as parent for clones.

### 18.2 Create and Verify Golden Backup
```bash
# [CHANGE] Execute on Proxmox VE Host Shell:
echo "[*] Generating final verified backup of sealed build VM 9000..."
vzdump 9000 \
    --compress zstd \
    --mode stop \
    --storage "${BACKUP_STORAGE}" \
    --notes-template "Ubuntu 24.04 VDI Golden Image v${TEMPLATE_VERSION} - Pre-Template Sealed State"

# [VALIDATION] Verify Backup Archive
pvesm list "${BACKUP_STORAGE}" --content backup
```

---

## 19. Convert to a Proxmox Template

```bash
# [CHANGE] Execute on Proxmox VE Host Shell:
# 1. Rename to final template naming convention
qm set 9000 --name "${TEMPLATE_NAME}"

# 2. Convert VM into Immutable Template
qm template 9000

# [VALIDATION] Verify Template Status
qm config 9000 | grep "template: 1"
# Expected: template: 1

echo "[+] Golden Template 9000 (${TEMPLATE_NAME}) successfully established."
```

> [!WARNING]
> A converted template cannot be powered on. Attempting `qm start 9000` will fail with `VM 9000 is a template`. Never attempt to convert a running VM.

---

## 20. Create VDI Clones

### 20.1 Approach 1: Persistent Ubuntu VDI (Full Clone)
Use for standard persistent user workstations:

```bash
# Configuration for new persistent desktop
NEW_VMID="201"
DESKTOP_NAME="vdi-user-01"
TARGET_STORAGE="local-lvm"
USER_SSH_KEY="/root/.ssh/id_ed25519.pub"

# 1. Create Full Independent Clone
qm clone 9000 "${NEW_VMID}" \
    --name "${DESKTOP_NAME}" \
    --full 1 \
    --storage "${TARGET_STORAGE}"

# 2. Adjust Hardware Sizing (Optional)
qm set "${NEW_VMID}" --cores 4 --memory 8192

# 3. Expand Disk for User Workload
qm disk resize "${NEW_VMID}" scsi0 +20G

# 4. Configure Unique Cloud-Init Settings
qm set "${NEW_VMID}" \
    --ciuser "vdiuser" \
    --sshkeys "${USER_SSH_KEY}" \
    --ipconfig0 "ip=dhcp"

# 5. Start the Desktop VM
qm start "${NEW_VMID}"
```

### 20.2 Approach 2: Non-Persistent Ubuntu VDI (Linked Clone)
Use for lab, kiosk, or ephemeral pooled sessions:

```bash
LINKED_VMID="301"
POOL_NAME="vdi-pool-kiosk-01"

# 1. Create Linked Clone (Instant Provisioning, shared base storage)
qm clone 9000 "${LINKED_VMID}" \
    --name "${POOL_NAME}" \
    --full 0

# 2. Configure Cloud-Init
qm set "${LINKED_VMID}" \
    --ciuser "kiosk" \
    --ipconfig0 "ip=dhcp"

# 3. Start
qm start "${LINKED_VMID}"

# Reset Procedure (To revert to clean state at end of shift):
# qm stop 301
# qm destroy 301
# qm clone 9000 301 --name "vdi-pool-kiosk-01" --full 0 && qm start 301
```

---

## 21. First-Boot Validation

Execute these automated checks on a booted clone to ensure full system health:

```bash
# [READ-ONLY] Execute inside Cloned VM (or via 'qm guest exec <VMID>'):

# 1. Check Cloud-Init Completion
cloud-init status --wait
# Expected: status: done

# 2. Verify Unique Machine ID
cat /etc/machine-id
# Expected: 32-character hex string (NOT empty, NOT identical to other clones)

# 3. Verify QEMU Guest Agent
systemctl is-active qemu-guest-agent
# Expected: active

# 4. Verify xrdp Remote Desktop Service
systemctl is-active xrdp
ss -tlpn | grep 3389
# Expected: active / LISTEN on 0.0.0.0:3389

# 5. Verify Disk Automatic Expansion
df -h /
# Expected: Root filesystem matches resized capacity

# 6. Verify AppArmor Enforcing Mode
aa-status | grep "apparmor module is loaded"
# Expected: loaded and enforcing
```

---

## 22. Multi-Clone Uniqueness Test

To guarantee that templates do not leak static identities, deploy two test clones (`201` and `202`) and run the uniqueness comparison script `/home/nishusaini/Desktop/Innspark/vdi-development/scripts/verify-clone-uniqueness.sh`:

```bash
# Execute on Proxmox Host:
/home/nishusaini/Desktop/Innspark/vdi-development/scripts/verify-clone-uniqueness.sh 10.31.1.201 10.31.1.202 vdiadmin
```

Expected Validation Output:
```
======================================================================
          UBUNTU VDI MULTI-CLONE UNIQUENESS VERIFICATION               
======================================================================
[*] Checking Hostname... PASSED (Unique)
    Clone 1: vdi-user-01
    Clone 2: vdi-user-02
[*] Checking /etc/machine-id... PASSED (Unique)
    Clone 1: e6a422119c8f498c8c7d81a98075bc01
    Clone 2: 7f3b890a23dc4efbb92100874135ab88
[*] Checking MAC Address... PASSED (Unique)
    Clone 1: bc:24:11:8a:02:14
    Clone 2: bc:24:11:8a:02:15
[*] Checking IP Address... PASSED (Unique)
    Clone 1: 10.31.1.201
    Clone 2: 10.31.1.202
[*] Checking SSH Host Key (ed25519)... PASSED (Unique)
    Clone 1: SHA256:4t7Xw+N...
    Clone 2: SHA256:8k2Lp-Q...
======================================================================
 RESULT: ALL UNIQUENESS VERIFICATIONS PASSED.
```

---

## 23. Template Maintenance & Versioning

Never modify an active production template directly. Adopt an **Immutable Versioned Lifecycle**:

```
+-----------------------------------+
| Active Template: v2026.1 (ID: 9000)| (DO NOT TOUCH)
+-----------------------------------+
                  │
                  ▼ (qm clone 9000 9099 --full 1)
+-----------------------------------+
|  Maintenance VM: ID 9099          |
|  - Boot and Apply apt-get upgrade  |
|  - Update security agents         |
|  - Test xrdp & desktop session    |
|  - Execute seal-ubuntu-vdi.sh     |
+-----------------------------------+
                  │
                  ▼ (qm template 9099)
+-----------------------------------+
| New Template: v2026.2 (ID: 9001)   |
|  - Acceptance testing on 2 clones |
|  - Production promotion signoff   |
|  - Archive v2026.1 after 30 days  |
+-----------------------------------+
```

---

## 24. Proxmox Automation Script

The non-destructive build automation script is located at `/home/nishusaini/Desktop/Innspark/vdi-development/scripts/create-ubuntu-vdi-build-vm.sh`.

It features:
- Complete pre-flight validation (verifies CLI tools, unused VM ID, storage pool capabilities, network bridges)
- Cryptographic SHA256 verification of Ubuntu cloud images
- Interactive confirmation prompt before modifying hypervisor state
- Structured execution logging to `/var/log/pve-vdi-builder-*.log`
- Clean hand-off to operator for guest configuration and sealing

---

## 25. Troubleshooting Guide

### Issue 1: xrdp Session Shows Blank / Black Screen on Login
- **Likely Cause**: Missing or conflicting `.xsession` configuration; desktop manager trying to launch Wayland or GNOME session.
- **Diagnostic Commands**:
  ```bash
  cat ~/.xsession
  journalctl -u xrdp-sesman.service -n 50 --no-pager
  cat /var/log/xrdp.log
  ```
- **Corrective Action**:
  Ensure `/etc/skel/.xsession` contains:
  ```sh
  export XDG_CURRENT_DESKTOP=XFCE
  export XDG_SESSION_DESKTOP=xfce
  exec /usr/bin/xfce4-session
  ```
  Copy to user home: `cp /etc/skel/.xsession ~/.xsession && chown $USER:$USER ~/.xsession`
- **Validation**: Reconnect via RDP; XFCE panel and desktop wallpaper load immediately.

---

### Issue 2: Polkit Prompt "Authentication is required to create a color profile"
- **Likely Cause**: `colord` daemon queries PolicyKit on remote display session setup.
- **Diagnostic Commands**:
  ```bash
  journalctl -xe | grep -i polkit
  ```
- **Corrective Action**:
  Create `/etc/polkit-1/localauthority/50-local.d/45-allow-colord.pkla` as detailed in Section 9.1. Restart Polkit: `systemctl restart polkit`.

---

### Issue 3: Duplicate IP Address or DHCP Failures Across Clones
- **Likely Cause**: `/etc/machine-id` was not truncated prior to template conversion. Ubuntu Netplan uses `machine-id` by default to derive DHCP DUID.
- **Diagnostic Commands**:
  ```bash
  cat /etc/machine-id
  ```
- **Corrective Action**:
  Inside clone:
  ```bash
  truncate -s 0 /etc/machine-id
  systemd-machine-id-setup
  systemctl restart systemd-networkd || netplan apply
  ```

---

### Issue 4: QEMU Guest Agent Not Responding on Proxmox
- **Likely Cause**: Agent daemon not running inside guest or QEMU agent socket missing on VM configuration.
- **Diagnostic Commands**:
  ```bash
  # On Proxmox:
  qm agent <VMID> ping
  # Inside Guest:
  systemctl status qemu-guest-agent
  ```
- **Corrective Action**:
  Ensure VM hardware has `agent: 1` (`qm set <VMID> --agent enabled=1`).
  Inside guest: `systemctl enable --now qemu-guest-agent`.

---

## 26. Final Acceptance Checklist

### Hypervisor Infrastructure (Proxmox VE)
- [ ] VM ID is dedicated and recorded in configuration management.
- [ ] Machine type set to `q35` with modern PCIe layout.
- [ ] Firmware configured as OVMF UEFI with 4MB EFI Disk.
- [ ] Storage Controller set to `VirtIO SCSI Single` with IOThreads enabled.
- [ ] Primary SCSI disk configured with `discard=on` (TRIM) and SSD emulation.
- [ ] Network adapter set to VirtIO with correct bridge and VLAN tag.
- [ ] Cloud-Init CD-ROM drive attached on IDE or SCSI bus.
- [ ] Boot order explicitly locked to `scsi0`.
- [ ] Compressed `.vst.zst` backup created and verified in backup datastore.
- [ ] Template conversion verified (`template: 1` in `qm config`).

### Guest Operating System (Ubuntu 24.04 LTS VDI)
- [ ] Minimal Ubuntu Server 24.04 LTS base image utilized.
- [ ] Unattended security updates active and scheduled.
- [ ] Chrony NTP synchronization healthy and tracking.
- [ ] Minimal XFCE desktop installed without bloatware.
- [ ] `xrdp` and `xorgxrdp` active and listening on port 3389.
- [ ] PolicyKit rules prevent color manager and power-off authorization prompts.
- [ ] No real or production user profiles baked into the image.
- [ ] All temporary test accounts completely purged.
- [ ] `cloud-init clean --logs --seed` executed before shutdown.
- [ ] `/etc/machine-id` truncated to 0 bytes.
- [ ] SSH host keys purged (`/etc/ssh/ssh_host_*`).
- [ ] Multi-clone uniqueness test passed (distinct MAC, IP, machine-id, and SSH keys).
