#!/usr/bin/env python3
"""
================================================================================
CiSai Squid Proxy Management Portal - Universal Multi-Server Deployer
================================================================================
Deploy or update the management portal on ANY remote Squid proxy server.
Supports both fresh installations and seamless non-destructive updates.
Supports both root and non-root users with sudo privileges.

Usage:
    python3 deploy_to_any_server.py [--ip <SERVER_IP>] [--user <SSH_USER>] [--update]

Examples:
    # Interactive mode (prompts for missing info, auto-detects install vs update):
    python3 deploy_to_any_server.py

    # Quick seamless update of an existing deployment:
    python3 deploy_to_any_server.py --update --ip 10.31.1.200 --user nishu

    # Non-root user with password authentication:
    python3 deploy_to_any_server.py --ip 10.31.1.200 --user nishu --pass nishu

    # Root user with SSH key:
    python3 deploy_to_any_server.py --ip 10.31.1.200 --user root --key ~/.ssh/id_rsa
================================================================================
"""

import os
import sys
import argparse
import subprocess
import getpass
import time
import base64
import tempfile

def print_banner():
    banner = r"""
================================================================================
   ______  _  _____         _ 
  / ____/ (_)/ ___/ ____ _ (_)
 / /     / / \__ \ / __ `// / 
/ /___  / / ___/ // /_/ // /  
\____/ /_/ /____/ \__,_//_/   
  SQUID PROXY MANAGEMENT PORTAL - UNIVERSAL DEPLOYER & UPDATER
================================================================================
"""
    print(banner)

def print_step(phase, title):
    print(f"\n[+] --------------------------------------------------------")
    print(f"[+] Phase {phase}: {title}")
    print(f"[+] --------------------------------------------------------")

