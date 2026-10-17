"""Shared helpers: config, logging, IP math, password hashing."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import sys
from pathlib import Path
from typing import Any, Dict

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: str = "INFO", log_file: str | None = None) -> logging.Logger:
    """Configure a root logger that writes to stdout (and optionally a file)."""
    root = logging.getLogger("sslvpn")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = logging.Formatter(LOG_FORMAT)
    if not root.handlers:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        root.addHandler(sh)
        if log_file:
            Path(log_file).parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(log_file)
            fh.setFormatter(fmt)
            root.addHandler(fh)
    root.propagate = False
    return root


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

DEFAULTS: Dict[str, Any] = {
    "server": {
        "host": "0.0.0.0",
        "port": 443,
        "tls_min_version": "TLSv1_2",
        "cipher_suite": "ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:"
                         "ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:"
                         "ECDHE-RSA-AES128-GCM-SHA256",
        "cert_file": "certs/server.crt",
        "key_file": "certs/server.key",
        "ca_file": "certs/ca.crt",
        "require_client_cert": False,
        "dh_params_file": None,
    },
    "network": {
        "vpn_subnet": "10.8.0.0/24",
        "server_ip": "10.8.0.1",
        "ip_pool_start": "10.8.0.10",
        "ip_pool_end": "10.8.0.250",
        "mtu": 1400,
        "tun_name": "ssl0",
        "wan_interface": None,  # auto-detected if None
        "enable_nat": True,
        "enable_ip_forward": True,
        "dns_servers": ["8.8.8.8", "1.1.1.1"],
    },
    "session": {
        "max_clients": 50,
        "idle_timeout_seconds": 300,
        "keepalive_interval_seconds": 30,
        "max_connections_per_user": 2,
        "handshake_timeout_seconds": 30,
    },
    "security": {
        "auth_mode": "password",  # password | client_cert | both
        "password_iterations": 200_000,
        "rate_limit_attempts": 5,
        "rate_limit_window_seconds": 300,
        "lockout_seconds": 900,
        "token_bucket_interval_seconds": 0.2,
    },
    "logging": {
        "level": "INFO",
        "file": None,
    },
    "tun_enabled": True,  # set False for mock/loopback testing without root
}


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge override dict into base dict."""
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(path: str | os.PathLike) -> Dict[str, Any]:
    """Load a JSON config file merged over built-in defaults."""
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy of defaults
    cfg_path = Path(path)
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as fh:
            user_cfg = json.load(fh)
        cfg = deep_merge(cfg, user_cfg)
    return cfg


def save_config(path: str | os.PathLike, cfg: Dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256)
# --------------------------------------------------------------------------

def hash_password(password: str, salt: bytes | None = None,
                  iterations: int = 200_000) -> tuple[str, str, int]:
    """Return (salt_hex, hash_hex, iterations) using PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return salt.hex(), dk.hex(), iterations


def verify_password(password: str, salt_hex: str, hash_hex: str,
                    iterations: int) -> bool:
    """Constant-time verification of a password against a stored hash."""
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(dk.hex(), hash_hex)


# --------------------------------------------------------------------------
# IP address helpers
# --------------------------------------------------------------------------

def ip_to_int(ip: str) -> int:
    return int(ipaddress.IPv4Address(ip))


def int_to_ip(value: int) -> str:
    return str(ipaddress.IPv4Address(value))


def ip_in_subnet(ip: str, subnet: str) -> bool:
    try:
        return ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(subnet, strict=False)
    except ValueError:
        return False


def subnet_allows(subnets: list[str], ip: str) -> bool:
    """Check whether ip is permitted by an allowlist of subnets."""
    if not subnets:
        return False
    if "0.0.0.0/0" in subnets:
        return True
    return any(ip_in_subnet(ip, s) for s in subnets)