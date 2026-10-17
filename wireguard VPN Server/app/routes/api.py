import os
import glob
from typing import Optional
import ipaddress
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import WG_EXECUTION_MODE, WG_INTERFACE
from app.core.security import decrypt_key, encrypt_key, is_wireguard_key
from app.core.ipam import IPAM
from app.core.wireguard import WireGuardEngine
from app.models.database import get_db, ServerInterface, Peer, User, AuditLog, log_audit, auto_import_database
from app.schemas import PeerCreate, PeerUpdate, ServerUpdate

router = APIRouter(prefix="/api", tags=["API"])

def get_current_user_api(request: Request, db: Session = Depends(get_db)) -> User:
    """Retrieve the currently authenticated user from session, token, or fallback."""
    uid = request.session.get("uid")
    if uid:
        user = db.get(User, uid)
        if user:
            return user

    # Check Bearer auth token if provided
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        from app.core.config import APP_SECRET, WG_AGENT_TOKEN
        if token and token in [APP_SECRET, WG_AGENT_TOKEN]:
            admin_user = db.scalar(select(User).filter_by(role="admin"))
            if admin_user:
                return admin_user

    # Internal localhost loopback CLI fallback
    client_host = getattr(request.client, "host", "") if request.client else ""
    if client_host in ["127.0.0.1", "localhost", "::1"]:
        admin_user = db.scalar(select(User).filter_by(role="admin"))
        if admin_user:
            return admin_user

    user = db.scalar(select(User).limit(1))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user

def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """Enforce Full Access / Admin role policy. Blocks viewer role with HTTP 403 Forbidden."""
    user = get_current_user_api(request, db)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Policy Restriction: Viewer account is Read-Only. Full Access / Admin permissions required."
        )
    return user

@router.get("/status")
def get_server_status(db: Session = Depends(get_db)):
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        raise HTTPException(status_code=404, detail="Interface not configured")

    peers = db.scalars(select(Peer).filter_by(interface_id=iface.id)).all()
    live_stats = WireGuardEngine.get_live_peer_stats(iface.name)

    active_count = sum(1 for p in peers if p.enabled and live_stats.get(p.public_key, {}).get("is_active", False))
    total_rx = sum(live_stats.get(p.public_key, {}).get("transfer_rx", 0) for p in peers)
    total_tx = sum(live_stats.get(p.public_key, {}).get("transfer_tx", 0) for p in peers)

    return {
        "interface": iface.name,
        "mode": WG_EXECUTION_MODE,
        "address": iface.address,
        "listen_port": iface.listen_port,
        "public_key": iface.public_key,
        "endpoint": iface.endpoint,
        "dns": iface.dns,
        "mtu": iface.mtu,
        "total_peers": len(peers),
        "enabled_peers": sum(1 for p in peers if p.enabled),
        "active_peers": active_count,
        "total_rx_readable": WireGuardEngine.format_bytes(total_rx),
        "total_tx_readable": WireGuardEngine.format_bytes(total_tx),
    }

@router.get("/live/metrics")
def get_live_metrics(db: Session = Depends(get_db)):
    """Ultra-fast endpoint returning dynamic peer status and bandwidth counters for frontend live polling."""
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        raise HTTPException(status_code=404, detail="Interface not configured")

    peers = db.scalars(select(Peer).filter_by(interface_id=iface.id)).all()
    live_stats = WireGuardEngine.get_live_peer_stats(iface.name)

    active_count = 0
    total_rx = 0
    total_tx = 0
    peer_metrics = []

    for p in peers:
        stat = live_stats.get(p.public_key, {})
        is_active = stat.get("is_active", False) and p.enabled
        if is_active:
            active_count += 1
        rx = stat.get("transfer_rx", 0)
        tx = stat.get("transfer_tx", 0)
        total_rx += rx
        total_tx += tx

        peer_metrics.append({
            "id": p.id,
            "public_key": p.public_key,
            "enabled": p.enabled,
            "is_active": is_active,
            "latest_handshake": stat.get("latest_handshake", 0),
            "handshake_readable": stat.get("handshake_readable", "Never") if p.enabled else "Disabled",
            "transfer_rx_readable": stat.get("transfer_rx_readable", "0 B"),
            "transfer_tx_readable": stat.get("transfer_tx_readable", "0 B"),
            "transfer_rx_raw": rx,
            "transfer_tx_raw": tx,
        })

    return {
        "interface": iface.name,
        "total_peers": len(peers),
        "enabled_peers": sum(1 for p in peers if p.enabled),
        "active_peers": active_count,
        "total_rx_readable": WireGuardEngine.format_bytes(total_rx),
        "total_tx_readable": WireGuardEngine.format_bytes(total_tx),
        "total_rx_raw": total_rx,
        "total_tx_raw": total_tx,
        "peers": peer_metrics
    }

