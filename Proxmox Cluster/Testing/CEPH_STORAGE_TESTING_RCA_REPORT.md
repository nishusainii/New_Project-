# COMPREHENSIVE ROOT CAUSE ANALYSIS (RCA) REPORT
## Proxmox VE Cluster & Ceph Storage Resilience Testing Incidents

---

| **Document Metadata** | **Details** |
| :--- | :--- |
| **Cluster Name** | `cisai-pve` (Proxmox VE 8.x Enterprise Cluster) |
| **Cluster Nodes** | `prox22` (`10.31.6.172`), `prox23` (`10.31.6.173`), `prox24` (`10.31.6.174`) |
| **Incident Classification** | Physical Fault Injection & Post-Testing Cluster Transition Artifacts |
| **Date & Time** | September 24, 2026 |
| **Environment** | Production Proxmox HA 3-Node Cluster (12x 20TB SAS Ceph OSDs + 3x 127 TiB ZFS Pools) |
| **Impact Level** | Zero Data Loss (100% Data Integrity Preserved) / Transient Management UI Degradation |
| **Author** | CISAI Datacenter Infrastructure & Storage Engineering |

---

## 1. Executive Summary

During physical datacenter fault-tolerance testing (including 10G interconnect cable pullout tests, SAS drive hot-swaps, and node power-cycle failover scenarios), four distinct phenomena were observed:

1. **Ceph Storage Recovery Delay & `HEALTH_WARN` State:** Ceph OSDs took time to recover, with some OSDs reporting `(5) Input/output error` and placement groups (PGs) remaining degraded.
2. **Web GUI "?" Question Marks & Blue Wrench Icons:** `prox23` and `prox24` appeared with question mark icons or wrench icons in the Proxmox Web GUI sidebar tree, with their resources listed as `unknown`.
3. **VM Migration & Freeze Locks:** Virtual Machines (9001–9004) temporarily displayed `migrate` or `freeze` state in HA Manager.
4. **Systemd "Transaction is Destructive" Service Start Failures:** Initial attempts to restart `pvestatd` and `pvedaemon` on member nodes returned `pam_nologin` and transaction conflict warnings.

This RCA document provides the **deep technical explanations** for why each of these behaviors occurred, why they are expected consequences of specific Linux kernel / Proxmox HA subsystems during physical pull testing, and how they were completely resolved to bring the cluster to **100% `HEALTH_OK`**.

---

## 2. Technical Root Causes & Mechanisms

```
+-----------------------------------------------------------------------------------------------+
|                                      CLUSTER RESILIENCE TESTING                               |
+------------------------------+-------------------------------+--------------------------------+
                               |                               |
                               v                               v
                [ Physical Drive Hot-Pull ]        [ HA Failover & Maintenance ]
                               |                               |
                               v                               v
             Kernel SCSI Re-enumeration:             HA Manager sets Node into
             /dev/sdb (8:16) -> /dev/sdn (8:208)      'Maintenance Mode' (Blue Wrench)
                               |                               |
                               v                               v
             LVM Device-Mapper In-Memory Desync:     pvestatd Daemon stopped on node;
             /dev/dm-X holds dead minor handle       PVE API reports status: 'unknown' (?)
                               |                               |
                               v                               v
             Ceph Direct AIO -> (5) I/O Error;       Pending Reboot triggers systemd
             Ceph Heartbeat Timeout (20s) -> OSDs    stop transaction & /run/nologin
                               |                               |
                               +---------------+---------------+
                                               |
                                               v
                          [ Post-Reboot & DM-Refresh Resolution ]
                                               |
                                               v
                    +-----------------------------------------------------+
                    | * 3/3 Corosync Quorum Active                        |
                    | * 12/12 Ceph OSDs UP/IN (HEALTH_OK)                 |
                    | * All 3 Nodes Solid Green Checkmarks in Web GUI     |
                    +-----------------------------------------------------+
```

---

### Root Cause 1: Why Ceph Storage Takes Time & Throws I/O Errors During Drive Hot-Pulls

