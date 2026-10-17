# Proxmox VE Enterprise Cluster & Dual-Storage Implementation Handbook
## Complete Bare-Metal to 5-Node Scaled Production Deployment (Ceph + ZFS RAIDZ2 + HA)

- **Document Version**: `2.0-Enterprise`
- **Cluster Blueprint**: `3 to 5 Physical Nodes` (`cisai-pve`)
- **Primary Cluster Leader / CRM Master**: `prox22` (`10.31.6.172` / `192.168.10.22`)
- **Storage Subsystems**: Ceph 20-OSD Shared RBD (4 disks/node) + ZFS RAIDZ2 Local NVMe/SAS (7 disks/node)
- **High-Speed Interconnect**: 10G/25G SFP28 Optical (`192.168.10.0/24`, MTU 9000)

---

## 1. Executive Summary & 5-Node Architectural Blueprint

This handbook provides the authoritative, end-to-end engineering standard operating procedure (SOP) for deploying and scaling a high-performance, fault-tolerant virtualization infrastructure on Proxmox Virtual Environment (PVE 8.x / 9.x). The architecture concurrently leverages two complementary storage backends across Dell PowerEdge / AMD EPYC servers with 10G/25G optical fabrics:

1. **Ceph Distributed Storage (Shared Tier)**:
   - **4 Disks per Node** (12 OSDs in 3 nodes; 20 OSDs across 5 nodes = ~360 TB raw).
   - 3x distributed replication (`size: 3, min_size: 2`).
   - Zero-downtime cross-node QEMU live migration without shared SAN/NAS bottlenecks.
   - Self-healing placement group (PG) architecture with automatic rebalancing.
2. **ZFS RAIDZ2 Storage (Local Performance Tier)**:
   - **7 Disks per Node** configured in RAIDZ2 per physical server (~91 TB usable, 2-disk failure tolerance).
   - High-throughput direct block I/O (measured at **4.0 GB/s sequential read**, **768 MB/s write**).
   - Automated incremental cross-node snapshot replication via `pvesr` every 30 minutes for sub-30min RPO protection.
3. **High Availability & Self-Fencing**:
   - Hardware watchdog integration (IPMI / `softdog`).
   - Automated CRM master election on `prox22` with active LRMs across all nodes.
   - Sub-60s automated VM failover and zero-downtime live migration.

---

## 2. Hardware Bill of Materials (BOM) & Drive Mapping (Per Server)

Each server is provisioned identically with 12 enterprise SAS drives (Seagate Exos X20 18.2 TB / 20 TB nominal) and a dedicated hardware RAID1 boot pair:

| Slot / Device | Model / Hardware Specs | Interface / Bus | Assigned Subsystem | Redundancy / Allocation |
| :--- | :--- | :--- | :--- | :--- |
| **`sdm` (PERC H755)** | 2x 960GB Enterprise SATA SSD | Hardware RAID1 (BOSS/PERC) | Host OS / Proxmox VE | `ext4` root / 32GB Swap / ISO Storage |
| **`sda, sdb, sdc, sdd`** | 4x 18.2 TB Seagate Exos X20 SAS | 12Gb/s SAS Pass-through (HBA) | Ceph Distributed Pool | 4x Ceph OSDs (18.2 TB raw each; 3x Replica) |
| **`sde, sdf, sdg, sdh, sdi, sdj, sdk`** | 7x 18.2 TB Seagate Exos X20 SAS | 12Gb/s SAS Pass-through (HBA) | Local ZFS Pool (`zfs-ha`) | 7-Disk RAIDZ2 (~91 TB usable; 2 parity disks) |
| **`sdl`** | 1x 18.2 TB Seagate Exos X20 SAS | 12Gb/s SAS Pass-through (HBA) | Global Hot Spare | Available for immediate ZFS/Ceph replacement |

---

## 3. Network Architecture & 5-Node IP Allocation Scheme

Traffic isolation is strictly enforced between management heartbeats and bulk storage transfers:

