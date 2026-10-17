# Production Runbook: Windows 10/11 VDI Golden Image on Proxmox VE

This document is an end-to-end, enterprise-grade engineering runbook for designing, provisioning, optimizing, hardening, sysprepping, sealing, and lifecycle-managing a **Windows 10 / Windows 11 Virtual Desktop Infrastructure (VDI) Golden Image** in **Proxmox Virtual Environment (PVE)**.

---

## 1. Intended Architecture

### 1.1 Architectural Rationale
Delivering Windows virtual desktops from a type-1 hypervisor like Proxmox VE provides high-density compute consolidation, enterprise storage integration (ZFS, Ceph, LVM-Thin, SAN), hardware acceleration, and rapid template cloning. 

However, Windows client operating systems (Windows 10 22H2, Windows 11 23H2/24H2) are inherently designed for standalone physical PCs. When deployed unmodified across hundreds of virtual machines on shared enterprise storage and hypervisors, default Windows background processes (indexing, telemetry, defragmentation, background store app updates) trigger severe **IOPS storms** and **CPU starvation**.

To achieve sub-second latency, deterministic boot times, and maximum VM density, this architecture incorporates:
1. **Modern PCIe Bus & Firmware**: The `q35` PCIe machine type paired with OVMF (UEFI) and dedicated 4MB EFI storage with pre-enrolled Microsoft SecureBoot keys.
2. **Virtual TPM 2.0 (swtpm)**: Dedicated vTPM device emulated by the hypervisor to fulfill Windows 11 hardware attestation and BitLocker encryption requirements.
3. **Paravirtualized I/O (VirtIO)**:
   - **VirtIO SCSI Single Controller (`virtio-scsi-single`)**: High-throughput storage controller with dedicated IOThreads and TRIM/Discard support.
   - **VirtIO Network Adapter (`virtio`)**: Multi-gigabit paravirtualized network throughput.
   - **VirtIO Ballooning (`balloon`)**: Memory balloon driver for hypervisor memory visibility.
   - **VirtIO Serial & QEMU Guest Agent (`qemu-ga`)**: Bi-directional communication channel enabling graceful shutdowns, live IP reporting, disk freeze/thaw for crash-consistent backups, and guest command execution.
4. **Display & Audio Subsystem**: SPICE QXL display adapter (`qxl`) with SPICE VDAGENT (clipboard sharing, dynamic resolution scaling) combined with `ich9-intel-hda` audio for high-fidelity audio redirection over RDP and SPICE.
5. **Sysprep Generalization with Hardware Persistence**: Windows System Preparation Tool (`sysprep.exe`) configured with `<PersistAllDeviceInstalls>true</PersistAllDeviceInstalls>` to ensure VirtIO SCSI and network drivers are never stripped during generalization, completely eliminating first-boot `INACCESSIBLE_BOOT_DEVICE` blue screens.

```
+-----------------------------------------------------------------------------------+
|                            Remote Clients (Thin / PC)                             |
|        [ Windows App / Remote Desktop Client / Web Browser / SPICE Viewer ]        |
+-----------------------------------------------------------------------------------+
                                         │  (RDP Port 3389 / SPICE / TLS)
                                         ▼
+-----------------------------------------------------------------------------------+
|                         Proxmox VE Hypervisor Host                                |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |             Windows 10 / Windows 11 VDI Guest Virtual Machine                |  |
|  |                                                                             |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  Desktop Experience (Shell, Multi-Monitor, Font Smoothing, Audio)     |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  Remote Access & Network: Remote Desktop (RDP/NLA) / SPICE VDAgent    |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  VDI Optimization Layer: Telemetry Off, WSearch Off, SysMain Off     |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  Hypervisor Integration: QEMU Guest Agent (qemu-ga) & Balloon Svc    |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  |  |  VirtIO Drivers: vioscsi, NetKVM, vioser, viostor, qxldod             |  |  |
|  |  +-----------------------------------------------------------------------+  |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  Hypervisor Layer: q35 PCIe Bus | OVMF (UEFI 4M) | vTPM 2.0 | VirtIO-SCSI-Single  |
|  Storage Layer: ZFS / Ceph / LVM-Thin / NVMe-oF / Enterprise SAN                  |
+-----------------------------------------------------------------------------------+
```

