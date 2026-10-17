# Custom SSL VPN (pure Python stdlib)

A self-contained SSL VPN server and client built **only on the Python standard
library** (`ssl`, `asyncio`, `socket`, `fcntl`). It establishes a TLS 1.2/1.3
tunnel, authenticates clients with a password and/or client certificates, and
bridges a TUN device so remote clients can reach the VPN subnet and the
internet through the server (real TUN mode).

> **No third-party dependencies.** Works on any Python 3.10+ interpreter.

## Features

- **TLS 1.2 / 1.3 tunnel** (`ssl`) with configurable minimum version and ciphers
- **Custom framed protocol** `[4-byte big-endian length][1-byte type][payload]`
  with JSON control messages (`HELLO/AUTH/DATA/PING/DISCONNECT`)
- **Authentication**: PBKDF2-HMAC-SHA256 password hashing, optional **mTLS**
  (client certificate CN mapping), or both
- **Per-user ACL subnets** (allow-list of destination subnets per user)
- **Bandwidth throttling** per user (token bucket)
- **Rate limiting & lockout** per client IP
- **Fixed or auto-assigned VPN IPs** (from a configurable pool)
- **Keepalive pings & idle timeout**
- **Mock TUN mode** for testing without root privileges
- **Real TUN mode** with IP forwarding + NAT via `ip`/`iptables` (root only)
- **CLI tools**: `vpn_server.py`, `vpn_client.py`
- **Test suite**: `tests/test_sslvpn.py` (17 tests, `unittest` only)

## Requirements

- Python **3.10+** (uses `X | None` type unions and modern `asyncio`)
- For **mock mode**: nothing else
- For **real TUN mode**: Linux with TUN support and root access
- `openssl` CLI (only needed to (re)generate certificates)

## Quick start (mock mode, no root)

```bash
cd testing

# 1. Generate certificates (CA, server, client) if not already present
bash scripts/generate_certs.sh

# 2. (Optional) create a user
python3 vpn_server.py add-user admin --password admin123

# 3. Start the server in mock-TUN mode
python3 vpn_server.py start --host 127.0.0.1 --port 8443 --mock-tun

# 4. In another terminal, connect with the CLI client
python3 vpn_client.py --server 127.0.0.1 --port 8443 \
    --username admin --password admin123 --mock-tun --timeout 5
```

You should see the client authenticate and print its assigned VPN IP
(e.g. `10.8.0.10`). Mock mode runs the whole tunnel in memory, so no
root or kernel TUN device is needed.

## Server CLI (`vpn_server.py`)

```
python3 vpn_server.py init-config              # write default config to config/
python3 vpn_server.py add-user USER [options]  # add a VPN user
python3 vpn_server.py list-users               # list configured users
python3 vpn_server.py start [options]          # start the VPN server
python3 vpn_server.py status                   # show pid file / server state
```

### `add-user` options

| Option               | Meaning                                              |
|----------------------|------------------------------------------------------|
| `--password PW`      | password (prompted if omitted)                       |
| `--vpn-ip X.X.X.X`   | fixed VPN IP (default: auto-assign from pool)        |
| `--subnet CIDR`      | allowed destination subnet (repeatable)              |
| `--bandwidth-kbps N` | bandwidth cap in kbit/s (0 = unlimited)              |
| `--cert-cn CN`       | expected client-certificate CN (for mTLS)            |
| `--iterations N`     | PBKDF2 iterations (default from config)              |

### `start` options

| Option          | Meaning                                        |
|-----------------|------------------------------------------------|
| `--host HOST`   | bind address (default `0.0.0.0`)               |
| `--port PORT`   | bind port (default 443; use >1024 if not root) |
| `--mock-tun`    | in-memory TUN, no root needed                  |
| `--tun-enabled` | override the `tun_enabled` config flag         |

Example:

```bash
python3 vpn_server.py add-user alice --vpn-ip 10.8.0.50 --subnet 10.0.0.0/8
python3 vpn_server.py start --port 4433 --mock-tun
```

## Client CLI (`vpn_client.py`)

```
python3 vpn_client.py --server HOST --username USER \
    [--port PORT] [--password PW] [--mock-tun] [--timeout SECONDS] [--verbose]
```

- `--server` and `--username` are required; the password is prompted if omitted.
- `--mock-tun` uses an in-memory TUN (no root).
- `--timeout N` auto-disconnects after N seconds (useful for scripts/tests).
- `--verbose` enables debug logging.

## Real TUN mode (root, Linux)

To bridge an actual kernel TUN device and NAT client traffic you need root:

```bash
# 1. Prepare the host (IP forwarding + NAT), run once per boot
#    Auto-detect the WAN interface, or pass it explicitly:
sudo bash scripts/setup_network.sh            # or: sudo bash scripts/setup_network.sh eth0

# 2. Start the server WITHOUT --mock-tun (TUN device is created by the server)
sudo python3 vpn_server.py start --host 0.0.0.0 --port 443

# 3. On the client, run WITHOUT --mock-tun (also needs root to create a TUN)
sudo python3 vpn_client.py --server YOUR_SERVER_IP --port 443 \
    --username admin --password admin123
```

