# WireGuard Enterprise - Technical Architecture Specification

## 1. Executive Overview & Architecture Philosophy

**WireGuard Enterprise** is an enterprise-grade, air-gapped VPN gateway and policy management platform. It combines the raw line-rate throughput of the in-tree Linux kernel WireGuard data plane with a modern, containerized Zero-Trust control plane.

### Core Architectural Principles
1. **Separation of Data Plane and Control Plane**:
   - **Data Plane (In-Tree Kernel)**: All packet encryption, decryption, route lookups, and NAT masquerading execute inside kernel space via `wireguard.ko` and `nftables`. No user-space packet copying occurs.
   - **Control Plane (Containerized FastAPI)**: Administrative tasks, peer keypair lifecycle management, telemetry collection, and dynamic firewall rule compilation run inside an isolated Docker container with strict boundaries.
2. **Zero-Trust Network Architecture (ZTNA)**:
   - Granular packet filtering per client `/32` IP address.
   - Strict ingress, egress, and inter-client isolation policies managed via `nftables` atomic transactions.
3. **Air-Gapped & Offline Independence**:
   - 100% self-contained: Zero external CDN dependencies, embedded CSS3/SVG design, local QR code generation, pre-compiled Python wheels, and single-tarball Docker distribution.
4. **Resilient Mutation Pipeline**:
   - 12-step safe mutation pipeline for firewall rules: dry-run syntax verification (`nft -c -f`), atomic commits, automated backup snapshots, and instant rollback on failure.

---

## 2. End-to-End System Architecture

```mermaid
flowchart TD
    subgraph Clients["WireGuard Clients"]
        C1["Admin Workstation\n(172.29.250.2/32)"]
        C2["Mobile Device\n(172.29.250.3/32)"]
        C3["Branch Office Gateway\n(172.29.250.4/32)"]
    end

    subgraph Host["Air-Gapped Linux Host (10.31.7.48)"]
        subgraph PhysicalNICs["Physical Network Interfaces"]
            WAN["WAN / Internet\n(ens19)"]
            LAN["Internal LAN / Subnet\n(ens18)"]
        end

        subgraph KernelSpace["Linux Kernel Space (Kernel 5.6+)"]
            WG_MOD["wireguard.ko (In-Tree Kernel Module)\n- Curve25519 ECDH\n- ChaCha20-Poly1305 AEAD\n- BLAKE2s Hashing"]
            WG_IF["Virtual Interface: wg0\nIP: 172.29.250.1/24\nPort: 443/UDP"]
            IP_FWD["Kernel Packet Forwarding\n(sysctl net.ipv4.ip_forward = 1)"]
            
            subgraph NFT_ENGINE["NFTables Kernel Subsystem"]
                TABLE_FILTER["table inet filter\n- chain input / forward / output"]
                TABLE_WG["table inet wiregate\n- chain input (Port 443 accept)\n- chain forward (ACL rules & state tracking)\n- chain postrouting (NAT Masquerade -> ens18/ens19)"]
            end
        end

        subgraph Storage["Persistent Host Storage"]
            WG_CONF["/etc/wireguard/wg0.conf\n(Cryptographic peers & routing)"]
            NFT_CONF["/etc/nftables.conf\n(Base host firewall rules)"]
            ACL_NFT["/etc/nftables/acl.nft\n(Dynamic WireGuard client ACLs)"]
            SQLITE_DB["/opt/wireguard-enterprise/data/wireguard.db\n(SQLite + WAL mode)"]
            ENV_FILE[".env\n(Secrets & Environment Configuration)"]
        end

        subgraph Container["Container Runtime (Docker - network_mode: host, cap_add: NET_ADMIN)"]
            subgraph WebApp["wireguard-manager (FastAPI Backend - Port 8000)"]
                API["REST API Router (/api/*)"]
                WEB["Web Router (/login, /peers, /firewall, /server)"]
                
                subgraph CoreModules["Application Core Engines"]
                    WG_ENG["WireGuard Engine\n- Keypair Generator (Curve25519)\n- wg syncconf / wg set\n- Handshake & Bandwidth Telemetry"]
                    NFT_ENG["NFTables Engine\n- 12-Step Safe Mutation Pipeline\n- Dry-Run Syntax Validator\n- Timestamped Snapshots & Rollback"]
                    IPAM["IPAM Engine\n- Next-Available IP Allocation\n- Subnet Boundary Enforcer"]
                    SEC["Security Engine\n- PBKDF2 Password Hashing\n- Session Cookie Management\n- Rate Limiting"]
                end
            end

            subgraph UI["Zero-CDN Presentation Layer"]
                TEMPLATES["Jinja2 Server-Side Templates\n(HTML5 + Semantic SVGs)"]
                STATIC_ASSETS["Static Assets\n- CSS: style.css (Obsidian Zinc, Nordic, OLED, Slate)\n- JS: app.js (AJAX, Modals, Live Polling)\n- JS: qrcode.min.js (Offline QR rendering)"]
            end
        end
    end

    subgraph Browser["Administrator Browser"]
        ADM["Web Browser\nhttp://10.31.7.48:8000\n(Obsidian Zinc UI)"]
    end

    %% Client tunnel connections
    C1 -. "Encrypted WireGuard UDP:443" .-> WAN
    C2 -. "Encrypted WireGuard UDP:443" .-> WAN
    C3 -. "Encrypted WireGuard UDP:443" .-> WAN
    WAN --> WG_IF
    WG_IF <--> WG_MOD
    WG_MOD <--> IP_FWD
    IP_FWD <--> NFT_ENGINE
    NFT_ENGINE -. "NAT Masquerade" .-> LAN
    NFT_ENGINE -. "Forwarding" .-> WAN

    %% Management connections
    ADM <== "HTTP / Port 8000" ==> WEB
    WEB --> CoreModules
    API --> CoreModules
    CoreModules <--> SQLITE_DB
    WG_ENG <== "IPC / Netlink / CLI" ==> WG_IF
    WG_ENG --> WG_CONF
    NFT_ENG --> NFT_CONF
    NFT_ENG --> ACL_NFT
    NFT_ENG <== "nft -f / atomic reload" ==> NFT_ENGINE
```

