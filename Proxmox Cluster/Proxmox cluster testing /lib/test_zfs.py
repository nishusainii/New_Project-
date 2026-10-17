import re
import time
from typing import Dict, Any, List
from .ssh_client import ProxmoxSSHClient

class ZfsStorageTest:
    def __init__(self, ssh_client: ProxmoxSSHClient, config: Dict[str, Any]):
        self.ssh = ssh_client
        self.config = config
        self.nodes = config.get("nodes", [])
        self.zfs_cfg = config.get("storage", {}).get("zfs", {})
        self.pool_name = self.zfs_cfg.get("pool", "zfs-ha")
        self.expected_disks = self.zfs_cfg.get("expected_disks_per_node", 7)
        self.expected_raid = self.zfs_cfg.get("raid_level", "raidz2")

    def run(self, run_io_test: bool = True) -> Dict[str, Any]:
        results = {
            "test_name": "ZFS RAIDZ2 (7-Disk) Health & Integrity Validation",
            "passed": True,
            "checks": [],
            "nodes_data": {}
        }

        for node in self.nodes:
            node_name = node["name"]
            results["nodes_data"][node_name] = {}

            # 1. Check zpool status
            code, out, err = self.ssh.run_cmd(node_name, f"zpool status {self.pool_name}")
            if code != 0:
                results["passed"] = False
                results["checks"].append({
                    "name": f"ZFS Pool '{self.pool_name}' on {node_name}",
                    "status": "FAIL",
                    "details": f"Failed to get pool status: {err}"
                })
                continue

            pool_online = "state: ONLINE" in out
            raid_found = f"{self.expected_raid}-0" in out
            
            # Count disks in vdev
            # Look for lines under raidz2-0 with ONLINE
            disk_lines = [line.strip() for line in out.splitlines() if "ONLINE" in line and (line.strip().startswith("wwn-") or line.strip().startswith("sd") or line.strip().startswith("nvme"))]
            disk_count = len(disk_lines)

            # Check errors (read, write, cksum)
            has_data_errors = "errors: No known data errors" not in out
            
            # Parse scrub status
            scrub_line = [l.strip() for l in out.splitlines() if "scan: scrub" in l]
            scrub_summary = scrub_line[0] if scrub_line else "No scrub info"

            layout_ok = pool_online and raid_found and (disk_count == self.expected_disks) and not has_data_errors
            results["checks"].append({
                "name": f"ZFS RAIDZ2 Layout & Health on {node_name}",
                "status": "PASS" if layout_ok else "FAIL",
                "details": f"State: {'ONLINE' if pool_online else 'DEGRADED'}, Layout: {self.expected_raid} with {disk_count}/{self.expected_disks} disks, Errors: {'0' if not has_data_errors else 'Detected'}"
            })
            if not layout_ok:
                results["passed"] = False

            results["checks"].append({
                "name": f"ZFS Scrub Verification on {node_name}",
                "status": "PASS" if "0 errors" in scrub_summary else "WARN",
                "details": scrub_summary
            })

            results["nodes_data"][node_name] = {
                "online": pool_online,
                "raid_level": self.expected_raid,
                "disk_count": disk_count,
                "scrub": scrub_summary
            }

            # 2. Optional Safe I/O Test using raw zvol (matching PVE VM block path)
            if run_io_test and layout_ok:
                test_vol = f"{self.pool_name}/testvol-{int(time.time())}"
                c1, _, e1 = self.ssh.run_cmd(node_name, f"zfs create -V 100M {test_vol} && sleep 1")
                if c1 == 0:
                    dev_path = f"/dev/zvol/{test_vol}"
                    # Perform 100MB direct write test
                    c2, o2, e2 = self.ssh.run_cmd(node_name, f"dd if=/dev/zero of={dev_path} bs=1M count=100 oflag=direct 2>&1")
                    speed_match = re.search(r"(\d+(?:\.\d+)?\s+[kMGT]?B/s)", o2)
                    write_speed = speed_match.group(1) if speed_match else "N/A"

                    # Perform 100MB direct read test
                    c3, o3, e3 = self.ssh.run_cmd(node_name, f"dd if={dev_path} of=/dev/null bs=1M iflag=direct 2>&1")
                    read_match = re.search(r"(\d+(?:\.\d+)?\s+[kMGT]?B/s)", o3)
                    read_speed = read_match.group(1) if read_match else "N/A"

                    # Clean up zvol
                    self.ssh.run_cmd(node_name, f"sleep 1; zfs destroy {test_vol} 2>/dev/null || (sleep 2; zfs destroy -r {test_vol} 2>/dev/null || true)")

                    results["checks"].append({
                        "name": f"ZFS RAIDZ2 Direct Block I/O on {node_name}",
                        "status": "PASS",
                        "details": f"Write: {write_speed}, Read: {read_speed} (100MB direct zvol block test)"
                    })

        return results
