from typing import Dict, Any, List
from .ssh_client import ProxmoxSSHClient

class ClusterHealthTest:
    def __init__(self, ssh_client: ProxmoxSSHClient, config: Dict[str, Any]):
        self.ssh = ssh_client
        self.config = config
        self.nodes = config.get("nodes", [])
        self.leader = config.get("cluster", {}).get("leader_node", "prox24")

    def run(self) -> Dict[str, Any]:
        results = {
            "test_name": "Cluster Health & Quorum Verification",
            "passed": True,
            "checks": [],
            "summary": {}
        }

        # 1. Check Corosync Quorum on Leader
        code, out, err = self.ssh.run_cmd(self.leader, "pvecm status")
        quorum_ok = (code == 0 and "Quorate:          Yes" in out)
        total_votes = "3" in out
        results["checks"].append({
            "name": "Corosync Quorum Status",
            "node": self.leader,
            "status": "PASS" if quorum_ok else "FAIL",
            "details": "Cluster is quorate with active votequorum" if quorum_ok else f"Quorum check failed: {err or out}"
        })
        if not quorum_ok:
            results["passed"] = False

        # 2. Check Node Membership
        code, out, err = self.ssh.run_cmd(self.leader, "pvecm nodes")
        nodes_found = []
        for n in self.nodes:
            if n["name"] in out or n["mgmt_ip"] in out:
                nodes_found.append(n["name"])
        all_nodes_present = len(nodes_found) == len(self.nodes)
        results["checks"].append({
            "name": "Cluster Membership",
            "node": self.leader,
            "status": "PASS" if all_nodes_present else "FAIL",
            "details": f"Online nodes: {', '.join(nodes_found)} (Expected {len(self.nodes)})"
        })
        if not all_nodes_present:
            results["passed"] = False

        # 3. Check System Services across all nodes
        services = ["pve-cluster", "pvedaemon", "pvestatd", "pveproxy", "corosync"]
        for node in self.nodes:
            node_name = node["name"]
            svc_check_cmd = f"for s in {' '.join(services)}; do echo -n \"$s:\"; systemctl is-active $s; done"
            code, out, err = self.ssh.run_cmd(node_name, svc_check_cmd)
            failed_svcs = []
            if code == 0:
                for line in out.splitlines():
                    if ":" in line:
                        s, state = line.split(":", 1)
                        if state.strip() != "active":
                            failed_svcs.append(f"{s}={state.strip()}")
            else:
                failed_svcs.append(f"Check failed: {err}")

            node_svc_ok = (len(failed_svcs) == 0)
            results["checks"].append({
                "name": f"PVE Core Services on {node_name}",
                "node": node_name,
                "status": "PASS" if node_svc_ok else "FAIL",
                "details": "All core services active" if node_svc_ok else f"Degraded services: {', '.join(failed_svcs)}"
            })
            if not node_svc_ok:
                results["passed"] = False

        # 4. Check Cluster Storage status from API
        code, out, err = self.ssh.run_cmd(self.leader, "pvesm status")
        ceph_active = "ceph" in out and "active" in out
        zfs_active = "zfs-ha" in out and "active" in out
        results["checks"].append({
            "name": "Cluster Storage Mounts",
            "node": self.leader,
            "status": "PASS" if (ceph_active and zfs_active) else "WARN",
            "details": f"Ceph: {'Active' if ceph_active else 'Down'}, ZFS-HA: {'Active' if zfs_active else 'Down'}"
        })

        results["summary"] = {
            "total_nodes": len(self.nodes),
            "quorate": quorum_ok,
            "active_nodes": nodes_found,
            "overall_status": "PASS" if results["passed"] else "FAIL"
        }
        return results