### 1.2 Specification Summary
- **Target OS**: Windows 11 Enterprise/Pro (23H2 / 24H2) or Windows 10 Enterprise/Pro (22H2)
- **Hypervisor**: Proxmox VE 8.x (Linux 6.8+ kernel)
- **Machine Type**: `q35` (Modern PCIe bus architecture)
- **BIOS Firmware**: `OVMF (UEFI)` with 4MB EFI Disk and pre-enrolled keys
- **Security Hardware**: Virtual TPM 2.0 (`tpmstate0`, version `v2.0`)
- **vCPU Topology**: Sockets: `1`, Cores: `4+`, Type: `host` (exposes AVX2, SSE4.2, and native instructions)
- **RAM**: 8192 MB (8GB) fixed; dynamic ballooning disabled (`balloon: 0`) for stable desktop frame rates
- **Storage Controller**: `virtio-scsi-single` with `iothread=1`
- **System Disk**: SCSI 0 (`scsi0`), `discard=on` (TRIM support), SSD emulation (`ssd=1`)
- **Network Interface**: `virtio` on `vmbr0` (with optional 802.1Q VLAN tagging)
- **Display Adapter**: SPICE QXL (`qxl,memory=64`)
- **Audio Device**: `ich9-intel-hda` with SPICE audio driver
- **Guest Agent**: Enabled (`agent: enabled=1,fstrim_cloned_disks=1`)

---

## 2. Assumptions and Limitations

### 2.1 Environmental Assumptions
1. Proxmox VE 8.x cluster or standalone node is active and reachable via SSH and Web GUI (`https://<node>:8006`).
2. An active storage pool supporting VM disk images (`images`) exists (e.g., `local-lvm`, `ceph-pool`, `zfs-pool`).
3. An ISO storage pool exists with sufficient space for the Windows 10/11 installation ISO (~5–6 GB) and Fedora VirtIO driver ISO (~600 MB).
4. An active network bridge (e.g., `vmbr0`) with DHCP server access or static IP assignment is available.

### 2.2 Proxmox Template vs. Complete VDI Brokering Platform
A **Proxmox VM Template** represents an immutable disk master and hardware definition.
- **What Proxmox Provides**: Instantaneous linked clones (`--full 0`), full clones (`--full 1`), automated snapshotting, live migration, and hypervisor resource scheduling.
- **What Proxmox Does NOT Provide**: Dynamic user entitlement brokering, session reconnect across hypervisor nodes, HTML5 clientless web gateways, and dynamic profile disk mounting.

To implement a full enterprise desktop-as-a-service (DaaS) solution, pair Proxmox templates with a dedicated VDI connection broker:
- **OpenUDS**: Enterprise open-source connection broker with native Proxmox VE integration, active directory user pools, and HTML5 RDP tunneling.
- **Apache Guacamole**: Clientless HTML5 gateway supporting RDP and SPICE without requiring client software.
- **Leostream**: Enterprise broker supporting Active Directory pools, MFA, and automated Proxmox VM lifecycle management.

### 2.3 Persistent vs. Non-Persistent VDI Models
| Dimension | Persistent VDI (Dedicated) | Non-Persistent VDI (Floating / Pooled) |
| :--- | :--- | :--- |
| **Clone Type** | Full Clone (`qm clone <TID> <VMID> --full 1`) | Linked Clone (`qm clone <TID> <VMID> --full 0`) |
| **Provisioning Speed** | 2–5 minutes per VM | 3–10 seconds per VM |
| **Storage Usage** | 64GB+ per VM | 500MB delta per VM initially |
| **User Customization** | Preserved across reboots | Discarded on session logoff / reset |
| **User Data Storage** | Local C: drive or redirected folders | Stored in **FSLogix Profile Containers (VHDX)** |
| **Use Case** | Software developers, engineering, power users | Shift workers, kiosks, call centers, students |

---

## 3. Read-Only Environment Discovery

Execute these commands from the Proxmox VE host shell to survey the hypervisor environment prior to provisioning:

