#!/usr/bin/env sh
# Health check: complete a real TLS handshake with the VPN listener.
# Exit code 0 means the server is accepting TLS connections.
# (certificates are baked into the image at /app/certs)

python3 - <<'PY'
import json
import socket
import ssl

cfg = json.load(open("/app/config/server_config.json"))
port = int(cfg["server"]["port"])
host = "127.0.0.1"

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.load_verify_locations(cafile="/app/certs/ca.crt")
ctx.check_hostname = False

s = socket.create_connection((host, port), timeout=3)
with ctx.wrap_socket(s, server_hostname="vpn.local") as tls:
    version = tls.version()
    if version not in ("TLSv1.2", "TLSv1.3"):
        raise SystemExit("unexpected TLS version: %s" % version)
print("TLS %s OK on %s:%d" % (version, host, port))
PY