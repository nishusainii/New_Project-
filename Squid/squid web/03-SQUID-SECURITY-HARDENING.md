# Server 2: Squid Proxy Security Hardening Guide
**Target Machine:** Server 2 (`proxy.innspark.in` — e.g., `10.31.1.159`)

---

## 1. Security Overview

An improperly configured proxy can turn into an open relay, leak internal network topologies, or become an entry point for lateral movement. This guide implements defense-in-depth across the application layer (Squid) and the network layer (Linux kernel & firewall).

---

## 2. Squid Application-Layer Hardening

### 2.1. Eliminating Open Proxy Vulnerability
Never allow global proxying. Access must strictly require **both** valid corporate source IP and authenticated credentials:

```squid
# 1. Define authorized internal networks
acl corporate_lan src 10.31.0.0/16
acl vpn_network    src 10.32.0.0/16

# 2. Require Authentication
acl authenticated_user proxy_auth REQUIRED

# 3. Deny anything not originating from authorized corporate networks
http_access deny !corporate_lan !vpn_network

# 4. Deny unauthenticated traffic
http_access deny !authenticated_user
```

### 2.2. Port Protocol Restrictions (Preventing Tunnel Abuses)
Attackers frequently use proxy `CONNECT` tunnels to bypass firewalls and access non-web ports (e.g., SMTP spam, SSH, RDP).

```squid
# Safe ports for standard HTTP/HTTPS/FTP
acl Safe_ports port 80          # http
acl Safe_ports port 21          # ftp
acl Safe_ports port 443         # https
acl Safe_ports port 70          # gopher
acl Safe_ports port 210         # wais
acl Safe_ports port 1025-65535  # unregistered ports
acl Safe_ports port 280         # http-mgmt
acl Safe_ports port 488         # gss-http
acl Safe_ports port 591         # filemaker
acl Safe_ports port 777         # multiling http

# SSL Ports allowed for CONNECT method
acl SSL_ports port 443

# Deny requests to unlisted or unsafe ports
http_access deny !Safe_ports

# Deny CONNECT method to non-SSL ports
http_access deny CONNECT !SSL_ports
```

### 2.3. Client Anonymity & Header Privacy
By default, proxies advertise the internal client IP in the `X-Forwarded-For` header and server version in the `Via` header. We strip these to preserve internal privacy:

```squid
# Remove internal client IP disclosure
forwarded_for delete

# Hide Squid version and proxy presence
via off

# Strip identifying HTTP headers
request_header_access X-Forwarded-For deny
request_header_access Via deny
request_header_access Server deny

# Mask proxy error page version details
visible_hostname proxy.innspark.in
dns_v4_first on
```

### 2.4. DoS and Abuse Mitigation
Prevent individual clients or rogue processes from exhausting server file descriptors and socket pools:

```squid
# Maximum concurrent TCP connections per single IP
acl max_client_connections maxconn 50
http_access deny max_client_connections

# Buffer and payload size limits
request_header_max_size 64 KB
request_body_max_size 100 MB
reply_header_max_size 64 KB
reply_body_max_size 500 MB all

# Timeout tuning to prevent lingering dead sockets
client_lifetime 4 hours
pconn_timeout 60 seconds
connect_timeout 30 seconds
request_timeout 30 seconds
```

---

## 3. Host & Network-Layer Hardening (UFW Firewall)

Ensure the proxy port (`3128`) is **never exposed to the public Internet**. Only authorized client subnets may connect.

### Step 3.1: Configure UFW Rules
Execute on Server 2:
```bash
# Reset UFW to default secure posture
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH with rate-limiting (anti-bruteforce)
sudo ufw limit 22/tcp

# Allow Squid proxy port (3128) ONLY from trusted corporate subnets
sudo ufw allow from 10.31.0.0/16 to any port 3128 proto tcp
sudo ufw allow from 10.32.0.0/16 to any port 3128 proto tcp

# Allow SARG Web Reports ONLY from Administrator workstations
sudo ufw allow from 10.31.1.0/24 to any port 8080 proto tcp

# Enable firewall
sudo ufw enable
sudo ufw status numbered
```

---

## 4. Linux Kernel Hardening (`/etc/sysctl.d/99-squid-security.conf`)

Tune TCP socket handling and anti-spoofing protections:

```bash
cat << 'EOF' | sudo tee /etc/sysctl.d/99-squid-security.conf
# Enable SYN Cookies against SYN flood attacks
net.ipv4.tcp_syncookies = 1

# Disable ICMP redirect acceptance
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0

# Enable IP spoofing protection (Reverse Path Filtering)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Increase system file descriptor limits for high proxy concurrency
fs.file-max = 2097152
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 8192
EOF

# Apply kernel settings immediately
sudo sysctl --system
```

---

## 5. Security Audit & Validation Checklist

Run the following checks after hardening:
1. **Port Scan from External Network:** Confirm port `3128` is `FILTERED` or `CLOSED` from any IP outside `10.31.0.0/16`.
2. **Unauthenticated Connection Attempt:**  
   `curl -x http://10.31.1.159:3128 http://example.com`  
   *Must return:* `HTTP/1.1 407 Proxy Authentication Required`.
3. **Connect to Forbidden Port:**  
   `curl -x http://user:pass@10.31.1.159:3128 http://example.com:25`  
   *Must return:* `HTTP/1.1 403 Forbidden`.
4. **Header Leak Check:**  
   Visit `http://ifconfig.me/all` through proxy; verify `via` and `x-forwarded-for` are absent.
