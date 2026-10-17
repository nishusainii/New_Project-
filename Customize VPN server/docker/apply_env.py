#!/usr/bin/env python3
"""Apply SSLVPN_* environment variables onto config/server_config.json.

Runs inside the container at startup, before the server starts, so a plain
`docker run` / `docker compose` can tune every server setting without editing
the JSON on disk.  Booleans accept 1/true/yes/on, lists are comma-separated,
empty values are ignored (the config file keeps its default).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

CONFIG = Path("/app/config/server_config.json")

Converter = Callable[[str], Any]


def _bool(v: str) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "on")


def _int(v: str) -> int:
    return int(str(v).strip())


def _list(v: str) -> list[str]:
    return [x.strip() for x in str(v).split(",") if x.strip()]


# env var -> ((config path...), converter)
MAPPINGS: dict[str, tuple[tuple[str, ...], Converter]] = {
    # server / TLS
    "SSLVPN_HOST": (("server", "host"), str),
    "SSLVPN_PORT": (("server", "port"), _int),
    "SSLVPN_TLS_MIN_VERSION": (("server", "tls_min_version"), str),
    "SSLVPN_CIPHER_SUITE": (("server", "cipher_suite"), str),
    "SSLVPN_CERT_FILE": (("server", "cert_file"), str),
    "SSLVPN_KEY_FILE": (("server", "key_file"), str),
    "SSLVPN_CA_FILE": (("server", "ca_file"), str),
    "SSLVPN_REQUIRE_CLIENT_CERT": (("server", "require_client_cert"), _bool),
    "SSLVPN_DH_PARAMS_FILE": (("server", "dh_params_file"), str),
    # network / TUN
    "SSLVPN_VPN_SUBNET": (("network", "vpn_subnet"), str),
    "SSLVPN_SERVER_IP": (("network", "server_ip"), str),
    "SSLVPN_IP_POOL_START": (("network", "ip_pool_start"), str),
    "SSLVPN_IP_POOL_END": (("network", "ip_pool_end"), str),
    "SSLVPN_MTU": (("network", "mtu"), _int),
    "SSLVPN_TUN_NAME": (("network", "tun_name"), str),
    "SSLVPN_WAN_INTERFACE": (("network", "wan_interface"), str),
    "SSLVPN_ENABLE_NAT": (("network", "enable_nat"), _bool),
    "SSLVPN_ENABLE_IP_FORWARD": (("network", "enable_ip_forward"), _bool),
    "SSLVPN_DNS_SERVERS": (("network", "dns_servers"), _list),
    # session
    "SSLVPN_MAX_CLIENTS": (("session", "max_clients"), _int),
    "SSLVPN_IDLE_TIMEOUT": (("session", "idle_timeout_seconds"), _int),
    "SSLVPN_KEEPALIVE_INTERVAL": (("session", "keepalive_interval_seconds"), _int),
    "SSLVPN_MAX_CONNECTIONS_PER_USER": (("session", "max_connections_per_user"), _int),
    "SSLVPN_HANDSHAKE_TIMEOUT": (("session", "handshake_timeout_seconds"), _int),
    # security
    "SSLVPN_AUTH_MODE": (("security", "auth_mode"), str),
    "SSLVPN_PASSWORD_ITERATIONS": (("security", "password_iterations"), _int),
    "SSLVPN_RATE_LIMIT_ATTEMPTS": (("security", "rate_limit_attempts"), _int),
    "SSLVPN_RATE_LIMIT_WINDOW": (("security", "rate_limit_window_seconds"), _int),
    "SSLVPN_LOCKOUT_SECONDS": (("security", "lockout_seconds"), _int),
    # logging
    "SSLVPN_LOG_LEVEL": (("logging", "level"), str),
    "SSLVPN_LOG_FILE": (("logging", "file"), str),
    # top-level
    "SSLVPN_TUN_ENABLED": (("tun_enabled",), _bool),
}


def main() -> int:
    if not CONFIG.exists():
        print(f"  ! {CONFIG} not found; nothing to apply")
        return 0
    cfg: dict = json.loads(CONFIG.read_text(encoding="utf-8"))
    changed = False
    for var, (path, convert) in sorted(MAPPINGS.items()):
        raw = os.environ.get(var)
        if raw is None or raw == "":
            continue
        node: Any = cfg
        for key in path[:-1]:
            node = node.setdefault(key, {})
        try:
            value = convert(raw)
        except ValueError as exc:
            print(f"  ! {var}={raw!r} invalid: {exc} (skipped)")
            continue
        node[path[-1]] = value
        changed = True
        print(f"  applied {var} = {value!r}")
    if changed:
        CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        print(f"  -> updated {CONFIG}")
    else:
        print("  (no SSLVPN_* overrides applied)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())