| Node Name | Node ID | Management IP (`vmbr0` - 1G) | Ceph & Migration IP (`nic3` - 10G) | Corosync Link 0 | Corosync Link 1 | Role |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **`prox21`** | 1 | `10.31.6.171/22` | `192.168.10.21/24` | `192.168.10.21` (Pri 1) | `10.31.6.171` (Fallback) | Expansion Node |
| **`prox22`** | 2 | `10.31.6.172/22` | `192.168.10.22/24` | `192.168.10.22` (Pri 1) | `10.31.6.172` (Fallback) | Cluster Leader / CRM Master |
| **`prox23`** | 3 | `10.31.6.173/22` | `192.168.10.23/24` | `192.168.10.23` (Pri 1) | `10.31.6.173` (Fallback) | Member Node / Ceph Mon |
| **`prox24`** | 4 | `10.31.6.174/22` | `192.168.10.24/24` | `192.168.10.24` (Pri 1) | `10.31.6.174` (Fallback) | Member Node / Ceph Mon |
| **`prox25`** | 5 | `10.31.6.175/22` | `192.168.10.25/24` | `192.168.10.25` (Pri 1) | `10.31.6.175` (Fallback) | Expansion Node |

---

## 4. Phase 1: Bare-Metal Proxmox VE Installation & Hardening

### Step 1.1: BIOS/UEFI & PERC Controller Preparation
1. **Boot Mode**: System BIOS -> `UEFI Mode`. Disable CSM / Legacy boot.
2. **Virtualization**: Enable `AMD-V`, `AMD-Vi (IOMMU)`, and `SR-IOV Global Enable`.
3. **Storage Controller (PERC H755/H740P)**:
   - Configure drives `sda` through `sdl` in **HBA / Enhanced Pass-through Mode**.
   - Create a 2-disk Hardware RAID1 Virtual Disk on the M.2/SATA SSDs for the Proxmox OS (`/dev/sdm`).

> **CRITICAL**: Never create individual RAID0 volumes for ZFS or Ceph. Disk cache write barriers must be handled natively by ZFS/Ceph drivers.

### Step 1.2: Proxmox VE Operating System Installation
1. Boot from the Proxmox VE 8/9 ISO via iDRAC Virtual Media.
2. Target Harddisk: Choose `/dev/sdm` (RAID1 OS SSD). Filesystem: `ext4`.
3. Set Timezone to `Asia/Kolkata` and assign management parameters:
   - Interface: `eno1` (1GbE RJ45)
   - Hostname: `prox22.cisai.local`
   - IP Address: `10.31.6.172/22`, Gateway: `10.31.4.1`, DNS: `10.31.6.1`
4. Complete installation and reboot.

### Step 1.3: Network Interfaces Configuration (`/etc/network/interfaces`)
Edit `/etc/network/interfaces` on each node:

```bash
auto lo
iface lo inet loopback

iface eno1 inet manual

auto vmbr0
iface vmbr0 inet static
	address 10.31.6.172/22
	gateway 10.31.4.1
	bridge-ports eno1
	bridge-stp off
	bridge-fd 0

# 10G Optical Interconnect for Ceph & Corosync High-Speed Fabric
auto nic3
iface nic3 inet static
	address 192.168.10.22/24
	mtu 9000
```
Apply networking live:
```bash
ifreload -a && ip a show nic3
```

### Step 1.4: Base System Packages & Chrony NTP
```bash
# 1. Enable pve-no-subscription repository
rm -f /etc/apt/sources.list.d/pve-enterprise.list
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-no-sub.list
apt update && apt install -y chrony ifupdown2 ethtool sysstat iotop jq

# 2. Configure Chrony for ultra-low latency inter-node time sync
echo "server 10.31.6.1 iburst" >> /etc/chrony/chrony.conf
systemctl restart chronyd && chronyc tracking
```

---

## 5. Phase 2: Cluster Initialization & Multi-Node Join

### Step 2.1: Initialize Cluster on Leader Node (`prox22`)
```bash
pvecm create cisai-pve --link0 192.168.10.22 --link1 10.31.6.172
pvecm status
```

