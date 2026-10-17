#!/usr/bin/env python3
# ==============================================================================
# Innspark Squid LDAP Group Authorization Helper
# Verifies memberUid in ou=groups,dc=innspark,dc=in
# ==============================================================================

import sys
import os
from ldap3 import Server, Connection, ALL

LDAP_HOST = os.getenv("LDAP_HOST", "127.0.0.1")
LDAP_PORT = int(os.getenv("LDAP_PORT", "389"))
BASE_DN = os.getenv("BASE_DN", "dc=innspark,dc=in")
GROUP_OU = os.getenv("GROUP_OU", f"ou=groups,{BASE_DN}")
ADMIN_DN = os.getenv("ADMIN_DN", f"cn=admin,{BASE_DN}")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Innspark@LDAPAdmin2026!")

server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL, connect_timeout=3)

for line in sys.stdin:
    clean = line.strip()
    if not clean:
        continue
    parts = clean.split()
    if len(parts) >= 2:
        username = parts[0]
        groupname = parts[1]
        try:
            conn = Connection(server, user=ADMIN_DN, password=ADMIN_PASSWORD, auto_bind=True)
            search_filter = f"(&(objectClass=posixGroup)(cn={groupname})(memberUid={username}))"
            conn.search(GROUP_OU, search_filter, attributes=["cn", "memberUid"])
            if len(conn.entries) > 0:
                sys.stdout.write("OK\n")
            else:
                sys.stdout.write("ERR\n")
            conn.unbind()
        except Exception:
            sys.stdout.write("ERR\n")
    else:
        sys.stdout.write("ERR\n")
    sys.stdout.flush()
