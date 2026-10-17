"""SSL VPN client: connects over TLS, authenticates and bridges a TUN."""

from __future__ import annotations

import asyncio
import logging
import os
import ssl
import time
from typing import Any, Dict, Optional

from . import PROTOCOL_VERSION, __version__
from .protocol import (
    TYPE_AUTH, TYPE_AUTH_FAIL, TYPE_AUTH_OK, TYPE_DATA, TYPE_DISCONNECT,
    TYPE_ERROR, TYPE_HELLO, TYPE_HELLO_ACK, TYPE_PING, TYPE_PONG,
    ProtocolError, pack_json, pack_message, read_message, unpack_json,
)
from .tun import TunDevice, TunError

log = logging.getLogger("sslvpn.client")


class SSLVPNClient:
    """Connects to an SSL VPN server and bridges a local TUN device."""

    def __init__(self, config: dict, username: str, password: str,
                 tun_mock: bool = False):
        self.cfg = config
        self.srv = config["server"]
        self.net = config["network"]
        self.username = username
        self.password = password
        self.tun_mock = tun_mock
        self.tun: Optional[TunDevice] = None
        self.session: Optional[dict] = None
        self.bytes_rx = 0
        self.bytes_tx = 0
        self._running = False
        self._connected_at: Optional[float] = None

    def build_tls_context(self, verify: bool = True,
                          client_cert: Optional[str] = None,
                          client_key: Optional[str] = None) -> ssl.SSLContext:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        min_ver = getattr(ssl.TLSVersion, self.srv.get("tls_min_version", "TLSv1_2"),
                          ssl.TLSVersion.TLSv1_2)
        ctx.minimum_version = min_ver
        if verify:
            ca = os.path.join(self.cfg.get("base_dir", "."), self.srv["ca_file"])
            ctx.load_verify_locations(cafile=ca)
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.check_hostname = False  # IP-based servers / custom SANs
        else:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        if client_cert and client_key:
            ctx.load_cert_chain(
                os.path.join(self.cfg.get("base_dir", "."), client_cert),
                os.path.join(self.cfg.get("base_dir", "."), client_key))
        cipher = self.srv.get("cipher_suite")
        if cipher:
            ctx.set_ciphers(cipher)
        return ctx
    # -- lifecycle -----------------------------------------------------------

    async def connect(self) -> dict:
        """Establish TLS, handshake and authenticate. Returns the session info."""
        ctx = self.build_tls_context(verify=True)
        host = self.srv["host"]
        port = self.srv["port"]
        reader, writer = await asyncio.open_connection(host, port, ssl=ctx)
        tls_ver = writer.get_extra_info("ssl_object").version()
        log.info("TLS established with %s:%s (%s)", host, port, tls_ver)

        # HELLO
        writer.write(pack_json(TYPE_HELLO, {
            "version": PROTOCOL_VERSION,
            "client_name": f"sslvpn-client-{__version__}",
        }))
        await writer.drain()

        mtype, payload = await read_message(reader)
        if mtype != TYPE_HELLO_ACK:
            raise ConnectionError(f"unexpected server message type {mtype}")
        hello = unpack_json(payload)
        log.info("server: %s auth_modes=%s", hello.get("server_name"),
                 hello.get("auth_modes"))

        # AUTH
        writer.write(pack_json(TYPE_AUTH, {
            "username": self.username,
            "password": self.password,
        }))
        await writer.drain()

        mtype, payload = await read_message(reader)
        if mtype == TYPE_AUTH_FAIL:
            reason = unpack_json(payload).get("reason", "denied")
            writer.close()
            raise PermissionError(f"authentication failed: {reason}")
        if mtype != TYPE_AUTH_OK:
            raise ConnectionError(f"unexpected message during auth: type {mtype}")

        self.session = unpack_json(payload)
        self._conn = (reader, writer)
        self._connected_at = time.time()
        log.info("authenticated: vpn_ip=%s subnet=%s mtu=%d",
                 self.session["vpn_ip"], self.session["subnet"],
                 self.session.get("mtu", self.net["mtu"]))
        return self.session

    def setup_tun(self) -> TunDevice:
        """Create the local TUN device and configure it."""
        if self.session is None:
            raise RuntimeError("connect() must be called first")
        name = "ssl0" if self.tun_mock else f"ssl{self.username[:6]}"
        mock = self.tun_mock
        self.tun = TunDevice(name, self.session.get("mtu", self.net["mtu"]),
                             mock=mock)
        self.tun.open()
        if not mock:
            try:
                self.tun.configure(
                    self.session["vpn_ip"],
                    peer_subnet=self.session["subnet"])
            except TunError as exc:
                log.warning("local TUN config failed: %s", exc)
        return self.tun

    async def run(self) -> None:
        """Pump packets between the TLS tunnel and the local TUN device."""
        if self.session is None:
            raise RuntimeError("connect() must be called first")
        if self.tun is None:
            self.setup_tun()

        keepalive = float(self.session.get("keepalive", 30))
        reader, writer = self._conn  # set in connect()
        self._running = True

        async def tun_to_server() -> None:
            while self._running:
                packet = self.tun.read_packet()
                if packet is None:
                    await asyncio.sleep(0.005)
                    continue
                self.bytes_tx += len(packet)
                writer.write(pack_message(TYPE_DATA, packet))
                await writer.drain()

        async def server_to_tun() -> None:
            while self._running:
                try:
                    mtype, payload = await asyncio.wait_for(
                        read_message(reader), timeout=keepalive * 2)
                except asyncio.TimeoutError:
                    log.warning("no data from server for %.0fs", keepalive * 2)
                    continue
                if mtype == TYPE_DATA:
                    self.bytes_rx += len(payload)
                    self.tun.write_packet(payload)
                elif mtype == TYPE_PING:
                    writer.write(pack_message(TYPE_PONG))
                    await writer.drain()
                elif mtype == TYPE_PONG:
                    pass
                elif mtype == TYPE_DISCONNECT:
                    reason = unpack_json(payload).get("reason", "server closed")
                    log.info("server disconnected: %s", reason)
                    break
                else:
                    log.warning("unknown message type %d", mtype)

        t1 = asyncio.create_task(tun_to_server())
        t2 = asyncio.create_task(server_to_tun())
        done, pending = await asyncio.wait(
            {t1, t2}, return_when=asyncio.FIRST_COMPLETED)
        self._running = False
        for task in pending:
            task.cancel()

    async def disconnect(self) -> None:
        self._running = False
        if self.tun:
            self.tun.close()
        log.info("client disconnected (rx=%d tx=%d)", self.bytes_rx, self.bytes_tx)