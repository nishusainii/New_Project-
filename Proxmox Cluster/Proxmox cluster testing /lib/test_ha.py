import re
from typing import Dict, Any, List
from .ssh_client import ProxmoxSSHClient

class HighAvailabilityTest:
    def __init__(self, ssh_client: ProxmoxSSHClient, config: Dict[str, Any]):
        self.ssh = ssh_client
        self.config = config
        self.leader = config.get("cluster", {}).get("leader_node", "prox24")
        self.nodes = [n["name"] for n in config.get("nodes", [])]

    def run(self) -> Dict[str, Any]:
        results = {
            "test_name": "Proxmox High Availability (HA) Manager & Watchdog Validation",
            "passed": True,
            "checks": [],
            "ha_status": {}
        }

        # 1. Query ha-manager status
        code, out, err = self.ssh.run_cmd(self.leader, "ha-manager status")
        if code != 0:
            results["passed"] = False
            results["checks"].append({
                "name": "HA Manager Status",
                "status": "FAIL",
                "details": f"Failed to retrieve ha-manager status: {err}"
            })
            return results

        # 2. Check HA Quorum
        quorum_ok = "quorum OK" in out
        results["checks"].append({
            "name": "HA Quorum",
            "status": "PASS" if quorum_ok else "FAIL",
            "details": "HA cluster is quorate" if quorum_ok else "HA cluster is not quorate!"
        })
        if not quorum_ok:
            results["passed"] = False

        # 3. Check CRM Master
        master_match = re.search(r"master\s+(\S+)\s+\(active", out)
        master_node = master_match.group(1) if master_match else "None"
        master_ok = master_node in self.nodes
        results["checks"].append({
            "name": "Cluster Resource Manager (CRM) Master",
            "status": "PASS" if master_ok else "FAIL",
            "details": f"Active CRM Master: {master_node}"
        })
        if not master_ok:
            results["passed"] = False

        # 4. Check Watchdog & Fencing
        fencing_ok = "fencing armed (CRM watchdog active)" in out
        results["checks"].append({
            "name": "Hardware Watchdog & Fencing Guard",
            "status": "PASS" if fencing_ok else "WARN",
            "details": "Watchdog fencing armed and protecting nodes" if fencing_ok else "Watchdog fencing state degraded"
        })

        # 5. Check Local Resource Managers (LRMs) on all nodes
        lrm_nodes = re.findall(r"lrm\s+(\S+)\s+\(([^,\)]+)", out)
        active_lrms = [node for node, state in lrm_nodes if state.strip() in ["active", "idle"]]
        all_lrms_ok = len(active_lrms) >= len(self.nodes)
        results["checks"].append({
            "name": "Local Resource Managers (LRM)",
            "status": "PASS" if all_lrms_ok else "FAIL",
            "details": f"Active LRMs: {', '.join(active_lrms)} ({len(active_lrms)}/{len(self.nodes)} nodes)"
        })
        if not all_lrms_ok:
            results["passed"] = False

        # 6. Check HA Services for Error Flags
        service_lines = [l.strip() for l in out.splitlines() if l.strip().startswith("service ")]
        error_services = [l for l in service_lines if "error" in l]
        services_ok = len(error_services) == 0
        results["checks"].append({
            "name": "HA Service States",
            "status": "PASS" if services_ok else "FAIL",
            "details": f"All {len(service_lines)} HA services clean" if services_ok else f"Services in ERROR state: {', '.join(error_services)}"
        })
        if not services_ok:
            results["passed"] = False

        results["ha_status"] = {
            "quorum": quorum_ok,
            "master": master_node,
            "fencing": fencing_ok,
            "services": service_lines
        }

        return results