Notes:

- `setup_network.sh` enables IP forwarding and adds an iptables `MASQUERADE`
  rule for the VPN subnet. The server also attempts these automatically
  (`enable_ip_forward` / `enable_nat` in the config) if it has permissions.
- Real TUN configuration happens inside `sslvpn/tun.py` via the `ip` command.
- If the TUN setup fails (e.g. no root), the server logs a warning and falls
  back to mock mode automatically.

## Docker deployment

A `Dockerfile`, `docker-compose.yml` and an `entrypoint`/config helper live in
the repo, so the server runs as a container (the image is pure stdlib — no
`pip` packages are installed at runtime).

### Build

```bash
docker build -t innspark/sslvpn:1.0.0 .
```

The image is `python:3.11-slim` + `iproute2`/`iptables`/`openssl`. If the
build host cannot reach the Debian mirrors (offline CI), the build still
succeeds and logs `WARNING: apt install failed ...` — the image then remains
usable in mock mode only.

### Two runtime modes

| Mode     | Command                                   | Privileges required           |
|----------|-------------------------------------------|-------------------------------|
| Mock TUN | `docker compose up -d`                    | none                          |
| Real TUN | `docker compose --profile real-tun up -d` | `/dev/net/tun` + `NET_ADMIN`  |

Both services use host networking, i.e. the TLS listener binds directly on the
host interface (this is also what this project host supports — its Docker
bridge cannot program NAT port-publishing rules). On hosts with a healthy
Docker bridge, switch the `sslvpn` service to `ports:` publishing instead —
see the comments in `docker-compose.yml`.

### First start

```bash
docker compose up -d
docker compose ps            # STATUS should end with (healthy) after ~5 s
docker compose logs -f sslvpn
```

The entrypoint (`docker/entrypoint.sh`) idempotently prepares the container:

- writes the default `config/server_config.json` if missing
- creates an empty `config/users.json` if missing
- generates the certificates into `certs/` if absent
  (`SSLVPN_SERVER_NAME` env sets the server CN, default `vpn.local`)
- seeds the initial `admin` account from `SSLVPN_ADMIN_PASSWORD`
  (only when `users.json` contains no users)
- applies every `SSLVPN_*` env var onto the config and starts the server

### Manage users (no restart needed)

```bash
# add / re-create a user — the running server hashes the users.json content
# and reloads it automatically on the next login attempt
docker compose exec sslvpn python3 vpn_server.py add-user bob --password hunter2
docker compose exec sslvpn python3 vpn_server.py list-users
docker compose exec sslvpn python3 vpn_server.py status
```

User edits made directly in `config/users.json` also take effect immediately
(no restart): the server reloads the file whenever it changes on disk.

### Configuration from environment

Any server setting can be overridden with an `SSLVPN_*` environment variable
at container start; `docker/apply_env.py` merges them into
`config/server_config.json` before the server starts:

```
SSLVPN_HOST, SSLVPN_PORT, SSLVPN_TLS_MIN_VERSION, SSLVPN_REQUIRE_CLIENT_CERT,
SSLVPN_VPN_SUBNET, SSLVPN_SERVER_IP, SSLVPN_IP_POOL_START, SSLVPN_IP_POOL_END,
SSLVPN_MTU, SSLVPN_TUN_NAME, SSLVPN_WAN_INTERFACE, SSLVPN_ENABLE_NAT,
SSLVPN_ENABLE_IP_FORWARD, SSLVPN_DNS_SERVERS, SSLVPN_MAX_CLIENTS,
SSLVPN_IDLE_TIMEOUT, SSLVPN_KEEPALIVE_INTERVAL, SSLVPN_MAX_CONNECTIONS_PER_USER,
SSLVPN_AUTH_MODE, SSLVPN_PASSWORD_ITERATIONS, SSLVPN_LOG_LEVEL, SSLVPN_LOG_FILE,
SSLVPN_TUN_ENABLED    # full list in docker/apply_env.py
```

### Client inside a container

```bash
docker run --rm --network host --entrypoint python3 innspark/sslvpn:1.0.0 \
    vpn_client.py --server 127.0.0.1 --port 443 \
    --username bob --password hunter2 --mock-tun --timeout 5
```

### Real TUN mode in Docker

```bash
docker compose --profile real-tun up -d
docker compose logs -f sslvpn-real
```

Needs the same host prerequisites as the section above (`/dev/net/tun`,
IP forwarding, WAN interface). With host networking the `ssl0` device and the
NAT rules live in the host network namespace; on a graceful
`docker compose down` they are removed for you (the server runs
`unconfigure`/`teardown_nat` during shutdown).

