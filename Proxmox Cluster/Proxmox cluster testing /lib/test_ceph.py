import json
import time
from typing import Dict, Any, List
from .ssh_client import ProxmoxSSHClient

class CephStorageTest:
    def __init__(self, ssh_client: ProxmoxSSHClient, config: Dict[str, Any]):
        self.ssh = ssh_client
        self.config = config
        self.leader = config.get("cluster", {}).get("leader_node", "prox24")
        self.ceph_cfg = config.get("storage", {}).get("ceph", {})
        self.expected_osds = self.ceph_cfg.get("expected_total_osds", 12)
        self.expected_mons = self.ceph_cfg.get("min_quorum_mons", 3)

    def run(self, run_benchmark: bool = True) -> Dict[str, Any]:
        results = {
            "test_name": "Ceph Storage Cluster Health & 4-Disk OSD Validation",
            "passed": True,
            "checks": [],
            "ceph_details": {},
            "benchmark": {}
        }

        # 1. Ceph Cluster Status
        code, ceph_status, err = self.ssh.run_cmd_json(self.leader, "ceph status -f json")
        if code != 0 or not ceph_status:
            results["passed"] = False
            results["checks"].append({
                "name": "Ceph Cluster Status",
                "status": "FAIL",
                "details": f"Failed to retrieve ceph status: {err}"
            })
            return results

        overall_health = ceph_status.get("health", {}).get("status", "UNKNOWN")
        health_ok = overall_health == "HEALTH_OK"
        results["checks"].append({
            "name": "Ceph Cluster Health",
            "status": "PASS" if health_ok else "WARN",
            "details": f"Cluster health is {overall_health}"
        })
        if overall_health == "HEALTH_ERR":
            results["passed"] = False

        # 2. Monitor Quorum Check
        monmap = ceph_status.get("monmap", {})
        mons_in_quorum = ceph_status.get("quorum_names", [])
        mon_ok = len(mons_in_quorum) >= self.expected_mons
        results["checks"].append({
            "name": "Ceph Monitor Quorum",
            "status": "PASS" if mon_ok else "FAIL",
            "details": f"Active Monitors: {', '.join(mons_in_quorum)} (Expected >= {self.expected_mons})"
        })
        if not mon_ok:
            results["passed"] = False

        # 3. OSD Status (12 OSDs: 4 per server across 3 nodes)
        osdmap = ceph_status.get("osdmap", {})
        num_osds = osdmap.get("num_osds", 0)
        num_up = osdmap.get("num_up_osds", 0)
        num_in = osdmap.get("num_in_osds", 0)

        osd_ok = (num_osds == self.expected_osds and num_up == self.expected_osds and num_in == self.expected_osds)
        results["checks"].append({
            "name": f"Ceph OSD Health ({self.expected_osds} Disks / 4 per Node)",
            "status": "PASS" if osd_ok else "FAIL",
            "details": f"Total: {num_osds}, Up: {num_up}, In: {num_in} (Expected {self.expected_osds})"
        })
        if not osd_ok:
            results["passed"] = False

        # 4. PG State Check
        pgmap = ceph_status.get("pgmap", {})
        num_pgs = pgmap.get("num_pgs", 0)
        pgs_by_state = pgmap.get("pgs_by_state", [])
        active_clean_pgs = 0
        degraded_pgs = 0
        for s in pgs_by_state:
            if "active+clean" in s.get("state_name", ""):
                active_clean_pgs += s.get("count", 0)
            elif "degraded" in s.get("state_name", ""):
                degraded_pgs += s.get("count", 0)

        pg_ok = (degraded_pgs == 0 and active_clean_pgs == num_pgs)
        results["checks"].append({
            "name": "Placement Group (PG) States",
            "status": "PASS" if pg_ok else "WARN",
            "details": f"Total PGs: {num_pgs}, Active+Clean: {active_clean_pgs}, Degraded: {degraded_pgs}"
        })
        if degraded_pgs > 0:
            results["passed"] = False

        # 5. OSD Node Distribution Verification
        code, osd_tree, err = self.ssh.run_cmd_json(self.leader, "ceph osd tree -f json")
        node_osds = {}
        if code == 0 and osd_tree:
            nodes_list = osd_tree.get("nodes", [])
            for node in nodes_list:
                if node.get("type") == "host":
                    node_osds[node.get("name")] = node.get("children", [])

            for node_name, osd_ids in node_osds.items():
                count = len(osd_ids)
                results["checks"].append({
                    "name": f"Node {node_name} Ceph Disks",
                    "status": "PASS" if count == 4 else "WARN",
                    "details": f"Assigned {count} OSDs: IDs {osd_ids} (Expected 4 disks)"
                })

        results["ceph_details"] = {
            "health": overall_health,
            "mons": mons_in_quorum,
            "osds": {"total": num_osds, "up": num_up, "in": num_in},
            "pgs": {"total": num_pgs, "clean": active_clean_pgs},
            "distribution": node_osds
        }

        # 6. Optional Safe Ceph Benchmark (rados bench on temporary pool)
        if run_benchmark:
            bench_pool = f"bench-test-{int(time.time())}"
            # Create temporary pool
            c1, o1, e1 = self.ssh.run_cmd(self.leader, f"ceph osd pool create {bench_pool} 16 16 && ceph osd pool application enable {bench_pool} rbd")
            if c1 == 0:
                # Run quick 10-second write benchmark
                c2, o2, e2 = self.ssh.run_cmd(self.leader, f"rados bench -p {bench_pool} 10 write --no-cleanup", timeout=40)
                # Parse write bandwidth
                bw_match = [line for line in o2.splitlines() if "Bandwidth (MB/sec):" in line]
                iops_match = [line for line in o2.splitlines() if "Average IOPS:" in line]
                write_bw = bw_match[0].split(":")[-1].strip() if bw_match else "N/A"
                write_iops = iops_match[0].split(":")[-1].strip() if iops_match else "N/A"

                # Run quick 10-second sequential read benchmark
                c3, o3, e3 = self.ssh.run_cmd(self.leader, f"rados bench -p {bench_pool} 10 seq", timeout=40)
                read_bw_match = [line for line in o3.splitlines() if "Bandwidth (MB/sec):" in line]
                read_bw = read_bw_match[0].split(":")[-1].strip() if read_bw_match else "N/A"

                # Clean up temporary test pool
                self.ssh.run_cmd(self.leader, f"ceph osd pool delete {bench_pool} {bench_pool} --yes-i-really-really-mean-it")

                results["benchmark"] = {
                    "write_bw_mb_s": write_bw,
                    "write_iops": write_iops,
                    "read_bw_mb_s": read_bw
                }
                results["checks"].append({
                    "name": "Ceph Pool I/O Benchmark",
                    "status": "PASS",
                    "details": f"Write: {write_bw} MB/s ({write_iops} IOPS), Sequential Read: {read_bw} MB/s"
                })

        return results
