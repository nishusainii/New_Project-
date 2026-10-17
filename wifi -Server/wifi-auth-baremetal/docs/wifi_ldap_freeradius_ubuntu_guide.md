# Enterprise Wi-Fi Server Deployment Guide: Innspark
## WPA2/WPA3-Enterprise (802.1X) with FreeRADIUS, Hardened OpenLDAP, ISC-DHCP, and Core DNS/NTP on Ubuntu Server

* **Organization / Domain:** `innspark.in` (`dc=innspark,dc=in`)
* **LDAP Identity Authority (Server A):** `192.168.2.12` (`ldap.innspark.in`)
* **RADIUS AAA & DHCP Gateway (Server B):** `192.168.2.14` (`radius.innspark.in`)
* **DNS & NTP Infrastructure:** `10.31.1.1` / `1.1.1.1` / `8.8.8.8` / Local Chrony NTP
* **Wireless Client Network:** `10.31.1.0/24` (Gateway: `10.31.1.1`, Pool: `10.31.1.50` – `10.31.1.250`)
* **Target Wi-Fi SSID:** `Innspark-Secure` (IEEE 802.1X Enterprise)

---

## 1. Enterprise 5-Tier Architecture & Protocol Flow

This deployment establishes an enterprise **IEEE 802.1X network access control architecture** across dedicated physical servers, network controllers, and client supplicants.

```text
                    +--------------------------------------------+
                    |                User Devices                |
                    |              Laptop / Mobile               |
                    |  - Subnet: 10.31.1.0/24 (DHCP: .50 - .250) |
                    |  - Supplicant: EAP-PEAP / EAP-TTLS         |
                    |  - User Identity: username@innspark.in     |
                    +---------------------+----------------------+
                                          |
                                          | WiFi (802.1X / WPA2-Enterprise / WPA3)
                                          | Dynamic AES-CCMP / GCMP Session Keys (PTK)
                                          | 802.11w Protected Management Frames (PMF)
                                          |
                    +---------------------v----------------------+
                    |               Access Points                |
                    |              (AP Controller)               |
                    |  - Management IP: 192.168.2.2              |
                    |  - SSID: Innspark-Secure                   |
                    |  - 802.1X Controlled Port (Gatekeeping)    |
                    |  - Layer 2 Client Isolation (Anti-Pivoting)|
                    +---------------------+----------------------+
                                          |
                                          | RADIUS Authentication (UDP 1812) & Acct (1813)
                                          | RFC 3579 Message-Authenticator (BlastRADIUS Immune)
                                          | Shared Secret: InnsparkRadiusSecret2026!
                                          |
                    +---------------------v----------------------+
                    |                WiFi Server                 |
                    |                FreeRADIUS                  |
                    |               (Auth Server)                |
                    |  - Server B IP: 192.168.2.14               |
                    |  - FreeRADIUS 3.2+ (EAP Termination Engine)|
                    |  - ISC-DHCP Server (Gateway: 10.31.1.1)    |
                    |  - Bind: cn=radius-bind,ou=Services,...    |
                    +---------------------+----------------------+
                                          |
                            LDAP Query    | LDAPS (Port 636 over TLS)
                            (Encrypted)   | Strict CA Verification (innspark-ldap-ca.pem)
                                          | Dedicated Read-Only Service Account Bind
                                          |
                    +---------------------v----------------------+
                    |                LDAP Server                 |
                    |               OpenLDAP / AD                |
                    |               User Database                |
                    |  - Server A IP: 192.168.2.12               |
                    |  - Base DN: dc=innspark,dc=in              |
                    |  - Disallow Anonymous Binds (olcDisallows) |
                    |  - SSHA / Argon2 Password Hashing          |
                    |  - Authorized Security Group: cn=wifi-users|
                    +---------------------+----------------------+
                                          |
                                          | DNS Query (UDP 53) & NTP Sync (UDP 123)
                                          | Sub-millisecond UTC Time Synchronization
                                          |
                    +---------------------v----------------------+
                    |              DNS / NTP Server              |
                    |  - DNS IP: 10.31.1.1, 1.1.1.1, 8.8.8.8     |
                    |  - Resolves: ldap.innspark.in, radius...   |
                    |  - Prevents TLS Certificate Skew Rejections|
                    +--------------------------------------------+
```

### Core Architecture Components

