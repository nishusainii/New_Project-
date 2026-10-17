#!/usr/bin/env python3
"""
================================================================================
Innspark / CiSai Squid Proxy Fleet Updater
================================================================================
Updates the management portal across all 4 Squid proxy servers:
  1. 10.31.1.159   (user: nishu, pass: nishu)
  2. 10.31.212.14  (user: user1, pass: cyberdrift)
  3. 10.31.1.24    (user: nishu, pass: nishu)
  4. 10.31.88.24   (user: nishu, pass: nishu@123)

Features:
  - Packages the latest portal codebase
  - Uses Paramiko for automated, non-interactive SSH/SFTP transport
  - Preserves existing configuration, admin credentials, ACLs, and backups
  - Restarts innspark-squid-portal.service with zero Squid proxy disruption
  - Validates HTTP 200 response and service health on all 4 nodes
================================================================================
"""

import os
import sys
import argparse
import subprocess
import time

try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False

PROXY_SERVERS = [
    {"ip": "10.31.1.159",  "name": "Proxy Node 1 (10.31.1.159)",  "user": "nishu", "password": "nishu"},
    {"ip": "10.31.212.14", "name": "Proxy Node 2 (10.31.212.14)", "user": "user1", "password": "cyberdrift"},
    {"ip": "10.31.1.24",   "name": "Proxy Node 3 (10.31.1.24)",   "user": "nishu", "password": "nishu"},
    {"ip": "10.31.88.24",  "name": "Proxy Node 4 (10.31.88.24)",  "user": "nishu", "password": "nishu@123"},
]

REMOTE_PORTAL_DIR = "/opt/innspark-squid-portal"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTAL_DIR = os.path.join(SCRIPT_DIR, "Proxy UI Management App") if os.path.exists(os.path.join(SCRIPT_DIR, "Proxy UI Management App")) else SCRIPT_DIR

def create_update_tarball():
    tar_path = "/tmp/squid-portal-update.tar.gz"
    if os.path.exists(tar_path):
        os.remove(tar_path)

    tar_cmd = [
        "tar", "-czf", tar_path,
        "-C", PORTAL_DIR,
        "app.py", "config.py", "auth.py", "squid_manager.py", "nftables_manager.py",
        "requirements.txt", "innspark-squid-portal.service",
        "templates", "static"
    ]
    subprocess.run(tar_cmd, check=True)
    return tar_path

def execute_remote_ssh(ssh_client, cmd, password=None, is_sudo=False):
    if is_sudo:
        full_cmd = f"echo '{password}' | sudo -S bash -c \"{cmd}\""
    else:
        full_cmd = cmd
    stdin, stdout, stderr = ssh_client.exec_command(full_cmd, timeout=30)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    return code, out, err

def update_node(node, override_pass, key_file, tar_path):
    ip = node["ip"]
    name = node["name"]
    user = node["user"]
    password = override_pass or node["password"]

    print(f"\n========================================================")
    print(f"[*] Updating {name} -> {user}@{ip}...")
    print(f"========================================================")

    if HAS_PARAMIKO:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(
                hostname=ip,
                username=user,
                password=password,
                key_filename=key_file if key_file and os.path.exists(key_file) else None,
                timeout=10,
                banner_timeout=15,
                look_for_keys=False,
                allow_agent=False
            )
            print(f"  ✓ Connected to host as '{user}'")

            # SFTP Transfer
            sftp = client.open_sftp()
            sftp.put(tar_path, "/tmp/squid-portal-update.tar.gz")
            sftp.close()
            print(f"  ✓ Transferred updated package to /tmp/squid-portal-update.tar.gz")

            # Remote extraction & reload
            remote_cmds = f"""
                mkdir -p {REMOTE_PORTAL_DIR}
                mkdir -p {REMOTE_PORTAL_DIR}/data
                mkdir -p /etc/squid/acl
                mkdir -p /etc/squid/acl/users
                mkdir -p /etc/squid/acl/domains
                mkdir -p /etc/squid/acl/ips
                mkdir -p /etc/squid/squid_backups/portal_backups/nftables
                mkdir -p /etc/squid/squid_backups/portal_archives

                tar -xzf /tmp/squid-portal-update.tar.gz -C {REMOTE_PORTAL_DIR}

                cp {REMOTE_PORTAL_DIR}/innspark-squid-portal.service /etc/systemd/system/
                systemctl daemon-reload
                systemctl enable innspark-squid-portal.service
                systemctl restart innspark-squid-portal.service
            """
            code, out, err = execute_remote_ssh(client, remote_cmds, password, is_sudo=True)
            if code != 0:
                print(f"  [✘] Remote extraction/restart failed: {err}")
                client.close()
                return False, f"Service Restart Failed: {err}"
            print(f"  ✓ Code extracted & innspark-squid-portal.service restarted")

            # Verify
            time.sleep(2)
            code_svc, out_svc, _ = execute_remote_ssh(client, "systemctl is-active innspark-squid-portal.service")
            is_active = out_svc.strip() == "active"
            print(f"  ✓ Service Status: {out_svc.strip()}")

            code_http, out_http, _ = execute_remote_ssh(client, "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/login")
            http_code = out_http.strip()
            print(f"  ✓ HTTP Endpoint (Port 5000): {http_code}")

            client.close()
            if is_active and http_code == "200":
                print(f"  [SUCCESS] {name} successfully updated!")
                return True, "Success"
            else:
                return False, f"Status: {out_svc.strip()}, HTTP: {http_code}"

        except Exception as e:
            print(f"  [✘] Connection/Execution error: {e}")
            return False, str(e)
    else:
        return False, "Paramiko library required."

def main():
    parser = argparse.ArgumentParser(description="Update CiSai / Innspark Squid Portal on all 4 proxy servers.")
    parser.add_argument("--password", "--pass", "-p", help="Global override SSH password")
    parser.add_argument("--key", "-k", help="SSH private key path")
    args = parser.parse_args()

    print("================================================================================")
    print("      INSPARK / CISAI SQUID PROXY FLEET UPDATER")
    print("      Node 1: 10.31.1.159   (user: nishu,      pass: nishu)")
    print("      Node 2: 10.31.212.14  (user: user1,      pass: cyberdrift)")
    print("      Node 3: 10.31.1.24    (user: nishu,      pass: nishu)")
    print("      Node 4: 10.31.88.24   (user: nishu,      pass: nishu@123)")
    print("================================================================================")

    print(f"[*] Packaging portal from: {PORTAL_DIR}")
    tar_path = create_update_tarball()
    print(f"  ✓ Archive created: {tar_path} ({round(os.path.getsize(tar_path)/1024, 1)} KB)")

    results = []
    for node in PROXY_SERVERS:
        ok, msg = update_node(node, args.password, args.key, tar_path)
        results.append({"ip": node["ip"], "name": node["name"], "user": node["user"], "success": ok, "msg": msg})

    print("\n" + "=" * 80)
    print(" FLEET UPDATE SUMMARY REPORT")
    print("=" * 80)
    all_ok = True
    for r in results:
        status_symbol = "✓ [ONLINE & UPDATED]" if r["success"] else "✘ [FAILED/UNREACHABLE]"
        print(f"  {status_symbol:<24} {r['name']:<30} ({r['user']}@{r['ip']}) -> {r['msg']}")
        if not r["success"]:
            all_ok = False
        print("=" * 80)

    if all_ok:
        print("\n[SUCCESS] All 4 Squid Proxy Servers have been updated to the latest portal version!\n")
    else:
        print("\n[NOTE] Some nodes could not be completed.")

if __name__ == "__main__":
    main()
