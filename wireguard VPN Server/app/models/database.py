import datetime
from typing import Generator, Optional
from sqlalchemy import (
    create_engine,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
    Session,
)

from app.core.config import (
    DATABASE_URL,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    WG_INTERFACE,
    WG_DEFAULT_ADDRESS,
    WG_DEFAULT_PORT,
    WG_DEFAULT_DNS,
    WG_DEFAULT_ENDPOINT,
    WG_DEFAULT_MTU,
)
from app.core.security import hash_password, verify_password, encrypt_key, decrypt_key, is_wireguard_key
from app.core.ipam import IPAM
from app.core.wireguard import WireGuardEngine

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="admin") # 'admin', 'viewer'
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

class ServerInterface(Base):
    __tablename__ = "interfaces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, default="wg0")
    address: Mapped[str] = mapped_column(String(64), default="10.8.0.1/24")
    listen_port: Mapped[int] = mapped_column(Integer, default=51820)
    private_key: Mapped[str] = mapped_column(Text)
    public_key: Mapped[str] = mapped_column(String(64))
    endpoint: Mapped[str] = mapped_column(String(128), default="")
    dns: Mapped[str] = mapped_column(String(128), default="")
    mtu: Mapped[int] = mapped_column(Integer, default=1420)
    extra_directives: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    peers: Mapped[list["Peer"]] = relationship("Peer", back_populates="interface", cascade="all, delete-orphan")

class Peer(Base):
    __tablename__ = "peers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    interface_id: Mapped[int] = mapped_column(Integer, ForeignKey("interfaces.id"))
    name: Mapped[str] = mapped_column(String(80), index=True)
    public_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    private_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # encrypted client priv key
    psk: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # preshared key
    allowed_ips: Mapped[str] = mapped_column(String(255))
    endpoint: Mapped[Optional[str]] = mapped_column(String(255), default="")
    keepalive: Mapped[Optional[int]] = mapped_column(Integer, default=25)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    device_type: Mapped[str] = mapped_column(String(20), default="laptop") # laptop, phone, desktop, server
    tunnel_mode: Mapped[str] = mapped_column(String(20), default="full")    # full, split, custom
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    interface: Mapped["ServerInterface"] = relationship("ServerInterface", back_populates="peers")
    acls: Mapped[list["WireGuardAcl"]] = relationship("WireGuardAcl", back_populates="peer", cascade="all, delete-orphan")

class WireGuardPolicy(Base):
    __tablename__ = "firewall_policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_isolation: Mapped[bool] = mapped_column(Boolean, default=True) # Block peer-to-peer traffic
    internet_access: Mapped[bool] = mapped_column(Boolean, default=True)   # Enable NAT masquerade
    allow_dns: Mapped[bool] = mapped_column(Boolean, default=True)         # Allow port 53
    default_forward_policy: Mapped[str] = mapped_column(String(10), default="drop") # 'drop' or 'accept'
    mss_clamping: Mapped[bool] = mapped_column(Boolean, default=True)     # Clamp TCP MSS to PMTU
    drop_invalid: Mapped[bool] = mapped_column(Boolean, default=True)     # Drop ct state invalid
    icmp_limit: Mapped[bool] = mapped_column(Boolean, default=True)       # Limit ping echo requests
    log_dropped: Mapped[bool] = mapped_column(Boolean, default=False)     # Log dropped packets
    auto_backup: Mapped[bool] = mapped_column(Boolean, default=True)      # Auto-snapshot before mutation

class WireGuardAcl(Base):
    __tablename__ = "wireguard_acls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    peer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("peers.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(80))
    src_cidr: Mapped[str] = mapped_column(String(64), default="") # auto from peer or custom
    dst_cidr: Mapped[str] = mapped_column(String(64), default="any") # e.g. 192.168.1.0/24 or any
    proto: Mapped[str] = mapped_column(String(10), default="all") # 'all', 'tcp', 'udp', 'icmp'
    ports: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) # e.g. '80,443' or '22'
    action: Mapped[str] = mapped_column(String(10), default="accept") # 'accept', 'drop', 'reject'
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    peer: Mapped[Optional["Peer"]] = relationship("Peer", back_populates="acls")

