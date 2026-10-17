# Proxmox VE Enterprise NFS Storage Implementation & Operations Guide
## 10-Disk Storage Pool Provisioning, Server Setup, Cluster Mount, 10G Tuning & Disaster Recovery

- **Document Version**: `1.1-Production`
- **Target Environment**: Proxmox VE 8.x / 9.x Cluster (`cisai-pve`)
- **Storage Subsystem**: 10-Disk Dedicated Enterprise SAS/SATA/NVMe Array
- **Dedicated Storage Fabric**: 10G/25G SFP28 Optical (`192.168.10.0/24`, MTU 9000)
- **Supported PVE Content Types**: `backup`, `iso`, `vztmpl`, `images`, `snippets`

---

## 1. Overview & Architectural Role of NFS in Proxmox VE

While block storage backends like **Ceph RBD** and local **ZFS RAIDZ2** are designed for high-performance active virtual machine disk I/O, **Network File System (NFS)** provides a standardized, shared, file-level storage repository across all nodes in the cluster:

1. **Centralized Backups (VZDump)**:
   - All 3 to 5 nodes stream automated snapshot backups (`.vma.zst`) to a single centralized NFS target.
   - Centralized prune and retention policies (`keep-last=3, keep-daily=7, keep-weekly=4, keep-monthly=12`).
2. **Shared ISO Images & Container Templates**:
   - Download operating system ISOs once; instantly boot VMs on any cluster node without manual copying.
   - Shared repository for LXC container templates (`*.tar.zst`).
3. **Shared VM Disk Images & Live Migration**:
   - Stores VM virtual disk images (`qcow2`, `raw`).
   - Enables instant zero-copy live migration between nodes without SAN or Ceph overhead.
4. **Cloud-Init Snippets & Hooks**:
   - Stores shared `user-data` YAML files for automated cloud-init provisioning.

---

## 2. Supported PVE Content Types on NFS

Proxmox automatically organizes the NFS directory structure into standardized subdirectories:

| Content Flag | Directory on NFS Export | File Format | Use Case |
| :--- | :--- | :--- | :--- |
| `backup` | `<export>/dump/` | `vzdump-qemu-*.vma.zst` | Scheduled VZDump virtual machine and container backups |
| `iso` | `<export>/template/iso/` | `*.iso` | OS installation images |
| `vztmpl` | `<export>/template/cache/` | `*.tar.zst` | Downloaded container templates |
| `images` | `<export>/images/<VMID>/` | `vm-<VMID>-disk-*.qcow2` | Virtual machine disks |
| `rootdir` | `<export>/subvol/<CTID>/` | Raw subvolumes | Container root filesystems |
| `snippets` | `<export>/snippets/` | `*.yaml, *.sh` | Cloud-init configuration files and hook scripts |

---

## 3. Network Fabric & 10G Subnet Routing

To achieve line-rate backup transfer speeds (**> 600 MB/s**) and prevent network congestion on Corosync heartbeats:
- **Corosync & Management**: `vmbr0` (`10.31.6.0/22`, MTU 1500)
- **NFS Storage & Ceph**: `nic3` (`192.168.10.0/24`, **MTU 9000 Jumbo Frames**)

> [!CRITICAL]
> Always mount NFS using the server's **`192.168.10.x`** IP address to route traffic across the 10G optical fabric.

---

## 4. Phase 1: 10-Disk Storage Pool Architecture & Provisioning

Before configuring the NFS server daemon, the 10 raw disks must be aggregated into a resilient, high-throughput storage volume.

### 4.1. Selecting the Optimal Storage Topology for 10 Disks

