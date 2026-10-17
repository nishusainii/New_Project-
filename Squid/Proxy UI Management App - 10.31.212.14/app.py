"""
Innspark Squid Proxy Management Portal - Flask Web Application & REST API
Server: 10.31.1.159 (proxyserver)
Port: 5000
"""

import os
import sys
import datetime
import urllib.parse

# ------------------------------------------------------------------------------
# Compatibility Shim: Fix ImportError when Werkzeug >= 3.0 is installed alongside Flask < 3.0
try:
    import werkzeug.urls
    if not hasattr(werkzeug.urls, "url_quote"):
        werkzeug.urls.url_quote = urllib.parse.quote
    if not hasattr(werkzeug.urls, "url_quote_plus"):
        werkzeug.urls.url_quote_plus = urllib.parse.quote_plus
    if not hasattr(werkzeug.urls, "url_unquote"):
        werkzeug.urls.url_unquote = urllib.parse.unquote
    if not hasattr(werkzeug.urls, "url_unquote_plus"):
        werkzeug.urls.url_unquote_plus = urllib.parse.unquote_plus
    if not hasattr(werkzeug.urls, "url_decode"):
        werkzeug.urls.url_decode = urllib.parse.parse_qs
    if not hasattr(werkzeug.urls, "url_encode"):
        werkzeug.urls.url_encode = urllib.parse.urlencode
except Exception:
    pass

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory

import config
import auth
import squid_manager
import nftables_manager

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY
app.config["SESSION_COOKIE_NAME"] = config.SESSION_COOKIE_NAME
app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(seconds=config.PERMANENT_SESSION_LIFETIME)

# Ensure admin credentials file is initialized on startup
auth.init_admin_creds()

# ------------------------------------------------------------------------------
# Frontend Web Views
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.context_processor
def inject_server_info():
    try:
        host_ip = request.host.split(':')[0]
    except Exception:
        host_ip = "127.0.0.1"
    return dict(server_ip=host_ip)

