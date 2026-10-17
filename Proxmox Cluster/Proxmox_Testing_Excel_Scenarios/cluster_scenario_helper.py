#!/usr/bin/env python3
"""
Proxmox VE + Ceph + ZFS Cluster Scenario Helper & Validator
Provides real-time cluster telemetry, pre-flight checks, and command references
for all 19 test scenarios defined in 'Manual Test Case proxmox.xlsx'.
"""

import sys
import os
import argparse
import paramiko

# Default cluster configuration (from config.yaml)
CLUSTER_NODES = {
    "prox22": {"mgmt_ip": "10.31.6.172", "cluster_ip": "192.168.10.22", "role": "leader"},
    "prox23": {"mgmt_ip": "10.31.6.173", "cluster_ip": "192.168.10.23", "role": "member"},
    "prox24": {"mgmt_ip": "10.31.6.174", "cluster_ip": "192.168.10.24", "role": "member"},
}
DEFAULT_USER = "root"
DEFAULT_PASS = "(cybe6@cluster)"

SCENARIOS = {
    "TC-01": {
        "title": "Remove 1 Disk from 1 Server (Single OSD Failure)",
        "category": "Ceph Storage",
        "commands": [
            "# 1. List OSD tree and identify target OSD (e.g. osd.0 on prox22)",
            "ceph osd tree",
            "# 2. Simulate disk failure / stop OSD:",
            "systemctl stop ceph-osd@0",
            "ceph osd down 0",
            "ceph osd out 0",
            "# 3. Verify health & PG degradation:",
            "ceph -s",
            "ceph health detail",
            "# 4. Recovery:",
            "systemctl start ceph-osd@0",
            "ceph osd in 0",
            "watch ceph -s"
        ]
    },
    "TC-02": {
        "title": "Remove 2 Disks from 1 Server",
        "category": "Ceph Storage",
        "commands": [
            "# 1. Stop 2 OSDs on the same node:",
            "systemctl stop ceph-osd@0 ceph-osd@1",
            "ceph osd out 0 1",
            "# 2. Verify cluster status (HEALTH_WARN, zero data loss):",
            "ceph status",
            "# 3. Recovery:",
            "systemctl start ceph-osd@0 ceph-osd@1",
            "ceph osd in 0 1"
        ]
    },
    "TC-03": {
        "title": "Remove 3 Disks from 1 Server",
        "category": "Ceph Storage",
        "commands": [
            "# 1. Stop 3 OSDs on prox22:",
            "systemctl stop ceph-osd@0 ceph-osd@1 ceph-osd@2",
            "ceph osd out 0 1 2",
            "# 2. Verify cluster remains active (CRUSH host failure domain protects replicas):",
            "ceph -s",
            "# 3. Recovery:",
            "systemctl start ceph-osd@0 ceph-osd@1 ceph-osd@2",
            "ceph osd in 0 1 2"
        ]
    },
    "TC-04": {
        "title": "Disk Slot Swapping: Slot 1 to Slot 3 (Controller & HBA)",
        "category": "Hardware / Controller",
        "commands": [
            "# 1. Identify disk WWN and UUID before moving:",
            "lsblk -o NAME,UUID,PARTUUID,SERIAL,WWN",
            "# 2. If Hardware RAID controller (e.g. MegaRAID/StorCLI), scan foreign config:",
            "storcli /c0 show",
            "storcli /c0/fall import",
            "# 3. If IT-Mode HBA, activate Ceph OSD volume:",
            "ceph-volume lvm activate --all",
            "ceph osd tree"
        ]
    },
    "TC-05": {
        "title": "Remove All Disks from a Single Node",
        "category": "Ceph Storage",
        "commands": [
            "# 1. Stop all 4 OSDs on prox24:",
            "systemctl stop ceph-osd@8 ceph-osd@9 ceph-osd@10 ceph-osd@11",
            "ceph osd out 8 9 10 11",
            "# 2. Verify node remains alive and VMs keep serving I/O from remaining 2 nodes:",
            "qm status 9001",
            "ceph -s",
            "# 3. Recovery:",
            "systemctl start ceph-osd@8 ceph-osd@9 ceph-osd@10 ceph-osd@11",
            "ceph osd in 8 9 10 11"
        ]
    },
    "TC-08": {
        "title": "Simulate Single Node Failure (Power Off 1 Node)",
        "category": "Proxmox HA",
        "commands": [
            "# 1. On prox24, simulate power loss:",
            "poweroff -f",
            "# 2. On prox22, monitor Corosync quorum (2/3 votes) and HA failover:",
            "watch -n 1 'pvecm status && echo --- && ha-manager status'",
            "# 3. Recovery: Power on prox24, verify 3/3 votes and 12/12 OSDs up."
        ]
    },
    "TC-09": {
        "title": "Simulate Dual Node Failure (Power Off 2 Nodes - Quorum Loss)",
        "category": "Proxmox HA",
        "commands": [
            "# 1. Power off prox23 and prox24:",
            "# 2. On prox22, observe quorum lost (1/3 votes), /etc/pve becomes read-only:",
            "pvecm status",
            "# 3. Disaster Recovery Bypass (if nodes permanently dead):",
            "pvecm expected 1",
            "# 4. Normal Recovery: Power on nodes to restore 2/3 majority votes."
        ]
    },
    "TC-11": {
        "title": "Network Failure: Disconnect Both Interfaces / Total Isolation",
        "category": "Networking",
        "commands": [
            "# 1. On prox24, isolate network:",
            "iptables -I INPUT -j DROP && iptables -I OUTPUT -j DROP",
            "# 2. Watch Corosync drop heartbeats and hardware watchdog fence prox24:",
            "ha-manager status",
            "# 3. Recovery: Clear iptables rules:",
            "iptables -F"
        ]
    },
    "TC-12": {
        "title": "Simulate Software Disk Failure on ZFS Root Pool (rpool)",
        "category": "ZFS Storage",
        "commands": [
            "# 1. Check pool status:",
            "zpool status rpool",
            "# 2. Take mirror disk offline:",
            "zpool offline rpool <disk_vdev_path>",
            "# 3. Verify degraded state and uninterrupted OS operation:",
            "zpool status rpool",
            "# 4. Recovery (Online & Resilver):",
            "zpool online rpool <disk_vdev_path>",
            "watch zpool status rpool"
        ]
    },
    "TC-14": {
        "title": "Replace a Failed Disk with a New One in ZFS (zpool replace)",
        "category": "ZFS Storage",
        "commands": [
            "# 1. Clone partition table from healthy drive /dev/sda to new drive /dev/sdb:",
            "sgdisk -Z /dev/sdb",
            "sgdisk -R /dev/sdb /dev/sda",
            "sgdisk -G /dev/sdb",
            "# 2. Setup bootloader partition:",
            "proxmox-boot-tool format /dev/sdb2",
            "proxmox-boot-tool init /dev/sdb2",
            "# 3. Replace in ZFS pool:",
            "zpool replace -f rpool <OLD_DEVICE_ID> /dev/sdb3",
            "zpool status rpool"
        ]
    },
    "TC-17": {
        "title": "Ceph Monitor Failure & Corrupted DB Reconstruction",
        "category": "Ceph Control Plane",
        "commands": [
            "# 1. Stop mon on prox23 and remove database:",
            "systemctl stop ceph-mon@prox23",
            "rm -rf /var/lib/ceph/mon/ceph-prox23",
            "# 2. Fetch monmap from healthy monitor:",
            "ceph mon getmap -o /tmp/monmap",
            "# 3. Rebuild monitor DB:",
            "ceph-mon --mkfs -i prox23 --monmap /tmp/monmap --keyring /etc/pve/priv/ceph.client.admin.keyring",
            "chown -R ceph:ceph /var/lib/ceph/mon/ceph-prox23",
            "systemctl start ceph-mon@prox23",
            "ceph -s"
        ]
    },
    "TC-18": {
        "title": "Ceph CRUSH Map Rebalancing Performance Benchmarking",
        "category": "Ceph Performance",
        "commands": [
            "# 1. Run baseline write benchmark:",
            "rados bench -p ceph 30 write --no-cleanup",
            "# 2. Trigger CRUSH weight change:",
            "ceph osd crush reweight osd.1 0.5",
            "# 3. Run write benchmark during rebalance:",
            "rados bench -p ceph 30 write --no-cleanup",
            "# 4. Restore original weight:",
            "ceph osd crush reweight osd.1 1.0"
        ]
    }
}

