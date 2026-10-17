"""SSL VPN server: asyncio + TLS, custom framed protocol, TUN bridge."""

from __future__ import annotations

import asyncio
import logging
import os
import ssl
import time
from typing import Dict, Optional

from . import PROTOCOL_VERSION, __version__
from .auth import AuthStore, User
from .protocol import (
    TYPE_AUTH, TYPE_AUTH_FAIL, TYPE_AUTH_OK, TYPE_DATA, TYPE_DISCONNECT,
    TYPE_ERROR, TYPE_HELLO, TYPE_HELLO_ACK, TYPE_PING, TYPE_PONG,
    ProtocolError, pack_json, pack_message, parse_hello, read_message,
    unpack_json,
)
from .tun import TunDevice, TunError, parse_dest_ip
from .utils import int_to_ip, ip_to_int, subnet_allows

log = logging.getLogger("sslvpn.server")


class TokenBucket:
    """Simple token bucket used for per-user bandwidth throttling."""

    def __init__(self, rate_bps: float):
        self.rate = max(rate_bps, 1.0)
        self.capacity = self.rate  # one second of burst
        self.tokens = self.capacity
        self.updated = time.monotonic()

    def consume(self, n: int) -> float:
        now = time.monotonic()
        self.tokens = min(self.capacity,
                          self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens >= n:
            self.tokens -= n
            return 0.0
        deficit = n - self.tokens
        self.tokens = 0.0
        return deficit / self.rate


class ClientSession:
    """State for one authenticated VPN client."""

    def __init__(self, reader, writer, peer_ip: str, vpn_ip: str,
                 user: User, server: "SSLVPNServer"):
        self.reader = reader
        self.writer = writer
        self.peer_ip = peer_ip
        self.vpn_ip = vpn_ip
        self.user = user
        self.server = server
        self.connected_at = time.time()
        self.last_activity = time.time()
        self.bytes_rx = 0
        self.bytes_tx = 0
        self.pings_sent = 0
        self.pongs_received = 0
        self.bucket: Optional[TokenBucket] = None
        if user.bandwidth_kbps and user.bandwidth_kbps > 0:
            self.bucket = TokenBucket(user.bandwidth_kbps * 125)  # kbps -> B/s
        self.alive = True

    async def send(self, msg_type: int, payload: bytes = b"") -> None:
        if self.writer.is_closing():
            return
        try:
            self.writer.write(pack_message(msg_type, payload))
            await self.writer.drain()
        except (ConnectionError, OSError):
            self.alive = False

    def to_status(self) -> dict:
        uptime = int(time.time() - self.connected_at)
        return {
            "username": self.user.username,
            "vpn_ip": self.vpn_ip,
            "peer": self.peer_ip,
            "connected_for_s": uptime,
            "bytes_rx": self.bytes_rx,
            "bytes_tx": self.bytes_tx,
            "idle_s": int(time.time() - self.last_activity),
        }


class SSLVPNServer:
    """Custom SSL VPN server.

    Args:
        config:      merged configuration dictionary (see utils.load_config)
        users_path:  path to users.json
        tun_mock:    force in-memory TUN (no root needed; for testing)
    """

    def __init__(self, config: dict, users_path: str, tun_mock: bool = False):
        self.cfg = config
        self.net = config["network"]
        self.sess_cfg = config["session"]
        self.sec = config["security"]
        self.auth = AuthStore(users_path, config)

        mock = tun_mock or not bool(config.get("tun_enabled", True))
        self.tun = TunDevice(self.net["tun_name"], self.net["mtu"], mock=mock)

        self.sessions: Dict[str, ClientSession] = {}   # vpn_ip -> session
        self.used_ips = set(self._fixed_ips())
        self._pool = self._build_ip_pool()
        self._server: Optional[asyncio.AbstractServer] = None
        self._running = False
        self._tun_task: Optional[asyncio.Task] = None
        self._started_at: Optional[float] = None

    # -- IP pool -------------------------------------------------------------

    def _fixed_ips(self) -> list[str]:
        return [u.vpn_ip for u in self.auth.users.values() if u.vpn_ip]

    def _build_ip_pool(self) -> list[str]:
        start = ip_to_int(self.net["ip_pool_start"])
        end = ip_to_int(self.net["ip_pool_end"])
        if start > end:
            raise ValueError("ip_pool_start must be <= ip_pool_end")
        pool = [int_to_ip(i) for i in range(start, end + 1)]
        return [ip for ip in pool if ip not in self.used_ips]

    def _alloc_ip(self) -> Optional[str]:
        for ip in self._pool:
            if ip not in self.used_ips:
                return ip
        return None

    # -- TLS context -----------------------------------------------------------

    def build_tls_context(self) -> ssl.SSLContext:
        srv_cfg = self.cfg["server"]
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        min_ver = getattr(ssl.TLSVersion, srv_cfg["tls_min_version"],
                          ssl.TLSVersion.TLSv1_2)
        ctx.minimum_version = min_ver
        ctx.maximum_version = ssl.TLSVersion.MAXIMUM_SUPPORTED

        cert = os.path.join(self.cfg.get("base_dir", "."), srv_cfg["cert_file"])
        key = os.path.join(self.cfg.get("base_dir", "."), srv_cfg["key_file"])
        ctx.load_cert_chain(cert, key)

        auth_mode = self.sec["auth_mode"]
        need_mtls = (srv_cfg.get("require_client_cert", False)
                     or auth_mode in ("client_cert", "both"))
        if need_mtls:
            ca = os.path.join(self.cfg.get("base_dir", "."), srv_cfg["ca_file"])
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.load_verify_locations(cafile=ca)
            log.info("mTLS enabled: client certificates required")

        dh = srv_cfg.get("dh_params_file")
        if dh:
            ctx.load_dh_params(os.path.join(self.cfg.get("base_dir", "."), dh))

        cipher = srv_cfg.get("cipher_suite")
        if cipher:
            ctx.set_ciphers(cipher)
        log.info("TLS context ready (min=%s)", srv_cfg["tls_min_version"])
        return ctx
    # -- lifecycle ------------------------------------------------------------

    async def start(self) -> None:
        srv_cfg = self.cfg["server"]
        self._running = True
        self._started_at = time.time()

        # TUN setup (real or mock)
        try:
            self.tun.open()
            if not self.tun.mock:
                self.tun.configure(self.net["server_ip"], self.net["vpn_subnet"])
                if self.net.get("enable_ip_forward", True):
                    self.tun.enable_ip_forward()
                if self.net.get("enable_nat", True):
                    wan = (self.net.get("wan_interface")
                           or TunDevice.detect_wan_interface())
                    self.tun.setup_nat(wan, self.net["vpn_subnet"])
        except TunError as exc:
            log.warning("TUN setup failed (%s); falling back to mock TUN", exc)
            self.tun.close()
            self.tun = TunDevice(self.net["tun_name"], self.net["mtu"], mock=True)
            self.tun.open()

        self._tun_task = asyncio.create_task(self._tun_reader_loop(),
                                             name="tun-reader")
        ctx = self.build_tls_context()
        self._server = await asyncio.start_server(
            self._on_client, srv_cfg["host"], srv_cfg["port"], ssl=ctx)
        sock = self._server.sockets[0] if self._server.sockets else None
        addr = sock.getsockname() if sock else (srv_cfg["host"], srv_cfg["port"])
        log.info("SSL VPN server %s listening on %s:%s (tls=%s, tun=%s%s)",
                 __version__, addr[0], addr[1], srv_cfg["tls_min_version"],
                 self.tun.name, ", MOCK" if self.tun.mock else "")

    async def shutdown(self) -> None:
        if not self._running:
            return
        log.info("shutting down ...")
        self._running = False
        for sess in list(self.sessions.values()):
            await sess.send(TYPE_DISCONNECT,
                            pack_json(TYPE_DISCONNECT,
                                      {"reason": "server shutdown"}))
        if self._server:
            self._server.close()
            await self._server.wait_closed()
        if self._tun_task:
            self._tun_task.cancel()
            try:
                await self._tun_task
            except (asyncio.CancelledError, Exception):
                pass
        try:
            self.tun.close()
            if not self.tun.mock:
                self.tun.unconfigure(self.net["server_ip"], self.net["vpn_subnet"])
                if self.net.get("enable_nat", True):
                    wan = (self.net.get("wan_interface")
                           or TunDevice.detect_wan_interface())
                    self.tun.teardown_nat(wan, self.net["vpn_subnet"])
        except TunError:
            pass
        log.info("shutdown complete")

    # -- TUN data plane --------------------------------------------------------

    async def _tun_reader_loop(self) -> None:
        """Read packets from the TUN device and fan them out to clients."""
        while self._running:
            packet = self.tun.read_packet()
            if packet is None:
                await asyncio.sleep(0.005)
                continue
            dest = parse_dest_ip(packet)
            if not dest:
                continue
            target = self.sessions.get(dest)
            if target is not None:
                await target.send(TYPE_DATA, packet)
                target.bytes_tx += len(packet)
            else:
                # dest is outside the VPN; kernel routes/NATs it (real TUN).
                log.debug("tun->%s (external, via kernel)", dest)
    # -- connection handling ----------------------------------------------------

    async def _on_client(self, reader, writer) -> None:
        peer = writer.get_extra_info("peername")
        peer_ip = peer[0] if peer else "?"
        log.info("new TLS connection from %s", peer_ip)
        session: Optional[ClientSession] = None
        try:
            session = await self._handshake(reader, writer, peer_ip)
            if session is None:
                return
            self.sessions[session.vpn_ip] = session
            log.info("client %s logged in as '%s' -> vpn %s",
                     peer_ip, session.user.username, session.vpn_ip)
            await self._session_loop(session)
        except (ConnectionError, ssl.SSLError, asyncio.IncompleteReadError,
                ProtocolError) as exc:
            log.info("connection %s ended: %s", peer_ip, exc)
        finally:
            if session is not None:
                self.sessions.pop(session.vpn_ip, None)
                self.used_ips.discard(session.vpn_ip)
                log.info("client %s (%s) disconnected",
                         session.vpn_ip, session.user.username)
            try:
                writer.close()
            except Exception:
                pass

    @staticmethod
    def _peer_cn(writer) -> Optional[str]:
        try:
            cert = writer.get_extra_info("peercert")
        except Exception:
            return None
        if not cert:
            return None
        for rdn in cert.get("subject", ()):
            for key, value in rdn:
                if key == "commonName":
                    return value
        return None

    def _user_connection_count(self, username: str) -> int:
        return sum(1 for s in self.sessions.values()
                   if s.user.username == username)

    async def _send_json(self, writer, msg_type: int, obj: dict) -> None:
        writer.write(pack_json(msg_type, obj))
        await writer.drain()

    async def _handshake(self, reader, writer,
                         peer_ip: str) -> Optional[ClientSession]:
        timeout = self.sess_cfg["handshake_timeout_seconds"]

        # 1) HELLO ---------------------------------------------------------
        try:
            mtype, payload = await read_message(reader, timeout)
        except asyncio.TimeoutError:
            await self._send_json(writer, TYPE_ERROR,
                                  {"code": "timeout", "message": "hello timeout"})
            return None
        if mtype != TYPE_HELLO:
            await self._send_json(writer, TYPE_ERROR,
                                  {"code": "bad_hello", "message": "expected HELLO"})
            return None
        try:
            parse_hello(payload)
        except ProtocolError as exc:
            await self._send_json(writer, TYPE_ERROR,
                                  {"code": "bad_hello", "message": str(exc)})
            return None

        await self._send_json(writer, TYPE_HELLO_ACK, {
            "version": PROTOCOL_VERSION,
            "server_name": f"sslvpn-{__version__}",
            "auth_modes": [self.sec["auth_mode"]],
            "max_mtu": self.net["mtu"],
            "server_ip": self.net["server_ip"],
            "vpn_subnet": self.net["vpn_subnet"],
        })

        # 2) AUTH ----------------------------------------------------------
        try:
            mtype, payload = await read_message(reader, timeout)
        except asyncio.TimeoutError:
            return None
        if mtype != TYPE_AUTH:
            await self._send_json(writer, TYPE_ERROR,
                                  {"code": "bad_auth", "message": "expected AUTH"})
            return None
        auth = unpack_json(payload)
        username = str(auth.get("username", ""))
        password = auth.get("password")
        cert_cn = self._peer_cn(writer)

        ok, reason = self.auth.authenticate(username, password, cert_cn, peer_ip)
        if not ok:
            await self._send_json(writer, TYPE_AUTH_FAIL, {"reason": reason})
            log.warning("auth failed for '%s' from %s: %s",
                        username, peer_ip, reason)
            return None

        user = self.auth.get(username)
        if user is None:
            await self._send_json(writer, TYPE_AUTH_FAIL, {"reason": "unknown user"})
            return None

        # limits -----------------------------------------------------------
        per_user = (user.max_connections
                    or self.sess_cfg["max_connections_per_user"])
        if self._user_connection_count(username) >= per_user:
            await self._send_json(writer, TYPE_AUTH_FAIL,
                                  {"reason": "connection limit reached for user"})
            return None
        if len(self.sessions) >= self.sess_cfg["max_clients"]:
            await self._send_json(writer, TYPE_AUTH_FAIL,
                                  {"reason": "server is full"})
            return None

        # IP assignment ----------------------------------------------------
        vpn_ip = user.vpn_ip or self._alloc_ip()
        if vpn_ip is None or (vpn_ip in self.used_ips and vpn_ip != user.vpn_ip):
            await self._send_json(writer, TYPE_AUTH_FAIL,
                                  {"reason": "no IP available"})
            return None
        self.used_ips.add(vpn_ip)

        # 3) AUTH_OK ---------------------------------------------------------
        await self._send_json(writer, TYPE_AUTH_OK, {
            "vpn_ip": vpn_ip,
            "server_ip": self.net["server_ip"],
            "subnet": self.net["vpn_subnet"],
            "mtu": self.net["mtu"],
            "dns": self.net["dns_servers"],
            "keepalive": self.sess_cfg["keepalive_interval_seconds"],
            "auth_mode": self.sec["auth_mode"],
        })
        return ClientSession(reader, writer, peer_ip, vpn_ip, user, self)

    # -- data plane routing ---------------------------------------------------

    async def _route_data(self, session: ClientSession, packet: bytes) -> None:
        """Route a DATA frame from a client: ACL check, throttle, write to TUN."""
        session.bytes_rx += len(packet)
        dest = parse_dest_ip(packet)
        if dest and session.user.allowed_subnets:
            if not subnet_allows(session.user.allowed_subnets, dest):
                log.debug("ACL: %s dropped packet to %s",
                          session.user.username, dest)
                return
        if session.bucket is not None:
            delay = session.bucket.consume(len(packet))
            if delay:
                await asyncio.sleep(min(delay, 1.0))
        self.tun.write_packet(packet)

    async def _session_loop(self, session: ClientSession) -> None:
        """Serve one client: read frames until it leaves or times out."""
        keepalive = self.sess_cfg["keepalive_interval_seconds"]
        idle = self.sess_cfg["idle_timeout_seconds"]
        while session.alive and self._running:
            try:
                mtype, payload = await asyncio.wait_for(
                    read_message(session.reader), timeout=keepalive)
            except asyncio.TimeoutError:
                now = time.time()
                if now - session.last_activity > idle:
                    log.info("idle timeout for %s (%s)",
                             session.vpn_ip, session.user.username)
                    break
                session.pings_sent += 1
                await session.send(TYPE_PING)
                continue
            except (asyncio.IncompleteReadError, ProtocolError,
                    ConnectionError, OSError) as exc:
                log.debug("session %s read error: %s", session.vpn_ip, exc)
                break
            session.last_activity = time.time()
            if mtype == TYPE_DATA:
                await self._route_data(session, payload)
            elif mtype == TYPE_PING:
                await session.send(TYPE_PONG)
            elif mtype == TYPE_PONG:
                session.pongs_received += 1
            elif mtype == TYPE_DISCONNECT:
                break
            elif mtype == TYPE_ERROR:
                log.warning("client %s sent ERROR: %s",
                            session.vpn_ip, payload[:200])
            else:
                log.warning("unexpected message type %d from %s",
                            mtype, session.vpn_ip)
        session.alive = False
        await session.send(TYPE_DISCONNECT,
                           pack_json(TYPE_DISCONNECT, {"reason": "bye"}))

    # -- status -----------------------------------------------------------------

    def status(self) -> dict:
        uptime = int(time.time() - self._started_at) if self._started_at else 0
        return {
            "version": __version__,
            "uptime_s": uptime,
            "clients": len(self.sessions),
            "max_clients": self.sess_cfg["max_clients"],
            "tun_device": self.tun.name,
            "tun_mock": self.tun.mock,
            "sessions": [s.to_status() for s in self.sessions.values()],
        }