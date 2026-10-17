# WireGuard Enterprise - Air-Gapped Production Deployment Guide

## 1. Executive Summary & Architecture

This guide provides the complete, deterministic procedure for deploying **WireGuard Enterprise Control Center** in an **Air-Gapped / Zero-Internet Production Environment**.

### Recommended Architecture: Scenario A (Host Kernel + Containerized Control Plane)

In this architecture:
- **Host Linux Kernel (5.6+)**: Runs the high-performance `wireguard.ko` in-tree kernel module. WireGuard cryptographic operations and packet processing occur directly inside the kernel at line-rate speed (zero user-space penalty).
- **Control Center Container (`wireguard-manager`)**: Runs with `network_mode: host` and `cap_add: [NET_ADMIN]`. It directly controls the host's `wg0` network interface and manages the kernel cryptographic routing table.
- **Firewall Integration (`nftables`)**: Host `/etc/nftables.conf` directly manages the firewall and WireGuard access control rules (`table inet wiregate`), guaranteeing zero packet drops, clean syntax validation, and atomic kernel synchronization.
- **Air-Gapped Guarantee**: All application dependencies, Python 3.12 binaries, cryptographic libraries, `nftables`, and `wireguard-tools` are pre-compiled and sealed into a single offline Docker image (`wireguard-enterprise-image.tar.gz`). The production server requires **zero internet access**, **zero package downloads**, and **zero external DNS resolution**.

```
                           AIR-GAPPED LINUX HOST
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                                                                          │
 │  Linux Kernel WireGuard (wg0: 172.29.250.1/24, UDP 443)                 │
 │  Kernel Crypto: Curve25519, ChaCha20-Poly1305, BLAKE2s                   │
 │  NFTables: /etc/nftables.conf (table inet wiregate)                      │
 │                                                                          │
 │  ┌────────────────────────────────────────────────────────────────────┐  │
 │  │ Docker Container: wireguard-manager                                │  │
 │  │ Image: wireguard-enterprise:latest (loaded from offline tar.gz)   │  │
 │  │                                                                    │  │
 │  │   FastAPI Web Engine (Port 8000)                                   │  │
 │  │   Live NOC Telemetry & Metrics Collector                           │  │
 │  │   Real-Time NFTables ACL Sync Engine                               │  │
 │  │   Automated Peer Keypair & QR Code Generator                       │  │
 │  │   Zero-External-Asset Glassmorphism UI (CSS3 + SVG)                │  │
 │  └────────────────────────────────────────────────────────────────────┘  │
 │                                                                          │
 └──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Prerequisites for the Air-Gapped Production Server

Ensure the target production server satisfies these baseline requirements:

| Component | Requirement | Verification Command |
| :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu 20.04+, Debian 11+, RHEL/Rocky 8+, AlmaLinux) | `uname -r` |
| **Kernel Version** | 5.6 or newer (contains built-in `wireguard.ko`) | `modprobe wireguard` |
| **Container Engine**| Docker Engine 20.10+ and Docker Compose v2+ | `docker --version` |
| **IPv4 Forwarding** | Enabled in kernel runtime | `sysctl net.ipv4.ip_forward` |
| **Inbound Ports** | Port **443/UDP** (WireGuard tunnel) and Port **8000/TCP** (Admin Web UI) | `ss -tulpn` |

> **Note on Installing Docker in an Air-Gapped Environment**:  
> If the production host does not yet have Docker installed:
> 1. On your connected machine, download the offline `.deb` or `.rpm` packages from Docker's official package repository:
>    - Ubuntu/Debian: `download.docker.com/linux/ubuntu/dists/<release>/pool/stable/amd64/`
>    - RHEL/CentOS/Rocky: `download.docker.com/linux/centos/<version>/x86_64/stable/Packages/`
> 2. Transfer packages to the production server and install via `dpkg -i *.deb` or `rpm -Uvh *.rpm`.

---

## 3. Step-by-Step Implementation Procedure

### Stage 1: Preparation on Connected Machine (Export Bundle)

Perform these steps on your development workstation or laptop with internet access:

1. **Extract or navigate to the source directory**:
   ```bash
   cd wireguard-enterprise
   ```

2. **Execute the Offline Bundle Exporter**:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/export-offline-bundle.sh
   ```
   *This script builds `wireguard-enterprise:latest` and exports it to `wireguard-enterprise-image.tar.gz`.*

