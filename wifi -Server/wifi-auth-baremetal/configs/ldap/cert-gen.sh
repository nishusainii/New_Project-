#!/usr/bin/env bash
# ==============================================================================
# Automated TLS Certificate Generator for OpenLDAP (LDAPS Port 636)
# ==============================================================================

set -euo pipefail

CERT_DIR="/etc/ssl/openldap"
SERVER_IP="${1:-192.168.2.12}"
DOMAIN="innspark.in"

echo "Generating Internal Certificate Authority and Server Certificates in $CERT_DIR..."
sudo mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

# 1. Generate Internal CA
if [ ! -f ldap-ca.pem ]; then
    sudo openssl req -new -x509 -nodes -days 3650 \
      -keyout ldap-ca.key -out ldap-ca.pem \
      -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Innspark Technologies/OU=Security/CN=Innspark-Internal-LDAP-CA"
    echo "✔ Internal CA Created."
fi

# 2. Generate Server Certificate
sudo openssl req -new -nodes -days 1825 \
  -keyout ldap-server.key -out ldap-server.csr \
  -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=Innspark Technologies/OU=IT/CN=$SERVER_IP"

# 3. Sign with CA
sudo openssl x509 -req -days 1825 \
  -in ldap-server.csr -CA ldap-ca.pem -CAkey ldap-ca.key -set_serial 01 \
  -out ldap-server.pem

# 4. Set secure permissions for openldap user
sudo chown -R openldap:openldap "$CERT_DIR"
sudo chmod 600 "$CERT_DIR/ldap-server.key" "$CERT_DIR/ldap-ca.key"
sudo chmod 644 "$CERT_DIR/ldap-server.pem" "$CERT_DIR/ldap-ca.pem"

echo "✔ TLS Certificates successfully generated in $CERT_DIR."
