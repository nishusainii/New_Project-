# Bare-Metal Ubuntu Enterprise Setup: Hardened OpenLDAP & FreeRADIUS AAA

This production manual provides the exact, copy-paste Ubuntu commands to deploy an enterprise-grade 802.1X authentication system across **two bare-metal servers** (or co-located on a single bare-metal server).

---

## 1. Network & Architecture Layout

```
[ Wireless Client ]
        │  (WPA2/WPA3 Enterprise - EAP-PEAP / EAP-TTLS)
        ▼
[ Wi-Fi Access Point (AP) / Switch ] (IP: 192.168.10.2)
        │
        │  RADIUS Auth (UDP 1812/1813) + BlastRADIUS Mitigation
        ▼
┌─────────────────────────────────────────────────────────┐
│ SERVER B: RADIUS AAA & Network Gateway (192.168.10.10)  │
│ - FreeRADIUS 3.2+ (802.1X Authentication Server)        │
│ - ISC-DHCP Server (IP Pool Lease Allocation)            │
│ - (Optional) Redis Server (Session / State Caching)     │
└──────────────────────────┬──────────────────────────────┘
                           │
                           │  Encrypted LDAPS (TCP 636 over TLS)
                           │  Least-Privilege Service Account Bind
                           ▼
┌─────────────────────────────────────────────────────────┐
│ SERVER A: Dedicated Identity Authority (192.168.10.20)  │
│ - OpenLDAP (slapd) with SSHA/Argon2 Password Hashing    │
│ - Strict Disallow of Anonymous Binds (olcDisallows)     │
│ - Granular Access Control Lists (ACLs)                  │
│ - UFW Firewall Restricted to Server B IP                │
└─────────────────────────────────────────────────────────┘
```

> **Note on Same-Server Setup:** If deploying both on the **same physical server**, replace `192.168.10.20` with `127.0.0.1` and bind FreeRADIUS directly to `ldaps://127.0.0.1:636`.

---

## Part 1: SERVER A — Dedicated Hardened OpenLDAP Setup

Run these commands on **Server A** (`192.168.10.20`).

### 1.1 Install OpenLDAP and Security Utilities
```bash
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  slapd ldap-utils openssl gnutls-bin ssl-cert ufw
```

### 1.2 Generate TLS Certificates for LDAPS (Port 636)
Create an internal Certificate Authority (CA) and Server Certificate:
```bash
sudo mkdir -p /etc/ssl/openldap
cd /etc/ssl/openldap

# 1. Create Internal CA Private Key and Certificate
sudo openssl req -new -x509 -nodes -days 3650 \
  -keyout ldap-ca.key -out ldap-ca.pem \
  -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Corporate/OU=IT Security/CN=Internal-LDAP-CA"

# 2. Create Server Private Key and CSR
sudo openssl req -new -nodes -days 1825 \
  -keyout ldap-server.key -out ldap-server.csr \
  -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Corporate/OU=IT Infrastructure/CN=192.168.10.20"

# 3. Sign the Server Certificate with CA
sudo openssl x509 -req -days 1825 \
  -in ldap-server.csr -CA ldap-ca.pem -CAkey ldap-ca.key -set_serial 01 \
  -out ldap-server.pem

# 4. Secure File Permissions
sudo chown -R openldap:openldap /etc/ssl/openldap
sudo chmod 600 /etc/ssl/openldap/ldap-server.key
sudo chmod 644 /etc/ssl/openldap/ldap-server.pem /etc/ssl/openldap/ldap-ca.pem
```

### 1.3 Configure `slapd` to Listen on LDAPS (Port 636)
Edit `/etc/default/slapd` to activate LDAPS:
```bash
sudo sed -i 's|^SLAPD_SERVICES=.*|SLAPD_SERVICES="ldap://127.0.0.1:389/ ldaps://0.0.0.0:636/ ldapi:///"|' /etc/default/slapd
```

### 1.4 Apply TLS Certificate Configuration to LDAP
Create a file named `configure-tls.ldif`:
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

### 1.5 Security Hardening: Disable Anonymous Binds & Enforce Auth
Prevent attackers from harvesting usernames or enumeration attacks:
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

