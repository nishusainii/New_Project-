#!/usr/bin/env bash
# ==============================================================================
# Innspark Solutions - Docker Demo Environment Launcher
# Launches OpenLDAP, Squid Proxy, SARG Reports, and Innspark Web Portal
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================================"
echo "    INNSPIARK SECURE PROXY & LDAP DEMO - CONTAINER LAUNCHER           "
echo "======================================================================"

# 1. Ensure shared directories exist with open permissions for container users
echo "[1/4] Preparing shared volumes..."
mkdir -p shared-logs shared-sarg squid/acl
chmod -R 777 shared-logs shared-sarg squid/acl

# 2. Touch access.log if not present so volumes mount cleanly
touch shared-logs/access.log shared-logs/cache.log
chmod 666 shared-logs/*.log

# 3. Build and launch containers
echo "[2/4] Building and starting Docker containers (network_mode: host)..."
docker compose up -d --build

# 4. Wait for services to initialize
echo "[3/4] Waiting for OpenLDAP and Squid to initialize (approx 8 seconds)..."
sleep 8

# 5. Output Access Summary
echo "======================================================================"
echo " [SUCCESS] Demo Stack Running on Your Laptop!"
echo "======================================================================"
echo " 🌐 Innspark Web Portal : http://localhost:5000"
echo " 📊 SARG Visual Reports : http://localhost:8082"
echo " 🛡️ Squid Proxy Port   : 127.0.0.1:3128"
echo " 🏢 OpenLDAP Port       : 127.0.0.1:389"
echo "----------------------------------------------------------------------"
echo " Default Demo Credentials:"
echo "   - Standard User : john.doe / UserSecret@2026"
echo "   - Admin User    : nishu.admin / AdminSecret@2026"
echo "   - LDAP Bind     : cn=squidbind,dc=innspark,dc=in / SquidBindPassword@2026"
echo "   - LDAP Root     : cn=admin,dc=innspark,dc=in / Innspark@LDAPAdmin2026!"
echo "----------------------------------------------------------------------"
echo " Run automated verification tests with:"
echo "   ./test-demo.sh"
echo "======================================================================"