def get_ssh_client(ip, user=DEFAULT_USER, password=DEFAULT_PASS):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=user, password=password, timeout=5)
    return client

def run_remote_cmd(client, cmd):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out if out else err

def check_cluster_telemetry():
    print("==================================================")
    print("      PROXMOX & CEPH CLUSTER TELEMETRY PRE-CHECK  ")
    print("==================================================")
    leader_ip = CLUSTER_NODES["prox22"]["mgmt_ip"]
    try:
        ssh = get_ssh_client(leader_ip)
        print(f"[+] Connected to Leader Node: prox22 ({leader_ip})\n")

        # Corosync Quorum
        pvecm_out = run_remote_cmd(ssh, "pvecm status | grep -E 'Quorum|Nodes|Quorate'")
        print("--- [Corosync Quorum Status] ---")
        print(pvecm_out)
        print()

        # Ceph Health
        ceph_out = run_remote_cmd(ssh, "ceph status | head -n 12")
        print("--- [Ceph Storage Health] ---")
        print(ceph_out)
        print()

        # HA Manager
        ha_out = run_remote_cmd(ssh, "ha-manager status | head -n 10")
        print("--- [Proxmox HA Manager Status] ---")
        print(ha_out)
        print()

        ssh.close()
    except Exception as e:
        print(f"[-] Could not connect to cluster leader: {e}")

def show_scenario(sc_id):
    if sc_id not in SCENARIOS:
        print(f"Scenario '{sc_id}' not found. Available scenarios:")
        for k, v in SCENARIOS.items():
            print(f"  {k}: {v['title']} ({v['category']})")
        return

    sc = SCENARIOS[sc_id]
    print("==================================================")
    print(f" Scenario {sc_id}: {sc['title']}")
    print(f" Category: {sc['category']}")
    print("==================================================")
    print("STEP-BY-STEP COMMANDS:")
    for cmd in sc["commands"]:
        print(f"  {cmd}")
    print()

def list_all():
    print("AVAILABLE TEST SCENARIOS (From Excel Analysis):")
    print("--------------------------------------------------")
    for k, v in SCENARIOS.items():
        print(f"[{k}] {v['title']}")
    print("\nFor full 19-scenario documentation, view:")
    print("PROXMOX_CEPH_TESTING_SCENARIOS_HOWTO.md")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proxmox Ceph Test Scenario Helper")
    parser.add_argument("--status", action="store_true", help="Query live cluster telemetry")
    parser.add_argument("--scenario", type=str, help="Show steps for a scenario ID (e.g. TC-01, TC-08)")
    parser.add_argument("--list", action="store_true", help="List all available scenarios")
    args = parser.parse_args()

    if args.status:
        check_cluster_telemetry()
    elif args.scenario:
        show_scenario(args.scenario.upper())
    elif args.list:
        list_all()
    else:
        list_all()
        print("\nTip: Run with --status to view live cluster health, or --scenario TC-01 for details.")