@router.get("/peers")
def list_peers(db: Session = Depends(get_db)):
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        return []

    peers = db.scalars(select(Peer).filter_by(interface_id=iface.id).order_by(Peer.id.desc())).all()
    live_stats = WireGuardEngine.get_live_peer_stats(iface.name)

    result = []
    for p in peers:
        stat = live_stats.get(p.public_key, {})
        result.append({
            "id": p.id,
            "name": p.name,
            "public_key": p.public_key,
            "allowed_ips": p.allowed_ips,
            "endpoint": p.endpoint,
            "keepalive": p.keepalive,
            "enabled": p.enabled,
            "device_type": getattr(p, "device_type", "laptop") or "laptop",
            "tunnel_mode": getattr(p, "tunnel_mode", "full") or "full",
            "has_private_key": bool(p.private_key),
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "is_active": stat.get("is_active", False) and p.enabled,
            "latest_handshake": stat.get("latest_handshake", 0),
            "handshake_readable": stat.get("handshake_readable", "Never") if p.enabled else "Disabled",
            "transfer_rx_readable": stat.get("transfer_rx_readable", "0 B"),
            "transfer_tx_readable": stat.get("transfer_tx_readable", "0 B"),
        })
    return result

@router.get("/peers/next-ip")
def get_next_available_peer_ip(db: Session = Depends(get_db)):
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        return {"next_ip": "172.29.250.11/32"}
    existing_peers = db.scalars(select(Peer).filter_by(interface_id=iface.id)).all()
    existing_ips = [p.allowed_ips for p in existing_peers]
    next_ip = IPAM.get_next_available_ip(iface.address, existing_ips) or "172.29.250.11/32"
    return {"next_ip": next_ip}

@router.post("/peers", status_code=status.HTTP_201_CREATED)

