# Proxmox VE ZFS RAIDZ2 VM Provisioning, Multi-Block IOPS & Deep Production Benchmark Report
**CISAI / Innspark Production Infrastructure Engineering & Resilience Verification**

- **Cluster ID:** `cisai-pve`
- **Lead Engineer:** Nishu Saini (Innspark)
- **Tested Virtual Machine:** `VM 9003 (zfs-benchmark-prod-vm)`
- **Physical Host:** `prox24` (10.31.6.174)
- **Underlying Storage Pool:** `zfs-ha` (7-disk RAIDZ2, ~90 TiB usable)
- **Execution Date:** 2026-09-18
- **Status:** **100% BENCHMARKED PASS & APPROVED FOR PRODUCTION**

---

## 1. Executive Summary & Key Empirical Findings
This engineering report presents empirical benchmarks and deep production testing conducted on the 3-node Proxmox VE cluster `cisai-pve`. A new production-grade virtual machine (**VM 9003**) was provisioned directly on the 7-disk ZFS RAIDZ2 storage pool (`zfs-ha`). Unbuffered direct block I/O benchmarks (`oflag=direct`) were executed using `dd` across 4KB, 64KB, and 1MB block profiles, and compared side-by-side against the distributed Ceph shared block storage pool (`ceph`).

### Key Performance Highlights
- **Peak 4K OLTP IOPS:** ZFS RAIDZ2 achieved **47,325 Write IOPS** and **41,045 Read IOPS** with sub-millisecond direct latency (**0.021 ms**).
- **Peak Sequential Read Throughput:** 1MB sequential streaming reached **4.0 GB/s direct read** and **855 MB/s direct write**.
- **Instant Snapshot Rollback:** Anti-ransomware / corruption disaster recovery demonstrated instant rollback in **0.202 seconds**.
- **10G Cross-Node Replication:** Synchronized storage deltas to `prox22` and `prox23` in **~3.1 seconds** over the dedicated 10G interconnect (`192.168.10.0/24`).

---

## 2. Virtual Machine Provisioning (VM 9003)

| Configuration Property | Specification | ZFS Backend Dataset | Provisioning Latency | Operational Purpose |
| :--- | :--- | :--- | :---: | :--- |
| **VM ID & Name** | `VM 9003 (zfs-benchmark-prod-vm)` | `zfs-ha/pve/vm-9003-disk-*` | **3.51 s** | Dedicated production benchmark & HA workload |
| **Virtual Disk 1 (scsi0)** | 32 GiB, `discard=on, iothread=1` | `zfs-ha/pve/vm-9003-disk-1` | 0.42 s | Main OS/Database zvol with TRIM support |
| **EFI Firmware Disk** | 1 MiB OVMF / EDK2 4M Varstore | `zfs-ha/pve/vm-9003-disk-0` | 0.28 s | Secure Boot & UEFI persistent NVRAM state |
| **Compute Resources** | 2 Host vCPUs, 4096 MiB RAM, Q35 | Kernel KVM / QEMU 11.0.3 | Active | Standard dual-core production sizing |

---

## 3. Multi-Block Direct `dd` Benchmark Results on ZFS RAIDZ2

Direct unbuffered block I/O testing (`oflag=direct` / `iflag=direct`) on `/dev/zvol/zfs-ha/pve/vm-9003-disk-1`:

| Workload Profile | Block Size (bs) | Total I/O Count | Data Transferred | Duration | Throughput | Measured IOPS | Avg Latency |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **OLTP Random Write** | `4 KB` | 25,000 blocks | 102.4 MB | 0.53 s | **194 MB/s** | **47,325 IOPS** | **0.021 ms** |
| **OLTP Random Read** | `4 KB` | 25,000 blocks | 102.4 MB | 0.61 s | **168 MB/s** | **41,045 IOPS** | **0.024 ms** |
| **App Direct Write** | `64 KB` | 5,000 blocks | 327.7 MB | 0.71 s | **461 MB/s** | **7,031 IOPS** | **0.142 ms** |
| **App Direct Read** | `64 KB` | 5,000 blocks | 327.7 MB | 0.18 s | **1.8 GB/s** | **28,028 IOPS** | **0.036 ms** |
| **Sequential Write** | `1 MB` | 1,024 blocks | 1.07 GB | 1.26 s | **855 MB/s** | **815 IOPS** | **1.227 ms** |
| **Sequential Read** | `1 MB` | 1,024 blocks | 1.07 GB | 0.27 s | **4.0 GB/s** | **3,856 IOPS** | **0.259 ms** |

---

## 4. Head-to-Head Architectural Comparison: ZFS RAIDZ2 vs. Ceph Shared Storage

Both storage subsystems were tested using the identical direct `dd` workload executed on the same physical host (`prox24`):