| Tier | Component | Host / IP | Protocols & Security Functions |
| :---: | :--- | :--- | :--- |
| **Tier 1** | **User Devices** | `10.31.1.50 - 10.31.1.250` (DHCP) | IEEE 802.1X EAPOL, PEAP/MSCHAPv2 or TTLS/PAP; Dynamic AES-CCMP; Server CA validation |
| **Tier 2** | **Access Points** | `192.168.2.2` (Subnet: `192.168.2.0/24`) | WPA3/WPA2-Enterprise; 802.11w PMF de-auth defense; L2 Client Isolation; 802.1X controlled port |
| **Tier 3** | **WiFi Server (FreeRADIUS)** | `192.168.2.14` (Server B) | FreeRADIUS 3.2+ (UDP 1812/1813), ISC-DHCP (`10.31.1.0/24`), Gateway `10.31.1.1`, BlastRADIUS defense |
| **Tier 4** | **LDAP Server** | `192.168.2.12` (Server A) | LDAPS (TCP 636), `dc=innspark,dc=in`, Service Bind `cn=radius-bind`, SSHA passwords, ACL lockdown |
| **Tier 5** | **DNS / NTP Server** | `10.31.1.1` / `1.1.1.1` / `8.8.8.8` | Authoritative DNS for `innspark.in`, sub-millisecond NTP sync (UDP 123) ensuring TLS certificate validity |

---

## 2. Enterprise Threat Model & Attack Vector Defense

| Threat ID | Threat Vector | Severity | Impact | Enforced Mitigation |
| :--- | :--- | :---: | :--- | :--- |
| **TM-01** | **Air-Interface Eavesdropping** | **CRITICAL** | Packet sniffing to recover shared pre-shared keys (WPA-PSK flaw) | **IEEE 802.1X Dynamic Session Keys (PTK).** Individualized link-layer AES encryption per device. |
| **TM-02** | **Deauthentication Flooding DoS** | **HIGH** | Spoofed 802.11 management frames disconnecting devices | **IEEE 802.11w Protected Management Frames (PMF)** set to *Required*. |
| **TM-03** | **BlastRADIUS (CVE-2024-3596)** | **CRITICAL** | MD5 collision attack forging Access-Accept packets | Mandatory **`require_message_authenticator = yes`** in `clients.conf`. |
| **TM-04** | **Rogue AP / Evil Twin Attack** | **HIGH** | Fake AP intercepting employee login attempts | **Server Certificate Pinning.** Client validates Server B's CA certificate before transmission. |
| **TM-05** | **Lateral Movement & Sniffing** | **HIGH** | Infected client attacking neighboring work devices | **AP Layer 2 Client Isolation** + Dynamic VLAN segregation. |
| **TM-06** | **LDAP Injection & Harvesting** | **HIGH** | Fuzzing LDAP attributes (`*)(uid=*`) to bypass login | **LDAP Parameter Sanitization** + **Disable Anonymous Binds** (`bind_anon`). |
| **TM-07** | **Directory Credential Exposure** | **HIGH** | Attackers intercepting plaintext passwords across the LAN | **Strict LDAPS (Port 636 over TLS)** between Server B and Server A. |
| **TM-08** | **DHCP Pool Starvation** | **MEDIUM** | Spoofed MAC addresses exhausting the `10.31.1.0/24` pool | **Lease Time Optimization** (7200s) + Managed Switch DHCP Snooping. |
| **TM-09** | **Clock Skew Authentication Failure** | **HIGH** | Drift in server clocks causes TLS/Kerberos validation failure | **NTP Time Synchronization (Chrony)** enforcing clock drift $\le 50\text{ ms}$. |

---

## 3. TIER 4 CONFIGURATION: Dedicated OpenLDAP Server (`192.168.2.12`)

Run all commands in this section on **Server A** (`192.168.2.12`).

### 3.1 Network & Package Installation
```bash
sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  slapd ldap-utils openssl gnutls-bin ssl-cert ufw
```