3. **Verify the generated image tarball**:
   ```bash
   ls -lh wireguard-enterprise-image.tar.gz
   ```

4. **Transfer the entire directory** (or the created `.zip` bundle) to the air-gapped production host using your approved secure transfer method (USB storage, SFTP, or internal jumpbox).

---

### Stage 2: Deployment on the Air-Gapped Production Host

Perform these steps logged into the production server as `root` (or with `sudo`):

1. **Unpack the archive**:
   ```bash
   unzip wireguard-enterprise-production.zip -d /opt/wireguard-enterprise
   cd /opt/wireguard-enterprise
   ```

2. **Run Kernel & Environment Verification**:
   ```bash
   chmod +x scripts/*.sh
   ./scripts/verify-host-kernel.sh
   ```
   *This confirms that `wireguard.ko`, Docker, and IP forwarding are ready.*

3. **Configure Host NFTables Integration (Recommended)**:
   ```bash
   ./scripts/setup-host-nftables.sh
   ```
   *Configures `/etc/nftables.conf` directly with standard filter tables and the `table inet wiregate` ruleset, and verifies syntax with `nft -c -f`.*

4. **Execute the Air-Gapped Automated Deployment**:
   ```bash
   ./scripts/deploy-offline.sh
   ```

   **What `deploy-offline.sh` does automatically:**
   - Validates root privileges.
   - Loads the `wireguard` kernel module and persists `net.ipv4.ip_forward = 1` in `/etc/sysctl.d/99-wireguard-forward.conf`.
   - Imports `wireguard-enterprise-image.tar.gz` directly into the local Docker daemon cache via `docker load`.
   - Generates production `.env` configuration with a cryptographically secure random session key.
   - Sets strict permissions on `./data` (`0700`).
   - Launches the containerized service via `docker compose up -d`.
   - Executes an HTTP health probe and outputs credentials.

---

## 4. Verification & Operational Usage

### 1. Access the Web Control Center
Open your browser and navigate to:
```
http://<YOUR_PRODUCTION_SERVER_IP>:8000
```
- **Default Username:** `admin`
- **Default Password:** `adminpassword123` *(Change immediately in `.env`)*

### 2. Verify Kernel Interface Status
Run on the host:
```bash
wg show wg0
ip addr show wg0
```
You will see `wg0` initialized at `172.29.250.1/24`, listening on UDP port `443`.

### 3. Adding and Connecting Peers
1. In the Web UI, navigate to **Peers Management**.
2. Click **Add Peer**:
   - Provide Peer Name (e.g., `Ops-Workstation-01`).
   - Allowed IPs auto-assigns the next IP (e.g., `172.29.250.2/32`).
3. Click **Download Config** or scan the **QR Code** on your client device.
4. Import into your WireGuard client (Windows, macOS, Linux, iOS, Android) and activate the tunnel.
5. In the Web UI, view the real-time handshake, transfer counters, and latency on the **Overview** dashboard.

### 4. Applying Firewall & ACL Policies
1. Navigate to **Firewall & ACL**.
2. View active input/forward chains, default policies, and drop telemetry.
3. Add ACL rules to enforce Zero-Trust access per peer IP or department subnet.

---

## 5. Maintenance & Disaster Recovery

### Inspect Logs
```bash
docker compose logs -f
```

### Restart Service
```bash
docker compose restart
```

### Full Backup (Air-Gapped)
All state (peer database, cryptographic keys, and firewall configurations) is preserved inside the `./data/` directory:
```bash
tar -czvf wireguard-backup-$(date +%F).tar.gz ./data/ .env
```

### Full Restore
```bash
docker compose down
tar -xzvf wireguard-backup-YYYY-MM-DD.tar.gz
docker compose up -d
```

### Updating the Image in Air-Gapped Mode
1. On your connected machine, rebuild and re-export the image:
   ```bash
   docker build -t wireguard-enterprise:latest .
   docker save wireguard-enterprise:latest | gzip > wireguard-enterprise-image.tar.gz
   ```
2. Transfer `wireguard-enterprise-image.tar.gz` to the production host.
3. On the production host:
   ```bash
   docker load < wireguard-enterprise-image.tar.gz
   docker compose down
   docker compose up -d
   ```
   *Your database, peers, and configuration in `./data` remain intact.*
