import re
from typing import Dict, Any, List
from .ssh_client import ProxmoxSSHClient

class NetworkHealthTest:
    def __init__(self, ssh_client: ProxmoxSSHClient, config: Dict[str, Any]):
        self.ssh = ssh_client
        self.config = config
        self.nodes = config.get("nodes", [])
        self.thresholds = config.get("thresholds", {})

    def _parse_ping(self, ping_output: str) -> Dict[str, float]:
        """
        Extract packet loss and average rtt from ping output.
        """
        res = {"loss": 100.0, "avg_rtt": 999.0}
        loss_match = re.search(r"(\d+(?:\.\d+)?)%\s+packet\s+loss", ping_output)
        if loss_match:
            res["loss"] = float(loss_match.group(1))

        rtt_match = re.search(r"rtt\s+min/avg/max/mdev\s+=\s+[\d\.]+/([\d\.]+)/", ping_output)
        if rtt_match:
            res["avg_rtt"] = float(rtt_match.group(1))
        return res

    def run(self) -> Dict[str, Any]:
        results = {
            "test_name": "Inter-Node Network Latency & Connectivity Matrix",
            "passed": True,
            "checks": [],
            "latency_matrix": {
                "management": {},
                "cluster_ceph": {}
            }
        }

        max_mgmt_lat = self.thresholds.get("max_mgmt_latency_ms", 5.0)
        max_cluster_lat = self.thresholds.get("max_cluster_latency_ms", 1.5)

        for src in self.nodes:
            src_name = src["name"]
            results["latency_matrix"]["management"][src_name] = {}
            results["latency_matrix"]["cluster_ceph"][src_name] = {}

            for dst in self.nodes:
                dst_name = dst["name"]
                if src_name == dst_name:
                    continue

                # 1. Ping Management IP
                mgmt_ip = dst["mgmt_ip"]
                code, out, err = self.ssh.run_cmd(src_name, f"ping -c 3 -W 2 {mgmt_ip}")
                stats = self._parse_ping(out)
                results["latency_matrix"]["management"][src_name][dst_name] = stats

                mgmt_ok = (code == 0 and stats["loss"] == 0.0 and stats["avg_rtt"] <= max_mgmt_lat)
                results["checks"].append({
                    "name": f"Mgmt Ping: {src_name} -> {dst_name} ({mgmt_ip})",
                    "status": "PASS" if mgmt_ok else "FAIL",
                    "details": f"Loss: {stats['loss']}%, Avg RTT: {stats['avg_rtt']} ms (Threshold: <= {max_mgmt_lat} ms)"
                })
                if not mgmt_ok:
                    results["passed"] = False

                # 2. Ping Cluster / Ceph Network IP
                cluster_ip = dst["cluster_ip"]
                code, out, err = self.ssh.run_cmd(src_name, f"ping -c 3 -W 2 {cluster_ip}")
                stats = self._parse_ping(out)
                results["latency_matrix"]["cluster_ceph"][src_name][dst_name] = stats

                cluster_ok = (code == 0 and stats["loss"] == 0.0 and stats["avg_rtt"] <= max_cluster_lat)
                results["checks"].append({
                    "name": f"Ceph Ping: {src_name} -> {dst_name} ({cluster_ip})",
                    "status": "PASS" if cluster_ok else "FAIL",
                    "details": f"Loss: {stats['loss']}%, Avg RTT: {stats['avg_rtt']} ms (Threshold: <= {max_cluster_lat} ms)"
                })
                if not cluster_ok:
                    results["passed"] = False

        return results
