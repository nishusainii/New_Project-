#!/usr/bin/env python3
"""
Dedicated One-Click Deployment & Synchronization Script for Audit Proxy (10.31.212.14)
Server: offsec-asianetproxy (10.31.212.14)
Port: 5000 (Portal), 8085 (Squid Proxy)
User: user1 / Pass: cyberdrift
"""

import os
import sys
import tarfile
import tempfile
import paramiko

TARGET_IP = "10.31.212.14"
SSH_USER = "user1"
SSH_PASS = "cyberdrift"
SSH_PORT = 22
REMOTE_PORTAL_DIR = "/opt/innspark-squid-portal"
SERVICE_NAME = "innspark-squid-portal.service"

LOCAL_DIR = os.path.dirname(os.path.abspath(__file__))

def create_tarball():
    temp_tar = tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False)
    temp_tar.close()
    
    exclude_dirs = {"__pycache__", ".git", ".idea", ".vscode", "data"}
    exclude_files = {".DS_Store", "cisai-squid-portal-deploy.zip", "squid-portal-deployment.zip", "squid-portal-update.zip"}
    
    with tarfile.open(temp_tar.name, "w:gz") as tar:
        for root, dirs, files in os.walk(LOCAL_DIR):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                if f in exclude_files or f.endswith(".pyc") or f.endswith(".tar.gz"):
                    continue
                full_path = os.path.join(root, f)
                arc_name = os.path.relpath(full_path, LOCAL_DIR)
                tar.add(full_path, arcname=arc_name)
    return temp_tar.name

def main():
    print("=" * 70)
    print(f"  DEPLOYING AUDIT PROXY PORTAL CODE TO {TARGET_IP}")
    print("=" * 70)

    print("[1/5] Creating deployment bundle from local folder...")
    tar_path = create_tarball()
    tar_size = os.path.getsize(tar_path)
    print(f"      Bundle created ({tar_size / 1024:.1f} KB)")

    print(f"[2/5] Connecting to {SSH_USER}@{TARGET_IP}:{SSH_PORT}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(TARGET_IP, port=SSH_PORT, username=SSH_USER, password=SSH_PASS, timeout=10)
        print("      Connected successfully.")
    except Exception as e:
        print(f"      Connection failed: {e}")
        sys.exit(1)

    print("[3/5] Uploading bundle via SFTP to /tmp/...")
    sftp = ssh.open_sftp()
    remote_tar = "/tmp/audit_portal_update.tar.gz"
    sftp.put(tar_path, remote_tar)
    sftp.close()
    os.remove(tar_path)
    print("      Upload completed.")

    print(f"[4/5] Extracting bundle to {REMOTE_PORTAL_DIR} and fixing permissions...")
    deploy_cmd = f"""
echo {SSH_PASS} | sudo -S mkdir -p {REMOTE_PORTAL_DIR}
echo {SSH_PASS} | sudo -S tar -xzf {remote_tar} -C {REMOTE_PORTAL_DIR}/
echo {SSH_PASS} | sudo -S chown -R root:root {REMOTE_PORTAL_DIR}
echo {SSH_PASS} | sudo -S chmod 755 {REMOTE_PORTAL_DIR}
echo {SSH_PASS} | sudo -S chmod -R 644 {REMOTE_PORTAL_DIR}/*.py {REMOTE_PORTAL_DIR}/templates/* {REMOTE_PORTAL_DIR}/static/* 2>/dev/null || true
echo {SSH_PASS} | sudo -S chmod -R 755 {REMOTE_PORTAL_DIR}/static {REMOTE_PORTAL_DIR}/templates {REMOTE_PORTAL_DIR}/data 2>/dev/null || true
echo {SSH_PASS} | sudo -S rm -f {remote_tar}
echo {SSH_PASS} | sudo -S systemctl restart {SERVICE_NAME}
"""
    stdin, stdout, stderr = ssh.exec_command(deploy_cmd)
    stdout.channel.recv_exit_status()
    print("      Service restarted.")

    print("[5/5] Verifying service status and health telemetry...")
    stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {SERVICE_NAME}")
    svc_status = stdout.read().decode().strip()
    print(f"      Service Status: {svc_status}")

    stdin, stdout, stderr = ssh.exec_command("curl -s -I http://127.0.0.1:5000/login | head -n 1")
    http_resp = stdout.read().decode().strip()
    print(f"      Local Web Check: {http_resp}")

    ssh.close()
    print("=" * 70)
    print(f"  DEPLOYMENT COMPLETE! Dashboard URL: http://{TARGET_IP}:5000")
    print("=" * 70)

if __name__ == "__main__":
    main()