```bash
# ==============================================================================
# READ-ONLY DISCOVERY SCRIPT (Execute on Proxmox VE Host Shell)
# ==============================================================================

# [READ-ONLY] 1. Inspect Proxmox VE Version and Kernel
pveversion -v

# [READ-ONLY] 2. Inspect Node Hostname and Hardware Architecture
hostname -f
lscpu | grep -E "Model name|Socket|Thread|NUMA|CPU\(s\)|Flags"

# [READ-ONLY] 3. Inspect Memory Allocation and Free Capacity
free -h

# [READ-ONLY] 4. List All Existing Virtual Machines and Identify Unused VM IDs
qm list
echo "=== Current VM IDs in Use ==="
qm list | awk 'NR>1 {print $1, $2, $3}' | sort -n

# [READ-ONLY] 5. Inspect Storage Pools, Types, and Content Support
pvesm status

# [READ-ONLY] 6. Check for Existing ISO Files (Windows and VirtIO)
pvesm list local --content iso 2>/dev/null || true

# [READ-ONLY] 7. Inspect Network Bridges and Interfaces
ip -brief link show
grep -E "iface vmbr|bridge-vlan-aware" /etc/network/interfaces
```

---

## 4. Configuration Variables

Set these shell variables before running deployment commands:

```bash
# ==============================================================================
# WINDOWS VDI BUILD ENVIRONMENT VARIABLES
# ==============================================================================
export VM_ID="9100"                                      # Unused ID for the build VM
export WINDOWS_VERSION="win11"                           # "win11" or "win10"
export VM_NAME="win11-vdi-gold-build"                    # Descriptive build VM name
export TEMPLATE_NAME="win11-vdi-gold-v2026.1"            # Immutable template name
export STORAGE="local-lvm"                               # VM disk storage pool (supports 'images')
export ISO_STORAGE="local"                               # ISO storage pool (supports 'iso')
export BRIDGE="vmbr0"                                    # Network bridge
export VLAN_ID=""                                        # Optional VLAN ID (e.g. 20)
export CORES="4"                                         # vCPUs (minimum 4 recommended)
export MEMORY="8192"                                     # Memory in MB (8GB)
export BALLOON="0"                                       # 0 disables ballooning for stable VDI latency
export DISK_SIZE="64G"                                   # System disk size
export WIN_ISO_NAME="Win11_23H2_English_x64.iso"         # Windows installer ISO filename
export VIRTIO_ISO_NAME="virtio-win.iso"                  # VirtIO drivers ISO filename
export ISO_DIR="/var/lib/vz/template/iso"                # ISO directory path on PVE
```

---

## 5. Image Creation Approaches

### 5.1 Comparison: VirtIO-Injected ISO vs. Interactive Setup

| Feature | Method A: Interactive ISO + VirtIO CD-ROM | Method B: Unattended Pre-Injected ISO |
| :--- | :--- | :--- |
| **Setup Complexity** | Low (attach 2 ISOs, click 'Load driver' once) | High (requires slipstreaming drivers into boot.wim) |
| **Driver Availability** | Loads drivers directly from mounted Fedora ISO | Drivers pre-integrated into Windows Setup image |
| **Flexibility** | Allows testing different VirtIO driver builds easily | Requires rebuilding ISO on driver updates |
| **Recommendation** | **Standard production approach for Proxmox** | Advanced large-scale automated CI/CD pipelines |

---

## 6. Create the Proxmox Build VM

### 6.1 Web Interface (GUI) Step-by-Step Procedure
1. Log in to **Proxmox Web GUI** (`https://<pve-node>:8006`).
2. Click **Create VM** (top right):
   - **General**: Node: `<target-node>`, VM ID: `9100`, Name: `win11-vdi-gold-build`. Check *Advanced*.
   - **OS**: 
     - Select *Use CD/DVD disc image file (iso)*: Storage: `local`, ISO Image: `Win11_23H2_English_x64.iso`.
     - Type: `Microsoft Windows`, Version: `11/2022/2025` (or `10/2016/2019`).
     - Check *Add additional drive for VirtIO drivers*: Storage: `local`, ISO: `virtio-win.iso`.
   - **System**:
     - Graphic card: `SPICE (qxl)`.
     - Machine: `q35`.
     - BIOS: `OVMF (UEFI)`.
     - Check *Add EFI Disk*: Storage: `local-lvm`, Pre-Enrolled Keys: checked.
     - SCSI Controller: `VirtIO SCSI Single`.
     - Check *Add TPM*: Storage: `local-lvm`, Version: `v2.0`.
     - Check *QEMU Agent*.
   - **Disks**:
     - Bus/Device: `SCSI`, ID: `0`.
     - Storage: `local-lvm`, Disk size: `64 GB`.
     - Cache: `Default (No cache)` or `Write back`.
     - Check *Discard* (enables TRIM).
     - Check *SSD emulation*.
     - Check *IO Thread*.
   - **CPU**:
     - Sockets: `1`, Cores: `4`, Type: `host`.
   - **Memory**:
     - Memory: `8192 MB`, Ballooning: uncheck (or set to 0).
   - **Network**:
     - Bridge: `vmbr0`, Model: `VirtIO (paravirtualized)`. Set VLAN Tag if required.
   - **Audio**:
     - After creation, go to VM -> **Hardware** -> **Add** -> **Audio Device** -> Device: `ich9-intel-hda`, Driver: `spice`.
