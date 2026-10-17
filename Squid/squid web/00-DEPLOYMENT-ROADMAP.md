# Dual-Server Architecture & Deployment Roadmap
**Organization Domain:** `innspark.in`  
**LDAP Base DN:** `dc=innspark,dc=in`

---

## 1. System Topology Overview

This deployment separates the **Identity / Directory Service** and the **Forward Caching Proxy** onto two independent Linux servers (Ubuntu 22.04 / 24.04 or Debian 11/12). None of these services are installed on your local workstation.

```
                          ┌────────────────────────────────────────────────────────┐
                          │            SERVER 1: LDAP DIRECTORY & WEB UI           │
                          │  Hostname: ldap.innspark.in (e.g., 10.31.1.10)         │
                          │  - OpenLDAP Daemon (slapd)                             │
                          │  - LDAP Account Manager (LAM Web UI on Port 443/80)    │
                          │  - User & Group Management Dashboard                   │
                          └───────────────────────────┬────────────────────────────┘
                                                      │
                                                      │ LDAP Queries (Port 389 / 636)
                                                      │ User Auth & Group Checks
                                                      ▼
┌─────────────────────────┐   HTTP / HTTPS Proxy      ┌────────────────────────────────────────────────────────┐
│     CLIENT NETWORK      │  Traffic (Port 3128)      │          SERVER 2: SQUID PROXY & SARG SERVER           │
│  - Workstations         ├──────────────────────────►│  Hostname: proxy.innspark.in (e.g., 10.31.1.159)      │
│  - Developers / Admins  │   With LDAP Auth Header   │  - Squid Proxy (LDAP Basic Auth + Group ACLs)          │
│  - Subnets:             │                           │  - Security Hardening (ACLs, Safe Ports, Anonymity)    │
│    10.31.0.0/16, etc.   │                           │  - SARG Report Generator (Automated via Cron)          │
└─────────────────────────┘                           │  - Apache Web Server (Protected SARG Reports on :8080) │
                                                      └───────────────────────────┬────────────────────────────┘
                                                                                  │
                                                                                  │ Direct Outbound Web Traffic
                                                                                  ▼
                                                                       ┌──────────────────────┐
                                                                       │       INTERNET       │
                                                                       │ (Filtered & Audited) │
                                                                       └──────────────────────┘
```

---

## 2. Server Roles & IP Assignment Matrix

| Server Role | Recommended Hostname | Example IP | Core Services | Open Ports & Protocols |
| :--- | :--- | :--- | :--- | :--- |
| **Server 1** (Identity Provider) | `ldap.innspark.in` | `10.31.1.10` | OpenLDAP (`slapd`), LDAP Account Manager (LAM) | **389/TCP** (LDAP), **636/TCP** (LDAPS), **443/TCP** (Web UI), **22/TCP** (SSH) |
| **Server 2** (Forward Proxy) | `proxy.innspark.in` | `10.31.1.159` | Squid Proxy, SARG Generator, Innspark Web Portal | **3128/TCP** (Squid Proxy), **5000/TCP** (Innspark Portal), **8080/TCP** (SARG Web Reports), **22/TCP** (SSH) |
| **Clients** | LAN Endpoints | `10.31.x.x` | Browsers, CLI tools, OS Proxy settings | Egress allowed to `10.31.1.159:3128` |

> [!TIP]
> Replace the example IP addresses (`10.31.1.10` and `10.31.1.159`) with the exact static IPs assigned to your machines in the Innspark network.

---

## 3. Directory Structure of This Toolkit

All configuration files, scripts, and documentation in this folder are organized as follows:

```text
squid web/
├── 00-DEPLOYMENT-ROADMAP.md                 # This overview & IP/port architecture map
├── 01-SERVER1-LDAP-AND-WEBUI-SETUP.md      # Server 1: OpenLDAP & LDAP Account Manager (Web UI)
├── 02-SERVER2-SQUID-PROXY-SETUP.md         # Server 2: Squid installation, config & service setup
├── 03-SQUID-SECURITY-HARDENING.md          # Server 2: Advanced ACLs, anti-spoofing, privacy & firewall
├── 04-SARG-REPORTING-SETUP.md              # Server 2: SARG installation, cron & password-protected Web UI
├── 05-CLIENT-TESTING-AND-DIAGNOSTICS.md    # End-to-end verification, curl testing, diagnostics
├── 06-INSPARK-CUSTOM-WEB-PORTAL.md         # Server 2: Unified Custom Web Portal (Flask + SPA)
├── innspark-squid-portal/                  # Complete deployable Web UI application
│   ├── app.py                              # Flask REST API & controller
│   ├── config.py                           # Portal settings & LDAP credentials
│   ├── requirements.txt                    # Dependencies: flask, ldap3, gunicorn
│   ├── innspark-portal.service             # Systemd service unit for Server 2
│   ├── install-portal.sh                   # 1-command installer script
│   ├── README.md                           # Documentation & Nginx HTTPS setup
│   ├── templates/index.html                # Single-page web dashboard
│   └── static/                             # CSS styling & JS frontend logic
├── configs/
│   ├── ldap-base.ldif                      # Base directory tree (OUs, groups, bind user)
│   ├── squid.conf                          # Production Squid config with LDAP auth & group ACLs
│   ├── sarg.conf                           # Tuned SARG configuration for daily/weekly reports
│   └── apache-sarg.conf                    # Apache VirtualHost & htpasswd protection for SARG
└── scripts/
    ├── test-ldap-auth.sh                   # Helper script to test LDAP credentials directly on Server 2
    └── generate-sarg-daily.sh              # SARG automated generation wrapper script
```

---

## 4. Step-by-Step Execution Sequence

1. **Step 1: Deploy Server 1 (LDAP + Web UI)**  
   Follow `01-SERVER1-LDAP-AND-WEBUI-SETUP.md` to install OpenLDAP, initialize `dc=innspark,dc=in`, and set up LDAP Account Manager (LAM). Create your proxy groups and initial user accounts via the Web UI.
2. **Step 2: Deploy Server 2 (Squid Proxy)**  
   Follow `02-SERVER2-SQUID-PROXY-SETUP.md` to install Squid, configure authentication pointing to Server 1 (`10.31.1.10`), and test user group verification.
3. **Step 3: Harden Squid Security**  
   Follow `03-SQUID-SECURITY-HARDENING.md` to eliminate open proxy vulnerabilities, strip client tracking headers, limit connection abuses, and set firewall rules.
4. **Step 4: Enable SARG Reporting with Web GUI**  
   Follow `04-SARG-REPORTING-SETUP.md` to parse `/var/log/squid/access.log`, generate visual usage analytics, and serve them over an authenticated web page.
5. **Step 5: Client Onboarding & Diagnostics**  
   Follow `05-CLIENT-TESTING-AND-DIAGNOSTICS.md` to configure client devices, test authentication, and troubleshoot any edge cases.
6. **Step 6: Launch Innspark Custom Unified Web Portal**  
   Follow `06-INSPARK-CUSTOM-WEB-PORTAL.md` and run `install-portal.sh` on Server 2 to manage LDAP users, whitelist/blacklist ACLs, live logs, and SARG reports from a unified web interface (`http://10.31.1.159:5000`).
