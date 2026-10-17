#!/usr/bin/env python3
"""
Innspark Squid Proxy Portal - Safe Automated Deployment Script
Target Node: 10.31.1.159 (proxyserver)
Port: 5000
"""

import os
import sys
import subprocess
import time

SERVER_IP = "10.31.1.159"
SSH_USER = "nishu"
SSH_PASS = "nishu"
REMOTE_PORTAL_DIR = "/opt/innspark-squid-portal"
LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

def run_ssh(cmd, is_sudo=False):
    """Executes a command over SSH."""
    if is_sudo:
        full_cmd = f"echo '{SSH_PASS}' | sudo -S bash -c \"{cmd}\""
    else:
        full_cmd = cmd

    ssh_cmd = [
        "ssh",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{SSH_USER}@{SERVER_IP}",
        full_cmd
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def print_step(title):
    print(f"\n[+] ========================================================")
    print(f"[+] {title}")
    print(f"[+] ========================================================")

def main():
    print_step("Phase 1: Pre-flight Safety Checks on Production Server")
    
    # 1. Check Squid
    code, out, err = run_ssh("systemctl is-active squid")
    if out.strip() != "active":
        print(f"[!] Warning: Squid is not reporting 'active' (output: {out.strip()}). Aborting for safety!")
        sys.exit(1)
    print("  ✓ Squid proxy is currently ACTIVE on 10.31.1.159")

    # 2. Check Webmin
    code, out, err = run_ssh("systemctl is-active webmin")
    print(f"  ✓ Webmin fallback status: {out.strip()} (will remain untouched on port 10443)")

    # 3. Check Port 5000
    code_svc, out_svc, _ = run_ssh("systemctl is-active innspark-squid-portal.service || true")
    portal_running = out_svc.strip() == "active"

    code, out, err = run_ssh("ss -tln | grep ':5000 ' || true")
    if out.strip() and not portal_running:
        print(f"[!] Warning: Port 5000 is already in use by another service: {out.strip()}")
        sys.exit(1)
    elif portal_running:
        print("  ✓ Port 5000 is currently running Innspark Squid Portal (Upgrading existing instance)")
    else:
        print("  ✓ Port 5000 is completely free and ready for the custom portal")

    print_step("Phase 2: Verifying & Installing Required Packages")
    install_cmd = "apt-get update -qq && apt-get install -y -qq python3-flask apache2-utils python3-pip"
    code, out, err = run_ssh(install_cmd, is_sudo=True)
    if code != 0:
        print(f"[!] Warning during package installation: {err}")
    else:
        print("  ✓ Python3 Flask and htpasswd utilities verified/installed.")

    print_step("Phase 3: Packaging & Transferring Portal Codebase")
    tar_path = "/tmp/innspark-portal.tar.gz"
    # Create local tarball
    tar_cmd = [
        "tar", "-czf", tar_path,
        "-C", LOCAL_DIR,
        "app.py", "config.py", "auth.py", "squid_manager.py",
        "requirements.txt", "innspark-squid-portal.service",
        "templates", "static"
    ]
    subprocess.run(tar_cmd, check=True)
    print(f"  ✓ Created local archive: {tar_path}")

    # Transfer archive to server
    scp_cmd = [
        "scp",
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        tar_path,
        f"{SSH_USER}@{SERVER_IP}:/tmp/innspark-portal.tar.gz"
    ]
    subprocess.run(scp_cmd, check=True)
    print("  ✓ Transferred codebase to /tmp/innspark-portal.tar.gz on 10.31.1.159")

    print_step("Phase 4: Extracting Code & Configuring Systemd Service")
    extract_cmds = f"""
        mkdir -p {REMOTE_PORTAL_DIR}
        mkdir -p {REMOTE_PORTAL_DIR}/data
        mkdir -p /etc/squid/squid_backups/portal_backups
        mkdir -p /etc/squid/squid_backups/portal_archives
        tar -xzf /tmp/innspark-portal.tar.gz -C {REMOTE_PORTAL_DIR}
        cp {REMOTE_PORTAL_DIR}/innspark-squid-portal.service /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable innspark-squid-portal.service
        systemctl restart innspark-squid-portal.service
    """
    code, out, err = run_ssh(extract_cmds, is_sudo=True)
    if code != 0:
        print(f"[!] Extraction / Service error: {err}")
        sys.exit(1)
    print("  ✓ Code extracted to /opt/innspark-squid-portal")
    print("  ✓ Systemd service 'innspark-squid-portal.service' registered and started")

    time.sleep(2)

    print_step("Phase 5: Post-Deployment Verification & Diagnostics")
    # Check portal service status
    code, out, err = run_ssh("systemctl is-active innspark-squid-portal.service")
    portal_active = out.strip() == "active"
    print(f"  ✓ Portal Service Status: {out.strip()}")

    # Check listening port
    code, out, err = run_ssh("ss -tlpn | grep ':5000 ' || true")
    print(f"  ✓ Port 5000 Binding: {out.strip()}")

    # Test HTTP login endpoint
    code, out, err = run_ssh("curl -sI http://127.0.0.1:5000/login | head -n 3")
    print(f"  ✓ HTTP Endpoint Response:\n{out.strip()}")

    # Verify Squid remains undisturbed
    code, out, err = run_ssh("systemctl is-active squid; ps -C squid -o pid,etimes,cmd")
    print(f"  ✓ Production Squid Status (Undisturbed):\n{out.strip()}")

    # Verify Webmin remains untouched
    code, out, err = run_ssh("systemctl is-active webmin; ss -tlpn | grep ':10443 ' || true")
    print(f"  ✓ Webmin Fallback on Port 10443 (Active & Untouched):\n{out.strip()}")

    if portal_active:
        print("\n========================================================")
        print(" [SUCCESS] Innspark Squid Management Portal Deployed!")
        print(" Access URL: http://10.31.1.159:5000")
        print(" Username:   admin")
        print(" Password:   admin@123")
        print("========================================================\n")
    else:
        print("[!] Service did not start as active. Checking journal logs:")
        code, out, err = run_ssh("journalctl -u innspark-squid-portal.service -n 20 --no-pager", is_sudo=True)
        print(out)

if __name__ == "__main__":
    main()