---

## 3. Detailed Architectural Layers

### Layer 1: Physical & Virtual Network Topology

The host is configured with dual physical interfaces and a dedicated virtual tunnel interface:

```
[ Physical LAN: ens18 ] ──┐
                          ├──> [ Linux Kernel Routing / NFTables ] <──> [ wg0: 172.29.250.1/24 (UDP 443) ]
[ Physical WAN: ens19 ] ──┘
```

- **`ens18` (LAN Interface)**: Connects to the local trusted corporate subnet (e.g., `10.31.7.0/24`), enabling routed access to internal servers, databases, and services.
- **`ens19` (WAN / Internet Interface)**: Connects to the upstream gateway or public Internet for client inbound tunnels and outbound masqueraded traffic.
- **`wg0` (Virtual WireGuard Interface)**:
  - **Subnet**: `172.29.250.0/24` (Configurable via `.env`).
  - **Server IP**: `172.29.250.1/24`.
  - **Listen Port**: `443/UDP` (Standard HTTPS port for firewall traversal).
  - **Cryptokey Routing Table**: Maps client public keys to their assigned `/32` IPs (e.g., `172.29.250.2/32`).

---

### Layer 2: In-Tree Linux Kernel Data Plane (`wireguard.ko`)

WireGuard runs directly inside the Linux kernel (kernel version >= 5.6) rather than user-space (such as `wireguard-go` or `openvpn` TUN/TAP):

- **Zero-Copy Network Stack**: WireGuard packets are processed directly within softirq handlers in the kernel networking subsystem, achieving near line-rate speeds (10 Gbps+ capable on modern hardware).
- **Cryptographic Algorithms**:
  - **Key Exchange**: Curve25519 (ECDH)
  - **Encryption & Authentication**: ChaCha20-Poly1305 (AEAD)
  - **Hashing**: BLAKE2s
  - **Key Rotation**: 1.5-minute re-keying timer with forward secrecy.
