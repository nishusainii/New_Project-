#!/usr/bin/env python3
"""
Automated Controlled Test Executor for Proxmox VE + Ceph Cluster
Executes fault injection scenarios sequentially, captures full telemetry,
executes immediate recovery, and verifies return to HEALTH_OK.
"""

import sys
import os
import time
import json
import yaml
import paramiko
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "new_cluster_config.yaml")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "live_test_execution_results.json")

def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

def get_ssh(ip, user, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=password, timeout=10)
    return client

def run_cmd(ssh, cmd, timeout=30):
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        return out if out else err
    except Exception as e:
        return f"ERROR: {e}"

def wait_for_ceph_health_ok(ssh, max_wait_sec=120, check_interval=5):
    print(f"[*] Waiting for Ceph to return to HEALTH_OK (max {max_wait_sec}s)...")
    start = time.time()
    while time.time() - start < max_wait_sec:
        st = run_cmd(ssh, "ceph health")
        if "HEALTH_OK" in st:
            elapsed = int(time.time() - start)
            print(f"[✔] Ceph stabilized to HEALTH_OK in {elapsed}s.")
            return True, elapsed
        time.sleep(check_interval)
    print("[-] Warning: Ceph did not reach HEALTH_OK within timeout.")
    return False, int(time.time() - start)

def check_vm_ping(ssh, vm_ip="10.31.6.172"):
    res = run_cmd(ssh, f"ping -c 3 -W 1 {vm_ip}")
    return "0% packet loss" in res

def execute_tc01_single_osd_failure(clients, cfg):
    print("\n" + "="*70)
    print("▶ EXECUTING TC-01: Remove 1 Disk from 1 Server (Single OSD Failure)")
    print("="*70)
    leader = clients["prox22"]
    target_node = "prox22"
    target_ssh = clients[target_node]
    osd_id = 0

    # 1. Baseline
    base_status = run_cmd(leader, "ceph status | head -n 8")
    print(f"[1] Baseline State:\n{base_status}\n")

    # 2. Inject Fault
    print(f"[2] Injecting Fault: Stopping ceph-osd@{osd_id} on {target_node}...")
    run_cmd(target_ssh, f"systemctl stop ceph-osd@{osd_id}")
    run_cmd(target_ssh, f"ceph osd down {osd_id}")
    run_cmd(target_ssh, f"ceph osd out {osd_id}")
    time.sleep(4)

    # 3. Telemetry during fault
    fault_health = run_cmd(leader, "ceph health detail")
    fault_status = run_cmd(leader, "ceph status | head -n 8")
    print(f"[3] Telemetry During Fault:\nHealth Detail: {fault_health}\nStatus Summary:\n{fault_status}\n")

    # 4. Recovery
    print(f"[4] Initiating Recovery: Starting ceph-osd@{osd_id} and marking IN...")
    run_cmd(target_ssh, f"systemctl start ceph-osd@{osd_id}")
    run_cmd(target_ssh, f"ceph osd in {osd_id}")

    # 5. Wait for stabilization
    ok, rec_time = wait_for_ceph_health_ok(leader, max_wait_sec=90)
    final_status = run_cmd(leader, "ceph status | head -n 8")
    print(f"[5] Post-Recovery State:\n{final_status}\n")

    verdict = "PASS" if ok else "FAIL"
    print(f"▶ TC-01 Result: {verdict} (Recovery Time: {rec_time}s)")
    return {
        "id": "TC-01",
        "title": "Remove 1 Disk from 1 Server",
        "verdict": verdict,
        "recovery_time_sec": rec_time,
        "fault_health": fault_health,
        "final_status": final_status
    }

