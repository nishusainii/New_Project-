# syntax=docker/dockerfile:1
#
# SSL VPN server image — pure Python stdlib, zero pip dependencies.
#
#   docker build -t innspark/sslvpn:1.0.0 .
#
# Two runtime modes (chosen by the entrypoint at container start):
#   * mock TUN  — in-memory tunnel; no privileges required.
#   * real TUN  — kernel TUN device + NAT; needs /dev/net/tun + NET_ADMIN.
#
FROM python:3.11-slim

# iproute2 -> `ip` for TUN interface configuration (real TUN mode)
# iptables -> NAT/MASQUERADE for VPN clients (real TUN mode)
# openssl  -> first-run certificate generation (scripts/generate_certs.sh)
# apt's default User-Agent is 503'd by some CDN edges / transparent proxies,
# so we send a browser-like UA instead. If apt still fails the build logs a
# warning and remains usable in MOCK mode.
RUN set -eux; \
    printf 'Acquire::http::User-Agent "Mozilla/5.0 (compatible; APT-Client)";\n' \
        > /etc/apt/apt.conf.d/99user-agent; \
    for i in 1 2 3; do \
        apt-get update \
        && apt-get install -y --no-install-recommends iproute2 iptables openssl \
        && rm -rf /var/lib/apt/lists/* \
        && break \
        || { echo "apt attempt $i failed; retrying in 3s..."; sleep 3; }; \
    done; \
    command -v ip >/dev/null && command -v iptables >/dev/null && command -v openssl >/dev/null \
        || echo "WARNING: apt install failed (offline build?); mock mode only"

WORKDIR /app

# Pure-stdlib project: copy everything the server, CLI and entrypoint need.
COPY sslvpn/       sslvpn/
COPY config/       config/
COPY certs/        certs/
COPY scripts/      scripts/
COPY docker/       docker/
COPY vpn_server.py vpn_client.py ./
COPY README.md     README.md

# Import smoke test — fail the build early if the module graph is broken.
RUN python3 -c "import sys; sys.path.insert(0, '/app'); import sslvpn.server, sslvpn.client; import sslvpn.protocol, sslvpn.auth, sslvpn.tun, sslvpn.utils; print('stdlib import smoke test OK')"

# TLS listener port (configurable via SSLVPN_PORT / server_config.json)
EXPOSE 443

# The server opens /dev/net/tun and runs iptables, so the image runs as root
# inside the container (same convention as openvpn/wireguard images). For a
# mock-only deployment you can add `user: "1000:1000"` to the service.
USER root

# Health check: real TLS handshake against the listener.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["/app/docker/healthcheck.sh"]

ENTRYPOINT ["/app/docker/entrypoint.sh"]