- **Kernel Routing Flag**:
  - Requires `net.ipv4.ip_forward = 1` persisted in `/etc/sysctl.d/99-wireguard-forward.conf`.

---

### Layer 3: Dynamic NFTables Firewall & Zero-Trust ACL Engine

The firewall architecture uses a modular, two-tier design to prevent configuration collisions:

```
/etc/nftables.conf (Main Host Ruleset)
    │
    ├──> table inet filter (Base host rules: input, forward, output)
    │
    └──> table inet wiregate (WireGuard ruleset)
            ├── chain input (Allows UDP 443, ICMP, established traffic)
            ├── chain forward
            │       │
            │       ├──> include "/etc/nftables/acl.nft" (Dynamic Client-specific ACLs)
            │       │
            │       └──> iifname "wg0" oifname != "wg0" accept
            │
            └── chain postrouting
                    └── ip saddr 172.29.250.0/24 oifname != "wg0" masquerade (NAT)
```

#### The 12-Step Safe Mutation Pipeline (`app/core/nftables.py`)
To prevent network lockouts, syntax errors, or kernel state corruption, any change to firewall rules undergoes a transactional pipeline:
1. **Pre-mutation lock acquisition** (prevents race conditions).
2. **Snapshot creation**: Current `/etc/nftables.conf` and `/etc/nftables/acl.nft` backed up with high-resolution timestamps to `data/firewall/backups/`.
3. **Parse and render**: Generates prospective ruleset with clean comment delimiters (`# WG_MANAGED_START` / `# WG_MANAGED_END`).
4. **Syntax dry-run**: Tests ruleset in user-space using `nft -c -f <tempfile>`.
5. **Atomic write**: Writes valid configuration to target file path.
6. **Kernel apply**: Executes `nft -f /etc/nftables.conf`.
7. **Verification check**: Queries `nft list ruleset` to verify table presence.
8. **Automated rollback**: If any step between 4 and 7 throws an error, the previous snapshot is restored and re-applied within milliseconds.
9. **Audit trail**: Records change event, actor, diff, and outcome in `audit_logs` SQLite table.

---

### Layer 4: Containerization & Isolation Runtime

```mermaid
flowchart LR
    subgraph HostNetworkStack["Host Network Stack (/dev/net/tun, wg0, ens18, ens19)"]
        H_NET["Host Sockets & Netlink"]
    end

    subgraph DockerHost["Docker Host"]
        subgraph Container["Container: wireguard-manager"]
            APP["FastAPI Application"]
        end
    end

    subgraph Volumes["Mounted Volumes"]
        V1["./data -> /data"]
        V2["./app -> /app/app"]
        V3["/etc/wireguard -> /etc/wireguard"]
        V4["/etc/nftables -> /etc/nftables"]
        V5["/etc/nftables.conf -> /etc/nftables.conf"]
    end

    APP <== "network_mode: host\n(Direct socket binding, 0 NAT overhead)" ==> H_NET
    APP --- Volumes
```

- **`network_mode: host`**: Bypasses the default Docker bridge network (`docker0`). The container directly interacts with `wg0`, `ens18`, and `ens19`, avoiding double-NAT penalties and allowing native netlink kernel communications.
- **`cap_add: [NET_ADMIN]`**: Grants the container capability to manage network interfaces (`wg`, `ip`), routes, and nftables rulesets without needing fully unconstrained privileged mode.
- **Volume Mounting**:
  - `./data:/data`: Houses SQLite database, encryption keys, and JSON backup states.
  - `./app:/app/app`: Mounts application code for real-time updates without image rebuilding.
  - `/etc/wireguard:/etc/wireguard`: Manages `wg0.conf`.
  - `/etc/nftables:/etc/nftables`: Manages `acl.nft`.
  - `/etc/nftables.conf:/etc/nftables.conf`: Manages host firewall ruleset.

---

### Layer 5: Backend Application Engine (FastAPI / Python 3.12)

