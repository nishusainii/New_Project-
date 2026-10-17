# Proxmox VE Datacenter Physical Testing & 19-Scenario Runbook Suite

This testing suite executes and verifies all test cases and physical datacenter procedures defined in [Proxmox_Datacenter_Physical_Testing_Checklist.pdf](file:///home/nishusaini/Desktop/Innspark/Proxmox%20Cluster/Proxmox_Datacenter_Physical_Testing_Checklist.pdf) across the 3 cluster nodes:

| Node Name | Node ID | Management IP | 10G DAC Storage IP | Dedicated BMC IP | Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`prox22`** | 2 | `10.31.6.172` | `192.168.10.22` | `10.31.5.78` | **CRM Master Leader** |
| **`prox23`** | 3 | `10.31.6.173` | `192.168.10.23` | `10.31.5.61` | **Member Node** |
| **`prox24`** | 1 | `10.31.6.174` | `192.168.10.24` | `10.31.5.62` | **Member Node** |

---

## 🚀 Available Scripts

### 1. Master Python Test Runner (`proxmox_physical_testing_suite.py`)
Provides real-time interactive prompts, live command execution, telemetry capture, and automatic generation of HTML, Markdown, and JSON test reports.

```bash
cd "/home/nishusaini/Desktop/Innspark/Proxmox Cluster/Testing"

# 1. Physical Datacenter Mode (Interactive with rack action prompts)
python3 proxmox_physical_testing_suite.py --interactive

# 2. Automated Simulation Mode (Non-interactive software fault simulation)
python3 proxmox_physical_testing_suite.py --auto

# 3. Pre-Flight Baseline Audit Only
python3 proxmox_physical_testing_suite.py --preflight

# 4. Run Specific Category (power | storage | network | preflight)
python3 proxmox_physical_testing_suite.py --category power
```

### 2. Standalone Bash Test Suite (`proxmox_physical_testing_suite.sh`)
Native bash script requiring zero python dependencies, perfect for direct execution from any Proxmox shell or laptop terminal:

```bash
cd "/home/nishusaini/Desktop/Innspark/Proxmox Cluster/Testing"
./proxmox_physical_testing_suite.sh
```

---

## 📋 19-Scenario & Physical Test Coverage Matrix

1. **Pre-Flight Inspection**: Corosync Quorum (3/3 votes), Ceph baseline (12 OSDs, 3 MONs), 10G DAC Fabric Latency, BMC IPMI reachability.
2. **Power & High Availability (Phase 2)**:
   - `Test 5.1`: Single PSU Power Cord Pull (Zero downtime, 0% packet drop)
   - `TC-08`: Hard Node Power Drop on `prox24` (Automated HA VM failover in 60–120s)
   - `TC-09`: Dual-Node Power Drop (`prox23` + `prox24` down, survivor `prox22` 1-vote split-brain safety freeze)
3. **Storage Hot-Swap & Resilience (Phase 3)**:
   - `TC-01`: Remove 1 Disk from 1 Server (`prox22` Slot 1 `/dev/sdb` -> `osd.0`)
   - `TC-02`: Remove 2 Disks from 1 Server (`prox22` Slot 1 & 2)
   - `TC-03`: Remove 3 Disks from 1 Server (`prox22` Slot 1, 2, 3)
   - `TC-04`: Drive Slot Mobility Swap (Slot 1 -> Slot 3 WWN IT-mode dynamic rebind)
   - `TC-05`: Remove All Disks from 1 Node (`prox24` all 4 Ceph drives)
   - `TC-06`: Remove 2 Disks Across 2 Nodes (`prox22` + `prox23`, min_size=2 safety)
   - `TC-07`: Hot Remove Disks While Running Active I/O Benchmark (`fio`/`rbd`)
   - `TC-12`: Software Disk Failure (ZFS degraded pool performance under direct I/O write)
   - `TC-13`: Physical ZFS OS Boot Mirror SSD Pull on `prox23` (`rpool` DEGRADED, host up)
   - `TC-14`: Replace/Re-insert SSD with New One & ZFS Resilver Scrub
   - `TC-15`: Disk Pull During Live 10G RAM VM Migration (`qm migrate 9001 prox24 --online 1`)
   - `TC-16`: Multiple OSD Failures Exceeding Min Size (`min_size` safety)
   - `TC-17`: Ceph Monitor Failure (`systemctl stop ceph-mon@prox24`, MON quorum 2/3)
   - `TC-18`: CRUSH Map Rebalance Benchmark (Backfill throttling)
   - `TC-19`: Ceph Single-Monitor SPOF Test (3-MON quorum architecture)
4. **Network & Fencing (Phase 4)**:
   - `TC-10`: 10G DAC Storage Cable Pull on `prox24` (Fabric isolation, mgmt intact)
   - `TC-11`: 1G Management Cable Pull on `prox24` (Hardware Watchdog fencing & HA failover)
5. **Post-Test Verification (Phase 5)**: Cluster quorum 3/3 votes restore, Ceph 12 OSDs healthy, HA Manager active.