### 1.6 Configure Granular Access Control Lists (ACLs)
Ensure passwords cannot be read by normal users and only authenticated services have search access:
```bash
cat << 'EOF' > /tmp/configure-acls.ldif
dn: olcDatabase={1}mdb,cn=config
changetype: modify
replace: olcAccess
olcAccess: {0}to attrs=userPassword
  by self write
  by anonymous auth
  by dn.exact="cn=admin,dc=corp,dc=internal" write
  by dn.exact="cn=radius-bind,ou=Services,dc=corp,dc=internal" read
  by * none
olcAccess: {1}to dn.base=""
  by * read
olcAccess: {2}to *
  by self write
  by dn.exact="cn=admin,dc=corp,dc=internal" write
  by dn.exact="cn=radius-bind,ou=Services,dc=corp,dc=internal" read
  by * read
EOF

sudo ldapmodify -Y EXTERNAL -H ldapi:/// -f /tmp/configure-acls.ldif
```

### 1.7 Restart slapd and Verify Listener
```bash
sudo systemctl restart slapd
sudo systemctl enable slapd
sudo ss -tulpn | grep slapd
# You should see slapd listening on port 636 (0.0.0.0:636) and port 389 (127.0.0.1:389)
```

### 1.8 Populate Base Structure, Least-Privilege Service Account & Users
Create the Directory Information Tree (DIT):
```bash
cat << 'EOF' > /tmp/base-structure.ldif
dn: ou=Users,dc=corp,dc=internal
objectClass: organizationalUnit
ou: Users

dn: ou=Groups,dc=corp,dc=internal
objectClass: organizationalUnit
ou: Groups

dn: ou=Services,dc=corp,dc=internal
objectClass: organizationalUnit
ou: Services

# Least-Privilege Account used exclusively by FreeRADIUS
dn: cn=radius-bind,ou=Services,dc=corp,dc=internal
objectClass: simpleSecurityObject
objectClass: organizationalRole
cn: radius-bind
userPassword: RadiusServiceSecret2026!
description: Dedicated read-only service account for FreeRADIUS 802.1X

# Wi-Fi Authorized Security Group
dn: cn=wifi-users,ou=Groups,dc=corp,dc=internal
objectClass: top
objectClass: posixGroup
cn: wifi-users
gidNumber: 5000
memberUid: john_doe
memberUid: alice_smith

# Employee 1: John Doe
dn: uid=john_doe,ou=Users,dc=corp,dc=internal
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
objectClass: posixAccount
cn: John Doe
sn: Doe
uid: john_doe
uidNumber: 1001
gidNumber: 5000
homeDirectory: /home/john_doe
mail: john.doe@corp.internal
userPassword: CorporatePass2026!

# Employee 2: Alice Smith
dn: uid=alice_smith,ou=Users,dc=corp,dc=internal
objectClass: top
objectClass: person
objectClass: organizationalPerson
objectClass: inetOrgPerson
objectClass: posixAccount
cn: Alice Smith
sn: Smith
uid: alice_smith
uidNumber: 1002
gidNumber: 5000
homeDirectory: /home/alice_smith
mail: alice.smith@corp.internal
userPassword: AliceStrongWifiPass#2026
EOF

# Add to LDAP database (enter your LDAP admin password when prompted)
ldapadd -x -D "cn=admin,dc=corp,dc=internal" -W -f /tmp/base-structure.ldif
```

### 1.9 Configure Server A Firewall (UFW)
Block all untrusted traffic to LDAP. Allow TCP port 636 **strictly from Server B's IP (`192.168.10.10`)**:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'
# Allow LDAPS strictly from RADIUS Server
sudo ufw allow from 192.168.10.10 to any port 636 proto tcp comment 'LDAPS from FreeRADIUS'
sudo ufw enable
sudo ufw status verbose
```

---

## Part 2: SERVER B — RADIUS AAA, DHCP & Redis Setup

Run these commands on **Server B** (`192.168.10.10`).

### 2.1 Install Packages
```bash
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  freeradius freeradius-ldap freeradius-utils isc-dhcp-server redis-server ufw
```

### 2.2 Trust Server A's CA Certificate
Copy the `ldap-ca.pem` from Server A to Server B:
```bash
# Copy from Server A (via scp or copy-paste):
sudo mkdir -p /etc/ssl/certs
# On Server B:
sudo scp user@192.168.10.20:/etc/ssl/openldap/ldap-ca.pem /etc/ssl/certs/ldap-ca.pem
sudo chmod 644 /etc/ssl/certs/ldap-ca.pem

