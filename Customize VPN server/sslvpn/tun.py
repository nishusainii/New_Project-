"""TUN/TAP device management.

Opens /dev/net/tun and exposes raw IP packet read/write.  Interface
configuration (IP address, routes, NAT) shells out to `ip` / `iptables`
/ `sysctl`, so it requires root.  The class degrades gracefully: with
``mock=True`` packets are simply bounced in memory (used for tests).

On Linux the control-plane (TLS, auth, protocol) never needs root; only
the data-plane kernel plumbing does.
"""

from __future__ import annotations

import fcntl
import logging
import os
import socket
import struct
import subprocess
from typing import Optional

log = logging.getLogger("sslvpn.tun")

# ioctl constants from <linux/if.h> / <linux/if_tun.h>
TUNSETIFF = 0x400454CA
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000
SIOCSIFMTU = 0x8922

TUN_DEV = "/dev/net/tun"


class TunError(RuntimeError):
    pass


class TunDevice:
    """A raw IP (layer-3) tunnel device."""

    def __init__(self, name: str = "ssl0", mtu: int = 1400, mock: bool = False):
        self.name = name
        self.mtu = mtu
        self.mock = mock
        self.fd: Optional[int] = None
        self._running = False
        if mock:
            self._mock_buf: list[bytes] = []
            log.info("TUN running in MOCK mode (in-memory only, no kernel device)")

    # -- lifecycle -----------------------------------------------------------

    def open(self) -> None:
        if self.mock:
            self._running = True
            return
        if not os.path.exists(TUN_DEV):
            raise TunError(f"{TUN_DEV} is not available (need /dev/net/tun)")
        # non-blocking: the asyncio readers poll this fd and must never block
        # the whole event loop waiting for a packet (O_NONBLOCK at open).
        self.fd = os.open(TUN_DEV, os.O_RDWR | os.O_NONBLOCK)
        try:
            ifr = struct.pack("16sH", self.name.encode()[:15], IFF_TUN | IFF_NO_PI)
            fcntl.ioctl(self.fd, TUNSETIFF, ifr)
            log.info("opened TUN device: %s (mtu=%d)", self.name, self.mtu)
        except OSError as exc:
            os.close(self.fd)
            self.fd = None
            raise TunError(f"cannot create TUN device '{self.name}': {exc}") from exc
        self._set_mtu(self.mtu)
        self._running = True

    def close(self) -> None:
        self._running = False
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        log.info("closed TUN device %s", self.name)

    def _set_mtu(self, mtu: int) -> None:
        """Set the MTU on the TUN interface.

        The kernel rejects SIOCSIFMTU on the TUN file descriptor itself
        (EINVAL); it must go through a plain socket fd with an ``ifreq``
        struct (or ``ip link set ... mtu``).  Falls back to `ip` when the
        ioctl path is not permitted.
        """
        if self.fd is None:
            return
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ifr = struct.pack("16sI", self.name.encode()[:15], mtu)
            ifr += b"\x00" * (40 - len(ifr))  # pad to sizeof(struct ifreq)
            fcntl.ioctl(sock.fileno(), SIOCSIFMTU, ifr)
            log.debug("set MTU %d on %s via SIOCSIFMTU", mtu, self.name)
            return
        except OSError:
            pass
        finally:
            if sock is not None:
                sock.close()
        # fallback: `ip link set <name> mtu <mtu>` (needs iproute2 + root)
        try:
            subprocess.run(["ip", "link", "set", self.name, "mtu", str(mtu)],
                           check=True, capture_output=True, text=True)
            log.debug("set MTU %d on %s via `ip link`", mtu, self.name)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise TunError(f"cannot set MTU on '{self.name}': {exc}") from exc

    # -- packet IO -----------------------------------------------------------

    def read_packet(self) -> Optional[bytes]:
        if not self._running:
            return None
        if self.mock:
            if self._mock_buf:
                return self._mock_buf.pop(0)
            return None
        try:
            return os.read(self.fd, self.mtu)
        except (BlockingIOError, OSError):
            return None

    def write_packet(self, packet: bytes) -> bool:
        if not self._running:
            return False
        if self.mock:
            self._mock_buf.append(packet)
            return True
        try:
            os.write(self.fd, packet)
            return True
        except OSError as exc:
            log.warning("TUN write failed: %s", exc)
            return False
    # -- kernel plumbing (requires root) --------------------------------------

    def _run(self, *cmd: str, check: bool = True) -> subprocess.CompletedProcess:
        try:
            proc = subprocess.run(list(cmd), capture_output=True, text=True)
        except OSError as exc:  # e.g. `ip`/`iptables` not installed
            raise TunError(f"required tool not found: {cmd[0]!r} ({exc})") from exc
        if check and proc.returncode != 0:
            raise TunError(f"command failed ({' '.join(cmd)}): {proc.stderr.strip()}")
        return proc

    def configure(self, server_ip: str, peer_subnet: str = "10.8.0.0/24") -> None:
        """Assign an address, bring the interface up and add a route."""
        if self.mock:
            log.info("mock configure(%s/%s) skipped", server_ip, peer_subnet)
            return
        prefix = peer_subnet.split("/")[1] if "/" in peer_subnet else "24"
        self._run("ip", "addr", "add", f"{server_ip}/{prefix}", "dev", self.name)
        self._run("ip", "link", "set", self.name, "up")
        # the kernel usually auto-creates the connected route on "addr add";
        # `replace` is idempotent so the route is correct either way
        self._run("ip", "route", "replace", peer_subnet, "dev", self.name,
                  "src", server_ip)
        log.info("configured %s: addr=%s/%s route=%s",
                 self.name, server_ip, prefix, peer_subnet)

    def unconfigure(self, server_ip: str, peer_subnet: str = "10.8.0.0/24") -> None:
        if self.mock:
            return
        try:
            prefix = peer_subnet.split("/")[1] if "/" in peer_subnet else "24"
            self._run("ip", "addr", "del", f"{server_ip}/{prefix}", "dev",
                      self.name, check=False)
            self._run("ip", "link", "set", self.name, "down", check=False)
        except TunError:
            pass

    @staticmethod
    def detect_wan_interface() -> Optional[str]:
        """Find the interface holding the default route."""
        try:
            out = subprocess.run(
                ["ip", "route", "show", "default"], capture_output=True, text=True
            ).stdout
            for line in out.splitlines():
                parts = line.split()
                if "dev" in parts:
                    return parts[parts.index("dev") + 1]
        except Exception:
            pass
        return None

    def setup_nat(self, wan_interface: str, vpn_subnet: str) -> None:
        if self.mock:
            log.info("mock NAT setup skipped")
            return
        if not wan_interface:
            raise TunError("cannot enable NAT: no WAN interface configured")
        if self._run("iptables", "-t", "nat", "-C", "POSTROUTING",
                     "-s", vpn_subnet, "-o", wan_interface, "-j", "MASQUERADE",
                     check=False).returncode != 0:
            self._run("iptables", "-t", "nat", "-A", "POSTROUTING",
                      "-s", vpn_subnet, "-o", wan_interface, "-j", "MASQUERADE")
        if self._run("iptables", "-C", "FORWARD", "-i", "ssl+", "-j", "ACCEPT",
                     check=False).returncode != 0:
            self._run("iptables", "-A", "FORWARD", "-i", "ssl+", "-j", "ACCEPT")
            self._run("iptables", "-A", "FORWARD", "-o", "ssl+", "-m", "state",
                      "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT")
        log.info("NAT enabled for %s -> %s", vpn_subnet, wan_interface)

    def teardown_nat(self, wan_interface: str, vpn_subnet: str) -> None:
        if self.mock:
            return
        try:
            self._run("iptables", "-t", "nat", "-D", "POSTROUTING",
                      "-s", vpn_subnet, "-o", wan_interface, "-j", "MASQUERADE",
                      check=False)
            self._run("iptables", "-D", "FORWARD", "-i", "ssl+", "-j", "ACCEPT",
                      check=False)
            self._run("iptables", "-D", "FORWARD", "-o", "ssl+", "-m", "state",
                      "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT", check=False)
        except TunError:
            pass

    @staticmethod
    def enable_ip_forward() -> None:
        for path in ("/proc/sys/net/ipv4/ip_forward",
                     "/proc/sys/net/ipv6/conf/all/forwarding"):
            try:
                with open(path, "w") as fh:
                    fh.write("1")
            except OSError:
                continue
        log.info("enabled IP forwarding")

    @staticmethod
    def disable_ip_forward() -> None:
        try:
            with open("/proc/sys/net/ipv4/ip_forward", "w") as fh:
                fh.write("0")
        except OSError:
            pass


def ip_version(packet: bytes) -> int:
    """Return 4 or 6 based on the IP version nibble; 0 if not IP."""
    if not packet:
        return 0
    return (packet[0] >> 4) & 0x0F


def parse_dest_ip(packet: bytes) -> Optional[str]:
    """Extract the destination IP address from an IP packet header."""
    try:
        ver = ip_version(packet)
        if ver == 4:
            return socket.inet_ntop(socket.AF_INET, packet[16:20])
        if ver == 6:
            return socket.inet_ntop(socket.AF_INET6, packet[24:40])
    except (ValueError, IndexError):
        return None
    return None