class NftCustomRule(Base):
    __tablename__ = "nft_custom_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    family: Mapped[str] = mapped_column(String(10), default="inet")
    table: Mapped[str] = mapped_column(String(32), default="wiregate")
    chain: Mapped[str] = mapped_column(String(32), default="wg_forward")
    statement: Mapped[str] = mapped_column(Text) # e.g. 'tcp dport 22 accept'
    comment: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """FastAPI database dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_audit(db: Session, actor: str, action: str, detail: str):
    """Utility to record audit actions."""
    try:
        entry = AuditLog(actor=actor, action=action, detail=detail)
        db.add(entry)
        db.commit()
    except Exception:
        db.rollback()

def init_db():
    """Initializes schema and creates default admin and default server interface if needed."""
    Base.metadata.create_all(bind=engine)

    # Safe column migration for SQLite
    try:
        with engine.connect() as conn:
            cols = [c[1] for c in conn.exec_driver_sql("PRAGMA table_info(peers)").fetchall()]
            if "device_type" not in cols:
                conn.exec_driver_sql("ALTER TABLE peers ADD COLUMN device_type VARCHAR(20) DEFAULT 'laptop'")
            if "tunnel_mode" not in cols:
                conn.exec_driver_sql("ALTER TABLE peers ADD COLUMN tunnel_mode VARCHAR(20) DEFAULT 'full'")
            conn.commit()
    except Exception:
        pass

def auto_import_database(db: Session) -> dict:
    """
    Unified, idempotent auto-import of server interface configuration and all peers.
    1. Scans /etc/wireguard/wg0.conf, all backup snapshots (.bak.*), and kernel dump (wg show wg0 dump).
    2. Adopts server private/public keys, address, listening port, MTU, and PostUp/PostDown scripts.
    3. Scans and deduplicates all unique peers by public key, merging friendly names, IPs, endpoints, and PSKs.
    4. Renders the complete, updated /etc/wireguard/wg0.conf and syncs WireGuard with zero downtime.
    """
    data = WireGuardEngine.discover_all_host_data(WG_INTERFACE)
    discovered_iface = data.get("interface", {})

    # 1. Interface Synchronization
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        priv_key = discovered_iface.get("private_key")
        if priv_key and is_wireguard_key(priv_key):
            try:
                pub_key = discovered_iface.get("public_key") or WireGuardEngine.public_key_from_private(priv_key)
            except Exception:
                pub_key = ""
        else:
            keys = WireGuardEngine.generate_keypair()
            priv_key = keys.private_key
            pub_key = keys.public_key

        iface = ServerInterface(
            name=WG_INTERFACE,
            address=discovered_iface.get("address") or WG_DEFAULT_ADDRESS,
            listen_port=int(discovered_iface.get("listen_port") or WG_DEFAULT_PORT),
            private_key=encrypt_key(priv_key),
            public_key=pub_key or "",
            endpoint=discovered_iface.get("endpoint") or WG_DEFAULT_ENDPOINT,
            dns=discovered_iface.get("dns") or WG_DEFAULT_DNS,
            mtu=int(discovered_iface.get("mtu") or WG_DEFAULT_MTU),
            extra_directives=discovered_iface.get("extra_directives") or ""
        )
        db.add(iface)
        db.flush()
        print(f"[+] Initialized interface: {WG_INTERFACE} (Public Key: {pub_key})")
    else:
        # Update existing interface if host or kernel has valid private key
        if discovered_iface.get("private_key") and is_wireguard_key(discovered_iface["private_key"]):
            priv_key = discovered_iface["private_key"]
            try:
                pub_key = discovered_iface.get("public_key") or WireGuardEngine.public_key_from_private(priv_key)
                if pub_key:
                    iface.private_key = encrypt_key(priv_key)
                    iface.public_key = pub_key
            except Exception:
                pass
        if discovered_iface.get("address") and discovered_iface["address"].strip():
            iface.address = discovered_iface["address"].strip()
        if discovered_iface.get("listen_port") and str(discovered_iface["listen_port"]).isdigit():
            iface.listen_port = int(discovered_iface["listen_port"])
        if discovered_iface.get("mtu") and str(discovered_iface["mtu"]).isdigit():
            iface.mtu = int(discovered_iface["mtu"])
        if discovered_iface.get("endpoint") and not iface.endpoint:
            iface.endpoint = discovered_iface["endpoint"]
        if discovered_iface.get("dns") and not iface.dns:
            iface.dns = discovered_iface["dns"]
        if discovered_iface.get("extra_directives") and discovered_iface["extra_directives"].strip():
            iface.extra_directives = discovered_iface["extra_directives"].strip()

    # 2. Peer Adoption & Upsert
    existing_peers = db.scalars(select(Peer).filter_by(interface_id=iface.id)).all()
    db_peers_by_pub = {p.public_key: p for p in existing_peers}
    occupied_ips = set(p.allowed_ips for p in existing_peers if p.allowed_ips)

    new_count = 0
    updated_count = 0

    for p_data in data.get("peers", []):
        pub = p_data.get("public_key", "").strip()
        if not pub or not is_wireguard_key(pub):
            continue

        candidate_ip = p_data.get("allowed_ips", "").strip()
        client_addr = p_data.get("client_address", "").strip()
        if candidate_ip in ["0.0.0.0/0", "0.0.0.0/0, ::/0", "::/0", ""] or not candidate_ip:
            if client_addr:
                candidate_ip = client_addr
            else:
                candidate_ip = IPAM.get_next_available_ip(iface.address, list(occupied_ips))

        if candidate_ip and "/" not in candidate_ip:
            candidate_ip = f"{candidate_ip}/32"

        if pub in db_peers_by_pub:
            peer = db_peers_by_pub[pub]
            if p_data.get("name") and not p_data["name"].startswith("Peer-") and peer.name.startswith("Peer-"):
                peer.name = p_data["name"]
            if candidate_ip and (not peer.allowed_ips or peer.allowed_ips == "0.0.0.0/0"):
                peer.allowed_ips = candidate_ip
                occupied_ips.add(candidate_ip)
            if p_data.get("endpoint") and not peer.endpoint:
                peer.endpoint = p_data["endpoint"]
            if p_data.get("psk") and not peer.psk and is_wireguard_key(p_data["psk"]):
                peer.psk = encrypt_key(p_data["psk"])
            if p_data.get("client_private_key") and not peer.private_key:
                peer.private_key = encrypt_key(p_data["client_private_key"])
            peer.enabled = True
            updated_count += 1
        else:
            if candidate_ip in occupied_ips:
                auto_ip = IPAM.get_next_available_ip(iface.address, list(occupied_ips))
                if auto_ip:
                    candidate_ip = auto_ip
            if candidate_ip:
                occupied_ips.add(candidate_ip)

            peer_name = p_data.get("name") or f"Peer-{len(existing_peers) + new_count + 1}"
            client_priv_enc = None
            if p_data.get("client_private_key"):
                client_priv_enc = encrypt_key(p_data["client_private_key"])

            new_peer = Peer(
                interface_id=iface.id,
                name=peer_name,
                public_key=pub,
                private_key=client_priv_enc,
                allowed_ips=candidate_ip,
                endpoint=p_data.get("endpoint", ""),
                keepalive=p_data.get("keepalive", 25),
                psk=encrypt_key(p_data["psk"]) if p_data.get("psk") and is_wireguard_key(p_data["psk"]) else None,
                device_type=p_data.get("device_type", "laptop"),
                tunnel_mode=p_data.get("tunnel_mode", "full"),
                enabled=True
            )
            db.add(new_peer)
            db_peers_by_pub[pub] = new_peer
            new_count += 1

    db.commit()

    # 3. Synchronize WireGuard configuration and kernel
    all_peers = db.scalars(select(Peer).filter_by(interface_id=iface.id)).all()
    server_priv = decrypt_key(iface.private_key)
    rendered = WireGuardEngine.render_server_config(
        server_address=iface.address,
        server_port=iface.listen_port,
        server_private_key=server_priv,
        peers=[{
            "name": p.name,
            "public_key": p.public_key,
            "psk": decrypt_key(p.psk) if p.psk else None,
            "allowed_ips": p.allowed_ips,
            "endpoint": p.endpoint,
            "keepalive": p.keepalive,
            "enabled": p.enabled
        } for p in all_peers],
        extra_directives=iface.extra_directives
    )
    sync_ok, sync_msg = WireGuardEngine.apply_syncconf(rendered, iface.name, allow_peer_removal=False)

    return {
        "success": True,
        "imported_new_peers": new_count,
        "updated_peers": updated_count,
        "total_peers": len(all_peers),
        "sync_status": sync_msg,
        "message": f"Successfully auto-imported {new_count} new peers and updated {updated_count} peers from host, backups, and live kernel. Total managed peers: {len(all_peers)}."
    }

def init_db():
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            cols = [c[1] for c in conn.exec_driver_sql("PRAGMA table_info(peers)").fetchall()]
            if "device_type" not in cols:
                conn.exec_driver_sql("ALTER TABLE peers ADD COLUMN device_type VARCHAR(20) DEFAULT 'laptop'")
            if "tunnel_mode" not in cols:
                conn.exec_driver_sql("ALTER TABLE peers ADD COLUMN tunnel_mode VARCHAR(20) DEFAULT 'full'")
            conn.commit()
    except Exception:
        pass

    with SessionLocal() as db:
        # 1. Ensure default Admin user exists
        user = db.scalar(select(User).filter_by(username=ADMIN_USERNAME))
        if not user:
            default_user = User(
                username=ADMIN_USERNAME,
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin"
            )
            db.add(default_user)
            db.commit()
            print(f"[+] Initialized default admin: {ADMIN_USERNAME}")
        else:
            if ADMIN_PASSWORD and not verify_password(user.password_hash, ADMIN_PASSWORD):
                user.password_hash = hash_password(ADMIN_PASSWORD)
                db.commit()
                print(f"[+] Synchronized admin password from environment for: {ADMIN_USERNAME}")

        # 2. Ensure default Viewer user exists (read-only policy)
        viewer = db.scalar(select(User).filter_by(username="viewer"))
        if not viewer:
            default_viewer = User(
                username="viewer",
                password_hash=hash_password("viewer123"),
                role="viewer"
            )
            db.add(default_viewer)
            db.commit()
            print("[+] Initialized default viewer: viewer (role: viewer)")
        else:
            if not verify_password(viewer.password_hash, "viewer123"):
                viewer.password_hash = hash_password("viewer123")
                viewer.role = "viewer"
                db.commit()
                print("[+] Synchronized viewer password and role")

        # 3. Ensure default server interface exists (never auto-import peers on startup)
        existing_iface = db.scalar(select(ServerInterface).limit(1))
        if not existing_iface:
            keys = WireGuardEngine.generate_keypair()
            default_iface = ServerInterface(
                name=WG_INTERFACE,
                address=WG_DEFAULT_ADDRESS,
                listen_port=WG_DEFAULT_PORT,
                private_key=encrypt_key(keys.private_key),
                public_key=keys.public_key,
                endpoint=WG_DEFAULT_ENDPOINT,
                dns=WG_DEFAULT_DNS,
                mtu=WG_DEFAULT_MTU,
                extra_directives=""
            )
            db.add(default_iface)
            db.commit()
            print(f"[+] Initialized default interface: {WG_INTERFACE}")

        # 3. Ensure default firewall policy exists
        policy = db.scalar(select(WireGuardPolicy).limit(1))
        if not policy:
            default_policy = WireGuardPolicy(
                client_isolation=True,
                internet_access=True,
                allow_dns=True,
                default_forward_policy="drop"
            )
            db.add(default_policy)
            db.commit()
            print("[+] Initialized default firewall policy.")