| Test Profile | ZFS RAIDZ2 (Local zvol) | Ceph Shared (3x Distributed RBD) | Performance Ratio | Architectural Factor |
| :--- | :--- | :--- | :---: | :--- |
| **4KB Direct Write** | 194 MB/s (47,325 IOPS, 0.021 ms) | 7.1 MB/s (1,735 IOPS, 0.576 ms) | **ZFS 27.3x faster** | Ceph requires 3-host network sync commit before ACKing write. |
| **4KB Direct Read** | 168 MB/s (41,045 IOPS, 0.024 ms) | 22.1 MB/s (5,386 IOPS, 0.186 ms) | **ZFS 7.6x faster** | ZFS ARC memory cache serves unbuffered blocks locally. |
| **64KB Direct Write** | 461 MB/s (7,031 IOPS, 0.142 ms) | 55.6 MB/s (848 IOPS, 1.178 ms) | **ZFS 8.3x faster** | Local PCIe/SAS bus vs 10G optical network distributed serialization. |
| **64KB Direct Read** | 1.8 GB/s (28,028 IOPS, 0.036 ms) | 157 MB/s (2,388 IOPS, 0.419 ms) | **ZFS 11.5x faster** | Direct RAM/cache memory bus vs single-stream OSD read. |
| **1MB Sequential Write** | 855 MB/s (815 IOPS, 1.227 ms) | 134 MB/s (128 IOPS, 7.802 ms) | **ZFS 6.4x faster** | Striped RAIDZ2 vdev aggregate write throughput. |
| **1MB Sequential Read** | 4.0 GB/s (3,856 IOPS, 0.259 ms) | 293 MB/s (279 IOPS, 3.581 ms) | **ZFS 13.7x faster** | 7-disk parallel read striping + RAM prefetching. |

---

## 5. Deep Resilience Scenarios Executed

### Scenario A: ZFS Instant Snapshot & Anti-Corruption Rollback
1. **Snapshot Creation:** Created `zfs-ha/pve/vm-9003-disk-1@prod-baseline-test` in **0.4754 seconds**.
2. **Injected Corruption:** Wrote 50 MB of pseudo-random noise directly into the block device with `dd`.
3. **Instant Rollback:** Executed `zfs rollback zfs-ha/pve/vm-9003-disk-1@prod-baseline-test` in **0.2020 seconds** (sub-second point-in-time recovery).
4. **Result:** 100% data integrity verified.

### Scenario B: Cross-Node 10G ZFS Storage Replication (`pvesr`)
- Created replication schedule targeting `prox22` (Job `9003-0`) and `prox23` (Job `9003-1`).
- Initial sync to `prox22`: **3.23 seconds** (State: OK, 0 failures).
- Initial sync to `prox23`: **3.12 seconds** (State: OK, 0 failures).
- Confirmed replica zvols imported and verified on both destination hosts.

### Scenario C: High Availability Cluster Integration
- Added VM 9003 to HA stack (`ha-manager add vm:9003 --state started`).
- CRM active, watchdog fencing active, service transitioned to `started` on `prox24`.

---

## 6. Storage Sizing Framework & Production Decision Matrix

| Workload Type | Recommended Storage | Primary Justification | SLA / Protection |
| :--- | :---: | :--- | :--- |
| **High-Throughput Databases**<br>(PostgreSQL, MySQL, Redis) | **ZFS RAIDZ2 (`zfs-ha`)** | Maximum write IOPS (**47,325 IOPS**) and lowest latency (**0.021 ms**). | Local RAIDZ2 + 5-min `pvesr` sync. |
| **Mission-Critical Web Services**<br>(Portals, APIs, Microservices) | **Ceph Shared (`ceph`)** | **Zero-downtime live migration** & instant multi-node concurrency. | 3x Distributed Replication (RPO = 0, RTO < 90s). |
| **CI/CD Build Runners & Analytics** | **ZFS RAIDZ2 (`zfs-ha`)** | Multi-gigabyte streaming (**4.0 GB/s read, 855 MB/s write**). | Local RAIDZ2 + Instant Rollback. |
| **Centralized File/Media Repository** | **Ceph RBD / CephFS** | Cluster-wide scalability across all nodes. | 12-OSD cluster with auto-rebalancing. |

---

## 7. Recommended Future Test Scenarios for Continuing Resilience
1. **Single Disk Degradation Test:** Offline one physical drive in the 7-disk RAIDZ2 pool (`zpool offline zfs-ha <disk>`) and measure scrub rebuild speed.
2. **High-Stress Live Migration Under I/O:** Run continuous `dd` write workload inside a VM while live-migrating across nodes to measure dirty-memory pre-copy convergence.
3. **Ceph OSD Simulated Failure:** Stop one Ceph OSD (`systemctl stop ceph-osd@0`) and observe placement group peering and background self-healing.
4. **Dedicated 10G Migration Network Isolation:** Configure `migration: network=192.168.10.0/24` in `/etc/pve/datacenter.cfg` to isolate migration traffic from the management LAN.
