#!/usr/bin/env python3
"""
================================================================================
Live Proxmox Cluster & Cable Pull Resilience Health Monitor
================================================================================
Continuously polls:
  1. Corosync Quorum & Knet Link Status
  2. Physical Link Carrier (10G nic3 & 1G vmbr0) across all 3 nodes
  3. Ceph Health, Monitor Quorum, and OSD Status (up/down/in/out)
  4. High Availability (HA) CRM Master & Node Watchdog Status
  5. Virtual Machine Execution State
================================================================================
"""

import paramiko
import time
import os
import sys

NODES = {
    'prox022': {'ip': '10.31.6.172', 'storage_ip': '192.168.10.22'},
    'prox023': {'ip': '10.31.6.173', 'storage_ip': '192.168.10.23'},
    'prox024': {'ip': '10.31.6.174', 'storage_ip': '192.168.10.24'},
}
SSH_USER = 'root'
SSH_PASS = '(cybe6@cluster)'

# ANSI Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'

def get_ssh(ip):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(ip, username=SSH_USER, password=SSH_PASS, timeout=3)
        return client
    except Exception:
        return None

def main():
    print(f"{CYAN}{BOLD}Starting Real-Time Cluster Health Monitor for Cable Pull Testing...{RESET}")
    print("Press Ctrl+C to stop.\n")
    time.sleep(1)

    while True:
        os.system('clear' if os.name == 'posix' else 'cls')
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"{BOLD}================================================================================")
        print(f" 🔍 PROXMOX VE CLUSTER HEALTH DASHBOARD — {now}")
        print(f"================================================================================{RESET}")

        # Connect to an available node
        active_ssh = None
        leader_name = None
        for name, meta in NODES.items():
            ssh = get_ssh(meta['ip'])
            if ssh:
                active_ssh = ssh
                leader_name = name
                break

        if not active_ssh:
            print(f"{RED}{BOLD}🚨 CRITICAL: Cannot reach ANY cluster node via SSH management network!{RESET}")
            time.sleep(2)
            continue

        try:
            # 1. Physical Interface Status across all nodes
            print(f"\n{BOLD}1. PHYSICAL CABLE & NETWORK INTERFACES{RESET}")
            print(f"{'Node':<10} {'Management (vmbr0)':<22} {'10G Storage (nic3)':<22} {'10G Ping (Latency)':<18}")
            print("-" * 75)

            for name, meta in NODES.items():
                s = get_ssh(meta['ip'])
                if not s:
                    print(f"{name:<10} {RED}HOST UNREACHABLE{RESET:<14} {RED}UNKNOWN{RESET:<14} {RED}FAIL{RESET}")
                    continue

                _, stdout, _ = s.exec_command("ip -br link show vmbr0; ip -br link show nic3; ping -c 1 -W 1 192.168.10.23 2>&1")
                out_lines = stdout.read().decode().strip().splitlines()
                s.close()

                vmbr0_status = "DOWN"
                nic3_status = "DOWN"
                ping_status = "FAIL"

                for line in out_lines:
                    if line.startswith("vmbr0"):
                        vmbr0_status = "UP" if "UP" in line else "DOWN"
                    elif line.startswith("nic3"):
                        nic3_status = "UP" if "UP" in line else "DOWN"
                    elif "time=" in line:
                        try:
                            ping_status = line.split("time=")[1].split()[0] + " ms"
                        except:
                            ping_status = "OK"

                v_color = GREEN if vmbr0_status == "UP" else RED
                n_color = GREEN if nic3_status == "UP" else RED
                p_color = GREEN if "ms" in ping_status or ping_status == "OK" else RED

                print(f"{name:<10} {v_color}{vmbr0_status:<22}{RESET} {n_color}{nic3_status:<22}{RESET} {p_color}{ping_status:<18}{RESET}")

            # 2. Corosync Quorum Status
            print(f"\n{BOLD}2. COROSYNC CLUSTER QUORUM (pvecm status){RESET}")
            _, stdout, _ = active_ssh.exec_command("pvecm status 2>/dev/null | grep -E 'Quorate|Nodes:|Total votes|Quorum:'")
            q_lines = stdout.read().decode().strip().splitlines()
            for ql in q_lines:
                if "Quorate:          Yes" in ql:
                    print(f"  {GREEN}{BOLD}✔ {ql.strip()}{RESET}")
                elif "Quorate:          No" in ql:
                    print(f"  {RED}{BOLD}✖ {ql.strip()} (CLUSTER SPLIT-BRAIN RISK){RESET}")
                else:
                    print(f"  {ql.strip()}")

            # 3. Ceph Distributed Storage Health
            print(f"\n{BOLD}3. CEPH REEF STORAGE HEALTH (ceph status){RESET}")
            _, stdout, _ = active_ssh.exec_command("ceph status 2>/dev/null")
            ceph_out = stdout.read().decode().strip()

            health_line = "UNKNOWN"
            mon_line = "UNKNOWN"
            osd_line = "UNKNOWN"
            pg_line = "UNKNOWN"

            for line in ceph_out.splitlines():
                line_s = line.strip()
                if line_s.startswith("health:"):
                    health_line = line_s
                elif line_s.startswith("mon:"):
                    mon_line = line_s
                elif line_s.startswith("osd:"):
                    osd_line = line_s
                elif "active+clean" in line_s or line_s.startswith("pgs:"):
                    pg_line = line_s

            h_color = GREEN if "HEALTH_OK" in health_line else (YELLOW if "HEALTH_WARN" in health_line else RED)
            print(f"  Status: {h_color}{BOLD}{health_line}{RESET}")
            print(f"  Monitors: {mon_line}")
            print(f"  OSD Daemons: {GREEN if '12 up' in osd_line else YELLOW}{osd_line}{RESET}")
            print(f"  Placement Groups: {pg_line}")

            # 4. High Availability & Virtual Machines
            print(f"\n{BOLD}4. HA RESOURCE MANAGER & ACTIVE VIRTUAL MACHINES{RESET}")
            _, stdout, _ = active_ssh.exec_command("ha-manager status 2>/dev/null | grep -E 'master|quorum OK|service'")
            ha_lines = stdout.read().decode().strip().splitlines()
            for hl in ha_lines:
                print(f"  {hl}")

            print(f"\n{BOLD}================================================================================{RESET}")
            print(f"{CYAN}Refreshing every 3 seconds... Press Ctrl+C to exit.{RESET}")

        except Exception as e:
            print(f"{RED}Error polling cluster: {e}{RESET}")
        finally:
            active_ssh.close()

        time.sleep(3)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{GREEN}Monitor stopped by user.{RESET}")
        sys.exit(0)