def create_peer(data: PeerCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        raise HTTPException(status_code=404, detail="Server interface not found")

    # 1. IP Allocation (IPAM)
    assigned_ip = data.allowed_ips
    if not assigned_ip or not assigned_ip.strip():
        existing_peers = db.scalars(select(Peer).filter_by(interface_id=iface.id)).all()
        existing_ips = [p.allowed_ips for p in existing_peers]
        auto_ip = IPAM.get_next_available_ip(iface.address, existing_ips)
        if not auto_ip:
            raise HTTPException(status_code=400, detail="Subnet is full. No available IP address.")
        assigned_ip = auto_ip
    else:
        assigned_ip = IPAM.format_allowed_ips(assigned_ip)

    # 2. Keypair generation or validation
    client_priv_enc = None
    if not data.public_key or not data.public_key.strip():
        keypair = WireGuardEngine.generate_keypair()
        public_key = keypair.public_key
        client_priv_enc = encrypt_key(keypair.private_key)
    else:
        public_key = data.public_key.strip()
        if not WireGuardEngine.validate_key(public_key):
            raise HTTPException(status_code=400, detail="Invalid Curve25519 public key format.")

    # Check for duplicate public key
    existing_key = db.scalar(select(Peer).filter_by(public_key=public_key))
    if existing_key:
        raise HTTPException(status_code=400, detail="A peer with this public key already exists.")

    # 3. PSK handling
    psk_value = None
    if data.generate_psk:
        psk_value = WireGuardEngine.generate_psk()
    elif data.psk and data.psk.strip():
        psk_value = data.psk.strip()

    # 4. Save to Database
    peer = Peer(
        interface_id=iface.id,
        name=data.name.strip(),
        public_key=public_key,
        private_key=client_priv_enc,
        psk=encrypt_key(psk_value) if psk_value else None,
        allowed_ips=assigned_ip,
        endpoint=data.endpoint.strip() if data.endpoint else "",
        keepalive=data.keepalive,
        device_type=data.device_type or "laptop",
        tunnel_mode=data.tunnel_mode or "full",
        enabled=True
    )
    db.add(peer)
    db.commit()
    db.refresh(peer)

    # 5. Sync WireGuard
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
    sync_ok, sync_msg = WireGuardEngine.apply_syncconf(rendered, iface.name)
    log_audit(db, "admin", "CREATE_PEER", f"Created peer '{peer.name}' ({peer.allowed_ips}). Sync: {sync_msg}")

    return {
        "id": peer.id,
        "name": peer.name,
        "public_key": peer.public_key,
        "allowed_ips": peer.allowed_ips,
        "sync_status": sync_msg
    }

@router.post("/peers/{peer_id}/toggle")
def toggle_peer(peer_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    peer = db.get(Peer, peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    peer.enabled = not peer.enabled
    db.commit()

    iface = db.get(ServerInterface, peer.interface_id)
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
    sync_ok, sync_msg = WireGuardEngine.apply_syncconf(rendered, iface.name)
    state_str = "enabled" if peer.enabled else "disabled"
    log_audit(db, "admin", "TOGGLE_PEER", f"Peer '{peer.name}' {state_str}. Sync: {sync_msg}")

    return {"id": peer.id, "enabled": peer.enabled, "sync_status": sync_msg}

@router.get("/peers/{peer_id}")
def get_peer(peer_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    peer = db.get(Peer, peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")
    return {
        "id": peer.id,
        "name": peer.name,
        "public_key": peer.public_key,
        "allowed_ips": peer.allowed_ips,
        "endpoint": peer.endpoint or "",
        "keepalive": peer.keepalive or 25,
        "enabled": peer.enabled,
        "device_type": peer.device_type,
        "tunnel_mode": peer.tunnel_mode
    }

@router.put("/peers/{peer_id}")
def update_peer(peer_id: int, data: PeerUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    peer = db.get(Peer, peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    old_name = peer.name

    if data.name is not None:
        clean_name = data.name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Peer name cannot be empty")
        peer.name = clean_name

    if data.allowed_ips is not None:
        clean_ip = data.allowed_ips.strip()
        if not clean_ip:
            raise HTTPException(status_code=400, detail="Allowed IPs cannot be empty")
        try:
            for item in clean_ip.split(","):
                ipaddress.ip_network(item.strip(), strict=False)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid IP address format: {e}")

        # Check for conflicts with other peers
        conflict = db.scalar(
            select(Peer).filter(
                Peer.interface_id == peer.interface_id,
                Peer.id != peer.id,
                Peer.allowed_ips == clean_ip
            )
        )
        if conflict:
            raise HTTPException(status_code=400, detail=f"IP '{clean_ip}' is already assigned to peer '{conflict.name}'")
        peer.allowed_ips = clean_ip

    if data.device_type is not None:
        peer.device_type = data.device_type.strip().lower()

    if data.tunnel_mode is not None:
        peer.tunnel_mode = data.tunnel_mode.strip().lower()

    if data.endpoint is not None:
        peer.endpoint = data.endpoint.strip() if data.endpoint else ""

    if data.keepalive is not None:
        peer.keepalive = max(0, min(3600, data.keepalive))

    if data.enabled is not None:
        peer.enabled = data.enabled

    db.commit()
    db.refresh(peer)

    # Sync changes to WireGuard server configuration and kernel
    iface = db.get(ServerInterface, peer.interface_id)
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
    sync_ok, sync_msg = WireGuardEngine.apply_syncconf(rendered, iface.name)
    log_audit(db, "admin", "UPDATE_PEER", f"Updated peer '{peer.name}' (formerly '{old_name}', ID: {peer.id}). Sync: {sync_msg}")

    return {
        "id": peer.id,
        "name": peer.name,
        "allowed_ips": peer.allowed_ips,
        "device_type": peer.device_type,
        "tunnel_mode": peer.tunnel_mode,
        "endpoint": peer.endpoint,
        "keepalive": peer.keepalive,
        "enabled": peer.enabled,
        "sync_status": sync_msg
    }

@router.delete("/peers/{peer_id}")
def delete_peer(peer_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    peer = db.get(Peer, peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    iface_id = peer.interface_id
    peer_name = peer.name
    db.delete(peer)
    db.commit()

    iface = db.get(ServerInterface, iface_id)
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
    sync_ok, sync_msg = WireGuardEngine.apply_syncconf(rendered, iface.name, allow_peer_removal=True)
    log_audit(db, "admin", "DELETE_PEER", f"Deleted peer '{peer_name}'. Sync: {sync_msg}")

    return {"message": f"Peer '{peer_name}' deleted.", "sync_status": sync_msg}

@router.get("/peers/{peer_id}/config")
def get_peer_config(peer_id: int, mode: Optional[str] = None, db: Session = Depends(get_db)):
    peer = db.get(Peer, peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    if not peer.private_key:
        raise HTTPException(
            status_code=400,
            detail="Private key was not generated on server. Configuration cannot be exported."
        )

    iface = db.get(ServerInterface, peer.interface_id)
    client_priv = decrypt_key(peer.private_key)
    psk_dec = decrypt_key(peer.psk) if peer.psk else None

    # Determine server endpoint to hand out to client
    endpoint = iface.endpoint
    if not endpoint:
        endpoint = "YOUR_SERVER_PUBLIC_IP"

    # Calculate allowed_ips_route based on split vs full tunnel
    tunnel_mode = (mode or getattr(peer, "tunnel_mode", "full") or "full").lower()
    if tunnel_mode == "split":
        try:
            net = ipaddress.ip_network(iface.address, strict=False)
            allowed_ips_route = str(net)
        except Exception:
            allowed_ips_route = "172.29.250.0/24"
    else:
        allowed_ips_route = "0.0.0.0/0, ::/0"

    client_conf = WireGuardEngine.render_client_config(
        client_private_key=client_priv,
        client_address=peer.allowed_ips,
        server_public_key=iface.public_key,
        server_endpoint=endpoint,
        server_port=iface.listen_port,
        dns=iface.dns.strip() if (iface.dns and iface.dns.strip()) else None,
        psk=psk_dec,
        mtu=iface.mtu or 1420,
        keepalive=peer.keepalive or 25,
        allowed_ips_route=allowed_ips_route
    )

    return {
        "peer_name": peer.name,
        "tunnel_mode": tunnel_mode,
        "allowed_ips_route": allowed_ips_route,
        "config": client_conf
    }

@router.get("/peers/{peer_id}/download")
def download_peer_config(peer_id: int, mode: Optional[str] = None, db: Session = Depends(get_db)):
    peer = db.get(Peer, peer_id)
    if not peer or not peer.private_key:
        raise HTTPException(status_code=404, detail="Configuration unavailable")

    data = get_peer_config(peer_id, mode=mode, db=db)
    filename = f"{peer.name.lower().replace(' ', '_')}.conf"
    return PlainTextResponse(
        content=data["config"],
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff"
        }
    )


@router.put("/server")
def update_server_settings(data: ServerUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        raise HTTPException(status_code=404, detail="Interface not found")

    iface.address = data.address.strip()
    iface.listen_port = data.listen_port
    iface.endpoint = data.endpoint.strip() if data.endpoint else ""
    iface.dns = data.dns.strip() if data.dns else ""
    iface.mtu = data.mtu
    iface.extra_directives = data.extra_directives.strip() if data.extra_directives else ""
    db.commit()

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
    sync_ok, sync_msg = WireGuardEngine.apply_syncconf(rendered, iface.name)
    log_audit(db, "admin", "UPDATE_SERVER", f"Updated server configuration and synced {iface.name}: {sync_msg}")
    return {"message": "Server settings saved and synchronized successfully"}

@router.post("/server/sync")
def sync_server_interface(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        raise HTTPException(status_code=404, detail="Interface not found")

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
    sync_ok, sync_msg = WireGuardEngine.apply_syncconf(rendered, iface.name)
    log_audit(db, "admin", "SYNC_SERVER", f"Manual sync executed: {sync_msg}")
    return {"success": sync_ok, "message": sync_msg}

def _ingest_parsed_config(parsed: dict, db: Session, iface: ServerInterface, source_label: str) -> dict:
    try:
        if_data = parsed.get("interface", {})
        if if_data.get("private_key") and is_wireguard_key(if_data["private_key"]):
            priv = if_data["private_key"]
            try:
                pub = if_data.get("public_key") or WireGuardEngine.public_key_from_private(priv)
                if pub:
                    iface.private_key = encrypt_key(priv)
                    iface.public_key = pub
            except Exception:
                pass
        if if_data.get("address") and if_data["address"].strip():
            iface.address = if_data["address"].strip()
        if if_data.get("listen_port") and str(if_data["listen_port"]).isdigit():
            iface.listen_port = int(if_data["listen_port"])
        if if_data.get("mtu") and str(if_data["mtu"]).isdigit():
            iface.mtu = int(if_data["mtu"])
        if if_data.get("endpoint"):
            iface.endpoint = if_data["endpoint"]
        if if_data.get("dns"):
            iface.dns = if_data["dns"]
        if if_data.get("extra_directives") and if_data["extra_directives"].strip():
            iface.extra_directives = if_data["extra_directives"].strip()

        existing_peers = db.scalars(select(Peer).filter_by(interface_id=iface.id)).all()
        # In-memory dictionary tracking peers by public key for instant deduplication
        peers_by_key = {p.public_key: p for p in existing_peers}
        occupied_ips = set(p.allowed_ips for p in existing_peers if p.allowed_ips)

        imported_count = 0
        updated_count = 0

        for p_data in parsed.get("peers", []):
            pub = p_data.get("public_key", "").strip()
            if not pub or not is_wireguard_key(pub):
                continue

            raw_ip = p_data.get("allowed_ips", "").strip()
            client_addr = p_data.get("client_address", "").strip()
            candidate_ip = raw_ip

            if candidate_ip in ["0.0.0.0/0", "0.0.0.0/0, ::/0", "::/0"] or not candidate_ip:
                if client_addr:
                    candidate_ip = client_addr
                else:
                    candidate_ip = IPAM.get_next_available_ip(iface.address, list(occupied_ips))

            if candidate_ip and "/" not in candidate_ip:
                candidate_ip = f"{candidate_ip}/32"

            if pub in peers_by_key:
                existing = peers_by_key[pub]
                if p_data.get("name") and not p_data["name"].startswith("Peer-"):
                    existing.name = p_data["name"]
                if candidate_ip and candidate_ip != "0.0.0.0/0":
                    existing.allowed_ips = candidate_ip
                if p_data.get("endpoint"):
                    existing.endpoint = p_data["endpoint"]
                if p_data.get("psk") and is_wireguard_key(p_data["psk"]):
                    existing.psk = encrypt_key(p_data["psk"])
                if p_data.get("client_private_key") and not existing.private_key:
                    existing.private_key = encrypt_key(p_data["client_private_key"])
                existing.enabled = True
                updated_count += 1
            else:
                if candidate_ip in occupied_ips:
                    auto_ip = IPAM.get_next_available_ip(iface.address, list(occupied_ips))
                    if auto_ip:
                        candidate_ip = auto_ip

                if candidate_ip:
                    occupied_ips.add(candidate_ip)

                client_priv_enc = None
                if p_data.get("client_private_key"):
                    client_priv_enc = encrypt_key(p_data["client_private_key"])

                new_peer = Peer(
                    interface_id=iface.id,
                    name=p_data.get("name") or f"Peer-{len(existing_peers) + imported_count + 1}",
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
                peers_by_key[pub] = new_peer
                imported_count += 1

        db.commit()

        # Resynchronize WireGuard kernel with all peers
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

        log_audit(db, "admin", "IMPORT_CONFIG", f"Imported {imported_count} new and updated {updated_count} peers from {source_label}. Sync: {sync_msg}")
        return {
            "success": True,
            "imported_new_peers": imported_count,
            "updated_peers": updated_count,
            "total_peers": len(all_peers),
            "sync_status": sync_msg,
            "message": f"Successfully imported {imported_count} new and updated {updated_count} peers from {source_label}. (WireGuard synced: {sync_msg})"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Configuration import failed: {str(e)}")

@router.post("/server/auto-import")
def auto_import_endpoint(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """
    Unified auto-import:
    Scans /etc/wireguard/wg0.conf, all backup snapshots (.bak.*), other .conf files,
    and active Linux kernel memory (wg show wg0 dump).
    Adopts server interface keys & settings and upserts all unique peers with zero downtime.
    """
    res = auto_import_database(db)
    log_audit(db, "admin", "AUTO_IMPORT", res.get("message", "Auto-import executed"))
    return res

@router.post("/server/import")
def import_host_configuration(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Unified auto-import endpoint (backward compatible)."""
    return auto_import_endpoint(db, current_user=current_user)

@router.post("/server/import-kernel")
def import_kernel_configuration(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Unified auto-import endpoint (backward compatible)."""
    return auto_import_endpoint(db, current_user=current_user)

@router.post("/server/import-text")
def import_text_configuration(body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Imports peers from raw text content (supports .conf INI format or JSON format)."""
    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Configuration text is empty.")

    parsed = WireGuardEngine.parse_config_text(content)
    if not parsed or not parsed.get("peers"):
        raise HTTPException(status_code=400, detail="Could not parse any peers from the provided text. Ensure format is valid WireGuard .conf or .json.")

    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    if not iface:
        raise HTTPException(status_code=404, detail="Interface not initialized.")

    return _ingest_parsed_config(parsed, db, iface, "Custom Text/JSON Input")

@router.post("/peers/import")
def import_peers_endpoint(body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return import_text_configuration(body, db, current_user=current_user)


