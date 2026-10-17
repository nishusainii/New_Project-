# Server 1: OpenLDAP Directory & Web UI (LAM) Setup
**Target Machine:** Server 1 (`ldap.innspark.in` — e.g., `10.31.1.10`)  
**Domain:** `innspark.in` | **Base DN:** `dc=innspark,dc=in`

---

## 1. Overview
This server acts as the centralized identity provider. It hosts:
1. **OpenLDAP (`slapd`)**: Directory holding user accounts and proxy permission groups.
2. **LDAP Account Manager (LAM)**: Web interface for administrators to create, edit, activate, or disable users and assign proxy groups directly from a browser.

---

## 2. Step-by-Step Installation (Execute on Server 1)

### Step 2.1: Update System & Install OpenLDAP
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install slapd ldap-utils -y
```
*(During installation, you may be prompted to enter an administrator password. Remember this password.)*

### Step 2.2: Reconfigure OpenLDAP for `innspark.in`
Run the debconf reconfigurator:
```bash
sudo dpkg-reconfigure slapd
```
Answer the prompts as follows:
- **Omit OpenLDAP server configuration?** `No`
- **DNS domain name:** `innspark.in`
- **Organization name:** `Innspark Solutions`
- **Administrator password:** *(Choose a strong password, e.g., `Innspark@LDAPAdmin2026!`)*
- **Confirm password:** *(Re-type the password)*
- **Do you want the database to be removed when slapd is purged?** `No`
- **Move old database?** `Yes`

### Step 2.3: Verify OpenLDAP Status & Base Tree
```bash
sudo systemctl status slapd
```
Query the base domain:
```bash
ldapsearch -x -b "dc=innspark,dc=in" -s base '(objectclass=*)' namingContexts
```
Expected output should contain:
```text
dn:
namingContexts: dc=innspark,dc=in
```

---

## 3. Initialize Base Organizational Units & Bind Account

Create the core organizational units (`people` for users, `groups` for proxy permission groups) and a dedicated read-only bind account for Squid (`cn=squidbind`).

### Step 3.1: Create Base LDIF File
On Server 1, create `/tmp/innspark-init.ldif`:
```bash
cat << 'EOF' > /tmp/innspark-init.ldif
# Organizational Unit for Users
dn: ou=people,dc=innspark,dc=in
objectClass: organizationalUnit
ou: people

# Organizational Unit for Groups
dn: ou=groups,dc=innspark,dc=in
objectClass: organizationalUnit
ou: groups

# Dedicated Bind Account for Squid Proxy
dn: cn=squidbind,dc=innspark,dc=in
objectClass: top
objectClass: person
objectClass: organizationalPerson
cn: squidbind
sn: ServiceAccount
description: Dedicated service account for Squid Proxy LDAP queries
userPassword: SquidBindPassword@2026

# Primary Proxy Users Group (Standard Access)
dn: cn=proxy_users,ou=groups,dc=innspark,dc=in
objectClass: top
objectClass: posixGroup
cn: proxy_users
gidNumber: 10001
description: Standard internet proxy users

