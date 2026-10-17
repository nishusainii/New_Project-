#!/usr/bin/env python3
"""SSL VPN Web Management Portal & REST API Server.

Pure Python standard library implementation (http.server, json, secrets, subprocess).
Provides a modern Web GUI on port 8080 for VPN authentication, monitoring,
user management, and log inspection.
"""

from __future__ import annotations

import argparse
import http.server
import json
import logging
import os
import secrets
import ssl
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from sslvpn.auth import AuthStore
from sslvpn.utils import load_config

CONFIG_PATH = BASE_DIR / "config" / "server_config.json"
USERS_PATH = BASE_DIR / "config" / "users.json"
CERTS_DIR = BASE_DIR / "certs"
WEB_DIR = BASE_DIR / "web"

log = logging.getLogger("sslvpn.web_gui")

# In-memory session store: token -> {"username": str, "created_at": float}
ACTIVE_SESSIONS: dict[str, dict] = {}
SESSION_TTL = 86400  # 24 hours

_STORE: AuthStore | None = None

def get_store() -> AuthStore:
    global _STORE
    if _STORE is None:
        cfg = load_config(CONFIG_PATH)
        _STORE = AuthStore(USERS_PATH, cfg)
    _STORE.maybe_reload()
    return _STORE


def get_container_status() -> dict:
    """Query docker for sslvpn-server status and health."""
    try:
        cmd = ["docker", "inspect", "--format", "{{json .State}}", "sslvpn-server"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            state = json.loads(res.stdout)
            health = state.get("Health", {}).get("Status", "unknown")
            return {
                "running": state.get("Running", False),
                "status": state.get("Status", "unknown"),
                "health": health,
                "started_at": state.get("StartedAt", "")
            }
    except Exception:
        pass
    return {"running": False, "status": "offline", "health": "unknown", "started_at": ""}


def get_container_logs(lines: int = 60) -> str:
    """Retrieve tail of container logs."""
    try:
        cmd = ["docker", "logs", "--tail", str(lines), "sslvpn-server"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        return (res.stdout or "") + (res.stderr or "")
    except Exception as exc:
        return f"Unable to fetch logs: {exc}"


class WebPortalHandler(http.server.BaseHTTPRequestHandler):
    server_version = "SSLVPN-WebGUI/1.0.0"

    def log_message(self, format, *args):
        log.info("%s - %s", self.address_string(), format % args)

    # ----------------------------------------------------
    # Helpers & Security Headers (VAPT Hardening)
    # ----------------------------------------------------
    def _add_security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-XSS-Protection", "1; mode=block")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com; img-src 'self' data:;")

    def send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._add_security_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = 400):
        self.send_json({"error": message}, status=status)

    def read_json_body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                return {}
            data = self.rfile.read(length)
            return json.loads(data.decode("utf-8"))
        except Exception:
            return None

    def get_auth_token(self) -> str | None:
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
        # Fallback to Cookie
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            if "sslvpn_token=" in part:
                return part.split("sslvpn_token=")[1].strip()
        return None

    def authenticate_request(self) -> str | None:
        token = self.get_auth_token()
        if not token or token not in ACTIVE_SESSIONS:
            return None
        sess = ACTIVE_SESSIONS[token]
        if time.time() - sess["created_at"] > SESSION_TTL:
            del ACTIVE_SESSIONS[token]
            return None
        return sess["username"]

    # ----------------------------------------------------
    # Static Files
    # ----------------------------------------------------
    def serve_file(self, path: Path, content_type: str):
        if not path.exists() or not path.is_file():
            self.send_response(404)
            self._add_security_headers()
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self._add_security_headers()
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    # ----------------------------------------------------
    # GET Handlers
    # ----------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        # Static assets
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        elif path == "/" or path == "/index.html":
            return self.serve_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
        elif path == "/static/style.css":
            return self.serve_file(WEB_DIR / "style.css", "text/css; charset=utf-8")
        elif path == "/static/app.js":
            return self.serve_file(WEB_DIR / "app.js", "application/javascript; charset=utf-8")

        # API: Session Check
        if path == "/api/session":
            user = self.authenticate_request()
            if user:
                return self.send_json({"authenticated": True, "username": user})
            return self.send_json({"authenticated": False}, status=401)

        # Protected API routes
        user = self.authenticate_request()
        if not user:
            return self.send_error_json("Unauthorized. Please log in.", status=401)

        if path == "/api/status":
            cfg = load_config(CONFIG_PATH)
            container_state = get_container_status()
            store = get_store()
            return self.send_json({
                "server": cfg.get("server", {}),
                "network": cfg.get("network", {}),
                "session": cfg.get("session", {}),
                "security": cfg.get("security", {}),
                "tun_mock": cfg.get("tun_mock", True),
                "container": container_state,
                "users_count": len(store.users)
            })

        elif path == "/api/users":
            store = get_store()
            # Return safe representation without hashes/salts
            safe_users = {}
            for name, u in store.users.items():
                safe_users[name] = {
                    "username": name,
                    "enabled": u.enabled,
                    "vpn_ip": u.vpn_ip,
                    "allowed_subnets": u.allowed_subnets,
                    "bandwidth_kbps": u.bandwidth_kbps,
                    "client_cn": u.client_cn
                }
            return self.send_json({"users": safe_users})

        elif path == "/api/logs":
            logs = get_container_logs(lines=80)
            return self.send_json({"logs": logs})

        self.send_error_json("Endpoint not found", status=404)

    # ----------------------------------------------------
    # POST Handlers
    # ----------------------------------------------------
    def do_POST(self):
        url = urlparse(self.path)
        path = url.path
        body = self.read_json_body()
        if body is None:
            return self.send_error_json("Invalid JSON payload", status=400)

        # Login
        if path == "/api/login":
            username = body.get("username", "").strip()
            password = body.get("password", "")

            if not username or not password:
                return self.send_error_json("Username and password are required")

            store = get_store()
            client_ip = self.client_address[0]
            ok, reason = store.authenticate(username, password, None, client_ip)
            if not ok:
                if "too many attempts" in reason:
                    return self.send_error_json(reason, status=429)
                return self.send_error_json(reason or "Invalid username or password", status=401)

            token = secrets.token_hex(32)
            ACTIVE_SESSIONS[token] = {
                "username": username,
                "created_at": time.time()
            }
            return self.send_json({
                "token": token,
                "username": username,
                "message": "Login successful"
            })

        # Logout
        if path == "/api/logout":
            token = self.get_auth_token()
            if token and token in ACTIVE_SESSIONS:
                del ACTIVE_SESSIONS[token]
            return self.send_json({"ok": True, "message": "Logged out"})

        # Protected POST routes
        user = self.authenticate_request()
        if not user:
            return self.send_error_json("Unauthorized", status=401)

        # Add User
        if path == "/api/users":
            new_username = body.get("username", "").strip()
            new_password = body.get("password", "")
            vpn_ip = body.get("vpn_ip", "").strip() or None
            subnets = body.get("allowed_subnets", ["0.0.0.0/0"])
            bw_raw = body.get("bandwidth_kbps", 0)

            # Strict VAPT Input Validation
            import re
            import ipaddress

            if not re.match(r'^[a-zA-Z0-9_\-\.]{3,32}$', new_username):
                return self.send_error_json("Username must be 3-32 alphanumeric characters, dot, underscore, or dash")

            if not new_password or len(new_password) < 6:
                return self.send_error_json("Password must be at least 6 characters")

            if vpn_ip:
                try:
                    ipaddress.IPv4Address(vpn_ip)
                except ValueError:
                    return self.send_error_json("Invalid IPv4 address format for vpn_ip")

            if not isinstance(subnets, list):
                return self.send_error_json("allowed_subnets must be a list of CIDR strings")

            validated_subnets = []
            for s in subnets:
                s_str = str(s).strip()
                try:
                    ipaddress.ip_network(s_str, strict=False)
                    validated_subnets.append(s_str)
                except ValueError:
                    return self.send_error_json(f"Invalid CIDR subnet format: {s}")

            try:
                bw = int(bw_raw)
                if bw < 0:
                    raise ValueError
            except (ValueError, TypeError):
                return self.send_error_json("Bandwidth limit must be a positive integer or 0")

            store = get_store()
            store.add_user(
                username=new_username,
                password=new_password,
                vpn_ip=vpn_ip,
                allowed_subnets=validated_subnets,
                bandwidth_kbps=bw
            )
            return self.send_json({"ok": True, "username": new_username})

        # Toggle User Enable/Disable
        elif path == "/api/users/toggle":
            target_user = body.get("username", "").strip()
            if target_user == "admin":
                return self.send_error_json("Cannot disable the default admin account", status=403)

            store = get_store()
            u = store.get(target_user)
            if not u:
                return self.send_error_json("User not found", status=404)

            u.enabled = not u.enabled
            store.save()

            # If user was disabled, revoke any active sessions
            if not u.enabled:
                for tok in list(ACTIVE_SESSIONS.keys()):
                    if ACTIVE_SESSIONS[tok].get("username") == target_user:
                        del ACTIVE_SESSIONS[tok]

            return self.send_json({"ok": True, "username": target_user, "enabled": u.enabled})

        self.send_error_json("Endpoint not found", status=404)

    # ----------------------------------------------------
    # DELETE Handlers
    # ----------------------------------------------------
    def do_DELETE(self):
        url = urlparse(self.path)
        path = url.path

        user = self.authenticate_request()
        if not user:
            return self.send_error_json("Unauthorized", status=401)

        if path.startswith("/api/users/"):
            target_user = path[len("/api/users/"):].strip()
            if target_user == "admin":
                return self.send_error_json("Default admin account cannot be deleted", status=403)

            store = get_store()
            if target_user in store.users:
                del store.users[target_user]
                store.save()

                # Revoke active sessions for deleted user
                for tok in list(ACTIVE_SESSIONS.keys()):
                    if ACTIVE_SESSIONS[tok].get("username") == target_user:
                        del ACTIVE_SESSIONS[tok]

                return self.send_json({"ok": True, "deleted": target_user})
            return self.send_error_json("User not found", status=404)

        self.send_error_json("Endpoint not found", status=404)