#### Mechanism:
* **SCSI Dynamic Minor Number Assignment:** When an enterprise SAS/SATA drive is physically unlatched from the backplane and re-inserted, the Linux SCSI mid-layer detects a removal of the device handle and assigns the *next sequential SCSI letter* upon re-insertion (e.g., the drive originally mapped as `/dev/sdb` with Major:Minor `8:16` is re-enumerated as `/dev/sdn` with Major:Minor `8:208`).
* **LVM Device-Mapper Desync:** Ceph Bluestore uses LVM Logical Volumes (`/dev/ceph-<vg>/osd-block-<uuid>`). When the physical drive returns as `/dev/sdn`, the in-memory Linux Device-Mapper table (`/dev/dm-7`) still points to the dead major:minor target `8:16`.
* **Direct I/O Failure:** When `ceph-volume` or `ceph-osd` attempts to read the Bluestore superblock via `direct_aligned_read`, the kernel returns `EIO (Error 5: Input/output error)`.
* **Ceph Heartbeat & Recovery Timers:** Ceph OSDs exchange heartbeat pings every 6 seconds. If an OSD misses heartbeats for `osd_heartbeat_grace` (20 seconds), the Ceph MON leader marks the OSD as `down`. Upon drive re-insertion and service startup, Ceph must:
  1. Peer placement groups (PGs).
  2. Replay Bluestore write-ahead logs (WAL).
  3. Reconcile degraded or misplaced objects across surviving replicas.
  This intentional reconciliation phase causes Ceph to transition from `undersized+degraded` -> `active+clean`, taking between 30 to 90 seconds depending on pending PG logs.

---

### Root Cause 2: Why the Proxmox Web GUI Showed "?" and Blue Wrench Icons

#### Mechanism:
* **HA Maintenance Mode Flag:** During node failover and recovery testing, `prox23` and `prox24` entered HA Maintenance mode (`lrm prox23 (maintenance mode)`).
* **UI Representation:**
  * **Blue Wrench Icon:** Proxmox Web UI renders a blue wrench icon next to any node that has an active `maintenance` state in `/etc/pve/ha/manager_status`.
  * **Question Mark `?` Icon & "Unknown" Status:** When a node enters maintenance mode or undergoes a reboot, the `pvestatd` (Proxmox VE Cluster Metric Daemon) on that node is suspended. The cluster resource API (`/cluster/resources`) stops receiving live CPU, memory, and storage metrics for that node, marking its status as `status: "unknown"` (which ExtJS displays as a `?`).
* **Resolution:** Disabling maintenance mode (`ha-manager node-maintenance disable <node>`) and restarting `pvestatd` immediately resumes metric broadcasting, turning all node icons to solid **green checkmarks**.

---

### Root Cause 3: Why Initial Systemctl Start Failed with "Transaction is Destructive"

#### Mechanism:
* **Pending Server Reboot Sequence:** When a reboot was initiated on `prox23` and `prox24`, systemd created `/run/nologin` (PAM login lock) and queued `stop` jobs for foundational targets (`systemd-modules-load.service`, `remote-fs.target`, `dev-pve-swap.swap`).
* **Transaction Conflict:** Executing `systemctl start pvestatd` via SSH while systemd already had an active `stop` job queued in its transaction pipeline caused systemd to reject the start request with:
  ```
  Failed to start pvestatd.service: Transaction for pvestatd.service/start is destructive 
  (systemd-modules-load.service has 'stop' job queued, but 'start' is included in transaction).
  ```
* **Resolution:** Allowing the enterprise servers to finish their full hardware reboot cycle (BIOS POST, SAS HBA discovery, systemd target initialization) allowed systemd to start all cluster daemons in the clean, dependency-ordered sequence.

---

### Root Cause 4: Why VMs Displayed "Migrate" and "Freeze" States

#### Mechanism:
* **Proxmox Cluster Resource Manager (CRM) Protection:** When `prox23` and `prox24` became unreachable during the 10G cable pullout and reboot tests, the Proxmox HA Manager's watchdog mechanism froze local resources (`freeze` state) to prevent split-brain execution.
* **Migration Locks:** VMs scheduled for failover had `lock: migrate` written to their configuration files in `/etc/pve/nodes/<node>/qemu-server/<vmid>.conf`.
* **Resolution:** Once quorum was restored (3/3 votes), the CRM leader (`prox22`) released the migration locks and resumed VMs into their configured running states.

---

## 3. Incident Timeline & Telemetry Summary

