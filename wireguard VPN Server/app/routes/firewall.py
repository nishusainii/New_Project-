from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional

from app.core.config import WG_INTERFACE
from app.core.nftables import NFTablesEngine, validate_rule_text, DisabledRuleStore
from app.models.database import (
    get_db,
    ServerInterface,
    Peer,
    WireGuardPolicy,
    WireGuardAcl,
    NftCustomRule,
    User,
    log_audit,
)
from app.routes.api import require_admin
from app.schemas import (
    FirewallPolicyUpdate,
    WireGuardAclCreate,
    CustomRuleCreate,
    ValidateConfigInput,
)

router = APIRouter(prefix="/api/firewall", tags=["Firewall & ACLs"])

def _compile_and_apply_current(db: Session, actor: str = "admin") -> tuple[bool, str]:
    """Helper to recompile all active policies, ACLs, and custom rules, and apply them."""
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    subnet = iface.address if iface else "10.8.0.0/24"

    policy = db.scalar(select(WireGuardPolicy).limit(1))
    if not policy:
        policy = WireGuardPolicy()
        db.add(policy)
        db.commit()

    acls = db.scalars(select(WireGuardAcl)).all()
    custom_rules = db.scalars(select(NftCustomRule)).all()

    # Format ACL dicts
    acl_dicts = []
    for a in acls:
        src = a.src_cidr
        if (not src or src == "any") and a.peer_id:
            peer = db.get(Peer, a.peer_id)
            if peer:
                src = peer.allowed_ips
        acl_dicts.append({
            "name": a.name,
            "src_cidr": src,
            "dst_cidr": a.dst_cidr,
            "proto": a.proto,
            "ports": a.ports,
            "action": a.action,
            "enabled": a.enabled
        })

    # Format Custom Rule dicts
    custom_dicts = [{
        "family": r.family,
        "table": r.table,
        "chain": r.chain,
        "statement": r.statement,
        "comment": r.comment,
        "enabled": r.enabled
    } for r in custom_rules]

    candidate = NFTablesEngine.compile_ruleset(
        server_subnet=subnet,
        interface=iface.name if iface else "wg0",
        client_isolation=policy.client_isolation,
        internet_access=policy.internet_access,
        allow_dns=policy.allow_dns,
        default_forward_policy=policy.default_forward_policy,
        acls=acl_dicts,
        custom_rules=custom_dicts,
        mss_clamping=getattr(policy, "mss_clamping", True),
        drop_invalid=getattr(policy, "drop_invalid", True),
        icmp_limit=getattr(policy, "icmp_limit", True),
        log_dropped=getattr(policy, "log_dropped", False)
    )

    success, msg = NFTablesEngine.apply_ruleset(candidate)
    log_audit(db, actor, "APPLY_FIREWALL", f"Ruleset apply: {msg}")
    return success, msg

@router.get("/status")
def get_firewall_status(db: Session = Depends(get_db)):
    policy = db.scalar(select(WireGuardPolicy).limit(1))
    if not policy:
        policy = WireGuardPolicy()
        db.add(policy)
        db.commit()

    acls_count = len(db.scalars(select(WireGuardAcl)).all())
    custom_count = len(db.scalars(select(NftCustomRule)).all())
    ruleset = NFTablesEngine.get_ruleset()
    caps = NFTablesEngine.capabilities()
    backups = NFTablesEngine.list_backups()

    return {
        "nft_available": caps.get("nft", False),
        "caps": caps,
        "stats": ruleset.get("stats", {}),
        "tables": ruleset.get("tables", []),
        "disabled_rules": len(ruleset.get("disabled", [])),
        "backups": len(backups),
        "policy": {
            "client_isolation": policy.client_isolation,
            "internet_access": policy.internet_access,
            "allow_dns": policy.allow_dns,
            "default_forward_policy": policy.default_forward_policy,
            "mss_clamping": getattr(policy, "mss_clamping", True),
            "drop_invalid": getattr(policy, "drop_invalid", True),
            "icmp_limit": getattr(policy, "icmp_limit", True),
            "log_dropped": getattr(policy, "log_dropped", False),
            "auto_backup": getattr(policy, "auto_backup", True)
        },
        "total_acls": acls_count,
        "total_custom_rules": custom_count,
        "active_ruleset": ruleset.get("raw", "")
    }

@router.get("/ruleset")
def get_firewall_ruleset():
    return NFTablesEngine.get_ruleset()

@router.get("/raw")
def get_firewall_raw():
    text, sim = NFTablesEngine.raw_ruleset()
    return {"raw": text, "simulated": sim}

