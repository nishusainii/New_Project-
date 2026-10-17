# Proxmox 3-Node Cluster Automated Testing Environment
**Innspark / CISAI Infrastructure Testing Suite**

Comprehensive automated test suite, storage benchmarking toolkit, live migration validator, and reporting dashboard for the 3-Node Proxmox VE cluster.

---

## Cluster Topology & Architecture

- **Cluster Name**: `cisai-pve`
- **Leader Node / CRM Master**: `prox22` (`10.31.6.172`)
- **Member Nodes**: `prox24` (`10.31.6.174`), `prox23` (`10.31.6.173`)
- **Cluster Networks**:
  - **Management Network**: `10.31.6.0/22` via `vmbr0`
  - **Ceph & Cluster Interconnect**: `192.168.10.0/24` via `nic3` (10G optical link, latency < 0.08 ms)
- **Storage Subsystems**:
  - **Ceph Shared Storage**: 12 OSDs total (4 disks per server x 3 servers, ~218 TiB raw, 3x replication pool `ceph`)
  - **ZFS RAIDZ2 Storage**: 7 disks per server in RAIDZ2 (`zfs-ha`, ~90 TiB usable per node, with `pvesr` replication)
- **High Availability**: Hardware watchdog fencing armed, CRM Master on `prox22`, active LRMs across all 3 nodes.
- **Validation Workloads**:
  - **VM 9001** (`ha-test-ceph-ubuntu2204`): Tests Ceph shared block storage and 3-node live migration.
  - **VM 9002** (`zfs-test-prox24-ubuntu2204`): Tests ZFS RAIDZ2 local storage and cross-node ZFS replication.

---

## Quick Start

### 1. Requirements
Ensure Python 3 and PyYAML are available:
```bash
pip install -r requirements.txt
```

### 2. Run All Automated Tests
To run the full suite across all 3 nodes:
```bash
python3 run_tests.py --all
```

### 3. Run Specific Test Suites
You can run targeted test suites individually:
```bash
# Verify Corosync quorum and PVE system services
python3 run_tests.py --test cluster

# Test 12-path inter-node latency & packet loss matrix
python3 run_tests.py --test network

# Test Ceph 4-disk OSD distribution and I/O benchmark
python3 run_tests.py --test ceph

# Test ZFS 7-disk RAIDZ2 integrity, scrub status, and direct block I/O
python3 run_tests.py --test zfs

# Test HA manager, CRM master, LRMs, and watchdog status
python3 run_tests.py --test ha

# Test VM Live Migration on Ceph and ZFS replication sync
python3 run_tests.py --test migration
```

### 4. Fast Check (Skip Benchmarks / Migration)
```bash
python3 run_tests.py --all --skip-benchmark --skip-migration
```

---

## Reporting & Dashboard

Every test execution automatically generates:
1. **Markdown Report**: Saved in `reports/test_report_<timestamp>.md`
2. **Latest JSON Data**: Saved in `reports/test_report_latest.json`
3. **Interactive Web Dashboard**: `web/index.html` (backed by `web/data.json`)

To view the dashboard in your browser:
```bash
python3 -m http.server 8081 --directory web
```
Then open `http://localhost:8081` in your browser. (If 8081 is in use, you can pick any free port such as 8000 or 8888).

---

## Directory Structure

```
├── config.yaml          # Cluster IP definitions, storage layout & thresholds
├── requirements.txt     # Python requirements
├── run_tests.py         # Master CLI runner and orchestrator
├── README.md            # Documentation and operational guide
├── lib/
│   ├── ssh_client.py    # Multi-node SSH communication engine
│   ├── test_cluster.py  # Quorum and PVE service validator
│   ├── test_network.py  # Dual-subnet ping latency matrix
│   ├── test_ceph.py     # 4-disk Ceph OSD & benchmark validator
│   ├── test_zfs.py      # 7-disk RAIDZ2 integrity & block I/O validator
│   ├── test_migration.py# 3-node live migration & replication validator
│   └── test_ha.py       # High Availability & watchdog fencing validator
├── reports/             # Generated test execution logs & reports
└── web/
    ├── index.html       # Dark-mode dashboard UI
    ├── styles.css       # Visual styles & tokens
    └── data.json        # Live test data feeding the dashboard
```
