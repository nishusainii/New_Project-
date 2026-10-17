# Innspark Custom Unified Web Management Portal
**Location:** `squid web/innspark-squid-portal/`  
**Deployment Target:** Server 2 (`proxy.innspark.in` — e.g., `10.31.1.159`)  
**Portal Port:** `5000` (HTTP) or `443` (via Nginx reverse proxy)

---

## 1. Overview

1. **Authentication & Session Control**: Role-based authentication against OpenLDAP with secure session cookies and dedicated login interface (`/login`).
2. **LDAP User Management**: Create users, reset passwords, grant/revoke proxy access group memberships (`proxy_users`, `proxy_admins`), and delete accounts.
3. **Squid Whitelist & Blacklist Rules**: Interactive domain tag editor with automated syntax verification and safe daemon reload (`squid -k reconfigure`).
4. **Live Proxy Traffic Stream**: Real-time log inspector with auto-refresh, pause/resume, search filtering, and HTTP status badge colorization.
5. **Embedded SARG Reports**: Integrated view of daily and historical analytics with an on-demand report generation trigger button.
6. **System Health Heartbeat**: Live connection status of the Squid proxy daemon and the remote OpenLDAP directory server.

---

## 2. Directory Contents (`innspark-squid-portal/`)

```text
innspark-squid-portal/
├── app.py                      # Flask REST API, authentication & core controller logic
├── config.py                   # Centralized configuration (LDAP IP, credentials, paths)
├── requirements.txt            # Python dependencies: flask, ldap3, gunicorn
├── innspark-portal.service     # Systemd background service unit
├── install-portal.sh           # Automated 1-command installer script
├── README.md                   # Technical reference & Nginx HTTPS config
├── templates/
│   ├── index.html              # Modern single-page management dashboard
│   └── login.html              # Cyber-dark authentication portal
└── static/
    ├── css/
    │   └── style.css           # Custom dark theme, glassmorphism, animations
    └── js/
        └── app.js              # State management, live log streaming, modal dialogs
```

---

## 3. Installation on Server 2

### Step 3.1: Copy Portal Folder to Server 2
Copy the `innspark-squid-portal` directory to Server 2:
```bash
scp -r "innspark-squid-portal" user@10.31.1.159:/tmp/
```

### Step 3.2: Run Installer Script
SSH into Server 2 and execute:
```bash
cd /tmp/innspark-squid-portal
chmod +x install-portal.sh
sudo ./install-portal.sh
```

The script will automatically:
- Install Python 3, venv, and pip
- Copy application to `/opt/innspark-squid-portal`
- Create isolated virtual environment and install `ldap3`, `flask`, `gunicorn`
- Configure and start `innspark-portal.service` via systemd
- Allow port 5000 through the UFW firewall

### Step 3.3: Verify Running Service
```bash
sudo systemctl status innspark-portal.service
```
Listening ports verification:
```bash
ss -tulpn | grep 5000
```

---

## 4. Accessing the Portal

Open your web browser from an authorized corporate workstation:
```text
http://10.31.1.159:5000
```

### Key UI Capabilities
- **Overview Dashboard**: Instant metrics on total LDAP users, whitelisted/blacklisted domains, and log size.
- **LDAP Users Tab**:
  - Click **"+ Create New User"** to add a user. The portal creates the `inetOrgPerson` and `posixAccount` object in OpenLDAP and automatically assigns them to `cn=proxy_users`.
  - Click **"Revoke Access"** or **"Grant Access"** to toggle user permissions instantly.
- **Domain ACLs Tab**:
  - Type a domain (e.g. `github.com` or `facebook.com`) and press **Add**.
  - Click **"Save Rules & Reload Squid"** to update `/etc/squid/acl/` files and reload Squid without dropping active client connections.
- **Live Traffic Tab**:
  - Watch real-time client requests stream into the table.
  - Filter by IP, username, or HTTP status (e.g. `403` or `407`).
- **SARG Reports Tab**:
  - View SARG reports directly within the interface or click **"⚡ Generate Report Now"** to re-analyze logs on demand.
