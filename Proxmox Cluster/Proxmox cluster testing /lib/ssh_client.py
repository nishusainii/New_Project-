import subprocess
import json
import logging
from typing import Tuple, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ClusterSSH")

class ProxmoxSSHClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cluster = config.get("cluster", {})
        self.nodes = {n["name"]: n for n in config.get("nodes", [])}
        self.leader_node = self.cluster.get("leader_node", "prox24")
        self.username = self.cluster.get("username", "root")
        self.password = self.cluster.get("password", "(cybe6@cluster)")

    def run_cmd(self, target_node: str, cmd: str, timeout: int = 60) -> Tuple[int, str, str]:
        """
        Execute a shell command on the specified node via SSH.
        """
        if target_node in self.nodes:
            target_ip = self.nodes[target_node]["mgmt_ip"]
        else:
            target_ip = target_node

        ssh_args = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            f"{self.username}@{target_ip}",
            cmd
        ]

        try:
            res = subprocess.run(
                ssh_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=True
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout}s on {target_node}: {cmd}")
            return -1, "", f"Timeout after {timeout}s"
        except Exception as e:
            logger.error(f"SSH execution failed on {target_node}: {e}")
            return -1, "", str(e)

    def run_cmd_json(self, target_node: str, cmd: str, timeout: int = 60) -> Tuple[int, Optional[Any], str]:
        """
        Execute a shell command and parse stdout as JSON.
        """
        code, out, err = self.run_cmd(target_node, cmd, timeout=timeout)
        if code != 0:
            return code, None, err
        try:
            data = json.loads(out)
            return code, data, ""
        except json.JSONDecodeError as e:
            return -1, None, f"JSON parse error: {e}. Output was: {out[:200]}"
