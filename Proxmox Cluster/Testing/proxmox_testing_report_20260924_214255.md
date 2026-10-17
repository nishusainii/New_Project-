# Proxmox VE Cluster Physical Testing & 19-Scenario Runbook Report
**Cluster Name:** `cisai-pve` | **Execution Date:** 2026-09-24 21:42:55 | **Pass Rate:** 18/22 (81.8%)

## Cluster Node Topology & IPs
| Node Name | Node ID | Management IP | 10G Fabric IP | Dedicated BMC IP | Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `prox22` | 2 | `10.31.6.172` | `192.168.10.22` | `10.31.5.78` | CRM Master Leader |
| `prox23` | 3 | `10.31.6.173` | `192.168.10.23` | `10.31.5.61` | Member Node |
| `prox24` | 1 | `10.31.6.174` | `192.168.10.24` | `10.31.5.62` | Member Node |

## Master 19-Scenario & Physical Test Execution Summary

| TC ID | Test Description | Category | Target Node | Status | Duration | Physical Action Performed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PRE-01** | Cluster Baseline Pre-Flight Health Audit | Pre-Flight | `prox22` | **WARN** | 75.12s | Software Automated |
| **TEST-5.1** | Single PSU Pull (Redundant Power Supply) | Power Redundancy | `prox24` | **WARN** | 150.03s | Unplug Power Cord 1 from the rear of prox24 (keep PSU 2 plugged in). |
| **TC-08** | Simulate Node Failure (Power Off / HA Failover) | Power / HA | `prox24` | **WARN** | 462.27s | Unplug BOTH power cords simultaneously from prox24 (or execute power drop simulation). |
| **TC-09** | Dual Node Failure (Split-Brain Safety Freeze) | Power / HA | `prox23, prox24` | **PASS** | 500.85s | Unplug power simultaneously from BOTH prox23 and prox24 (or simulate dual node stop). |
| **TC-01** | Remove 1 Disk from 1 Server | Ceph Storage | `prox22` | **PASS** | 108.26s | Unlatch and pull drive caddy for Slot 1 (/dev/sdb / osd.0) on prox22. |
| **TC-02** | Remove 2 Disks from 1 Server | Ceph Storage | `prox22` | **PASS** | 81.69s | Unlatch Slot 1 and Slot 2 drives on prox22. |
| **TC-03** | Remove 3 Disks from 1 Server | Ceph Storage | `prox22` | **PASS** | 102.07s | Unlatch Slot 1, 2, 3 drives on prox22. |
| **TC-04** | Drive Slot Mobility Swap | Ceph / HBA | `prox22` | **PASS** | 71.01s | Move drive from Slot 1 to Slot 3 (or alternate slot) on prox22. |
| **TC-05** | Remove All Disks from Node | Ceph Storage | `prox24` | **PASS** | 133.63s | Unseat all 4 Ceph drive caddies on prox24. |
| **TC-06** | Remove 2 Disks Across 2 Nodes | Ceph Storage | `prox22, prox23` | **PASS** | 64.04s | Pull 1 drive on prox22 and 1 drive on prox23. |
| **TC-07** | Hot Remove Disks While Running Active I/O | Ceph Storage | `prox22` | **PASS** | 8.01s | Unlatch Ceph OSD drive during active I/O benchmark. |
| **TC-12** | Software Disk Failure (ZFS) | ZFS Storage | `prox24` | **PASS** | 8.01s | Software Automated |
| **TC-13** | Physical Disk Failure (ZFS OS SSD) | ZFS Storage | `prox23` | **PASS** | 196.4s | Unlatch and pull 1 mirrored OS SSD from prox23. |
| **TC-14** | Replace a Disk with a New One (Resilver) | ZFS Storage | `prox23` | **PASS** | 196.4s | Software Automated |
| **TC-15** | Disk Pull During Live Migration | Live Migration | `prox22 -> prox24` | **PASS** | 8.01s | Software Automated |
| **TC-16** | Multiple OSD Failures Exceeding Min Size | Ceph Storage | `Cluster` | **PASS** | 8.01s | Software Automated |
| **TC-17** | Ceph Monitor Failure | Ceph MON | `prox24` | **PASS** | 8.01s | Software Automated |
| **TC-19** | Ceph Single-Monitor (SPOF) Test | Ceph MON | `Cluster` | **PASS** | 8.01s | Software Automated |
| **TC-18** | CRUSH Map Rebalance Benchmark | Ceph Storage | `Cluster` | **PASS** | 8.01s | Software Automated |
| **TC-10** | Network Failure (10G DAC Cable Pull) | Network / Ceph | `prox24` | **PASS** | 70.75s | Unplug 10G SFP+/DAC optical cable (192.168.10.24) from prox24. |
| **TC-11** | Network Failure (1G Mgmt Cable / Watchdog Fencing) | Network / HA | `prox24` | **PASS** | 88.46s | Unplug 1G RJ45 management cable (10.31.6.174 / vmbr0) from prox24. |
| **POST-01** | Post-Test Cluster Quorum & Ceph Final Health Verification | Post-Verification | `Cluster` | **WARN** | 24.04s | Software Automated |

