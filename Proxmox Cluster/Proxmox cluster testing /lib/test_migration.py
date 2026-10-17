import time
from typing import Dict, Any, List
from .ssh_client import ProxmoxSSHClient

class MigrationTest:
    def __init__(self, ssh_client: ProxmoxSSHClient, config: Dict[str, Any]):
        self.ssh = ssh_client
        self.config = config
        self.leader = config.get("cluster", {}).get("leader_node", "prox24")
        self.nodes = [n["name"] for n in config.get("nodes", [])]
        self.vms = config.get("test_vms", [])

    def _get_vm_location(self, vmid: int) -> str:
        code, out, _ = self.ssh.run_cmd(
            self.leader,
            f"pvesh get /cluster/resources --type vm --output-format json"
        )
        if code == 0:
            import json
            try:
                res = json.loads(out)
                for item in res:
                    if int(item.get("vmid", -1)) == vmid:
                        return item.get("node", "")
            except Exception:
                pass
        return ""

    def _get_vm_status(self, node: str, vmid: int) -> str:
        code, out, _ = self.ssh.run_cmd(node, f"qm status {vmid}")
        if code == 0 and "running" in out:
            return "running"
        elif code == 0 and "stopped" in out:
            return "stopped"
        return "unknown"

    def run(self, perform_live_migration: bool = True) -> Dict[str, Any]:
        results = {
            "test_name": "VM Live Migration & Storage Continuity Test",
            "passed": True,
            "checks": [],
            "migrations": []
        }

        # 1. Test Ceph Live Migration (VM 9001)
        ceph_vms = [v for v in self.vms if v.get("storage") == "ceph"]
        if ceph_vms:
            target_vm = ceph_vms[0]
            vmid = target_vm["vmid"]
            vm_name = target_vm["name"]

            current_node = self._get_vm_location(vmid)
            vm_status = self._get_vm_status(current_node, vmid) if current_node else "unknown"

            results["checks"].append({
                "name": f"Ceph VM {vmid} ({vm_name}) Initial State",
                "status": "PASS" if vm_status == "running" else "WARN",
                "details": f"Located on {current_node}, status: {vm_status}"
            })

            if perform_live_migration and vm_status == "running":
                # Pick next target node
                target_node = "prox23" if current_node == "prox22" else ("prox24" if current_node == "prox23" else "prox22")
                
                # Perform migration via ha-manager or qm migrate
                t0 = time.time()
                mig_cmd = f"ha-manager migrate vm:{vmid} {target_node}" if target_vm.get("ha_managed") else f"qm migrate {vmid} {target_node} --online"
                code, out, err = self.ssh.run_cmd(self.leader, mig_cmd)

                # Poll until migration completes (up to 90 seconds)
                migrated_ok = False
                elapsed = 0
                for _ in range(30):
                    time.sleep(3)
                    elapsed = int(time.time() - t0)
                    new_node = self._get_vm_location(vmid)
                    new_status = self._get_vm_status(new_node, vmid)
                    if new_node == target_node and new_status == "running":
                        migrated_ok = True
                        break

                results["checks"].append({
                    "name": f"Ceph VM {vmid} Live Migration: {current_node} -> {target_node}",
                    "status": "PASS" if migrated_ok else "FAIL",
                    "details": f"Migrated in {elapsed}s, VM running on {target_node}" if migrated_ok else f"Migration timed out or failed. Final node: {new_node}, status: {new_status}"
                })
                if not migrated_ok:
                    results["passed"] = False

                results["migrations"].append({
                    "vmid": vmid,
                    "storage": "ceph",
                    "from_node": current_node,
                    "to_node": target_node,
                    "duration_seconds": elapsed,
                    "success": migrated_ok
                })

        # 2. Test ZFS Replication Status (VM 9002)
        zfs_vms = [v for v in self.vms if v.get("storage") == "zfs-ha"]
        if zfs_vms:
            target_vm = zfs_vms[0]
            vmid = target_vm["vmid"]
            vm_name = target_vm["name"]

            current_node = self._get_vm_location(vmid)
            vm_status = self._get_vm_status(current_node, vmid) if current_node else "unknown"

            # Check pvesr replication status on the node hosting the VM
            repl_node = current_node if current_node else self.leader
            code, out, err = self.ssh.run_cmd(repl_node, f"pvesr status")
            repl_lines = [l for l in out.splitlines() if str(vmid) in l]
            all_repl_ok = len(repl_lines) > 0 and all("OK" in l for l in repl_lines)

            results["checks"].append({
                "name": f"ZFS VM {vmid} ({vm_name}) Replication Sync",
                "status": "PASS" if all_repl_ok else "WARN",
                "details": f"State: {'All targets synchronized OK' if all_repl_ok else 'Replication pending or error'}. Jobs: {len(repl_lines)}"
            })

        return results
