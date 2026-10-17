"""Authentication: user store, rate limiting, client-cert mapping."""

from __future__ import annotations

import json
import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import verify_password

log = logging.getLogger("sslvpn.auth")


@dataclass
class User:
    """A VPN user account."""

    username: str
    salt_hex: str
    hash_hex: str
    iterations: int
    enabled: bool = True
    vpn_ip: Optional[str] = None        # fixed IP; None = auto from pool
    allowed_subnets: list[str] = field(default_factory=lambda: ["0.0.0.0/0"])
    bandwidth_kbps: int = 0             # 0 = unlimited
    client_cn: Optional[str] = None     # expected TLS client cert CN (mTLS)
    groups: list[str] = field(default_factory=list)
    max_connections: Optional[int] = None  # override global per-user limit

    @classmethod
    def from_dict(cls, username: str, d: dict) -> "User":
        return cls(
            username=username,
            salt_hex=d["salt"],
            hash_hex=d["hash"],
            iterations=int(d.get("iterations", 200_000)),
            enabled=bool(d.get("enabled", True)),
            vpn_ip=d.get("vpn_ip"),
            allowed_subnets=list(d.get("allowed_subnets", ["0.0.0.0/0"])),
            bandwidth_kbps=int(d.get("bandwidth_kbps", 0)),
            client_cn=d.get("client_cn"),
            groups=list(d.get("groups", [])),
            max_connections=d.get("max_connections"),
        )

    def verify(self, password: str) -> bool:
        if not self.enabled:
            return False
        return verify_password(password, self.salt_hex, self.hash_hex, self.iterations)

    def to_dict(self) -> dict:
        return {
            "salt": self.salt_hex,
            "hash": self.hash_hex,
            "iterations": self.iterations,
            "enabled": self.enabled,
            "vpn_ip": self.vpn_ip,
            "allowed_subnets": self.allowed_subnets,
            "bandwidth_kbps": self.bandwidth_kbps,
            "client_cn": self.client_cn,
            "groups": self.groups,
            "max_connections": self.max_connections,
        }
class AuthStore:
    """Loads users.json, tracks auth failures and lockouts per IP."""

    def __init__(self, users_path: str | Path, cfg: dict):
        self.path = Path(users_path)
        self.cfg = cfg
        self.security = cfg["security"]
        self.users: Dict[str, User] = {}
        self._failures: Dict[str, list[float]] = {}      # client_ip -> timestamps
        self._locked_until: Dict[str, float] = {}        # client_ip -> epoch
        self._mfile_signature: str | None = None
        self.load()

    # -- persistence --------------------------------------------------------

    def _read_raw(self) -> bytes | None:
        try:
            return self.path.read_bytes()
        except OSError:
            return None

    def _load(self, raw: bytes) -> None:
        data = json.loads(raw.decode("utf-8"))
        self.users = {
            name: User.from_dict(name, d)
            for name, d in data.get("users", {}).items()
        }
        self._mfile_signature = hashlib.sha256(raw).hexdigest()

    def load(self) -> None:
        raw = self._read_raw()
        if raw is None:
            self.users = {}
            self._mfile_signature = None
            log.warning("users file not found: %s (no users loaded)",
                        self.path)
            return
        self._load(raw)

    def maybe_reload(self) -> None:
        """Reload users.json if its content changed since the last load.

        Lets `vpn_server.py add-user` (e.g. via `docker exec`) take effect on
        a running server without a restart.  Content-hashed rather than
        mtime-based so it also works on filesystems with coarse timestamps.
        """
        raw = self._read_raw()
        if raw is None:
            if self._mfile_signature is not None:
                log.info("users.json deleted; unloading all users")
                self.users = {}
                self._mfile_signature = None
            return
        if hashlib.sha256(raw).hexdigest() == self._mfile_signature:
            return
        try:
            self._load(raw)
            log.info("users.json changed on disk; reloaded %d user(s)",
                     len(self.users))
        except ValueError:  # invalid JSON (possible concurrent write)
            log.warning("users.json not parseable; keeping existing users")

    def save(self) -> None:
        data = {"users": {name: u.to_dict() for name, u in self.users.items()}}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def get(self, username: str) -> Optional[User]:
        return self.users.get(username)

    def add_user(self, username: str, password: str, iterations: int | None = None,
                 vpn_ip: str | None = None, allowed_subnets: list[str] | None = None,
                 bandwidth_kbps: int = 0, client_cn: str | None = None) -> User:
        from .utils import hash_password

        iters = iterations or int(self.security.get("password_iterations", 200_000))
        salt, digest, iters = hash_password(password, iterations=iters)
        user = User(
            username=username,
            salt_hex=salt,
            hash_hex=digest,
            iterations=iters,
            vpn_ip=vpn_ip,
            allowed_subnets=allowed_subnets or ["0.0.0.0/0"],
            bandwidth_kbps=bandwidth_kbps,
            client_cn=client_cn,
        )
        self.users[username] = user
        self.save()
        return user

    # -- rate limiting --------------------------------------------------------

    def _is_locked(self, client_ip: str) -> Optional[float]:
        until = self._locked_until.get(client_ip, 0.0)
        if until > time.time():
            return until
        if until:
            self._locked_until.pop(client_ip, None)
        return None

    def is_blocked(self, client_ip: str) -> Optional[float]:
        """Return remaining lockout seconds if the client is blocked."""
        until = self._is_locked(client_ip)
        if until is not None:
            return max(0.0, until - time.time())
        return None

    def record_failure(self, client_ip: str) -> Optional[float]:
        now = time.time()
        window = self.security["rate_limit_window_seconds"]
        limit = self.security["rate_limit_attempts"]
        fails = [t for t in self._failures.get(client_ip, []) if now - t < window]
        fails.append(now)
        self._failures[client_ip] = fails
        if len(fails) >= limit:
            lockout = self.security["lockout_seconds"]
            self._locked_until[client_ip] = now + lockout
            self._failures.pop(client_ip, None)
            return lockout
        return None

    def clear_failures(self, client_ip: str) -> None:
        self._failures.pop(client_ip, None)
        self._locked_until.pop(client_ip, None)

    # -- authentication ------------------------------------------------------

    def authenticate(self, username: str, password: str | None,
                     cert_cn: str | None, client_ip: str) -> tuple[bool, str]:
        """Attempt login; returns (ok, reason)."""
        self.maybe_reload()  # pick up users added/removed since last load
        lock = self.is_blocked(client_ip)
        if lock:
            return False, f"too many attempts, try again in {int(lock)}s"

        user = self.get(username)
        mode = self.security["auth_mode"]
        ok = False

        if user is None:
            ok = False
        elif mode in ("password", "both") and password is not None:
            ok = user.verify(password)
        elif mode in ("client_cert", "both") and cert_cn is not None:
            ok = user.client_cn == cert_cn
        else:
            ok = False

        if not ok:
            self.record_failure(client_ip)
            return False, "invalid username or password"

        self.clear_failures(client_ip)
        return True, "authenticated"


def default_auth_mode(cfg: dict) -> str:
    return cfg["security"].get("auth_mode", "password")