3. Verify summary and click **Finish**.

---

### 6.2 Equivalent CLI Deployment (Scripted)

Run directly on the Proxmox host shell:

```bash
# 1. Download VirtIO Drivers ISO if not present
mkdir -p /var/lib/vz/template/iso
if [ ! -f "/var/lib/vz/template/iso/virtio-win.iso" ]; then
    wget -O /var/lib/vz/template/iso/virtio-win.iso \
        https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso
fi

# 2. Create the VM with exact q35, OVMF, vTPM 2.0, VirtIO SCSI & Audio configuration
qm create 9100 \
    --name win11-vdi-gold-build \
    --machine q35 \
    --bios ovmf \
    --cpu host \
    --cores 4 \
    --sockets 1 \
    --memory 8192 \
    --balloon 0 \
    --scsihw virtio-scsi-single \
    --net0 virtio,bridge=vmbr0 \
    --agent enabled=1,fstrim_cloned_disks=1 \
    --vga qxl,memory=64 \
    --audio0 device=ich9-intel-hda,driver=spice \
    --ostype win11

# 3. Add EFI Disk (4MB with SecureBoot keys)
qm set 9100 --efidisk0 local-lvm:0,pre-enrolled-keys=1,efitype=4m

# 4. Add Virtual TPM 2.0 (swtpm)
qm set 9100 --tpmstate0 local-lvm:0,version=v2.0

# 5. Create 64GB VirtIO SCSI System Disk with TRIM and SSD Emulation
qm set 9100 --scsi0 local-lvm:64,discard=on,ssd=1,iothread=1

# 6. Attach Windows Installation ISO and VirtIO Driver ISO
qm set 9100 --ide0 local:iso/Win11_23H2_English_x64.iso,media=cdrom
qm set 9100 --ide2 local:iso/virtio-win.iso,media=cdrom

# 7. Set Boot Order (Windows ISO first, then SCSI Disk)
qm set 9100 --boot order=ide0;scsi0
```

---

## 7. Windows Installation & VirtIO Driver Loading

1. Start the VM:
   ```bash
   qm start 9100
   ```
2. Open the Proxmox Console (**SPICE** or **noVNC**).
3. Press any key when prompted (`Press any key to boot from CD or DVD...`).
4. Select Language, Time, and Keyboard -> click **Next** -> click **Install now**.
5. When prompted *Where do you want to install Windows?*, the disk list will be empty (expected, as Windows lacks VirtIO SCSI drivers out-of-the-box).
6. **Load VirtIO SCSI Driver**:
   - Click **Load driver** -> click **Browse**.
   - Expand the mounted CD Drive labeled `virtio-win`.
   - Navigate to: `vioscsi` -> `w11` (or `w10`) -> `amd64`.
   - Select **Red Hat VirtIO SCSI controller** -> click **Next**.
   - The 64 GB primary SCSI drive appears immediately!
7. Select **Drive 0 Unallocated Space** and click **Next**.
8. Windows Setup will partition the disk, copy files, and reboot into the Out-of-Box Experience (OOBE).

---

## 8. VirtIO Guest Tools & QEMU Agent Installation

Once logged into the Windows desktop:

1. Open **File Explorer** and navigate to `This PC`.
2. Double-click the **CD Drive: virtio-win**.
3. Run **`virtio-win-guest-tools.exe`**.
4. Complete the installation wizard with all defaults selected. This automatically installs:
   - **NetKVM**: Red Hat VirtIO Ethernet Adapter driver (connects VM to network).
   - **vioscsi**: VirtIO SCSI Controller driver.
   - **vioser**: VirtIO Serial driver.
   - **Balloon**: VirtIO Balloon memory service.
   - **qemu-ga**: QEMU Guest Agent Windows service.
   - **SPICE vdagent**: SPICE agent for dynamic screen resolution resizing and clipboard synchronization.