def execute_ssh(server_ip, user, password=None, key_file=None, cmd="", is_sudo=False, sudo_password=None):
    """Executes a command on the remote server via OpenSSH with safe base64 encapsulation."""
    ssh_opts = [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        "-o", "LogLevel=ERROR"
    ]
    if key_file and os.path.exists(key_file):
        ssh_opts.extend(["-i", os.path.abspath(key_file)])

    active_sudo_pass = sudo_password if sudo_password is not None else password
    b64_cmd = base64.b64encode(cmd.encode("utf-8")).decode("ascii")

    if is_sudo and user != "root":
        if active_sudo_pass:
            escaped_pass = active_sudo_pass.replace("'", "'\\''")
            full_remote_cmd = f"echo '{escaped_pass}' | sudo -S -p '' bash -c 'echo {b64_cmd} | base64 -d | bash'"
        else:
            full_remote_cmd = f"echo {b64_cmd} | base64 -d | sudo -n bash"
    else:
        full_remote_cmd = f"echo {b64_cmd} | base64 -d | bash"

    has_sshpass = subprocess.run(["which", "sshpass"], capture_output=True).returncode == 0
    env = os.environ.copy()
    askpass_script = None

    try:
        if password and not key_file:
            if has_sshpass:
                ssh_cmd = ["sshpass", "-p", password, "ssh"] + ssh_opts + [f"{user}@{server_ip}", full_remote_cmd]
            else:
                fd, askpass_script = tempfile.mkstemp(prefix="askpass_", suffix=".sh")
                with open(fd, "w") as f:
                    f.write(f"#!/bin/sh\ncat << 'EOF_SSH_PW'\n{password}\nEOF_SSH_PW\n")
                os.chmod(askpass_script, 0o700)
                env["SSH_ASKPASS"] = askpass_script
                env["SSH_ASKPASS_REQUIRE"] = "force"
                env["DISPLAY"] = ":0"
                ssh_cmd = ["ssh"] + ssh_opts + [f"{user}@{server_ip}", full_remote_cmd]
        else:
            ssh_cmd = ["ssh"] + ssh_opts + [f"{user}@{server_ip}", full_remote_cmd]

        res = subprocess.run(ssh_cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        return res.returncode, res.stdout, res.stderr
    finally:
        if askpass_script and os.path.exists(askpass_script):
            try:
                os.remove(askpass_script)
            except OSError:
                pass

def scp_transfer(server_ip, user, password, key_file, local_file, remote_dest):
    """Transfers a file to remote server via SCP."""
    ssh_opts = [
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        "-o", "ConnectTimeout=10",
        "-o", "LogLevel=ERROR"
    ]
    if key_file and os.path.exists(key_file):
        ssh_opts.extend(["-i", os.path.abspath(key_file)])

    has_sshpass = subprocess.run(["which", "sshpass"], capture_output=True).returncode == 0
    env = os.environ.copy()
    askpass_script = None

    try:
        if password and not key_file:
            if has_sshpass:
                scp_cmd = ["sshpass", "-p", password, "scp"] + ssh_opts + [local_file, f"{user}@{server_ip}:{remote_dest}"]
            else:
                fd, askpass_script = tempfile.mkstemp(prefix="askpass_", suffix=".sh")
                with open(fd, "w") as f:
                    f.write(f"#!/bin/sh\ncat << 'EOF_SSH_PW'\n{password}\nEOF_SSH_PW\n")
                os.chmod(askpass_script, 0o700)
                env["SSH_ASKPASS"] = askpass_script
                env["SSH_ASKPASS_REQUIRE"] = "force"
                env["DISPLAY"] = ":0"
                scp_cmd = ["scp"] + ssh_opts + [local_file, f"{user}@{server_ip}:{remote_dest}"]
        else:
            scp_cmd = ["scp"] + ssh_opts + [local_file, f"{user}@{server_ip}:{remote_dest}"]

        res = subprocess.run(scp_cmd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        return res.returncode == 0, res.stderr
    finally:
        if askpass_script and os.path.exists(askpass_script):
            try:
                os.remove(askpass_script)
            except OSError:
                pass

def parse_args():
    parser = argparse.ArgumentParser(description="Deploy or update Squid Management Portal on any Linux server.")
    parser.add_argument("--ip", "-i", help="Target server IP or hostname")
    parser.add_argument("--user", "-u", default=None, help="SSH username (e.g. nishu, ubuntu, root)")
    parser.add_argument("--password", "--pass", "-p", help="SSH password")
    parser.add_argument("--sudo-pass", help="Sudo password for non-root user (if different from SSH password)")
    parser.add_argument("--key", "-k", help="Path to SSH private key file")
    parser.add_argument("--port", type=int, default=5000, help="Portal web port (default: 5000)")
    parser.add_argument("--admin-user", default="admin", help="Default portal admin username (default: admin)")
    parser.add_argument("--admin-pass", default="admin@123", help="Default portal admin password (default: admin@123)")
    parser.add_argument("--update", action="store_true", help="Perform seamless update/upgrade on existing portal installation")
    return parser.parse_args()

def main():
    print_banner()
    args = parse_args()

    # 1. Target server IP
    server_ip = args.ip
    while not server_ip:
        server_ip = input("[?] Enter Target Server IP Address: ").strip()

    # 2. Ask for SSH Username (Never assume root!)
    ssh_user = args.user
    if not ssh_user:
        current_local_user = getpass.getuser()
        entered_user = input(f"[?] Enter SSH Username (e.g. {current_local_user}, ubuntu, root) [{current_local_user}]: ").strip()
        ssh_user = entered_user if entered_user else current_local_user

    key_file = args.key
    ssh_pass = args.password
    sudo_pass = args.sudo_pass

    # 3. Authentication credentials
    if not key_file and not ssh_pass:
        auth_choice = input("[?] Authenticate via Password or SSH Key? [P/k]: ").strip().lower()
        if auth_choice == "k":
            key_file = input("[?] Path to SSH Private Key [~/.ssh/id_rsa]: ").strip() or os.path.expanduser("~/.ssh/id_rsa")
            # If non-root user using key, ask if sudo requires a password
            if ssh_user != "root" and not sudo_pass:
                ask_sudo = getpass.getpass(f"[?] Enter sudo password for '{ssh_user}' (press Enter if passwordless sudo): ").strip()
                if ask_sudo:
                    sudo_pass = ask_sudo
        else:
            ssh_pass = getpass.getpass(f"[?] Enter SSH Password for {ssh_user}@{server_ip}: ")
            if ssh_user != "root" and not sudo_pass:
                same_sudo = input(f"[?] Is sudo password for '{ssh_user}' the same as SSH password? [Y/n]: ").strip().lower()
                if same_sudo == "n":
                    sudo_pass = getpass.getpass(f"[?] Enter sudo password for '{ssh_user}': ").strip()
                else:
                    sudo_pass = ssh_pass

    target_port = args.port
    admin_user = args.admin_user
    admin_pass = args.admin_pass

    local_dir = os.path.dirname(os.path.abspath(__file__))
    remote_portal_dir = "/opt/innspark-squid-portal"

    # --------------------------------------------------------------------------
    # Phase 1: Pre-flight Verification & Connectivity
    # --------------------------------------------------------------------------
    print_step(1, f"Pre-flight Connectivity Check ({ssh_user}@{server_ip})")
    code, out, err = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, "uname -a", sudo_password=sudo_pass)
    if code != 0:
        print(f"[✘] SSH connection failed to {ssh_user}@{server_ip}!")
        print(f"    Error: {err.strip()}")
        sys.exit(1)
    print(f"  ✓ Connected to host: {out.strip()}")

    # Check Squid status
    code_sq, out_sq, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, "which squid || true", is_sudo=True, sudo_password=sudo_pass)
    if not out_sq.strip():
        print(f"  [!] Warning: 'squid' binary was not found in PATH on {server_ip}.")
        cont = input("  [?] Continue anyway? [y/N]: ").strip().lower()
        if cont != "y":
            sys.exit(1)
    else:
        print(f"  ✓ Squid binary detected at: {out_sq.strip()}")

    code_sq_act, out_sq_act, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, "systemctl is-active squid || true", sudo_password=sudo_pass)
    squid_active = out_sq_act.strip() == "active"
    print(f"  ✓ Squid Service Active: {'YES (Undisturbed)' if squid_active else 'NO / STOPPED'}")

    # Check if existing portal installation exists
    code_ex, out_ex, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, f"test -d {remote_portal_dir} && echo 'EXISTS' || echo 'NEW'", is_sudo=True, sudo_password=sudo_pass)
    is_existing = out_ex.strip() == "EXISTS"

    if is_existing:
        print(f"  ✓ Existing portal detected at {remote_portal_dir}")
        if not args.update:
            print("\n[?] Target server already has an active portal installation.")
            print("    [1] Update / Upgrade Codebase (Preserves all credentials & configs, restarts service) [Recommended]")
            print("    [2] Full Re-installation (Re-verify all OS packages and reset service)")
            op_choice = input("    Choose option [1/2, default: 1]: ").strip()
            is_update_mode = op_choice != "2"
        else:
            is_update_mode = True
    else:
        is_update_mode = False

    # Check port availability
    check_port_cmd = f"ss -tln | grep ':{target_port} ' || true"
    code_port, out_port, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, check_port_cmd, is_sudo=True, sudo_password=sudo_pass)
    if out_port.strip():
        code_p, out_p, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, "systemctl is-active innspark-squid-portal.service || true", sudo_password=sudo_pass)
        if out_p.strip() == "active":
            print(f"  ✓ Port {target_port} is running existing Innspark/CiSai Portal (will upgrade seamlessly)")
        else:
            print(f"  [!] Warning: Port {target_port} is currently bound by another service:")
            print(f"      {out_port.strip()}")
            cont = input(f"  [?] Proceed and restart service on port {target_port}? [y/N]: ").strip().lower()
            if cont != "y":
                sys.exit(1)
    else:
        print(f"  ✓ Port {target_port} is available for the portal.")

    # --------------------------------------------------------------------------
    # Phase 2: Remote Dependency Verification & Installation
    # --------------------------------------------------------------------------
    dep_install_cmd = """
        if command -v apt-get &> /dev/null; then
            export DEBIAN_FRONTEND=noninteractive
            apt-get update -qq
            apt-get install -y -qq python3 python3-pip python3-flask python3-requests apache2-utils curl tar gzip
        elif command -v dnf &> /dev/null; then
            dnf install -y -q python3 python3-pip python3-requests httpd-tools curl tar gzip
            pip3 install -q flask "werkzeug<3.0.0" requests || true
        elif command -v yum &> /dev/null; then
            yum install -y -q python3 python3-pip httpd-tools curl tar gzip
            pip3 install -q flask "werkzeug<3.0.0" requests || true
        fi

        if ! python3 -c "import flask, requests" &>/dev/null; then
            pip3 install -q "werkzeug<3.0.0" requests 2>/dev/null || pip3 install --break-system-packages -q "werkzeug<3.0.0" requests 2>/dev/null || true
        fi
    """

    if is_update_mode:
        print_step(2, "Verifying Remote Runtime Environment (Update Mode)")
        fast_check_cmd = """
            if ! python3 -c "import flask, requests" &>/dev/null; then
                echo "MISSING_DEPS"
            else
                echo "DEPS_OK"
            fi
        """
        _, out_fast, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, fast_check_cmd, is_sudo=True, sudo_password=sudo_pass)
        if "MISSING_DEPS" in out_fast:
            print("  [!] Installing required runtime packages...")
            execute_ssh(server_ip, ssh_user, ssh_pass, key_file, dep_install_cmd, is_sudo=True, sudo_password=sudo_pass)
        else:
            print("  ✓ Python3, Flask, and Requests verified on target node (Fast-track update)")
    else:
        print_step(2, "Verifying and Installing Dependencies on Remote Server (Full Install)")
        code_dep, _, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, dep_install_cmd, is_sudo=True, sudo_password=sudo_pass)
        if code_dep != 0:
            print(f"  [!] Note: Dependency check completed with status {code_dep}")
        else:
            print("  ✓ Python3, Flask, Requests, and htpasswd utility verified on target node.")

    # --------------------------------------------------------------------------
    # Phase 3: Packaging Local Codebase
    # --------------------------------------------------------------------------
    print_step(3, "Packaging Portal Codebase")
    tar_path = "/tmp/cisai-squid-portal-deploy.tar.gz"
    if os.path.exists(tar_path):
        os.remove(tar_path)

    tar_cmd = [
        "tar", "-czf", tar_path,
        "--exclude=__pycache__",
        "--exclude=*.pyc",
        "--exclude=.git",
        "-C", local_dir,
        "app.py", "config.py", "auth.py", "squid_manager.py", "nftables_manager.py",
        "deploy_to_any_server.py",
        "requirements.txt", "innspark-squid-portal.service",
        "templates", "static"
    ]
    subprocess.run(tar_cmd, check=True)
    print(f"  ✓ Created archive: {tar_path} ({round(os.path.getsize(tar_path)/1024, 1)} KB)")

    # Transfer archive to target node (/tmp is world-writable)
    success, scp_err = scp_transfer(server_ip, ssh_user, ssh_pass, key_file, tar_path, "/tmp/cisai-portal.tar.gz")
    if not success:
        print(f"[✘] Failed to transfer archive to {server_ip}: {scp_err}")
        sys.exit(1)
    print(f"  ✓ Uploaded package to {server_ip}:/tmp/cisai-portal.tar.gz")

    # --------------------------------------------------------------------------
    # Phase 4: Extraction, Systemd Unit & Credentials Configuration
    # --------------------------------------------------------------------------
    if is_update_mode:
        print_step(4, "Applying Code Update & Preserving Existing Configurations")
        update_cmds = f"""
            # Create automated snapshot backup of current codebase
            mkdir -p {remote_portal_dir}/backups
            tar -czf {remote_portal_dir}/backups/portal-preupdate-$(date +%Y%m%d_%H%M%S).tar.gz \
                -C {remote_portal_dir} app.py config.py auth.py squid_manager.py templates static 2>/dev/null || true

            # Extract updated codebase over /opt/innspark-squid-portal
            tar -xzf /tmp/cisai-portal.tar.gz -C {remote_portal_dir}

            # Update systemd unit and restart service
            cp {remote_portal_dir}/innspark-squid-portal.service /etc/systemd/system/
            systemctl daemon-reload
            systemctl enable innspark-squid-portal.service
            systemctl restart innspark-squid-portal.service
        """
        code_ext, out_ext, err_ext = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, update_cmds, is_sudo=True, sudo_password=sudo_pass)
        if code_ext != 0:
            print(f"[✘] Remote update failed: {err_ext}")
            sys.exit(1)
        print(f"  ✓ Automated pre-update snapshot saved in {remote_portal_dir}/backups/")
        print(f"  ✓ Updated codebase unpacked into {remote_portal_dir}")
        print("  ✓ Systemd service reloaded & restarted")
    else:
        print_step(4, "Configuring Remote Portal & Systemd Service (Fresh Setup)")
        creds_code = f"""
import json
from werkzeug.security import generate_password_hash
creds = {{
    "username": "{admin_user}",
    "password_hash": generate_password_hash("{admin_pass}", method="pbkdf2:sha256")
}}
import os
os.makedirs('{remote_portal_dir}/data', exist_ok=True)
with open('{remote_portal_dir}/data/admin_creds.json', 'w') as f:
    json.dump(creds, f, indent=2)
print("ADMIN_CREDS_INITIALIZED")
"""
        creds_b64 = base64.b64encode(creds_code.encode()).decode()

        extract_cmds = f"""
            mkdir -p {remote_portal_dir}
            mkdir -p {remote_portal_dir}/data
            mkdir -p /etc/squid/acl/users
            mkdir -p /etc/squid/acl/domains
            mkdir -p /etc/squid/acl/ips
            mkdir -p /etc/squid/squid_backups/portal_backups
            mkdir -p /etc/squid/squid_backups/portal_archives

            # Extract codebase
            tar -xzf /tmp/cisai-portal.tar.gz -C {remote_portal_dir}

            # Initialize admin credentials if not already existing
            if [ ! -f "{remote_portal_dir}/data/admin_creds.json" ]; then
                python3 -c "import base64; exec(base64.b64decode('{creds_b64}'))"
            fi

            # Register systemd unit
            cp {remote_portal_dir}/innspark-squid-portal.service /etc/systemd/system/
            systemctl daemon-reload
            systemctl enable innspark-squid-portal.service
            systemctl restart innspark-squid-portal.service
        """
        code_ext, out_ext, err_ext = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, extract_cmds, is_sudo=True, sudo_password=sudo_pass)
        if code_ext != 0:
            print(f"[✘] Remote setup failed: {err_ext}")
            sys.exit(1)
        print(f"  ✓ Unpacked into {remote_portal_dir}")
        print("  ✓ Configured ACL directory structure (/etc/squid/acl/{users,domains,ips})")
        print("  ✓ Systemd service 'innspark-squid-portal.service' registered and started")

    # --------------------------------------------------------------------------
    # Phase 5: Post-Deployment Health Check
    # --------------------------------------------------------------------------
    print_step(5, "Running Post-Deployment Health Diagnostics")
    time.sleep(2)

    code_svc, out_svc, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, "systemctl is-active innspark-squid-portal.service", sudo_password=sudo_pass)
    is_active = out_svc.strip() == "active"
    print(f"  ✓ Portal Service Status: {out_svc.strip()}")

    # Test HTTP endpoint
    code_http, out_http, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{target_port}/login", sudo_password=sudo_pass)
    http_code = out_http.strip()
    print(f"  ✓ Local HTTP Status Code: {http_code}")

    # Verify Squid is still healthy
    code_sq_final, out_sq_final, _ = execute_ssh(server_ip, ssh_user, ssh_pass, key_file, "systemctl is-active squid || true", sudo_password=sudo_pass)
    print(f"  ✓ Squid Proxy Daemon Status: {out_sq_final.strip()} (Undisturbed)")

    op_label = "Updated" if is_update_mode else "Installed"
    print("\n" + "=" * 80)
    if is_active and http_code == "200":
        print(f" [SUCCESS] CiSai Squid Management Portal Successfully {op_label}!")
        print(f" Target Server : {server_ip}")
        print(f" Portal URL    : http://{server_ip}:{target_port}")
        if not is_update_mode:
            print(f" Username      : {admin_user}")
            print(f" Password      : {admin_pass}")
        print(" Service Name  : innspark-squid-portal.service")
        print("=" * 80)
        print("\nUseful Management Commands on Target Node:")
        print(f"  • View Service Logs : sudo journalctl -u innspark-squid-portal -f")
        print(f"  • Restart Portal    : sudo systemctl restart innspark-squid-portal")
        print(f"  • Check Status      : sudo systemctl status innspark-squid-portal\n")
    else:
        print(f" [!] Deployment completed, but service returned status '{out_svc.strip()}' (HTTP {http_code}).")
        print(f"     Run on target server: journalctl -u innspark-squid-portal -n 50 --no-pager")
        print("=" * 80)

if __name__ == "__main__":
    main()
