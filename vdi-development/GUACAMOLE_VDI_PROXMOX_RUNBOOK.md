# Production Runbook: Apache Guacamole Enterprise VDI Gateway on Proxmox VE

This document is an end-to-end, enterprise-grade engineering runbook for designing, deploying, securing, and operating an **Apache Guacamole Clientless Remote Desktop Gateway** in front of a **Proxmox Virtual Environment (PVE)** VDI cluster hosting **Ubuntu 24.04 LTS (xrdp)** and **Windows 10/11 (RDP)** virtual desktop workloads.

---

## 1. Intended Architecture

### 1.1 Architectural Rationale
Virtual Desktop Infrastructure (VDI) in high-density environments requires a clientless, hardware-accelerated, and strictly isolated gateway layer. Exposing internal hypervisor networks or VM Remote Desktop ports (TCP 3389) directly to end users introduces substantial attack surface. 

Apache Guacamole provides an HTML5 clientless gateway that translates web browser transports (HTTPS, WebSockets) to enterprise remote display protocols (RDP, TLS, NLA) without requiring any client-side software, agent, or browser plugin.

```
+---------------------------------------------------------------------------------------------------------+
|                                    Remote Users (Any Modern Web Browser)                                |
+---------------------------------------------------------------------------------------------------------+
                                                     │  HTTPS (TCP 443) + WSS (Secure WebSockets)
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
|                                 Guacamole Production Gateway Host (DMZ)                                 |
|                                                                                                         |
|  +---------------------------------------------------------------------------------------------------+  |
|  |                   Nginx Edge Reverse Proxy (TLS Termination, HSTS, WebSocket Upgrade)             |  |
|  +---------------------------------------------------------------------------------------------------+  |
|                                                    │  HTTP (TCP 8080)
|                                                    ▼
|  +---------------------------------------------------------------------------------------------------+  |
|  |                              Apache Guacamole Web Client (Apache Tomcat)                          |  |
|  |                                                                                                   |  |
|  |  +------------------------+  +-------------------------+  +------------------------------------+  |  |
|  |  | guacamole-auth-ldap    |  | guacamole-auth-totp     |  | guacamole-auth-jdbc-postgresql    |  |  |
|  |  | (Active Directory SSO) |  | (RFC 6238 2FA Engine)   |  | (Permissions, Records, Connections)|  |  |
|  |  +------------------------+  +-------------------------+  +------------------------------------+  |  |
|  +---------------------------------------------------------------------------------------------------+  |
|                                                    │  Guacamole Protocol (TCP 4822)
|                                                    ▼
|  +---------------------------------------------------------------------------------------------------+  |
|  |                       guacd Daemon (Native C Protocol Translation Engine)                         |  |
|  +---------------------------------------------------------------------------------------------------+  |
+----------------------------------------------------+----------------------------------------------------+
                                                     │  RDP / TLS / NLA (TCP 3389) [Isolated VDI Subnet]
                                                     ▼
+---------------------------------------------------------------------------------------------------------+
|                                  Proxmox Virtual Environment (PVE)                                      |
|                                                                                                         |
|  +--------------------------------------------------+  +---------------------------------------------+  |
|  |       Ubuntu 24.04 LTS Golden Image VM           |  |      Windows 10 / 11 Golden Image VM        |  |
|  |  - Display: XFCE Desktop Environment             |  |  - Display: Native Windows Desktop (DWM)    |  |
|  |  - Service: xrdp + xorgxrdp (TCP 3389)           |  |  - Service: Remote Desktop Service (TermSrv)|  |
|  |  - Audio: pulseaudio-module-xrdp                 |  |  - Security: Network Level Auth (NLA)       |  |
|  |  - Agent: QEMU Guest Agent (qemu-ga)             |  |  - Drivers: VirtIO SCSI & NetKVM Suite      |  |
|  +--------------------------------------------------+  +---------------------------------------------+  |
+---------------------------------------------------------------------------------------------------------+
```

### 1.2 Specification Summary
- **Hypervisor Host**: Proxmox VE 8.x (`prox000innspark` - `10.31.1.163`)
- **Gateway Host**: Dedicated Ubuntu Server 24.04 LTS (`10.31.4.55`)
- **Container Architecture**: Docker Engine 26.x + Docker Compose v2
- **Directory Services**: Active Directory / Samba 4 LDAP (`sAMAccountName`)
- **Multi-Factor Engine**: `guacamole-auth-totp` (RFC 6238 rolling 6-digit codes)
- **Database Engine**: PostgreSQL 16 Alpine (Connection profiles and audit logs)
- **Edge Reverse Proxy**: Nginx 1.27 Alpine (TLS 1.2/1.3, HTTP/2, WebSockets)

