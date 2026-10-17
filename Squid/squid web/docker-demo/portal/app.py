#!/usr/bin/env python3
# ==============================================================================
# Innspark Solutions - Unified Squid & LDAP Web Management Portal
# Backend API & Controller
# ==============================================================================

import os
import sys
import subprocess
import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Import local configuration
import config

try:
    from ldap3 import Server, Connection, ALL, MODIFY_ADD, MODIFY_DELETE, SUBTREE
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    print("[WARNING] ldap3 module is not installed. Install with: pip install ldap3", file=sys.stderr)

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(
    days=getattr(config, "PERMANENT_SESSION_LIFETIME_DAYS", 7)
)

# ------------------------------------------------------------------------------
# Helper Functions: LDAP Connection & Authentication
# ------------------------------------------------------------------------------
def get_ldap_connection(admin=False):
    """Establishes an LDAP connection using admin or bind credentials."""
    if not LDAP_AVAILABLE:
        raise RuntimeError("ldap3 Python package is not installed.")
    
    server = Server(
        config.LDAP_HOST,
        port=config.LDAP_PORT,
        use_ssl=config.LDAP_USE_SSL,
        get_info=ALL,
        connect_timeout=3
    )
    user_dn = config.ADMIN_DN if admin else config.BIND_DN
    password = config.ADMIN_PASSWORD if admin else config.BIND_PASSWORD
    
    conn = Connection(server, user=user_dn, password=password, auto_bind=True)
    return conn

def authenticate_user(username, password):
    """
    Authenticates a user against OpenLDAP or administrative credentials.
    Returns (True, user_dict) on success, or (False, error_str) on failure.
    """
    if not username or not password:
        return False, "Username and password are required."

    u = username.strip()

    # 1. Administrator Account Check
    if u.lower() in ("admin", "administrator", "cn=admin"):
        # Attempt direct LDAP bind using ADMIN_DN
        if LDAP_AVAILABLE:
            try:
                server = Server(
                    config.LDAP_HOST,
                    port=config.LDAP_PORT,
                    use_ssl=config.LDAP_USE_SSL,
                    get_info=ALL,
                    connect_timeout=3
                )
                conn = Connection(server, user=config.ADMIN_DN, password=password, auto_bind=True)
                if conn.bound:
                    conn.unbind()
                    return True, {
                        "username": "admin",
                        "display_name": "System Administrator",
                        "role": "Administrator",
                        "is_admin": True
                    }
            except Exception:
                pass

        # Fallback check against configured ADMIN_PASSWORD
        if password == config.ADMIN_PASSWORD:
            return True, {
                "username": "admin",
                "display_name": "System Administrator",
                "role": "Administrator",
                "is_admin": True
            }
        return False, "Invalid administrator password."

    # 2. Standard LDAP User Authentication
    if not LDAP_AVAILABLE:
        return False, "LDAP authentication module (ldap3) is not installed."

    try:
        bind_conn = get_ldap_connection(admin=False)
        user_filter = f"(&(objectClass=inetOrgPerson)(uid={u}))"
        bind_conn.search(
            search_base=config.USER_OU,
            search_filter=user_filter,
            search_scope=SUBTREE,
            attributes=["cn", "displayName", "mail", "uid"]
        )

        target_dn = None
        display_name = u
        if bind_conn.entries:
            entry = bind_conn.entries[0]
            target_dn = entry.entry_dn
            if hasattr(entry, "displayName") and entry.displayName.value:
                display_name = str(entry.displayName.value)
            elif hasattr(entry, "cn") and entry.cn.value:
                display_name = str(entry.cn.value)
        else:
            target_dn = f"uid={u},{config.USER_OU}"

        # Check membership in proxy_admins group
        is_admin_user = False
        try:
            admin_group_filter = f"(&(objectClass=groupOfNames)(cn=proxy_admins)(member={target_dn}))"
            bind_conn.search(
                search_base=config.GROUP_OU,
                search_filter=admin_group_filter,
                search_scope=SUBTREE,
                attributes=["cn"]
            )
            if bind_conn.entries:
                is_admin_user = True
            else:
                # Also check posixGroup memberUid format
                bind_conn.search(
                    search_base=config.GROUP_OU,
                    search_filter=f"(&(objectClass=posixGroup)(cn=proxy_admins)(memberUid={u}))",
                    search_scope=SUBTREE,
                    attributes=["cn"]
                )
                if bind_conn.entries:
                    is_admin_user = True
        except Exception:
            pass

        bind_conn.unbind()

        # Attempt user bind with user's DN & entered password
        server = Server(
            config.LDAP_HOST,
            port=config.LDAP_PORT,
            use_ssl=config.LDAP_USE_SSL,
            get_info=ALL,
            connect_timeout=3
        )
        user_conn = Connection(server, user=target_dn, password=password, auto_bind=True)
        if user_conn.bound:
            user_conn.unbind()
            return True, {
                "username": u,
                "display_name": display_name,
                "role": "Administrator" if is_admin_user else "Proxy User",
                "is_admin": is_admin_user
            }
        else:
            return False, "Invalid LDAP username or password."
    except Exception as e:
        err_str = str(e)
        if "invalidCredentials" in err_str or "Invalid credentials" in err_str:
            return False, "Invalid LDAP username or password."
        return False, f"LDAP authentication failed: {err_str}"