### 3.2 Generate TLS Certificates for `innspark.in` LDAPS (Port 636)
Generate a dedicated internal Certificate Authority and Server Certificate for `192.168.2.12`:
```bash
sudo mkdir -p /etc/ssl/openldap
cd /etc/ssl/openldap

# 1. Generate Private Key & CA Certificate (10-Year Validity)
sudo openssl req -new -x509 -nodes -days 3650 \
  -keyout ldap-ca.key -out ldap-ca.pem \
  -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Innspark Technologies/OU=Security/CN=Innspark-LDAP-CA"

# 2. Generate Server Key & CSR for ldap.innspark.in and IP 192.168.2.12
sudo openssl req -new -nodes -days 1825 \
  -keyout ldap-server.key -out ldap-server.csr \
  -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Innspark Technologies/OU=IT/CN=192.168.2.12"

# 3. Sign the Server Certificate with the CA
sudo openssl x509 -req -days 1825 \
  -in ldap-server.csr -CA ldap-ca.pem -CAkey ldap-ca.key -set_serial 01 \
  -out ldap-server.pem

# 4. Enforce strict permissions (openldap ownership)
sudo chown -R openldap:openldap /etc/ssl/openldap
sudo chmod 600 /etc/ssl/openldap/ldap-server.key
sudo chmod 644 /etc/ssl/openldap/ldap-server.pem /etc/ssl/openldap/ldap-ca.pem
```

### 3.3 Bind slapd to LDAPS (Port 636)
Edit `/etc/default/slapd` so OpenLDAP listens over encrypted LDAPS on all interfaces, and unencrypted LDAP only on localhost:
```bash
sudo sed -i 's|^SLAPD_SERVICES=.*|SLAPD_SERVICES="ldap://127.0.0.1:389/ ldaps://0.0.0.0:636/ ldapi:///"|' /etc/default/slapd
```

### 3.4 Apply TLS Certificate Configuration to slapd
```bash
cat << 'EOF' > /tmp/configure-tls.ldif
dn: cn=config
changetype: modify
replace: olcTLSCACertificateFile
olcTLSCACertificateFile: /etc/ssl/openldap/ldap-ca.pem
-
replace: olcTLSCertificateFile
olcTLSCertificateFile: /etc/ssl/openldap/ldap-server.pem
-
replace: olcTLSCertificateKeyFile
olcTLSCertificateKeyFile: /etc/ssl/openldap/ldap-server.key
-
replace: olcTLSVerifyClient
olcTLSVerifyClient: never
EOF

sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/configure-tls.ldif
```

### 3.5 Security Hardening: Disable Anonymous Binds
Prevent unauthorized enumeration of users and directory structures:
```bash
cat << 'EOF' > /tmp/harden-security.ldif
dn: cn=config
changetype: modify
add: olcDisallows
olcDisallows: bind_anon
-
add: olcRequires
olcRequires: authc

dn: olcDatabase={-1}frontend,cn=config
changetype: modify
add: olcRequires
olcRequires: authc
EOF

sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/harden-security.ldif
```

### 3.6 Configure Granular Access Control Lists (ACLs)
Restrict access so users can update their own passwords, the `radius-bind` service account can read credentials, and attackers cannot read password hashes:
```bash
cat << 'EOF' > /tmp/configure-acls.ldif
dn: olcDatabase={1}mdb,cn=config
changetype: modify
replace: olcAccess
olcAccess: {0}to attrs=userPassword
  by self write
  by anonymous auth
  by dn.exact="cn=admin,dc=innspark,dc=in" write
  by dn.exact="cn=radius-bind,ou=Services,dc=innspark,dc=in" read
  by * none
olcAccess: {1}to dn.base=""
  by * read
olcAccess: {2}to *
  by self write
  by dn.exact="cn=admin,dc=innspark,dc=in" write
  by dn.exact="cn=radius-bind,ou=Services,dc=innspark,dc=in" read
  by * read
EOF

sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/configure-acls.ldif
```

### 3.7 Restart OpenLDAP Service
```bash
sudo systemctl restart slapd
sudo systemctl enable slapd
sudo ss -tulpn | grep slapd
# Verify slapd is listening on 0.0.0.0:636 (LDAPS) and 127.0.0.1:389
```

### 3.8 Populate Directory Tree for `dc=innspark,dc=in`
Create organizational units, the least-privilege service account for FreeRADIUS, the Wi-Fi security group, and sample employee accounts:

