#!/usr/bin/env python3
"""SSL VPN client command-line interface.

Usage:
    python3 vpn_client.py --server HOST [--port PORT] --username USER
        [--password PW] [--mock-tun] [--timeout SECONDS]
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import logging
import sys
from pathlib import Path

from sslvpn import __version__
from sslvpn.client import SSLVPNClient
from sslvpn.utils import load_config, setup_logging

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "server_config.json"


def load_client_config(host: str, port: int) -> dict:
    cfg = load_config(CONFIG_PATH)
    cfg["base_dir"] = str(BASE_DIR)
    cfg["server"]["host"] = host
    cfg["server"]["port"] = port
    return cfg


async def run(args) -> int:
    cfg = load_client_config(args.server, args.port)
    client = SSLVPNClient(cfg, args.username, args.password, tun_mock=args.mock_tun)

    try:
        await client.connect()
        print(f"connected. your VPN IP: {client.session['vpn_ip']}")
        print(f"subnet: {client.session['subnet']}  "
              f"MTU: {client.session.get('mtu')}  "
              f"DNS: {','.join(client.session.get('dns', []))}")
        client.setup_tun()
        print("tunnel established. press Ctrl+C to disconnect ...")
        try:
            await asyncio.wait_for(client.run(), timeout=args.timeout or None)
        except asyncio.TimeoutError:
            print(f"timeout reached ({args.timeout}s), disconnecting ...")
    except (PermissionError, ConnectionError) as exc:
        logging.getLogger("sslvpn.client").error("%s", exc)
        return 1
    finally:
        await client.disconnect()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="vpn_client",
                                     description="Custom SSL VPN client")
    parser.add_argument("--server", required=True, help="VPN server host/IP")
    parser.add_argument("--port", type=int, default=None,
                        help="server port (default: from config, 443)")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", default=None)
    parser.add_argument("--mock-tun", action="store_true",
                        help="use in-memory TUN (no root required)")
    parser.add_argument("--timeout", type=float, default=None,
                        help="auto-disconnect after N seconds")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    setup_logging("DEBUG" if args.verbose else "INFO")
    if args.password is None:
        args.password = getpass.getpass(f"password for {args.username}: ")
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())