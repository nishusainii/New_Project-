"""
Innspark Squid Proxy Management Portal - Dedicated Configuration for 10.31.212.14
Server Target: 10.31.212.14 (offsec-asianetproxy)
Role: Audit Proxy & FortiGate SSL-VPN Forwarder
Port: 8085 on interface ens18
Firewall Policy: Restricted / Isolated Egress (Allowed specific destination IPs only)
"""

import os

# Base directory of the portal
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directory for portal state and admin credentials
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Node Identity & Audit Proxy Specifications
SERVER_NAME = "Audit Proxy Server"
SERVER_IP = "10.31.212.14"
PRIMARY_PORT = 8085
PRIMARY_INTERFACE = "ens18"
GATEWAY_IP = "10.31.212.1"
IS_AUDIT_PROXY = True

# Web Server Settings
HOST = "0.0.0.0"
PORT = 5000
SECRET_KEY = os.environ.get("PORTAL_SECRET_KEY", "innspark-audit-proxy-secret-212-14-9e9de80a")
SESSION_COOKIE_NAME = "innspark_audit_session"
SESSION_COOKIE_HTTPONLY = True
PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

# Admin Credentials File
ADMIN_CREDS_FILE = os.path.join(DATA_DIR, "admin_creds.json")

# Default Admin (initialized if file doesn't exist)
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin@123"

# Squid Configuration Paths on 10.31.212.14
SQUID_CONF = "/etc/squid/squid.conf"
SQUID_PASSWD_FILE = "/etc/squid/password"
SQUID_ACL_DIR = "/etc/squid/acl"
SQUID_ACL_USERS_DIR = "/etc/squid/acl"
SQUID_ACL_DOMAINS_DIR = "/etc/squid/acl/domains"
SQUID_ACL_IPS_DIR = "/etc/squid/acl/ips"
SQUID_ALLOWED_IPS_FILE = "/etc/squid/allowed_ips.txt"
SQUID_OPENFORTIVPN_CLIENTS_FILE = "/etc/squid/openfortivpn_clients.txt"

# nftables Firewall Configuration Path
NFTABLES_CONF = "/etc/nftables.conf"

# Squid Logs
SQUID_ACCESS_LOG = "/var/log/squid/access.log"
SQUID_CACHE_LOG = "/var/log/squid/cache.log"

# SARG Reports
SARG_REPORTS_DIR = "/var/www/html/sarg"
SARG_BINARY = "/usr/local/sbin/sarg"

# Backup Configuration
BACKUP_DIR = "/etc/squid/squid_backups/portal_backups"
ARCHIVE_DIR = "/etc/squid/squid_backups/portal_archives"
MAX_ACTIVE_BACKUPS = 5   # Automatically rotate and retain the last 5 active snapshots
MAX_ARCHIVE_BACKUPS = 5  # Automatically purge and retain only the last 5 compressed archives (.tar.gz)

# Fleet: All Squid Proxy Servers in the cluster (Multi-Server Dashboard)
FLEET_SERVERS = [
    {"ip": "10.31.212.14", "name": "Audit Proxy (This Server)", "port": 5000, "current": True},
    {"ip": "10.31.1.159",  "name": "Proxy Server 1 (Multi-WAN)", "port": 5000},
    {"ip": "10.31.88.24",  "name": "Proxy Server 2", "port": 5000},
    {"ip": "10.31.1.24",   "name": "Proxy Server 3 (Multi-WAN)", "port": 5000},
]
FLEET_TIMEOUT = 5  # seconds for cross-server API calls
