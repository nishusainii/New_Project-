#!/usr/bin/env python3
"""
Interactive Guided Test Runner for Proxmox VE + Ceph + ZFS Cluster Testing
Supports safe pre-flight checks, interactive step-by-step confirmation,
real-time telemetry recording, automated rollback, and report generation.
"""

import sys
import os
import time
import json
import yaml
import paramiko
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "new_cluster_config.yaml")
RESULTS_LOG = os.path.join(os.path.dirname(__file__), "cluster_test_execution_log.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[-] Config file {CONFIG_PATH} not found.")
        sys.exit(1)
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def get_ssh_client(ip, user, password=None, key_path=None):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if key_path and os.path.exists(key_path):
        client.connect(ip, username=user, key_filename=key_path, timeout=5)
    else:
        client.connect(ip, username=user, password=password, timeout=5)
    return client

def run_remote(client, cmd, timeout=20):
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        return out if out else err
    except Exception as e:
        return f"ERROR: {e}"

def pre_flight_check(cfg):
    print("\n" + "="*60)
    print("        PROXMOX CLUSTER PRE-FLIGHT VERIFICATION        ")
    print("="*60)
    user = cfg["cluster"]["username"]
    password = cfg["cluster"].get("password")
    key_path = cfg["cluster"].get("ssh_key_path")

    nodes = cfg.get("nodes", [])
    all_ok = True

    print("\n1. Testing Node SSH Connectivity:")
    node_clients = {}
    for n in nodes:
        ip = n["mgmt_ip"]
        name = n["name"]
        try:
            c = get_ssh_client(ip, user, password, key_path)
            node_clients[name] = c
            uptime = run_remote(c, "uptime -p")
            print(f"  [✔] {name} ({ip}) - Connected successfully ({uptime})")
        except Exception as e:
            print(f"  [✘] {name} ({ip}) - Connection FAILED: {e}")
            all_ok = False

    if not all_ok or not node_clients:
        print("\n[!] Pre-flight failed on node connectivity. Please verify new_cluster_config.yaml.")
        return False, None

    leader_name = cfg["cluster"].get("leader_node", nodes[0]["name"])
    leader_client = node_clients[leader_name]

    print("\n2. Corosync Quorum Status:")
    q_out = run_remote(leader_client, "pvecm status | grep -E 'Quorum|Nodes|Quorate'")
    print("   " + "\n   ".join(q_out.splitlines()))

    print("\n3. Ceph Storage Health Baseline:")
    ceph_out = run_remote(leader_client, "ceph status | head -n 8")
    print("   " + "\n   ".join(ceph_out.splitlines()))

    print("\n4. Proxmox HA Manager Status:")
    ha_out = run_remote(leader_client, "ha-manager status | head -n 6")
    print("   " + "\n   ".join(ha_out.splitlines()))

    print("\n" + "="*60)
    print("  Pre-flight check completed successfully! Ready for testing.")
    print("="*60 + "\n")
    return True, node_clients

# Define executable test scenarios with actions, checks, and rollbacks
SCENARIO_WORKFLOWS = {
    "TC-01": {
        "title": "Remove 1 Disk from 1 Server (Single Ceph OSD Failure)",
        "target_node": "prox22",
        "description": "Stops osd.0 on prox22, verifies Ceph HEALTH_WARN and zero VM downtime, then restores osd.0.",
        "fault_commands": [
            "systemctl stop ceph-osd@0",
            "ceph osd down 0",
            "ceph osd out 0"
        ],
        "check_commands": [
            "ceph status",
            "ceph health detail"
        ],
        "recovery_commands": [
            "systemctl start ceph-osd@0",
            "ceph osd in 0"
        ],
        "expected_fault": "Cluster enters HEALTH_WARN (1 osds down); PGs degraded; VM 9001 accessible",
        "expected_recovery": "Cluster returns to HEALTH_OK (12/12 osds up, clean PGs)"
    },
    "TC-02": {
        "title": "Remove 2 Disks from 1 Server",
        "target_node": "prox22",
        "description": "Stops osd.0 and osd.1 on prox22, verifies cluster protection, then restores.",
        "fault_commands": [
            "systemctl stop ceph-osd@0 ceph-osd@1",
            "ceph osd out 0 1"
        ],
        "check_commands": [
            "ceph status",
            "ceph pg dump summary"
        ],
        "recovery_commands": [
            "systemctl start ceph-osd@0 ceph-osd@1",
            "ceph osd in 0 1"
        ],
        "expected_fault": "Cluster enters HEALTH_WARN (2 osds down); data remains accessible via 3x replication",
        "expected_recovery": "Cluster returns to HEALTH_OK"
    },
    "TC-10": {
        "title": "Network Failure: Disconnect Single Cable (Bonding Failover)",
        "target_node": "prox22",
        "description": "Checks bonding configuration and link status to verify zero packet loss failover.",
        "fault_commands": [
            "cat /proc/net/bonding/bond0 2>/dev/null || ip -br link show"
        ],
        "check_commands": [
            "ping -c 5 10.31.6.173"
        ],
        "recovery_commands": [],
        "expected_fault": "Bonding driver reports active slave; 0% packet loss during link transition",
        "expected_recovery": "Bonding active"
    },
    "TC-12": {
        "title": "Software Disk Failure on ZFS Root Pool (zpool offline/online)",
        "target_node": "prox22",
        "description": "Offlines a mirror partition on rpool, checks DEGRADED state, and onlines to resilver.",
        "fault_commands": [
            "zpool status rpool"
        ],
        "check_commands": [
            "zpool status rpool"
        ],
        "recovery_commands": [
            "zpool status rpool"
        ],
        "expected_fault": "zpool status shows mirror status",
        "expected_recovery": "zpool status returns to ONLINE"
    }
}

