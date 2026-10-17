# Innspark Squid Proxy Management Portal

A modern, high-performance web administration interface designed specifically for the production Squid Proxy on **`10.31.1.159`** (`proxyserver`).

---

## 1. Quick Access Information

- **Portal URL**: [http://10.31.1.159:5000](http://10.31.1.159:5000)
- **Initial Username**: `nishu`
- **Initial Password**: `nishu`
- **Webmin Fallback**: [https://10.31.1.159:10443](https://10.31.1.159:10443) (Runs concurrently without conflict)

---

## 2. Key Features

1. **Dashboard & Live Telemetry**:
   - Real-time status of Squid daemon (PID, Uptime, Memory usage, CPU consumption).
   - High-level metric counts for users, domain rules, allowed IPs, and access log size.
2. **Proxy Users Management (`/etc/squid/password`)**:
   - Add, edit, delete NCSA htpasswd users.
   - 1-click password reset.
   - Direct assignment to ACL groups (`ai_users`, `github_users`, `core_port_users`, `static_port_users`, `sajan_user`).
3. **User Groups & ACL Rules (`/etc/squid/acl/users/`)**:
   - Visual membership editor with tag chips.
4. **Domain Policies (`/etc/squid/acl/domains/`)**:
   - Categorized domain management: `ai_domains.txt`, `github_domains.txt`, `whatsapp_domains.txt`.
   - Wildcard subdomain support (e.g. `.openai.com`) and exact host matching.
5. **Allowed Client IPs (`/etc/squid/allowed_ips.txt`)**:
   - Subnet CIDR and single host IP whitelisting.
6. **Multi-Port & Egress Route Visualizer**:
   - Visual mapping of the 7 configured ports (`3128`, `8860`, `8859`, `8878`, `8888`, `8898`, `8858`) and their bound outgoing IPs (`192.168.x.30`).
7. **Live Traffic Stream**:
   - Real-time tailing of `/var/log/squid/access.log`.
   - Color-coded HTTP response badges (`200 OK`, `403 FORBIDDEN`, `407 AUTH`).
   - Filter by client IP, username, URL, or status code.
8. **SARG Analytics Integration**:
   - Embedded report viewer with on-demand report generation trigger (`/usr/local/sbin/sarg`).
9. **Direct File Editor**:
   - Syntax-highlighted in-browser editor for `squid.conf`, `allowed_ips.txt`, and all ACL files.
   - Automated pre-flight syntax check (`squid -k parse`) before applying any changes.
10. **Backup & Restore Center (With Automated 5-Snapshot Retention)**:
    - Automatically creates a timestamped backup before any configuration edit.
    - Maintains the **last 5 active backups**.
    - When a new snapshot is created, older backups are automatically rotated and compressed into `/etc/squid/squid_backups/portal_archives/*.tar.gz`.
    - 1-Click **"Extract & Restore"** to revert any changes safely.

---

## 3. Production Safety Architecture

- **Zero Downtime**: Configuration changes are applied via `squid -k reconfigure`. Squid never drops active TCP connections.
- **Port Isolation**: Runs on port `5000`, leaving Apache (`80`), Squid (`3128`, `8858-8898`), and Webmin (`10443`) untouched.
- **Pre-flight Validation**: If a syntax error is introduced during an edit, the portal rejects the change and Squid keeps running smoothly.

---

## 4. Service Management on Server

The portal is managed as a standard systemd daemon on `10.31.1.159`:

```bash
# Check service status
sudo systemctl status innspark-squid-portal.service

# Restart portal
sudo systemctl restart innspark-squid-portal.service

# View live logs
sudo journalctl -u innspark-squid-portal.service -f
```