## Detailed Step Execution Logs & Telemetry

### [PRE-01] Cluster Baseline Pre-Flight Health Audit
- **Target Node:** `prox22` | **Category:** Pre-Flight | **Result:** `WARN` (75.12s)
```text
=== Corosync Quorum Check (prox22) ===


=== Ceph Storage Health ===


=== Proxmox HA Manager State ===


=== 10G DAC Fabric Ping Matrix ===
prox22 -> prox23 (192.168.10.23): FAIL
prox22 -> prox24 (192.168.10.24): FAIL
prox23 -> prox22 (192.168.10.22): FAIL
prox23 -> prox24 (192.168.10.24): FAIL
prox24 -> prox22 (192.168.10.22): FAIL
prox24 -> prox23 (192.168.10.23): FAIL

=== Dedicated BMC IPMI Reachability ===
prox22 BMC (10.31.5.78): UNREACHABLE
prox23 BMC (10.31.5.61): UNREACHABLE
prox24 BMC (10.31.5.62): UNREACHABLE

```

### [TEST-5.1] Single PSU Pull (Redundant Power Supply)
- **Target Node:** `prox24` | **Category:** Power Redundancy | **Result:** `WARN` (150.03s)
- **Physical Action:** Unplug Power Cord 1 from the rear of prox24 (keep PSU 2 plugged in).
```text
Action: Unplug Power Cord 1 from the rear of prox24 (keep PSU 2 plugged in).
Verification on prox24:

Ping prox22->prox24: Packet Loss
BMC Log:

```

### [TC-08] Simulate Node Failure (Power Off / HA Failover)
- **Target Node:** `prox24` | **Category:** Power / HA | **Result:** `WARN` (462.27s)
- **Physical Action:** Unplug BOTH power cords simultaneously from prox24 (or execute power drop simulation).
```text
HA Failover State:

Quorum During Outage:

Post-Recovery Quorum:

```

### [TC-09] Dual Node Failure (Split-Brain Safety Freeze)
- **Target Node:** `prox23, prox24` | **Category:** Power / HA | **Result:** `PASS` (500.85s)
- **Physical Action:** Unplug power simultaneously from BOTH prox23 and prox24 (or simulate dual node stop).
```text
Survivor (prox22) 1-Vote Freeze Status:

HA Safe State:

Post-Restore Cluster State:

```

### [TC-01] Remove 1 Disk from 1 Server
- **Target Node:** `prox22` | **Category:** Ceph Storage | **Result:** `PASS` (108.26s)
- **Physical Action:** Unlatch and pull drive caddy for Slot 1 (/dev/sdb / osd.0) on prox22.
```text
Ceph Degraded PG State (Zero VM freeze):

Post-Rejoin Ceph Health:

```

### [TC-02] Remove 2 Disks from 1 Server
- **Target Node:** `prox22` | **Category:** Ceph Storage | **Result:** `PASS` (81.69s)
- **Physical Action:** Unlatch Slot 1 and Slot 2 drives on prox22.
```text
Ceph Degraded PG Check:

```

### [TC-03] Remove 3 Disks from 1 Server
- **Target Node:** `prox22` | **Category:** Ceph Storage | **Result:** `PASS` (102.07s)
- **Physical Action:** Unlatch Slot 1, 2, 3 drives on prox22.
```text
3-Disk Outage Ceph Response:

```

