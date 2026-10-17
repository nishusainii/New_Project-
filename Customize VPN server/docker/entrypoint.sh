#!/usr/bin/env bash
# SSL VPN server container entrypoint.
#
#  1. initialises config / users / certificates on first run
#  2. applies SSLVPN_* environment overrides onto config/server_config.json
#  3. starts vpn_server.py in MOCK or real TUN mode
#
# The server is exec'd as PID 1 so `docker stop` (SIGTERM) triggers the
# server's own graceful shutdown handler.

set -euo pipefail

APP_DIR="/app"
CONFIG_DIR="$APP_DIR/config"
CERTS_DIR="$APP_DIR/certs"

mkdir -p "$CONFIG_DIR" "$CERTS_DIR"

echo "==> SSL VPN server container starting (app dir: $APP_DIR)"

# -- 1. default config -----------------------------------------------------
if [[ ! -f "$CONFIG_DIR/server_config.json" ]]; then
    echo "==> no server_config.json found; writing defaults"
    (cd "$APP_DIR" && python3 vpn_server.py init-config)
fi

# -- 2. empty users file -----------------------------------------------------
if [[ ! -f "$CONFIG_DIR/users.json" ]]; then
    echo '{"users": {}}' > "$CONFIG_DIR/users.json"
fi

# -- 3. certificates -----------------------------------------------------------
if [[ ! -f "$CERTS_DIR/server.crt" || ! -f "$CERTS_DIR/server.key" ]]; then
    server_name="${SSLVPN_SERVER_NAME:-vpn.local}"
    echo "==> no server certificate found; generating with CN=$server_name"
    bash "$APP_DIR/scripts/generate_certs.sh" "$server_name"
fi

# -- 4. environment overrides -----------------------------------------------------
echo "==> applying SSLVPN_* environment overrides"
(cd "$APP_DIR" && python3 docker/apply_env.py)

# -- 5. optional first-run admin seed (only when users.json is empty) ---------------
if [[ -n "${SSLVPN_ADMIN_PASSWORD:-}" ]]; then
    has_users="$(python3 -c 'import json,sys; print(1 if json.load(open(sys.argv[1])).get("users") else 0)' \
        "$CONFIG_DIR/users.json")"
    if [[ "$has_users" == "0" ]]; then
        echo "==> users.json is empty; seeding 'admin' from SSLVPN_ADMIN_PASSWORD"
        (cd "$APP_DIR" && python3 vpn_server.py add-user admin \
            --password "$SSLVPN_ADMIN_PASSWORD")
    else
        echo "==> users.json already has users; skipping admin seed"
    fi
fi

# -- 6. TUN mode decision --------------------------------------------------------
mock_flag=""
if [[ "${SSLVPN_MOCK:-0}" == "1" ]]; then
    echo "==> TUN mode: MOCK (in-memory, no privileges needed)"
    mock_flag="--mock-tun"
elif [[ -e /dev/net/tun ]]; then
    echo "==> TUN mode: REAL (/dev/net/tun present)"
else
    echo "!! /dev/net/tun is not available in this container; falling back to MOCK TUN"
    mock_flag="--mock-tun"
fi

# -- 7. start the server ------------------------------------------------------------
args=(start)
if [[ -n "$mock_flag" ]]; then
    args+=("$mock_flag")
fi

echo "==> exec: python3 vpn_server.py ${args[*]}"
exec python3 "$APP_DIR/vpn_server.py" "${args[@]}"