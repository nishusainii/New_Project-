# Proxmox VE Cluster Physical Testing & 19-Scenario Runbook Report
**Cluster Name:** `cisai-pve` | **Execution Date:** 2026-09-24 19:28:11 | **Pass Rate:** 1/1 (100.0%)

## Cluster Node Topology & IPs
| Node Name | Node ID | Management IP | 10G Fabric IP | Dedicated BMC IP | Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `prox22` | 2 | `10.31.6.172` | `192.168.10.22` | `10.31.5.78` | CRM Master Leader |
| `prox23` | 3 | `10.31.6.173` | `192.168.10.23` | `10.31.5.61` | Member Node |
| `prox24` | 1 | `10.31.6.174` | `192.168.10.24` | `10.31.5.62` | Member Node |

## Master 19-Scenario & Physical Test Execution Summary

| TC ID | Test Description | Category | Target Node | Status | Duration | Physical Action Performed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PRE-01** | Cluster Baseline Pre-Flight Health Audit | Pre-Flight | `prox22` | **PASS** | 7.44s | Software Automated |

## Detailed Step Execution Logs & Telemetry

### [PRE-01] Cluster Baseline Pre-Flight Health Audit
- **Target Node:** `prox22` | **Category:** Pre-Flight | **Result:** `PASS` (7.44s)
```text
=== Corosync Quorum Check (prox22) ===
Cluster information
-------------------
Name:             cisai-pve
Config Version:   4
Transport:        knet
Secure auth:      on

Quorum information
------------------
Date:             Thu Sep 24 19:28:04 2026
Quorum provider:  corosync_votequorum
Nodes:            3
Node ID:          0x00000002
Ring ID:          1.c7
Quorate:          Yes

Votequorum information
----------------------
Expected votes:   3
Highest expected: 3
Total votes:      3
Quorum:           2  
Flags:            Quorate 

Membership information
----------------------
    Nodeid      Votes Name
0x00000001          1 10.31.6.174
0x00000002          1 10.31.6.172 (local)
0x00000003          1 10.31.6.173

=== Ceph Storage Health ===
cluster:
    id:     bcddd50d-c91b-4f6c-b255-19c78e15564f
    health: HEALTH_OK
 
  services:
    mon: 3 daemons, quorum prox24,prox23,prox22 (age 2h) [leader: prox24]
    mgr: prox24(active, since 2h), standbys: prox23, prox22
    osd: 12 osds: 12 up (since 2h), 12 in (since 2h)
 
  data:
    pools:   2 pools, 33 pgs
    objects: 2.40k objects, 9.0 GiB
    usage:   28 GiB used, 218 TiB / 218 TiB avail
    pgs:     33 active+clean
 
  io:
    client:   2.3 KiB/s wr, 0 op/s rd, 0 op/s wr

=== Proxmox HA Manager State ===
quorum OK
master prox23 (active, Thu Sep 24 19:28:02 2026)
fencing armed (CRM watchdog active)
lrm prox22 (active, watchdog active, Thu Sep 24 19:27:56 2026)
lrm prox23 (active, watchdog active, Thu Sep 24 19:28:04 2026)
lrm prox24 (active, watchdog active, Thu Sep 24 19:27:56 2026)
service vm:9001 (prox22, started)
service vm:9002 (prox24, started)
service vm:9003 (prox22, started)
service vm:9004 (prox23, started)

=== 10G DAC Fabric Ping Matrix ===
prox22 -> prox23 (192.168.10.23): OK
prox22 -> prox24 (192.168.10.24): OK
prox23 -> prox22 (192.168.10.22): OK
prox23 -> prox24 (192.168.10.24): OK
prox24 -> prox22 (192.168.10.22): OK
prox24 -> prox23 (192.168.10.23): OK

=== Dedicated BMC IPMI Reachability ===
prox22 BMC (10.31.5.78): REACHABLE
prox23 BMC (10.31.5.61): REACHABLE
prox24 BMC (10.31.5.62): REACHABLE

```
