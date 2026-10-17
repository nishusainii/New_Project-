# Innspark Squid & LDAP Local Docker Demo Environment

This directory contains a **fully functional, containerized demo** of the entire solution designed to run directly on your laptop using Docker and Docker Compose.

---

## 1. Demo Architecture

All services communicate over `network_mode: host` to eliminate Docker bridge and iptables conflicts and utilize host DNS:

| Container Name | Service | Port | Description |
| :--- | :--- | :--- | :--- |
| **`innspark-ldap-demo`** | OpenLDAP (`slapd`) | `389` | Identity provider initialized with `dc=innspark,dc=in`, base OUs, bind user, and sample accounts. |
| **`innspark-squid-demo`** | Squid Proxy 7.x | `3128` | Forward proxy enforcing LDAP basic authentication, group ACLs, safe ports, and header anonymization. |
| **`innspark-portal-demo`** | Innspark Web Portal | `5000` | Custom cyber-dark web dashboard to manage LDAP users, whitelist/blacklist rules, live logs, and SARG views. |
| **`innspark-sarg-demo`** | SARG Log Analyzer | `8082` | Continuous log analyzer generating visual HTML reports from `/var/log/squid/access.log`. |

---

## 2. Quick Start

### Step 1: Start the Demo Stack
```bash
cd "squid web/docker-demo"
chmod +x *.sh
./start-demo.sh
```

### Step 2: Open the Web Interfaces in Your Browser
- **Innspark Unified Management Portal:**  
  [http://localhost:5000](http://localhost:5000)
- **SARG Visual Audit Reports:**  
  [http://localhost:8082](http://localhost:8082)

---

## 3. Run Automated Testing Suite

Execute the pre-built test script to validate all security controls:

```bash
./test-demo.sh
```

### What the Test Script Validates:
1. **LDAP Query:** Confirms OpenLDAP is online and user `john.doe` exists.
2. **Unauthenticated Request:** Tests `curl` through proxy without credentials; expects `HTTP 407 Proxy Authentication Required`.
3. **Authenticated Request:** Tests `curl` through proxy with valid LDAP credentials (`john.doe:UserSecret@2026`); expects `HTTP 200 OK`.
4. **Invalid Password:** Tests `curl` with a wrong password; expects rejection (`HTTP 407`).
5. **Blacklist Filtering:** Tests `curl` requesting `tiktok.com`; expects `HTTP 403 Forbidden`.
6. **Portal Health:** Confirms the Innspark Web Portal dashboard is active on port 5000.

---

## 4. Manual Testing from Terminal

You can also run manual curl tests anytime:

```bash
# Test 1: Should fail with 407
curl -I -x http://localhost:3128 https://www.google.com

# Test 2: Should succeed with 200/301
curl -I -x http://john.doe:UserSecret@2026@localhost:3128 https://www.google.com

# Test 3: Should be blocked by ACL with 403
curl -I -x http://john.doe:UserSecret@2026@localhost:3128 http://www.tiktok.com
```

---

## 5. Stopping the Demo

When finished testing, shut down the containers:

```bash
./stop-demo.sh
```