### Healthcheck

The image ships a `HEALTHCHECK` that completes a real TLS handshake against
the listener; `docker compose ps` shows `(healthy)` when clients can connect.

## Certificates

`scripts/generate_certs.sh` creates the whole hierarchy under `certs/`:

| File          | Purpose                                   |
|---------------|-------------------------------------------|
| `ca.crt`      | self-signed CA certificate                |
| `ca.key`      | CA private key (keep safe)                |
| `server.crt`  | server TLS certificate (CN = vpn.local)   |
| `server.key`  | server private key                        |
| `client.crt`  | client certificate (CN = vpn-user, mTLS)  |
| `client.key`  | client private key                        |

```bash
# Regenerate with a custom server hostname
bash scripts/generate_certs.sh myvpn.example.com
```

## Configuration (`config/server_config.json`)

All settings have built-in defaults (`sslvpn/utils.py`) merged with the JSON
file. Key sections:

- `server` — bind `host`/`port`, `tls_min_version`, `cipher_suite`,
  cert/key/CA paths, `require_client_cert`, `dh_params_file`
- `network` — `vpn_subnet`, `server_ip`, `ip_pool_start`/`ip_pool_end`, `mtu`,
  `tun_name`, `wan_interface`, `enable_nat`, `enable_ip_forward`, `dns_servers`
- `session` — `max_clients`, `idle_timeout_seconds`,
  `keepalive_interval_seconds`, `max_connections_per_user`,
  `handshake_timeout_seconds`
- `security` — `auth_mode` (`password` | `client_cert` | `both`),
  `password_iterations`, rate-limit / lockout settings,
  `token_bucket_interval_seconds`

Users live in `config/users.json` (managed via `add-user` / `list-users`).

## Wire protocol

```
+----------------+----------------+-------------------------+
| 4-byte length  | 1-byte type    | payload (length bytes)  |
+----------------+----------------+-------------------------+
```

All integers are big-endian. After authentication, `TYPE_DATA` (0x06) carries a
raw IPv4/IPv6 packet; control messages use JSON payloads:

| Type           | Value | Direction              | Payload                              |
|----------------|-------|------------------------|--------------------------------------|
| `HELLO`        | 0x01  | client → server         | `{version, client_name}`             |
| `HELLO_ACK`    | 0x02  | server → client         | `{version, server_name, auth_modes}` |
| `AUTH`         | 0x03  | client → server         | `{username, password}`               |
| `AUTH_OK`      | 0x04  | server → client         | `{vpn_ip, server_ip, subnet, mtu, dns}` |
| `AUTH_FAIL`    | 0x05  | server → client         | `{reason}`                           |
| `DATA`         | 0x06  | both                    | raw IP packet                        |
| `PING` / `PONG`| 0x07/0x08 | both                | keepalive                            |
| `DISCONNECT`   | 0x09  | both                    | `{reason}`                           |
| `ERROR`        | 0x0A  | both                    | `{code, message}`                    |

## Project layout

```
testing/
├── sslvpn/
│   ├── __init__.py   # version + protocol version
│   ├── utils.py      # config, logging, PBKDF2, IP math
│   ├── protocol.py   # framing + message constants
│   ├── auth.py       # user store, rate limiting, mTLS CN mapping
│   ├── tun.py        # TUN device (mock + real), ip/iptables helpers
│   ├── server.py     # SSLVPNServer (TLS, handshake, data plane)
│   └── client.py     # SSLVPNClient (TLS, handshake, TUN bridge)
├── vpn_server.py     # server CLI
├── vpn_client.py     # client CLI
├── config/           # server_config.json, users.json
├── certs/            # generated CA/server/client certificates
├── scripts/          # generate_certs.sh, setup_network.sh
├── tests/            # test_sslvpn.py (18 unittest tests)
├── Dockerfile        # python:3.11-slim image (mock + real TUN)
├── docker-compose.yml# two profiles: mock TUN and real TUN + NAT
├── .dockerignore     # keep the build context small
└── docker/           # entrypoint.sh, apply_env.py, healthcheck.sh
```

## Running the tests

```bash
cd testing
python3 -m unittest discover -s tests -v
```

## Security notes

- Passwords are stored as **PBKDF2-HMAC-SHA256** hashes with random salts.
- Client IPs are **rate-limited and locked out** after repeated failures.
- Per-user **ACL subnets** restrict which destinations a client may reach.
- Enable `auth_mode: "client_cert"` (or `"both"`) to require client
  certificates in addition to (or instead of) passwords.
- The server certificate is verified by default (`verify=True` in the client).
  For a production deployment, generate certificates with proper hostnames and
  keep `ca.key` and `server.key` private.
- This project is an educational/self-contained implementation. For critical
  deployments, prefer audited solutions (OpenVPN, WireGuard, IPsec).