5. Verify services in PowerShell:
   ```powershell
   Get-Service -Name "qemu-ga", "BalloonService", "spice-vdagent"
   ```
6. From the Proxmox host shell, verify agent communication:
   ```bash
   qm guest ping 9100
   qm guest cmd 9100 network-get-interfaces
   ```

---

## 9. Remote Desktop (RDP) & Display Configuration

Windows VDI primarily relies on Microsoft Remote Desktop Protocol (RDP) for end-user access.

Execute inside an elevated PowerShell prompt within the Windows VM:

```powershell
# 1. Enable Remote Desktop
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0

# 2. Enforce Network Level Authentication (NLA)
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Name "UserAuthentication" -Value 1

# 3. Allow Remote Desktop through Windows Firewall
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

# 4. Enable Audio Redirection over RDP (Capture and Playback)
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Name "fDisableAudioCapture" -Value 0
Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server\WinStations\RDP-Tcp" -Name "fDisableCam" -Value 0

# 5. Enable Multi-Monitor High FPS RDP Experience
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services" -Name "SelectTransport" -Value 1 -ErrorAction SilentlyContinue
```

---

## 10. VDI User and Profile Strategy

### 10.1 Persistent VDI Model
- Users log in as local administrators or Active Directory domain users.
- User data, application settings, and browser profiles reside permanently on `C:\Users\%USERNAME%`.
- Backup policies protect the full VM via Proxmox Backup Server (PBS).

### 10.2 Non-Persistent VDI Model with FSLogix Profile Containers
In non-persistent pools (linked clones), desktop state is reset on logoff. To preserve user data seamlessly:
1. Deploy **Microsoft FSLogix Profile Containers**.
2. Mount an SMB file share (e.g. `\\fs01.internal.vdi\profiles$`).
3. During user login, FSLogix mounts a virtual disk (`Profile_%USERNAME%.vhdx`) dynamically under `C:\Users\%USERNAME%`.
4. The user experiences a persistent desktop while the underlying VM remains completely stateless.

```powershell
# Install FSLogix (Download from Microsoft)
# Configure FSLogix Profile Container via Registry
$FSLogixPath = "HKLM:\SOFTWARE\FSLogix\Profiles"
if (-not (Test-Path $FSLogixPath)) { New-Item -Path $FSLogixPath -Force | Out-Null }
Set-ItemProperty -Path $FSLogixPath -Name "Enabled" -Value 1 -Type DWord
Set-ItemProperty -Path $FSLogixPath -Name "VHDLocations" -Value "\\fs01.internal.vdi\profiles$" -Type MultiString
Set-ItemProperty -Path $FSLogixPath -Name "VolumeType" -Value "VHDX" -Type String
Set-ItemProperty -Path $FSLogixPath -Name "SizeInMBs" -Value 30000 -Type DWord
```

---

## 11. Active Directory & Enterprise Integration

To join cloned desktops to Active Directory or Azure AD:
- **Do NOT join the Golden Image to the Active Directory domain prior to Sysprep!**
- The Golden Image must remain in a clean WORKGROUP state.
- Clones join the domain on their **first boot** via:
  1. Sysprep `unattend.xml` under `<Identification>`:
     ```xml
     <Identification>
       <Credentials>
         <Domain>INTERNAL</Domain>
         <Password>JoinPassword123</Password>
         <Username>domainjoinuser</Username>
       </Credentials>
       <JoinDomain>internal.vdi</JoinDomain>
     </Identification>
     ```
  2. Or post-deployment automation (PowerShell `Add-Computer` or VDI connection broker).

---

## 12. VDI Application Baseline

Install enterprise core software into the Golden Image before sealing:

1. **Microsoft Visual C++ Redistributable All-In-One**:
   - Essential for enterprise applications, runtimes, and developer tools.
2. **Web Browsers**:
   - Google Chrome / Mozilla Firefox / Microsoft Edge.
   - Configure master preferences to disable auto-launch and background update daemons.