| Topology | Usable Capacity (e.g. 10x 2TB drives) | Fault Tolerance | Read/Write Profile | Recommended Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **ZFS RAIDZ2 (Single 10-disk vdev)** | **~80%** (8 Data + 2 Parity) ~16 TB | Survives **any 2 disk failures** | High sequential throughput; moderate random IOPS | **Recommended for Proxmox Backups, ISOs & Templates** |
| **ZFS Striped Mirrors (RAID 10: 5x 2-disk mirrors)** | **50%** (5 Data + 5 Mirror) ~10 TB | Survives **1 disk per pair** (up to 5 disks) | Extreme random read/write IOPS; fastest resilver times | **Recommended for active VM disk images (`qcow2`)** |
| **ZFS Dual RAIDZ2 (2x 5-disk vdevs)** | **60%** (6 Data + 4 Parity) ~12 TB | Survives **2 disks per vdev** (up to 4 disks) | Balanced random IOPS and sequential bandwidth | Mixed workload (active VMs + backups) |
| **Linux Software RAID 6 (`mdadm` + XFS)** | **~80%** (8 Data + 2 Parity) ~16 TB | Survives **any 2 disk failures** | High sequential throughput; standard POSIX filesystem | Non-ZFS Linux distribution or minimal RAM environments |

---

### 4.2. Disk Discovery & Identification

Identify all 10 target disks and reference them by their persistent WWN / serial ID:

```bash
# List block devices
lsblk -o NAME,SIZE,TYPE,FSTYPE,MODEL,SERIAL

# Find unique persistent disk IDs
ls -la /dev/disk/by-id/
```

> [!IMPORTANT]
> Never use standard device letters like `/dev/sdb` or `/dev/sdc` for pool creation, because disk letter assignments can shift upon reboot or bus re-enumeration. Always use `/dev/disk/by-id/...`.

---

### 4.3. Creating the Storage Pool

#### Option A: ZFS RAIDZ2 (10 Disks — Recommended for Backups)
```bash
zpool create -f -o ashift=12 -O acltype=posixacl -O xattr=sa -O normalization=formD nfs-pool raidz2 \
  /dev/disk/by-id/nvme-drive1 \
  /dev/disk/by-id/nvme-drive2 \
  /dev/disk/by-id/nvme-drive3 \
  /dev/disk/by-id/nvme-drive4 \
  /dev/disk/by-id/nvme-drive5 \
  /dev/disk/by-id/nvme-drive6 \
  /dev/disk/by-id/nvme-drive7 \
  /dev/disk/by-id/nvme-drive8 \
  /dev/disk/by-id/nvme-drive9 \
  /dev/disk/by-id/nvme-drive10
```

#### Option B: ZFS Striped Mirrors (RAID 10 — Recommended for VM Disks)
```bash
zpool create -f -o ashift=12 -O acltype=posixacl -O xattr=sa -O normalization=formD nfs-pool \
  mirror /dev/disk/by-id/drive1 /dev/disk/by-id/drive2 \
  mirror /dev/disk/by-id/drive3 /dev/disk/by-id/drive4 \
  mirror /dev/disk/by-id/drive5 /dev/disk/by-id/drive6 \
  mirror /dev/disk/by-id/drive7 /dev/disk/by-id/drive8 \
  mirror /dev/disk/by-id/drive9 /dev/disk/by-id/drive10
```

#### Option C: Linux `mdadm` RAID 6 + XFS
```bash
# 1. Create RAID 6 array
mdadm --create --verbose /dev/md0 --level=6 --raid-devices=10 \
  /dev/disk/by-id/drive1 /dev/disk/by-id/drive2 /dev/disk/by-id/drive3 \
  /dev/disk/by-id/drive4 /dev/disk/by-id/drive5 /dev/disk/by-id/drive6 \
  /dev/disk/by-id/drive7 /dev/disk/by-id/drive8 /dev/disk/by-id/drive9 \
  /dev/disk/by-id/drive10

# 2. Save layout to configuration
mdadm --detail --scan >> /etc/mdadm/mdadm.conf
update-initramfs -u

# 3. Format with XFS and mount
mkfs.xfs -K /dev/md0
mkdir -p /mnt/nfs_storage
echo "/dev/md0 /mnt/nfs_storage xfs defaults,noatime 0 0" >> /etc/fstab
mount -a
```

---

### 4.4. ZFS Dataset Creation & Recordsize Tuning

Create a dedicated dataset with compression and tailored record size:

