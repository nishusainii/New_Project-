# INNSPARK ENTERPRISE CCTV DASHBOARD // SERVER DEPLOYMENT & VAPT MANUAL

Comprehensive enterprise operations guide for deploying, configuring, hardening, and maintaining the **24-Camera Surveillance Operations Center (SOC)** on a Linux production server.

---

## 📋 Table of Contents
1. [System Specifications & Architecture](#1-system-specifications--architecture)
2. [Network & Firewall Port Allocation](#2-network--firewall-port-allocation)
3. [Quick Automated Deployment (1 Command)](#3-quick-automated-deployment-1-command)
4. [Step-by-Step Manual Deployment (Every Command Explained)](#4-step-by-step-manual-deployment-every-command-explained)
5. [Nginx Reverse Proxy & SSL/TLS Configuration](#5-nginx-reverse-proxy--ssltls-configuration)
6. [VAPT & Security Hardening Verification](#6-vapt--security-hardening-verification)
7. [Operational Commands & Troubleshooting](#7-operational-commands--troubleshooting)

---

## 1. System Specifications & Architecture

- **Operating System**: Ubuntu 22.04 / 24.04 LTS, Debian 12, or RHEL / Rocky Linux 9 (x86_64 architecture).
- **CPU**: 4 Cores recommended (handles 24 WebRTC streams with on-demand remuxing).
- **RAM**: 8 GB RAM recommended (16 GB for high concurrency multi-user viewing).
- **Storage**: SSD with minimum 20 GB free space (plus dedicated storage if recording video to disk).
- **Runtime**: Node.js v20.x+ LTS & MediaMTX v1.21.2 gateway binary.

---

## 2. Network & Firewall Port Allocation

Ensure your network infrastructure / security groups permit the following ports:

| Port | Protocol | Scope | Purpose |
| :--- | :--- | :--- | :--- |
| **`3000`** | TCP | Internal / Reverse Proxy | Node.js Express Web Dashboard & REST API |
| **`80`** | TCP | Public / LAN | HTTP Web Traffic (Redirects to HTTPS) |
| **`443`** | TCP | Public / LAN | HTTPS Encrypted Web Traffic |
| **`8554`** | TCP | LAN / Subnet | MediaMTX RTSP Ingestion & Re-streaming |
| **`8889`** | TCP | LAN / WAN | MediaMTX WebRTC (WHEP) HTTP Signaling |
| **`8189`** | UDP | LAN / WAN | MediaMTX WebRTC ICE Media Stream |
| **`8888`** | TCP | LAN / WAN | MediaMTX Low-Latency HLS Stream Fallback |
| **`9997`** | TCP | **Localhost Only** (`127.0.0.1`) | MediaMTX Dynamic Control API (Hardened) |

---

## 3. Quick Automated Deployment (1 Command)

If you uploaded the deployment package to your Linux server, run the automated installation script as root:

```bash
# 1. Extract the package
unzip inncctv-enterprise-linux.zip -d /tmp/inncctv-pkg
cd /tmp/inncctv-pkg

# 2. Run the automated installer
sudo bash deploy/setup-server.sh
```

The script automatically:
1. Installs Node.js LTS, `ffmpeg`, `ufw`, and system utilities.
2. Creates an unprivileged system service account (`inncctv`).
3. Deploys the code to `/opt/inncctv` with strict permissions.
4. Installs production Node.js dependencies (`npm install --omit=dev`).
5. Configures and starts the background `systemd` service.
6. Opens necessary UFW firewall ports.

---

## 4. Step-by-Step Manual Deployment (Every Command Explained)

If you prefer to deploy step-by-step with complete manual control, execute the following commands in sequence:

### Step 4.1: Update System Packages & Install Prerequisites
```bash
sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y curl wget unzip ffmpeg ufw nginx
```

### Step 4.2: Install Node.js LTS (v20+)
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
npm -v
```

### Step 4.3: Create a Dedicated Non-Root System User
For security hardening, never run camera services as `root`:
```bash
sudo useradd -r -s /usr/sbin/nologin -d /opt/inncctv inncctv
```

### Step 4.4: Extract Code to `/opt/inncctv`
```bash
sudo mkdir -p /opt/inncctv
sudo unzip inncctv-enterprise-linux.zip -d /opt/inncctv/
```

### Step 4.5: Install Production Dependencies
```bash
cd /opt/inncctv
sudo npm install --omit=dev
```

### Step 4.6: Set Executable Flags and Secure Permissions
```bash
sudo chmod +x /opt/inncctv/bin/mediamtx
sudo chmod +x /opt/inncctv/start.sh
sudo chown -R inncctv:inncctv /opt/inncctv
```

### Step 4.7: Configure Systemd Background Service
Create the service unit file to ensure the application starts automatically on server boot:
```bash
sudo cp /opt/inncctv/deploy/inncctv.service /etc/systemd/system/inncctv.service
sudo systemctl daemon-reload
sudo systemctl enable inncctv.service
sudo systemctl start inncctv.service
```

Verify service status:
```bash
sudo systemctl status inncctv.service
```

### Step 4.8: Configure UFW Firewall
```bash
sudo ufw allow 22/tcp comment "SSH Remote Administration"
sudo ufw allow 80/tcp comment "HTTP Web Proxy"
sudo ufw allow 443/tcp comment "HTTPS Web Proxy"
sudo ufw allow 3000/tcp comment "Innspark CCTV Dashboard"
sudo ufw allow 8554/tcp comment "MediaMTX RTSP Port"
sudo ufw allow 8889/tcp comment "MediaMTX WebRTC Port"
sudo ufw allow 8189/udp comment "MediaMTX WebRTC ICE UDP"
sudo ufw allow 8888/tcp comment "MediaMTX HLS Port"
sudo ufw enable
```

---

## 5. Nginx Reverse Proxy & SSL/TLS Configuration

To expose the dashboard on standard port 80/443 with HTTPS and WebSocket proxying:

### Step 5.1: Copy Nginx Site Configuration
```bash
sudo cp /opt/inncctv/deploy/nginx-inncctv.conf /etc/nginx/sites-available/inncctv
sudo ln -sf /etc/nginx/sites-available/inncctv /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Step 5.2: Install Free SSL Certificate (Let's Encrypt / Certbot)
```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d cctv.yourcompany.com
```

---

## 6. VAPT & Security Hardening Verification

This dashboard has been engineered and tested against the **OWASP Top 10** and Enterprise VAPT requirements:

### Security Controls Implemented:
1. **Password Storage**: Passwords are never stored in plaintext. They are protected using **`scrypt` cryptographic key derivation** with 16-byte random salts and verified using constant-time comparisons (`crypto.timingSafeEqual`) to defeat timing side-channel attacks.
2. **Session Security**: Session tokens are cryptographically signed using **HMAC-SHA256** with an 8-hour expiration.
3. **Anti-Brute-Force Rate Limiting**: Client IPs are locked out for 15 minutes after 5 consecutive failed login attempts on `/api/auth/login`.
4. **Information Disclosure Protection**: `X-Powered-By` header is stripped from all HTTP responses.
5. **Clickjacking & XSS Protection**: `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, and a strict `Content-Security-Policy` are enforced on all routes.
6. **Command Injection Defense**: Strict regex validation on IP addresses (`IPv4`) and RTSP URLs prevents command injection metacharacters (`;`, `&`, `|`, `` ` ``, `$`).
7. **Internal API Isolation**: MediaMTX management API (`9997`) is bound strictly to `127.0.0.1:9997`, inaccessible from outside the server.

### How to Run VAPT Verification Commands:

```bash
# 1. Verify Security Headers (No information leakage)
curl -s -I http://localhost:3000/ | grep -E "(X-Frame|X-Content|X-XSS|Content-Security|X-Powered-By)"

# Expected Output:
# X-Frame-Options: SAMEORIGIN
# X-Content-Type-Options: nosniff
# X-XSS-Protection: 1; mode=block
# Content-Security-Policy: default-src 'self' ...
# (No X-Powered-By header)

# 2. Test Input Injection Sanitization
curl -s -X POST http://localhost:3000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","floor":1,"ip":"invalid-ip","rtspUrl":"rtsp://evil;rm -rf /"}'

# Expected Output:
# {"success":false,"errors":["Invalid IPv4 address format.","RTSP URL contains forbidden shell metacharacters."]}

# 3. Test Brute-Force Rate Limiter
# (Sending 6 bad requests will return HTTP 429 Too Many Requests on the 6th attempt)
```

---

## 7. Operational Commands & Troubleshooting

### Check Service Status
```bash
sudo systemctl status inncctv.service
```

### Restart Service
```bash
sudo systemctl restart inncctv.service
```

### Stop Service
```bash
sudo systemctl stop inncctv.service
```

### View Live Real-Time Logs
```bash
sudo journalctl -u inncctv.service -f
```

### Back Up Camera Configurations
The entire 24-camera configuration and layout is stored in a single JSON file:
```bash
# Backup
sudo cp /opt/inncctv/config/cameras.json /opt/cameras_backup_$(date +%F).json

# Restore
sudo cp /opt/cameras_backup_2026-10-15.json /opt/inncctv/config/cameras.json
sudo systemctl restart inncctv.service
```

---

## 🔐 Default Access Credentials

- **URL**: `http://<SERVER_IP>:3000` or `https://cctv.yourcompany.com`
- **Administrator**: `admin` / `innspark@2026`
- **SOC Operator**: `operator` / `innspark@2026`
- **Floor Supervisor**: `supervisor` / `innspark@2026`

*(To change passwords in production, set `ADMIN_PASSWORD=your_new_password` in `/etc/systemd/system/inncctv.service` and restart the service).*