### Step 2.2: Join Additional Nodes
From each joining node, execute the join command pointing to `prox22`:
```bash
# On prox23:
prox23# pvecm add 192.168.10.22 --link0 192.168.10.23 --link1 10.31.6.173

# On prox24:
prox24# pvecm add 192.168.10.22 --link0 192.168.10.24 --link1 10.31.6.174

# For 5-Node Expansion (prox21 & prox25):
prox21# pvecm add 192.168.10.22 --link0 192.168.10.21 --link1 10.31.6.171
prox25# pvecm add 192.168.10.22 --link0 192.168.10.25 --link1 10.31.6.175
```

### Step 2.3: Verify Quorum and Corosync Link Status
```bash
pvecm status
corosync-cfgtool -s
```
- **3-Node Cluster**: Total votes: 3, Quorum: 2 (tolerates 1 node loss).
- **5-Node Cluster**: Total votes: 5, Quorum: 3 (tolerates 2 simultaneous node losses).

---

## 6. Phase 3: Ceph Distributed Storage Implementation

### Step 3.1: Install Ceph Packages & Initialize Cluster
```bash
pveceph install --version squid
pveceph init --network 192.168.10.0/24 --cluster-network 192.168.10.0/24
```

### Step 3.2: Provision Ceph Monitors & Managers
```bash
pveceph mon create --mon-address 192.168.10.22
pveceph mon create --mon-address 192.168.10.23
pveceph mon create --mon-address 192.168.10.24
pveceph mgr create
```

### Step 3.3: Disk Discovery & OSD Creation (4 Disks/Node)
On each node, prepare and create OSDs on the 4 dedicated SAS drives (`sda` - `sdd`):
```bash
# Zap existing partition signatures
for d in /dev/sda /dev/sdb /dev/sdc /dev/sdd; do
  wipefs -a $d
  sgdisk --zap-all $d
done

# Create 4 Ceph OSDs
pveceph osd create /dev/sda
pveceph osd create /dev/sdb
pveceph osd create /dev/sdc
pveceph osd create /dev/sdd
```

### Step 3.4: Configure Pool & CRUSH Rules
```bash
# Create shared pool with 3x replication
pveceph pool create ceph --size 3 --min_size 2 --pg_num 32 --application rbd
ceph osd pool set ceph pg_autoscale_mode on
ceph -s
```

---

## 7. Phase 4: ZFS RAIDZ2 Storage Implementation (7 Disks/Node)

### Step 4.1: Identify 7 Dedicated SAS Disks
```bash
ls -l /dev/disk/by-id/ | grep -E 'sd[e-k]$'
```

### Step 4.2: Create Enterprise ZFS RAIDZ2 Pool (`zfs-ha`)
Run on each physical node:
```bash
zpool create -f -o ashift=12 \
  -O compression=zstd \
  -O atime=off \
  -O xattr=sa \
  -O normalization=formD \
  -O acltype=posixacl \
  zfs-ha raidz2 /dev/sde /dev/sdf /dev/sdg /dev/sdh /dev/sdi /dev/sdj /dev/sdk
```

### Step 4.3: Tune ZFS ARC Memory Cache
Prevent ZFS ARC cache from exhausting RAM on virtual machine compute hosts:
```bash
cat << 'EOF' > /etc/modprobe.d/zfs.conf
options zfs zfs_arc_max=34359738368
options zfs zfs_arc_min=8589934592
EOF
update-initramfs -u
```

### Step 4.4: Storage Registration & Automated Cross-Node Replication (`pvesr`)
```bash
# 1. Register pool in PVE cluster storage
pvesm add zfspool zfs-ha --pool zfs-ha --content images,rootdir --sparse 1

# 2. Schedule incremental snapshot replication every 30 mins
pvesr create-job 9002-0 local/prox22 --schedule "*/30" --type local
pvesr status
```

---

## 8. Phase 5: High Availability (HA) & VM Live Migration

### Step 5.1: Arm Hardware Watchdog Self-Fencing
```bash
modprobe softdog
echo "softdog" >> /etc/modules
systemctl restart pve-ha-crm pve-ha-lrm
ha-manager status
```

### Step 5.2: Configure HA Priority Groups
```bash
ha-manager groupadd prod-group --nodes "prox22:100,prox23:80,prox24:60,prox21:40,prox25:20" --nofailback 1
ha-manager add vm:9001 --group prod-group --max_restart 2 --max_relocate 2
```