```bash
# 1. Create dedicated dataset for PVE NFS share
zfs create -o compression=zstd -o atime=off nfs-pool/pve-storage

# 2. Optimize recordsize:
# For VZDump Backups and ISOs (large streaming files):
zfs set recordsize=1M nfs-pool/pve-storage

# (Alternative) If primarily hosting VM images (qcow2):
# zfs set recordsize=64k nfs-pool/pve-storage

# 3. Verify dataset properties
zfs get compression,recordsize,mountpoint nfs-pool/pve-storage
```

---

## 5. Phase 2: Deploying & Configuring the NFS Server

### 5.1. Install NFS Packages & Set Permissions
```bash
# Install kernel NFS server
apt update && apt install -y nfs-kernel-server rpcbind

# Prepare shared directory permissions
chown -R nobody:nogroup /nfs-pool/pve-storage
chmod 777 /nfs-pool/pve-storage
```

### 5.2. Configure NFS Daemon Threads for 10 Disks
A 10-disk array can easily bottleneck if restricted to the default 8 NFS server threads. Increase worker threads to **32 or 64**:
Edit `/etc/nfs.conf`:
```ini
[nfsd]
threads=32
```
Restart the service to apply:
```bash
systemctl restart nfs-kernel-server
```

### 5.3. Configure `/etc/exports`
Add the export rule to `/etc/exports` restricting access to the 10G storage fabric:
```text
/nfs-pool/pve-storage 192.168.10.0/24(rw,sync,no_subtree_check,no_root_squash,no_all_squash,sec=sys)
```

Apply changes live:
```bash
exportfs -arv
systemctl enable --now nfs-kernel-server rpcbind
```

### Export Flags Breakdown:
- `rw`: Full read and write privileges for backup creation and template uploading.
- `sync`: Flushes data directly to disk before acknowledging I/O. Essential for backup data integrity.
- `no_subtree_check`: Eliminates pathname checking overhead; speeds up file operations and prevents errors during file renames.
- `no_root_squash`: **Mandatory for Proxmox VE.** Backups and VM creations run under root context. Without this flag, operations fail with `Permission Denied`.
- `sec=sys`: Standard UNIX UID/GID authentication over isolated private storage VLANs.

### 5.4. Firewall Rules (Ports 2049 & 111)
```bash
ufw allow from 192.168.10.0/24 to any port 2049 proto tcp
ufw allow from 192.168.10.0/24 to any port 111 proto tcp
ufw allow from 192.168.10.0/24 to any port 111 proto udp
```

---

## 6. Phase 3: Mounting NFS Storage in Proxmox VE

### 6.1. Verify Server Reachability from Proxmox Node
```bash
showmount -e 192.168.10.50
```

### 6.2. Method 1 — CLI Mounting via `pvesm` (Cluster Leader)
```bash
pvesm add nfs nfs-10disk-storage \
  --server 192.168.10.50 \
  --export /nfs-pool/pve-storage \
  --content backup,iso,vztmpl,images \
  --options "vers=4.2,tcp,nconnect=8,timeo=600,retrans=2" \
  --prune-backups "keep-last=3,keep-daily=7,keep-weekly=4,keep-monthly=12"
```

Verify cluster status:
```bash
pvesm status
```

### 6.3. Method 2 — Proxmox Web GUI
1. Navigate to: **Datacenter** -> **Storage** -> Click **Add** -> **NFS**.
2. **ID**: `nfs-10disk-storage`
3. **Server**: `192.168.10.50` (NFS 10G IP)
4. **Export**: Select `/nfs-pool/pve-storage` from dropdown.
5. **Content**: Select `VZDump backup file`, `ISO image`, `Container template`, `Disk image`.
6. **Nodes**: Select `All` (cluster-wide shared storage).
7. Click **Add**.

---

## 7. Phase 4: 10GbE High-Performance Tuning Parameters

Mount options inside `/etc/pve/storage.cfg`:

| Mount Option | Optimal Value | Performance Benefit |
| :--- | :--- | :--- |
| `vers=4.2` | NFSv4.2 | Supports Server-Side Copy (SSC) for instant VM cloning without data traversing the network |
| `nconnect=8` | 8 Parallel TCP Streams | Multiplexes RPC requests across 8 parallel sockets, saturating 10GbE fabric |
| `rsize=1048576` | 1 MB Buffer | Maximizes sequential read speeds during VM restore operations |
| `wsize=1048576` | 1 MB Buffer | Maximizes sequential write speeds during backup creation (**> 600 MB/s**) |
| `timeo=600` | 60s Timeout | Prevents false timeouts during heavy parallel backup commits |

