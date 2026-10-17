# Dockerized Secure Wi-Fi Server Stack (802.1X + FreeRADIUS + LDAP + DHCP)

This project provides a complete, containerized enterprise Wi-Fi authentication and IP allocation infrastructure on Ubuntu Server using Docker and Docker Compose.

---

## 1. Architecture

```
+-------------------+        802.1X (EAP-PEAP / EAP-TTLS)       +--------------------+
|  Wireless Client  | <=======================================> |  Wi-Fi Access Point|
| (Laptop / Mobile) |                                           |  (Authenticator)   |
+-------------------+                                           +--------------------+
          | DHCP (UDP 67/68)                                               |
          | (Dynamic IP allocation)                                        | RADIUS Auth (UDP 1812)
          v                                                                v
+------------------------------------------------------------------------------------+
|                           DOCKER HOST (UBUNTU SERVER)                              |
|                                                                                    |
|  +---------------------+      +---------------------+      +--------------------+  |
|  |     wifi-dhcp       |      |   wifi-freeradius   |      |   wifi-openldap    |  |
|  |  (ISC-DHCP Server)  |      | (FreeRADIUS 802.1X) | <==> | (Directory Server) |  |
|  |  [network: host]    |      |  [network: host]    |      |  [network: host]   |  |
|  +---------------------+      +---------------------+      +--------------------+  |
|                                                                      ^             |
|                               +---------------------+                |             |
|                               |   wifi-ldap-admin   |                |             |
|                               | (Innspark Web Portal| ===============+             |
|                               |   Port 8088 (Web)   |                              |
|                               +---------------------+                              |
+------------------------------------------------------------------------------------+
```

### Why `network_mode: host` is used:
1. **ISC-DHCP:** DHCP Discover packets are raw Layer 2 broadcasts (`255.255.255.255:67`). Standard Docker bridge networks block broadcast traffic; host network mode enables direct reception on physical interfaces.
2. **FreeRADIUS:** AP requests arrive on UDP 1812 without source-NAT translation, ensuring exact IP matching in `clients.conf`.
3. **No iptables overhead:** Eliminates Docker bridge NAT conflicts.

---

## 2. Directory Structure

```
wifi-auth-docker/
├── docker-compose.yml       # Defines all 4 services
├── .env                     # Credentials, interface names, and ports
├── seed-ldap.sh             # Seeds initial users & Wi-Fi group into LDAP
├── test-auth.sh             # Automated RADIUS <-> LDAP test script
├── test-hardened-suite.sh   # BlastRADIUS and 100-concurrency stress test
├── vapt-audit.sh            # Automated 11-point security audit script
├── ldap/
│   └── users.ldif           # Bootstrap LDIF (Users, Wi-Fi group, passwords)
├── radius/
│   ├── Dockerfile           # FreeRADIUS image with LDAP module enabled
│   ├── clients.conf         # Authorized Access Points & shared secret
│   └── mods-available/
│       └── ldap             # FreeRADIUS LDAP connection config
├── web-admin/               # Modern Enterprise Web Dashboard
│   ├── Dockerfile           # Python 3.11 + Gunicorn
│   ├── requirements.txt     # Flask & ldap3
│   ├── app.py               # REST API, session auth & LDAP integration
│   ├── templates/
│   │   ├── login.html       # Enterprise dark-glassmorphism login portal
│   │   └── index.html       # Modern administration & monitoring dashboard
│   └── static/              # CSS styles & client JavaScript
└── dhcp/
    └── data/
        ├── dhcpd.conf       # DHCP subnet pool, gateway, DNS
        └── dhcpd.leases     # Dynamic lease database
```

---

## 3. Quick Start

### Step 1: Start LDAP, Web Console, and FreeRADIUS
From the `wifi-auth-docker` directory:
```bash
docker compose up -d openldap web-admin freeradius
```

### Step 2: Seed the LDAP Directory with Initial Users
Run the automated seed script:
```bash
./seed-ldap.sh
```
This automatically initializes:
- Security Group: `cn=wifi-users,ou=Groups,dc=innspark,dc=in`
- User 1: `john.doe@innspark.in` / Password: `WifiPassword2026!`
- User 2: `alice.smith@innspark.in` / Password: `WifiPassword2026!`

