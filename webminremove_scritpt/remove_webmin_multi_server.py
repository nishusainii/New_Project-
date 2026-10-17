#!/usr/bin/env python3
"""
Multi-server Webmin removal tool.
Runs from your local machine using Python + Paramiko (no local sudo needed).
"""

import getpass
import os
import sys
import time

try:
    import paramiko
except ImportError:
    print("[ERROR] Paramiko is required. Please check your python environment.")
    sys.exit(1)

# ==============================================================================
# CONFIGURATION: Enter your 4 servers below
# If you leave "password": "", you will be prompted securely in the terminal.
# ==============================================================================
SERVERS = [
    {
        "host": "10.31.1.159",
        "user": "nishu",
        "password": "",  # Set password here or leave empty to be prompted
        "port": 22,
    },
    {
        "host": "10.31.1.24",
        "user": "nishu",
        "password": "",
        "port": 22,
    },
    {
        "host": "10.31.88.24",
        "user": "nishu",
        "password": "",
        "port": 22,
    },
    {
        "host": "10.31.212.14",
        "user": "user1",
        "password": "",
        "port": 22,
    },
]

# Color formatting
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
NC = "\033[0m"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_UNINSTALLER = os.path.join(SCRIPT_DIR, "uninstall_webmin.sh")
REMOTE_TEMP_PATH = "/tmp/uninstall_webmin.sh"


def process_server(server_info):
    host = server_info.get("host")
    user = server_info.get("user", "root")
    port = server_info.get("port", 22)
    password = server_info.get("password", "")

    print(f"\n{BLUE}=========================================================={NC}")
    print(f"{BLUE}>>> Processing Server: {host} (User: {user}) <<<{NC}")
    print(f"{BLUE}=========================================================={NC}")

    if not password:
        password = getpass.getpass(f"Enter SSH password for {user}@{host}: ")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 1. Connect
        print(f"  {CYAN}[1/3] Connecting to {host}:{port}...{NC}")
        client.connect(
            hostname=host,
            port=port,
            username=user,
            password=password,
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
        print(f"  {GREEN}[OK] Connected successfully.{NC}")

        # 2. Upload uninstaller via SFTP
        print(f"  {CYAN}[2/3] Uploading uninstaller script...{NC}")
        sftp = client.open_sftp()
        sftp.put(LOCAL_UNINSTALLER, REMOTE_TEMP_PATH)
        sftp.chmod(REMOTE_TEMP_PATH, 0o755)
        sftp.close()
        print(f"  {GREEN}[OK] Uninstaller uploaded to {REMOTE_TEMP_PATH}.{NC}")

        # 3. Execute remote uninstallation
        print(f"  {CYAN}[3/3] Executing complete uninstallation...{NC}")
        if user == "root":
            exec_command = f"bash {REMOTE_TEMP_PATH}"
        else:
            exec_command = f"sudo -S -p '' bash {REMOTE_TEMP_PATH}"

        stdin, stdout, stderr = client.exec_command(exec_command, get_pty=True)

        if user != "root":
            # Send sudo password
            stdin.write(password + "\n")
            stdin.flush()

        # Stream output in real-time
        for line in iter(stdout.readline, ""):
            print(f"    {line}", end="")

        exit_status = stdout.channel.recv_exit_status()

        # Clean up remote temp file
        cleanup_client = client.exec_command(f"rm -f {REMOTE_TEMP_PATH}")

        if exit_status == 0:
            print(f"  {GREEN}[SUCCESS] Webmin removed completely from {host}.{NC}")
            return "SUCCESS"
        else:
            print(f"  {RED}[FAIL] Script exited with code {exit_status} on {host}.{NC}")
            return f"FAILED (Exit code {exit_status})"

    except paramiko.AuthenticationException:
        print(f"  {RED}[FAIL] Authentication failed for {user}@{host}.{NC}")
        return "FAILED (Authentication Error)"
    except Exception as e:
        print(f"  {RED}[FAIL] Error on {host}: {e}{NC}")
        return f"FAILED ({e})"
    finally:
        client.close()


def main():
    if not os.path.isfile(LOCAL_UNINSTALLER):
        print(f"{RED}[ERROR] Could not find uninstaller at '{LOCAL_UNINSTALLER}'{NC}")
        sys.exit(1)

    print(f"{CYAN}=========================================================={NC}")
    print(f"{CYAN}       MULTI-SERVER WEBMIN COMPLETE PURGE TOOL            {NC}")
    print(f"{CYAN}=========================================================={NC}")
    print(f"Targets ({len(SERVERS)} servers):")
    for s in SERVERS:
        print(f"  - {s['host']} ({s.get('user', 'root')})")
    print(f"==========================================================")

    results = {}
    for server in SERVERS:
        res = process_server(server)
        results[server["host"]] = res

    # Final summary
    print(f"\n{CYAN}=========================================================={NC}")
    print(f"{CYAN}                     SUMMARY REPORT                       {NC}")
    print(f"{CYAN}=========================================================={NC}")
    total_success = 0
    total_fail = 0

    for s in SERVERS:
        host = s["host"]
        status = results.get(host, "SKIPPED")
        if status == "SUCCESS":
            print(f"  {host} ({s.get('user', 'root')}) : {GREEN}{status}{NC}")
            total_success += 1
        else:
            print(f"  {host} ({s.get('user', 'root')}) : {RED}{status}{NC}")
            total_fail += 1

    print("==========================================================")
    print(f"Total: {len(SERVERS)} | Success: {total_success} | Failed: {total_fail}")
    print("==========================================================")

    if total_fail > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
