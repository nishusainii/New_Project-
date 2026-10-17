# WireGuard Control Center 🛡️

A lightweight, high-performance web management control center for **WireGuard VPN** and **NFTables Firewall & ACLs**, built with **FastAPI**, **SQLAlchemy**, and a modern SOC dashboard.

---

## Key Features

- **⚡ Zero-Downtime Atomic Reload (`wg syncconf`)**: Executes `wg syncconf wg0 <(wg-quick strip wg0)` with zero packet loss, preserving active client tunnels and established cryptographic sessions.
- **🎨 Dedicated Core UI**: Independent focused pages (`/`, `/peers`, `/firewall`, `/server`) with responsive dark/light/OLED themes, glowing status pulses, and glassmorphism styling.
- **👥 Peer Client Management**: Fast client provisioning, QR code modal, `.conf` downloads, full vs split tunnel configurations, and device tagging.
- **🛡️ NFTables Firewall & ACL Management**: Real-time nftables inspection, custom rule enforcement, IP/Port ACL rules, input/forward policy toggles, NAT masquerading, and one-click emergency killswitch.
- **🌓 Multi-Theme Support**: Dark SOC, Light Slate, and Midnight OLED themes toggled instantly from the dashboard top navigation.
- **🔒 Secure & Air-Gapped Ready**: Argon2id authentication, encrypted private key storage, session-based auth with CSRF protection, and zero external runtime dependencies.

---

## Architecture Overview

```
                        ┌─────────────────────────────────────────┐
                        │          Web UI & Mobile Admin          │
                        │    (Tailwind CSS + Pure JS + QR)       │
                        └──────────────────┬──────────────────────┘
                                           │  REST / Web Forms
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│ FastAPI Application Service                                                    │
│                                                                                 │
│  ┌─────────────────┐   ┌─────────────────┐   ┌───────────────────────────────┐ │
│  │   Auth & RBAC   │   │  IPAM Engine    │   │  WireGuard Engine             │ │
│  │ (Argon2 / CSRF) │   │ (Subnet Alloc)  │   │  (Curve25519 / Syncconf)      │ │
│  └─────────────────┘   └─────────────────┘   └───────────────┬───────────────┘ │
│                                                              │                 │
│  ┌──────────────────────────────────────────────┐            │                 │
│  │ SQLite Database (Encrypted Credentials)     │            │                 │
│  └──────────────────────────────────────────────┘            │                 │
└──────────────────────────────────────────────────────────────┼──────────────────┘
                                                               │
                                         ┌─────────────────────┴─────────────────────┐
                                         │ wg syncconf / Netlink / Kernel Interface   │
                                         │            (wg0: 51820/UDP)               │
                                         └───────────────────────────────────────────┘
```

---

## Quickstart with Docker

1. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env to set your ADMIN_PASSWORD and WG_DEFAULT_ENDPOINT (e.g. your public IP)
   ```

2. **Build and Launch**:
   ```bash
   docker compose up -d --build
   ```

3. **Access Dashboard**:
   - URL: `http://localhost:8000`
   - Default Username: `admin`
   - Default Password: `adminpassword123` (or whatever you set in `.env`)
   - Interactive API Docs: `http://localhost:8000/docs`

---

## REST API Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/status` | Current server status, interface details, and global telemetry |
| `GET` | `/api/peers` | List all peers with live handshake and transfer stats |
| `POST` | `/api/peers` | Add a new peer (auto-generates keys & assigns next IP) |
| `GET` | `/api/peers/{id}/config` | Export client WireGuard configuration text |
| `GET` | `/api/peers/{id}/download` | Download `.conf` file directly |
| `POST` | `/api/peers/{id}/toggle` | Enable or disable a peer dynamically |
| `DELETE`| `/api/peers/{id}` | Permanently delete a peer and sync interface |
| `PUT` | `/api/server` | Update server interface settings |
| `GET` | `/api/firewall/status` | Active NFT status, global policies, and live ruleset |
| `GET` | `/api/firewall/preview` | Preview compiled candidate NFTables configuration |
| `POST` | `/api/firewall/validate` | Dry-run syntax check (`nft -c -f`) for candidate configs |
| `POST` | `/api/firewall/apply` | Safely compile and apply NFTables configuration to kernel |
| `POST` | `/api/firewall/policy` | Update core policies (isolation, NAT masquerade, DNS) |
| `GET` | `/api/firewall/acls` | List all WireGuard ACL rules |
| `POST` | `/api/firewall/acls` | Create new WireGuard ACL rule |
| `POST` | `/api/firewall/acls/{id}/toggle` | Enable or disable a WireGuard ACL |
| `DELETE`| `/api/firewall/acls/{id}` | Delete a WireGuard ACL |
| `POST` | `/api/firewall/custom-rules` | Create custom NFTables rule statement |
| `DELETE`| `/api/firewall/custom-rules/{id}` | Delete custom NFTables rule |

---

## Execution Modes

WireGate supports three execution modes via `WG_EXECUTION_MODE` in `.env`:

1. **`direct` (Default)**: Directly executes WireGuard commands (`wg syncconf wg0`) inside the container or host.
2. **`dry-run`**: Validates configuration syntax, renders draft configs, and simulates telemetry without modifying any network interface.
3. **`agent`**: Dispatches HMAC-signed configuration updates to a secure host agent over `http://host.docker.internal:9081`.
