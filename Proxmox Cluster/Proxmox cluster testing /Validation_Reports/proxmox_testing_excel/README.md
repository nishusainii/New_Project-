# Proxmox Cluster Testing — Excel & Tabular Dataset

This directory contains the formal Microsoft Excel workbook (`.xlsx`) and raw CSV dataset exports for the 3-node **Proxmox VE + Ceph** cluster failure and recovery validation testing.

## Files Included

| File Name | Format | Description |
|---|---|---|
| `Proxmox_Cluster_Validation_Report.xlsx` | **Microsoft Excel** | Comprehensive 6-sheet workbook with full styles, colors, and formatting |
| `01_executive_summary.csv` | CSV | High-level KPIs, cluster metadata, and SLA scorecards |
| `02_cluster_topology.csv` | CSV | Physical hardware inventory, IP allocation, OSD maps, and workloads |
| `03_scenario_01_dual_shutdown.csv` | CSV | Scenario 1: Dual Node Shutdown timeline and telemetry |
| `04_scenario_02_network_isolation.csv` | CSV | Scenario 2: Single Node Network Split timeline and VM failovers |
| `05_scenario_03_ceph_outage.csv` | CSV | Scenario 3: Ceph Storage Network Outage and 28s recovery |
| `06_sla_compliance_matrix.csv` | CSV | 9-point Enterprise SLA compliance matrix (100% PASS) |

## Worksheets in Excel Workbook

1. **`Executive_Summary`**: Overall cluster status, SLA compliance rate, and scenario results.
2. **`Cluster_Topology`**: Node hardware specs, network interfaces (`vmbr0`, `nic3`), and Ceph pool specs.
3. **`Scenario_01_Dual_Shutdown`**: 2-node poweroff timeline, quorum loss behavior, and recovery.
4. **`Scenario_02_Network_Split`**: Single-node network isolation, watchdog fencing, and VM failover.
5. **`Scenario_03_Ceph_Outage`**: Storage mesh failure, client I/O suspension, and 28s recovery.
6. **`SLA_Compliance_Matrix`**: Target vs measured recovery times and production sign-off.