```bash
cat << 'EOF' > /tmp/innspark-dit.ldif
# Organizational Units
dn: ou=Users,dc=innspark,dc=in
objectClass: organizationalUnit
ou: Users

dn: ou=Groups,dc=innspark,dc=in
objectClass: organizationalUnit
ou: Groups

dn: ou=Services,dc=innspark,dc=in
objectClass: organizationalUnit
ou: Services

# Dedicated Service Account for FreeRADIUS (Least Privilege - Not Admin)
dn: cn=radius-bind,ou=Services,dc=innspark,dc=in
objectClass: simpleSecurityObject
objectClass: organizationalRole
cn: radius-bind
userPassword: InnsparkRadiusBind2026!
description: Dedicated read-only service account for Server B FreeRADIUS AAA

# Wi-Fi Authorized Security Group
dn: cn=wifi-users,ou=Groups,dc=innspark,dc=in
objectClass: top
objectClass: posixGroup
cn: wifi-users
gidNumber: 5000
memberUid: john.doe
memberUid: alice.smith

# Employee Account 1: John Doe
dn: uid=john.doe,ou=Users,dc=innspark,dc=in
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
objectClass: posixAccount
cn: John Doe
sn: Doe
uid: john.doe
uidNumber: 1001
gidNumber: 5000
homeDirectory: /home/john.doe
mail: john.doe@innspark.in
userPassword: InnsparkUserPass2026!

# Employee Account 2: Alice Smith
dn: uid=alice.smith,ou=Users,dc=innspark,dc=in
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
objectClass: posixAccount
cn: Alice Smith
sn: Smith
uid: alice.smith
uidNumber: 1002
gidNumber: 5000
homeDirectory: /home/alice.smith
mail: alice.smith@innspark.in
userPassword: AliceStrongWifiPass#2026
EOF

# Add DIT structure to LDAP database (enter LDAP admin password when prompted)
ldapadd -x -D "cn=admin,dc=innspark,dc=in" -W -f /tmp/innspark-dit.ldif
```

### 3.9 Server A UFW Firewall Hardening
Allow TCP port 636 **strictly from Server B (`192.168.2.14`)**:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
sudo ufw allow from 192.168.2.14 to any port 636 proto tcp comment 'LDAPS from Server B'
sudo ufw enable
sudo ufw status verbose
```

---

## 4. TIER 3 CONFIGURATION: WiFi Server / FreeRADIUS & DHCP (`192.168.2.14`)

Run all commands in this section on **Server B** (`192.168.2.14`).

### 4.1 Install Packages
```bash
sudo apt-get update && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  freeradius freeradius-ldap freeradius-utils isc-dhcp-server redis-server ufw
```

### 4.2 Import Server A's CA Certificate
Copy the `ldap-ca.pem` from Server A (`192.168.2.12`) to Server B:
```bash
sudo mkdir -p /etc/ssl/certs
# Copy from Server A:
sudo scp user@192.168.2.12:/etc/ssl/openldap/ldap-ca.pem /etc/ssl/certs/innspark-ldap-ca.pem
sudo chmod 644 /etc/ssl/certs/innspark-ldap-ca.pem

# Configure ldap.conf client
cat << 'EOF' | sudo tee /etc/ldap/ldap.conf
BASE    dc=innspark,dc=in
URI     ldaps://192.168.2.12:636
TLS_CACERT /etc/ssl/certs/innspark-ldap-ca.pem
TLS_REQCERT demand
EOF
```

**Verify encrypted LDAPS connection to Server A:**
```bash
# 1. Verify Anonymous rejection (expected error 48):
ldapsearch -x -H ldaps://192.168.2.12:636 -b "dc=innspark,dc=in"
# Expected: ldap_bind: Inappropriate authentication (48) -> PROVES HARDENED!

# 2. Verify Authenticated query with radius-bind:
ldapsearch -x -H ldaps://192.168.2.12:636 \
  -D "cn=radius-bind,ou=Services,dc=innspark,dc=in" \
  -w "InnsparkRadiusBind2026!" \
  -b "ou=Users,dc=innspark,dc=in" "(uid=john.doe)"
