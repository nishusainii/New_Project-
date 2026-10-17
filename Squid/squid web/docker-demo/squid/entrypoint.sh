#!/bin/sh
set -e

# Remove stale PID files if container was forcibly restarted
rm -f /var/run/squid.pid /run/squid.pid 2>/dev/null || true

# Ensure permissions
chown -R squid:squid /var/log/squid /etc/squid/acl

# Create swap directories if not already created
if [ ! -d /var/spool/squid/00 ]; then
    echo "[SQUID] Initializing cache swap directories..."
    squid -z -N
fi

echo "[SQUID] Starting Squid in foreground on port 3128..."
exec squid -NYCd 1