# ------------------------------------------------------------------------------
# Authentication Decorator
# ------------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required", "redirect": "/login"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# ------------------------------------------------------------------------------
# Helper Functions: Squid & System Management
# ------------------------------------------------------------------------------
def get_squid_status():
    """Checks whether the Squid proxy service is currently running."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", 3128), timeout=1):
            return {"active": True, "status": "active (port 3128 listening)"}
    except Exception:
        pass
    try:
        res = subprocess.run(
            ["systemctl", "is-active", "squid"],
            capture_output=True,
            text=True,
            timeout=2
        )
        status_text = res.stdout.strip()
        if status_text == "active":
            return {"active": True, "status": "active"}
    except Exception:
        pass
    return {"active": False, "status": "inactive"}

def reload_squid_service():
    """Safely triggers a Squid reconfigure with configuration syntax test."""
    # Test squid config syntax first if squid binary is available
    test_res = subprocess.run(["squid", "-k", "parse"], capture_output=True, text=True)
    if test_res.returncode != 0:
        return False, f"Squid configuration parse error: {test_res.stderr.strip()}"
    
    # Trigger reload
    reload_res = subprocess.run(["squid", "-k", "reconfigure"], capture_output=True, text=True)
    if reload_res.returncode == 0:
        return True, "Squid configuration reloaded successfully."
    else:
        # Fallback to systemctl reload
        sys_res = subprocess.run(["systemctl", "reload", "squid"], capture_output=True, text=True)
        if sys_res.returncode == 0:
            return True, "Squid reloaded via systemctl."
        return False, reload_res.stderr.strip() or sys_res.stderr.strip()

def read_acl_file(file_path):
    """Reads a domain ACL file returning a list of cleaned domain strings."""
    if not os.path.isfile(file_path):
        return []
    domains = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            clean = line.strip()
            if clean and not clean.startswith("#"):
                domains.append(clean)
    return sorted(list(set(domains)))

def write_acl_file(file_path, domain_list):
    """Safely updates an ACL text file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"# Innspark Squid ACL List - Managed via Web Portal\n")
        f.write(f"# Updated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        for domain in sorted(list(set(domain_list))):
            d = domain.strip()
            if d:
                f.write(f"{d}\n")

# ------------------------------------------------------------------------------
# Web Routes: Authentication & Interface
# ------------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Handles user authentication and session creation."""
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        if request.is_json:
            data = request.get_json() or {}
            username = data.get("username", "")
            password = data.get("password", "")
            remember = data.get("remember", False)
        else:
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            remember = request.form.get("remember") in ("true", "1", "on", "yes")

        success, res = authenticate_user(username, password)
        if success:
            session["logged_in"] = True
            session["username"] = res["username"]
            session["display_name"] = res["display_name"]
            session["role"] = res["role"]
            session["is_admin"] = res["is_admin"]
            session["login_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if remember:
                session.permanent = True
            else:
                session.permanent = False

            if request.is_json:
                return jsonify({"success": True, "redirect": "/"})
            return redirect(url_for("index"))
        else:
            error = res
            if request.is_json:
                return jsonify({"success": False, "error": error}), 401

    return render_template(
        "login.html",
        domain="innspark.in",
        base_dn=config.BASE_DN,
        error=error
    )

@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Destroys the current user session and redirects to login."""
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/auth/me")
@login_required
def api_auth_me():
    """Returns the currently authenticated session profile."""
    return jsonify({
        "username": session.get("username"),
        "display_name": session.get("display_name"),
        "role": session.get("role"),
        "is_admin": session.get("is_admin", False),
        "login_time": session.get("login_time")
    })

@app.route("/")
@login_required
def index():
    """Renders the main unified dashboard."""
    return render_template(
        "index.html",
        domain="innspark.in",
        base_dn=config.BASE_DN,
        ldap_host=config.LDAP_HOST,
        sarg_url=config.SARG_WEB_URL,
        current_user=session.get("username", "admin"),
        display_name=session.get("display_name", "System Administrator"),
        user_role=session.get("role", "Administrator")
    )

# ------------------------------------------------------------------------------
# API Routes: Dashboard & System Status
# ------------------------------------------------------------------------------
@app.route("/api/status")
@login_required
def api_status():
    """Returns real-time status of Squid, LDAP connectivity, and counts."""
    squid_info = get_squid_status()
    
    # Test LDAP reachability
    ldap_connected = False
    ldap_error = None
    try:
        conn = get_ldap_connection(admin=False)
        ldap_connected = conn.bound
        conn.unbind()
    except Exception as e:
        ldap_error = str(e)

    # ACL counts
    whitelist = read_acl_file(config.WHITELIST_PATH)
    blacklist = read_acl_file(config.BLACKLIST_PATH)

    # Log file status
    log_size = 0
    if os.path.isfile(config.ACCESS_LOG_PATH):
        log_size = os.path.getsize(config.ACCESS_LOG_PATH)

    return jsonify({
        "timestamp": datetime.datetime.now().isoformat(),
        "squid": squid_info,
        "ldap": {
            "connected": ldap_connected,
            "host": config.LDAP_HOST,
            "port": config.LDAP_PORT,
            "base_dn": config.BASE_DN,
            "error": ldap_error
        },
        "metrics": {
            "whitelisted_domains": len(whitelist),
            "blacklisted_domains": len(blacklist),
            "access_log_bytes": log_size
        }
    })

# ------------------------------------------------------------------------------
# API Routes: LDAP User Management
# ------------------------------------------------------------------------------
@app.route("/api/users", methods=["GET"])
@login_required
def api_get_users():
    """Lists all users in ou=people and their group memberships."""
    try:
        conn = get_ldap_connection(admin=False)
        
        # Search all users in ou=people
        conn.search(
            search_base=config.USER_OU,
            search_filter="(objectClass=posixAccount)",
            search_scope=SUBTREE,
            attributes=["uid", "cn", "sn", "givenName", "mail", "uidNumber", "gidNumber", "homeDirectory"]
        )
        users = []
        for entry in conn.entries:
            uid = str(entry.uid.value) if entry.uid else ""
            users.append({
                "uid": uid,
                "cn": str(entry.cn.value) if entry.cn else uid,
                "givenName": str(entry.givenName.value) if hasattr(entry, "givenName") and entry.givenName else "",
                "sn": str(entry.sn.value) if hasattr(entry, "sn") and entry.sn else "",
                "mail": str(entry.mail.value) if hasattr(entry, "mail") and entry.mail else "",
                "uidNumber": entry.uidNumber.value if hasattr(entry, "uidNumber") else None,
                "in_proxy_users": False,
                "in_proxy_admins": False
            })

        # Fetch group memberships
        conn.search(
            search_base=config.GROUP_OU,
            search_filter="(objectClass=posixGroup)",
            search_scope=SUBTREE,
            attributes=["cn", "memberUid"]
        )
        proxy_users_members = set()
        proxy_admins_members = set()
        for g_entry in conn.entries:
            group_cn = str(g_entry.cn.value)
            members = g_entry.memberUid.values if hasattr(g_entry, "memberUid") and g_entry.memberUid else []
            if group_cn == "proxy_users":
                proxy_users_members.update(members)
            elif group_cn == "proxy_admins":
                proxy_admins_members.update(members)

        for u in users:
            u["in_proxy_users"] = u["uid"] in proxy_users_members
            u["in_proxy_admins"] = u["uid"] in proxy_admins_members

        conn.unbind()
        return jsonify({"success": True, "users": users})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/users", methods=["POST"])
@login_required
def api_create_user():
    """Creates a new LDAP user and assigns them to proxy access groups."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    full_name = data.get("full_name", "").strip() or username
    first_name = data.get("first_name", "").strip() or username
    last_name = data.get("last_name", "").strip() or "User"
    email = data.get("email", "").strip() or f"{username}@innspark.in"
    password = data.get("password", "").strip()
    is_proxy_user = bool(data.get("is_proxy_user", True))
    is_proxy_admin = bool(data.get("is_proxy_admin", False))

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required."}), 400

    try:
        conn = get_ldap_connection(admin=True)

        # Determine next available uidNumber
        conn.search(
            search_base=config.USER_OU,
            search_filter="(objectClass=posixAccount)",
            search_scope=SUBTREE,
            attributes=["uidNumber"]
        )
        existing_uids = [e.uidNumber.value for e in conn.entries if hasattr(e, "uidNumber") and e.uidNumber]
        next_uid_number = max(existing_uids) + 1 if existing_uids else 2000

        user_dn = f"uid={username},{config.USER_OU}"
        object_classes = ["inetOrgPerson", "posixAccount", "shadowAccount"]
        attributes = {
            "cn": full_name,
            "sn": last_name,
            "givenName": first_name,
            "mail": email,
            "userPassword": password,
            "uidNumber": next_uid_number,
            "gidNumber": 5000,  # default gidNumber
            "homeDirectory": f"/home/{username}",
            "loginShell": "/bin/bash"
        }

        # Add user entry
        if not conn.add(user_dn, object_class=object_classes, attributes=attributes):
            err = conn.result.get("description", "Failed to add user")
            conn.unbind()
            return jsonify({"success": False, "error": f"LDAP add error: {err}"}), 400

        # Assign to groups
        groups_to_add = []
        if is_proxy_user:
            groups_to_add.append("proxy_users")
        if is_proxy_admin:
            groups_to_add.append("proxy_admins")

        for grp in groups_to_add:
            group_dn = f"cn={grp},{config.GROUP_OU}"
            conn.modify(group_dn, {"memberUid": [(MODIFY_ADD, [username])]})

        conn.unbind()
        return jsonify({
            "success": True,
            "message": f"User '{username}' created successfully.",
            "uid": username,
            "uidNumber": next_uid_number
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/users/<uid>", methods=["DELETE"])
@login_required
def api_delete_user(uid):
    """Removes a user from LDAP and purges their group memberships."""
    try:
        conn = get_ldap_connection(admin=True)
        user_dn = f"uid={uid},{config.USER_OU}"
        
        # Remove from groups first
        for grp in ["proxy_users", "proxy_admins"]:
            try:
                conn.modify(
                    f"cn={grp},{config.GROUP_OU}",
                    {"memberUid": [(MODIFY_DELETE, [uid])]}
                )
            except Exception:
                pass

        # Delete user object
        if not conn.delete(user_dn):
            err = conn.result.get("description", "Failed to delete user")
            conn.unbind()
            return jsonify({"success": False, "error": err}), 400

        conn.unbind()
        return jsonify({"success": True, "message": f"User '{uid}' deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/users/<uid>/toggle-group", methods=["POST"])
@login_required
def api_toggle_group(uid):
    """Adds or removes a user from a specific proxy group."""
    data = request.get_json() or {}
    group_name = data.get("group_name")
    action = data.get("action")  # 'add' or 'remove'

    if group_name not in ["proxy_users", "proxy_admins"]:
        return jsonify({"success": False, "error": "Invalid group."}), 400

    try:
        conn = get_ldap_connection(admin=True)
        mod_type = MODIFY_ADD if action == "add" else MODIFY_DELETE
        group_dn = f"cn={group_name},{config.GROUP_OU}"
        
        conn.modify(group_dn, {"memberUid": [(mod_type, [uid])]})
        conn.unbind()
        return jsonify({"success": True, "message": f"User {uid} updated in {group_name}."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ------------------------------------------------------------------------------
# API Routes: Whitelist / Blacklist ACL Management
# ------------------------------------------------------------------------------
@app.route("/api/acls", methods=["GET"])
@login_required
def api_get_acls():
    """Returns current whitelist and blacklist domain lists."""
    return jsonify({
        "whitelist": read_acl_file(config.WHITELIST_PATH),
        "blacklist": read_acl_file(config.BLACKLIST_PATH)
    })

@app.route("/api/acls", methods=["POST"])
@login_required
def api_update_acls():
    """Updates whitelist and/or blacklist files and optionally reloads Squid."""
    data = request.get_json() or {}
    whitelist = data.get("whitelist")
    blacklist = data.get("blacklist")
    trigger_reload = bool(data.get("reload_squid", True))

    try:
        if whitelist is not None and isinstance(whitelist, list):
            write_acl_file(config.WHITELIST_PATH, whitelist)
        if blacklist is not None and isinstance(blacklist, list):
            write_acl_file(config.BLACKLIST_PATH, blacklist)

        reload_msg = "ACL files saved."
        if trigger_reload:
            success, msg = reload_squid_service()
            reload_msg += f" Squid Reload: {msg}"

        return jsonify({"success": True, "message": reload_msg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/squid/reload", methods=["POST"])
@login_required
def api_reload_squid():
    """Explicitly triggers a Squid configuration reload."""
    success, msg = reload_squid_service()
    status_code = 200 if success else 500
    return jsonify({"success": success, "message": msg}), status_code

# ------------------------------------------------------------------------------
# API Routes: Live Log Streaming
# ------------------------------------------------------------------------------
@app.route("/api/logs", methods=["GET"])
@login_required
def api_get_logs():
    """Reads the last N lines from the Squid access log and returns structured items."""
    lines_count = int(request.args.get("lines", 50))
    if not os.path.isfile(config.ACCESS_LOG_PATH):
        return jsonify({"success": True, "logs": [], "note": "Log file does not exist yet."})

    try:
        # Use tail command for maximum speed on large log files
        res = subprocess.run(
            ["tail", "-n", str(lines_count), config.ACCESS_LOG_PATH],
            capture_output=True,
            text=True,
            timeout=3
        )
        raw_lines = res.stdout.splitlines()
        parsed_logs = []
        for line in reversed(raw_lines):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 10:
                # Squid native log format:
                # time elapsed remotehost code/status bytes method URL rfc931 peerstatus/peerhost type
                try:
                    ts = float(parts[0])
                    time_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    time_str = parts[0]
                
                parsed_logs.append({
                    "timestamp": time_str,
                    "elapsed_ms": parts[1],
                    "client_ip": parts[2],
                    "action_status": parts[3],
                    "bytes": parts[4],
                    "method": parts[5],
                    "url": parts[6],
                    "user": parts[7] if parts[7] != "-" else "anonymous",
                    "hierarchy": parts[8],
                    "mime_type": parts[9]
                })
            else:
                parsed_logs.append({"raw": line})

        return jsonify({"success": True, "logs": parsed_logs})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ------------------------------------------------------------------------------
# API Routes: SARG Report Trigger
# ------------------------------------------------------------------------------
@app.route("/api/sarg/generate", methods=["POST"])
@login_required
def api_sarg_generate():
    """Runs SARG to regenerate HTML reports."""
    if not os.path.isfile(config.SARG_BIN_PATH):
        return jsonify({"success": False, "error": f"SARG not found at {config.SARG_BIN_PATH}"}), 404

    try:
        res = subprocess.run(
            [config.SARG_BIN_PATH],
            capture_output=True,
            text=True,
            timeout=30
        )
        if res.returncode == 0:
            return jsonify({
                "success": True,
                "message": "SARG reports generated successfully.",
                "url": config.SARG_WEB_URL
            })
        else:
            return jsonify({
                "success": False,
                "error": res.stderr or "SARG execution error."
            }), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ------------------------------------------------------------------------------
# Main Entry Point
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"Starting Innspark Squid & LDAP Portal on {config.PORTAL_HOST}:{config.PORTAL_PORT}...")
    app.run(host=config.PORTAL_HOST, port=config.PORTAL_PORT, debug=config.DEBUG)
