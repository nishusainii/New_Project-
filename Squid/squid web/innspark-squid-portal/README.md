# Innspark Squid & LDAP Unified Web Portal
**Platform:** Python Flask + Vanilla CSS & JS Single-Page App  
**Target Host:** Server 2 (`proxy.innspark.in` — e.g., `10.31.1.159`)  
**Port:** `5000` (or reverse-proxied over Nginx/Apache on `443`)

---

## 1. Features
- **LDAP Directory Management**:
  - Live query of `ou=people,dc=innspark,dc=in` on Server 1.
  - Form-based user creation (UID, name, email, password, posixAccount UID generator).
  - One-click assignment or removal from `proxy_users` and `proxy_admins`.
  - Permanent user deletion.
- **Domain Whitelist & Blacklist Filtering**:
  - Tag-based domain editor for `/etc/squid/acl/whitelist_domains.txt` and `blacklist_domains.txt`.
  - Instant Squid configuration syntax verification and safe daemon reload (`squid -k reconfigure`).
- **Live Traffic Monitoring**:
  - Streaming real-time requests from `/var/log/squid/access.log`.
  - Filtering by client IP, status code (`200 OK`, `403 Forbidden`, `407 Auth Required`), URL, and username.
- **Embedded SARG Reports**:
  - Embedded audit dashboard with one-click report generator (`/usr/bin/sarg`).
- **System Health Monitor**:
  - Live heartbeat for Squid proxy and OpenLDAP directory server.

---

## 2. Quick 1-Command Deployment on Server 2

Copy the `innspark-squid-portal` directory to Server 2 and execute:

```bash
chmod +x install-portal.sh
sudo ./install-portal.sh
```

---

## 3. Configuration Overrides (`.env` or `config.py`)

Create `/opt/innspark-squid-portal/.env` to override any default settings:

```ini
LDAP_HOST=10.31.1.10
LDAP_PORT=389
BASE_DN=dc=innspark,dc=in
ADMIN_DN=cn=admin,dc=innspark,dc=in
ADMIN_PASSWORD=Innspark@LDAPAdmin2026!
SQUID_CONF_PATH=/etc/squid/squid.conf
WHITELIST_PATH=/etc/squid/acl/whitelist_domains.txt
BLACKLIST_PATH=/etc/squid/acl/blacklist_domains.txt
ACCESS_LOG_PATH=/var/log/squid/access.log
SARG_WEB_URL=http://10.31.1.159:8080/sarg/
```

After modifying settings, restart the service:
```bash
sudo systemctl restart innspark-portal.service
```

---

## 4. Reverse Proxying with Nginx (Optional HTTPS)

If you wish to expose the portal on standard port 443 with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name portal.innspark.in;

    ssl_certificate /etc/ssl/certs/innspark.crt;
    ssl_certificate_key /etc/ssl/private/innspark.key;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
