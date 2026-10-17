# ==============================================================================
# Innspark Solutions - Unified Squid & LDAP Web Portal Configuration
# Domain: innspark.in
# ==============================================================================

import os

# Server 1: LDAP Directory Settings
LDAP_HOST = os.getenv("LDAP_HOST", "10.31.1.10")
LDAP_PORT = int(os.getenv("LDAP_PORT", "389"))
LDAP_USE_SSL = os.getenv("LDAP_USE_SSL", "False").lower() in ("true", "1", "yes")

# Base DN & Tree Suffixes
BASE_DN = os.getenv("BASE_DN", "dc=innspark,dc=in")
USER_OU = os.getenv("USER_OU", f"ou=people,{BASE_DN}")
GROUP_OU = os.getenv("GROUP_OU", f"ou=groups,{BASE_DN}")

# OpenLDAP Administrative Bind (used by Portal for creating/modifying accounts)
ADMIN_DN = os.getenv("ADMIN_DN", f"cn=admin,{BASE_DN}")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Innspark@LDAPAdmin2026!")

# Squid Service Read-Only Bind (used for connection testing)
BIND_DN = os.getenv("BIND_DN", f"cn=squidbind,{BASE_DN}")
BIND_PASSWORD = os.getenv("BIND_PASSWORD", "SquidBindPassword@2026")

# Server 2: Local Squid Proxy Paths
SQUID_CONF_PATH = os.getenv("SQUID_CONF_PATH", "/etc/squid/squid.conf")
WHITELIST_PATH = os.getenv("WHITELIST_PATH", "/etc/squid/acl/whitelist_domains.txt")
BLACKLIST_PATH = os.getenv("BLACKLIST_PATH", "/etc/squid/acl/blacklist_domains.txt")
ACCESS_LOG_PATH = os.getenv("ACCESS_LOG_PATH", "/var/log/squid/access.log")
CACHE_LOG_PATH = os.getenv("CACHE_LOG_PATH", "/var/log/squid/cache.log")

# SARG Reports Configuration
SARG_OUTPUT_DIR = os.getenv("SARG_OUTPUT_DIR", "/var/www/html/sarg")
SARG_WEB_URL = os.getenv("SARG_WEB_URL", "http://10.31.1.159:8080/sarg/")
SARG_BIN_PATH = os.getenv("SARG_BIN_PATH", "/usr/bin/sarg")

# Portal Security & Flask Options
SECRET_KEY = os.getenv("SECRET_KEY", "innspark-cyber-portal-secret-key-2026-secure")
PERMANENT_SESSION_LIFETIME_DAYS = int(os.getenv("PERMANENT_SESSION_LIFETIME_DAYS", "7"))
PORTAL_HOST = os.getenv("PORTAL_HOST", "0.0.0.0")
PORTAL_PORT = int(os.getenv("PORTAL_PORT", "5000"))
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1")