# Expected: Successfully returns John Doe's record over encrypted TLS!
```

---

### 4.3 Configure FreeRADIUS LDAP Module for `innspark.in`
Edit `/etc/freeradius/3.0/mods-available/ldap`:
```bash
cat << 'EOF' | sudo tee /etc/freeradius/3.0/mods-available/ldap
ldap {
    # Server Connection to Server A
    server = 'ldaps://192.168.2.12:636'
    identity = 'cn=radius-bind,ou=Services,dc=innspark,dc=in'
    password = 'InnsparkRadiusBind2026!'
    base_dn = 'dc=innspark,dc=in'

    user {
        base_dn = 'ou=Users,dc=innspark,dc=in'
        filter = '(uid=%{%{Stripped-User-Name}:-%{User-Name}})'
        scope = 'sub'
    }

    group {
        base_dn = 'ou=Groups,dc=innspark,dc=in'
        filter = '(objectClass=posixGroup)'
        membership_filter = '(&(objectClass=posixGroup)(memberUid=%{Stripped-User-Name}))'
        membership_attribute = 'memberUid'
    }

    tls {
        ca_file = '/etc/ssl/certs/innspark-ldap-ca.pem'
        require_cert = 'demand'
    }

    options {
        timeout = 5
        timelimit = 5
        net_timeout = 5
        chase_referrals = no
        rebind = yes
    }

    pool {
        start = 5
        min = 4
        max = 32
        spare = 3
        uses = 0
        lifetime = 0
        idle_timeout = 60
    }
}
EOF

# Enable the LDAP module symlink
sudo ln -sf /etc/freeradius/3.0/mods-available/ldap /etc/freeradius/3.0/mods-enabled/ldap
```

---

### 4.4 Enable LDAP in FreeRADIUS Virtual Sites
Enable LDAP lookups inside both the outer authentication pipeline and the inner tunnel:

```bash
# 1. Enable ldap in /etc/freeradius/3.0/sites-available/default
sudo sed -i '/^[[:space:]]*#[[:space:]]*ldap/s/#//g' /etc/freeradius/3.0/sites-available/default

# 2. Enable ldap in /etc/freeradius/3.0/sites-available/inner-tunnel
sudo sed -i '/^[[:space:]]*#[[:space:]]*ldap/s/#//g' /etc/freeradius/3.0/sites-available/inner-tunnel
```

---

### 4.5 Configure Access Points & BlastRADIUS Defense (`clients.conf`)
Configure your Wi-Fi AP network and localhost test client with **`require_message_authenticator = yes`** to neutralize **BlastRADIUS (CVE-2024-3596)**:

```bash
cat << 'EOF' | sudo tee -a /etc/freeradius/3.0/clients.conf

# Production Wi-Fi Access Points on 192.168.2.0/24
client innspark_ap_subnet {
    ipaddr = 192.168.2.0/24
    secret = InnsparkRadiusSecret2026!
    shortname = innspark-aps
    require_message_authenticator = yes
    nas_type = other
}

# Localhost test client
client localhost_test {
    ipaddr = 127.0.0.1
    secret = testing123
    require_message_authenticator = yes
}
EOF
```

---

### 4.6 Configure ISC-DHCP Server (Subnet `10.31.1.0/24`)
Configure IP address allocation for wireless clients connecting to `Innspark-Secure`:

```bash
cat << 'EOF' | sudo tee /etc/dhcp/dhcpd.conf
# General Lease Policies
default-lease-time 7200;      # 2 Hours
max-lease-time 28800;         # 8 Hours
authoritative;
log-facility local7;

# Wireless Client Subnet (10.31.1.0/24)
subnet 10.31.1.0 netmask 255.255.255.0 {
    range 10.31.1.50 10.31.1.250;
    option routers 10.31.1.1;                           # Wi-Fi Default Gateway
    option subnet-mask 255.255.255.0;
    option broadcast-address 10.31.1.255;
    option domain-name "innspark.in";
    option domain-name-servers 10.31.1.1, 1.1.1.1, 8.8.8.8;
}
EOF

# Bind DHCP to the Wi-Fi interface (replace eth1 with your Wi-Fi VLAN / interface name)
# Check interfaces using: ip -br a
WIFI_IFACE="eth1"
sudo sed -i "s|INTERFACESv4=.*|INTERFACESv4=\"${WIFI_IFACE}\"|" /etc/default/isc-dhcp-server

sudo systemctl restart isc-dhcp-server
sudo systemctl enable isc-dhcp-server
sudo systemctl status isc-dhcp-server --no-pager
```

> **Assign Gateway IP `10.31.1.1`:** Ensure `eth1` (the interface attached to the Wi-Fi VLAN) has the static IP `10.31.1.1/24`:
> ```yaml
>   eth1:
>     addresses:
>       - 10.31.1.1/24
> ```

---

### 4.7 Configure Server B Firewall (UFW)
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'

# Allow RADIUS traffic from AP subnet (192.168.2.0/24)
sudo ufw allow from 192.168.2.0/24 to any port 1812 proto udp comment 'RADIUS Auth from APs'
sudo ufw allow from 192.168.2.0/24 to any port 1813 proto udp comment 'RADIUS Acct from APs'

# Allow DHCP broadcast requests on the Wi-Fi client interface
sudo ufw allow in on eth1 to any port 67 proto udp comment 'DHCP Server'

sudo ufw enable
sudo ufw status verbose
```