3. **Microsoft 365 Apps / Office**:
   - Install with **Shared Computer Licensing** enabled:
     ```xml
     <Configuration>
       <Add OfficeClientEdition="64" Channel="Current">
         <Product ID="O365ProPlusRetail">
           <Language ID="en-us" />
         </Product>
       </Add>
       <Property Name="SharedComputerLicensing" Value="1" />
     </Configuration>
     ```
4. **Enterprise Utilities**:
   - 7-Zip, Adobe Acrobat Reader, enterprise monitoring agents.

---

## 13. Windows VDI Optimization

Standard Windows includes numerous consumer background processes that cause hypervisor write amplification and high CPU usage.

### 13.1 Key Optimizations
1. **Disable Hibernation (`powercfg /h off`)**:
   - Reclaims 6–8 GB of disk space (`hiberfil.sys`).
   - Disables Fast Startup (which causes stale state in linked clones).
2. **Disable Windows Search Indexer (`WSearch`)**:
   - Prevents continuous disk indexing across hundreds of clones on shared storage pools.
3. **Disable Superfetch / SysMain**:
   - Unnecessary on hypervisors with flash/SSD arrays and causes write bursts.
4. **Disable Scheduled Defragmentation**:
   - Hypervisor thin provisioning handles storage reclamation via TRIM (`discard=on`). Defragmentation inside guests causes severe hypervisor write amplification.
5. **Disable Telemetry & Consumer Experience**:
   - Stops automatic background installation of consumer apps (games, social media) and telemetry uploads.
6. **Tune Visual Effects**:
   - Disable window animations, shadows, and smooth scrolling for reduced streaming bandwidth.
   - **Retain Font Smoothing (ClearType)** to ensure text remains sharp over RDP.

---

## 14. Security Hardening

1. **Virtual TPM 2.0 Attestation**:
   - Verifies guest integrity and enables Windows 11 BitLocker / Credential Guard.
2. **Windows Defender VDI Tuning**:
   - If using FSLogix, exclude VHD/VHDX profile paths from real-time scanning:
     ```powershell
     Add-MpPreference -ExclusionExtension ".vhdx", ".vhd"
     ```
3. **Local Account Security**:
   - Ensure the built-in local administrator has a strong password.
   - Disable guest accounts.

---

## 15. Sysprep Preparation & Generalization

### 15.1 Why Sysprep is Mandatory
Sysprep (`sysprep.exe`) prepares an installation of Windows for duplication across multiple VMs:
1. **Security Identifier (SID) Reset**: Every Windows installation has a Machine SID. If multiple VMs share the same SID, Active Directory, WSUS, SCCM, and security tokens fail catastrophically. Sysprep regenerates a unique SID on first boot.
2. **Hardware Identity Generalization**: Cleans machine-specific identifiers, MAC bindings, and plug-and-play states.
3. **OOBE Automation**: Resets the setup state so clones run unattended initial setup via `unattend.xml`.

### 15.2 The VirtIO Driver Persistence Safeguard
By default, `sysprep.exe /generalize` removes third-party device drivers. If VirtIO drivers are removed, the cloned VM cannot access its SCSI boot disk and will crash on first boot with:
```
STOP: 0x0000007B (INACCESSIBLE_BOOT_DEVICE)
```
To prevent this, the Sysprep answer file MUST include:
```xml
<component name="Microsoft-Windows-PnpSysprep" ...>
  <PersistAllDeviceInstalls>true</PersistAllDeviceInstalls>
</component>
```

### 15.3 The AppX Package Sysprep Trap (Error 0x80073cf2)
In Windows 10 and 11, if Windows Store automatically updates built-in UWP apps for the logged-in build user, Sysprep will abort with error:
`SYSPRP Package ... was installed for a user, but not provisioned for all users.`
Our optimization script strips conflicting user-specific packages and stops Store updates prior to Sysprep.

---

## 16. Golden-Image Sealing Script

The PowerShell script `optimize-and-seal-windows-vdi.ps1` automates all optimizations, bloatware cleanup, log truncation, and Sysprep execution.

### Execution:
1. Copy `scripts/optimize-and-seal-windows-vdi.ps1` and `scripts/unattend.xml` into the Windows VM.
2. Open PowerShell as **Administrator**.
3. Execute:
   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force
   .\optimize-and-seal-windows-vdi.ps1
   ```
4. When prompted, confirm execution. The script optimizes the system, stages `unattend.xml`, executes Sysprep, and powers off the VM.

---

## 17. Pre-Template Validation

Execute on the Proxmox host shell before converting to template:

```bash
# 1. Verify VM is fully shut down (status: stopped)
qm status 9100