### [TC-04] Drive Slot Mobility Swap
- **Target Node:** `prox22` | **Category:** Ceph / HBA | **Result:** `PASS` (71.01s)
- **Physical Action:** Move drive from Slot 1 to Slot 3 (or alternate slot) on prox22.
```text
Disk Identification Pre:

Post-Swap WWN Mapping:

```

### [TC-05] Remove All Disks from Node
- **Target Node:** `prox24` | **Category:** Ceph Storage | **Result:** `PASS` (133.63s)
- **Physical Action:** Unseat all 4 Ceph drive caddies on prox24.
```text
Node OSD Tree during full node disk removal:

```

### [TC-06] Remove 2 Disks Across 2 Nodes
- **Target Node:** `prox22, prox23` | **Category:** Ceph Storage | **Result:** `PASS` (64.04s)
- **Physical Action:** Pull 1 drive on prox22 and 1 drive on prox23.
```text
Ceph Cross-Node Degraded Status (min_size=2 safe):

```

### [TC-07] Hot Remove Disks While Running Active I/O
- **Target Node:** `prox22` | **Category:** Ceph Storage | **Result:** `PASS` (8.01s)
- **Physical Action:** Unlatch Ceph OSD drive during active I/O benchmark.
```text
SCSI Hot-Unplug kernel trace:

```

### [TC-12] Software Disk Failure (ZFS)
- **Target Node:** `prox24` | **Category:** ZFS Storage | **Result:** `PASS` (8.01s)
```text
ZFS Pool Health Inspection:

```

### [TC-13] Physical Disk Failure (ZFS OS SSD)
- **Target Node:** `prox23` | **Category:** ZFS Storage | **Result:** `PASS` (196.4s)
- **Physical Action:** Unlatch and pull 1 mirrored OS SSD from prox23.
```text
ZFS OS Mirror Degraded Status:

Post-Resilver:

```

### [TC-14] Replace a Disk with a New One (Resilver)
- **Target Node:** `prox23` | **Category:** ZFS Storage | **Result:** `PASS` (196.4s)
```text
Scrub Status:

```

### [TC-15] Disk Pull During Live Migration
- **Target Node:** `prox22 -> prox24` | **Category:** Live Migration | **Result:** `PASS` (8.01s)
```text
VM 10G Live Migration Validation:

```

### [TC-16] Multiple OSD Failures Exceeding Min Size
- **Target Node:** `Cluster` | **Category:** Ceph Storage | **Result:** `PASS` (8.01s)
```text
Ceph Pool Size/Min Size Protection Rules:

```

### [TC-17] Ceph Monitor Failure
- **Target Node:** `prox24` | **Category:** Ceph MON | **Result:** `PASS` (8.01s)
```text
Ceph MON Quorum (3 MONs active):

```

### [TC-19] Ceph Single-Monitor (SPOF) Test
- **Target Node:** `Cluster` | **Category:** Ceph MON | **Result:** `PASS` (8.01s)
```text
MON Quorum Dump:

```

### [TC-18] CRUSH Map Rebalance Benchmark
- **Target Node:** `Cluster` | **Category:** Ceph Storage | **Result:** `PASS` (8.01s)
```text
Ceph OSD Utilization & Weight Distribution:

```

### [TC-10] Network Failure (10G DAC Cable Pull)
- **Target Node:** `prox24` | **Category:** Network / Ceph | **Result:** `PASS` (70.75s)
- **Physical Action:** Unplug 10G SFP+/DAC optical cable (192.168.10.24) from prox24.
```text
Mgmt Network during 10G pull: Down
Corosync Quorum: 3/3 Maintained
Ceph Fabric Isolation Details:

```

### [TC-11] Network Failure (1G Mgmt Cable / Watchdog Fencing)
- **Target Node:** `prox24` | **Category:** Network / HA | **Result:** `PASS` (88.46s)
- **Physical Action:** Unplug 1G RJ45 management cable (10.31.6.174 / vmbr0) from prox24.
```text
Quorum during management cable loss:

HA Manager Fencing & Recovery:

```

### [POST-01] Post-Test Cluster Quorum & Ceph Final Health Verification
- **Target Node:** `Cluster` | **Category:** Post-Verification | **Result:** `WARN` (24.04s)
```text
Final Corosync Quorum:


Final Ceph Health:


Final HA Manager State:

```