### Step 3: Verify Authentication
Execute the automated test script:
```bash
./test-auth.sh
```
*Expected output:*
```
Received Access-Accept Id 216 from 127.0.0.1:1812 length 38
===> SUCCESS: User 'john.doe' authenticated successfully via LDAP!
Received Access-Reject Id 104 from 127.0.0.1:1812 length 38
===> SUCCESS: Rogue / invalid password was properly REJECTED!
```

---

## 4. Managing Users with Enterprise Web Console

1. Open your browser and navigate to:
   ```
   http://<server-ip>:8088
   ```
2. **Secure Login Gateway:** You are automatically presented with the enterprise authentication screen before accessing the management dashboard.
3. **Sign In Credentials:**
   - **Root Admin:** `admin` (or `cn=admin,dc=innspark,dc=in`)
   - **Password:** `AdminPassword123!` (or value from `.env`)
   - **Corporate Users:** Standard employees (e.g. `john.doe@innspark.in`) can also sign in with their directory credentials.
4. **Dashboard Features:**
   - Real-time OpenLDAP directory & FreeRADIUS AAA health indicators.
   - Live KPI counters (Total Employees, Wi-Fi Authorized, Security Status).
   - Instant 1-click Wi-Fi access toggle (adds/removes `memberUid` in `cn=wifi-users`).
   - One-click employee password reset modal.
   - Real-time AAA diagnostic simulator testing 802.1X PEAP/TTLS credentials.
   - Secure session badge and top-header **Sign Out** button.

---

## 5. Configuring the Wi-Fi Access Point (AP)

Configure your physical Access Point (UniFi, Cisco, Aruba, MikroTik, TP-Link, OpenWrt):

| Setting | Value | Description |
| :--- | :--- | :--- |
| **SSID Security** | `WPA2/WPA3-Enterprise (802.1X)` | Enterprise authentication |
| **RADIUS Auth IP** | `<your-ubuntu-server-ip>` | Host IP where Docker runs |
| **RADIUS Auth Port** | `1812` | Standard UDP port |
| **RADIUS Secret** | `SafeRadiusSharedSecret2026!` | Matches `radius/clients.conf` |
| **RADIUS Acct Port** | `1813` | Standard UDP port |
| **PMF (802.11w)** | `Required` or `Optional` | Protects against deauth attacks |

---

## 6. Configuring DHCP Server for Wi-Fi Clients

ISC-DHCP requires that the subnet in `dhcp/data/dhcpd.conf` matches the IP address assigned to the host interface.

1. Check your host's network interface and IP:
   ```bash
   ip -br addr
   ```
2. Edit `dhcp/data/dhcpd.conf` to declare your Wi-Fi subnet:
   ```conf
   subnet 192.168.10.0 netmask 255.255.255.0 {
       range 192.168.10.50 192.168.10.200;
       option routers 192.168.10.1;
       option domain-name-servers 1.1.1.1, 8.8.8.8;
       option domain-name "corp.internal";
   }
   ```
3. Set your interface name in `.env` (e.g. `DHCP_INTERFACE=enp44s0` or `vlan10`).
4. Start the DHCP service:
   ```bash
   docker compose --profile dhcp up -d dhcp
   ```
5. View active IP leases in real time:
   ```bash
   cat dhcp/data/dhcpd.leases
   ```

---

## 7. Connecting Client Devices

* **Windows 10/11:** Connect to SSID $\rightarrow$ enter LDAP username (e.g. `john.doe`) and password (`WifiPassword2026!`).
* **Android:** Select SSID $\rightarrow$ EAP Method: `PEAP` or `TTLS` $\rightarrow$ Phase 2: `MSCHAPv2` or `PAP` $\rightarrow$ Identity: `john.doe`, Password: `WifiPassword2026!`.
* **iOS / macOS:** Connect to SSID $\rightarrow$ Enter credentials $\rightarrow$ Accept server certificate.

---

## 8. Monitoring & Maintenance

- **Live RADIUS Logs:**
  ```bash
  docker logs -f wifi-freeradius
  ```
- **Live LDAP Logs:**
  ```bash
  docker logs -f wifi-openldap
  ```
- **Stop All Containers:**
  ```bash
  docker compose down
  ```
- **Restart All Containers:**
  ```bash
  docker compose up -d openldap phpldapadmin freeradius
  ```