---

## 5. TIER 5 CONFIGURATION: DNS & NTP Core Infrastructure

Accurate time and domain name resolution are mandatory for 802.1X enterprise networking:
* **Why NTP is Critical:** TLS certificates have strict `NotBefore` and `NotAfter` validity timestamps. If the clock on Server A (`192.168.2.12`) or Server B (`192.168.2.14`) drifts by more than 300 seconds, EAP-TLS handshakes fail with `certificate_expired` or `certificate_unknown`.
* **Why DNS is Critical:** Resolves `ldap.innspark.in` to `192.168.2.12` and `radius.innspark.in` to `192.168.2.14`, preventing hardcoded IP breakage during cluster failover.

### 5.1 Configure NTP Synchronization with Chrony (On Both Servers)
Install and configure `chrony` on **both Server A and Server B**:

```bash
sudo apt-get install -y chrony

# Configure /etc/chrony/chrony.conf
cat << 'EOF' | sudo tee /etc/chrony/chrony.conf
# Authoritative NTP Pools
server time.cloudflare.com iburst
server time.google.com iburst
server 0.pool.ntp.org iburst
server 1.pool.ntp.org iburst

# Step the clock immediately if drift > 1 second on boot
makestep 1.0 3

# Record drift
driftfile /var/lib/chrony/chrony.drift
logdir /var/log/chrony
maxupdateskew 100.0
rtcsync
EOF

sudo systemctl restart chrony
sudo systemctl enable chrony

# Verify sub-millisecond synchronization
chronyc sources -v
chronyc tracking
```

### 5.2 Configure DNS Server for `innspark.in` (On Gateway / Server B or DNS Appliance)
To provide local DNS resolution for the Wi-Fi clients and internal servers, install `dnsmasq` or configure `/etc/hosts` resolution:

```bash
sudo apt-get install -y dnsmasq

cat << 'EOF' | sudo tee /etc/dnsmasq.d/innspark.conf
# Domain and Interface Bindings
domain=innspark.in
listen-address=127.0.0.1,10.31.1.1,192.168.2.14
bind-interfaces

# Authoritative Internal Host Records
address=/ldap.innspark.in/192.168.2.12
address=/radius.innspark.in/192.168.2.14
address=/gateway.innspark.in/10.31.1.1
address=/wifi.innspark.in/10.31.1.1

# Upstream Public DNS Forwarders
server=1.1.1.1
server=8.8.8.8
server=9.9.9.9

# Caching & Security
cache-size=1000
no-negcache
stop-dns-rebind
EOF

sudo systemctl restart dnsmasq
sudo systemctl enable dnsmasq

# Test DNS resolution
dig @10.31.1.1 ldap.innspark.in +short
# Returns: 192.168.2.12
```

---

## 6. TIER 2 CONFIGURATION: Access Points & AP Controller Setup

Apply these configurations to your Wi-Fi Controller or Access Points (AP Management IP: `192.168.2.2`, Subnet: `192.168.2.0/24`):

### 6.1 Unified Controller Parameters
| Setting Field | Production Value | Security Rationale |
| :--- | :--- | :--- |
| **SSID Name** | `Innspark-Secure` | Broadcasted Corporate Network |
| **Security Type** | **WPA2/WPA3-Enterprise (802.1X)** | Enterprise AES-CCMP/GCMP |
| **RADIUS Auth Server** | `192.168.2.14` | Server B IP |
| **RADIUS Auth Port** | `1812` (UDP) | Standard RFC 2865 |
| **Shared Secret** | `InnsparkRadiusSecret2026!` | Matches `clients.conf` |
| **RADIUS Acct Server** | `192.168.2.14` | Server B IP |
| **RADIUS Acct Port** | `1813` (UDP) | Standard RFC 2866 |
| **Message-Authenticator** | **Required / Enabled** | Neutralizes BlastRADIUS (CVE-2024-3596) |
| **Protected Management Frames (PMF)**| **Required (802.11w)** | Stops De-auth & Disassociation DoS |
| **Client Isolation** | **Enabled** | Blocks peer-to-peer lateral movement |
| **VLAN ID** | `10` (mapped to `10.31.1.0/24`) | Isolated client subnet |