# Configure ldap.conf client
cat << 'EOF' | sudo tee /etc/ldap/ldap.conf
BASE    dc=corp,dc=internal
URI     ldaps://192.168.10.20:636
TLS_CACERT /etc/ssl/certs/ldap-ca.pem
TLS_REQCERT demand
EOF
```

Verify TLS connection from Server B to Server A:
```bash
# Test anonymous query rejection:
ldapsearch -x -H ldaps://192.168.10.20:636 -b "dc=corp,dc=internal"
# Result: ldap_bind: Inappropriate authentication (48) -> PROVES HARDENED!

# Test with radius-bind service account:
ldapsearch -x -H ldaps://192.168.10.20:636 \
  -D "cn=radius-bind,ou=Services,dc=corp,dc=internal" \
  -w "RadiusServiceSecret2026!" \
  -b "ou=Users,dc=corp,dc=internal" "(uid=john_doe)"
# Result: Successfully retrieves John Doe record over encrypted TLS!
```

---

### 2.3 Configure FreeRADIUS LDAP Module
Configure `/etc/freeradius/3.0/mods-available/ldap`:
```bash
cat << 'EOF' | sudo tee /etc/freeradius/3.0/mods-available/ldap
ldap {
    server = 'ldaps://192.168.10.20:636'
    identity = 'cn=radius-bind,ou=Services,dc=corp,dc=internal'
    password = 'RadiusServiceSecret2026!'
    base_dn = 'dc=corp,dc=internal'

    user {
        base_dn = 'ou=Users,dc=corp,dc=internal'
        filter = '(uid=%{%{Stripped-User-Name}:-%{User-Name}})'
        scope = 'sub'
    }

    group {
        base_dn = 'ou=Groups,dc=corp,dc=internal'
        filter = '(objectClass=posixGroup)'
        membership_filter = '(&(objectClass=posixGroup)(memberUid=%{Stripped-User-Name}))'
        membership_attribute = 'memberUid'
    }

    tls {
        ca_file = '/etc/ssl/certs/ldap-ca.pem'
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

### 2.4 Configure FreeRADIUS Virtual Sites (`default` & `inner-tunnel`)
Enable LDAP in the authentication and authorization pipelines:

```bash
# 1. Edit /etc/freeradius/3.0/sites-available/default:
# Ensure 'ldap' is uncommented in authorize, authenticate, and post-auth sections.
sudo sed -i '/^[[:space:]]*#[[:space:]]*ldap/s/#//g' /etc/freeradius/3.0/sites-available/default

# 2. Edit /etc/freeradius/3.0/sites-available/inner-tunnel:
sudo sed -i '/^[[:space:]]*#[[:space:]]*ldap/s/#//g' /etc/freeradius/3.0/sites-available/inner-tunnel
```

---

### 2.5 Configure Wi-Fi Access Points in `clients.conf` (BlastRADIUS Mitigation)
Enforce `require_message_authenticator = yes` to neutralize **BlastRADIUS (CVE-2024-3596)**:

```bash
cat << 'EOF' | sudo tee -a /etc/freeradius/3.0/clients.conf

# Production Wi-Fi Access Points
client corporate_ap_subnet {
    ipaddr = 192.168.10.0/24
    secret = SuperSecretRadiusKey2026!
    shortname = corporate-aps
    require_message_authenticator = yes
    nas_type = other
}

# Localhost testing client
client localhost_test {
    ipaddr = 127.0.0.1
    secret = testing123
    require_message_authenticator = yes
}
EOF
```

---

### 2.6 Configure ISC-DHCP Server (IP Address Allocation)
Configure `/etc/dhcp/dhcpd.conf` for the Wi-Fi client subnet:
```bash
cat << 'EOF' | sudo tee /etc/dhcp/dhcpd.conf
default-lease-time 7200;
max-lease-time 14400;
authoritative;

# Wi-Fi Client VLAN (Subnet 192.168.10.0/24)
subnet 192.168.10.0 netmask 255.255.255.0 {
    range 192.168.10.100 192.168.10.200;
    option routers 192.168.10.1;
    option subnet-mask 255.255.255.0;
    option domain-name "corp.internal";
    option domain-name-servers 1.1.1.1, 8.8.8.8;
    option broadcast-address 192.168.10.255;
}
EOF

# Bind DHCP to your physical Wi-Fi interface (e.g., eth1, ens18, or vlan10)
# Check your interface name with: ip -br a
WIFI_IFACE="eth1" # Replace with your actual interface name
sudo sed -i "s|INTERFACESv4=.*|INTERFACESv4=\"${WIFI_IFACE}\"|" /etc/default/isc-dhcp-server

sudo systemctl restart isc-dhcp-server
sudo systemctl enable isc-dhcp-server
```

---

### 2.7 Configure Redis Server (Session & State Cache)
If you require Redis for session state tracking or caching:
```bash
# Secure Redis on localhost only
sudo sed -i 's|^bind .*|bind 127.0.0.1 ::1|' /etc/redis/redis.conf
# Set strong authentication password
sudo sed -i 's|^# requirepass .*|requirepass RedisSessionAuth2026!|' /etc/redis/redis.conf
sudo systemctl restart redis-server
sudo systemctl enable redis-server

# Verify Redis:
redis-cli -a "RedisSessionAuth2026!" ping
# Response: PONG
```

---

### 2.8 Configure Server B Firewall (UFW)
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp comment 'SSH'

# RADIUS Authentication & Accounting from AP subnet
sudo ufw allow from 192.168.10.0/24 to any port 1812 proto udp comment 'RADIUS Auth'
sudo ufw allow from 192.168.10.0/24 to any port 1813 proto udp comment 'RADIUS Acct'

# DHCP Requests from Wi-Fi Clients
sudo ufw allow in on eth1 to any port 67 proto udp comment 'DHCP Server'

sudo ufw enable
sudo ufw status verbose
```

---

## Part 3: Verification & End-to-End Testing

Run these tests on **Server B** to verify full functionality and security:

### 3.1 Start FreeRADIUS in Debug Mode
To observe live authentication packets in real-time:
```bash
sudo systemctl stop freeradius
sudo freeradius -X
```

### 3.2 Test 1: Legitimate User Authentication (Access-Accept)
In a second terminal on Server B:
```bash
radtest john_doe CorporatePass2026! 127.0.0.1 0 testing123
```
**Expected Output:**
```
Received Access-Accept Id 200 from 127.0.0.1:1812 to 127.0.0.1:0 length 20
```

### 3.3 Test 2: Invalid Password Rejection (Access-Reject)
```bash
radtest john_doe WrongPassword#999 127.0.0.1 0 testing123
```
**Expected Output:**
```
Received Access-Reject Id 201 from 127.0.0.1:1812 to 127.0.0.1:0 length 20
```

### 3.4 Test 3: Unauthorized User Rejection
```bash
radtest hacker_user RandomPassword 127.0.0.1 0 testing123
```
**Expected Output:**
```
Received Access-Reject Id 202 from 127.0.0.1:1812 to 127.0.0.1:0 length 20
```

### 3.5 Test 4: BlastRADIUS Immunity Validation
Verify that packets without a Message-Authenticator or with spoofed MD5 checksums are rejected:
```bash
echo "User-Name = 'john_doe', User-Password = 'CorporatePass2026!'" | \
  radclient -x 127.0.0.1:1812 auth testing123
```
Once verified, press `Ctrl+C` on the debug terminal and start the systemd daemon:
```bash
sudo systemctl start freeradius
sudo systemctl enable freeradius
```

---

## Part 4: Access Point (AP) Configuration Reference

On your physical Wi-Fi Controller or Access Point (e.g., Cisco, Ubiquiti UniFi, Aruba, MikroTik):

| Setting Field | Value | Notes |
|---|---|---|
| **Security Mode** | WPA2-Enterprise / WPA3-Enterprise (802.1X) | Highest security |
| **RADIUS Authentication Server IP** | `192.168.10.10` (Server B) | Point to FreeRADIUS |
| **RADIUS Port** | `1812` (UDP) | Standard Auth Port |
| **Shared Secret** | `SuperSecretRadiusKey2026!` | Matches `clients.conf` |
| **RADIUS Accounting Server IP** | `192.168.10.10` | Optional for session tracking |
| **RADIUS Accounting Port** | `1813` (UDP) | Standard Acct Port |
| **Message-Authenticator** | **Enabled / Required** | Defends against BlastRADIUS |
| **VLAN ID** | `10` (or your Wi-Fi VLAN) | Handled by DHCP Server |