def run_server(host: str, port: int, use_ssl: bool = False, cert_file: str | None = None, key_file: str | None = None):
    server_address = (host, port)
    httpd = http.server.ThreadingHTTPServer(server_address, WebPortalHandler)
    proto = "http"

    if use_ssl:
        cert_path = Path(cert_file) if cert_file else CERTS_DIR / "server.crt"
        key_path = Path(key_file) if key_file else CERTS_DIR / "server.key"
        if cert_path.exists() and key_path.exists():
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=str(cert_path), keyfile=str(key_path))
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
            proto = "https"
            log.info("SSL enabled using certificate: %s", cert_path)
        else:
            log.warning("SSL requested but cert/key not found: %s, %s. Falling back to HTTP.", cert_path, key_path)

    log.info("SSL VPN Web Portal listening on %s://%s:%d", proto, host, port)
    print(f"SSL VPN Web Portal running at {proto}://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Web Portal...")
    finally:
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="SSL VPN Web Management Portal")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080, help="Bind port (default: 8080)")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS using server certificate")
    parser.add_argument("--cert", default=None, help="Path to TLS certificate file")
    parser.add_argument("--key", default=None, help="Path to TLS private key file")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    run_server(args.host, args.port, use_ssl=args.ssl, cert_file=args.cert, key_file=args.key)


if __name__ == "__main__":
    main()