| Time (IST) | Event / Test Phase | System Telemetry | Subsystem Impact |
| :--- | :--- | :--- | :--- |
| **21:30** | SAS Drive Hot-Pull (TC-01/04) | Kernel logs `Attached SCSI disk [sdn]` | `osd.3` down due to stale `dm-7` mapping |
| **22:05** | 10G Interconnect Outage Test | 10G DAC ping timeout (192.168.10.x) | Ceph MON marks OSDs down after 20s grace |
| **22:20** | HA Maintenance Mode Activated | `lrm prox23 (maintenance mode)` | UI displays Blue Wrench icon; `pvestatd` paused |
| **22:25** | Systemd Reboot Sequence | `pam_nologin` active; transaction lock | Node status transitions to `unknown` (?) |
| **22:29** | Nodes Boot Complete & Corosync Quorum | 3/3 Votes Quorate (`Ring ID: 1.10f`) | Corosync & PVE cluster sync restored |
| **22:30** | Ceph Bluestore Direct AIO Active | 12/12 OSDs UP & IN; 33 PGs clean | Ceph returns to **`HEALTH_OK`**; UI Green |

---

## 4. Final Health Verification Matrix

| Component | Target Metric | Verified Post-Test State | Result |
| :--- | :--- | :--- | :--- |
| **Node Status** | `prox22`, `prox23`, `prox24` | 🟢 All 3 nodes `online` in `/cluster/resources` | **PASS** |
| **Corosync Quorum** | 3 / 3 Expected Votes | 🟢 3 Votes (`Quorate: Yes`, `Total votes: 3`) | **PASS** |
| **Ceph Health** | Cluster Status | 🟢 **`HEALTH_OK`** (0 degraded objects, 0 down PGs) | **PASS** |
| **Ceph OSDs** | 12 OSDs across 3 Nodes | 🟢 **12 / 12 UP & IN** (33/33 active+clean) | **PASS** |
| **Ceph MONs** | 3 MON Daemons | 🟢 **3 MONs in Quorum** (`prox22`, `prox23`, `prox24`) | **PASS** |
| **ZFS Storage** | `zfs-ha` RAIDZ2 Pool | 🟢 **127 TiB ONLINE** (0 read/write/cksum errors) | **PASS** |
| **10G Network** | Interconnect Latency | 🟢 **0.08ms – 0.14ms (0% packet drop)** | **PASS** |
| **HA Manager** | CRM / LRM State | 🟢 Quorum OK, CRM Watchdog Armed & Active | **PASS** |
| **Data Loss** | Object Integrity | 🟢 **0 Bytes Lost / 100% Data Integrity** | **PASS** |

---

## 5. Standard Operating Procedures (SOP)

### SOP-A: Resolving Stale Ceph LVM Mappings After Drive Hot-Swap Without Reboot
If a drive is hot-swapped and throws `(5) Input/output error`:
```bash
# 1. Stop OSD target
systemctl stop ceph-osd.target

# 2. Deactivate stale LVM mappings
vgchange -an $(vgs -o vg_name --noheadings | grep ceph | tr "\n" " ") 2>/dev/null || true

# 3. Rescan SCSI bus
udevadm trigger && udevadm settle

# 4. Reactivate Ceph Volume Groups
vgchange -ay

# 5. Clear systemd burst limits and activate OSDs
systemctl reset-failed
ceph-volume lvm activate --all
systemctl restart ceph-osd.target
```

### SOP-B: Clearing HA Maintenance Mode & Question Mark UI Icons
If a node shows a blue wrench or question mark after maintenance:
```bash
# 1. Disable maintenance mode
ha-manager node-maintenance disable <node_name>

# 2. Ensure cluster metric services are active
systemctl start pvestatd pvedaemon pveproxy

# 3. Clear any leftover migration locks on VMs
for vmid in $(qm list | awk 'NR>1 {print $1}'); do
    qm unlock $vmid 2>/dev/null || true
done
```

---

## 6. Conclusion & Production Readiness

* **Zero Hardware Failure:** All 36x 20TB Enterprise SAS hard drives, 10G SFP+ DAC cables, and Supermicro/Dell server backplanes are in 100% operational condition.
* **Fault Tolerance Validated:** Ceph 3x replication and ZFS RAIDZ2 successfully protected all virtual machine data through single drive pulls, multi-drive mobility swaps, 10G storage network blackouts, and node reboots.
* **Current Operational State:** **PRODUCTION READY (100% HEALTH_OK)**.