@router.get("/backups")
def get_firewall_backups():
    return {"backups": NFTablesEngine.list_backups()}

@router.post("/backups")
def post_firewall_backup(db: Session = Depends(get_db)):
    res = NFTablesEngine.create_backup(prefix="manual")
    log_audit(db, "admin", "CREATE_FIREWALL_BACKUP", f"Created backup {res.get('name')}")
    return res

@router.post("/backups/restore")
def restore_firewall_backup(body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Missing backup name")
    try:
        res = NFTablesEngine.restore_backup(name)
        log_audit(db, current_user.username, "RESTORE_FIREWALL_BACKUP", f"Restored backup {name}")
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rules/validate")
def validate_rule(body: dict):
    text = body.get("rule") or body.get("statement") or ""
    family = body.get("family") or "inet"
    table = body.get("table") or "wiregate"
    chain = body.get("chain") or "wg_forward"
    try:
        return validate_rule_text(text, family, table, chain, semantic=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/rules/toggle")
def toggle_rule(body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    action = body.get("action")  # 'disable' or 'enable'
    rule_id = str(body.get("id"))
    store = DisabledRuleStore()
    if action == "enable":
        store.pop(rule_id)
        log_audit(db, current_user.username, "ENABLE_RULE", f"Re-enabled parked rule {rule_id}")
        return {"ok": True, "action": "enable", "id": rule_id}
    else:
        store.add({
            "id": rule_id,
            "family": body.get("family", "inet"),
            "table": body.get("table", "wiregate"),
            "chain": body.get("chain", "wg_forward"),
            "text": body.get("text", "")
        }, current_user.username)
        log_audit(db, current_user.username, "DISABLE_RULE", f"Parked rule {rule_id}")
        return {"ok": True, "action": "disable", "id": rule_id}

@router.post("/disabled/forget")
def forget_disabled_rule(body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    rule_id = str(body.get("id"))
    store = DisabledRuleStore()
    store.pop(rule_id)
    log_audit(db, current_user.username, "FORGET_DISABLED_RULE", f"Forgot parked rule {rule_id}")
    return {"ok": True, "id": rule_id}

@router.get("/file")
def get_conf_file(target: str = "conf"):
    """Get the current file information (defaults to target='conf' for /etc/nftables.conf)."""
    if target == "acl":
        return NFTablesEngine.get_acl_file_info()
    return NFTablesEngine.get_conf_file_info()

@router.get("/files")
def get_both_files():
    """Get main /etc/nftables.conf and /etc/nftables/acl.nft file information."""
    return {
        "conf": NFTablesEngine.get_conf_file_info(),
        "acl": NFTablesEngine.get_acl_file_info()
    }

@router.post("/file")
def save_firewall_file(body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Save changes to /etc/nftables.conf."""
    content = body.get("content", "")
    target = body.get("target", "conf")
    if target == "acl":
        ok, msg = NFTablesEngine.save_acl_file(content)
        action_name = "SAVE_ACL_FILE"
    else:
        ok, msg = NFTablesEngine.save_conf_file(content)
        action_name = "SAVE_CONF_FILE"
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    log_audit(db, current_user.username, action_name, msg)
    return {"success": True, "message": msg}

@router.post("/link-conf")
def link_conf(db: Session = Depends(get_db)):
    """Validates /etc/nftables.conf configuration."""
    is_valid, msg = NFTablesEngine.validate_ruleset_file(target="conf")
    return {"success": is_valid, "message": msg}

@router.post("/validate")
def validate_ruleset_endpoint(body: dict = None):
    """Validate syntax of current or proposed ruleset with `nft -c -f`."""
    content = None
    target = "conf"
    if body:
        content = body.get("content") or body.get("config")
        target = body.get("target", "conf")
    is_valid, msg = NFTablesEngine.validate_ruleset_file(content, target=target)
    return {"is_valid": is_valid, "message": msg}

@router.post("/reload")
def reload_firewall(body: dict = None, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Validate, save, and safely reload ruleset into kernel with `nft -f`."""
    content = body.get("content") if body else None
    target = body.get("target", "conf") if body else "conf"
    success, msg = NFTablesEngine.reload_ruleset_file(content, target=target)
    if not success:
        log_audit(db, "admin", "RELOAD_FIREWALL_FAIL", f"Reload failed: {msg}")
        raise HTTPException(status_code=400, detail=msg)
    log_audit(db, "admin", "RELOAD_FIREWALL_SUCCESS", msg)
    return {"success": True, "message": msg}

@router.get("/preview")
def preview_ruleset(db: Session = Depends(get_db)):
    iface = db.scalar(select(ServerInterface).filter_by(name=WG_INTERFACE))
    subnet = iface.address if iface else "10.8.0.0/24"
    policy = db.scalar(select(WireGuardPolicy).limit(1)) or WireGuardPolicy()
    acls = db.scalars(select(WireGuardAcl)).all()
    custom_rules = db.scalars(select(NftCustomRule)).all()

    acl_dicts = []
    for a in acls:
        src = a.src_cidr
        if (not src or src == "any") and a.peer_id:
            peer = db.get(Peer, a.peer_id)
            if peer:
                src = peer.allowed_ips
        acl_dicts.append({
            "name": a.name,
            "src_cidr": src,
            "dst_cidr": a.dst_cidr,
            "proto": a.proto,
            "ports": a.ports,
            "action": a.action,
            "enabled": a.enabled
        })

    custom_dicts = [{
        "chain": r.chain,
        "statement": r.statement,
        "comment": r.comment,
        "enabled": r.enabled
    } for r in custom_rules]

    rendered = NFTablesEngine.compile_ruleset(
        server_subnet=subnet,
        interface=iface.name if iface else "wg0",
        client_isolation=policy.client_isolation,
        internet_access=policy.internet_access,
        allow_dns=policy.allow_dns,
        default_forward_policy=policy.default_forward_policy,
        acls=acl_dicts,
        custom_rules=custom_dicts,
        mss_clamping=getattr(policy, "mss_clamping", True),
        drop_invalid=getattr(policy, "drop_invalid", True),
        icmp_limit=getattr(policy, "icmp_limit", True),
        log_dropped=getattr(policy, "log_dropped", False)
    )

    is_valid, val_msg = NFTablesEngine.validate_ruleset(rendered)
    return {
        "candidate": rendered,
        "is_valid": is_valid,
        "validation_message": val_msg
    }

@router.post("/apply")
def apply_firewall(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    success, msg = _compile_and_apply_current(db, actor=current_user.username)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"success": True, "message": msg}


@router.post("/policy")
def update_policy(data: FirewallPolicyUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    policy = db.scalar(select(WireGuardPolicy).limit(1))
    if not policy:
        policy = WireGuardPolicy()
        db.add(policy)

    policy.client_isolation = data.client_isolation
    policy.internet_access = data.internet_access
    policy.allow_dns = data.allow_dns
    policy.default_forward_policy = data.default_forward_policy.lower()
    if data.mss_clamping is not None:
        policy.mss_clamping = data.mss_clamping
    if data.drop_invalid is not None:
        policy.drop_invalid = data.drop_invalid
    if data.icmp_limit is not None:
        policy.icmp_limit = data.icmp_limit
    if data.log_dropped is not None:
        policy.log_dropped = data.log_dropped
    if data.auto_backup is not None:
        policy.auto_backup = data.auto_backup
    db.commit()

    if getattr(policy, "auto_backup", True):
        try:
            NFTablesEngine.create_backup(prefix="pre_policy_update")
        except Exception:
            pass

    success, msg = _compile_and_apply_current(db, actor=current_user.username)
    log_audit(db, current_user.username, "UPDATE_FIREWALL_POLICY", f"Updated policy: forward={policy.default_forward_policy}, isolation={policy.client_isolation}")
    return {"success": success, "message": f"Policies updated. Apply: {msg}"}

@router.post("/lockdown")
def emergency_lockdown(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Emergency killswitch: drops all forwarded traffic across WireGuard interface immediately."""
    policy = db.scalar(select(WireGuardPolicy).limit(1))
    if not policy:
        policy = WireGuardPolicy()
        db.add(policy)

    try:
        NFTablesEngine.create_backup(prefix="pre_lockdown")
    except Exception:
        pass

    policy.default_forward_policy = "drop"
    policy.client_isolation = True
    policy.internet_access = False
    policy.log_dropped = True
    db.commit()

    success, msg = _compile_and_apply_current(db, actor="EMERGENCY_LOCKDOWN")
    log_audit(db, current_user.username, "EMERGENCY_LOCKDOWN", "Emergency killswitch triggered: all forward traffic dropped")
    return {"success": success, "message": f"Emergency Lockdown Activated! {msg}"}

@router.get("/acls")
def list_acls(db: Session = Depends(get_db)):
    acls = db.scalars(select(WireGuardAcl).order_by(WireGuardAcl.id.desc())).all()
    res = []
    for a in acls:
        peer_name = "All Peers"
        effective_src = a.src_cidr
        if a.peer_id:
            peer = db.get(Peer, a.peer_id)
            if peer:
                peer_name = peer.name
                effective_src = peer.allowed_ips

        res.append({
            "id": a.id,
            "peer_id": a.peer_id,
            "peer_name": peer_name,
            "name": a.name,
            "src_cidr": effective_src or "All",
            "dst_cidr": a.dst_cidr,
            "proto": a.proto,
            "ports": a.ports or "Any",
            "action": a.action,
            "enabled": a.enabled,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else None
        })
    return res

@router.post("/acls", status_code=status.HTTP_201_CREATED)
def create_acl(data: WireGuardAclCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    src_ip = data.src_cidr
    if data.peer_id:
        peer = db.get(Peer, data.peer_id)
        if not peer:
            raise HTTPException(status_code=404, detail="Target peer not found")
        if not src_ip:
            src_ip = peer.allowed_ips

    acl = WireGuardAcl(
        peer_id=data.peer_id,
        name=data.name.strip(),
        src_cidr=src_ip.strip() if src_ip else "",
        dst_cidr=data.dst_cidr.strip() if data.dst_cidr else "any",
        proto=data.proto.lower().strip(),
        ports=data.ports.strip() if data.ports else None,
        action=data.action.lower().strip(),
        enabled=True
    )
    db.add(acl)
    db.commit()
    db.refresh(acl)

    # Auto-compile and apply safely
    success, msg = _compile_and_apply_current(db, actor=current_user.username)
    log_audit(db, current_user.username, "CREATE_ACL", f"Created ACL '{acl.name}'. Apply: {msg}")

    return {
        "id": acl.id,
        "name": acl.name,
        "apply_status": msg
    }

@router.post("/acls/{acl_id}/toggle")
def toggle_acl(acl_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    acl = db.get(WireGuardAcl, acl_id)
    if not acl:
        raise HTTPException(status_code=404, detail="ACL not found")

    acl.enabled = not acl.enabled
    db.commit()

    success, msg = _compile_and_apply_current(db, actor=current_user.username)
    state_str = "enabled" if acl.enabled else "disabled"
    log_audit(db, current_user.username, "TOGGLE_ACL", f"ACL '{acl.name}' {state_str}. Apply: {msg}")

    return {"id": acl.id, "enabled": acl.enabled, "apply_status": msg}

@router.delete("/acls/{acl_id}")
def delete_acl(acl_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    acl = db.get(WireGuardAcl, acl_id)
    if not acl:
        raise HTTPException(status_code=404, detail="ACL not found")

    name = acl.name
    db.delete(acl)
    db.commit()

    success, msg = _compile_and_apply_current(db, actor=current_user.username)
    log_audit(db, current_user.username, "DELETE_ACL", f"Deleted ACL '{name}'. Apply: {msg}")

    return {"message": f"ACL '{name}' deleted.", "apply_status": msg}

@router.get("/custom-rules")
def list_custom_rules(db: Session = Depends(get_db)):
    rules = db.scalars(select(NftCustomRule).order_by(NftCustomRule.id.desc())).all()
    return [{
        "id": r.id,
        "family": r.family,
        "table": r.table,
        "chain": r.chain,
        "statement": r.statement,
        "comment": r.comment,
        "enabled": r.enabled,
        "created_at": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else None
    } for r in rules]

@router.post("/custom-rules", status_code=status.HTTP_201_CREATED)
def create_custom_rule(data: CustomRuleCreate, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    # Test syntax before saving with proper NFT block newlines
    clean_stmt = data.statement.strip().rstrip(";")
    candidate_test = f"table {data.family} {data.table} {{\n    chain {data.chain} {{\n        {clean_stmt}\n    }}\n}}"
    is_valid, msg = NFTablesEngine.validate_ruleset(candidate_test)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid rule syntax: {msg}")

    rule = NftCustomRule(
        family=data.family,
        table=data.table,
        chain=data.chain,
        statement=data.statement.strip(),
        comment=data.comment.strip() if data.comment else None,
        enabled=True
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)

    success, msg = _compile_and_apply_current(db, actor=current_user.username)
    log_audit(db, current_user.username, "CREATE_NFT_RULE", f"Created custom NFT rule: {rule.statement}. Apply: {msg}")

    return {"id": rule.id, "statement": rule.statement, "apply_status": msg}

@router.delete("/custom-rules/{rule_id}")
def delete_custom_rule(rule_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    rule = db.get(NftCustomRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    stmt = rule.statement
    db.delete(rule)
    db.commit()

    success, msg = _compile_and_apply_current(db, actor=current_user.username)
    log_audit(db, current_user.username, "DELETE_NFT_RULE", f"Deleted custom rule: {stmt}. Apply: {msg}")

    return {"message": "Custom rule deleted.", "apply_status": msg}

@router.delete("/raw-rule/{family}/{table}/{chain}/{handle}")
def delete_raw_rule_handle(family: str, table: str, chain: str, handle: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    success, msg = NFTablesEngine.delete_rule_by_handle(family, table, chain, handle)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    log_audit(db, current_user.username, "DELETE_RAW_RULE", f"Deleted rule handle {handle} from {family}/{table}/{chain}")
    return {"message": msg}

@router.put("/raw-rule/{family}/{table}/{chain}/{handle}")
def update_raw_rule_handle(family: str, table: str, chain: str, handle: int, body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    statement = (body.get("statement") or "").strip()
    if not statement:
        raise HTTPException(status_code=400, detail="Statement is required")
    success, msg = NFTablesEngine.replace_rule_by_handle(family, table, chain, handle, statement)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    log_audit(db, current_user.username, "UPDATE_RAW_RULE", f"Updated rule handle {handle} in {family}/{table}/{chain}: {statement}")
    return {"message": msg}

@router.post("/chain-rule")
def add_chain_rule(body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    family = body.get("family", "inet")
    table = body.get("table", "filter")
    chain = body.get("chain", "input")
    statement = (body.get("statement") or "").strip()
    if not statement:
        raise HTTPException(status_code=400, detail="Statement is required")
    success, msg = NFTablesEngine.add_rule_to_chain(family, table, chain, statement)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    log_audit(db, current_user.username, "ADD_CHAIN_RULE", f"Added rule to {family}/{table}/{chain}: {statement}")
    return {"success": True, "message": msg}

@router.post("/import-kernel")
def import_kernel_firewall_rules(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Extracts live rules from kernel and merges them into /etc/nftables.conf."""
    ok, msg, rules = NFTablesEngine.import_kernel_rules()
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    if not rules:
        return {"success": True, "count": 0, "message": "No extra client rules found in kernel to import."}

    rule_lines = [r["statement"] for r in rules]
    merge_ok, merge_msg = NFTablesEngine.merge_rules_into_conf_file("\n".join(rule_lines))
    if not merge_ok:
        raise HTTPException(status_code=400, detail=merge_msg)

    log_audit(db, current_user.username, "IMPORT_KERNEL_RULES", f"Imported {len(rules)} rules from kernel into /etc/nftables.conf")
    return {
        "success": True,
        "count": len(rules),
        "rules": rules,
        "message": f"Successfully imported {len(rules)} rules from live kernel into /etc/nftables.conf."
    }

@router.post("/import-text")
def import_text_firewall_rules(body: dict, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    """Validates and merges user-pasted rules into /etc/nftables.conf or /etc/nftables/acl.nft."""
    rules_text = body.get("rules") or body.get("content") or ""
    target = body.get("target", "conf")
    if not rules_text.strip():
        raise HTTPException(status_code=400, detail="Rules text is empty.")

    if target == "acl":
        merge_ok, merge_msg = NFTablesEngine.merge_rules_into_acl_file(rules_text)
        target_name = "/etc/nftables/acl.nft"
    else:
        merge_ok, merge_msg = NFTablesEngine.merge_rules_into_conf_file(rules_text)
        target_name = "/etc/nftables.conf"

    if not merge_ok:
        raise HTTPException(status_code=400, detail=merge_msg)

    log_audit(db, "admin", "IMPORT_TEXT_RULES", f"Imported custom rules into {target_name}")
    return {
        "success": True,
        "message": merge_msg
    }

@router.get("/backups/files")
def list_firewall_disk_backups():
    """Lists on-disk .bak files created during mutations."""
    import glob
    import os
    baks = []
    for pattern in ["/etc/nftables/acl.nft.bak*", "/etc/nftables.conf.bak*"]:
        for p in glob.glob(pattern):
            try:
                st = os.stat(p)
                baks.append({
                    "path": p,
                    "filename": os.path.basename(p),
                    "size": st.st_size,
                    "mtime": st.st_mtime
                })
            except Exception:
                pass
    return {"disk_backups": sorted(baks, key=lambda x: x["mtime"], reverse=True)}

