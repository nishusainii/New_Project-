#!/usr/bin/env bash
# Generate the certificate hierarchy for the SSL VPN:
#   certs/ca.crt          - self-signed CA
#   certs/server.crt|key  - server TLS certificate signed by the CA
#   certs/client.crt|key  - optional client certificate (for mTLS mode)
#
# Usage:  ./scripts/generate_certs.sh [server_hostname]
# Default server_hostname: vpn.local (use --verify-remote to test cert checking)

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$BASE_DIR/certs"
SERVER_NAME="${1:-vpn.local}"
DAYS=825

mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

echo "==> Generating CA key and certificate"
openssl genrsa -out ca.key 2048 2>/dev/null
openssl req -x509 -new -nodes -key ca.key -sha256 -days "$DAYS" \
    -subj "/CN=SSLVPN-CA/O=Innspark/C=IN" -out ca.crt

# Detect whether SERVER_NAME is an IP address or hostname for SAN
if [[ "$SERVER_NAME" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    SAN="IP:${SERVER_NAME},IP:127.0.0.1"
else
    SAN="DNS:${SERVER_NAME},DNS:vpn.local,IP:127.0.0.1"
fi

echo "==> Generating server key + CSR (SAN: $SAN)"
openssl genrsa -out server.key 2048 2>/dev/null
openssl req -new -key server.key \
    -subj "/CN=${SERVER_NAME}/O=Innspark/C=IN" \
    -addext "subjectAltName=${SAN}" \
    -out server.csr

echo "==> Signing server certificate"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -days "$DAYS" -sha256 \
    -extfile <(printf "subjectAltName=%s\nbasicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth" "$SAN") \
    -out server.crt

echo "==> Generating optional client certificate"
openssl genrsa -out client.key 2048 2>/dev/null
openssl req -new -key client.key -subj "/CN=vpn-user/O=Innspark/C=IN" \
    -out client.csr
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -days "$DAYS" -sha256 \
    -extfile <(printf "basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nextendedKeyUsage=clientAuth") \
    -out client.crt

rm -f server.csr client.csr ca.srl

echo
echo "Certificates written to $CERT_DIR:"
ls -1 "$CERT_DIR"
echo
echo "Next steps:"
echo "  python3 vpn_server.py add-user admin --password <pw>"
echo "  python3 vpn_server.py start --mock-tun   # test without root"
echo "  sudo ./scripts/setup_network.sh          # enable real TUN + NAT"