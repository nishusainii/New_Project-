# Server 2: Squid Proxy Installation & LDAP Authentication Setup
**Target Machine:** Server 2 (`proxy.innspark.in` — e.g., `10.31.1.159`)  
**LDAP Directory Server:** Server 1 (`ldap.innspark.in` — e.g., `10.31.1.10`)  
**Base DN:** `dc=innspark,dc=in`

---

## 1. Overview
Server 2 runs the forward caching proxy. Every outbound client connection requests authentication against OpenLDAP on Server 1 using Squid's built-in `basic_ldap_auth` and `ext_ldap_group_acl` helpers.

---

## 2. Step-by-Step Installation (Execute on Server 2)

### Step 2.1: Install Squid and LDAP Utilities
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install squid ldap-utils -y
```

Verify the installed Squid version and helper locations:
```bash
squid -v
ls -l /usr/lib/squid/basic_ldap_auth
ls -l /usr/lib/squid/ext_ldap_group_acl
```

### Step 2.2: Backup Default Configuration
```bash
sudo cp /etc/squid/squid.conf /etc/squid/squid.conf.original-$(date +%F)
```

### Step 2.3: Create ACL and Credential Directories
```bash
sudo mkdir -p /etc/squid/acl
sudo mkdir -p /var/log/squid
sudo chown -R proxy:proxy /var/log/squid
```

### Step 2.4: Store LDAP Bind Credentials Securely
Squid needs the password for `cn=squidbind,dc=innspark,dc=in` to query LDAP:
```bash
echo -n "SquidBindPassword@2026" | sudo tee /etc/squid/ldap_password.txt
sudo chown proxy:proxy /etc/squid/ldap_password.txt
sudo chmod 600 /etc/squid/ldap_password.txt
```

---

## 3. Verify LDAP Communication Directly from Server 2

Before configuring Squid, verify that Server 2 can query Server 1:

### Test 3.1: Network Connectivity Check
```bash
nc -zv 10.31.1.10 389
```
*Expected: `Connection to 10.31.1.10 389 port [tcp/ldap] succeeded!`*

### Test 3.2: Query Directory Using Bind User
```bash
ldapsearch -x -H ldap://10.31.1.10:389 \
  -D "cn=squidbind,dc=innspark,dc=in" \
  -y /etc/squid/ldap_password.txt \
  -b "ou=people,dc=innspark,dc=in" \
  "(uid=john.doe)"
```
*Expected: Successful dump of `john.doe` user object.*

### Test 3.3: Test Squid's LDAP Auth Helper Interactively
Run the helper manually and test credentials:
```bash
/usr/lib/squid/basic_ldap_auth \
  -b "ou=people,dc=innspark,dc=in" \
  -D "cn=squidbind,dc=innspark,dc=in" \
  -W /etc/squid/ldap_password.txt \
  -f "(&(uid=%s)(objectClass=posixAccount))" \
  -H ldap://10.31.1.10:389
```
Now type: `<username> <password>` and press Enter:
```text
john.doe UserSecret@2026
```
- **If output is `OK`:** Authentication helper is functioning properly.
- **If output is `ERR`:** Incorrect password or invalid user.
*(Press `Ctrl + C` to exit).*

### Test 3.4: Test Squid's Group ACL Helper Interactively
Run the group helper to verify membership in `proxy_users`:
```bash
/usr/lib/squid/ext_ldap_group_acl \
  -b "ou=groups,dc=innspark,dc=in" \
  -D "cn=squidbind,dc=innspark,dc=in" \
  -W /etc/squid/ldap_password.txt \
  -f "(&(objectClass=posixGroup)(cn=%g)(memberUid=%u))" \
  -H ldap://10.31.1.10:389
```
Now type: `<username> <groupname>` and press Enter:
```text
john.doe proxy_users
```
- **If output is `OK`:** Group check succeeds.
*(Press `Ctrl + C` to exit).*

---

## 4. Deploying Squid Configuration

Copy the production configuration file provided in `configs/squid.conf` to `/etc/squid/squid.conf`.

### Step 4.1: Deploy Configuration
```bash
sudo cp configs/squid.conf /etc/squid/squid.conf
```
*(Make sure IP addresses in `/etc/squid/squid.conf` match your network).*

### Step 4.2: Create ACL Whitelist and Blacklist Files
```bash
sudo touch /etc/squid/acl/whitelist_domains.txt
sudo touch /etc/squid/acl/blacklist_domains.txt

# Add sample blocked domains
cat << 'EOF' | sudo tee /etc/squid/acl/blacklist_domains.txt
.tiktok.com
.gambling.com
.bet365.com
EOF

# Set permissions
sudo chown -R proxy:proxy /etc/squid/acl
```

### Step 4.3: Test Configuration Syntax
```bash
sudo squid -k parse
```
*Review the output. Ensure there are no fatal errors or warnings.*

### Step 4.4: Restart and Enable Squid Service
```bash
sudo systemctl restart squid
sudo systemctl enable squid
sudo systemctl status squid
```

### Step 4.5: Verify Listening Port
```bash
ss -tulpn | grep 3128
```
*Expected output: `LISTEN ... 0.0.0.0:3128 ... squid`*
