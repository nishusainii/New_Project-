# Innspark Enterprise Wi-Fi 802.1X Authentication (Bare-Metal Production Package)

**Architecture:** Native Ubuntu 22.04 / 24.04 LTS (No Containers)  
**Organization:** Innspark Technologies (P) Ltd.  
**Domain / Base DN:** `dc=innspark,dc=in`  
**Security Level:** Hardened 802.1X EAP / WPA2/WPA3-Enterprise, BlastRADIUS (CVE-2024-3596) Immune, PMF Capable  

---

## 1. Package Overview

This package contains automated native deployment scripts, production configuration files, systemd service units, and security verification suites for deploying Enterprise Wi-Fi Authentication directly on bare-metal or virtualized Ubuntu servers without Docker.

### Two Deployment Topologies Supported:

```
TOPOLOGY A: Two-Server Production Split
+---------------------------+             +---------------------------+
|  Server A: OpenLDAP       |   LDAPS     |  Server B: FreeRADIUS     |
|  IP: 192.168.2.12         |<----------->|  IP: 192.168.2.14         |
|  Slapd (Port 389 / 636)   |  (TLS CA)   |  RADIUS (UDP 1812/1813)   |
|  Base DN: dc=innspark,dc=in|            |  ISC-DHCP (UDP 67/68)     |
+---------------------------+             +-------------+-------------+
                                                        |
                                                  RADIUS Auth
                                                        |
                                          +-------------v-------------+
                                          | Enterprise Wi-Fi APs      |
                                          | Subnet: 10.31.1.0/24      |
                                          | SSID: Innspark-Secure     |
                                          +---------------------------+

TOPOLOGY B: Single-Server Unified Deployment
+---------------------------------------------------------------------+
|  Single Server (192.168.2.14 / localhost)                           |
|  - OpenLDAP Directory (Port 389/636)                                |
|  - FreeRADIUS 3 AAA Server (UDP 1812 / 1813)                        |
|  - ISC-DHCP Server (10.31.1.0/24 Pool)                              |
|  - Modern Web Admin Portal (Port 8088 Systemd Service)              |
+---------------------------------------------------------------------+
```

---

## 2. Directory Structure

```
wifi-auth-baremetal/
├── README.md                      # This production deployment guide
├── setup-server-a-ldap.sh         # Automated installer for Server A (OpenLDAP + TLS + ACLs)
├── setup-server-b-radius.sh       # Automated installer for Server B (FreeRADIUS + DHCP + UFW)
├── setup-single-server.sh         # All-in-one installer for single host deployment
├── setup-web-admin.sh             # Web portal installer with systemd service unit
├── configs/                       # Native configuration files
│   ├── ldap/
│   │   ├── users.ldif             # Seed organizational units, groups & demo users
│   │   ├── disable-anon.ldif      # Disables anonymous LDAP binds
│   │   ├── slapd-hardened-acls.ldif # Production ACLs protecting userPassword
│   │   └── cert-gen.sh            # CA & server SSL certificate generator
│   ├── radius/
│   │   ├── clients.conf           # Access Point definitions & BlastRADIUS enforcement
│   │   └── ldap                   # FreeRADIUS mods-available/ldap module config
│   ├── dhcp/
│   │   └── dhcpd.conf             # ISC-DHCP configuration (10.31.1.0/24 scope)
│   └── web-admin/                 # Python 3 Flask / Gunicorn Admin Console
│       ├── app.py                 # Backend API with ldap3 integration & password hashing
│       ├── requirements.txt       # Python dependencies (Flask, ldap3, gunicorn)
│       ├── templates/             # Modern UI & Login Gate templates
│       ├── static/                # CSS stylesheet & AJAX JS
│       └── innspark-web-admin.service # Systemd unit file
├── tests/                         # Native validation & audit scripts
│   ├── test-auth.sh               # Quick RADIUS <-> LDAP authentication test
│   ├── test-hardened-suite.sh     # Stress, concurrency (100 reqs), BlastRADIUS & injection tests
│   ├── vapt-audit.sh              # 10-parameter VAPT security compliance audit
│   └── demo-wifi-connection.sh    # End-to-end interactive 802.1X user connection simulation
└── docs/                          # Architecture guides, HTML/PDF manuals, and screenshots
```

