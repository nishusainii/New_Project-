import os
import re
import socket
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from ldap3 import Server, Connection, ALL, SUBTREE, MODIFY_REPLACE, MODIFY_ADD, MODIFY_DELETE

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "innspark-enterprise-wifi-ldap-secret-key-2026")
app.permanent_session_lifetime = timedelta(hours=8)

# LDAP Configurations from Environment
LDAP_HOST = os.environ.get("LDAP_HOST", "127.0.0.1")
LDAP_PORT = int(os.environ.get("LDAP_PORT", "389"))
LDAP_BASE_DN = os.environ.get("LDAP_BASE_DN", "dc=innspark,dc=in")
LDAP_ADMIN_DN = os.environ.get("LDAP_ADMIN_DN", "cn=admin,dc=innspark,dc=in")
LDAP_ADMIN_PASSWORD = os.environ.get("LDAP_ADMIN_PASSWORD", "AdminPassword123!")

USERS_DN = f"ou=Users,{LDAP_BASE_DN}"
GROUPS_DN = f"ou=Groups,{LDAP_BASE_DN}"
WIFI_GROUP_DN = f"cn=wifi-users,{GROUPS_DN}"

def get_ldap_admin_connection():
    server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
    conn = Connection(server, LDAP_ADMIN_DN, LDAP_ADMIN_PASSWORD, auto_bind=True)
    return conn

def authenticate_ldap_user(user_input, password):
    """
    Authenticates a user against OpenLDAP directory.
    Supports 'admin' shortcut, full DN, simple username, or corporate email.
    """
    if not user_input or not password:
        return False, None, "Directory username and password are required."

    user_input = user_input.strip()
    
    # Check for admin credentials
    if user_input.lower() in ["admin", "root", "administrator"] or user_input.lower() == LDAP_ADMIN_DN.lower():
        bind_dn = LDAP_ADMIN_DN
        display_name = "System Administrator"
        is_admin = True
    elif "=" in user_input:
        bind_dn = user_input
        display_name = user_input.split("=")[1].split(",")[0]
        is_admin = (bind_dn.lower() == LDAP_ADMIN_DN.lower())
    else:
        # Standard corporate user (e.g. 'john.doe' or 'john.doe@innspark.in')
        clean_user = user_input.split("@")[0].strip()
        bind_dn = f"uid={clean_user},{USERS_DN}"
        display_name = clean_user
        is_admin = False
        
        # Query LDAP directory using admin connection to find exact user entry & name
        try:
            admin_conn = get_ldap_admin_connection()
            admin_conn.search(
                USERS_DN,
                f"(&(objectClass=inetOrgPerson)(|(uid={clean_user})(mail={user_input})))",
                search_scope=SUBTREE,
                attributes=["cn", "givenName", "sn", "uid"]
            )
            if admin_conn.entries:
                entry = admin_conn.entries[0]
                bind_dn = str(entry.entry_dn)
                if "cn" in entry and entry.cn.value:
                    display_name = str(entry.cn.value)
            admin_conn.unbind()
        except Exception:
            pass

    # Attempt bind with resolved DN and supplied password
    try:
        server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
        conn = Connection(server, bind_dn, password)
        if conn.bind():
            conn.unbind()
            return True, {
                "dn": bind_dn,
                "username": user_input,
                "display_name": display_name,
                "is_admin": is_admin
            }, None
        else:
            return False, None, "Invalid directory credentials. Please check your username and password."
    except Exception as e:
        return False, None, f"LDAP directory error: {str(e)}"