### Step 5.3: Verify Zero-Downtime Live Migration
```bash
ha-manager migrate vm:9001 prox23
journalctl -u pve-ha-crm -n 15 --no-pager
```

---

## 9. Phase 6: Expanding from 3 to 5 Nodes Blueprint

Follow this phased checklist to expand the live cluster without workload interruption:
1. **Host Setup**: Install base PVE OS on `prox21` and `prox25`. Configure `vmbr0` (`10.31.6.171`/`175`) and `nic3` (`192.168.10.21`/`25`).
2. **Corosync Expansion**: Join nodes using `pvecm add 192.168.10.22 --link0 ... --link1 ...`. Quorum increases from 2 to 3.
3. **Ceph Expansion**:
   - `pveceph install --version squid` on nodes 4 and 5.
   - Create 4 OSDs per new node (`sda` through `sdd`).
   - Ceph seamlessly integrates the 8 new drives (12 -> 20 OSDs total) and rebalances PGs automatically.
4. **ZFS Provisioning**: Create `zfs-ha` RAIDZ2 pool on new nodes using `sde` through `sdk`.
5. **Update HA Groups**: Re-weight HA group priorities across all 5 nodes.

---

## 10. Phase 7: Real-World Troubleshooting & Disaster Recovery

### Playbook A: Ceph OSD Failure & Drive Replacement
```bash
# 1. Identify failed OSD (e.g. OSD.3)
ceph osd find 3
# 2. Stop and purge failed OSD
systemctl stop ceph-osd@3
pveceph osd destroy 3 --cleanup 1
# 3. Physically replace the SAS disk
# 4. Create new OSD on replacement disk
pveceph osd create /dev/sdb
ceph -s  # Monitor recovery until HEALTH_OK
```

### Playbook B: Corosync Quorum Loss / Split-Brain Recovery
```bash
# If nodes lose quorum and cluster locks into read-only mode:
pvecm expected 1
# Perform emergency repairs, then restore expected votes:
pvecm expected 5
```

### Playbook C: ZFS Degraded Drive Replacement
```bash
# 1. Check drive errors
zpool status zfs-ha
# 2. Offline the failed drive
zpool offline zfs-ha /dev/sdg
# 3. Swap drive and trigger resilver with new persistent WWN
zpool replace zfs-ha /dev/sdg /dev/disk/by-id/scsi-35000c500b...
zpool status zfs-ha
```

### Playbook D: ZFS Replication (`pvesr`) Lock Errors
```bash
qm unlock <VMID>
pvesr run --id <JOBID> -v
pvesr status
```

### Playbook E: 10G Jumbo Frames / MTU Validation
```bash
# Test 9000 MTU without fragmentation (-M do)
ping -M do -s 8972 -c 5 192.168.10.23

# Inspect optical transceiver DDM power levels
ethtool -m nic3 | grep -E 'Receiver signal average optical power|Tx power'
```

---

## 11. Phase 8: Daily Operations & Verification Cheat Sheet

| Subsystem | Command | Expected Output | Remediation Action |
| :--- | :--- | :--- | :--- |
| **Corosync Quorum** | `pvecm status` | `Quorate: Yes`, 3/5 votes | `corosync-cfgtool -s` |
| **Ceph Health** | `ceph -s` | `HEALTH_OK`, all OSDs UP & IN | `ceph health detail` |
| **ZFS RAIDZ2** | `zpool status zfs-ha` | `state: ONLINE`, 0 errors | `zpool scrub zfs-ha` |
| **HA CRM Master** | `ha-manager status` | `master prox22 (active)` | `journalctl -u pve-ha-crm` |
| **ZFS Replication** | `pvesr status` | `State: OK`, `FailCount: 0` | `pvesr run --id <JOBID> -v` |
| **Automated Tests** | `python3 run_tests.py --all` | `ALL TESTS PASSED` | Review `reports/` logs |

---

## 12. Document Sign-Off

- **Prepared By**: Infrastructure Engineering (Innspark / CISAI Cluster Team)
- **Architecture**: 5-Node Scaled Topology • Ceph 20-OSD + ZFS RAIDZ2 Dual-Storage
- **Certified Operating Systems**: Proxmox Virtual Environment 8.x / 9.x
- **Date**: September 18, 2026