The application core is structured into decoupled domain services:

```mermaid
classDiagram
    class WireGuardEngine {
        +generate_keypair() WireGuardKeypair
        +public_key_from_private(priv) str
        +get_interface_status(iface) Dict
        +sync_conf(iface, conf_path) bool
        +add_peer(peer_data) bool
        +remove_peer(pubkey) bool
        +get_peer_telemetry() List~Dict~
    }

    class NFTablesEngine {
        +apply_acl_rules(rules) Tuple~bool, str~
        +validate_syntax(ruleset) bool
        +create_snapshot() str
        +rollback(snapshot_path) bool
        +parse_ruleset() Dict
        +get_conf_file_info() Dict
    }

    class IPAMEngine {
        +get_next_available_ip(subnet, used_ips) str
        +validate_ip(ip, subnet) bool
        +calculate_utilization() float
    }

    class SecurityEngine {
        +hash_password(raw_password) str
        +verify_password(raw, hashed) bool
        +create_session(user_id) str
        +validate_session(token) bool
    }

    class DatabaseManager {
        +init_db()
        +get_db_session() Session
        +get_peers() List
        +get_firewall_rules() List
        +log_audit(action, user, details)
    }

    WireGuardEngine ..> DatabaseManager
    NFTablesEngine ..> DatabaseManager
    IPAMEngine ..> DatabaseManager
    SecurityEngine ..> DatabaseManager
```

---

### Layer 6: Presentation & Theme Architecture

The user interface follows a modern glassmorphism design philosophy engineered for security operations centers (SOC) and NOC engineers:

- **100% Offline / Zero-CDN**:
  - No external fonts (uses native system typography stack: Inter, `-apple-system`, BlinkMacSystemFont, Segoe UI).
  - All icons are inline SVG vectors (crisp at all DPI scales, zero external network requests).
  - Embedded QR code generation via local `app/static/js/qrcode.min.js`.
- **Multi-Theme Engine**:
  - **Obsidian Zinc (Default)**: Linear & Tailscale inspired dark palette (`#09090b` background, `#27272a` borders, vibrant `#6366f1` accent).
  - **Nordic Frost**: Arctic deep-blue palette (`#0b101b` canvas, `#38bdf8` ice-blue accent).
  - **Midnight OLED**: Ultra-deep pitch black (`#000000` canvas, high-contrast `#10b981` emerald accent).
  - **Light Slate**: Clean daylight mode (`#f8fafc` canvas, `#2563eb` cobalt accent).

---

## 4. Key Sequence Flows

### 4.1 Peer Creation & Kernel Synchronization Flow

```mermaid
sequenceDiagram
    actor Admin as Administrator
    participant UI as Web Dashboard
    participant API as FastAPI Backend
    participant IPAM as IPAM Engine
    participant Crypto as Cryptography (X25519)
    participant DB as SQLite (wireguard.db)
    participant WG as Kernel WireGuard (wg0)

    Admin->>UI: Click "Add Peer" (Name: Workstation-1)
    UI->>API: POST /api/peers
    API->>IPAM: Allocate Next Available IP
    IPAM-->>API: 172.29.250.2/32
    API->>Crypto: Generate Curve25519 Keypair
    Crypto-->>API: { PrivKey, PubKey }
    API->>DB: INSERT into peers (name, pubkey, privkey, ip, status)
    DB-->>API: Record Persisted
    API->>WG: Execute `wg set wg0 peer <PubKey> allowed-ips 172.29.250.2/32`
    WG-->>API: Kernel Routing Updated
    API-->>UI: Return Peer Details + QR Code Base64
    UI-->>Admin: Render Download .conf & Display QR Code
```

---

### 4.2 Firewall Rule Update & Safe Mutation Flow

