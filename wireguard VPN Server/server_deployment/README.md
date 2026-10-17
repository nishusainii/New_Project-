# WireGuard Enterprise - Architecture & Server Deployment Guide

Welcome to the **WireGuard Enterprise** deployment package. This directory contains the complete infrastructure definitions, shell automation scripts, configuration templates, and technical documentation for deploying an enterprise-grade Zero-Trust WireGuard VPN gateway.

---

## 📁 Folder Contents

| File / Folder | Purpose |
|---|---|
| `WireGuard_Server_Architecture_and_Deployment_Guide.pdf` | **Comprehensive Technical Specification & Architecture PDF** with embedded flowcharts, diagrams, and command cheatsheets. |
| `setup_host.sh` | Automated host initialization script (kernel modules, `sysctl`, directories, dependencies, and NFTables). |
| `deploy.sh` | Automated application deployment script (Docker image load, file sync, and container startup). |
| `docker-compose.yml` | Container runtime definition with `host` networking, security capabilities (`NET_ADMIN`, `NET_RAW`), and volume mounts. |
| `.env.example` | Production environment variables and secrets template. |
| `nftables.conf.template` | Host firewall baseline configuration template with management SSH, WireGuard UDP 443, ICMP ping, and ZTNA forwarding hooks. |
| `acl.nft.template` | Baseline client Access Control List (ACL) template. |
| `generate_pdf.py` | Python build script used to generate the high-resolution architecture PDF. |

---

## 🚀 Quick Start: 3-Step Server Deployment

### Step 1: Clone / Copy Files to the Server
Ensure this repository or the `server_deployment/` folder is placed on your target Linux host (e.g. at `/root/wireguard VPN Server` or `/opt/wireguard-enterprise`).

```bash
cd "server_deployment"
chmod +x setup_host.sh deploy.sh
```

### Step 2: Initialize the Host
Run the host preparation script as `root` (or with `sudo`):
```bash
sudo ./setup_host.sh
```
*What this does:*
1. Installs `wireguard`, `wireguard-tools`, `nftables`, `docker.io`, and `docker-compose`.
2. Enables kernel packet forwarding (`net.ipv4.ip_forward = 1`) and BBR congestion control.
3. Loads `wireguard.ko` kernel module.
4. Creates directory structure in `/etc/wireguard`, `/etc/nftables`, and `/opt/wireguard-enterprise`.
5. Deploys `/etc/nftables.conf` and `/etc/nftables/acl.nft`, verifies syntax, and enables `nftables.service`.

### Step 3: Deploy the Container
Run the container deployment script:
```bash
sudo ./deploy.sh
```
*What this does:*
1. Synchronizes application source code to `/opt/wireguard-enterprise/app`.
2. Loads the pre-packaged Docker image or builds from Dockerfile.
3. Spawns `wireguard-manager` in Docker with `network_mode: host` and `cap_add: [NET_ADMIN, NET_RAW]`.
4. Performs live health verification on `http://127.0.0.1:8000`.

---

## 🌐 Accessing the Management Dashboard

- **URL:** `http://<SERVER_IP>:8000`
- **Default Username:** `admin`
- **Default Password:** `admin@123`

---

## 🛠️ Operational Command Reference

### Service & Container Management
```bash
# View container status
docker ps -f name=wireguard-manager

# View live application logs
docker logs -f wireguard-manager

# Restart the application container
sudo docker restart wireguard-manager

# Stop the application container
sudo docker stop wireguard-manager
```

### WireGuard Kernel & Network Inspection
```bash
# Check live WireGuard interface and connected peers
sudo wg show wg0

# Check interface IP and packet counters
ip -s addr show wg0

# Verify kernel routing table for VPN clients
ip route show dev wg0
```

### NFTables Firewall Inspection & Reload
```bash
# View all active firewall rules in kernel
sudo nft list ruleset

# View the VPN client ACL chain specifically
sudo nft list chain inet filter vpn_acl

# Validate syntax of firewall rules before applying
sudo nft -c -f /etc/nftables.conf

# Atomically reload firewall rules without dropping connections
sudo nft -f /etc/nftables.conf

# Check systemd firewall service status
sudo systemctl status nftables.service
```

### Database & Peer Backup
```bash
# Create immediate SQLite database snapshot
sudo cp /opt/wireguard-enterprise/data/wireguard.db /opt/wireguard-enterprise/data/wireguard_backup_$(date +%Y%m%d%H%M%S).db

# Backup WireGuard configuration
sudo cp /etc/wireguard/wg0.conf /etc/wireguard/archive/wg0_backup_$(date +%Y%m%d%H%M%S).conf
```