# 2. Detach Windows Installer ISO and VirtIO Driver ISO
# (Clones should not have setup ISOs mounted)
qm set 9100 --delete ide0
qm set 9100 --delete ide2

# 3. Set Boot Order to boot directly from SCSI 0
qm set 9100 --boot order=scsi0

# 4. Review clean configuration
qm config 9100
```

---

## 18. Backup and Rollback

Create a standalone, compressed backup of the sealed build VM prior to template conversion:

```bash
# Backup sealed build VM to backup storage
vzdump 9100 \
    --mode stop \
    --compress zstd \
    --storage local \
    --notes-template "Windows 11 VDI Golden Master - Sealed $(date +'%Y-%m-%d')"
```

---

## 19. Convert to a Proxmox Template

Execute on the Proxmox host shell:

```bash
# Convert VM 9100 to an immutable template
qm template 9100
```

Once converted:
- The VM icon in the Proxmox Web GUI changes to a template icon.
- The virtual disks become read-only base disks.
- The template can now be cloned instantaneously.

---

## 20. Create VDI Clones

### 20.1 Linked Clones (Fast Provisioning, Minimal Storage)
Linked clones reference the template's base disk read-only and write differences to a small delta layer:

```bash
# Create Linked Clone (VM 9101)
qm clone 9100 9101 \
    --name win11-vdi-clone-01 \
    --full 0 \
    --pool VDI-Pool

# Create Linked Clone (VM 9102)
qm clone 9100 9102 \
    --name win11-vdi-clone-02 \
    --full 0 \
    --pool VDI-Pool

# Start Clones
qm start 9101
qm start 9102
```

### 20.2 Full Clones (Independent Storage)
For persistent power-user workstations requiring complete independence:

```bash
qm clone 9100 9110 \
    --name win11-vdi-dev-01 \
    --full 1 \
    --storage local-lvm
