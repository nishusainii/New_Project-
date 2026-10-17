# Proxmox VE Cluster High Availability (HA) Failover & Automatic Migration Validation Report
**CISAI / Innspark Production Infrastructure Engineering & Resilience Verification**

- **Cluster ID:** `cisai-pve`
- **Lead Engineer:** Nishu Saini (Innspark)
- **Execution Date:** 2026-09-18
- **Platform:** Proxmox VE 8.x / Corosync 3.x / Ceph Reef / ZFS RAIDZ2
- **Overall Verdict:** **100% VERIFIED PASS & APPROVED FOR PRODUCTION**

---

## 1. Executive Summary & Validation Scope
This test validation report documents the live verification of Proxmox VE High Availability (HA) automated failover, zero-downtime live migration, and node reboot resilience conducted on the active 3-node enterprise cluster `cisai-pve`.

### Key Verified Capabilities
1. **Reboot Automatic Migration (`shutdown_policy=migrate`):** When a host is rebooted, running HA VMs automatically live-migrate to surviving nodes before the host restarts.
2. **Ceph Distributed Live Migration (0s Downtime):** VM 9001 transferred 4.0 GiB RAM state live without connection loss or VM shutdown across cluster nodes.
3. **ZFS Replicated Failover (Synchronized Storage):** VM 9002 utilized active NBD dirty-bitmap mirroring and scheduled snapshots to maintain storage continuity across hosts.

---

## 2. Production Topology & Physical Infrastructure

| Node Hostname | Node ID | Management IP | Storage Interconnect (10G DAC) | Cluster Role | Storage Subsystems Active |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **prox22** | 2 | `10.31.6.172` | `192.168.10.22` | Active CRM Master / Corosync Voter | 4 Ceph OSDs (0,3,6,9) + 7-Disk ZFS RAIDZ2 (`zfs-ha`) |
| **prox23** | 3 | `10.31.6.173` | `192.168.10.23` | Member Node / Corosync Voter | 4 Ceph OSDs (1,4,7,10) + 7-Disk ZFS RAIDZ2 (`zfs-ha`) |
| **prox24** | 1 | `10.31.6.174` | `192.168.10.24` | Primary Workload Host / Reboot Target | 4 Ceph OSDs (2,5,8,11) + 7-Disk ZFS RAIDZ2 (`zfs-ha`) |

---

## 3. High Availability Policy Configuration (`datacenter.cfg`)

### Default vs Production Configuration Analysis
By default, Proxmox VE uses `shutdown_policy=conditional`. In this default configuration, if an operator issues a `reboot` command, Proxmox **freezes** running HA virtual machines on the local server and does not migrate them, causing workload downtime.

To fulfill the production mandate of automatic evacuation on reboot or shutdown, the cluster datacenter configuration was updated in `/etc/pve/datacenter.cfg` (synchronized across all nodes via pmxcfs):

```ini
keyboard: en-us
ha: shutdown_policy=migrate
```

**Mechanism:** With `shutdown_policy=migrate`, systemd shutdown hooks notify `pve-ha-crm`. The HA manager intercepts the power-off sequence, issues live migration commands to evacuate all running guests to healthy quorum members, and releases the host for reboot only after all guests are safely operational elsewhere.

---

## 4. Test Scenario 1: Controlled Node Evacuation (Node Maintenance Mode)

| Step | Execution Command | Target Workload | Source Host | Destination Host | Migration Method & Outcome |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **1.1** | `ha-manager crm-command node-maintenance enable prox24` | Cluster Control | `prox24` | Cluster-Wide | **PASS** CRM initiates coordinated evacuation |
| **1.2** | `qmigrate 9001 (Ceph RBD)` | VM 9001 | `prox24` | `prox22` | **PASS** Live RAM transfer (4.0 GiB), 0s VM downtime |
| **1.3** | `qmigrate 9002 (ZFS zvol)` | VM 9002 | `prox24` | `prox23` | **PASS** NBD dirty-bitmap mirror + RAM sync to prox23 |
| **1.4** | Post-Evacuation Verification | Both VMs | `prox24` | Surviving Nodes | **PASS** `prox24` empty, marked in maintenance mode |
| **1.5** | `ha-manager crm-command node-maintenance disable prox24` | Cluster Control | `prox24` | Active Pool | **PASS** Node re-enters active quorum rotation |

---

## 5. Test Scenario 2: Live Host Reboot Automatic Failover (`reboot prox24`)

### Chronological Timeline Table