---

## 2. Network & Firewall Topology

| Port / Protocol | Direction | Source | Destination | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **TCP 80** | Inbound | Client LAN/WAN | Gateway (Nginx) | HTTP plaintext redirect to HTTPS 443 |
| **TCP 443** | Inbound | Client LAN/WAN | Gateway (Nginx) | HTTPS web client &amp; WSS WebSocket transport |
| **TCP 389 / 636** | Outbound | Gateway (Guacamole) | AD Domain Controller | LDAP authentication &amp; group queries |
| **TCP 3389** | Outbound | Gateway (guacd) | Proxmox VDI Subnet | RDP transport to Ubuntu (xrdp) &amp; Windows VMs |
| **TCP 4822** | Internal | Guacamole Web | guacd Daemon | Guacamole internal protocol (bridge network) |
| **TCP 5432** | Internal | Guacamole Web | PostgreSQL DB | Relational data &amp; permission queries |

---

## 3. Production Deployment (Docker Compose)

### 3.1 Initial Directory & Database Schema Setup
```bash
mkdir -p /opt/guacamole/{init,nginx/conf.d,nginx/certs,data/postgres,data/record}
cd /opt/guacamole

# Extract the official PostgreSQL relational schema
docker run --rm guacamole/guacamole:1.5.5 /opt/guacamole/bin/initdb.sh --postgresql > /opt/guacamole/init/initdb.sql
```

### 3.2 Docker Compose Configuration (`docker-compose.yml`)
Save the following configuration to `/opt/guacamole/docker-compose.yml`:

```yaml
version: '3.8'

services:
  # 1. guacd: Native C Protocol Translation Daemon
  guacd:
    image: guacamole/guacd:1.5.5
    container_name: guacd
    restart: always
    volumes:
      - ./data/record:/var/lib/guacamole/recordings:rw
    networks:
      - guac-backend
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

  # 2. PostgreSQL: Connection Profiles, Permissions & Auditing
  guac-db:
    image: postgres:16-alpine
    container_name: guac-db
    restart: always
    environment:
      POSTGRES_DB: guacamole_db
      POSTGRES_USER: guac_admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./init/initdb.sql:/docker-entrypoint-initdb.d/initdb.sql:ro
      - ./data/postgres:/var/lib/postgresql/data:rw
    networks:
      - guac-backend
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U guac_admin -d guacamole_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 3. Guacamole Client: Web Application (Tomcat) + Auth Plugins
  guacamole:
    image: guacamole/guacamole:1.5.5
    container_name: guacamole
    restart: always
    depends_on:
      guac-db:
        condition: service_healthy
      guacd:
        condition: service_started
    environment:
      GUACD_HOSTNAME: guacd
      GUACD_PORT: 4822
      POSTGRESQL_HOSTNAME: guac-db
      POSTGRESQL_PORT: 5432
      POSTGRESQL_DATABASE: guacamole_db
      POSTGRESQL_USER: guac_admin
      POSTGRESQL_PASSWORD: ${DB_PASSWORD}

      # Active Directory / LDAP Authentication Provider
      LDAP_HOSTNAME: ${AD_DC_IP}
      LDAP_PORT: 389
      LDAP_ENCRYPTION_METHOD: none # Use 'starttls' or 'ssl' for production DC
      LDAP_SEARCH_BIND_DN: ${AD_BIND_DN}
      LDAP_SEARCH_BIND_PASSWORD: ${AD_BIND_PASSWORD}
      LDAP_USER_BASE_DN: ${AD_USER_BASE_DN}
      LDAP_USERNAME_ATTRIBUTE: sAMAccountName
      LDAP_USER_SEARCH_FILTER: "(&(objectClass=user)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
      LDAP_GROUP_BASE_DN: ${AD_GROUP_BASE_DN}
      LDAP_GROUP_NAME_ATTRIBUTE: cn

      # Two-Factor Authentication (TOTP / RFC 6238)
      TOTP_ENABLED: "true"
      TOTP_ISSUER: "Innspark Enterprise VDI"
      TOTP_DIGITS: 6
      TOTP_PERIOD: 30
      TOTP_MODE: "sha1"
    networks:
      - guac-backend
      - guac-frontend

  # 4. Nginx: SSL Termination & WebSocket Gateway
  nginx:
    image: nginx:1.27-alpine
    container_name: guac-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - guacamole
    networks:
      - guac-frontend

networks:
  guac-backend:
    internal: true
  guac-frontend:
    driver: bridge
```

