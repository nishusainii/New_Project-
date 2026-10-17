"""Wire protocol for the SSL VPN tunnel.

Framing::

    +----------------+----------------+-------------------------+
    | 4-byte length  | 1-byte type    | payload (length bytes)  |
    +----------------+----------------+-------------------------+

All multi-byte integers are big-endian.  After authentication the DATA
type carries a raw IPv4/IPv6 packet which the receiver writes to its TUN
device.

Control messages use JSON payloads:
    HELLO / HELLO_ACK / AUTH / AUTH_OK / AUTH_FAIL / DISCONNECT / PING / PONG
"""

from __future__ import annotations

import json
import struct
from typing import Any, Optional, Tuple

from . import PROTOCOL_VERSION

# Message type constants ---------------------------------------------------
TYPE_HELLO = 0x01       # client -> server : {version, client_name}
TYPE_HELLO_ACK = 0x02   # server -> client : {version, server_name, auth_modes, max_mtu}
TYPE_AUTH = 0x03        # client -> server : {username, password | cert_cn}
TYPE_AUTH_OK = 0x04     # server -> client : {vpn_ip, server_ip, subnet, mtu, dns[]}
TYPE_AUTH_FAIL = 0x05   # server -> client : {reason, retry_after?}
TYPE_DATA = 0x06        # bidirectional : raw IP packet
TYPE_PING = 0x07        # keepalive
TYPE_PONG = 0x08
TYPE_DISCONNECT = 0x09  # {reason}
TYPE_ERROR = 0x0A       # {code, message}

_HEADER = struct.Struct("!IB")  # 4-byte length + 1-byte type
HEADER_SIZE = _HEADER.size

MAX_PAYLOAD = 65_535 - HEADER_SIZE


class ProtocolError(Exception):
    """Raised on malformed or oversized frames."""


def pack_message(msg_type: int, payload: bytes = b"") -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ProtocolError(f"payload too large: {len(payload)}")
    return _HEADER.pack(len(payload), msg_type) + payload


def pack_json(msg_type: int, obj: dict) -> bytes:
    return pack_message(msg_type, json.dumps(obj, separators=(",", ":")).encode("utf-8"))


def unpack_json(payload: bytes) -> dict:
    try:
        return json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ProtocolError(f"invalid JSON payload: {exc}") from exc


async def read_message(reader, timeout: float | None = None) -> Tuple[int, bytes]:
    """Read a single framed message from an asyncio stream reader."""
    header = await _read_exact(reader, HEADER_SIZE, timeout)
    (length, msg_type) = _HEADER.unpack(header)
    if length < 0 or length > MAX_PAYLOAD:
        raise ProtocolError(f"invalid frame length: {length}")
    payload = await _read_exact(reader, length, timeout)
    return msg_type, payload


async def _read_exact(reader, n: int, timeout: float | None) -> bytes:
    if timeout is None:
        data = await reader.readexactly(n)
    else:
        data = await asyncio_wait_exact(reader, n, timeout)
    return data


async def asyncio_wait_exact(reader, n: int, timeout: float) -> bytes:
    """readexactly with a timeout (asyncio.wait_for wrapper)."""
    import asyncio

    return await asyncio.wait_for(reader.readexactly(n), timeout=timeout)


def parse_hello(payload: bytes) -> dict:
    obj = unpack_json(payload)
    if not isinstance(obj, dict):
        raise ProtocolError("HELLO payload must be an object")
    version = obj.get("version", 0)
    if int(version) != PROTOCOL_VERSION:
        raise ProtocolError(f"protocol version mismatch: {version}")
    return obj


# --------------------------------------------------------------------------
# Session identifiers for control-plane debug
# --------------------------------------------------------------------------

def peer_label(reader, writer) -> str:
    try:
        peer = writer.get_extra_info("peername")
        return f"{peer[0]}:{peer[1]}" if peer else "?"
    except Exception:
        return "?"


def current_tls_version(transport) -> Optional[str]:
    try:
        ssl_obj = transport.get_extra_info("ssl_object")
        return ssl_obj.version() if ssl_obj else None
    except Exception:
        return None