| Time Offset | prox24 Host State | Corosync Quorum | VM 9001 (Ceph) Location | VM 9002 (ZFS) Location | Cluster Event Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| **T + 00s** | Reboot Triggered | 3/3 Votes | `prox24` (running) | `prox24` (running) | SSH `reboot` dispatched. Systemd triggers PVE shutdown hook. |
| **T + 12s** | Intercepting Reboot | 3/3 Votes | `prox24 -> prox22` | `prox24 -> prox23` | CRM Master schedules migrations; host power-off is paused. |
| **T + 75s** | Evacuation Finished | 3/3 Votes | `prox22` (running) | `prox23` (running) | Both VMs successfully landed and active on survivors. |
| **T + 95s** | Host Shutting Down | 2/3 Votes | `prox22` (running) | `prox23` (running) | `prox24` completes shutdown and power cycles hardware. |
| **T + 120s – 350s** | Host Offline / POST | 2/3 Votes | `prox22` (running) | `prox23` (running) | Server executes BIOS/UEFI POST and OS boot. Workloads online. |
| **T + 386s** | OS Booted, LRM Active | 3/3 Votes | `prox22` (running) | `prox23` (running) | `prox24` Corosync knet links re-established. Quorum 3/3 restored. |
| **T + 397s** | Ceph & ZFS Online | 3/3 Votes | `prox22 -> prox24` | `prox23 -> prox24` | All 4 OSDs on prox24 rejoin Ceph. Workloads migrate back. |
| **T + 440s** | Cluster Stabilized | 3/3 Votes | `prox24` (healthy) | `prox24` (healthy) | Failback complete. 12/12 OSDs UP, ZFS replication jobs OK. |

---

## 6. Comprehensive Automated Test Suite Validation Matrix

| Subsystem Suite | Check Item | Monitored Metric / Threshold | Measured Value | Verdict |
| :--- | :--- | :--- | :--- | :---: |
| **Cluster & Quorum** | Corosync Quorum State | Votequorum quorate (Expected: Yes) | Quorate: Yes (3/3 votes, Quorum: 2) | **PASS** |
| | Cluster Membership | All 3 nodes online | `prox22`, `prox23`, `prox24` connected | **PASS** |
| | Core Daemons | `pve-cluster`, `corosync`, `pvedaemon` | Active & running across all 3 nodes | **PASS** |
| | Storage Mounts | Cluster shared & local storage | Ceph: Active, ZFS-HA: Active | **PASS** |
| **Network Matrix** | Management LAN Latency | Inter-node ping RTT (<= 5.0 ms, loss 0%) | Avg: 0.188 ms – 0.242 ms (0.0% loss) | **PASS** |
| | 10G Interconnect Latency | Inter-node ping RTT (<= 1.5 ms, loss 0%) | Avg: 0.074 ms – 0.118 ms (0.0% loss) | **PASS** |
| | Path Redundancy | Dual subnet matrix (12 paths) | All 12 paths reachable without packet loss | **PASS** |
| **Ceph Storage** | Monitor Quorum | Active Ceph Monitors (>= 3) | 3 active (`mon.prox22`, `mon.prox23`, `mon.prox24`) | **PASS** |
| | OSD Distribution | 12 Disks total (4 per node) | 12/12 OSDs UP & IN (IDs 0–11) | **PASS** |
| | Placement Groups | Degraded / misplaced PGs = 0 | 33/33 PGs active+clean | **PASS** |
| **ZFS RAIDZ2** | Pool Health | State: ONLINE, 0 errors | State: ONLINE (7/7 disks healthy per node) | **PASS** |
| | ZFS Pool Scrub | Scrub repaired 0B, 0 checksum errors | Clean scrub completed on all 3 nodes | **PASS** |
| | ZFS Replication | Jobs `9002-0` & `9002-1` sync state | State: OK, 0 FailCount (LastSync verified) | **PASS** |
| **HA Manager** | Quorum & CRM Master | Active CRM Master on online host | Active CRM Master: `prox22` (active) | **PASS** |
| | Hardware Watchdog | Watchdog fencing armed | Fencing armed (CRM watchdog active) | **PASS** |
| | LRM States | Active LRMs on 3/3 nodes, 0 error states | 3 LRMs active; VM 9001 & VM 9002 running | **PASS** |

---

## 7. Operator SOP & Command Reference

### Workflow A: Standard Server Reboot / Kernel Patching
With `ha: shutdown_policy=migrate` permanently configured:
```bash
# Execute standard reboot on any cluster node
reboot
# The HA stack automatically migrates running guests to other nodes before powering down.
```

### Workflow B: Planned Physical Hardware Maintenance
```bash
# Step 1: Evacuate the node cleanly
ha-manager crm-command node-maintenance enable <node-name>

# Step 2: Confirm node has no running services
ha-manager status

# Step 3: Perform hardware maintenance, power on server, then restore:
ha-manager crm-command node-maintenance disable <node-name>
```

---

## 8. Certification & Sign-Off
- **Test Engineer:** Nishu Saini, Systems Engineer (Innspark Infrastructure)
- **Lead Reviewer:** Infrastructure Architecture Team (CISAI Computing Cluster)
- **Date:** 2026-09-18
- **Certification Status:** **CERTIFIED PASS & READY FOR PRODUCTION**
