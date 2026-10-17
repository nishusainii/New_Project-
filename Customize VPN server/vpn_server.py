#!/usr/bin/env python3
"""SSL VPN server command-line interface.

Usage:
    python3 vpn_server.py init-config [--dir .]
    python3 vpn_server.py add-user USERNAME [--password PW] [--vpn-ip X]
        [--subnet 10.0.0.0/8] [--bandwidth-kbps N] [--cert-cn CN]
        [--iterations N]
    python3 vpn_server.py list-users
    python3 vpn_server.py start [--port PORT] [--host HOST] [--mock-tun]
    python3 vpn_server.py status
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import logging
import os
import signal
import sys
from pathlib import Path

from sslvpn import __version__
from sslvpn.auth import AuthStore
from sslvpn.server import SSLVPNServer
from sslvpn.utils import load_config, setup_logging, save_config, DEFAULTS

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config" / "server_config.json"
USERS_PATH = BASE_DIR / "config" / "users.json"


def load() -> dict:
    cfg = load_config(CONFIG_PATH)
    cfg["base_dir"] = str(BASE_DIR)
    return cfg


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_init_config(args) -> None:
    cfg = json.loads(json.dumps(DEFAULTS))
    save_config(CONFIG_PATH, cfg)
    print(f"wrote default config: {CONFIG_PATH}")
    print("edit it, then run: python3 vpn_server.py add-user <username>")
    print("and: python3 scripts/generate_certs.sh")


def cmd_add_user(args) -> None:
    cfg = load()
    store = AuthStore(USERS_PATH, cfg)
    password = args.password or getpass.getpass(f"password for {args.username}: ")
    if args.password is None:
        confirm = getpass.getpass("confirm password: ")
        if password != confirm:
            sys.exit("passwords do not match")
    user = store.add_user(
        args.username,
        password,
        iterations=args.iterations,
        vpn_ip=args.vpn_ip,
        allowed_subnets=args.subnet,
        bandwidth_kbps=args.bandwidth_kbps,
        client_cn=args.cert_cn,
    )
    print(f"user '{user.username}' added"
          + (f" (fixed IP {user.vpn_ip})" if user.vpn_ip else "")
          + (f" (client cert CN={user.client_cn})" if user.client_cn else ""))


def cmd_list_users(args) -> None:
    cfg = load()
    store = AuthStore(USERS_PATH, cfg)
    for name, user in sorted(store.users.items()):
        print(f"{name:20s} vpn_ip={user.vpn_ip or 'auto':12s} "
              f"subnets={','.join(user.allowed_subnets)} "
              f"bw={user.bandwidth_kbps}kbps "
              f"cert_cn={user.client_cn or '-'} "
              f"{'enabled' if user.enabled else 'DISABLED'}")
async def _run_server(args, cfg: dict) -> None:
    server = SSLVPNServer(cfg, str(USERS_PATH), tun_mock=args.mock_tun)
    await server.start()

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _sigint() -> None:
        print("\nreceived SIGINT, shutting down ...")
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _sigint)
        except NotImplementedError:
            pass

    async def _status_loop() -> None:
        while not stop.is_set():
            await asyncio.sleep(10)
            st = server.status()
            log.info("status: clients=%d/%d tun=%s%s", st["clients"],
                     st["max_clients"], st["tun_device"],
                     " (mock)" if st["tun_mock"] else "")

    task = asyncio.create_task(_status_loop())
    await stop.wait()
    await server.shutdown()
    task.cancel()


def cmd_start(args) -> None:
    cfg = load()
    if args.host:
        cfg["server"]["host"] = args.host
    if args.port:
        cfg["server"]["port"] = args.port
    if args.tun_enabled is not None:
        cfg["tun_enabled"] = args.tun_enabled
    log = setup_logging(cfg["logging"]["level"], cfg["logging"]["file"])
    log.info("SSL VPN server v%s starting", __version__)
    asyncio.run(_run_server(args, cfg))


def cmd_status(args) -> None:
    pid_file = BASE_DIR / "vpn_server.pid"
    print(f"pid file: {pid_file}")
    if pid_file.exists():
        print(f"pid: {pid_file.read_text().strip()}")
    else:
        print("server not running (no pid file)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="vpn_server",
                                     description="Custom SSL VPN server")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-config", help="write default config file")
    p_init.set_defaults(func=cmd_init_config)

    p_add = sub.add_parser("add-user", help="add a VPN user account")
    p_add.add_argument("username")
    p_add.add_argument("--password", default=None)
    p_add.add_argument("--vpn-ip", default=None)
    p_add.add_argument("--subnet", action="append", default=None,
                       help="allowed destination subnet (repeatable)")
    p_add.add_argument("--bandwidth-kbps", type=int, default=0)
    p_add.add_argument("--cert-cn", default=None,
                       help="expected TLS client certificate CN (mTLS)")
    p_add.add_argument("--iterations", type=int, default=None)
    p_add.set_defaults(func=cmd_add_user)

    p_list = sub.add_parser("list-users", help="list configured users")
    p_list.set_defaults(func=cmd_list_users)

    p_start = sub.add_parser("start", help="start the VPN server")
    p_start.add_argument("--host", default=None)
    p_start.add_argument("--port", type=int, default=None)
    p_start.add_argument("--mock-tun", action="store_true",
                         help="use in-memory TUN (no root required)")
    p_start.add_argument("--tun-enabled", dest="tun_enabled",
                         type=lambda s: s.lower() in ("1", "true", "yes"),
                         default=None, help="override tun_enabled config")
    p_start.set_defaults(func=cmd_start)

    p_status = sub.add_parser("status", help="show server status")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())