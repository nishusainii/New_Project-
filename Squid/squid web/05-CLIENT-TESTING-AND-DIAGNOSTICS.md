# Client Testing, Onboarding & Troubleshooting Guide
**Proxy Server:** `10.31.1.159:3128` | **LDAP Server:** `10.31.1.10:389`

---

## 1. Client-Side Testing (Command Line)

Run these tests from any workstation in the corporate network (`10.31.0.0/16`):

### Test 1: Unauthenticated Connection
A request without credentials must be rejected with `HTTP 407 Proxy Authentication Required`:
```bash
curl -I -x http://10.31.1.159:3128 https://www.google.com
```
*Expected Output:*
```text
HTTP/1.1 407 Proxy Authentication Required
Proxy-Authenticate: Basic realm="Innspark Corporate Secure Proxy - Authentication Required"
```

### Test 2: Valid Authentication
Test with an LDAP user created in Server 1's LAM Web UI:
```bash
curl -I -x http://john.doe:UserSecret@2026@10.31.1.159:3128 https://www.google.com
```
*Expected Output:*
```text
HTTP/1.1 200 OK (or HTTP/1.1 301/302 Moved)
```

### Test 3: Invalid Password
```bash
curl -I -x http://john.doe:WrongPassword@10.31.1.159:3128 https://www.google.com
```
*Expected Output:*
```text
HTTP/1.1 407 Proxy Authentication Required
```

### Test 4: Blacklisted / Blocked Domain
Attempt to browse a domain listed in `/etc/squid/acl/blacklist_domains.txt`:
```bash
curl -I -x http://john.doe:UserSecret@2026@10.31.1.159:3128 http://www.tiktok.com
```
*Expected Output:*
```text
HTTP/1.1 403 Forbidden
```

---

## 2. Client Browser & OS Configuration

### Option A: Mozilla Firefox (Manual Proxy Configuration)
1. Open **Settings** -> Search for **Network Settings**.
2. Select **Manual proxy configuration**.
3. **HTTP Proxy:** `10.31.1.159`, Port: `3128`.
4. Check **"Also use this proxy for HTTPS"**.
5. Check **"Proxy DNS when using SOCKS v5"** (if applicable).
6. Click **OK**.
7. Browse to any website; the browser will present an authentication dialog. Enter LDAP username and password.

### Option B: Linux / macOS Terminal Shell Variables
Add to `~/.bashrc` or `~/.zshrc`:
```bash
export http_proxy="http://john.doe:UserSecret@2026@10.31.1.159:3128"
export https_proxy="http://john.doe:UserSecret@2026@10.31.1.159:3128"
export no_proxy="localhost,127.0.0.1,10.31.0.0/16,.innspark.in"
```

---

## 3. Server-Side Diagnostics & Log Inspection

### 3.1. Monitor Live Squid Traffic (on Server 2)
Watch live traffic with client IP, authenticated user, HTTP code, and URL:
```bash
sudo tail -f /var/log/squid/access.log | awk '{print $3, "User:" $8, "Status:" $4, "URL:" $7}'
```
- A successful request shows: `TCP_TUNNEL/200` or `TCP_MISS/200` with the LDAP username.
- A failed auth shows: `TCP_DENIED/407`.

### 3.2. Check Squid Internal Errors & LDAP Helper Logs
```bash
sudo tail -f /var/log/squid/cache.log
```
Look for helper messages such as:
- `basic_ldap_auth: WARNING: LDAP search failed`
- `ext_ldap_group_acl: helper: User not in group`

### 3.3. Monitor LDAP Server Queries (on Server 1)
To verify queries arriving from Server 2:
```bash
sudo journalctl -u slapd -f
```

---

## 4. Common Troubleshooting Scenarios

| Issue Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| `HTTP 407` loop despite entering correct password | Search filter mismatch in `squid.conf` | Verify whether user object in LDAP uses `posixAccount` or `inetOrgPerson`. Check search filter `(&(uid=%s)(objectClass=posixAccount))`. |
| `HTTP 403 Forbidden` for valid users | User is not in `proxy_users` group | Log into LAM Web UI (`http://10.31.1.10/lam`), navigate to **Groups**, edit `proxy_users`, and verify user's UID is in `memberUid`. |
| Connection times out from Client to Proxy | Firewall blocking port 3128 | On Server 2, run `sudo ufw status`. Verify rule `3128/tcp ALLOW from 10.31.0.0/16`. |
| SARG reports empty or missing users | Squid log format not logging username | Ensure `squid.conf` uses `logformat combined ...` or default format containing `%un` (authenticated username), and that clients are authenticating. |
| `basic_ldap_auth: unable to bind to LDAP server` | Bind password wrong or port 389 closed | On Server 2, run `nc -zv 10.31.1.10 389` and test bind with `./scripts/test-ldap-auth.sh`. |