### 3.3 Environment Secrets Configuration (`.env`)
Create `/opt/guacamole/.env` (`chmod 600 .env`):
```ini
# PostgreSQL Credentials
DB_PASSWORD=P9x#vL7$qK2@mE4!EnterpriseSecurePass

# Active Directory Domain Controller Configuration
AD_DC_IP=10.31.1.10
AD_BIND_DN=CN=svc_guacamole,OU=ServiceAccounts,DC=innspark,DC=local
AD_BIND_PASSWORD=SvcAccountPasswordSecure2026!
AD_USER_BASE_DN=OU=VDIUsers,DC=innspark,DC=local
AD_GROUP_BASE_DN=OU=VDIGroups,DC=innspark,DC=local
```

---

## 4. Edge Nginx Reverse Proxy & WebSockets

Save to `/opt/guacamole/nginx/conf.d/guacamole.conf`:

```nginx
server {
    listen 80;
    server_name vdi.innspark.local;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name vdi.innspark.local;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    client_max_body_size 1024M;

    location / {
        proxy_pass http://guacamole:8080/guacamole/;
        proxy_buffering off;
        proxy_http_version 1.1;

        # WebSocket Upgrade Directives
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $http_connection;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
```

---

## 5. Proxmox Golden VM Connection Profiles

### 5.1 Windows 10 / 11 Golden Image Profile (Native RDP)
- **Protocol:** `RDP`
- **Hostname:** Static IP of Windows VM (e.g. `10.31.1.170`)
- **Port:** `3389`
- **Username:** `${GUAC_USERNAME}` *(Passes corporate AD username)*
- **Password:** `${GUAC_PASSWORD}` *(Passes corporate AD password)*
- **Security Mode:** `NLA` (Network Level Authentication)
- **Ignore Server Certificate:** `true`
- **Color Depth:** `True color (24-bit)`
- **Font Smoothing:** `true`
- **Enable Audio:** `true`
- **Enable Drive:** `true` *(Enables web-based drag-and-drop file transfers)*

### 5.2 Ubuntu 24.04 LTS Golden Image Profile (xrdp / xorgxrdp)
- **Protocol:** `RDP`
- **Hostname:** Static IP of Ubuntu VM (e.g. `10.31.1.171`)
- **Port:** `3389`
- **Username:** `${GUAC_USERNAME}`
- **Password:** `${GUAC_PASSWORD}`
- **Security Mode:** `Any` or `TLS`
- **Resize Method:** `Display Update` *(Dynamically resizes XFCE desktop resolution on browser window resize)*
- **Color Depth:** `True color (24-bit)`
- **Enable Audio:** `true` *(Streams via pulseaudio-module-xrdp)*

---

## 6. Security Hardening & Operations

### 6.1 Disabling Default Administrator
1. Log in via web interface with `guacadmin / guacadmin`.
2. Create an enterprise administrative account or assign admin privileges to an Active Directory group.
3. Log in as the new administrator.
4. Disable or delete the default `guacadmin` user.

### 6.2 Session Screen Recording for Compliance
- Set **Recording path** to: `/var/lib/guacamole/recordings`
- Set **Recording name** to: `${GUAC_USERNAME}-${GUAC_STARTDATE}-${GUAC_STARTTIME}.guac`
- Check **Automatically create recording path**
- To convert to MP4:
  ```bash
  docker exec -it guacd guacenc -s 1920x1080 /var/lib/guacamole/recordings/session.guac
  ```

### 6.3 Nightly Automated Backup
Save to `/opt/guacamole/scripts/backup-guacamole.sh` (`chmod 700`):
```bash
#!/usr/bin/env bash
set -euo pipefail
BACKUP_DIR="/var/backups/guacamole"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

mkdir -p "${BACKUP_DIR}"
docker exec guac-db pg_dump -U guac_admin guacamole_db | gzip > "${BACKUP_DIR}/guac_db_${TIMESTAMP}.sql.gz"
tar -czf "${BACKUP_DIR}/guac_config_${TIMESTAMP}.tar.gz" -C /opt/guacamole docker-compose.yml .env nginx/
find "${BACKUP_DIR}" -type f -name "*.gz" -mtime +30 -delete
```
Schedule via root crontab:
```cron
0 2 * * * /opt/guacamole/scripts/backup-guacamole.sh >> /var/log/guacamole_backup.log 2>&1
```