### 6.2 Cisco Catalyst / IOS-XE CLI Example
```text
aaa new-model
radius server RADIUS_SERVER_B
 address ipv4 192.168.2.14 auth-port 1812 acct-port 1813
 key InnsparkRadiusSecret2026!
 require message-authenticator

aaa group server radius INNSPARK_RADIUS_GRP
 server name RADIUS_SERVER_B

aaa authentication dot1x default group INNSPARK_RADIUS_GRP
aaa authorization network default group INNSPARK_RADIUS_GRP
aaa accounting dot1x default start-stop group INNSPARK_RADIUS_GRP

wlan Innspark-Secure 1 Innspark-Secure
 security wpa psk set-key ascii 0
 security dot1x authentication-list default
 security wpa wpa2 ciphers aes
 security pmf mandatory
 client-isolation
 vlan 10
 no shutdown
```

### 6.3 Ubiquiti UniFi Controller GUI Settings
1. Navigate to **Settings** &rarr; **Profiles** &rarr; **RADIUS**:
   * Create Profile: `Innspark-RADIUS`
   * IP: `192.168.2.14`, Port: `1812`, Password: `InnsparkRadiusSecret2026!`
   * Accounting: Enable, Port: `1813`
2. Navigate to **Settings** &rarr; **WiFi**:
   * Name: `Innspark-Secure`
   * Security Protocol: `WPA2/WPA3 Enterprise`
   * RADIUS Profile: `Innspark-RADIUS`
   * PMF: `Required`
   * Client Device Isolation: `Checked`
   * Network: Select VLAN `10` (`10.31.1.0/24`)

---

## 7. TIER 1 CONFIGURATION: Employee Device Connection Guide

### 7.1 Windows 10 & 11
1. Click the Wi-Fi icon on the taskbar, select **`Innspark-Secure`**, and click **Connect**.
2. When prompted, enter your Innspark credentials:
   - **User name:** `john.doe` (or `john.doe@innspark.in`)
   - **Password:** `InnsparkUserPass2026!`
3. If prompted to verify the server certificate identity, click **Connect** (or distribute `innspark-ldap-ca.pem` via Active Directory GPO / Intune).

### 7.2 Android (11, 12, 13, 14+)
1. Tap **`Innspark-Secure`** in Wi-Fi settings.
2. Select:
   - **EAP method:** `PEAP` (or `TTLS`)
   - **Phase 2 authentication:** `MSCHAPV2` (or `PAP`)
   - **CA certificate:** Select `Use system certificates`
   - **Domain:** `innspark.in`
   - **Identity:** `john.doe`
   - **Password:** `InnsparkUserPass2026!`
3. Tap **Connect**.

### 7.3 Apple iOS / iPadOS / macOS
1. Open Wi-Fi settings, select **`Innspark-Secure`**.
2. Enter:
   - **Username:** `john.doe`
   - **Password:** `InnsparkUserPass2026!`
3. Tap **Trust** in the top right corner when the RADIUS certificate appears.

### 7.4 Ubuntu / Linux CLI (`wpa_supplicant`)
Create `/etc/wpa_supplicant/wpa_supplicant-wlan0.conf`:
```ini
network={
    ssid="Innspark-Secure"
    key_mgmt=WPA-EAP
    eap=PEAP
    identity="john.doe"
    password="InnsparkUserPass2026!"
    phase2="auth=MSCHAPV2"
    ca_cert="/etc/ssl/certs/innspark-ldap-ca.pem"
}
```
Connect via:
```bash
sudo wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant-wlan0.conf
sudo dhclient wlan0
```

---

## 8. Verification, Security Testing & VAPT Audit

Run these tests on **Server B** (`192.168.2.14`):

### 8.1 Interactive Debug Mode
Start FreeRADIUS in interactive debug mode to monitor authentication packets live:
```bash
sudo systemctl stop freeradius
sudo freeradius -X
```

### 8.2 Test 1: Valid Employee Login (`Access-Accept`)
In a second terminal on Server B:
```bash
radtest john.doe InnsparkUserPass2026! 127.0.0.1 0 testing123
```
**Expected Response:**
```text
Received Access-Accept Id 200 from 127.0.0.1:1812 to 127.0.0.1:0 length 20
```