---

## 8. Phase 5: Automated Scheduled Backups (VZDump) to NFS

### 8.1. Configure Nightly Backup Schedule
1. In PVE GUI: **Datacenter** -> **Backup** -> Click **Add**.
2. Schedule: `01:00` (Nightly).
3. Storage: `nfs-10disk-storage`.
4. Selection Mode: `All Guests`.
5. Mode: `Snapshot` (Zero downtime).
6. Compression: `Zstandard (zstd)`.
7. Prune: Keep last 3, Keep daily 7, Keep weekly 4, Keep monthly 12.

### 8.2. Manual CLI Backup Verification
```bash
vzdump 9001 --storage nfs-10disk-storage --mode snapshot --compress zstd
```

---

## 9. Phase 6: Maintenance & Troubleshooting Playbooks

### 9.1. 10-Disk Pool Maintenance & Disk Replacement
```bash
# Check pool health and error counts
zpool status nfs-pool

# Schedule monthly data integrity scrub
zpool scrub nfs-pool

# Replacing a failed disk in the 10-disk array:
# 1. Take failed disk offline
zpool offline nfs-pool /dev/disk/by-id/old-drive-serial
# 2. Physically replace drive
# 3. Rebuild (resilver) onto new disk
zpool replace nfs-pool /dev/disk/by-id/old-drive-serial /dev/disk/by-id/new-drive-serial
```

### 9.2. Playbook A: Storage Shows Question Mark `(?)` Icon
```bash
# 1. Test port 2049 connectivity
nc -zv 192.168.10.50 2049
# 2. Check exported shares
showmount -e 192.168.10.50
# 3. Refresh storage daemon state
pvesm set nfs-10disk-storage --disable 1 && sleep 2 && pvesm set nfs-10disk-storage --disable 0
pvesm status
```

### 9.3. Playbook B: Stale File Handle (`ESTALE`) Resolution
```bash
# 1. Detach stale mount via lazy unmount
umount -l /mnt/pve/nfs-10disk-storage
# 2. Refresh storage status
pvesm status
```

### 9.4. Playbook C: Preventing Node Boot Hangs on Unreachable NFS Server
```bash
pvesm set nfs-10disk-storage --options "vers=4.2,tcp,nconnect=8,timeo=600,retrans=2,_netdev,nofail,x-systemd.automount,x-systemd.idle-timeout=60"
```

### 9.5. Playbook D: Permission Denied (`EACCES` / `EPERM`)
1. Ensure `/etc/exports` contains `no_root_squash`.
2. Ensure directory permissions: `chmod 777 /nfs-pool/pve-storage`.
3. Re-export: `exportfs -arv`.

---

## 10. Administrator Daily Operational Cheat Sheet

| Task | Command | Expected Healthy Output |
| :--- | :--- | :--- |
| **Inspect 10-Disk ZFS Health** | `zpool status nfs-pool` | `state: ONLINE`, 0 read/write/cksum errors |
| **Inspect NFS Health on PVE** | `pvesm status -storage nfs-10disk-storage` | `Status: active` |
| **List Backups on NFS** | `pvesm list nfs-10disk-storage --content backup` | List of `.vma.zst` files |
| **List ISOs on NFS** | `pvesm list nfs-10disk-storage --content iso` | List of `.iso` files |
| **Check Active Mount Options** | `nfsstat -m /mnt/pve/nfs-10disk-storage` | Shows active `vers=4.2`, `nconnect=8` |
| **Test NFS Write Speed** | `dd if=/dev/zero of=/mnt/pve/nfs-10disk-storage/test.img bs=1M count=1000 oflag=direct` | `> 550 MB/s` |

---

## 11. Engineering Document Sign-Off

- **Document Author**: Infrastructure Engineering (Innspark / CISAI Infrastructure Team)
- **Architecture**: 10-Disk Enterprise Array + NFSv4.2 10GbE Multipath Shared Storage for Proxmox VE
- **Status**: Verified & Ready for Production