```mermaid
sequenceDiagram
    actor Admin as Administrator
    participant UI as Firewall & ACL View
    participant API as FastAPI (/api/firewall)
    participant NFT_ENG as NFTables Core Engine
    participant Disk as Host Filesystem
    participant Kernel as Linux NFTables Kernel

    Admin->>UI: Submit Rule: Drop TCP 22 for Peer 172.29.250.5
    UI->>API: POST /api/firewall/acl
    API->>NFT_ENG: apply_rule(chain="forward", rule="ip saddr 172.29.250.5 tcp dport 22 drop")
    NFT_ENG->>Disk: Backup /etc/nftables/acl.nft -> /data/firewall/backups/snapshot_ts.json
    NFT_ENG->>Disk: Write prospective rules to /tmp/nft_test.conf
    NFT_ENG->>Kernel: Dry-Run Syntax Validation: `nft -c -f /tmp/nft_test.conf`
    
    alt Syntax Valid
        Kernel-->>NFT_ENG: 0 (Success)
        NFT_ENG->>Disk: Overwrite /etc/nftables/acl.nft
        NFT_ENG->>Kernel: Atomic Reload: `nft -f /etc/nftables.conf`
        Kernel-->>NFT_ENG: Applied in Kernel
        NFT_ENG-->>API: Status 200 OK
        API-->>UI: Update Table & Display Success Toast
    else Syntax Error
        Kernel-->>NFT_ENG: Error code / Syntax rejection
        NFT_ENG->>Disk: Restore previous snapshot
        NFT_ENG-->>API: Error 400 (Validation Failed, Rollback Executed)
        API-->>UI: Display Alert with Exact Error Message
    end
```

---

## 5. Database Schema & Data Model

The application uses SQLite in WAL (Write-Ahead Logging) mode for concurrent read operations without locking writes.

```mermaid
erDiagram
    PEERS ||--o{ AUDIT_LOGS : generates
    FIREWALL_RULES ||--o{ AUDIT_LOGS : modifies
    SERVER_CONFIG ||--o{ AUDIT_LOGS : tracks

    PEERS {
        int id PK
        string name
        string public_key UK
        string private_key
        string preshared_key
        string allowed_ips
        string assigned_ip
        boolean is_active
        datetime created_at
        datetime last_handshake
        bigint rx_bytes
        bigint tx_bytes
    }

    SERVER_CONFIG {
        int id PK
        string interface_name
        string private_key
        string public_key
        int listen_port
        string network_subnet
        string server_ip
        string dns_servers
        string lan_interface
        string wan_interface
        text post_up_rules
        text post_down_rules
    }

    FIREWALL_RULES {
        int id PK
        string rule_type
        string chain
        string action
        string protocol
        string source_ip
        string destination_ip
        int port
        int rule_priority
        boolean is_enabled
        string description
        datetime updated_at
    }

    AUDIT_LOGS {
        int id PK
        string action
        string target
        string executed_by
        text details
        datetime timestamp
    }

    USERS {
        int id PK
        string username UK
        string password_hash
        string role
        datetime last_login
    }
```

---

## 6. Security Architecture & Threat Model

| Security Dimension | Implementation & Mitigations |
| :--- | :--- |
| **Tunnel Cryptography** | Curve25519 ECDH for key exchange; ChaCha20-Poly1305 for authenticated encryption. Re-keying occurs every 1.5 minutes automatically. |
| **Credential Protection** | Admin passwords hashed using PBKDF2 with SHA-256 and salt. Session cookies use `SameSite=Lax`, `HttpOnly`, and cryptographically signed session tokens. |
| **Host Network Attack Surface** | Only UDP port `443` (WireGuard) and TCP port `8000` (Web UI) are opened. No unauthenticated user-space ports are exposed to untrusted networks. |
| **Isolation & Containment** | Control plane operates in a non-root-contained Docker workspace with dropped capabilities except `NET_ADMIN`. |
| **Zero External Telemetry** | Complete air-gap guarantee: No analytics, tracking pixels, CDN scripts, or external font stylesheets. System functions identically with physical network cables disconnected from the Internet. |
| **Denial of Service (DoS) Defense** | WireGuard does not respond to unauthenticated packets (stealth port scanning resistance). Nftables state tracking drops invalid and malformed frames before socket dispatch. |