```

---

## 21. First-Boot Validation

During the first boot of each clone:
1. Windows runs the Sysprep `specialize` pass.
2. Machine SIDs and computer names are regenerated.
3. Plug-and-Play keeps VirtIO drivers intact.
4. `oobeSystem` suppresses interactive setup screens.
5. FirstLogonCommands ensure QEMU Guest Agent is running and sets the network profile.
6. The machine reaches the Windows desktop / login screen with RDP active.

---

## 22. Multi-Clone Uniqueness Test

Run the verification script `scripts/verify-windows-clone-uniqueness.sh` on the Proxmox host to compare two clones:

```bash
./scripts/verify-windows-clone-uniqueness.sh 9101 9102
```

### Verification Matrix:
- **QEMU Guest Agent**: Both VMs respond to `qm guest ping`.
- **Hostname (`COMPUTERNAME`)**: Must be distinct (e.g. auto-randomized or assigned).
- **Machine SID**: Must be completely unique.
- **Hardware MAC Address**: Distinct MACs on `net0`.
- **IPv4 Address**: Distinct IP addresses from DHCP.
- **RDP Listener**: Port 3389 listening and operational.

---

## 23. Template Maintenance & Patching Lifecycle

To update the golden image (e.g. monthly Patch Tuesday updates):

1. **Deploy Maintenance VM from Template**:
   ```bash
   qm clone 9100 9199 --name win11-vdi-maintenance --full 1
   qm start 9199
   ```
2. **Apply Updates**:
   - Install Windows Cumulative Updates.
   - Update VirtIO guest tools or application software.
3. **Re-Run Sealing**:
   - Execute `optimize-and-seal-windows-vdi.ps1`.
   - The VM runs Sysprep and powers off.
4. **Convert to New Template Version**:
   ```bash
   qm template 9199
   # Rename to win11-vdi-gold-v2026.2
   qm set 9199 --name win11-vdi-gold-v2026.2
   ```

---

## 24. Proxmox Automation Scripts

This repository includes turnkey automation scripts under [`scripts/`](file:///home/nishusaini/Desktop/Innspark/vdi-development/scripts):

1. [`create-windows-vdi-build-vm.sh`](file:///home/nishusaini/Desktop/Innspark/vdi-development/scripts/create-windows-vdi-build-vm.sh):
   - Proxmox host script to provision the build VM with q35, OVMF, vTPM 2.0, VirtIO SCSI, and network.
2. [`unattend.xml`](file:///home/nishusaini/Desktop/Innspark/vdi-development/scripts/unattend.xml):
   - Battle-tested Sysprep answer file preserving VirtIO drivers, suppressing OOBE, and randomizing hostnames.
3. [`optimize-and-seal-windows-vdi.ps1`](file:///home/nishusaini/Desktop/Innspark/vdi-development/scripts/optimize-and-seal-windows-vdi.ps1):
   - Windows PowerShell guest script performing VDI performance tuning, bloatware cleanup, and Sysprep sealing.
4. [`verify-windows-clone-uniqueness.sh`](file:///home/nishusaini/Desktop/Innspark/vdi-development/scripts/verify-windows-clone-uniqueness.sh):
   - Host script validating SID, Hostname, MAC, IP, and QEMU agent across clones.

---

## 25. Troubleshooting Guide

### 25.1 VirtIO SCSI Disk Not Detected in Windows Setup
- **Cause**: Windows Setup does not contain open-source VirtIO SCSI drivers.
- **Solution**: Click **Load driver** -> browse to mounted VirtIO ISO -> `vioscsi\w11\amd64` (or `w10\amd64`) -> select **Red Hat VirtIO SCSI controller**.

### 25.2 Sysprep Fails with Error 0x80073cf2
- **Cause**: Windows Store updated a modern AppX package in the background for the current user.
- **Diagnostic Log**: Inspect `C:\Windows\System32\Sysprep\Panther\setupact.log`.
- **Solution**: Run `optimize-and-seal-windows-vdi.ps1`, which removes per-user provisioned bloatware and stops `AppXSvc` prior to Sysprep.

### 25.3 Cloned VM Fails with `INACCESSIBLE_BOOT_DEVICE` (BSOD)
- **Cause**: Sysprep was run without `<PersistAllDeviceInstalls>true</PersistAllDeviceInstalls>`, causing Windows to uninstall the VirtIO SCSI storage driver.
- **Solution**: Ensure `unattend.xml` contains the `Microsoft-Windows-PnpSysprep` component with `PersistAllDeviceInstalls` set to `true`.

### 25.4 QEMU Guest Agent Shows Offline in Proxmox UI
- **Cause**: QEMU Guest Agent service is stopped or VirtIO serial driver is missing.
- **Solution**: Run `virtio-win-guest-tools.exe` to reinstall the serial driver and set service `qemu-ga` to Automatic.

### 25.5 Black Screen upon RDP Connection
- **Cause**: Display driver conflict between QXL and RDP display virtualization.
- **Solution**: Install the Red Hat QXL DOD driver (`qxldod`) from the VirtIO ISO, or set Group Policy `Use WDDM graphics display driver for Remote Desktop Connections` to `Enabled`.

---

## 26. Final Acceptance Checklist

- [ ] VM created with `q35`, `OVMF (UEFI)`, `vTPM 2.0`, and `VirtIO-SCSI-Single`.
- [ ] Disk configured with `discard=on` (TRIM) and `ssd=1`.
- [ ] Windows installed and activated (or KMS configured).
- [ ] VirtIO Guest Tools installed (SCSI, NetKVM, Balloon, QEMU-GA).
- [ ] `qemu-ga` service is running and verified via `qm guest ping <VMID>`.
- [ ] Remote Desktop (RDP) enabled with Network Level Authentication (NLA).
- [ ] Hibernation disabled (`powercfg /h off`) and `hiberfil.sys` removed.
- [ ] SysMain and Windows Search indexer disabled.
- [ ] Visual effects tuned with Font Smoothing (ClearType) enabled.
- [ ] Temporary files, Windows Update cache, and event logs purged.
- [ ] `unattend.xml` staged with `PersistAllDeviceInstalls=true`.
- [ ] Sysprep executed successfully with `/generalize /oobe /shutdown`.
- [ ] Installation ISOs detached from the VM.
- [ ] Backup created with `vzdump`.
- [ ] VM converted to template via `qm template`.
- [ ] Test linked clones deployed and verified using `verify-windows-clone-uniqueness.sh`.
- [ ] All SIDs, hostnames, and IP addresses confirmed 100% unique.
