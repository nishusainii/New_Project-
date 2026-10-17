# CiSai Squid Management Portal - Multi-Server Deployment Guide

This guide explains how to deploy the **CiSai Squid Proxy Management Portal** to any other proxy server in your infrastructure.

---

## Deployment Options

You have two simple ways to implement the portal on other servers:

1. **Option A (Remote Deploy from Workstation)**: Use `deploy_to_any_server.py` to push and install the portal onto any target server via SSH.
2. **Option B (Direct Local Install on Target Node)**: Copy this directory to the target server and run `sudo bash install_local_portal.sh`.

---

## Option A: Remote Deployment from Workstation (Recommended)

Run `deploy_to_any_server.py` from your management workstation.

### 1. Interactive Mode
Simply run the script with no arguments. It will interactively prompt you for the server IP, username, and authentication:
```bash
python3 deploy_to_any_server.py
```

### 2. Password-Based SSH Command
```bash
python3 deploy_to_any_server.py \
  --ip 10.31.1.200 \
  --user nishu \
  --pass "your_password"
```

### 3. SSH Key-Based Command
```bash
python3 deploy_to_any_server.py \
  --ip 10.31.1.200 \
  --user root \
  --key ~/.ssh/id_rsa
```

### 4. Full Custom Parameters (Port, Custom Admin User/Pass)
```bash
python3 deploy_to_any_server.py \
  --ip 10.31.1.200 \
  --user ubuntu \
  --key ~/.ssh/id_rsa \
  --port 5000 \
  --admin-user admin \
  --admin-pass "SuperSecret123!"
```

---

## Option B: Direct Local Install on Target Server

If you copy the portal folder directly to the new proxy server (via USB, SCP, or Git), install it locally in one step:

```bash
# 1. SSH into the new proxy server
ssh user@new-proxy-ip

# 2. Navigate to the copied folder
cd /path/to/portal_files

# 3. Run the installer as root
sudo bash install_local_portal.sh
```

To set custom initial credentials:
```bash
sudo ADMIN_USER="admin" ADMIN_PASS="MySecurePass123" bash install_local_portal.sh
```

---

## What the Installer Automates

Both scripts automatically handle:
1. **Pre-flight Checks**: Detects OS distribution, verifies Squid is installed and running (`systemctl is-active squid`), and verifies port 5000 is open.
2. **Dependency Installation**: Auto-installs `python3`, `python3-pip`, `python3-flask`, `apache2-utils` (for `htpasswd`), and `curl` across Debian/Ubuntu, RHEL, CentOS, AlmaLinux, and Rocky Linux.
3. **Directory Structure**: Sets up `/opt/innspark-squid-portal`, `/opt/innspark-squid-portal/data`, and `/etc/squid/acl/{users,domains,ips}`.
4. **Credential Setup**: Generates secure PBKDF2:SHA-256 hashed admin credentials in `/opt/innspark-squid-portal/data/admin_creds.json`.
5. **Systemd Service**: Registers, enables, and starts `innspark-squid-portal.service` with auto-restart on failure.
6. **Health Check**: Tests the local HTTP response (`HTTP 200 OK`) and confirms Squid is undisturbed.
*(Note: Firewall rules are untouched by the script and can be configured independently by the system administrator).*

---

## Post-Deployment Management on the New Node

Once installed on the new server, manage the portal using standard systemd commands:

```bash
# Check service status
sudo systemctl status innspark-squid-portal

# Restart the service
sudo systemctl restart innspark-squid-portal

# View real-time log output
sudo journalctl -u innspark-squid-portal -f

# Stop the service
sudo systemctl stop innspark-squid-portal
```

---

## Network & Firewall Access

Ensure port `5000` (or your chosen port) is allowed through any upstream enterprise network firewalls:
```bash
# Ubuntu / Debian (UFW)
sudo ufw allow 5000/tcp

# RHEL / CentOS / AlmaLinux (firewalld)
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```
Access the portal at: **`http://<NEW_SERVER_IP>:5000`**
