"""Unit + integration tests for the custom SSL VPN (stdlib unittest only).

Run with:  python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from sslvpn import PROTOCOL_VERSION  # noqa: E402
from sslvpn.auth import AuthStore  # noqa: E402
from sslvpn.client import SSLVPNClient  # noqa: E402
from sslvpn.protocol import (  # noqa: E402
    TYPE_AUTH, TYPE_AUTH_FAIL, TYPE_AUTH_OK, TYPE_DATA, TYPE_DISCONNECT,
    TYPE_ERROR, TYPE_HELLO, TYPE_HELLO_ACK, TYPE_PING, TYPE_PONG,
    ProtocolError, pack_json, pack_message, read_message,
)
from sslvpn.server import SSLVPNServer, TokenBucket  # noqa: E402
from sslvpn.tun import parse_dest_ip  # noqa: E402
from sslvpn.utils import (  # noqa: E402
    hash_password, int_to_ip, ip_in_subnet, ip_to_int, load_config,
    subnet_allows, verify_password,
)

PROJECT = BASE
DEFAULT_CONFIG = PROJECT / "config" / "server_config.json"


def make_ipv4(src: str, dst: str, payload: bytes = b"\x00" * 4) -> bytes:
    """Build a minimal valid-looking IPv4 packet with given src/dst."""
    total = 20 + len(payload)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,            # version 4, IHL 5
        0,               # DSCP/ECN
        total,
        0x1234,          # id
        0x4000,          # flags/frag
        64,              # TTL
        17,              # UDP
        0,               # checksum (0 ok for our parser)
        bytes(map(int, src.split("."))),
        bytes(map(int, dst.split("."))),
    )
    return header + payload


# ---------------------------------------------------------------------------
# Pure unit tests
# ---------------------------------------------------------------------------

class TestUtils(unittest.TestCase):
    def test_password_hash_roundtrip(self):
        salt, digest, iters = hash_password("s3cret", iterations=1000)
        self.assertTrue(verify_password("s3cret", salt, digest, 1000))
        self.assertFalse(verify_password("wrong", salt, digest, 1000))

    def test_ip_helpers(self):
        self.assertEqual(ip_to_int("10.8.0.1"), 0x0A080001)
        self.assertEqual(int_to_ip(0x0A080001), "10.8.0.1")
        self.assertTrue(ip_in_subnet("10.8.0.42", "10.8.0.0/24"))
        self.assertFalse(ip_in_subnet("10.9.0.1", "10.8.0.0/24"))
        self.assertTrue(subnet_allows(["0.0.0.0/0"], "8.8.8.8"))
        self.assertTrue(subnet_allows(["10.0.0.0/8"], "10.1.2.3"))
        self.assertFalse(subnet_allows(["10.0.0.0/8"], "192.168.1.1"))

    def test_config_defaults(self):
        cfg = load_config(DEFAULT_CONFIG)
        self.assertEqual(cfg["network"]["vpn_subnet"], "10.8.0.0/24")
        self.assertTrue(cfg["tun_enabled"])


class TestProtocol(unittest.TestCase):
    def test_pack_roundtrip(self):
        async def go():
            reader = asyncio.StreamReader()
            writer = asyncio.StreamWriter  # unused
            payload = pack_json(TYPE_HELLO, {"version": 1, "client_name": "x"})
            reader.feed_data(payload)
            reader.feed_eof()
            mtype, body = await read_message(reader)
            self.assertEqual(mtype, TYPE_HELLO)
            self.assertEqual(json.loads(body)["version"], 1)

        asyncio.run(go())

    def test_pack_oversized(self):
        with self.assertRaises(ProtocolError):
            pack_message(TYPE_DATA, b"\x00" * 100_000)

    def test_parse_dest_ip(self):
        pkt = make_ipv4("10.8.0.10", "10.8.0.11")
        self.assertEqual(parse_dest_ip(pkt), "10.8.0.11")


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.users_file = Path(self.tmp) / "users.json"
        cfg = load_config(DEFAULT_CONFIG)
        cfg["security"]["password_iterations"] = 1000
        self.cfg = cfg
        self.store = AuthStore(self.users_file, cfg)
        self.store.add_user("alice", "wonder", iterations=1000)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_success_and_failure(self):
        ok, reason = self.store.authenticate("alice", "wonder", None, "1.2.3.4")
        self.assertTrue(ok)
        ok, reason = self.store.authenticate("alice", "bad", None, "1.2.3.4")
        self.assertFalse(ok)

    def test_unknown_user(self):
        ok, reason = self.store.authenticate("nobody", "x", None, "5.6.7.8")
        self.assertFalse(ok)

    def test_rate_limit_lockout(self):
        ip = "9.9.9.9"
        for _ in range(5):
            self.store.authenticate("alice", "wrong", None, ip)
        remaining = self.store.is_blocked(ip)
        self.assertIsNotNone(remaining)
        ok, reason = self.store.authenticate("alice", "wonder", None, ip)
        self.assertFalse(ok)  # blocked even with correct password

    def test_client_cert_mode(self):
        self.cfg["security"]["auth_mode"] = "client_cert"
        self.store = AuthStore(self.users_file, self.cfg)
        # existing alice has no client_cn -> fail
        ok, _ = self.store.authenticate("alice", "wonder", "vpn-user", "1.2.3.4")
        self.assertFalse(ok)
        self.store.add_user("bob", "pw", iterations=1000, client_cn="vpn-user")
        ok, _ = self.store.authenticate("bob", "pw", "vpn-user", "1.2.3.4")
        self.assertTrue(ok)
        ok, _ = self.store.authenticate("bob", "pw", "other-cn", "1.2.3.4")
        self.assertFalse(ok)

    def test_users_reload_on_change(self):
        """users.json edits by an outside process take effect without restart."""
        ok, _ = self.store.authenticate("carol", "pw", None, "7.7.7.7")
        self.assertFalse(ok)
        # simulate `vpn_server.py add-user carol` in another process/container exec
        other = AuthStore(self.users_file, self.cfg)
        other.add_user("carol", "pw", iterations=1000)
        # authenticate() reloads the changed file via maybe_reload()
        ok, _ = self.store.authenticate("carol", "pw", None, "8.8.8.8")
        self.assertTrue(ok)


class TestTokenBucket(unittest.TestCase):
    def test_limits_rate(self):
        bucket = TokenBucket(1000)  # 1 KB/s
        first = bucket.consume(500)
        self.assertEqual(first, 0.0)
        second = bucket.consume(800)  # needs more than remaining
# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

class RunningServer:
    """Context manager that runs an SSL VPN server (mock TUN) on an ephemeral port."""

    def __init__(self, cfg_overrides: dict | None = None, users: dict | None = None):
        self.tmp = tempfile.mkdtemp()
        self.users_file = Path(self.tmp) / "users.json"
        cfg = load_config(DEFAULT_CONFIG)
        cfg["base_dir"] = str(PROJECT)
        cfg["server"]["host"] = "127.0.0.1"
        cfg["server"]["port"] = 0
        cfg["session"]["keepalive_interval_seconds"] = 5
        cfg["session"]["handshake_timeout_seconds"] = 10
        if cfg_overrides:
            cfg = json.loads(json.dumps(cfg))  # deep copy
            for k, v in cfg_overrides.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        self.cfg = cfg
        self.users = users or {}
        self.port: int | None = None
        self.server: SSLVPNServer | None = None
        self._store: AuthStore | None = None

    async def __aenter__(self):
        self._store = AuthStore(self.users_file, self.cfg)
        for name, kwargs in self.users.items():
            self._store.add_user(name, **kwargs)
        self._store.save()
        self.server = SSLVPNServer(self.cfg, str(self.users_file), tun_mock=True)
        await self.server.start()
        self.port = self.server._server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *exc):
        await self.server.shutdown()
        shutil.rmtree(self.tmp)


def client_cfg(port: int) -> dict:
    cfg = load_config(DEFAULT_CONFIG)
    cfg["base_dir"] = str(PROJECT)
    cfg["server"]["host"] = "127.0.0.1"
    cfg["server"]["port"] = port
    return cfg


async def raw_connect(port: int, username: str, password: str,
                      client_cert=None, client_key=None):
    """Open TLS, HELLO/AUTH and return (mtype, payload, reader, writer)."""
    client = SSLVPNClient(client_cfg(port), username, password, tun_mock=True)
    ctx = client.build_tls_context(verify=True,
                                   client_cert=client_cert,
                                   client_key=client_key)
    reader, writer = await asyncio.open_connection("127.0.0.1", port, ssl=ctx)
    writer.write(pack_json(TYPE_HELLO, {"version": PROTOCOL_VERSION,
                                        "client_name": "test"}))
    await writer.drain()
    mtype, payload = await read_message(reader)
    assert mtype == TYPE_HELLO_ACK, f"expected HELLO_ACK, got {mtype}"
    writer.write(pack_json(TYPE_AUTH, {"username": username,
                                       "password": password}))
    await writer.drain()
    mtype, payload = await read_message(reader)
    return mtype, payload, reader, writer


async def read_data(reader, timeout=5.0):
    """Read messages until a DATA frame arrives (skip pings)."""
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        mtype, payload = await asyncio.wait_for(read_message(reader),
                                                timeout=timeout)
        if mtype == TYPE_DATA:
            return payload
        if mtype == TYPE_DISCONNECT:
            return None
    return None


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------

class TestEndToEnd(unittest.TestCase):
    def test_auth_success_assigns_ip(self):
        async def go():
            async with RunningServer(users={
                "admin": {"password": "admin123", "iterations": 1000},
            }) as srv:
                mtype, payload, reader, writer = await raw_connect(
                    srv.port, "admin", "admin123")
                self.assertEqual(mtype, TYPE_AUTH_OK)
                info = json.loads(payload)
                self.assertEqual(info["vpn_ip"], "10.8.0.10")
                self.assertEqual(info["server_ip"], "10.8.0.1")
                writer.write(pack_json(TYPE_DISCONNECT, {"reason": "test"}))
                await writer.drain()
                writer.close()

        asyncio.run(go())

    def test_auth_bad_password_rejected(self):
        async def go():
            async with RunningServer(users={
                "admin": {"password": "admin123", "iterations": 1000},
            }) as srv:
                mtype, payload, reader, writer = await raw_connect(
                    srv.port, "admin", "wrongpass")
                self.assertEqual(mtype, TYPE_AUTH_FAIL)

        asyncio.run(go())

    def test_two_clients_data_plane(self):
        async def go():
            async with RunningServer(users={
                "admin": {"password": "admin123", "iterations": 1000},
            }) as srv:
                mtype_a, _, ra, wa = await raw_connect(srv.port, "admin", "admin123")
                self.assertEqual(mtype_a, TYPE_AUTH_OK)
                mtype_b, _, rb, wb = await raw_connect(srv.port, "admin", "admin123")
                self.assertEqual(mtype_b, TYPE_AUTH_OK)

                # client A -> client B (intra-VPN routing through mock TUN)
                pkt = make_ipv4("10.8.0.10", "10.8.0.11", b"ping-payload")
                wa.write(pack_message(TYPE_DATA, pkt))
                await wa.drain()

                got = await read_data(rb)
                self.assertIsNotNone(got, "client B never received the packet")
                self.assertEqual(got, pkt)

                wa.close()
                wb.close()

    def test_mtls_auth_mode(self):
        async def go():
            overrides = {"security": {"auth_mode": "client_cert"},
                         "server": {"require_client_cert": True}}
            async with RunningServer(overrides, users={
                "bob": {"password": "pw", "iterations": 1000,
                        "client_cn": "vpn-user"},
            }) as srv:
                # with client cert CN=vpn-user -> success
                mtype, payload, reader, writer = await raw_connect(
                    srv.port, "bob", "pw",
                    client_cert="certs/client.crt", client_key="certs/client.key")
                self.assertEqual(mtype, TYPE_AUTH_OK)
                writer.close()

                # without a client cert -> TLS handshake must fail
                with self.assertRaises(Exception):
                    await raw_connect(srv.port, "bob", "pw")

        asyncio.run(go())

    def test_fixed_vpn_ip_user(self):
        async def go():
            async with RunningServer(users={
                "fixed": {"password": "pw", "iterations": 1000,
                          "vpn_ip": "10.8.0.77"},
            }) as srv:
                mtype, payload, reader, writer = await raw_connect(
                    srv.port, "fixed", "pw")
                self.assertEqual(mtype, TYPE_AUTH_OK)
                self.assertEqual(json.loads(payload)["vpn_ip"], "10.8.0.77")
                writer.close()

        asyncio.run(go())

    def test_client_class_end_to_end(self):
        async def go():
            async with RunningServer(users={
                "admin": {"password": "admin123", "iterations": 1000},
            }) as srv:
                client = SSLVPNClient(client_cfg(srv.port), "admin", "admin123",
                                      tun_mock=True)
                info = await client.connect()
                self.assertEqual(info["vpn_ip"], "10.8.0.10")
                client.setup_tun()
                # give the server a moment to register, then disconnect
                await asyncio.sleep(0.1)
                await client.disconnect()

        asyncio.run(go())


if __name__ == "__main__":
    unittest.main(verbosity=2)