@app.before_request
def check_authentication():
    """
    Enforces authentication before accessing the dashboard or backend APIs.
    """
    # Allow static assets
    if request.path.startswith("/static/"):
        return None
    # Allow authentication endpoints
    if request.path in ["/login", "/logout"]:
        return None

    # Verify session authentication
    if not session.get("authenticated"):
        if request.path.startswith("/api/"):
            return jsonify({
                "success": False,
                "error": "Authentication required. Please log in first.",
                "unauthorized": True
            }), 401
        
        # For web pages, redirect to /login
        target = request.full_path if request.query_string else request.path
        return redirect(url_for("login", next=target))

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))

    error = None
    username_val = ""

    if request.method == "POST":
        username_val = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username_val or not password:
            error = "Please enter both directory username and password."
        else:
            success, user_data, err_msg = authenticate_ldap_user(username_val, password)
            if success:
                session.clear()
                session.permanent = True
                session["authenticated"] = True
                session["user_dn"] = user_data["dn"]
                session["username"] = user_data["username"]
                session["display_name"] = user_data["display_name"]
                session["is_admin"] = user_data["is_admin"]

                next_url = request.args.get("next") or request.form.get("next")
                if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
                    next_url = url_for("index")
                return redirect(next_url)
            else:
                error = err_msg or "Invalid username or password."

    return render_template(
        "login.html",
        error=error,
        username=username_val,
        domain=LDAP_BASE_DN,
        ldap_host=f"{LDAP_HOST}:{LDAP_PORT}",
        next=request.args.get("next", "")
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    return render_template(
        "index.html",
        domain=LDAP_BASE_DN,
        current_user=session.get("display_name", "Administrator"),
        current_username=session.get("username", "admin"),
        is_admin=session.get("is_admin", True)
    )

@app.route("/api/status", methods=["GET"])
def api_status():
    ldap_online = False
    error_msg = ""
    try:
        conn = get_ldap_admin_connection()
        ldap_online = True
        conn.unbind()
    except Exception as e:
        error_msg = str(e)

    radius_online = True # FreeRADIUS container runs locally on host UDP 1812

    return jsonify({
        "ldap_online": ldap_online,
        "radius_online": radius_online,
        "ldap_host": f"{LDAP_HOST}:{LDAP_PORT}",
        "base_dn": LDAP_BASE_DN,
        "error": error_msg
    })

@app.route("/api/users", methods=["GET"])
def api_get_users():
    try:
        conn = get_ldap_admin_connection()
        
        # 1. Fetch Wi-Fi Group Members
        wifi_members = set()
        conn.search(WIFI_GROUP_DN, "(objectClass=*)", attributes=["memberUid"])
        if conn.entries:
            for m in conn.entries[0].memberUid:
                wifi_members.add(str(m))

        # 2. Fetch Users
        conn.search(
            USERS_DN,
            "(&(objectClass=inetOrgPerson)(uid=*))",
            search_scope=SUBTREE,
            attributes=["uid", "cn", "sn", "givenName", "mail", "uidNumber", "gidNumber"]
        )

        users_list = []
        for entry in conn.entries:
            uid = str(entry.uid)
            users_list.append({
                "uid": uid,
                "cn": str(entry.cn) if "cn" in entry else uid,
                "sn": str(entry.sn) if "sn" in entry else "",
                "givenName": str(entry.givenName) if "givenName" in entry else "",
                "mail": str(entry.mail) if "mail" in entry else f"{uid}@innspark.in",
                "uidNumber": int(entry.uidNumber.value) if "uidNumber" in entry else 10000,
                "wifi_authorized": uid in wifi_members
            })

        conn.unbind()
        # Sort by uid
        users_list.sort(key=lambda x: x["uid"])
        return jsonify({"success": True, "users": users_list, "total": len(users_list)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/users", methods=["POST"])
def api_create_user():
    data = request.json or {}
    uid = data.get("uid", "").strip().lower()
    first_name = data.get("givenName", "").strip()
    last_name = data.get("sn", "").strip()
    password = data.get("password", "").strip()
    email = data.get("mail", "").strip() or f"{uid}@innspark.in"
    wifi_auth = data.get("wifi_authorized", True)

    if not uid or not last_name or not password:
        return jsonify({"success": False, "error": "Username, Last Name, and Password are required."}), 400

    # Sanitize UID
    if not re.match(r"^[a-zA-Z0-9._-]+$", uid):
        return jsonify({"success": False, "error": "Username can only contain letters, numbers, dots, and hyphens."}), 400

    full_name = f"{first_name} {last_name}".strip() if first_name else last_name
    user_dn = f"uid={uid},{USERS_DN}"

    try:
        conn = get_ldap_admin_connection()

        # Determine next uidNumber
        conn.search(USERS_DN, "(objectClass=posixAccount)", attributes=["uidNumber"])
        max_uid = 10000
        for entry in conn.entries:
            if "uidNumber" in entry and entry.uidNumber.value > max_uid:
                max_uid = entry.uidNumber.value
        next_uid_number = max_uid + 1

        attributes = {
            "objectClass": [
                "top", "person", "organizationalPerson", "inetOrgPerson", "posixAccount", "shadowAccount"
            ],
            "cn": full_name,
            "sn": last_name,
            "uid": uid,
            "uidNumber": next_uid_number,
            "gidNumber": 10000,
            "homeDirectory": f"/home/{uid}",
            "loginShell": "/bin/bash",
            "mail": email,
            "userPassword": password
        }
        if first_name:
            attributes["givenName"] = first_name

        # Add user
        if not conn.add(user_dn, attributes=attributes):
            return jsonify({"success": False, "error": conn.result.get("description", "Failed to add user")}), 400

        # Add to Wi-Fi Group if checked
        if wifi_auth:
            conn.modify(WIFI_GROUP_DN, {"memberUid": [(MODIFY_ADD, [uid])]})

        conn.unbind()
        return jsonify({"success": True, "message": f"User '{uid}' created successfully with Wi-Fi authorization!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/users/<uid>/password", methods=["POST"])
def api_update_password(uid):
    data = request.json or {}
    new_password = data.get("password", "").strip()
    if not new_password:
        return jsonify({"success": False, "error": "Password cannot be empty"}), 400

    try:
        conn = get_ldap_admin_connection()
        user_dn = f"uid={uid},{USERS_DN}"
        conn.modify(user_dn, {"userPassword": [(MODIFY_REPLACE, [new_password])]})
        if conn.result.get("result") != 0:
            return jsonify({"success": False, "error": conn.result.get("description", "Password change failed")}), 400
        conn.unbind()
        return jsonify({"success": True, "message": f"Password updated successfully for {uid}!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/users/<uid>/toggle-wifi", methods=["POST"])
def api_toggle_wifi(uid):
    data = request.json or {}
    enable = data.get("enable", True)

    try:
        conn = get_ldap_admin_connection()
        if enable:
            conn.modify(WIFI_GROUP_DN, {"memberUid": [(MODIFY_ADD, [uid])]})
            msg = f"Wi-Fi access granted for '{uid}' (added to cn=wifi-users)."
        else:
            conn.modify(WIFI_GROUP_DN, {"memberUid": [(MODIFY_DELETE, [uid])]})
            msg = f"Wi-Fi access revoked for '{uid}' (removed from cn=wifi-users)."
        conn.unbind()
        return jsonify({"success": True, "message": msg, "wifi_authorized": enable})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/users/<uid>", methods=["DELETE"])
def api_delete_user(uid):
    try:
        conn = get_ldap_admin_connection()
        user_dn = f"uid={uid},{USERS_DN}"
        
        # Remove from Wi-Fi group first (ignore if not in group)
        try:
            conn.modify(WIFI_GROUP_DN, {"memberUid": [(MODIFY_DELETE, [uid])]})
        except Exception:
            pass

        # Delete entry
        if not conn.delete(user_dn):
            return jsonify({"success": False, "error": conn.result.get("description", "Failed to delete user")}), 400
        conn.unbind()
        return jsonify({"success": True, "message": f"User '{uid}' deleted successfully."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/test-auth", methods=["POST"])
def api_test_auth():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400

    clean_user = username.split("@")[0].strip().lower()
    user_dn = f"uid={clean_user},{USERS_DN}"

    try:
        # Check exact user in LDAP using admin connection
        admin_conn = get_ldap_admin_connection()
        admin_conn.search(
            USERS_DN,
            f"(&(objectClass=inetOrgPerson)(|(uid={clean_user})(mail={username})))",
            search_scope=SUBTREE,
            attributes=["uid", "cn"]
        )
        if admin_conn.entries:
            user_dn = str(admin_conn.entries[0].entry_dn)
            clean_user = str(admin_conn.entries[0].uid)

        server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
        user_conn = Connection(server, user_dn, password)
        if user_conn.bind():
            # Check group membership
            admin_conn.search(WIFI_GROUP_DN, "(objectClass=*)", attributes=["memberUid"])
            in_group = False
            if admin_conn.entries:
                members = [str(m).lower() for m in admin_conn.entries[0].memberUid]
                in_group = clean_user.lower() in members
            admin_conn.unbind()
            user_conn.unbind()

            return jsonify({
                "success": True,
                "authenticated": True,
                "user_dn": user_dn,
                "wifi_authorized": in_group,
                "message": "LDAP Bind Success! Credentials match." + (" Authorized for Wi-Fi (Access-Accept)." if in_group else " Warning: User is NOT in cn=wifi-users!")
            })
        else:
            admin_conn.unbind()
            return jsonify({
                "success": True,
                "authenticated": False,
                "user_dn": user_dn,
                "wifi_authorized": False,
                "message": "LDAP Bind Rejected: Invalid password or user does not exist (Access-Reject)."
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8088)), debug=False)