### 8.3 Test 2: Invalid Password Rejection (`Access-Reject`)
```bash
radtest john.doe WrongPass#999 127.0.0.1 0 testing123
```
**Expected Response:**
```text
Received Access-Reject Id 201 from 127.0.0.1:1812 to 127.0.0.1:0 length 20
```

### 8.4 Test 3: BlastRADIUS Immunity Validation
Verify that packets without Message-Authenticator or with spoofed MD5 checksums are rejected:
```bash
echo "User-Name = 'john.doe', User-Password = 'InnsparkUserPass2026!'" | \
  radclient -x 127.0.0.1:1812 auth testing123
```

### 8.5 Test 4: Verify NTP Clock Synchronization
```bash
chronyc sources -v
# Ensure all time sources show '*' (active) or '+' (candidate) with offset < 50ms
```

### 8.6 Test 5: Verify DNS Resolution
```bash
dig @10.31.1.1 ldap.innspark.in +short
# Must return: 192.168.2.12
```

Once tests pass, stop debug mode (`Ctrl+C`) and start the production daemon:
```bash
sudo systemctl start freeradius
sudo systemctl enable freeradius
```

## 9. Modern Enterprise Wi-Fi & LDAP Management Web Console

The containerized stack includes a modern, dark-glassmorphic administrative portal running on port `8088`:

* **Local Browser URL:** [http://localhost:8088](http://localhost:8088) (Redirects to `/login`)
* **LAN Browser URL:** `http://10.31.1.59:8088`
* **Connected Directory:** OpenLDAP (`127.0.0.1:389`)
* **Base DN:** `dc=innspark,dc=in`
* **Wi-Fi Authorization Group:** `cn=wifi-users,ou=Groups,dc=innspark,dc=in`

### Authentication & Access:
* **Security Gateway:** Unauthenticated requests are intercepted and redirected to the `/login` portal.
* **Root Administrator:** `admin` (or `cn=admin,dc=innspark,dc=in`) / `AdminPassword123!`
* **Corporate Directory Users:** Any provisioned employee account (e.g. `john.doe@innspark.in`) can log in with their directory credentials.
* **Session Management:** Encrypted HTTP session cookies with top-header status pill and secure **Sign Out** button.

### Administrative Features:
1. **One-Click User Creation:** Automatically generates usernames (`first.last`), creates LDAP accounts, and assigns to `cn=wifi-users`.
2. **Instant Password Reset:** Integrated cryptographic password generator that immediately synchronizes with FreeRADIUS.
3. **Wi-Fi Access Toggle:** Instant grant/revoke of 802.1X network access without deleting employee accounts.
4. **Live EAP/LDAP Auth Tester:** Real-time credential test directly in the browser with Access-Accept / Access-Reject feedback.

---

## 9. Operational Maintenance & Monitoring

| Operational Task | Target Server | Command |
| :--- | :--- | :--- |
| **Check RADIUS Status** | Server B (`192.168.2.14`) | `sudo systemctl status freeradius` |
| **Restart RADIUS Daemon** | Server B (`192.168.2.14`) | `sudo systemctl restart freeradius` |
| **Follow Live RADIUS Logs** | Server B (`192.168.2.14`) | `sudo tail -f /var/log/freeradius/radius.log` |
| **Check Live DHCP Leases** | Server B (`192.168.2.14`) | `sudo tail -f /var/lib/dhcp/dhcpd.leases` |
| **Check DHCP Daemon Status**| Server B (`192.168.2.14`) | `sudo systemctl status isc-dhcp-server` |
| **Check OpenLDAP Status** | Server A (`192.168.2.12`) | `sudo systemctl status slapd` |
| **Restart OpenLDAP Daemon** | Server A (`192.168.2.12`) | `sudo systemctl restart slapd` |
| **Test LDAPS from Server B**| Server B (`192.168.2.14`) | `ldapsearch -x -H ldaps://192.168.2.12:636 -D "cn=radius-bind,ou=Services,dc=innspark,dc=in" -w "InnsparkRadiusBind2026!" -b "dc=innspark,dc=in"` |
| **Check NTP Time Sync** | Both Servers | `chronyc tracking && chronyc sources` |
| **Monitor 802.1X Packets** | Server B (`192.168.2.14`) | `sudo tcpdump -n -i eth0 port 1812 or port 67` |
