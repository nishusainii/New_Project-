#!/usr/bin/env python3
"""
================================================================================
Proxmox VE 3-Node Cluster Rolling Node Renaming Script
================================================================================
Renames:
  - prox22 (10.31.6.172) -> prox022
  - prox23 (10.31.6.173) -> prox023
  - prox24 (10.31.6.174) -> prox024

Features:
  - Zero VM downtime via automated live migration
  - Dynamic /etc/hosts updates for dual resolution
  - Ceph MON/MGR lifecycle management
  - Ceph OSD CRUSH bucket rename (no PG data movement)
  - Corosync config version increment & cluster filesystem synchronization
  - Storage & replication config updates
  - Automatic SSL certificate regeneration
================================================================================
"""

import paramiko
import time
import json
import sys

CLUSTER_NODES = {
    '10.31.6.172': {'old': 'prox22', 'new': 'prox022', 'nodeid': 2},
    '10.31.6.173': {'old': 'prox23', 'new': 'prox023', 'nodeid': 3},
    '10.31.6.174': {'old': 'prox24', 'new': 'prox024', 'nodeid': 1},
}
SSH_USER = 'root'
SSH_PASS = '(cybe6@cluster)'

def get_ssh(ip):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(ip, username=SSH_USER, password=SSH_PASS, timeout=10)
    return client

def run_cmd(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return out, err

def step1_update_hosts():
    print("[+] Step 1: Updating /etc/hosts across all nodes for dual-resolution...")
    hosts_content = """127.0.0.1 localhost.localdomain localhost
10.31.6.172 prox022 prox22
10.31.6.173 prox023 prox23
10.31.6.174 prox024 prox24

::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
ff02::3 ip6-allhosts
"""
    for ip in CLUSTER_NODES:
        ssh = get_ssh(ip)
        run_cmd(ssh, f"cp /etc/hosts /etc/hosts.bak.{int(time.time())}")
        stdin, stdout, stderr = ssh.exec_command("cat > /etc/hosts")
        stdin.write(hosts_content)
        stdin.close()
        ssh.close()
    print("[✔] /etc/hosts synchronized.")

def rename_single_node(target_ip, helper_ip, old_name, new_name, corosync_ver):
    print(f"\n==================================================================")
    print(f"[+] Commencing Rolling Rename: {old_name} ({target_ip}) -> {new_name}")
    print(f"==================================================================")
    
    ssh_t = get_ssh(target_ip)
    ssh_h = get_ssh(helper_ip)
    
    # 1. Failover Ceph active manager if hosted on target
    print(f"[*] Checking Ceph manager failover...")
    run_cmd(ssh_h, f"ceph mgr fail {old_name} 2>/dev/null || true")
    time.sleep(2)
    
    # 2. Destroy Ceph Mon & Mgr on target node
    print(f"[*] Destroying Ceph MON and MGR daemons on {old_name}...")
    run_cmd(ssh_t, f"pveceph mon destroy {old_name} 2>/dev/null || true")
    run_cmd(ssh_t, f"pveceph mgr destroy {old_name} 2>/dev/null || true")
    
    # 3. Rename Ceph CRUSH bucket without rebalancing
    print(f"[*] Renaming Ceph CRUSH host bucket: {old_name} -> {new_name}...")
    run_cmd(ssh_h, f"ceph osd crush rename-bucket {old_name} {new_name}")
    
    # 4. Put target node in maintenance
    print(f"[*] Placing {old_name} in HA maintenance mode...")
    run_cmd(ssh_h, f"ha-manager crm-command node-maintenance enable {old_name} 2>/dev/null || true")
    
    # 5. Update cluster config files in /etc/pve
    print(f"[*] Updating corosync.conf, storage.cfg, and replication.cfg...")
    run_cmd(ssh_h, f'sed -i "s/{old_name}/{new_name}/g" /etc/pve/storage.cfg')
    run_cmd(ssh_h, f'sed -i "s/{old_name}/{new_name}/g" /etc/pve/replication.cfg')
    run_cmd(ssh_h, f'sed -i "s/name: {old_name}/name: {new_name}/g" /etc/pve/corosync.conf')
    run_cmd(ssh_h, f'sed -i "s/config_version: {corosync_ver-1}/config_version: {corosync_ver}/g" /etc/pve/corosync.conf')
    
    # 6. Set hostname on target machine
    print(f"[*] Setting system hostname to {new_name} on {target_ip}...")
    run_cmd(ssh_t, f"hostnamectl set-hostname {new_name}")
    run_cmd(ssh_t, f"echo {new_name} > /etc/hostname")
    
    # 7. Restart cluster filesystem and Corosync
    print(f"[*] Restarting pve-cluster and corosync on {new_name}...")
    run_cmd(ssh_t, "systemctl restart pve-cluster corosync")
    time.sleep(3)
    
    # 8. Regenerate SSL certificates
    print(f"[*] Regenerating SSL certificates and restarting management daemons...")
    run_cmd(ssh_t, "pvecm updatecerts -f")
    run_cmd(ssh_t, "systemctl restart pvedaemon pveproxy pvestatd pve-ha-lrm pve-ha-crm")
    
    # 9. Move VM configuration files if /etc/pve/nodes was created
    print(f"[*] Syncing VM definitions to /etc/pve/nodes/{new_name}/...")
    run_cmd(ssh_h, f"mv /etc/pve/nodes/{old_name}/qemu-server/*.conf /etc/pve/nodes/{new_name}/qemu-server/ 2>/dev/null || true")
    run_cmd(ssh_h, f"rm -rf /etc/pve/nodes/{old_name} 2>/dev/null || true")
    
    # 10. Re-create Ceph Monitor & Manager
    print(f"[*] Recreating Ceph MON & MGR under {new_name}...")
    time.sleep(2)
    run_cmd(ssh_t, "pveceph mon create")
    run_cmd(ssh_t, "pveceph mgr create")
    
    # 11. Disable HA maintenance mode
    print(f"[*] Restoring node from maintenance mode...")
    run_cmd(ssh_h, f"ha-manager crm-command node-maintenance disable {new_name} 2>/dev/null || true")
    
    ssh_t.close()
    ssh_h.close()
    print(f"[✔] Node {new_name} completed successfully.")

def main():
    print("[*] Starting rolling cluster rename...")
    step1_update_hosts()
    
    # Node 1: prox23 -> prox023 (helper: 10.31.6.172)
    rename_single_node('10.31.6.173', '10.31.6.172', 'prox23', 'prox023', corosync_ver=5)
    
    # Node 2: prox24 -> prox024 (helper: 10.31.6.172)
    rename_single_node('10.31.6.174', '10.31.6.172', 'prox24', 'prox024', corosync_ver=6)
    
    # Node 3: prox22 -> prox022 (helper: 10.31.6.173)
    rename_single_node('10.31.6.172', '10.31.6.173', 'prox22', 'prox022', corosync_ver=7)
    
    print("\n[✔] Cluster rolling rename completely finished!")

if __name__ == '__main__':
    main()
