# Proxmox VE + Ceph + ZFS High Availability Testing Runbook
## Comprehensive Analysis & Step-by-Step "How-To" Test Scenarios Guide

This document provides an in-depth analysis of the test parameters defined in [`Manual Test Case proxmox.xlsx`](file:///home/nishusaini/Desktop/Innspark/Proxmox%20Cluster/Proxmox%20cluster%20testing%20/Manual%20Test%20Case%20proxmox.xlsx) along with a step-by-step technical **How-To Execution Runbook** for validating a 3-node enterprise Proxmox VE cluster backed by Ceph distributed storage and ZFS storage pools.

---

## Part 1: Analysis of the Excel Test Workbook

### 1. Structure of the Excel File
The workbook contains two primary test sheets:
- **`Manual Test Case Template`**: Initial baseline test execution tracking sheet (Steps 1–30, covering basic disk removals, slot swapping, node power-offs, and network disconnects).
- **`Ceph Cluster 2.0`**: Comprehensive expanded test matrix (Steps 1–55, covering 19 distinct test conditions across Ceph OSDs, ZFS OS mirrors, network interfaces, Corosync quorum, monitor failure recovery, and storage benchmarking).

### 2. Overview of All 19 Test Conditions

| Condition ID | Category | Test Condition Title | Excel Steps | Severity / Risk |
|---|---|---|---|---|
| **TC-01** | Ceph Storage | Remove 1 Disk from 1 Server | Steps 1 – 3 | Low (Self-Healing) |
| **TC-02** | Ceph Storage | Remove 2 Disks from 1 Server | Steps 4 – 6 | Low-Medium (Protected by 3x Replica) |
| **TC-03** | Ceph Storage | Remove 3 Disks from 1 Server | Steps 7 – 9 | Medium (Degraded PGs) |
| **TC-04** | Hardware / Controller | Disk Slot Swap: Slot 1 to Slot 3 | Steps 10 – 12 | Low-Medium (Controller Dependent) |
| **TC-05** | Ceph Storage | Remove All Disks from a Single Node | Steps 13 – 15 | High (All Node OSDs Down) |
| **TC-06** | Ceph Storage | Cross-Node Multi-Disk Failure (2 Disks across 2 Servers) | Steps 16 – 18 | High (Risk if min_size breached) |
| **TC-07** | Ceph Storage | Live Hot-Removal of Disks | Steps 19 – 21 | Medium (SCSI disconnect under load) |
| **TC-08** | Proxmox HA | Simulate Single Node Failure (Power Off 1 Node) | Steps 22 – 24 | Medium (Quorum retained 2/3, HA Failover) |
| **TC-09** | Proxmox HA | Simulate Dual Node Failure (Power Off 2 Nodes) | Steps 25 – 27 | Critical (Quorum Lost 1/3, Safe VM Freeze) |
| **TC-10** | Networking | Network Failure: Disconnect Single Interface / Cable | Steps 28 – 30 | Low (Bonding Failover) |
| **TC-11** | Networking | Network Failure: Disconnect Both Interfaces / Total Isolation | Steps 31 – 33 | High (Node Fencing via Watchdog) |
| **TC-12** | ZFS Storage | Simulate Software Disk Failure on ZFS Root Pool (`rpool`) | Steps 35 – 37 | Low (ZFS Offline / Resilver) |
| **TC-13** | ZFS Storage | Simulate Physical Disk Failure on ZFS Boot Mirror (SSD Pull) | Steps 38 – 40 | Medium (Degraded Boot Mirror) |
| **TC-14** | ZFS Storage | Replace a Failed Disk with a New One (`zpool replace`) | Steps 41 – 43 | Low-Medium (Disk Partitioning & Resilver) |
| **TC-15** | Virtualization / HA | Disk Removal During Active VM Live Migration | Steps 41 – 43 (b) | High (QEMU Migration Abort/Protection) |
| **TC-16** | Ceph Storage | Multiple OSD Failures Exceeding Replication Factor | Steps 44 – 46 | Critical (Disaster Scenario: PGs Down) |
| **TC-17** | Ceph Control Plane | Ceph Monitor Failure & Corrupted DB Recreation | Steps 47 – 49 | High (Monmap Extraction & Mon Rebuild) |
| **TC-18** | Ceph Performance | CRUSH Map Rebalance & Benchmarking Under Load | Steps 50 – 52 | Low-Medium (I/O Throttle Validation) |
| **TC-19** | Ceph Control Plane | Ceph Single-Monitor SPOF Failure & Cluster Freeze | Steps 52 – 55 (b) | Critical (Control Plane Lockout) |

---

### 3. Key Observations & Lessons Learned from Excel Results

1. **The Disk Slot Swapping Anomaly (TC-04 / Steps 10–12)**:
   - *Excel Note:* *"After inserting the disk into slot three, the system did not recognize it... Due to the RAID we think that it is not configured."*
   - *Technical Cause:* When using hardware RAID cards (e.g., MegaRAID/PERC) configured in RAID 0 or Virtual Drive mode rather than an HBA in IT-Mode (Initiator Target), changing the physical backplane slot changes the Enclosure/Slot ID. The controller flags the drive as "Foreign" or "Missing" until foreign configurations are cleared or imported. Under pure IT-Mode HBAs, Linux identifies drives by WWN (`/dev/disk/by-id/`), allowing slot mobility without issue.
2. **The CRUSH Rebalance Benchmarking Note (TC-18 / Steps 93–94)**:
   - *Excel Note:* *"Fail - Benchmark results during rebalance: Average IOPS: 40, Average Latency: 0.389s."*
   - *Technical Explanation:* The tester expected IOPS to drop drastically or latency to spike during a rebalance. Because modern Ceph (Reef) employs adaptive recovery throttling (`osd_max_backfills = 1`, `osd_recovery_sleep = 0`), client I/O was prioritized over background PG peering. The benchmark holding steady at ~40 IOPS is actually an indicator of storage stability, not a malfunction.
3. **Quorum Protection vs Split-Brain (TC-09 / Steps 25–27)**:
   - Proxmox cluster membership follows Corosync majority rules: `votes > (total_nodes / 2)`. In a 3-node cluster, loss of 2 nodes leaves 1 vote (out of 3), which drops quorum. The cluster immediately mounts `/etc/pve` read-only and Proxmox HA halts VMs. This ensures that surviving isolated nodes cannot write to shared storage, preventing data corruption.

---

## Part 2: Step-by-Step "How-To" Test Scenarios Runbook

### Lab Cluster Baseline Specifications
- **Cluster Name:** `cisai-pve`
- **Node 1:** `prox22` (Management: `10.31.6.172`, Cluster/Ceph: `192.168.10.22`, NodeID: 2)
- **Node 2:** `prox23` (Management: `10.31.6.173`, Cluster/Ceph: `192.168.10.23`, NodeID: 3)
- **Node 3:** `prox24` (Management: `10.31.6.174`, Cluster/Ceph: `192.168.10.24`, NodeID: 1)
- **Ceph Topology:** 12 OSDs (4 per node: e.g., `osd.0`–`osd.3` on prox22, `osd.4`–`osd.7` on prox23, `osd.8`–`osd.11` on prox24), 3 Monitors, 3 Managers. Pool size = 3, min_size = 2.
- **ZFS Topology:** Boot pool `rpool` (mirrored SSDs), Data pool `zfs-ha` (RAIDZ2).

---

### Scenario TC-01: Remove 1 Disk from 1 Server (Single OSD Failure)

#### Objective
Verify that losing a single Ceph OSD drive causes zero downtime for client VMs and triggers automatic degradation and recovery alerts.

#### Pre-requisites
1. Verify cluster health: `ceph status` reports `HEALTH_OK`.
2. Verify all 12 OSDs are `up` and `in`: `ceph osd tree`.
3. Verify test VM (e.g., VM 9001) is running with continuous ping and write activity.

#### Step-by-Step Execution
1. **Identify the target OSD:**
   ```bash
   # On prox22 (or any node)
   ceph osd tree
   ```
   Select an OSD (e.g., `osd.0` on `prox22`, mapped to physical drive `/dev/sdb`).
2. **Simulate the drive removal:**
   - *Physical removal:* Unlatch and pull the drive caddy for `/dev/sdb`.
   - *Software emulation (if remote):*
     ```bash
     systemctl stop ceph-osd@0
     ceph osd down 0
     ceph osd out 0
     ```
3. **Monitor the cluster state:**
   ```bash
   ceph -s
   ceph osd tree
   ceph health detail
   ```

#### Expected Observations
- Cluster transitions from `HEALTH_OK` to `HEALTH_WARN`.
- Status shows: `1 osds down, 1 osds out`.
- Placement Groups: Multiple PGs transition to `active+undersized+degraded`.
- VM Status: Continuous ping to VM 9001 shows 0% packet loss. Client disk read/writes continue without interruption because remaining 2 replicas serve I/O.

#### Recovery Procedure
1. Re-insert the physical drive (or start service):
   ```bash
   systemctl start ceph-osd@0
   ceph osd in 0
   ```
2. Monitor auto-recovery:
   ```bash
   watch ceph -s
   ```
3. Cluster completes PG peering and backfill, returning to `HEALTH_OK` (`12/12 osds up`).

---

### Scenario TC-02 & TC-03: Remove 2 to 3 Disks from 1 Server

#### Objective
Evaluate Ceph resiliency when multiple OSDs on the same physical host fail simultaneously, approaching total node storage capacity loss.

#### Pre-requisites
1. Confirm 3-way replication (`size = 3`, `min_size = 2`):
   ```bash
   ceph osd pool get ceph size
   ceph osd pool get ceph min_size
   ```

#### Step-by-Step Execution
1. Stop 2 or 3 OSD services on `prox22` (e.g., `osd.0`, `osd.1`, and `osd.2`):
   ```bash
   systemctl stop ceph-osd@0 ceph-osd@1 ceph-osd@2
   ceph osd out 0 1 2
   ```
2. Check cluster metrics:
   ```bash
   ceph status
   ceph pg dump summary
   ```

#### Expected Observations
- Cluster shows `HEALTH_WARN: 3 osds down, 3 osds out`.
- PG degradation increases (e.g., ~33% PGs degraded and undersized).
- Because CRUSH failure domain is set to `host`, Ceph never places more than one replica of the same PG on the same physical server. Thus, losing 3 disks on the *same* host never causes PG loss.
- VMs remain fully operational.

#### Recovery Procedure
```bash
systemctl start ceph-osd@0 ceph-osd@1 ceph-osd@2
ceph osd in 0 1 2
watch -n 2 ceph -s
```
Verify all PGs transition back to `active+clean`.

---

### Scenario TC-04: Drive Slot Swapping (Slot 1 to Slot 3)

#### Objective
Investigate cluster and storage controller behavior when an existing drive is moved to a different physical backplane drive bay.

#### Pre-requisites
1. Identify the drive's unique identifiers before moving:
   ```bash
   lsblk -o NAME,UUID,PARTUUID,SERIAL,WWN,MOUNTPOINT
   ceph-volume lvm list
   ```

#### Step-by-Step Execution
1. Power off the server or gracefully unmount the disk.
2. Physically pull the drive from Slot 1 and insert it into Slot 3.
3. Power on the server (or monitor kernel messages if hot-plugged):
   ```bash
   dmesg | tail -n 40
   lsblk -f
   ```

#### Expected Observations & Diagnostics
- **Case A: IT-Mode HBA / Pure Passthrough (Recommended):**
  - The drive appears as a new device name (e.g., `/dev/sde` instead of `/dev/sdb`), but WWN and partition UUIDs are intact.
  - Systemd automatically activates the OSD:
    ```bash
    ceph-volume lvm activate --all
    ```
  - OSD comes online automatically with zero configuration change.
- **Case B: Hardware RAID Controller (Dell PERC / MegaRAID / HP Smart Array):**
  - If controller was configured in RAID 0 per drive, the controller will flag the drive as "Foreign", "Unconfigured Good", or "Missing" due to slot mismatch.
  - To resolve on MegaRAID/StorCLI:
    ```bash
    storcli /c0 show
    storcli /c0 /dall show
    # Import foreign configuration if detected:
    storcli /c0/fall show
    storcli /c0/fall import
    ```
  - Once imported, OS sees disk and Ceph boots the OSD.

---

### Scenario TC-05: Remove All Disks from a Single Node

#### Objective
Verify that complete storage failure on one node does not crash VMs running on that node or disrupt the rest of the cluster.

#### Step-by-Step Execution
1. Stop all 4 OSDs on `prox24`:
   ```bash
   systemctl stop ceph-osd@8 ceph-osd@9 ceph-osd@10 ceph-osd@11
   ceph osd out 8 9 10 11
   ```
2. Verify node state: `prox24` management and network are alive; only its Ceph OSDs are offline.
3. Check VM 9001 (running on Ceph):
   ```bash
   qm status 9001
   ping -c 5 <VM_IP>
   ```

#### Expected Observations
- Ceph reports `HEALTH_WARN: 4 osds down`.
- Since copies exist on `prox22` and `prox23`, the cluster has 2 surviving replicas per PG (exceeding `min_size = 2`).
- VMs continue running. Any VM running on `prox24` accesses Ceph storage across the cluster network interface (`nic3` / `192.168.10.0/24`) from `prox22` and `prox23`.

#### Recovery Procedure
```bash
systemctl start ceph-osd@8 ceph-osd@9 ceph-osd@10 ceph-osd@11
ceph osd in 8 9 10 11
watch ceph -s
```

---

### Scenario TC-06: Cross-Node Multi-Disk Failure (2 Disks from 2 Servers)

#### Objective
Simulate multi-disk hardware degradation across separate hosts and verify Ceph minimum size enforcement.

#### Step-by-Step Execution
1. Take down 2 OSDs on `prox22` and 2 OSDs on `prox23`:
   ```bash
   # On prox22
   systemctl stop ceph-osd@0 ceph-osd@1
   # On prox23
   systemctl stop ceph-osd@4 ceph-osd@5
   ```
2. Observe PG distribution:
   ```bash
   ceph pg dump | grep -i degraded
   ceph -s
   ```

#### Expected Observations
- Health reports significant PG degradation (~60-70% PGs degraded).
- If any PG happens to have had replicas on `[osd.0, osd.4, osd.8]`, it now only has 1 replica alive (`osd.8`).
- When replicas drop below `min_size = 2`, that specific PG temporarily pauses I/O to prevent inconsistent writes.
- Notice: Once disks are brought back, I/O unblocks without data corruption.

#### Recovery Procedure
```bash
# On prox22
systemctl start ceph-osd@0 ceph-osd@1
# On prox23
systemctl start ceph-osd@4 ceph-osd@5
ceph osd in 0 1 4 5
watch ceph -s
```

---

### Scenario TC-07: Live Hot-Removal of Disks (Hot-Unplug Under Load)

#### Objective
Validate that pulling an active drive during high I/O workload does not hang the Linux SCSI subsystem or cause OS kernel panic.

#### Pre-requisites
1. Start an active storage workload in the background:
   ```bash
   rados bench -p ceph 120 write --no-cleanup &
   ```

#### Step-by-Step Execution
1. While `rados bench` is actively printing write IOPS, physically hot-unplug one of the OSD drives.
2. Watch kernel and storage telemetry:
   ```bash
   dmesg -w
   ceph -w
   ```

#### Expected Observations
- Kernel logs a device disconnect (`device removed / rejected I/O`).
- Ceph OSD process detects write errors, aborts safely, and notifies the Ceph Monitor.
- `rados bench` encounters a brief latency bump (100–300 ms) while I/O is redirected to replica OSDs, but benchmark does NOT abort.
- Zero kernel panic on Proxmox host.

#### Recovery Procedure
1. Re-insert the hot-swap drive into the bay.
2. Verify kernel recognition: `dmesg | tail -n 20` shows drive assigned `/dev/sdX`.
3. Restart the OSD:
   ```bash
   systemctl start ceph-osd@<id>
   ```

---

### Scenario TC-08: Simulate Node Failure (Power Off 1 Node)

#### Objective
Validate Proxmox HA CRM automatic failover and Corosync quorum when one node suffers sudden hardware power loss.

#### Pre-requisites
1. Verify HA resource status:
   ```bash
   ha-manager status
   ```
2. Ensure VM 9001 is configured for HA:
   ```bash
   ha-manager config
   # Should list: vm:9001 (state=started, max_relocate=1)
   ```
3. Place VM 9001 running on `prox24`.

#### Step-by-Step Execution
1. Pull power cable or execute hard poweroff on `prox24`:
   ```bash
   # On prox24
   poweroff -f
   ```
2. On `prox22` (surviving HA master), track quorum and HA events in real-time:
   ```bash
   watch -n 1 "pvecm status && echo '--- HA ---' && ha-manager status"
   ```

#### Expected Timeline & Telemetry
```
T0          Node prox24 powered off
T+15s       Corosync drops token; prox22 + prox23 report 2/3 votes -> QUORATE
T+45s       Ceph monitors detect mon.prox24 lost; quorum maintained by prox22 + prox23
T+50-60s    HA CRM watchdog timeout declares prox24 dead; flags VMs for fencing
T+120-140s  Fencing verified; HA schedules VM 9001 restart on prox22 or prox23
T+145s      VM 9001 boots up on healthy node; guest OS ping responds
```

#### Recovery Procedure
1. Power `prox24` back on.
2. As soon as OS boots:
   - Corosync re-joins: votes return to 3/3.
   - Ceph OSDs start: 12/12 OSDs up.
   - PGs re-peer back to `HEALTH_OK`.
   - HA manager automatically stabilizes.

---

### Scenario TC-09: Remove Two Nodes from a Three-Node Cluster (Quorum Loss)

#### Objective
Validate that losing 2 out of 3 nodes safely freezes operations to prevent split-brain and verify emergency disaster recovery procedures.

#### Pre-requisites
1. All 3 nodes online and quorate: `pvecm status` shows `Nodes: 3, Quorum: 2`.

#### Step-by-Step Execution
1. Power off `prox23` and `prox24` simultaneously:
   ```bash
   # On prox23
   poweroff -f
   # On prox24
   poweroff -f
   ```
2. On surviving node `prox22`, observe cluster and filesystem behavior:
   ```bash
   pvecm status
   ls -la /etc/pve
   qm status 9001
   ```

#### Expected Observations
- `pvecm status` shows `Activity: Blocked, Quorum: 2, Votes: 1 (Lost Quorum)`.
- `/etc/pve` (Proxmox Cluster Filesystem - `pmxcfs`) switches to **read-only mode**. Attempting to edit files or start VMs via GUI returns error: `Cluster not ready - no quorum? (500)`.
- HA stops running VMs to prevent dual-writing to shared storage.
- Ceph monitors drop to 1/3, suspending storage write operations safely.

#### Emergency Disaster Recovery Procedure (If lost nodes are permanently dead)
To regain quorum on the single surviving node:
```bash
# Temporarily set expected votes to 1
pvecm expected 1

# Verify /etc/pve is writeable again:
touch /etc/pve/local/test_write && rm /etc/pve/local/test_write
```

#### Normal Recovery Procedure (Bringing nodes back)
1. Power on `prox23` and `prox24`.
2. Once at least one node boots, quorum (2/3) is immediately restored, `/etc/pve` becomes read-write, Ceph monitors re-peer, and VMs resume.

---

### Scenario TC-10: Network Failure (Single Cable / Bonding Degradation)

#### Objective
Verify that losing one physical interface on a bonded link (`bond0`) does not drop packets or disrupt VM traffic.

#### Step-by-Step Execution
1. Identify active slave interface:
   ```bash
   cat /proc/net/bonding/bond0
   ```
2. Disable the active slave interface (e.g., `nic1`):
   ```bash
   ip link set nic1 down
   ```
3. Start continuous ping and check bonding status:
   ```bash
   ping -c 20 10.31.6.1
   cat /proc/net/bonding/bond0
   ```

#### Expected Observations
- Bonding driver switches to backup slave interface within <50 ms.
- 0% packet loss (or at most 1 dropped packet).
- Proxmox and Ceph experience no disruption.

#### Recovery Procedure
```bash
ip link set nic1 up
cat /proc/net/bonding/bond0
```

---

### Scenario TC-11: Total Network Isolation (Dual Cable Disconnect)

#### Objective
Validate hardware watchdog fencing and HA failover when a node is completely severed from management and storage networks.

#### Step-by-Step Execution
1. On `prox24`, drop all incoming and outgoing network traffic:
   ```bash
   iptables -I INPUT -j DROP
   iptables -I OUTPUT -j DROP
   ```
2. Simultaneously on `prox22`, watch cluster response:
   ```bash
   pvecm status
   ha-manager status
   ```

#### Expected Observations
- `prox22` and `prox23` retain 2/3 quorum.
- `prox24` loses Corosync heartbeats. Its local software watchdog (`/dev/watchdog`) does not get refreshed by Corosync, causing `prox24` to trigger an automatic hardware reboot (fencing) after ~53–60 seconds.
- Surviving nodes fence `prox24` and migrate/restart its VMs.

#### Recovery Procedure
1. Clear firewall block on `prox24`:
   ```bash
   iptables -F
   ```
2. Node re-establishes network connection and joins cluster cleanly.

---

### Scenario TC-12: Simulate Software Disk Failure on ZFS Root Pool (`rpool`)

#### Objective
Verify ZFS mirror resiliency by marking one boot mirror drive offline via software command.

#### Pre-requisites
1. Check root pool status:
   ```bash
   zpool status rpool
   ```

#### Step-by-Step Execution
1. Offline one mirror disk:
   ```bash
   # Replace <disk-part> with the second partition/vdev from zpool status (e.g., /dev/disk/by-id/nvme-...-part3)
   zpool offline rpool /dev/disk/by-id/nvme-WDS500G3X0G-00SJE0_xxxx-part3
   ```
2. Check pool status:
   ```bash
   zpool status rpool
   ```

#### Expected Observations
- Pool state transitions to `DEGRADED`.
- Proxmox OS remains fully operational and responsive; reads/writes transparently redirect to the surviving mirror SSD.

#### Recovery Procedure
1. Bring disk back online:
   ```bash
   zpool online rpool /dev/disk/by-id/nvme-WDS500G3X0G-00SJE0_xxxx-part3
   ```
2. Observe auto-resilver:
   ```bash
   zpool status rpool
   # scan: resilver in progress ...
   # scan: resilvered X MB in 00:00:04 with 0 errors
   # state: ONLINE
   ```

---

### Scenario TC-13: Physical Failure of ZFS Boot Mirror (SSD Pull)

#### Objective
Verify that Proxmox VE can boot and run with one boot mirror SSD physically missing.

#### Step-by-Step Execution
1. Power down server:
   ```bash
   poweroff
   ```
2. Physically disconnect Boot SSD #1 from the server.
3. Power on the server.

#### Expected Observations
- UEFI/BIOS discovers Boot SSD #2 in the boot order and boots Proxmox VE.
- Node boots successfully to web GUI and SSH login.
- `zpool status rpool` reports:
  ```
  state: DEGRADED
  status: One or more devices could not be used because the device is missing.
  ```

#### Recovery Procedure
1. Power down, reconnect Boot SSD #1, and power on.
2. ZFS automatically detects re-attached drive, initiates resilver, and returns to `ONLINE`.

---

### Scenario TC-14: Replace a Failed Disk with a New One in ZFS (`zpool replace`)

#### Objective
Complete the production procedure for replacing a permanently dead boot disk with a new, blank drive.

#### Step-by-Step Execution
1. **Identify failed and replacement drive:**
   - Good surviving drive: `/dev/sda`
   - New blank drive: `/dev/sdb`
2. **Copy partition table from good drive to new drive:**
   ```bash
   sgdisk -Z /dev/sdb
   sgdisk -R /dev/sdb /dev/sda
   sgdisk -G /dev/sdb
   ```
3. **Format and initialize bootloader on new drive:**
   ```bash
   # Partition 2 is typically the ESP (EFI System Partition)
   proxmox-boot-tool format /dev/sdb2
   proxmox-boot-tool init /dev/sdb2
   ```
4. **Replace the disk in the ZFS pool:**
   ```bash
   # Partition 3 is the ZFS data partition
   zpool replace -f rpool <OLD_FAILED_DEVICE_ID> /dev/sdb3
   ```
5. **Verify resilver and status:**
   ```bash
   zpool status rpool
   proxmox-boot-tool status
   ```

---

### Scenario TC-15: Disk Removal During Active VM Live Migration

#### Objective
Validate cluster integrity and error handling if a storage drive drops while a VM is actively migrating across nodes.

#### Pre-requisites
1. Test VM 9001 running on `prox22`.

#### Step-by-Step Execution
1. Start live migration from `prox22` to `prox23`:
   ```bash
   qm migrate 9001 prox23 --online
   ```
2. While migration log shows RAM transfer or disk sync in progress, drop an OSD drive on source or target:
   ```bash
   systemctl stop ceph-osd@0
   ```
3. Monitor migration output:
   ```bash
   cat /var/log/pve/tasks/...
   ```

#### Expected Observations
- **Ceph Shared Storage:** Since Ceph handles disk access over network fabric, a single OSD failure does NOT abort migration; QEMU continues reading through surviving replicas.
- **Local ZFS Storage:** If migration uses QEMU `drive-mirror` and local target disk fails, QEMU safely pauses/aborts migration, logs an error, and keeps the original VM running intact on `prox22`. Data is NEVER corrupted.

---

### Scenario TC-16: Multiple OSD Failures Exceeding Replication Factor

#### Objective
Examine cluster behavior during a catastrophe where surviving replicas drop below `min_size` and perform safe recovery.

#### Step-by-Step Execution
1. Force out OSDs until a PG loses all copies:
   ```bash
   ceph osd out 0 4 8
   systemctl stop ceph-osd@0 ceph-osd@4 ceph-osd@8
   ```
2. Check cluster state:
   ```bash
   ceph -s
   ceph health detail
   ```

#### Expected Observations
- Cluster shows `HEALTH_ERR: reduced data availability: X pgs down, X pgs incomplete`.
- Client I/O to affected blocks blocks safely in memory (no data corruption occurs, but applications pause waiting for I/O).

#### Safe Recovery Procedure
```bash
# Never mark PGs lost without backups! Bring OSD services back:
systemctl start ceph-osd@0 ceph-osd@4 ceph-osd@8
ceph osd in 0 4 8
# Wait for peering:
watch -n 1 ceph -s
```
All PGs return to `active+clean` and paused I/O resumes automatically.

---

### Scenario TC-17: Ceph Monitor Failure & Corrupted DB Reconstruction

#### Objective
Simulate total corruption of a Ceph Monitor database on one node and rebuild it from surviving cluster monitors.

#### Step-by-Step Execution
1. Stop monitor on `prox23` and delete its database:
   ```bash
   systemctl stop ceph-mon@prox23
   rm -rf /var/lib/ceph/mon/ceph-prox23
   ```
2. Verify cluster status from `prox22`:
   ```bash
   ceph -s
   # Shows HEALTH_WARN: 1/3 mons down, quorum prox22,prox24
   ```
3. **Rebuild the monitor on `prox23`:**
   ```bash
   # On prox23:
   # Extract latest monmap from healthy monitor:
   ceph mon getmap -o /tmp/monmap
   
   # Re-initialize monitor DB:
   ceph-mon --mkfs -i prox23 --monmap /tmp/monmap --keyring /etc/pve/priv/ceph.client.admin.keyring
   
   # Ensure correct permissions:
   chown -R ceph:ceph /var/lib/ceph/mon/ceph-prox23
   
   # Start service:
   systemctl start ceph-mon@prox23
   ```
4. Verify cluster health:
   ```bash
   ceph -s
   # Output: 3 mons: prox22,prox23,prox24 (all in quorum) -> HEALTH_OK
   ```

---

### Scenario TC-18: Ceph CRUSH Map Rebalancing Performance Benchmarking

#### Objective
Benchmark real-time IOPS and latency while Ceph is actively rebalancing data across OSDs.

#### Step-by-Step Execution
1. **Establish baseline benchmark:**
   ```bash
   rados bench -p ceph 60 write --no-cleanup
   # Note baseline IOPS (e.g., ~150 IOPS) and Latency (e.g., ~105 ms)
   ```
2. **Trigger rebalance by adjusting CRUSH weight of an OSD:**
   ```bash
   ceph osd crush reweight osd.1 0.5
   ```
3. **Run benchmark during rebalance:**
   ```bash
   rados bench -p ceph 60 write --no-cleanup
   ```
4. Check recovery traffic:
   ```bash
   ceph -s | grep -i recovery
   ```

#### Evaluation Criteria
- Because Ceph Reef throttles recovery I/O (`osd_max_backfills = 1`), client writes should continue with reasonable latency.
- Restore weight to 1.0 after test:
  ```bash
  ceph osd crush reweight osd.1 1.0
  ```

---

### Scenario TC-19: Ceph Single-Monitor SPOF Failure & Cluster Freeze

#### Objective
Demonstrate why Ceph requires an odd number (minimum 3) of monitors to maintain quorum.

#### Step-by-Step Execution
1. Stop monitors on `prox23` and `prox24`:
   ```bash
   systemctl stop ceph-mon@prox23
   systemctl stop ceph-mon@prox24
   ```
2. Observe single monitor on `prox22`:
   - With 1/3 monitors alive, quorum is lost (`votes < 2`).
   - Run `ceph -s`: command hangs or prints `no monitors reached / quorum lost`.
   - Client read/writes to Ceph storage freeze.

#### Recovery Procedure
```bash
# Bring surviving monitors back online:
systemctl start ceph-mon@prox23 ceph-mon@prox24
ceph -s
```
Quorum is restored immediately and storage operations resume.

---

## Part 3: Quick Diagnostic Cheat Sheet

| Purpose | Command |
|---|---|
| Check Corosync Quorum | `pvecm status` |
| View Cluster Nodes | `pvecm nodes` |
| Check High Availability | `ha-manager status` |
| Ceph General Health | `ceph status` or `ceph -s` |
| Ceph Detailed Alerts | `ceph health detail` |
| Ceph OSD Topology | `ceph osd tree` |
| Placement Group Health | `ceph pg dump summary` |
| Real-time Ceph Events | `ceph -w` |
| ZFS Pool Status | `zpool status -v` |
| ZFS Disk Replacement | `zpool replace -f <pool> <old-id> <new-dev>` |
| Network Bond Status | `cat /proc/net/bonding/bond0` |
| Storage Benchmark | `rados bench -p ceph 30 write --no-cleanup` |