def execute_tc02_dual_osd_failure(clients, cfg):
    print("\n" + "="*70)
    print("▶ EXECUTING TC-02: Remove 2 Disks from 1 Server (osd.0 & osd.1 on prox22)")
    print("="*70)
    leader = clients["prox22"]
    target_ssh = clients["prox22"]

    # 1. Baseline check
    base_status = run_cmd(leader, "ceph health")
    print(f"[1] Baseline: {base_status}")

    # 2. Inject Fault
    print("[2] Stopping osd.0 and osd.1 on prox22...")
    run_cmd(target_ssh, "systemctl stop ceph-osd@0 ceph-osd@1")
    run_cmd(target_ssh, "ceph osd down 0 1")
    run_cmd(target_ssh, "ceph osd out 0 1")
    time.sleep(4)

    # 3. Telemetry
    fault_health = run_cmd(leader, "ceph health detail")
    fault_status = run_cmd(leader, "ceph status | head -n 8")
    print(f"[3] Telemetry During Dual OSD Outage:\n{fault_health}\n{fault_status}\n")

    # 4. Recovery
    print("[4] Restoring osd.0 and osd.1...")
    run_cmd(target_ssh, "systemctl start ceph-osd@0 ceph-osd@1")
    run_cmd(target_ssh, "ceph osd in 0 1")

    # 5. Wait for clean
    ok, rec_time = wait_for_ceph_health_ok(leader, max_wait_sec=90)
    final_status = run_cmd(leader, "ceph status | head -n 8")
    print(f"[5] Post-Recovery State:\n{final_status}\n")

    verdict = "PASS" if ok else "FAIL"
    print(f"▶ TC-02 Result: {verdict} (Recovery Time: {rec_time}s)")
    return {
        "id": "TC-02",
        "title": "Remove 2 Disks from 1 Server",
        "verdict": verdict,
        "recovery_time_sec": rec_time,
        "fault_health": fault_health,
        "final_status": final_status
    }

def execute_tc10_network_bonding_check(clients, cfg):
    print("\n" + "="*70)
    print("▶ EXECUTING TC-10: Network Interface Link & Bonding Redundancy Check")
    print("="*70)
    leader = clients["prox22"]
    target_ssh = clients["prox22"]

    bond_info = run_cmd(target_ssh, "cat /proc/net/bonding/bond0 2>/dev/null || ip -br link")
    print(f"[1] Network Interfaces / Bonding Info:\n{bond_info}\n")

    # Ping latency check to other nodes
    p1 = run_cmd(leader, "ping -c 4 -W 1 10.31.6.173")
    p2 = run_cmd(leader, "ping -c 4 -W 1 10.31.6.174")
    p3 = run_cmd(leader, "ping -c 4 -W 1 192.168.10.23")
    print(f"[2] Mgmt Network Ping (prox23):\n{p1}\n")
    print(f"[3] Mgmt Network Ping (prox24):\n{p2}\n")
    print(f"[4] Ceph Fabric Network Ping (prox23 storage):\n{p3}\n")

    loss_ok = ("0% packet loss" in p1) and ("0% packet loss" in p2) and ("0% packet loss" in p3)
    verdict = "PASS" if loss_ok else "WARN"
    print(f"▶ TC-10 Result: {verdict}")
    return {
        "id": "TC-10",
        "title": "Network Redundancy & Link Status Check",
        "verdict": verdict,
        "bonding_info": bond_info[:300]
    }

def execute_tc12_zfs_root_pool_check(clients, cfg):
    print("\n" + "="*70)
    print("▶ EXECUTING TC-12: ZFS Root Boot Pool (rpool) Mirror Health Check")
    print("="*70)
    target_ssh = clients["prox22"]

    zfs_status = run_cmd(target_ssh, "zpool status rpool")
    print(f"[1] ZFS rpool Status:\n{zfs_status}\n")

    is_online = "state: ONLINE" in zfs_status
    no_errors = "errors: No known data errors" in zfs_status
    verdict = "PASS" if (is_online and no_errors) else "WARN"
    print(f"▶ TC-12 Result: {verdict}")
    return {
        "id": "TC-12",
        "title": "ZFS Root Pool Mirror Health Check",
        "verdict": verdict,
        "zfs_status": zfs_status
    }

def main():
    cfg = load_config()
    user = cfg["cluster"]["username"]
    pwd = cfg["cluster"]["password"]

    print("Connecting to all nodes...")
    clients = {}
    for n in cfg["nodes"]:
        name = n["name"]
        ip = n["mgmt_ip"]
        clients[name] = get_ssh(ip, user, pwd)

    results = []

    # Run TC-01
    r1 = execute_tc01_single_osd_failure(clients, cfg)
    results.append(r1)

    # Short pause
    time.sleep(5)

    # Run TC-02
    r2 = execute_tc02_dual_osd_failure(clients, cfg)
    results.append(r2)

    # Short pause
    time.sleep(5)

    # Run TC-10
    r3 = execute_tc10_network_bonding_check(clients, cfg)
    results.append(r3)

    # Run TC-12
    r4 = execute_tc12_zfs_root_pool_check(clients, cfg)
    results.append(r4)

    # Close connections
    for c in clients.values():
        c.close()

    # Save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✔] Live testing completed. Saved results to {RESULTS_PATH}")

if __name__ == "__main__":
    main()