---

## 3. Deployment Instructions

### Deployment Option 1: Two-Server Production Split

#### On Server A (LDAP Directory Server - `192.168.2.12`):
```bash
cd wifi-auth-baremetal
sudo chmod +x *.sh tests/*.sh configs/ldap/*.sh

# Run Server A installation
sudo ./setup-server-a-ldap.sh
```
*What it configures:*
- Installs `slapd`, `ldap-utils`, and SSL toolchain.
- Configures Base DN `dc=innspark,dc=in` and admin credentials.
- Disables anonymous binds and locks down password hashes.
- Imports `ou=Users`, `ou=Groups`, `cn=wifi-users`, and seed users.
- Configures UFW firewall to allow TCP 389 and TCP 636 only from Server B.

#### On Server B (AAA & DHCP Server - `192.168.2.14`):
```bash
cd wifi-auth-baremetal
sudo chmod +x *.sh tests/*.sh

# Run Server B installation (points to Server A IP)
sudo ./setup-server-b-radius.sh
```
*What it configures:*
- Installs `freeradius`, `freeradius-ldap`, `freeradius-utils`, and `isc-dhcp-server`.
- Links FreeRADIUS LDAP module pointing to Server A (`192.168.2.12`).
- Enforces `require_message_authenticator = yes` in `clients.conf` (BlastRADIUS immunity).
- Configures ISC-DHCP scope `10.31.1.0/24` on dedicated Wi-Fi VLAN interface.
- Opens UDP 1812/1813 and DHCP ports in UFW firewall.

---

### Deployment Option 2: Single-Server Unified Deployment

If deploying LDAP, FreeRADIUS, DHCP, and Web Admin on a single Ubuntu host:
```bash
cd wifi-auth-baremetal
sudo chmod +x *.sh tests/*.sh configs/ldap/*.sh

sudo ./setup-single-server.sh
```

---

### Deploying the Web Admin Portal (Optional GUI):
To install the Web Management Console as a persistent systemd service on port `8088`:
```bash
sudo ./setup-web-admin.sh
```
- Access URL: `http://<SERVER_IP>:8088/`
- Default Login Credentials:
  - Username: `admin`
  - Password: `AdminPassword2026!`
- Service Management:
  ```bash
  sudo systemctl status innspark-web-admin
  sudo systemctl restart innspark-web-admin
  ```

---

## 4. Verification & Testing

Run these tests directly on the server to verify the installation:

### 1. Test Single User Authentication
```bash
./tests/test-auth.sh john.doe WifiPassword2026!
```
Verifies LDAP bind, password checking, and Access-Accept response.

### 2. Run Hardened Security & Stress Suite
```bash
./tests/test-hardened-suite.sh
```
Executes:
- BlastRADIUS (CVE-2024-3596) RFC 3579 Message-Authenticator integrity.
- 100-packet concurrent stress test (0% packet drop threshold).
- LDAP injection and fuzzing payloads.
- Rogue shared secret rejection.

### 3. Run 10-Parameter VAPT Security Audit
```bash
./tests/vapt-audit.sh
```
Audits:
- Anonymous LDAP enumeration blocking.
- RADIUS shared secret entropy (>= 16 characters).
- BlastRADIUS `require_message_authenticator`.
- Port isolation and DHCP lease parameters.

### 4. Run Interactive Wi-Fi Connection Demo
```bash
./tests/demo-wifi-connection.sh mamta.saini WifiPassword2026!
```
Simulates the 4-step client connection lifecycle (Over-The-Air Association -> EAP Exchange -> LDAP Verification -> DHCP IP Lease).

---

## 5. Security & Hardening Features

- **BlastRADIUS Mitigation (CVE-2024-3596):** `require_message_authenticator = yes` enforced for all Access Points in `clients.conf`.
- **Credential Storage:** User passwords stored in OpenLDAP using SSHA / SSHA-512 hashes.
- **Access Control:** Anonymous binds blocked; directory reading restricted to authenticated entities.
- **Firewall Integration:** Dedicated UFW firewall configuration limiting ports to authorized network interfaces.
