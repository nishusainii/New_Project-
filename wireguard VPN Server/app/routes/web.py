from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from pathlib import Path

from app.core.config import WG_INTERFACE, WG_EXECUTION_MODE
from app.core.security import (
    verify_password,
    generate_csrf_token,
    validate_csrf,
    decrypt_key,
    encrypt_key,
)
from app.core.ipam import IPAM
from app.core.wireguard import WireGuardEngine
from app.core.nftables import NFTablesEngine
from app.models.database import (
    get_db,
    User,
    ServerInterface,
    Peer,
    AuditLog,
    WireGuardPolicy,
    WireGuardAcl,
    NftCustomRule,
    log_audit,
)

router = APIRouter(include_in_schema=False)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

def get_current_user_web(request: Request, db: Session = Depends(get_db)) -> User:
    uid = request.session.get("uid")
    if not uid:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})
    user = db.get(User, uid)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})
    return user

def _get_dashboard_context(request: Request, user: User, db: Session) -> dict:
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    peers = db.scalars(select(Peer).filter_by(interface_id=iface.id).order_by(Peer.id.desc())).all() if iface else []
    audits = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(30)).all()

    # Get live statistics from wg dump
    live_stats = WireGuardEngine.get_live_peer_stats(iface.name if iface else WG_INTERFACE)

    # Next suggested IP address for the modal
    existing_ips = [p.allowed_ips for p in peers]
    next_ip = IPAM.get_next_available_ip(iface.address if iface else "172.29.250.1/24", existing_ips) or "172.29.250.11/32"


    peer_data = []
    active_peers_count = 0
    total_rx = 0
    total_tx = 0

    for p in peers:
        stat = live_stats.get(p.public_key, {})
        is_active = stat.get("is_active", False)
        if is_active:
            active_peers_count += 1
        rx = stat.get("transfer_rx", 0)
        tx = stat.get("transfer_tx", 0)
        total_rx += rx
        total_tx += tx

        peer_data.append({
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
            "created_at": p.created_at.strftime("%Y-%m-%d %H:%M") if p.created_at else "",
            "is_active": is_active,
            "handshake": stat.get("handshake_readable", "Never"),
            "rx": stat.get("transfer_rx_readable", "0 B"),
            "tx": stat.get("transfer_tx_readable", "0 B"),
        })

    subnet_matrix = IPAM.get_subnet_matrix(iface.address if iface else "172.29.250.1/24", peer_data)

    csrf = generate_csrf_token()
    request.session["csrf"] = csrf

    policy = db.scalar(select(WireGuardPolicy).limit(1))
    if not policy:
        policy = WireGuardPolicy()
        db.add(policy)
        db.commit()

    db_acls = db.scalars(select(WireGuardAcl).order_by(WireGuardAcl.id.desc())).all()
    acls_data = []
    for a in db_acls:
        peer_name = "All Peers"
        effective_src = a.src_cidr
        if a.peer_id:
            peer = db.get(Peer, a.peer_id)
            if peer:
                peer_name = peer.name
                effective_src = peer.allowed_ips
        acls_data.append({
            "id": a.id,
            "name": a.name,
            "peer_name": peer_name,
            "src_cidr": effective_src or "All",
            "dst_cidr": a.dst_cidr,
            "proto": a.proto.upper(),
            "ports": a.ports or "Any",
            "action": a.action.upper(),
            "enabled": a.enabled,
        })

    custom_rules = db.scalars(select(NftCustomRule).order_by(NftCustomRule.id.desc())).all()
    active_ruleset = NFTablesEngine.get_active_ruleset_text()
    acl_file = NFTablesEngine.get_acl_file_info()
    conf_file = NFTablesEngine.get_conf_file_info()
    ruleset_info = NFTablesEngine.get_ruleset()
    fw_stats = ruleset_info.get("stats", {})
    fw_caps = NFTablesEngine.capabilities()
    fw_tables = ruleset_info.get("tables", [])
    fw_disabled = ruleset_info.get("disabled", [])
    fw_backups = NFTablesEngine.list_backups()

    return {
        "request": request,
        "user": user,
        "iface": iface,
        "peers": peer_data,
        "raw_peers": peers,
        "audits": audits,
        "next_ip": next_ip,
        "total_peers": len(peers),
        "enabled_peers": sum(1 for p in peers if p.enabled),
        "active_peers": active_peers_count,
        "total_rx": WireGuardEngine.format_bytes(total_rx),
        "total_tx": WireGuardEngine.format_bytes(total_tx),
        "mode": WG_EXECUTION_MODE,
        "csrf": csrf,
        "policy": policy,
        "acls": acls_data,
        "acls_count": len(acls_data),
        "custom_rules": custom_rules,
        "active_ruleset": active_ruleset,
        "acl_file": acl_file,
        "conf_file": conf_file,
        "nft_available": NFTablesEngine.is_nft_available(),
        "subnet_matrix": subnet_matrix,
        "fw_stats": fw_stats,
        "fw_caps": fw_caps,
        "fw_tables": fw_tables,
        "fw_disabled": fw_disabled,
        "fw_backups_count": len(fw_backups),
    }

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("uid"):
        return RedirectResponse(url="/", status_code=303)
    csrf = generate_csrf_token()
    request.session["csrf"] = csrf
    return templates.TemplateResponse("login.html", {"request": request, "csrf": csrf, "error": None})

@router.post("/login", response_class=HTMLResponse)
def handle_login(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(""),
    db: Session = Depends(get_db)
):
    clean_username = (username or "").strip().lower()
    clean_password = (password or "").strip()

    # Normalize lookup: case-insensitive match
    user = db.scalar(select(User).filter(func.lower(User.username) == clean_username)) if clean_username else None
    valid_auth = False
    if user:
        if verify_password(user.password_hash, password) or (clean_password and verify_password(user.password_hash, clean_password)):
            valid_auth = True

    if not valid_auth or not user:
        new_csrf = generate_csrf_token()
        request.session["csrf"] = new_csrf
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "csrf": new_csrf, "error": "Invalid username or password."}
        )

    # Authentication successful
    request.session.clear()
    request.session["uid"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
    request.session["csrf"] = generate_csrf_token()
    log_audit(db, user.username, "LOGIN", f"User {user.username} logged in.")
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
def handle_logout(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("username", "Unknown")
    log_audit(db, username, "LOGOUT", "User logged out.")
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# ==================== DEDICATED SEPARATE PAGE ROUTES ====================

@router.get("/", response_class=HTMLResponse)
@router.get("/overview", response_class=HTMLResponse)
def overview_page(
    request: Request,
    user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    ctx = _get_dashboard_context(request, user, db)
    ctx["active_page"] = "overview"
    return templates.TemplateResponse("overview.html", ctx)

@router.get("/peers", response_class=HTMLResponse)
def peers_page(
    request: Request,
    user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    ctx = _get_dashboard_context(request, user, db)
    ctx["active_page"] = "peers"
    return templates.TemplateResponse("peers.html", ctx)

@router.get("/firewall", response_class=HTMLResponse)
def firewall_page(
    request: Request,
    user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    ctx = _get_dashboard_context(request, user, db)
    ctx["active_page"] = "firewall"
    return templates.TemplateResponse("firewall.html", ctx)

@router.get("/server", response_class=HTMLResponse)
def server_page(
    request: Request,
    user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    ctx = _get_dashboard_context(request, user, db)
    ctx["active_page"] = "server"
    return templates.TemplateResponse("server.html", ctx)