@app.route("/")
@auth.login_required
def dashboard_page():
    """Main Single Page Application Dashboard."""
    return render_template("index.html", user=session.get("username", config.DEFAULT_ADMIN_USER))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    """Admin Login Page."""
    if session.get("logged_in"):
        return redirect(url_for("dashboard_page"))

    error_msg = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)

        success, msg = auth.verify_credentials(username, password, client_ip)
        if success:
            session.permanent = True
            session["logged_in"] = True
            session["username"] = username
            session["login_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return redirect(url_for("dashboard_page"))
        else:
            error_msg = msg

    return render_template("login.html", error=error_msg)

@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Session Logout."""
    session.clear()
    return redirect(url_for("login_page"))

# ------------------------------------------------------------------------------
# REST API: Status & Telemetry
# ------------------------------------------------------------------------------
@app.route("/api/status", methods=["GET"])
@auth.login_required
def api_status():
    """Returns Squid daemon status and metrics."""
    status_info = squid_manager.get_service_status()
    metrics = squid_manager.get_system_metrics()
    return jsonify({
        "status": status_info,
        "metrics": metrics,
        "analytics": metrics.get("analytics", {}),
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/api/dashboard/analytics", methods=["GET"])
@auth.login_required
def api_dashboard_analytics():
    """Returns real-time log traffic analytics for specified time-range or sample size."""
    sample_range = request.args.get("range", "500")
    analytics = squid_manager.get_dashboard_analytics(sample_range=sample_range)
    return jsonify({"success": True, "analytics": analytics})

@app.route("/api/ports/check/<int:port>", methods=["POST"])
@auth.login_required
def api_check_port(port):
    """Probes a specific Squid proxy port for listening state, gateway reachability, public egress IP, and ISP data quota / captive portal status."""
    try:
        diag = squid_manager.probe_port_internet(port)
        is_ok = diag["status"] == "ONLINE"
        return jsonify({
            "success": is_ok,
            "port": port,
            "status": diag["status"],
            "badge": diag["badge"],
            "color": diag["color"],
            "latency_ms": diag["latency_ms"],
            "gateway": diag["gateway"],
            "gateway_ok": diag["gateway_ok"],
            "public_ip": diag["public_ip"],
            "message": diag["message"],
            "details": diag
        })
    except Exception as e:
        return jsonify({"success": False, "port": port, "status": "ERROR", "badge": "ERROR", "color": "rose", "message": str(e)})

@app.route("/api/ports/check-all", methods=["POST"])
@auth.login_required
def api_check_all_ports():
    """Runs concurrent internet and ISP connectivity diagnostics across all configured proxy ports."""
    try:
        results = squid_manager.probe_all_ports_internet()
        all_online = all(r.get("status") == "ONLINE" for r in results.values())
        return jsonify({
            "success": True,
            "all_online": all_online,
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ------------------------------------------------------------------------------
# REST API: Proxy Users (/etc/squid/password)
# ------------------------------------------------------------------------------
@app.route("/api/users", methods=["GET"])
@auth.login_required
def api_get_users():
    """Lists all proxy users with group memberships."""
    users = squid_manager.list_users()
    groups = squid_manager.list_acl_groups()
    return jsonify({"users": users, "groups": [g["name"] for g in groups]})

@app.route("/api/users", methods=["POST"])
@auth.login_required
def api_add_user():
    """Creates a new proxy user."""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    groups = data.get("groups", [])

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password are required."}), 400

    ok, msg = squid_manager.add_user(username, password, groups)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/users/<username>/password", methods=["PUT"])
@auth.login_required
def api_change_user_password(username):
    """Changes password for an existing proxy user."""
    data = request.get_json() or {}
    new_password = data.get("password", "").strip()
    if not new_password:
        return jsonify({"success": False, "error": "New password cannot be empty."}), 400

    ok, msg = squid_manager.update_user_password(username, new_password)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/users/<username>", methods=["DELETE"])
@auth.login_required
def api_delete_user(username):
    """Deletes a proxy user."""
    ok, msg = squid_manager.delete_user(username)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/users/<username>/groups", methods=["PUT"])
@auth.login_required
def api_update_user_groups(username):
    """Updates group memberships for a proxy user."""
    data = request.get_json() or {}
    selected_groups = data.get("groups", [])
    ok, msg = squid_manager.update_user_group_assignments(username, selected_groups)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

# ------------------------------------------------------------------------------
# REST API: ACL Groups
# ------------------------------------------------------------------------------
@app.route("/api/groups", methods=["GET"])
@auth.login_required
def api_get_groups():
    """Lists all user ACL groups along with all registered proxy users."""
    groups = squid_manager.list_acl_groups()
    all_users = [u["username"] for u in squid_manager.list_users()]
    return jsonify({"groups": groups, "all_users": all_users})

@app.route("/api/groups", methods=["POST"])
@auth.login_required
def api_create_group():
    """Creates a new ACL group."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    users = data.get("users", [])
    if not name:
        return jsonify({"success": False, "error": "Group name is required."}), 400

    ok, msg = squid_manager.create_group(name, users)
    if ok:
        if data.get("reload", False):
            squid_manager.reload_squid()
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/groups/<group_name>", methods=["PUT"])
@auth.login_required
def api_update_group(group_name):
    """Updates users belonging to an ACL group."""
    data = request.get_json() or {}
    users = data.get("users", [])
    ok, msg = squid_manager.save_group_members(group_name, users)
    if ok:
        if data.get("reload", False):
            squid_manager.reload_squid()
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/groups/<group_name>", methods=["DELETE"])
@auth.login_required
def api_delete_group(group_name):
    """Deletes an ACL group."""
    ok, msg = squid_manager.delete_group(group_name)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

# ------------------------------------------------------------------------------
# REST API: Domain Policies
# ------------------------------------------------------------------------------
@app.route("/api/domains", methods=["GET"])
@auth.login_required
def api_get_domains():
    """Lists all domain policy files and their contents."""
    domain_lists = squid_manager.list_domain_lists()
    return jsonify({"domain_lists": domain_lists})

@app.route("/api/domains/<list_name>", methods=["POST"])
@auth.login_required
def api_add_domain(list_name):
    """Adds a domain to a domain policy list."""
    data = request.get_json() or {}
    domain = data.get("domain", "").strip()
    if not domain:
        return jsonify({"success": False, "error": "Domain is required."}), 400

    ok, msg = squid_manager.add_domain(list_name, domain)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/domains/<list_name>", methods=["DELETE"])
@auth.login_required
def api_remove_domain(list_name):
    """Removes a domain from a domain policy list."""
    data = request.get_json() or {}
    domain = data.get("domain", "").strip()
    if not domain:
        return jsonify({"success": False, "error": "Domain is required."}), 400

    ok, msg = squid_manager.remove_domain(list_name, domain)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

# ------------------------------------------------------------------------------
# REST API: Allowed IPs
# ------------------------------------------------------------------------------
@app.route("/api/allowed-ips", methods=["GET"])
@auth.login_required
def api_get_allowed_ips():
    """Lists allowed client IPs and subnets."""
    ips = squid_manager.list_allowed_ips()
    return jsonify({"ips": ips})

@app.route("/api/allowed-ips", methods=["POST"])
@auth.login_required
def api_add_allowed_ip():
    """Adds an IP or CIDR to allowed list."""
    data = request.get_json() or {}
    ip = data.get("ip", "").strip()
    if not ip:
        return jsonify({"success": False, "error": "IP or CIDR is required."}), 400

    ok, msg = squid_manager.add_allowed_ip(ip)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/allowed-ips", methods=["DELETE"])
@auth.login_required
def api_remove_allowed_ip():
    """Removes an IP or CIDR from allowed list."""
    data = request.get_json() or {}
    ip = data.get("ip", "").strip()
    if not ip:
        return jsonify({"success": False, "error": "IP is required."}), 400

    ok, msg = squid_manager.remove_allowed_ip(ip)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

# ------------------------------------------------------------------------------
# REST API: Port & Outgoing Routing
# ------------------------------------------------------------------------------
@app.route("/api/ports", methods=["GET"])
@auth.login_required
def api_get_ports():
    """Returns ports and mapped outgoing IP routing table."""
    ports = squid_manager.get_ports_info()
    return jsonify({"ports": ports})

# ------------------------------------------------------------------------------
# REST API: Per-Port Bandwidth & Traffic Statistics
# ------------------------------------------------------------------------------
@app.route("/api/bandwidth/ports", methods=["GET"])
@auth.login_required
def api_get_port_bandwidth():
    """Returns granular real-time and historical bandwidth statistics for all configured proxy ports."""
    stats = squid_manager.get_port_bandwidth_stats()
    return jsonify(stats)

# ------------------------------------------------------------------------------
# REST API: Live Access Logs
# ------------------------------------------------------------------------------
@app.route("/api/logs", methods=["GET"])
@auth.login_required
def api_get_logs():
    """Streams recent lines from access.log with status, user, and time window filters."""
    lines_count = request.args.get("lines", 100, type=int)
    search_query = request.args.get("q", None)
    status_filter = request.args.get("status", None)
    user_filter = request.args.get("user", None)
    time_range = request.args.get("time", "15m")
    entries = squid_manager.tail_access_log(
        lines=lines_count, 
        search_query=search_query,
        status_filter=status_filter,
        user_filter=user_filter,
        time_range=time_range
    )
    return jsonify({"logs": entries})

# ------------------------------------------------------------------------------
# REST API: Direct File & Directory Management
# ------------------------------------------------------------------------------
@app.route("/api/files", methods=["GET"])
@auth.login_required
def api_get_files():
    """Lists safe editable files and squid directories."""
    files = squid_manager.get_editable_files()
    directories = squid_manager.get_squid_directories()
    return jsonify({"files": files, "directories": directories})

@app.route("/api/files/<file_id>", methods=["GET"])
@auth.login_required
def api_read_file(file_id):
    """Reads content of an editable file."""
    ok, content, path = squid_manager.read_editable_file(file_id)
    if ok:
        return jsonify({"success": True, "content": content, "path": path})
    return jsonify({"success": False, "error": content}), 400

@app.route("/api/files/<file_id>", methods=["POST"])
@auth.login_required
def api_save_file(file_id):
    """Safely saves file with backup and syntax verification."""
    data = request.get_json() or {}
    content = data.get("content", "")
    ok, msg = squid_manager.save_editable_file(file_id, content)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/files/create", methods=["POST"])
@auth.login_required
def api_create_file():
    """Creates a new configuration/ACL file."""
    data = request.get_json() or {}
    parent_dir = data.get("parent_dir", "/etc/squid").strip()
    filename = data.get("filename", "").strip()
    content = data.get("content", "")

    if not filename:
        return jsonify({"success": False, "error": "Filename is required."}), 400

    ok, msg = squid_manager.create_file(parent_dir, filename, content)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/files/delete", methods=["POST"])
@auth.login_required
def api_delete_file():
    """Safely deletes an editable file (with pre-flight snapshot)."""
    data = request.get_json() or {}
    file_path = data.get("path", "").strip()

    if not file_path:
        return jsonify({"success": False, "error": "File path is required."}), 400

    ok, msg = squid_manager.delete_file(file_path)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/directories/create", methods=["POST"])
@auth.login_required
def api_create_directory():
    """Creates a new folder in /etc/squid."""
    data = request.get_json() or {}
    parent_dir = data.get("parent_dir", "/etc/squid").strip()
    dirname = data.get("dirname", "").strip()

    if not dirname:
        return jsonify({"success": False, "error": "Directory name is required."}), 400

    ok, msg = squid_manager.create_directory(parent_dir, dirname)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/directories/delete", methods=["POST"])
@auth.login_required
def api_delete_directory():
    """Safely deletes a subfolder within /etc/squid."""
    data = request.get_json() or {}
    dir_path = data.get("path", "").strip()

    if not dir_path:
        return jsonify({"success": False, "error": "Directory path is required."}), 400

    ok, msg = squid_manager.delete_directory(dir_path)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

# ------------------------------------------------------------------------------
# REST API: Backups & Restore (With 5-Snapshot Rotation)
# ------------------------------------------------------------------------------
@app.route("/api/backups", methods=["GET"])
@auth.login_required
def api_get_backups():
    """Returns the 5 active backups and archives."""
    backups = squid_manager.list_backups()
    return jsonify(backups)

@app.route("/api/backups", methods=["POST"])
@auth.login_required
def api_create_backup():
    """Creates a manual backup snapshot."""
    data = request.get_json() or {}
    desc = data.get("description", "Manual backup via Web Portal")
    meta = squid_manager.create_backup(desc)
    return jsonify({"success": True, "backup": meta})

@app.route("/api/backups/restore", methods=["POST"])
@auth.login_required
def api_restore_backup():
    """Extracts and restores a backup snapshot."""
    data = request.get_json() or {}
    backup_id = data.get("backup_id", "").strip()
    if not backup_id:
        return jsonify({"success": False, "error": "Backup ID is required."}), 400

    ok, msg = squid_manager.restore_backup(backup_id)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

# ------------------------------------------------------------------------------
# REST API: Safe Squid Daemon Operations
# ------------------------------------------------------------------------------
@app.route("/api/squid/reload", methods=["POST"])
@auth.login_required
def api_squid_reload():
    """Graceful reload via squid -k reconfigure."""
    ok, msg = squid_manager.reload_squid()
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/api/squid/parse", methods=["POST"])
@auth.login_required
def api_squid_parse():
    """Syntax check via squid -k parse."""
    ok, msg = squid_manager.validate_squid_syntax()
    return jsonify({"valid": ok, "output": msg})

# ------------------------------------------------------------------------------
# REST API: SARG Reports
# ------------------------------------------------------------------------------
@app.route("/api/sarg/generate", methods=["POST"])
@auth.login_required
def api_sarg_generate():
    """Triggers SARG report generation."""
    ok, msg = squid_manager.trigger_sarg_generation()
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

@app.route("/sarg/")
@app.route("/sarg/<path:filename>")
@auth.login_required
def serve_sarg(filename="index.html"):
    """Serves SARG HTML reports embedded within the portal."""
    if os.path.exists(config.SARG_REPORTS_DIR):
        if filename in ("index.html", ""):
            # Parse directory names to locate the newest report by calendar date
            month_map = {
                "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
            }
            candidates = []
            try:
                for entry in os.scandir(config.SARG_REPORTS_DIR):
                    if entry.is_dir() and os.path.exists(os.path.join(entry.path, "dashboard.html")):
                        m = re.match(r"^(\d{2})([A-Za-z]{3})(\d{4})-(\d{2})([A-Za-z]{3})(\d{4})", entry.name)
                        if m:
                            d1, mon1, y1, d2, mon2, y2 = m.groups()
                            try:
                                dt1 = datetime.date(int(y1), month_map.get(mon1.lower(), 1), int(d1))
                                dt2 = datetime.date(int(y2), month_map.get(mon2.lower(), 1), int(d2))
                                candidates.append((max(dt1, dt2), dt1, entry.name))
                            except Exception:
                                pass
            except Exception:
                pass

            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                latest_folder = candidates[0][2]
                resp = redirect(f"/sarg/{latest_folder}/dashboard.html")
                resp.set_cookie("cisoi_gate", "1", path="/", samesite="Lax")
                return resp

        resp = send_from_directory(config.SARG_REPORTS_DIR, filename)
        resp.set_cookie("cisoi_gate", "1", path="/", samesite="Lax")
        return resp
    return "SARG reports directory not found.", 404

# ------------------------------------------------------------------------------
# REST API: Advanced Analytics — Fleet, Blocked, User Activity, Security, Hourly
# ------------------------------------------------------------------------------
@app.route("/api/fleet/status", methods=["GET"])
@auth.login_required
def api_fleet_status():
    """Returns multi-server fleet health overview."""
    fleet = squid_manager.get_fleet_status()
    return jsonify(fleet)

@app.route("/api/analytics/blocked", methods=["GET"])
@auth.login_required
def api_analytics_blocked():
    """Returns blocked requests analytics."""
    sample = request.args.get("lines", 1000, type=int)
    data = squid_manager.get_blocked_requests(sample_lines=sample)
    return jsonify(data)

@app.route("/api/analytics/user/<username>", methods=["GET"])
@auth.login_required
def api_analytics_user(username):
    """Returns per-user activity profile."""
    sample = request.args.get("lines", 2000, type=int)
    data = squid_manager.get_user_activity(username, sample_lines=sample)
    return jsonify(data)

@app.route("/api/analytics/security", methods=["GET"])
@auth.login_required
def api_analytics_security():
    """Returns security and audit events."""
    sample = request.args.get("lines", 2000, type=int)
    data = squid_manager.get_security_events(sample_lines=sample)
    return jsonify(data)

@app.route("/api/analytics/hourly", methods=["GET"])
@auth.login_required
def api_analytics_hourly():
    """Returns hourly traffic time-series data for charts."""
    hours = request.args.get("hours", 24, type=int)
    data = squid_manager.get_hourly_traffic_breakdown(hours=hours)
    return jsonify(data)

# ------------------------------------------------------------------------------
# REST API: Portal Admin Settings
# ------------------------------------------------------------------------------
@app.route("/api/settings/password", methods=["POST"])
@auth.login_required
def api_change_admin_password():
    """Changes portal admin password."""
    data = request.get_json() or {}
    old_pass = data.get("current_password", "").strip()
    new_pass = data.get("new_password", "").strip()

    ok, msg = auth.update_admin_password(old_pass, new_pass)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg}), 400

