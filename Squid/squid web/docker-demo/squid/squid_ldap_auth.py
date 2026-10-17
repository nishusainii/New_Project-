#!/usr/bin/env python3
# ==============================================================================
# Innspark Squid Basic LDAP Authentication Helper
# Communicates via stdin/stdout with Squid Daemon
# ==============================================================================

import sys
import os
from ldap3 import Server, Connection, ALL

LDAP_HOST = os.getenv("LDAP_HOST", "127.0.0.1")
LDAP_PORT = int(os.getenv("LDAP_PORT", "389"))
BASE_DN = os.getenv("BASE_DN", "dc=innspark,dc=in")
USER_OU = os.getenv("USER_OU", f"ou=people,{BASE_DN}")

server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL, connect_timeout=3)

for line in sys.stdin:
    clean = line.strip()
    if not clean:
        continue
    parts = clean.split()
    if len(parts) >= 2:
        username = parts[0]
        password = parts[1]
        user_dn = f"uid={username},{USER_OU}"
        try:
            conn = Connection(server, user=user_dn, password=password, auto_bind=True)
            if conn.bound:
                sys.stdout.write("OK\n")
            else:
                sys.stdout.write("ERR\n")
            conn.unbind()
        except Exception:
            sys.stdout.write("ERR\n")
    else:
        sys.stdout.write("ERR\n")
    sys.stdout.flush()