# Admin Proxy Group (Unrestricted Access)
dn: cn=proxy_admins,ou=groups,dc=innspark,dc=in
objectClass: top
objectClass: posixGroup
cn: proxy_admins
gidNumber: 10002
description: Proxy administrators with elevated access
EOF
```

### Step 3.2: Import LDIF into OpenLDAP
Import the configuration using the OpenLDAP admin credentials:
```bash
ldapadd -x -D "cn=admin,dc=innspark,dc=in" -W -f /tmp/innspark-init.ldif
```
*(Enter the OpenLDAP administrator password when prompted).*

### Step 3.3: Verify Created Tree
```bash
ldapsearch -x -b "dc=innspark,dc=in" -D "cn=admin,dc=innspark,dc=in" -W "(objectClass=*)" dn
```
You should see:
- `ou=people,dc=innspark,dc=in`
- `ou=groups,dc=innspark,dc=in`
- `cn=squidbind,dc=innspark,dc=in`
- `cn=proxy_users,ou=groups,dc=innspark,dc=in`
- `cn=proxy_admins,ou=groups,dc=innspark,dc=in`

---

## 4. Install & Configure LDAP Account Manager (LAM Web UI)

LDAP Account Manager provides an intuitive, form-based Web UI for managing users, passwords, and groups.

### Step 4.1: Install LAM & Apache
```bash
sudo apt install ldap-account-manager apache2 php libapache2-mod-php -y
```

### Step 4.2: Enable Apache & Start Services
```bash
sudo systemctl enable apache2
sudo systemctl restart apache2
```

### Step 4.3: Access the Web UI
Open your browser and navigate to:
```text
http://<SERVER1_IP>/lam
```
*(Example: `http://10.31.1.10/lam`)*

### Step 4.4: First-Time LAM Configuration Wizard
1. In the top right corner, click **"LAM configuration"**.
2. Click **"Edit server profiles"**.
3. Enter the default master password: `lam` (you will be prompted to change it).
4. Under the **"General settings"** tab:
   - **Tree suffix:** `dc=innspark,dc=in`
   - **Default language:** `English`
5. Under the **"Server settings"** tab:
   - **Server address:** `ldap://localhost:389`
   - **Use TLS:** Optional / Unchecked for initial test (enable after setting certificates).
6. Under the **"Account types"** tab:
   - **Users:**
     - List suffix: `ou=people,dc=innspark,dc=in`
     - Available modules: Ensure `Unix (posixAccount)` and `Personal (inetOrgPerson)` are active.
   - **Groups:**
     - List suffix: `ou=groups,dc=innspark,dc=in`
     - Available modules: `Unix (posixGroup)`.
7. Under the **"Security settings"** tab:
   - **List of valid users:** `cn=admin,dc=innspark,dc=in`
8. Click **Save** at the bottom of the page.

---

## 5. Creating Users & Managing Proxy Access via Web UI

Once configured, manage users directly from `http://<SERVER1_IP>/lam`:

### Step 5.1: Log into LAM
1. Navigate to `http://<SERVER1_IP>/lam`.
2. Select your profile (`innspark`).
3. **Password:** Enter your OpenLDAP `admin` password.
4. Click **Login**.

### Step 5.2: Create a New Proxy User
1. Click the **Users** tab at the top.
2. Click **New user**.
3. Fill in the user profile:
   - **User name (UID):** `john.doe`
   - **First name:** `John`
   - **Last name:** `Doe`
   - **Password:** Set user's password (e.g., `UserSecret@2026`).
4. Click the **Unix** subtab:
   - Assign primary group or add `proxy_users` to the secondary groups.
5. Click **Save**.

### Step 5.3: Add User to Proxy Group
1. Click the **Groups** tab.
2. Click the edit icon next to `proxy_users`.
3. Select `john.doe` from the user list and add them as a member.
4. Click **Save**.

Now `john.doe` is in `cn=proxy_users,ou=groups,dc=innspark,dc=in` and ready to authenticate through Squid!

---

## 6. Firewall Configuration (Server 1)

Allow LDAP and Web UI traffic only from your internal trusted subnets:

```bash
# Allow SSH for administration
sudo ufw allow 22/tcp

# Allow Web UI access from corporate network
sudo ufw allow from 10.31.0.0/16 to any port 80 proto tcp
sudo ufw allow from 10.31.0.0/16 to any port 443 proto tcp

# Allow LDAP queries strictly from Squid Proxy Server (Server 2 IP: 10.31.1.159)
sudo ufw allow from 10.31.1.159 to any port 389 proto tcp
sudo ufw allow from 10.31.1.159 to any port 636 proto tcp

# Enable firewall
sudo ufw enable
sudo ufw status verbose
```