# ------------------------------------------------------------------------------
# REST API: nftables Firewall Management
# ------------------------------------------------------------------------------
@app.route("/api/nftables/ruleset", methods=["GET"])
@auth.login_required
def api_nftables_ruleset():
    """Returns parsed nftables tables, chains, rules with handles, and raw config."""
    try:
        data = nftables_manager.get_nftables_ruleset()
        return jsonify({"success": True, "ruleset": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/nftables/validate", methods=["POST"])
@auth.login_required
def api_nftables_validate():
    """Validates nftables syntax using 'nft -c -f'."""
    data = request.get_json() or {}
    content = data.get("content")
    is_valid, msg, err = nftables_manager.validate_nftables(content)
    return jsonify({
        "success": is_valid,
        "valid": is_valid,
        "message": msg,
        "error": err
    })

@app.route("/api/nftables/apply", methods=["POST"])
@auth.login_required
def api_nftables_apply():
    """Applies ruleset atomically with 'nft -f /etc/nftables.conf' and systemctl reload."""
    data = request.get_json() or {}
    content = data.get("content")
    ok, msg, err = nftables_manager.apply_nftables_conf(content, backup_reason="User manual apply")
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg, "details": err}), 400

@app.route("/api/nftables/rules/add", methods=["POST"])
@auth.login_required
def api_nftables_add_rule():
    """Adds a structured or raw rule to /etc/nftables.conf and applies live."""
    data = request.get_json() or {}
    table_family = data.get("table_family", "inet").strip()
    table_name = data.get("table_name", "filter").strip()
    chain_name = data.get("chain_name", "forward").strip()
    rule_statement = data.get("rule_statement", "").strip()
    comment = data.get("comment", "").strip()

    if not rule_statement:
        return jsonify({"success": False, "error": "Rule statement cannot be empty."}), 400

    ok, msg, err = nftables_manager.add_rule_to_conf(table_family, table_name, chain_name, rule_statement, comment)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg, "details": err}), 400

@app.route("/api/nftables/rules/delete", methods=["POST"])
@auth.login_required
def api_nftables_delete_rule():
    """Deletes a rule by handle or text from live ruleset and /etc/nftables.conf."""
    data = request.get_json() or {}
    table_family = data.get("table_family", "inet").strip()
    table_name = data.get("table_name", "filter").strip()
    chain_name = data.get("chain_name", "forward").strip()
    handle = data.get("handle")
    rule_text = data.get("rule_text", "").strip()

    ok, msg, err = nftables_manager.delete_rule_from_ruleset(table_family, table_name, chain_name, handle=handle, rule_text=rule_text)
    if ok:
        return jsonify({"success": True, "message": msg})
    return jsonify({"success": False, "error": msg, "details": err}), 400

# ------------------------------------------------------------------------------
# Run Server
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"[*] Starting Innspark Squid Management Portal on {config.HOST}:{config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=False)
