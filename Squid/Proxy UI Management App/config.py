"""
Innspark Squid Proxy Management Portal - Configuration
Server Target: 10.31.1.159 (proxyserver)
Port: 5000
"""

import os

# Base directory of the portal
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directory for portal state and admin credentials
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Web Server Settings
HOST = "0.0.0.0"
PORT = 5000
SECRET_KEY = os.environ.get("PORTAL_SECRET_KEY", "innspark-squid-secret-key-2026-prod-9e9de80a")
SESSION_COOKIE_NAME = "innspark_squid_session"
SESSION_COOKIE_HTTPONLY = True
PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

# Admin Credentials File
ADMIN_CREDS_FILE = os.path.join(DATA_DIR, "admin_creds.json")

# Default Admin (initialized if file doesn't exist)
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "admin@123"

# Squid Configuration Paths on 10.31.1.159
SQUID_CONF = "/etc/squid/squid.conf"
SQUID_PASSWD_FILE = "/etc/squid/password"
SQUID_ACL_DIR = "/etc/squid/acl"
SQUID_ACL_USERS_DIR = "/etc/squid/acl"
SQUID_ACL_DOMAINS_DIR = "/etc/squid/acl/domains"
SQUID_ACL_IPS_DIR = "/etc/squid/acl/ips"
SQUID_ALLOWED_IPS_FILE = "/etc/squid/allowed_ips.txt"

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
    {"ip": "10.31.1.159",  "name": "Proxy Server 1", "port": 5000},
    {"ip": "10.31.88.24",  "name": "Proxy Server 2", "port": 5000},
    {"ip": "10.31.1.24",   "name": "Proxy Server 3", "port": 5000},
    {"ip": "10.31.212.14", "name": "Proxy Server 4", "port": 5000},
]
FLEET_TIMEOUT = 5  # seconds for cross-server API calls