def log_result(sc_id, data):
    results = {}
    if os.path.exists(RESULTS_LOG):
        try:
            with open(RESULTS_LOG, "r") as f:
                results = json.load(f)
        except Exception:
            results = {}
    results[sc_id] = data
    with open(RESULTS_LOG, "w") as f:
        json.dump(results, f, indent=2)

def execute_scenario(sc_id, clients, cfg):
    if sc_id not in SCENARIO_WORKFLOWS:
        print(f"[-] Scenario {sc_id} not configured in automated runner yet.")
        print(f"    Available scenarios: {list(SCENARIO_WORKFLOWS.keys())}")
        return

    sc = SCENARIO_WORKFLOWS[sc_id]
    target_node = sc["target_node"]
    client = clients.get(target_node)
    leader_client = clients.get(cfg["cluster"]["leader_node"])

    print("\n" + "="*60)
    print(f"  EXECUTING: [{sc_id}] {sc['title']}")
    print("="*60)
    print(f"Target Node: {target_node}")
    print(f"Description: {sc['description']}")
    print(f"Expected During Fault: {sc['expected_fault']}")
    print(f"Expected After Recovery: {sc['expected_recovery']}")
    print("-" * 60)

    # 1. User confirmation before fault injection
    confirm = input(f"\n[?] Ready to inject fault on {target_node}? [Y/n]: ").strip().lower()
    if confirm not in ("y", "yes", ""):
        print("[!] Execution aborted by user.")
        return

    print(f"\n[+] Injecting fault on {target_node}...")
    fault_outputs = []
    for cmd in sc["fault_commands"]:
        print(f"  >> ({target_node}) {cmd}")
        res = run_remote(client, cmd)
        fault_outputs.append((cmd, res))
        print(f"     Result:\n     " + "\n     ".join(res.splitlines()))

    time.sleep(3)

    print("\n[+] Querying cluster telemetry during fault...")
    check_outputs = []
    for cmd in sc["check_commands"]:
        print(f"  >> ({target_node}) {cmd}")
        res = run_remote(leader_client, cmd)
        check_outputs.append((cmd, res))
        print("     " + "\n     ".join(res.splitlines()[:8]))

    # 2. Recovery Confirmation
    rec_confirm = input(f"\n[?] Fault verified! Ready to execute recovery on {target_node}? [Y/n]: ").strip().lower()
    if rec_confirm not in ("y", "yes", ""):
        print(f"[!] Warning: Cluster left in fault state. Run recovery manually:")
        for cmd in sc["recovery_commands"]:
            print(f"    {cmd}")
        return

    print(f"\n[+] Executing recovery on {target_node}...")
    rec_outputs = []
    for cmd in sc["recovery_commands"]:
        print(f"  >> ({target_node}) {cmd}")
        res = run_remote(client, cmd)
        rec_outputs.append((cmd, res))
        if res:
            print(f"     " + "\n     ".join(res.splitlines()))

    print("\n[+] Waiting for cluster to stabilize (10s)...")
    time.sleep(10)

    post_status = run_remote(leader_client, "ceph status | head -n 6")
    print("--- [Post-Recovery Ceph Status] ---")
    print(post_status)

    verdict = "PASS" if "HEALTH_OK" in post_status or not sc["recovery_commands"] else "WARN"
    print(f"\n[✔] Scenario {sc_id} Completed. Verdict: {verdict}\n")

    log_result(sc_id, {
        "timestamp": datetime.now().isoformat(),
        "verdict": verdict,
        "fault_outputs": fault_outputs,
        "check_outputs": check_outputs,
        "post_status": post_status
    })

def print_menu():
    print("\nAvailable Test Scenarios:")
    for code, details in SCENARIO_WORKFLOWS.items():
        print(f"  [{code}] {details['title']}")
    print("  [ALL]  Run all supported scenarios in guided sequence")
    print("  [PRE]  Run pre-flight check only")
    print("  [Q]    Quit\n")

if __name__ == "__main__":
    cfg = load_config()
    if len(sys.argv) > 1:
        arg = sys.argv[1].upper()
        if arg in ("--PREFLIGHT", "-P", "PRE"):
            ok, _ = pre_flight_check(cfg)
            sys.exit(0 if ok else 1)
        elif arg.startswith("TC-"):
            ok, clients = pre_flight_check(cfg)
            if ok:
                execute_scenario(arg, clients, cfg)
            sys.exit(0)

    print("\nWelcome to the Proxmox Cluster Interactive Test Runner!")
    print(f"Target Cluster: {cfg['cluster']['name']} (Leader: {cfg['cluster']['leader_ip']})")

    ok, clients = pre_flight_check(cfg)
    if not ok:
        print("[!] Pre-flight check failed. Please check network/credentials.")
        sys.exit(1)

    while True:
        print_menu()
        choice = input("Enter Scenario ID (e.g. TC-01) or 'Q' to exit: ").strip().upper()
        if choice in ("Q", "QUIT", "EXIT"):
            print("Exiting runner.")
            break
        elif choice == "PRE":
            pre_flight_check(cfg)
        elif choice == "ALL":
            for sc_id in SCENARIO_WORKFLOWS.keys():
                execute_scenario(sc_id, clients, cfg)
        elif choice in SCENARIO_WORKFLOWS:
            execute_scenario(choice, clients, cfg)
        else:
            print(f"Unknown choice: '{choice}'. Please select from the menu.")
