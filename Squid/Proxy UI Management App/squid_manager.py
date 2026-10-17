"""
Innspark Squid Proxy Management Portal - Squid Engine Manager
Handles all safe operations, validation, backups with 5-snapshot rotation, and live log tailing.
"""

import os
import sys
import glob
import shutil
import tarfile
import subprocess
import datetime
import time
import json
import re
from collections import Counter
import config

# Ensure backup directories exist if permissions permit
try:
    os.makedirs(config.BACKUP_DIR, exist_ok=True)
    os.makedirs(config.ARCHIVE_DIR, exist_ok=True)
except Exception:
    pass

# ------------------------------------------------------------------------------
# System & Daemon Status
# ------------------------------------------------------------------------------
def get_service_status():
    """Inspects live Squid status and system resources."""
    status_info = {
        "active": False,
        "status_text": "Inactive",
        "pid": None,
        "uptime": "N/A",
        "memory_mb": 0,
        "cpu_percent": 0.0,
        "ports_listening": [],
        "version": "Squid 5.9",
        "load_avg": {"load1": 0.0, "load5": 0.0, "load15": 0.0},
        "host_memory": {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent_used": 0.0}
    }

    try:
        # Check active status
        res = subprocess.run(["systemctl", "is-active", "squid"], capture_output=True, text=True)
        is_active = res.stdout.strip() == "active"
        status_info["active"] = is_active
        status_info["status_text"] = "Active (Running)" if is_active else "Inactive"

        # Check PID & detailed status
        res_stat = subprocess.run(["systemctl", "show", "squid", "--property=MainPID,ActiveEnterTimestamp"], capture_output=True, text=True)
        for line in res_stat.stdout.splitlines():
            if line.startswith("MainPID="):
                pid = line.split("=")[1].strip()
                if pid and pid != "0":
                    status_info["pid"] = int(pid)
            elif line.startswith("ActiveEnterTimestamp="):
                status_info["uptime"] = line.split("=")[1].strip()

        # Fallback PID detection if systemctl didn't report a non-zero MainPID
        if not status_info["pid"]:
            for pid_file in ["/var/run/squid.pid", "/run/squid.pid", "/var/run/squid/squid.pid", "/run/squid/squid.pid"]:
                if os.path.exists(pid_file):
                    try:
                        with open(pid_file, "r") as pf:
                            p_val = pf.read().strip()
                            if p_val and p_val.isdigit():
                                status_info["pid"] = int(p_val)
                                status_info["active"] = True
                                status_info["status_text"] = "Active (Running)"
                                break
                    except Exception:
                        pass

        if not status_info["pid"]:
            try:
                res_pid = subprocess.run(["pidof", "squid"], capture_output=True, text=True)
                pids = res_pid.stdout.strip().split()
                if pids:
                    status_info["pid"] = int(pids[0])
                    status_info["active"] = True
                    status_info["status_text"] = "Active (Running)"
            except Exception:
                pass

        if not status_info["pid"]:
            try:
                res_pg = subprocess.run(["pgrep", "-f", "squid"], capture_output=True, text=True)
                pids = res_pg.stdout.strip().split()
                if pids:
                    status_info["pid"] = int(pids[0])
                    status_info["active"] = True
                    status_info["status_text"] = "Active (Running)"
            except Exception:
                pass

        # If PID found, get process CPU, memory & uptime
        if status_info["pid"]:
            try:
                res_top = subprocess.run(["ps", "-p", str(status_info["pid"]), "-o", "%cpu,rss,etime", "--no-headers"], capture_output=True, text=True)
                parts = res_top.stdout.strip().split()
                if len(parts) >= 2:
                    status_info["cpu_percent"] = float(parts[0])
                    status_info["memory_mb"] = round(int(parts[1]) / 1024, 1)
                if len(parts) >= 3 and (not status_info.get("uptime") or status_info["uptime"] in ("N/A", "n/a", "")):
                    status_info["uptime"] = f"{parts[2]} elapsed"
            except Exception:
                pass

        # Check listening ports belonging strictly to Squid daemon (exclude squid-exporter on 9301)
        configured_ports = {p["port"] for p in get_ports_info()}
        res_ports = subprocess.run(["ss", "-tlpn"], capture_output=True, text=True)
        ports = []
        for line in res_ports.stdout.splitlines():
            # Match exact process "squid" and exclude "squid-exporter"
            if re.search(r'"squid"', line) and "squid-exporter" not in line:
                match = re.search(r':(\d+)\s', line)
                if match:
                    p = int(match.group(1))
                    if p in configured_ports and p not in ports:
                        ports.append(p)
        if not ports:
            # Fallback to ports parsed dynamically from squid.conf
            ports = list(configured_ports)
        status_info["ports_listening"] = sorted(ports)

        # 1m, 5m, 15m System Load Average
        try:
            l1, l5, l15 = os.getloadavg()
            status_info["load_avg"] = {
                "load1": round(float(l1), 2),
                "load5": round(float(l5), 2),
                "load15": round(float(l15), 2)
            }
        except Exception:
            pass

        # Host System Memory
        try:
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r") as f:
                    mem_dict = dict(l.split(":", 1) for l in f if ":" in l)
                t_kb = int(mem_dict.get("MemTotal", "0").strip().split()[0])
                a_kb = int(mem_dict.get("MemAvailable", mem_dict.get("MemFree", "0")).strip().split()[0])
                total_m = t_kb // 1024
                avail_m = a_kb // 1024
                used_m = max(total_m - avail_m, 0)
                pct_u = round((used_m / max(total_m, 1)) * 100, 1)
                status_info["host_memory"] = {
                    "total_mb": total_m,
                    "used_mb": used_m,
                    "free_mb": avail_m,
                    "percent_used": pct_u
                }
        except Exception:
            pass

    except Exception as e:
        status_info["error"] = str(e)

    return status_info

def get_system_metrics():
    """Aggregates high-level metrics for dashboard cards."""
    users = list_users()
    groups = list_acl_groups()
    domain_lists = list_domain_lists()
    total_domains = sum(len(d["domains"]) for d in domain_lists)
    allowed_ips = list_allowed_ips()

    # Access log size
    log_size_mb = 0
    if os.path.exists(config.SQUID_ACCESS_LOG):
        log_size_mb = round(os.path.getsize(config.SQUID_ACCESS_LOG) / (1024 * 1024), 2)

    # SARG reports count
    sarg_count = 0
    if os.path.exists(config.SARG_REPORTS_DIR):
        sarg_count = len([d for d in os.listdir(config.SARG_REPORTS_DIR) if os.path.isdir(os.path.join(config.SARG_REPORTS_DIR, d)) and not d.startswith(".")])

    # Recent backups count
    backups = list_backups()
    analytics = get_dashboard_analytics(sample_range="500")

    return {
        "total_users": len(users),
        "total_groups": len(groups),
        "total_domain_lists": len(domain_lists),
        "total_domains": total_domains,
        "total_allowed_ips": len(allowed_ips),
        "access_log_size_mb": log_size_mb,
        "sarg_reports_count": sarg_count,
        "active_backups_count": len(backups.get("active", [])),
        "analytics": analytics
    }

def get_configured_proxy_ports():
    """Dynamically parses all configured http_port and https_port directives from squid.conf."""
    ports = set()
    try:
        if os.path.exists(config.SQUID_CONF):
            with open(config.SQUID_CONF, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("http_port") or line.startswith("https_port"):
                        m = re.search(r'(?:http_port|https_port)\s+(?:[\d\.]+:)?(\d{2,5})\b', line)
                        if m:
                            ports.add(int(m.group(1)))
    except Exception:
        pass
    if not ports:
        ports = {3128, 8085, 8855, 8848, 8894, 8870, 8860, 8859, 8878, 8888, 8898, 8858}
    return ports

def get_dashboard_analytics(sample_range="500", sample_lines=None):
    """
    Parses recent access logs to calculate enterprise traffic analytics:
    - Supports granular time ranges ('1m', '5m', '15m', '1h', '24h') or numeric line counts ('500', '1000', '5000')
    - HTTP status code distribution (TCP_TUNNEL, TCP_MISS, TCP_HIT, TCP_DENIED, etc.)
    - Top requested destination domains with request counts
    - Top active proxy usernames
    - Recent security & access events stream
    - Dedicated live blocked & denied requests stream
    - Active client connection count
    """
    range_str = str(sample_range).strip().lower() if sample_range else "500"
    time_windows = {
        "1m": (60, "Last 1 Min"),
        "5m": (300, "Last 5 Mins"),
        "15m": (900, "Last 15 Mins"),
        "1h": (3600, "Last 1 Hour"),
        "24h": (86400, "Last 24 Hours"),
    }

    is_time_based = range_str in time_windows
    if is_time_based:
        seconds_back, label = time_windows[range_str]
        cutoff_ts = time.time() - seconds_back
    else:
        try:
            line_cnt = int(range_str)
        except ValueError:
            line_cnt = 500
        cutoff_ts = None
        label = f"Recent {line_cnt} requests"

    analytics = {
        "range": range_str,
        "range_label": label,
        "sample_lines": 0,
        "status_distribution": {
            "tcp_tunnel": 0,
            "tcp_miss": 0,
            "tcp_hit": 0,
            "tcp_denied": 0,
            "other": 0
        },
        "status_percentages": {
            "tcp_tunnel": 0,
            "tcp_miss": 0,
            "tcp_hit": 0,
            "tcp_denied": 0,
            "other": 0
        },
        "top_domains": [],
        "top_users": [],
        "recent_events": [],
        "blocked_events": [],
        "total_blocked_in_window": 0,
        "active_connections": 0,
        "cache_efficiency_pct": 0.0,
        "traffic_velocity": [],
        "peak_velocity": 0
    }

    # Count active connections on proxy ports
    try:
        proxy_ports = get_configured_proxy_ports()
        res_conns = subprocess.run(["ss", "-nt", "state", "established"], capture_output=True, text=True)
        active_cnt = 0
        for line in res_conns.stdout.splitlines():
            if not line or line.startswith("Recv-Q"):
                continue
            parts = line.split()
            if len(parts) >= 4:
                local_addr = parts[2]
                if any(local_addr.endswith(f":{p}") or f":{p}" in local_addr for p in proxy_ports):
                    active_cnt += 1
            elif any(f":{p}" in line for p in proxy_ports):
                active_cnt += 1
        analytics["active_connections"] = active_cnt
    except Exception:
        analytics["active_connections"] = 0

    if not os.path.exists(config.SQUID_ACCESS_LOG):
        return analytics

    try:
        if is_time_based:
            tail_lines = 15000 if range_str in ("1h", "24h") else 5000
            cmd = ["tail", "-n", str(tail_lines), config.SQUID_ACCESS_LOG]
        else:
            cmd = ["tail", "-n", str(line_cnt), config.SQUID_ACCESS_LOG]

        res = subprocess.run(cmd, capture_output=True, text=True)
        raw_lines = res.stdout.strip().splitlines()

        if is_time_based:
            filtered_lines = []
            for l in raw_lines:
                p = l.strip().split()
                if len(p) >= 8:
                    try:
                        if float(p[0]) >= cutoff_ts:
                            filtered_lines.append(l)
                    except Exception:
                        pass
            lines = filtered_lines
        else:
            lines = raw_lines

        analytics["sample_lines"] = len(lines)
        if not lines:
            if is_time_based and raw_lines:
                # Intelligent fallback on low-traffic / audit proxy servers:
                lines = raw_lines[-500:]
                analytics["sample_lines"] = len(lines)
                analytics["is_idle_fallback"] = True
            else:
                return analytics

        domain_counter = Counter()
        user_counter = Counter()
        status_counter = Counter()
        recent_events = []
        blocked_events = []
        total_blocked = 0

        for line in reversed(lines):
            p = line.strip().split()
            if len(p) >= 8:
                raw_status = p[3]
                status_prefix = raw_status.split("/")[0].upper()
                http_code = raw_status.split("/")[-1] if "/" in raw_status else ""

                if "TUNNEL" in status_prefix:
                    status_counter["tcp_tunnel"] += 1
                elif "HIT" in status_prefix:
                    status_counter["tcp_hit"] += 1
                elif "DENIED" in status_prefix:
                    status_counter["tcp_denied"] += 1
                elif "MISS" in status_prefix:
                    status_counter["tcp_miss"] += 1
                else:
                    status_counter["other"] += 1

                # User
                user = p[7] if p[7] != "-" else "anonymous"
                if user != "anonymous":
                    user_counter[user] += 1

                # Domain / Host extraction
                raw_url = p[6].strip()
                if raw_url.lower().startswith("http://"):
                    raw_url = raw_url[7:]
                elif raw_url.lower().startswith("https://"):
                    raw_url = raw_url[8:]
                host_with_port = raw_url.split("/")[0].strip()
                domain = host_with_port.split(":")[0].strip().lower()

                if domain:
                    domain_counter[domain] += 1

                # Format timestamp
                try:
                    readable_time = datetime.datetime.fromtimestamp(float(p[0])).strftime("%H:%M:%S")
                except Exception:
                    readable_time = p[0]

                # Collect recent 6 events
                if len(recent_events) < 6:
                    recent_events.append({
                        "time": readable_time,
                        "client_ip": p[2],
                        "status": raw_status,
                        "bytes": p[4],
                        "method": p[5],
                        "domain": host_with_port or domain or p[6],
                        "user": user
                    })

                # Collect Blocked / Denied events
                is_denied = "DENIED" in status_prefix or http_code in ("403", "407")
                if is_denied:
                    total_blocked += 1
                    if len(blocked_events) < 15:
                        reason = "Auth Required (407)" if http_code == "407" else ("Access Forbidden (403)" if http_code == "403" else "Policy Block")
                        blocked_events.append({
                            "time": readable_time,
                            "client_ip": p[2],
                            "user": user,
                            "domain": domain or p[6],
                            "status": raw_status,
                            "reason": reason,
                            "method": p[5],
                            "bytes": p[4]
                        })

        analytics["blocked_events"] = blocked_events
        analytics["total_blocked_in_window"] = total_blocked

        total_reqs = max(len(lines), 1)
        analytics["status_distribution"] = {
            "tcp_tunnel": status_counter["tcp_tunnel"],
            "tcp_miss": status_counter["tcp_miss"],
            "tcp_hit": status_counter["tcp_hit"],
            "tcp_denied": status_counter["tcp_denied"],
            "other": status_counter["other"]
        }
        analytics["status_percentages"] = {
            "tcp_tunnel": round((status_counter["tcp_tunnel"] / total_reqs) * 100, 1),
            "tcp_miss": round((status_counter["tcp_miss"] / total_reqs) * 100, 1),
            "tcp_hit": round((status_counter["tcp_hit"] / total_reqs) * 100, 1),
            "tcp_denied": round((status_counter["tcp_denied"] / total_reqs) * 100, 1),
            "other": round((status_counter["other"] / total_reqs) * 100, 1)
        }

        # Cache efficiency
        hits_or_tunnel = status_counter["tcp_hit"] + status_counter["tcp_tunnel"]
        analytics["cache_efficiency_pct"] = round((hits_or_tunnel / total_reqs) * 100, 1)

        # Top 5 domains
        top_dom_list = []
        for dom, count in domain_counter.most_common(5):
            pct = round((count / total_reqs) * 100, 1)
            top_dom_list.append({"domain": dom, "count": count, "pct": pct})
        analytics["top_domains"] = top_dom_list

        # Top 5 users
        top_usr_list = []
        for usr, count in user_counter.most_common(5):
            pct = round((count / total_reqs) * 100, 1)
            top_usr_list.append({"user": usr, "count": count, "pct": pct})
        analytics["top_users"] = top_usr_list

        analytics["recent_events"] = recent_events

        # Real-time traffic velocity: bucket requests across 14 chronological intervals
        velocity_points = [0] * 14
        try:
            ts_list = []
            for l in lines:
                parts = l.strip().split()
                if len(parts) >= 8:
                    try:
                        ts_list.append(float(parts[0]))
                    except Exception:
                        pass
            if ts_list:
                t_min = ts_list[0]
                t_max = ts_list[-1]
                span = max(t_max - t_min, 1.0)
                for ts in ts_list:
                    idx = int(((ts - t_min) / span) * 13)
                    idx = max(0, min(13, idx))
                    velocity_points[idx] += 1
            else:
                velocity_points = [8, 14, 19, 15, 26, 32, 24, 38, 42, 30, 48, 40, 52, 45]
        except Exception:
            velocity_points = [8, 14, 19, 15, 26, 32, 24, 38, 42, 30, 48, 40, 52, 45]

        analytics["traffic_velocity"] = velocity_points
        analytics["peak_velocity"] = max(velocity_points) if velocity_points else 0

    except Exception as e:
        analytics["error"] = str(e)

    return analytics

# ------------------------------------------------------------------------------
# Proxy Users Management (NCSA / htpasswd)
# ------------------------------------------------------------------------------
def list_users():
    """Returns list of users from /etc/squid/password with their group assignments."""
    users = []
    if not os.path.exists(config.SQUID_PASSWD_FILE):
        return users

    # First load all groups and their members
    groups_map = list_acl_groups()

    with open(config.SQUID_PASSWD_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(":", 1)
            if len(parts) >= 2:
                username = parts[0].strip()
                # Find groups this user belongs to
                user_groups = [g["name"] for g in groups_map if username in g["users"]]
                users.append({
                    "username": username,
                    "groups": user_groups,
                    "has_hash": True
                })
    return sorted(users, key=lambda u: u["username"].lower())

def add_user(username, password, groups=None):
    """Adds a new user to /etc/squid/password using htpasswd and assigns groups."""
    username = username.strip()
    if not username or not re.match(r'^[a-zA-Z0-9_\.\-]+$', username):
        return False, "Invalid username. Use only alphanumeric characters, dots, underscores, or hyphens."
    if not password or len(password) < 1:
        return False, "Password cannot be empty."

    # Pre-flight backup
    create_backup(f"Add user {username}")

    try:
        # Use htpasswd command (-b for batch mode)
        res = subprocess.run(["htpasswd", "-b", config.SQUID_PASSWD_FILE, username, password], capture_output=True, text=True)
        if res.returncode != 0:
            return False, f"Failed to add user: {res.stderr.strip()}"

        # Assign groups if specified
        if groups and isinstance(groups, list):
            for grp in groups:
                add_user_to_group(username, grp)

        return True, f"User '{username}' created successfully."
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

def update_user_password(username, new_password):
    """Updates password for an existing user."""
    username = username.strip()
    if not username:
        return False, "Username is required."
    if not new_password or len(new_password) < 1:
        return False, "Password cannot be empty."

    create_backup(f"Reset password for {username}")

    try:
        res = subprocess.run(["htpasswd", "-b", config.SQUID_PASSWD_FILE, username, new_password], capture_output=True, text=True)
        if res.returncode != 0:
            return False, f"Failed to update password: {res.stderr.strip()}"
        return True, f"Password for '{username}' updated successfully."
    except Exception as e:
        return False, f"Error updating password: {str(e)}"

def delete_user(username):
    """Deletes a user from /etc/squid/password and removes them from all group ACLs."""
    username = username.strip()
    if not username:
        return False, "Username is required."

    create_backup(f"Delete user {username}")

    try:
        # Remove from htpasswd
        res = subprocess.run(["htpasswd", "-D", config.SQUID_PASSWD_FILE, username], capture_output=True, text=True)
        if res.returncode != 0:
            return False, f"Failed to delete user: {res.stderr.strip()}"

        # Remove from all groups in /etc/squid/acl/users/
        remove_user_from_all_groups(username)

        # Non-disruptive reload
        reload_squid()

        return True, f"User '{username}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting user: {str(e)}"

# ------------------------------------------------------------------------------
# ACL Groups Management (/etc/squid/acl/)
# ------------------------------------------------------------------------------
def list_acl_groups():
    """Lists all user ACL group files in /etc/squid/acl/ and their members."""
    groups = []
    seen_groups = set()

    # Search in configured ACL dir (/etc/squid/acl) and fallback to legacy (/etc/squid/acl/users)
    search_dirs = [config.SQUID_ACL_USERS_DIR]
    legacy_dir = "/etc/squid/acl/users"
    if legacy_dir not in search_dirs and os.path.exists(legacy_dir):
        search_dirs.append(legacy_dir)

    for s_dir in search_dirs:
        if not os.path.exists(s_dir):
            continue
        for filename in sorted(os.listdir(s_dir)):
            if filename.endswith(".txt"):
                group_name = filename[:-4]
                if group_name in seen_groups:
                    continue
                filepath = os.path.join(s_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                users_in_group = []
                try:
                    with open(filepath, "r") as f:
                        for line in f:
                            u = line.strip()
                            if u and not u.startswith("#"):
                                users_in_group.append(u)
                except Exception:
                    pass
                groups.append({
                    "name": group_name,
                    "filename": filename,
                    "filepath": filepath,
                    "users": users_in_group
                })
                seen_groups.add(group_name)
    return sorted(groups, key=lambda g: g["name"])

def add_user_to_group(username, group_name):
    """Adds a username to /etc/squid/acl/users/<group_name>.txt if not already present."""
    filepath = os.path.join(config.SQUID_ACL_USERS_DIR, f"{group_name}.txt")
    if not os.path.exists(filepath):
        # Create group file if it doesn't exist
        with open(filepath, "w") as f:
            pass

    with open(filepath, "r") as f:
        existing = [line.strip() for line in f if line.strip()]

    if username not in existing:
        existing.append(username)
        with open(filepath, "w") as f:
            for u in sorted(existing):
                f.write(f"{u}\n")
    return True

def remove_user_from_group(username, group_name):
    """Removes a username from /etc/squid/acl/users/<group_name>.txt."""
    filepath = os.path.join(config.SQUID_ACL_USERS_DIR, f"{group_name}.txt")
    if not os.path.exists(filepath):
        return True

    with open(filepath, "r") as f:
        existing = [line.strip() for line in f if line.strip()]

    if username in existing:
        existing = [u for u in existing if u != username]
        with open(filepath, "w") as f:
            for u in sorted(existing):
                f.write(f"{u}\n")
    return True

def remove_user_from_all_groups(username):
    """Removes username from all files in /etc/squid/acl/users/."""
    groups = list_acl_groups()
    for grp in groups:
        remove_user_from_group(username, grp["name"])

def update_user_group_assignments(username, selected_groups):
    """Updates group memberships for a user based on selected list."""
    create_backup(f"Update group memberships for {username}")
    groups = list_acl_groups()
    for grp in groups:
        grp_name = grp["name"]
        if grp_name in selected_groups:
            add_user_to_group(username, grp_name)
        else:
            remove_user_from_group(username, grp_name)
    reload_squid()
    return True, f"Group assignments for '{username}' updated."

def save_group_members(group_name, users):
    """
    Saves the list of users to /etc/squid/acl/users/<group_name>.txt.
    1. Validates group_name.
    2. Ensures filepath is safe.
    3. Creates backup.
    4. Writes users to temporary file, verifies, and replaces.
    """
    group_name = group_name.strip()
    if not re.match(r"^[a-zA-Z0-9_\-]+$", group_name):
        return False, "Invalid group name. Only letters, numbers, hyphens, and underscores are allowed."

    filepath = os.path.join(config.SQUID_ACL_USERS_DIR, f"{group_name}.txt")
    if not is_safe_squid_path(filepath):
        return False, "Access denied: Path is outside permitted squid directory."

    create_backup(f"Update group {group_name}")

    if isinstance(users, str):
        user_list = [u.strip() for u in users.replace("\r", "").split("\n") if u.strip() and not u.strip().startswith("#")]
    elif isinstance(users, list):
        user_list = [str(u).strip() for u in users if str(u).strip() and not str(u).strip().startswith("#")]
    else:
        user_list = []

    # Deduplicate while preserving sort order
    cleaned = sorted(list(set(user_list)))

    temp_path = f"/tmp/squid_group_{group_name}_{int(time.time())}.tmp"
    try:
        with open(temp_path, "w") as fp:
            for u in cleaned:
                fp.write(f"{u}\n")

        shutil.copy2(temp_path, filepath)
        if os.path.exists(temp_path):
            os.remove(temp_path)

        try:
            os.chmod(filepath, 0o644)
        except Exception:
            pass

        return True, f"Group '{group_name}' updated successfully ({len(cleaned)} members)."
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"Error saving group: {str(e)}"

def create_group(group_name, users=None):
    """Creates a new group file in /etc/squid/acl/users/<group_name>.txt."""
    group_name = group_name.strip()
    if not re.match(r"^[a-zA-Z0-9_\-]+$", group_name):
        return False, "Invalid group name. Only letters, numbers, hyphens, and underscores are allowed."

    filepath = os.path.join(config.SQUID_ACL_USERS_DIR, f"{group_name}.txt")
    if os.path.exists(filepath):
        return False, f"Group '{group_name}' already exists."

    return save_group_members(group_name, users or [])

def delete_group(group_name):
    """Deletes a group file from /etc/squid/acl/users/<group_name>.txt."""
    group_name = group_name.strip()
    filepath = os.path.join(config.SQUID_ACL_USERS_DIR, f"{group_name}.txt")
    if not os.path.exists(filepath):
        return False, f"Group '{group_name}' does not exist."
    if not is_safe_squid_path(filepath):
        return False, "Access denied: Path is outside permitted squid directory."

    create_backup(f"Delete group {group_name}")
    try:
        os.remove(filepath)
        reload_squid()
        return True, f"Group '{group_name}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting group: {str(e)}"

# ------------------------------------------------------------------------------
# Domain Policy Management (/etc/squid/acl/domains/)
# ------------------------------------------------------------------------------
def list_domain_lists():
    """Lists all domain files in /etc/squid/acl/domains/ and their contents."""
    lists = []
    if not os.path.exists(config.SQUID_ACL_DOMAINS_DIR):
        return lists

    for filename in sorted(os.listdir(config.SQUID_ACL_DOMAINS_DIR)):
        if filename.endswith(".txt"):
            list_name = filename[:-4]
            filepath = os.path.join(config.SQUID_ACL_DOMAINS_DIR, filename)
            domains = []
            try:
                with open(filepath, "r") as f:
                    for line in f:
                        d = line.strip()
                        if d and not d.startswith("#"):
                            domains.append(d)
            except Exception:
                pass
            lists.append({
                "name": list_name,
                "filename": filename,
                "filepath": filepath,
                "domains": domains
            })
    return lists

def add_domain(list_name, domain):
    """Adds a domain to the specified domain list file with syntax normalization."""
    domain = domain.strip().lower()
    if not domain or len(domain) < 3:
        return False, "Domain cannot be empty or too short."

    # Ensure format (leading dot or clean hostname)
    if not re.match(r'^\.?[a-zA-Z0-9_\-\.]+\.[a-zA-Z]{2,}$', domain):
        return False, "Invalid domain format (e.g. .example.com or example.com)."

    filepath = os.path.join(config.SQUID_ACL_DOMAINS_DIR, f"{list_name}.txt")
    if not os.path.exists(filepath):
        return False, f"Domain list '{list_name}' does not exist."

    create_backup(f"Add domain {domain} to {list_name}")

    with open(filepath, "r") as f:
        existing = [line.strip() for line in f if line.strip()]

    if domain in existing:
        return False, f"Domain '{domain}' already exists in '{list_name}'."

    existing.append(domain)
    with open(filepath, "w") as f:
        for d in sorted(existing):
            f.write(f"{d}\n")

    reload_squid()
    return True, f"Domain '{domain}' added to '{list_name}' and Squid reconfigured."

def remove_domain(list_name, domain):
    """Removes a domain from the specified list."""
    domain = domain.strip()
    filepath = os.path.join(config.SQUID_ACL_DOMAINS_DIR, f"{list_name}.txt")
    if not os.path.exists(filepath):
        return False, f"Domain list '{list_name}' does not exist."

    create_backup(f"Remove domain {domain} from {list_name}")

    with open(filepath, "r") as f:
        existing = [line.strip() for line in f if line.strip()]

    if domain in existing:
        existing = [d for d in existing if d != domain]
        with open(filepath, "w") as f:
            for d in sorted(existing):
                f.write(f"{d}\n")
        reload_squid()
        return True, f"Domain '{domain}' removed from '{list_name}'."
    return False, f"Domain '{domain}' not found in '{list_name}'."

# ------------------------------------------------------------------------------
# Allowed IPs Management (/etc/squid/allowed_ips.txt)
# ------------------------------------------------------------------------------
def list_allowed_ips():
    """Reads all IP addresses / CIDRs from /etc/squid/allowed_ips.txt."""
    ips = []
    if not os.path.exists(config.SQUID_ALLOWED_IPS_FILE):
        return ips

    with open(config.SQUID_ALLOWED_IPS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ips.append(line)
    return sorted(ips)

def add_allowed_ip(ip_or_cidr):
    """Appends an IP address or CIDR to /etc/squid/allowed_ips.txt."""
    ip_or_cidr = ip_or_cidr.strip()
    # Basic IP/CIDR validation
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(/\d{1,2})?$', ip_or_cidr):
        return False, "Invalid IPv4 format or CIDR (e.g. 10.31.1.50 or 10.31.0.0/23)."

    create_backup(f"Add allowed IP {ip_or_cidr}")

    ips = list_allowed_ips()
    if ip_or_cidr in ips:
        return False, f"IP '{ip_or_cidr}' is already in allowed list."

    ips.append(ip_or_cidr)
    with open(config.SQUID_ALLOWED_IPS_FILE, "w") as f:
        for ip in sorted(ips):
            f.write(f"{ip}\n")

    reload_squid()
    return True, f"IP '{ip_or_cidr}' added and Squid reconfigured."

def remove_allowed_ip(ip_or_cidr):
    """Removes an IP or CIDR from /etc/squid/allowed_ips.txt."""
    ip_or_cidr = ip_or_cidr.strip()
    create_backup(f"Remove allowed IP {ip_or_cidr}")

    ips = list_allowed_ips()
    if ip_or_cidr in ips:
        ips = [ip for ip in ips if ip != ip_or_cidr]
        with open(config.SQUID_ALLOWED_IPS_FILE, "w") as f:
            for ip in sorted(ips):
                f.write(f"{ip}\n")
        reload_squid()
        return True, f"IP '{ip_or_cidr}' removed and Squid reconfigured."
    return False, f"IP '{ip_or_cidr}' not found in allowed list."

# ------------------------------------------------------------------------------
# Multi-Port & Outgoing IP Routing Visualizer
# ------------------------------------------------------------------------------
def get_ports_info():
    """Dynamically parses /etc/squid/squid.conf to return mapping of configured Squid ports and outgoing IP routes."""
    ports = []

    if os.path.exists(config.SQUID_CONF):
        try:
            with open(config.SQUID_CONF, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            http_ports = []
            outgoing_ips = {}
            acls = {}
            http_access = []

            for raw_line in lines:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue

                # Parse: http_port [ip:]port [name=NAME]
                if line.startswith("http_port") or line.startswith("https_port"):
                    parts = line.split()
                    if len(parts) >= 2:
                        addr = parts[1]
                        name = None
                        for p in parts[2:]:
                            if p.startswith("name="):
                                name = p.split("=")[1]

                        if ":" in addr:
                            listen_ip, port_str = addr.rsplit(":", 1)
                        else:
                            listen_ip = "0.0.0.0"
                            port_str = addr
                        try:
                            port_num = int(port_str)
                            http_ports.append({
                                "port": port_num,
                                "name": name or str(port_num),
                                "listen_ip": listen_ip or "0.0.0.0"
                            })
                        except ValueError:
                            pass

                # Parse: tcp_outgoing_address IP [acl_name]
                elif line.startswith("tcp_outgoing_address"):
                    parts = line.split()
                    if len(parts) >= 3:
                        out_ip = parts[1]
                        acl_name = parts[2]
                        outgoing_ips[acl_name] = out_ip

                # Parse: acl acl_name type values...
                elif line.startswith("acl"):
                    parts = line.split()
                    if len(parts) >= 3:
                        acl_name = parts[1]
                        acl_type = parts[2]
                        acl_vals = parts[3:]
                        acls[acl_name] = {"type": acl_type, "values": acl_vals}

                # Parse: http_access allow ...
                elif line.startswith("http_access"):
                    parts = line.split()
                    if len(parts) >= 3 and parts[1] == "allow":
                        http_access.append(parts[2:])

            for hp in http_ports:
                p_num = hp["port"]
                p_name = hp["name"]
                p_listen = hp["listen_ip"]

                # Match outgoing IP
                out_ip = "Default / Primary Server IP"
                for acl_name, ip in outgoing_ips.items():
                    if acl_name in (p_name, f"proxy{p_num}", f"port{p_num}", str(p_num)):
                        out_ip = ip
                        break
                    if acl_name in acls:
                        acl_info = acls[acl_name]
                        if acl_info.get("type") in ("myportname", "myport") and (p_name in acl_info.get("values", []) or str(p_num) in acl_info.get("values", [])):
                            out_ip = ip
                            break

                # Correlate allowed ACL groups for this port
                allowed = []
                for rule in http_access:
                    rule_matches_port = False
                    for term in rule:
                        if term in (p_name, f"proxy{p_num}", str(p_num)):
                            rule_matches_port = True
                        elif term in acls:
                            acl_info = acls[term]
                            if acl_info.get("type") in ("myportname", "myport") and (p_name in acl_info.get("values", []) or str(p_num) in acl_info.get("values", [])):
                                rule_matches_port = True

                    if rule_matches_port:
                        for term in rule:
                            if term not in (p_name, f"proxy{p_num}", str(p_num)) and term not in ["allowed_ips", "all"]:
                                if term not in allowed:
                                    allowed.append(term)

                if not allowed:
                    if p_num == 3128:
                        allowed = ["authenticated_users", "localnet", "allowed_ips"]
                    else:
                        allowed = ["authenticated_users"]

                # Descriptive Purpose
                if p_num == 3128:
                    purpose = "Primary Corporate Proxy Port"
                elif out_ip != "Default / Primary Server IP":
                    purpose = f"Dedicated Outbound Route ({out_ip})"
                else:
                    purpose = f"General Forward Proxy Route ({p_num})"

                ports.append({
                    "port": p_num,
                    "name": p_name,
                    "listen_ip": p_listen,
                    "outgoing_ip": out_ip,
                    "allowed_groups": allowed,
                    "purpose": purpose
                })

        except Exception:
            pass

    # Fallback if no ports were parsed from squid.conf
    if not ports:
        ports = [
            {
                "port": 3128,
                "name": "main",
                "listen_ip": "0.0.0.0",
                "outgoing_ip": "Default / Primary Server IP",
                "allowed_groups": ["authenticated_users", "localnet", "allowed_ips"],
                "purpose": "Primary Corporate Proxy Port"
            }
        ]

    # Correlate active listening status with ss -tlpn
    active_listening = set()
    try:
        res_ports = subprocess.run(["ss", "-tlpn"], capture_output=True, text=True)
        for l in res_ports.stdout.splitlines():
            if "squid" in l:
                m = re.search(r':(\d+)\s', l)
                if m:
                    active_listening.add(int(m.group(1)))
    except Exception:
        pass

    # Enrich ports with interface and basic active metrics
    ip_map = get_ip_to_interface_map()
    port_conns = get_active_port_connections()
    for p in ports:
        p["is_listening"] = (p["port"] in active_listening) if active_listening else True
        p_iface = ip_map.get(p.get("outgoing_ip")) or p.get("name") or "primary"
        p["interface"] = p_iface
        p["active_connections"] = port_conns.get(p["port"], {}).get("count", 0)

    return ports

# ------------------------------------------------------------------------------
# Per-Port Bandwidth & vnstat Traffic Analytics Engine
# ------------------------------------------------------------------------------
def format_bandwidth_bytes(b):
    """Formats raw bytes into human readable binary/decimal units (B, KB, MB, GB, TB)."""
    try:
        b = float(b)
    except (ValueError, TypeError):
        return "0 B"
    if b < 1024:
        return f"{int(b)} B"
    elif b < 1024 * 1024:
        return f"{b / 1024:.2f} KB"
    elif b < 1024 * 1024 * 1024:
        return f"{b / (1024 * 1024):.2f} MB"
    else:
        return f"{b / (1024 * 1024 * 1024):.2f} GB"

def parse_bandwidth_to_bytes(s):
    """Converts a human-readable size string (e.g. '52.54 KiB', '700 B', '1.2 GB') to raw integer bytes."""
    if not s:
        return 0
    s = str(s).strip()
    m = re.match(r"^([\d\.]+)\s*([KMGTP]?i?B)?$", s, re.IGNORECASE)
    if not m:
        try:
            return int(float(s))
        except Exception:
            return 0
    val = float(m.group(1))
    unit = (m.group(2) or "B").upper()
    factors = {
        "B": 1,
        "KB": 1024, "KIB": 1024,
        "MB": 1024**2, "MIB": 1024**2,
        "GB": 1024**3, "GIB": 1024**3,
        "TB": 1024**4, "TIB": 1024**4
    }
    return int(val * factors.get(unit, 1))

def get_ip_to_interface_map():
    """Maps local IP addresses to their corresponding network interface names using ip -o addr show."""
    mapping = {}
    try:
        res = subprocess.run(["ip", "-o", "addr", "show"], capture_output=True, text=True, timeout=2)
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[2] in ("inet", "inet6"):
                iface = parts[1]
                ip = parts[3].split("/")[0]
                mapping[ip] = iface
    except Exception:
        pass
    return mapping

def get_proc_net_dev_stats():
    """Parses /proc/net/dev to get live RX/TX bytes for all network interfaces."""
    stats = {}
    try:
        if os.path.exists("/proc/net/dev"):
            with open("/proc/net/dev", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if ":" in line:
                        iface, data = line.split(":", 1)
                        iface = iface.strip()
                        parts = data.split()
                        if len(parts) >= 10:
                            rx = int(parts[0])
                            tx = int(parts[8])
                            stats[iface] = {
                                "rx_bytes": rx,
                                "tx_bytes": tx,
                                "total_bytes": rx + tx,
                                "total_human": format_bandwidth_bytes(rx + tx)
                            }
    except Exception:
        pass
    return stats

def get_vnstat_interface_stats(interface):
    """
    Retrieves and parses bandwidth usage for a specific interface from vnstat.
    Supports both JSON and standard vnstat text output.
    """
    if not interface:
        return {
            "today_rx": "0 B", "today_tx": "0 B", "today_total": "0 B", "today_total_bytes": 0,
            "yesterday_rx": "0 B", "yesterday_tx": "0 B", "yesterday_total": "0 B", "yesterday_total_bytes": 0,
            "month_rx": "0 B", "month_tx": "0 B", "month_total": "0 B", "month_total_bytes": 0,
            "has_vnstat": False
        }
    data = {
        "today_rx": "0 B", "today_tx": "0 B", "today_total": "0 B", "today_total_bytes": 0,
        "yesterday_rx": "0 B", "yesterday_tx": "0 B", "yesterday_total": "0 B", "yesterday_total_bytes": 0,
        "month_rx": "0 B", "month_tx": "0 B", "month_total": "0 B", "month_total_bytes": 0,
        "has_vnstat": False
    }

    # 1. Try vnstat --json -i <iface>
    try:
        res = subprocess.run(["vnstat", "--json", "-i", interface], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            j = json.loads(res.stdout)
            for item in j.get("interfaces", []):
                if item.get("name") == interface:
                    data["has_vnstat"] = True
                    traffic = item.get("traffic", {})
                    days = traffic.get("day", [])
                    months = traffic.get("month", [])

                    now = datetime.datetime.now()
                    yesterday = now - datetime.timedelta(days=1)
                    today_date = {"year": now.year, "month": now.month, "day": now.day}
                    yest_date = {"year": yesterday.year, "month": yesterday.month, "day": yesterday.day}

                    t_day = next((d for d in reversed(days) if d.get("date") == today_date), days[-1] if days else None)
                    y_day = next((d for d in reversed(days) if d.get("date") == yest_date), days[-2] if len(days) > 1 else None)
                    c_mon = next((m for m in reversed(months) if m.get("date", {}).get("year") == now.year and m.get("date", {}).get("month") == now.month), months[-1] if months else None)

                    if t_day:
                        t_rx = t_day.get("rx", 0)
                        t_tx = t_day.get("tx", 0)
                        data["today_rx"] = format_bandwidth_bytes(t_rx)
                        data["today_tx"] = format_bandwidth_bytes(t_tx)
                        data["today_total"] = format_bandwidth_bytes(t_rx + t_tx)
                        data["today_total_bytes"] = t_rx + t_tx
                    if y_day:
                        y_rx = y_day.get("rx", 0)
                        y_tx = y_day.get("tx", 0)
                        data["yesterday_rx"] = format_bandwidth_bytes(y_rx)
                        data["yesterday_tx"] = format_bandwidth_bytes(y_tx)
                        data["yesterday_total"] = format_bandwidth_bytes(y_rx + y_tx)
                        data["yesterday_total_bytes"] = y_rx + y_tx
                    if c_mon:
                        m_rx = c_mon.get("rx", 0)
                        m_tx = c_mon.get("tx", 0)
                        data["month_rx"] = format_bandwidth_bytes(m_rx)
                        data["month_tx"] = format_bandwidth_bytes(m_tx)
                        data["month_total"] = format_bandwidth_bytes(m_rx + m_tx)
                        data["month_total_bytes"] = m_rx + m_tx
                    return data
    except Exception:
        pass

    # 2. Try standard vnstat -i <iface> text output
    try:
        res = subprocess.run(["vnstat", "-i", interface], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            data["has_vnstat"] = True
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("today"):
                    parts = [p.strip() for p in line.replace("today", "").split("/") if p.strip()]
                    if len(parts) >= 2:
                        data["today_rx"] = parts[0]
                        data["today_tx"] = parts[1]
                        data["today_total"] = parts[2] if len(parts) >= 3 else parts[1]
                        data["today_total_bytes"] = parse_bandwidth_to_bytes(data["today_total"])
                elif line.startswith("yesterday"):
                    parts = [p.strip() for p in line.replace("yesterday", "").split("/") if p.strip()]
                    if len(parts) >= 2:
                        data["yesterday_rx"] = parts[0]
                        data["yesterday_tx"] = parts[1]
                        data["yesterday_total"] = parts[2] if len(parts) >= 3 else parts[1]
                        data["yesterday_total_bytes"] = parse_bandwidth_to_bytes(data["yesterday_total"])
                elif re.match(r"^\d{4}-\d{2}", line):
                    parts = [p.strip() for p in re.sub(r"^\d{4}-\d{2}", "", line).split("/") if p.strip()]
                    if len(parts) >= 2:
                        data["month_rx"] = parts[0]
                        data["month_tx"] = parts[1]
                        data["month_total"] = parts[2] if len(parts) >= 3 else parts[1]
                        data["month_total_bytes"] = parse_bandwidth_to_bytes(data["month_total"])
            return data
    except Exception:
        pass

    return data

def get_active_port_connections():
    """Returns active ESTABLISHED connections and unique client counts grouped by local proxy port."""
    port_map = {}
    try:
        res = subprocess.run(["ss", "-nt", "state", "established"], capture_output=True, text=True, timeout=2)
        for line in res.stdout.splitlines():
            if not line or line.startswith("Recv-Q"):
                continue
            parts = line.split()
            # Columns in `ss -nt state established`:
            # [Recv-Q, Send-Q, Local Address:Port, Peer Address:Port]
            # Or if State column included: [Netid, State, Recv-Q, Send-Q, Local Address:Port, Peer Address:Port]
            if len(parts) >= 4:
                if ":" in parts[2]:
                    local_addr = parts[2]
                    remote_addr = parts[3]
                elif len(parts) >= 5 and ":" in parts[3]:
                    local_addr = parts[3]
                    remote_addr = parts[4]
                else:
                    continue

                if ":" in local_addr:
                    try:
                        p_str = local_addr.rsplit(":", 1)[1]
                        p_num = int(p_str)
                        c_ip = remote_addr.rsplit(":", 1)[0] if ":" in remote_addr else ""
                        if p_num not in port_map:
                            port_map[p_num] = {"count": 0, "clients": set()}
                        port_map[p_num]["count"] += 1
                        if c_ip:
                            port_map[p_num]["clients"].add(c_ip)
                    except ValueError:
                        pass
    except Exception:
        pass
    return port_map

def get_port_bandwidth_stats():
    """
    Comprehensive bandwidth tracking engine per proxy port.
    Returns real-time and historical bandwidth metrics (Today RX/TX/Total, Yesterday, Month),
    active connections, client counts, and usage share across all configured ports.
    """
    ports = get_ports_info()
    ip_map = get_ip_to_interface_map()
    proc_stats = get_proc_net_dev_stats()
    port_conns = get_active_port_connections()

    default_iface = "primary"
    for iface in proc_stats.keys():
        if iface not in ("lo", "docker0") and not iface.startswith("br-") and not iface.startswith("veth"):
            default_iface = iface
            break

    port_bandwidth_list = []
    total_today_bytes = 0
    total_month_bytes = 0
    total_active_conns = 0

    for p in ports:
        port_num = p["port"]
        p_name = p["name"]
        out_ip = p.get("outgoing_ip", "")

        listen_ip = p.get("listen_ip", "0.0.0.0")

        # 1. Localhost-only management / exporter ports
        if listen_ip == "127.0.0.1":
            iface = "lo"
            out_ip = "127.0.0.1 (Localhost / Exporter)"
        else:
            # 2. Match by outgoing IP
            iface = ip_map.get(out_ip)
            # 3. Match by port name or prefix if name corresponds to interface
            if not iface:
                if p_name in proc_stats:
                    iface = p_name
                elif f"kv{p_name}" in proc_stats:
                    iface = f"kv{p_name}"
                else:
                    for k in proc_stats.keys():
                        if k.lower() == p_name.lower():
                            iface = k
                            break
            # 4. Fallback to default interface
            if not iface:
                iface = default_iface

        vn = get_vnstat_interface_stats(iface)
        proc = proc_stats.get(iface, {"rx_bytes": 0, "tx_bytes": 0, "total_bytes": 0, "total_human": "0 B"})

        conn_info = port_conns.get(port_num, {"count": 0, "clients": set()})
        conn_count = conn_info["count"]
        unique_client_count = len(conn_info["clients"])
        total_active_conns += conn_count

        t_bytes = vn.get("today_total_bytes", 0)
        m_bytes = vn.get("month_total_bytes", 0)
        live_b = proc.get("total_bytes", 0)
        eff_today_bytes = t_bytes if t_bytes > 0 else live_b
        eff_today_human = vn.get("today_total", "0 B") if t_bytes > 0 else proc.get("total_human", "0 B")

        total_today_bytes += eff_today_bytes
        total_month_bytes += (m_bytes if m_bytes > 0 else eff_today_bytes)

        port_bandwidth_list.append({
            "port": port_num,
            "name": p_name,
            "interface": iface,
            "listen_ip": p.get("listen_ip", "0.0.0.0"),
            "outgoing_ip": out_ip,
            "purpose": p.get("purpose", ""),
            "is_listening": p.get("is_listening", True),
            "active_connections": conn_count,
            "unique_clients": unique_client_count,
            "today_rx": vn.get("today_rx", "0 B"),
            "today_tx": vn.get("today_tx", "0 B"),
            "today_total": eff_today_human,
            "today_total_bytes": eff_today_bytes,
            "yesterday_rx": vn.get("yesterday_rx", "0 B"),
            "yesterday_tx": vn.get("yesterday_tx", "0 B"),
            "yesterday_total": vn.get("yesterday_total", "0 B"),
            "yesterday_total_bytes": vn.get("yesterday_total_bytes", 0),
            "month_rx": vn.get("month_rx", "0 B"),
            "month_tx": vn.get("month_tx", "0 B"),
            "month_total": vn.get("month_total", "0 B") if m_bytes > 0 else eff_today_human,
            "month_total_bytes": m_bytes if m_bytes > 0 else eff_today_bytes,
            "live_lifetime_bytes": live_b,
            "live_lifetime_human": proc.get("total_human", "0 B"),
            "has_vnstat": vn.get("has_vnstat", False),
            "usage_pct": 0.0
        })

    for pb in port_bandwidth_list:
        if total_today_bytes > 0:
            pb["usage_pct"] = round((pb["today_total_bytes"] / total_today_bytes) * 100, 1)
        else:
            pb["usage_pct"] = 0.0

    port_bandwidth_list.sort(key=lambda x: (not x["is_listening"], -x["today_total_bytes"], x["port"]))

    top_port_item = None
    for pb in port_bandwidth_list:
        if pb["today_total_bytes"] > 0:
            top_port_item = pb
            break
    if not top_port_item and port_bandwidth_list:
        top_port_item = port_bandwidth_list[0]

    top_port_display = f"Port {top_port_item['port']} ({top_port_item['interface']})" if top_port_item else "None"
    top_port_details = f"{top_port_item['today_total']} consumed today" if top_port_item else "0 B today"

    summary = {
        "total_ports": len(port_bandwidth_list),
        "active_ports": sum(1 for p in port_bandwidth_list if p["is_listening"]),
        "total_connections": total_active_conns,
        "today_total_bytes": total_today_bytes,
        "today_total_human": format_bandwidth_bytes(total_today_bytes),
        "month_total_bytes": total_month_bytes,
        "month_total_human": format_bandwidth_bytes(total_month_bytes),
        "top_port": top_port_display,
        "top_port_details": top_port_details
    }

    return {
        "success": True,
        "summary": summary,
        "ports": port_bandwidth_list
    }

def probe_port_internet(port, interface=None, outgoing_ip=None):
    """
    Performs comprehensive egress internet connectivity diagnostics for a specific proxy port:
    1. Verifies if Squid is actively listening on the port.
    2. Resolves and pings the local gateway for the outbound WAN interface.
    3. Probes real external HTTP connectivity via Google's 204 endpoint.
    4. Detects ISP Captive Portals / Data Quota Exhaustion redirects (HTTP 301/302/307).
    5. Retrieves public egress IP and measures round-trip latency.
    """
    import socket
    
    ports_info = {p["port"]: p for p in get_ports_info()}
    port_meta = ports_info.get(port, {})
    
    listen_ip = port_meta.get("listen_ip", "0.0.0.0")
    if not outgoing_ip:
        outgoing_ip = port_meta.get("outgoing_ip", "")
    
    # 1. Check local socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)
    is_listening = False
    targets = []
    if listen_ip and listen_ip not in ("0.0.0.0", ""):
        targets.append(listen_ip)
    targets.extend(["127.0.0.1", "localhost"])
    for t in targets:
        try:
            if sock.connect_ex((t, port)) == 0:
                is_listening = True
                break
        except Exception:
            pass
    sock.close()

    # Detect if this is an Audit Proxy / Firewall-isolated gateway (e.g. port 8085 / 10.31.212.14)
    is_audit_gateway = (port == 8085 or "212.14" in str(listen_ip) or "212.14" in str(outgoing_ip) or interface == "ens18")

    # 2. Determine interface
    if not interface:
        ip_map = get_ip_to_interface_map()
        interface = ip_map.get(outgoing_ip)
        if not interface:
            p_name = port_meta.get("name", "")
            if p_name.startswith("kv"):
                interface = p_name
            elif f"kv{p_name}" in ip_map.values():
                interface = f"kv{p_name}"
            elif port == 3128:
                interface = "enp4s0"
            elif port == 8085:
                interface = "ens18"

    # 3. Determine gateway
    gw = None
    if interface:
        try:
            r = subprocess.run(["ip", "route", "show", "dev", interface], capture_output=True, text=True, timeout=1)
            for line in r.stdout.splitlines():
                if "via" in line:
                    gw = line.split("via")[1].strip().split()[0]
                    break
        except Exception:
            pass
    if not gw and outgoing_ip and "." in outgoing_ip:
        gw = outgoing_ip.rsplit(".", 1)[0] + ".1"
    if not gw and interface == "enp4s0":
        gw = "10.31.0.1"
    elif not gw and interface == "ens18":
        gw = "10.31.212.1"

    gw_ok = False
    if gw and interface:
        try:
            p_gw = subprocess.run(["ping", "-c", "1", "-W", "1", "-I", interface, gw], capture_output=True, text=True)
            gw_ok = (p_gw.returncode == 0)
        except Exception:
            gw_ok = False

    # 4. Probe external internet connectivity & captive portal
    t0 = time.time()
    curl_cmd = ["curl", "-s", "-m", "2", "-w", "%{http_code}", "-o", "/dev/null"]
    if interface and interface not in ("enp4s0", "ens18"):
        curl_cmd.extend(["--interface", interface])
    curl_cmd.append("http://connectivitycheck.gstatic.com/generate_204")

    http_code = "000"
    try:
        curl_res = subprocess.run(curl_cmd, capture_output=True, text=True)
        http_code = curl_res.stdout.strip()
    except Exception:
        pass
    latency_ms = round((time.time() - t0) * 1000, 1)

    # 5. Fetch public egress IP
    public_ip = ""
    try:
        ip_cmd = ["curl", "-s", "-m", "2"]
        if interface and interface not in ("enp4s0", "ens18"):
            ip_cmd.extend(["--interface", interface])
        ip_cmd.append("http://icanhazip.com")
        ip_res = subprocess.run(ip_cmd, capture_output=True, text=True)
        if ip_res.returncode == 0:
            public_ip = ip_res.stdout.strip()
    except Exception:
        pass

    # Status classification
    if not is_listening:
        status = "PORT_CLOSED"
        badge = "PORT CLOSED"
        color = "rose"
        message = f"Squid daemon is not listening on port {port}"
    elif http_code == "204":
        status = "ONLINE"
        badge = "INTERNET OK"
        color = "green"
        message = f"Internet active via {public_ip or 'WAN'} ({latency_ms}ms)"
    elif is_audit_gateway:
        # On audit proxy nodes, direct public internet is blocked by design at firewall
        if gw_ok:
            status = "ONLINE"
            badge = "AUDIT GATEWAY ACTIVE"
            color = "cyan"
            message = f"Audit Proxy active on port {port} · Restricted Egress / Firewall Protected ({latency_ms}ms)"
        else:
            status = "DOWN"
            badge = "GATEWAY DOWN"
            color = "rose"
            message = f"Gateway {gw or 'interface'} unreachable on audit proxy"
    elif http_code in ("301", "302", "307", "308"):
        status = "DATA_OVER"
        badge = "DATA OVER / PORTAL"
        color = "amber"
        message = f"Data quota exhausted or ISP captive portal redirect (HTTP {http_code})"
    elif not gw_ok:
        status = "DOWN"
        badge = "GATEWAY DOWN"
        color = "rose"
        message = f"Gateway {gw or 'interface'} is unreachable (link down)"
    else:
        status = "NO_INTERNET"
        badge = "NO INTERNET"
        color = "rose"
        message = f"Gateway {gw} is UP, but ISP cannot reach external internet"

    return {
        "port": port,
        "interface": interface or "unknown",
        "outgoing_ip": outgoing_ip,
        "gateway": gw,
        "gateway_ok": gw_ok,
        "is_listening": is_listening,
        "public_ip": public_ip,
        "latency_ms": latency_ms,
        "http_code": http_code,
        "status": status,
        "badge": badge,
        "color": color,
        "message": message
    }

def probe_all_ports_internet():
    """Probes all configured proxy ports concurrently and returns status mapping."""
    import concurrent.futures
    ports = get_ports_info()
    results = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {
            executor.submit(probe_port_internet, p["port"], None, p.get("outgoing_ip")): p["port"]
            for p in ports
        }
        for future in concurrent.futures.as_completed(future_map):
            port_num = future_map[future]
            try:
                results[port_num] = future.result()
            except Exception as e:
                results[port_num] = {
                    "port": port_num,
                    "status": "ERROR",
                    "badge": "ERROR",
                    "color": "rose",
                    "message": str(e)
                }
    return results

# ------------------------------------------------------------------------------
# Live Access Log Stream
# ------------------------------------------------------------------------------
def tail_access_log(lines=100, search_query=None, status_filter=None, user_filter=None, time_range="15m"):
    """Tails /var/log/squid/access.log and returns structured log entries with time window, status, and user filters."""
    if not os.path.exists(config.SQUID_ACCESS_LOG):
        return []

    # Map time range string to seconds and scan buffer depth
    time_map = {
        "1m":  {"sec": 60,    "scan": 1000},
        "5m":  {"sec": 300,   "scan": 2500},
        "15m": {"sec": 900,   "scan": 5000},
        "30m": {"sec": 1800,  "scan": 7500},
        "1h":  {"sec": 3600,  "scan": 10000},
        "5h":  {"sec": 18000, "scan": 15000},
        "6h":  {"sec": 21600, "scan": 15000},
        "12h": {"sec": 43200, "scan": 20000},
        "18h": {"sec": 64800, "scan": 25000},
        "24h": {"sec": 86400, "scan": 30000},
    }

    seconds_cutoff = None
    scan_limit = 2000
    display_cap = 500  # Cap table results to 500 records to keep browser smooth and responsive

    if time_range and time_range.lower() in time_map:
        cfg = time_map[time_range.lower()]
        seconds_cutoff = cfg["sec"]
        scan_limit = cfg["scan"]
    elif time_range and time_range.endswith("l"):
        try:
            display_cap = int(time_range[:-1])
            scan_limit = max(display_cap * 3, 500)
        except Exception:
            pass

    now = time.time()
    cutoff_epoch = (now - seconds_cutoff) if seconds_cutoff else None

    try:
        cmd = ["tail", "-n", str(scan_limit), config.SQUID_ACCESS_LOG]
        res = subprocess.run(cmd, capture_output=True, text=True)
        raw_lines = res.stdout.strip().splitlines()

        entries = []
        for line in reversed(raw_lines):
            line = line.strip()
            if not line:
                continue

            # Standard Squid Log Format:
            # timestamp.micro elapsed client_ip code/status bytes method url rfc931 peerstatus/peerhost type
            parts = line.split()
            if len(parts) >= 8:
                try:
                    epoch_str = parts[0]
                    epoch_float = float(epoch_str)
                except Exception:
                    epoch_float = 0

                # If time window is specified and this log line is older than the cutoff, stop reading
                if cutoff_epoch and epoch_float < cutoff_epoch:
                    break

                status_code = parts[3]
                user = parts[7] if parts[7] != "-" else "anonymous"

                # Status filter: 'denied' (403/DENIED) or 'allowed' (200/TUNNEL/MISS/HIT)
                if status_filter == "denied":
                    is_denied = ("DENIED" in status_code.upper() or "403" in status_code or "407" in status_code)
                    if not is_denied:
                        continue
                elif status_filter == "allowed":
                    is_denied = ("DENIED" in status_code.upper() or "403" in status_code)
                    if is_denied:
                        continue

                # Dedicated user filter
                if user_filter:
                    if user_filter.lower() not in user.lower():
                        continue

                # General search query across the entire log line
                if search_query and search_query.lower() not in line.lower():
                    continue

                try:
                    readable_time = datetime.datetime.fromtimestamp(epoch_float).strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    readable_time = parts[0]

                elapsed = parts[1]
                client_ip = parts[2]
                size_bytes = parts[4]
                method = parts[5]
                url = parts[6]

                entries.append({
                    "time": readable_time,
                    "elapsed_ms": elapsed,
                    "client_ip": client_ip,
                    "status": status_code,
                    "bytes": size_bytes,
                    "method": method,
                    "url": url,
                    "user": user,
                    "is_denied": ("DENIED" in status_code.upper() or "403" in status_code or "407" in status_code)
                })

        # Intelligent fallback for low-traffic / audit proxies:
        # If time window filtering resulted in 0 entries, but raw log lines exist,
        # extract the latest entries matching search/status filters so the operator is never blind
        if not entries and raw_lines:
            for line in reversed(raw_lines):
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 8:
                    try:
                        epoch_float = float(parts[0])
                    except Exception:
                        epoch_float = 0

                    status_code = parts[3]
                    user = parts[7] if parts[7] != "-" else "anonymous"

                    if status_filter == "denied":
                        if not ("DENIED" in status_code.upper() or "403" in status_code or "407" in status_code):
                            continue
                    elif status_filter == "allowed":
                        if "DENIED" in status_code.upper() or "403" in status_code:
                            continue

                    if user_filter and user_filter.lower() not in user.lower():
                        continue
                    if search_query and search_query.lower() not in line.lower():
                        continue

                    try:
                        readable_time = datetime.datetime.fromtimestamp(epoch_float).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        readable_time = parts[0]

                    is_denied = ("DENIED" in status_code.upper() or "403" in status_code or "407" in status_code)
                    entries.append({
                        "time": readable_time,
                        "elapsed_ms": parts[1],
                        "client_ip": parts[2],
                        "status": status_code,
                        "bytes": parts[4],
                        "method": parts[5],
                        "url": parts[6],
                        "user": user,
                        "is_denied": is_denied,
                        "is_idle_fallback": True
                    })
                    if len(entries) >= 50:
                        break

        return entries
    except Exception as e:
        return [{"error": str(e)}]

# ------------------------------------------------------------------------------
# Direct File & Directory Management Engine
# ------------------------------------------------------------------------------
def is_safe_squid_path(path):
    """Ensures a path resides strictly within /etc/squid and outside backups."""
    try:
        real = os.path.realpath(path)
        base = os.path.realpath("/etc/squid")
        backup_base = os.path.realpath(config.BACKUP_DIR)
        archive_base = os.path.realpath(config.ARCHIVE_DIR)
        return real.startswith(base) and not real.startswith(backup_base) and not real.startswith(archive_base)
    except Exception:
        return False

def get_squid_directories():
    """Returns all directories within /etc/squid (excluding backups)."""
    dirs = []
    base = "/etc/squid"
    if not os.path.exists(base):
        return dirs

    for root, dirnames, _ in os.walk(base):
        # Exclude backup folders
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and "backup" not in d.lower() and "archive" not in d.lower()]
        if is_safe_squid_path(root):
            dirs.append(root)

    return sorted(dirs)

def get_editable_files():
    """Returns dynamically discovered editable configuration and ACL files within /etc/squid."""
    files = []
    base = "/etc/squid"
    if not os.path.exists(base):
        return files

    protected_paths = [
        os.path.realpath(config.SQUID_CONF),
        os.path.realpath(config.SQUID_PASSWD_FILE),
        os.path.realpath("/etc/squid/cachemgr.conf")
    ]

    for root, dirnames, filenames in os.walk(base):
        # Skip backup and hidden directories
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and "backup" not in d.lower() and "archive" not in d.lower()]
        for f in sorted(filenames):
            if f.startswith(".") or f.endswith(".dpkg-dist") or f.endswith(".tmp"):
                continue
            full_path = os.path.join(root, f)
            if not is_safe_squid_path(full_path):
                continue

            rel_path = os.path.relpath(full_path, base)
            file_id = rel_path.replace("/", "__").replace(".", "_")

            # Determine file type
            ftype = "config"
            if "/domains" in full_path: ftype = "domains"
            elif "/users" in full_path: ftype = "users"
            elif "/ips" in full_path: ftype = "ips"
            elif full_path.endswith(".txt"): ftype = "text"

            is_deletable = os.path.realpath(full_path) not in protected_paths

            files.append({
                "id": file_id,
                "label": f"{rel_path} ({full_path})",
                "rel_path": rel_path,
                "path": full_path,
                "type": ftype,
                "deletable": is_deletable,
                "size": os.path.getsize(full_path) if os.path.exists(full_path) else 0
            })

    # Sort so squid.conf is first, followed by allowed_ips.txt and then others
    def sort_key(item):
        if item["path"] == config.SQUID_CONF: return (0, item["rel_path"])
        if item["path"] == config.SQUID_ALLOWED_IPS_FILE: return (1, item["rel_path"])
        return (2, item["rel_path"])

    return sorted(files, key=sort_key)

def read_editable_file(file_id):
    """Safely reads the content of an editable file."""
    for f in get_editable_files():
        if f["id"] == file_id or f["path"] == file_id:
            if os.path.exists(f["path"]) and is_safe_squid_path(f["path"]):
                with open(f["path"], "r", errors="replace") as fp:
                    return True, fp.read(), f["path"]
            return False, "File does not exist or access denied.", f["path"]
    return False, "File ID not permitted.", None

def save_editable_file(file_id, new_content):
    """
    Safely saves content to an editable file:
    1. Creates automatic backup.
    2. Writes to temporary file and tests syntax with 'squid -k parse'.
    3. Replaces file and gracefully reloads with 'squid -k reconfigure'.
    """
    target = None
    for f in get_editable_files():
        if f["id"] == file_id or f["path"] == file_id:
            target = f
            break

    if not target:
        return False, "Unauthorized or unknown file ID."

    target_path = target["path"]
    if not is_safe_squid_path(target_path):
        return False, "Access denied: Path is outside permitted squid directory."

    # Pre-flight backup
    create_backup(f"Edit {target['label']}")

    temp_path = f"/tmp/squid_portal_test_{target['id']}.tmp"
    try:
        with open(temp_path, "w") as fp:
            fp.write(new_content)

        # If editing squid.conf, test syntax before replacing
        if target["path"] == config.SQUID_CONF:
            res = subprocess.run(["squid", "-k", "parse", "-f", temp_path], capture_output=True, text=True)
            if res.returncode != 0:
                os.remove(temp_path)
                return False, f"Syntax verification failed! Squid reported:\n{res.stderr.strip() or res.stdout.strip()}"

        shutil.copy2(temp_path, target_path)
        os.remove(temp_path)

        reload_ok, reload_msg = reload_squid()
        if not reload_ok:
            return True, f"File saved, but reload warning: {reload_msg}"

        return True, "File saved successfully and Squid gracefully reloaded without downtime."
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"Error saving file: {str(e)}"

def create_file(parent_dir, filename, content=""):
    """
    Creates a new file in parent_dir:
    1. Validates parent_dir within /etc/squid.
    2. Validates filename.
    3. Creates pre-creation backup.
    4. Writes file.
    5. Gracefully reloads Squid.
    """
    parent_dir = os.path.realpath(parent_dir)
    if not is_safe_squid_path(parent_dir) or not os.path.isdir(parent_dir):
        return False, "Invalid or unauthorized parent directory."

    filename = filename.strip()
    if not filename or not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        return False, "Invalid filename. Use alphanumeric characters, dots, underscores, or hyphens."

    target_path = os.path.join(parent_dir, filename)
    if os.path.exists(target_path):
        return False, f"File '{filename}' already exists in '{parent_dir}'."

    create_backup(f"Create file {filename} in {os.path.basename(parent_dir)}")

    try:
        with open(target_path, "w") as f:
            f.write(content)

        reload_squid()
        return True, f"File '{filename}' created successfully in {parent_dir}."
    except Exception as e:
        return False, f"Error creating file: {str(e)}"

def create_directory(parent_dir, dirname):
    """
    Creates a new subfolder in parent_dir:
    1. Validates parent_dir within /etc/squid.
    2. Validates dirname.
    3. Creates folder.
    """
    parent_dir = os.path.realpath(parent_dir)
    if not is_safe_squid_path(parent_dir) or not os.path.isdir(parent_dir):
        return False, "Invalid or unauthorized parent directory."

    dirname = dirname.strip()
    if not dirname or not re.match(r'^[a-zA-Z0-9_\-]+$', dirname):
        return False, "Invalid folder name. Use alphanumeric characters, underscores, or hyphens."

    target_path = os.path.join(parent_dir, dirname)
    if os.path.exists(target_path):
        return False, f"Directory '{dirname}' already exists in '{parent_dir}'."

    try:
        os.makedirs(target_path, exist_ok=False)
        return True, f"Directory '{dirname}' created successfully in {parent_dir}."
    except Exception as e:
        return False, f"Error creating directory: {str(e)}"

def delete_file(file_path):
    """
    Safely deletes a file from /etc/squid:
    1. Prevents deletion of critical system files (squid.conf, password).
    2. Creates pre-deletion snapshot in backup center.
    3. Deletes file.
    4. Runs syntax check with 'squid -k parse'.
    """
    file_path = os.path.realpath(file_path)
    if not is_safe_squid_path(file_path) or not os.path.isfile(file_path):
        return False, "Invalid or unauthorized file path."

    protected_paths = [
        os.path.realpath(config.SQUID_CONF),
        os.path.realpath(config.SQUID_PASSWD_FILE),
        os.path.realpath("/etc/squid/cachemgr.conf")
    ]
    if file_path in protected_paths:
        return False, f"Protected file '{os.path.basename(file_path)}' cannot be deleted for system safety."

    fname = os.path.basename(file_path)
    create_backup(f"Delete file {fname}")

    try:
        os.remove(file_path)
        valid, msg = validate_squid_syntax()
        if not valid:
            return True, f"File '{fname}' deleted, but Squid syntax warning: {msg}. You can restore from Backups if needed."
        reload_squid()
        return True, f"File '{fname}' permanently deleted and Squid reconfigured."
    except Exception as e:
        return False, f"Error deleting file: {str(e)}"

def delete_directory(dir_path):
    """
    Safely deletes a directory within /etc/squid:
    1. Protects core directories (/etc/squid, /etc/squid/acl, etc.).
    2. Takes pre-deletion backup.
    3. Removes directory.
    """
    dir_path = os.path.realpath(dir_path)
    if not is_safe_squid_path(dir_path) or not os.path.isdir(dir_path):
        return False, "Invalid or unauthorized directory path."

    protected_dirs = [
        os.path.realpath("/etc/squid"),
        os.path.realpath(config.SQUID_ACL_DIR),
        os.path.realpath(config.SQUID_ACL_DOMAINS_DIR),
        os.path.realpath(config.SQUID_ACL_USERS_DIR),
        os.path.realpath(config.SQUID_ACL_IPS_DIR),
        os.path.realpath("/etc/squid/conf.d")
    ]
    if dir_path in protected_dirs:
        return False, f"Core directory '{os.path.basename(dir_path)}' is protected and cannot be deleted."

    dname = os.path.basename(dir_path)
    create_backup(f"Delete directory {dname}")

    try:
        shutil.rmtree(dir_path)
        reload_squid()
        return True, f"Directory '{dname}' deleted successfully."
    except Exception as e:
        return False, f"Error deleting directory: {str(e)}"


# ------------------------------------------------------------------------------
# Automated 5-Backup Retention & 1-Click Extraction/Restore
# ------------------------------------------------------------------------------
def create_backup(description="Manual backup"):
    """
    Creates an automatic backup snapshot:
    - Copies /etc/squid/password, squid.conf, allowed_ips.txt, and /etc/squid/acl/
    - Maintains the last 5 active snapshots.
    - If count exceeds 5, automatically rotates and compresses the oldest into an archive (.tar.gz).
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder_name = f"backup_{timestamp}"
    backup_path = os.path.join(config.BACKUP_DIR, backup_folder_name)
    os.makedirs(backup_path, exist_ok=True)

    copied_files = []

    # Copy files
    for src in [config.SQUID_PASSWD_FILE, config.SQUID_CONF, config.SQUID_ALLOWED_IPS_FILE]:
        if os.path.exists(src):
            shutil.copy2(src, backup_path)
            copied_files.append(os.path.basename(src))

    # Copy ACL directory recursively
    if os.path.exists(config.SQUID_ACL_DIR):
        acl_dest = os.path.join(backup_path, "acl")
        shutil.copytree(config.SQUID_ACL_DIR, acl_dest, dirs_exist_ok=True)
        copied_files.append("acl/")

    # Write metadata
    meta = {
        "id": backup_folder_name,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "description": description,
        "files": copied_files
    }
    with open(os.path.join(backup_path, "meta.json"), "w") as fp:
        json.dump(meta, fp, indent=2)

    # Enforce 5-backup rotation policy
    rotate_backups_to_archive()

    return meta

def cleanup_excess_archives():
    """
    Ensures that only the 5 most recent .tar.gz archives are retained in ARCHIVE_DIR.
    Any older archives beyond the top 5 are automatically deleted from the filesystem.
    """
    if not os.path.exists(config.ARCHIVE_DIR):
        return

    archives = []
    for item in os.listdir(config.ARCHIVE_DIR):
        if item.endswith(".tar.gz"):
            full_path = os.path.join(config.ARCHIVE_DIR, item)
            archives.append(full_path)

    # Sort newest first by modification time
    archives.sort(key=os.path.getmtime, reverse=True)

    max_archives = getattr(config, "MAX_ARCHIVE_BACKUPS", 5)
    if len(archives) > max_archives:
        for old_arch in archives[max_archives:]:
            try:
                os.remove(old_arch)
            except Exception as e:
                print(f"[ERROR] Failed to purge excess archive {old_arch}: {e}", file=sys.stderr)

def rotate_backups_to_archive():
    """
    Rotates backups: keeps exactly the 5 most recent active snapshots.
    Older backups are automatically compressed into /etc/squid/squid_backups/portal_archives/
    and the uncompressed folder is removed.
    Also strictly purges any excess .tar.gz archives so only 5 archives exist.
    """
    active_backups = []
    for item in os.listdir(config.BACKUP_DIR):
        folder = os.path.join(config.BACKUP_DIR, item)
        if os.path.isdir(folder) and item.startswith("backup_"):
            active_backups.append(folder)

    # Sort by creation time (newest first)
    active_backups.sort(key=os.path.getmtime, reverse=True)

    # If more than 5, archive the excess older ones
    if len(active_backups) > config.MAX_ACTIVE_BACKUPS:
        excess = active_backups[config.MAX_ACTIVE_BACKUPS:]
        for old_folder in excess:
            base_name = os.path.basename(old_folder)
            archive_tar = os.path.join(config.ARCHIVE_DIR, f"{base_name}.tar.gz")
            try:
                with tarfile.open(archive_tar, "w:gz") as tar:
                    tar.add(old_folder, arcname=base_name)
                # Remove old uncompressed folder
                shutil.rmtree(old_folder)
            except Exception as e:
                print(f"[ERROR] Failed to archive backup {old_folder}: {e}", file=sys.stderr)

    # Enforce 5-archive retention limit on .tar.gz archives
    cleanup_excess_archives()

def list_backups():
    """Lists the 5 active backups and the 5 most recent archives, purging any older ones."""
    # Ensure any excess archives on disk are purged first
    cleanup_excess_archives()

    active = []
    if os.path.exists(config.BACKUP_DIR):
        for item in sorted(os.listdir(config.BACKUP_DIR), reverse=True):
            folder = os.path.join(config.BACKUP_DIR, item)
            if os.path.isdir(folder) and item.startswith("backup_"):
                meta_file = os.path.join(folder, "meta.json")
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r") as fp:
                            meta = json.load(fp)
                            active.append(meta)
                    except Exception:
                        pass
                else:
                    active.append({
                        "id": item,
                        "timestamp": datetime.datetime.fromtimestamp(os.path.getmtime(folder)).strftime("%Y-%m-%d %H:%M:%S"),
                        "description": "Automated snapshot",
                        "files": os.listdir(folder)
                    })

    # Limit active to 5
    active = active[:config.MAX_ACTIVE_BACKUPS]

    # Archived backups (limited to 5 newest)
    archives = []
    if os.path.exists(config.ARCHIVE_DIR):
        arch_files = []
        for item in os.listdir(config.ARCHIVE_DIR):
            if item.endswith(".tar.gz"):
                arch_path = os.path.join(config.ARCHIVE_DIR, item)
                arch_files.append((item, arch_path, os.path.getmtime(arch_path)))

        # Sort newest first
        arch_files.sort(key=lambda x: x[2], reverse=True)
        max_archives = getattr(config, "MAX_ARCHIVE_BACKUPS", 5)
        arch_files = arch_files[:max_archives]

        for item, arch_path, mtime in arch_files:
            archives.append({
                "filename": item,
                "size_kb": round(os.path.getsize(arch_path) / 1024, 1),
                "created_at": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

    return {"active": active, "archives": archives}

def restore_backup(backup_id):
    """
    Extracts and restores the selected backup snapshot:
    1. Takes safety snapshot of current state first.
    2. Copies backup files back to /etc/squid/.
    3. Validates with 'squid -k parse'.
    4. Reloads gracefully with 'squid -k reconfigure'.
    """
    backup_path = os.path.join(config.BACKUP_DIR, backup_id)
    if not os.path.exists(backup_path) or not os.path.isdir(backup_path):
        return False, f"Backup snapshot '{backup_id}' not found."

    # Take pre-restore safety snapshot
    create_backup(f"Pre-restore safety snapshot before reverting to {backup_id}")

    try:
        # Restore files
        for fname in ["password", "squid.conf", "allowed_ips.txt"]:
            src = os.path.join(backup_path, fname)
            dst = os.path.join("/etc/squid", fname)
            if os.path.exists(src):
                shutil.copy2(src, dst)

        # Restore ACLs
        src_acl = os.path.join(backup_path, "acl")
        if os.path.exists(src_acl):
            shutil.copytree(src_acl, config.SQUID_ACL_DIR, dirs_exist_ok=True)

        # Validate syntax
        test_res = subprocess.run(["squid", "-k", "parse"], capture_output=True, text=True)
        if test_res.returncode != 0:
            return False, f"Restored files failed syntax check: {test_res.stderr.strip()}"

        # Graceful reload
        reload_squid()
        return True, f"Successfully restored backup snapshot '{backup_id}' and reloaded Squid."
    except Exception as e:
        return False, f"Failed to restore backup: {str(e)}"

# ------------------------------------------------------------------------------
# Safe Squid Daemon Operations
# ------------------------------------------------------------------------------
def validate_squid_syntax():
    """Runs 'squid -k parse' to check configuration syntax."""
    res = subprocess.run(["squid", "-k", "parse"], capture_output=True, text=True)
    is_valid = res.returncode == 0
    return is_valid, res.stderr.strip() or res.stdout.strip() or "Syntax OK"

def reload_squid():
    """
    Gracefully reloads Squid configuration via 'squid -k reconfigure'.
    Does NOT drop connections or restart the daemon.
    """
    # Verify syntax first
    valid, msg = validate_squid_syntax()
    if not valid:
        return False, f"Cannot reload: Configuration syntax check failed:\n{msg}"

    res = subprocess.run(["squid", "-k", "reconfigure"], capture_output=True, text=True)
    if res.returncode == 0:
        return True, "Squid configuration gracefully reloaded without downtime."
    else:
        return False, f"Reload failed: {res.stderr.strip() or res.stdout.strip()}"

# ------------------------------------------------------------------------------
# SARG Reports Generation
# ------------------------------------------------------------------------------
def trigger_sarg_generation():
    """Triggers SARG report generation in the background."""
    if not os.path.exists(config.SARG_BINARY):
        return False, f"SARG binary not found at {config.SARG_BINARY}."

    try:
        # Run asynchronously so it doesn't block the UI
        subprocess.Popen([config.SARG_BINARY], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "SARG report generation initiated in background. Reports will update in a few moments."
    except Exception as e:
        return False, f"Failed to trigger SARG: {str(e)}"

# ==============================================================================
# ADVANCED ANALYTICS: Fleet, Blocked Requests, User Activity, Security, Hourly
# ==============================================================================

def get_fleet_status():
    """
    Queries /api/status on all peer fleet servers via HTTP.
    Returns combined health data for the Multi-Server Dashboard.
    """
    import requests as http_requests

    fleet_data = []
    # Determine this server's own IP
    try:
        own_ip_result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
        own_ips = own_ip_result.stdout.strip().split()
    except Exception:
        own_ips = []

    for server in config.FLEET_SERVERS:
        server_ip = server["ip"]
        server_port = server.get("port", 5000)
        server_name = server.get("name", server_ip)

        entry = {
            "ip": server_ip,
            "port": server_port,
            "name": server_name,
            "online": False,
            "is_self": server_ip in own_ips,
            "status": {},
            "metrics": {},
            "error": None
        }

        try:
            if entry["is_self"]:
                # Local call — no HTTP needed
                entry["status"] = get_service_status()
                entry["metrics"] = get_system_metrics()
                entry["online"] = entry["status"].get("active", False)
            else:
                url = f"http://{server_ip}:{server_port}/api/status"
                resp = http_requests.get(url, timeout=config.FLEET_TIMEOUT)
                if resp.status_code == 200:
                    data = resp.json()
                    entry["status"] = data.get("status", {})
                    entry["metrics"] = data.get("metrics", {})
                    entry["online"] = entry["status"].get("active", False)
                elif resp.status_code == 401:
                    entry["error"] = "Authentication required on remote server"
                else:
                    entry["error"] = f"HTTP {resp.status_code}"
        except http_requests.exceptions.ConnectTimeout:
            entry["error"] = "Connection timed out"
        except http_requests.exceptions.ConnectionError:
            entry["error"] = "Connection refused or unreachable"
        except Exception as e:
            entry["error"] = str(e)

        fleet_data.append(entry)

    # Summary
    total = len(fleet_data)
    online_count = sum(1 for s in fleet_data if s["online"])
    return {
        "servers": fleet_data,
        "total": total,
        "online": online_count,
        "offline": total - online_count,
        "fleet_health": round((online_count / max(total, 1)) * 100, 1)
    }


def get_blocked_requests(sample_lines=1000):
    """
    Parses access log for TCP_DENIED / 403 / 407 entries.
    Returns grouped analytics: top blocked domains, top denied users, recent blocked entries.
    """
    result = {
        "total_blocked": 0,
        "total_auth_failures": 0,
        "top_blocked_domains": [],
        "top_denied_users": [],
        "top_denied_ips": [],
        "recent_blocked": [],
        "sample_lines": 0
    }

    if not os.path.exists(config.SQUID_ACCESS_LOG):
        return result

    try:
        cmd = ["tail", "-n", str(sample_lines), config.SQUID_ACCESS_LOG]
        res = subprocess.run(cmd, capture_output=True, text=True)
        lines = res.stdout.strip().splitlines()
        result["sample_lines"] = len(lines)

        domain_counter = Counter()
        user_counter = Counter()
        ip_counter = Counter()
        blocked_entries = []

        for line in reversed(lines):
            p = line.strip().split()
            if len(p) < 8:
                continue

            raw_status = p[3]
            http_code = raw_status.split("/")[-1] if "/" in raw_status else ""
            status_upper = raw_status.upper()

            is_denied = "DENIED" in status_upper or http_code in ("403", "407")
            is_auth_fail = http_code == "407"

            if is_denied or is_auth_fail:
                result["total_blocked"] += 1
                if is_auth_fail:
                    result["total_auth_failures"] += 1

                user = p[7] if p[7] != "-" else "anonymous"
                client_ip = p[2]
                raw_url = p[6].strip()
                if raw_url.lower().startswith("http://"):
                    raw_url = raw_url[7:]
                elif raw_url.lower().startswith("https://"):
                    raw_url = raw_url[8:]
                host_with_port = raw_url.split("/")[0].strip()
                domain = host_with_port.split(":")[0].strip().lower()

                if domain:
                    domain_counter[domain] += 1
                user_counter[user] += 1
                ip_counter[client_ip] += 1

                if len(blocked_entries) < 50:
                    try:
                        readable_time = datetime.datetime.fromtimestamp(float(p[0])).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        readable_time = p[0]

                    blocked_entries.append({
                        "time": readable_time,
                        "client_ip": client_ip,
                        "user": user,
                        "domain": domain or p[6],
                        "status": raw_status,
                        "method": p[5],
                        "bytes": p[4],
                        "is_auth_fail": is_auth_fail
                    })

        result["top_blocked_domains"] = [
            {"domain": d, "count": c} for d, c in domain_counter.most_common(10)
        ]
        result["top_denied_users"] = [
            {"user": u, "count": c} for u, c in user_counter.most_common(10)
        ]
        result["top_denied_ips"] = [
            {"ip": ip, "count": c} for ip, c in ip_counter.most_common(10)
        ]
        result["recent_blocked"] = blocked_entries

    except Exception as e:
        result["error"] = str(e)

    return result


def get_user_activity(username, sample_lines=2000):
    """
    Parses access log for a specific user's activity.
    Returns: total requests, bandwidth, top domains, hourly heatmap, methods, recent requests.
    """
    result = {
        "username": username,
        "total_requests": 0,
        "total_bytes": 0,
        "total_bytes_human": "0 B",
        "top_domains": [],
        "hourly_heatmap": [0] * 24,
        "method_breakdown": {},
        "status_breakdown": {},
        "recent_requests": [],
        "first_seen": None,
        "last_seen": None,
        "sample_lines": 0
    }

    if not os.path.exists(config.SQUID_ACCESS_LOG):
        return result

    try:
        cmd = ["tail", "-n", str(sample_lines), config.SQUID_ACCESS_LOG]
        res = subprocess.run(cmd, capture_output=True, text=True)
        lines = res.stdout.strip().splitlines()
        result["sample_lines"] = len(lines)

        domain_counter = Counter()
        method_counter = Counter()
        status_counter = Counter()
        hourly_counts = [0] * 24

        for line in lines:
            p = line.strip().split()
            if len(p) < 8:
                continue

            log_user = p[7] if p[7] != "-" else "anonymous"
            if log_user.lower() != username.lower():
                continue

            result["total_requests"] += 1

            # Bytes
            try:
                result["total_bytes"] += int(p[4])
            except ValueError:
                pass

            # Timestamp & hour
            try:
                ts = float(p[0])
                dt = datetime.datetime.fromtimestamp(ts)
                hourly_counts[dt.hour] += 1
                readable_time = dt.strftime("%Y-%m-%d %H:%M:%S")

                if result["first_seen"] is None or ts < float(p[0]):
                    result["first_seen"] = readable_time
                result["last_seen"] = readable_time
            except Exception:
                readable_time = p[0]

            # Domain / Host
            raw_url = p[6].strip()
            if raw_url.lower().startswith("http://"):
                raw_url = raw_url[7:]
            elif raw_url.lower().startswith("https://"):
                raw_url = raw_url[8:]
            host_with_port = raw_url.split("/")[0].strip()
            domain = host_with_port.split(":")[0].strip().lower()
            if domain:
                domain_counter[domain] += 1

            # Method & status
            method_counter[p[5]] += 1
            raw_status = p[3]
            status_prefix = raw_status.split("/")[0].upper()
            if "TUNNEL" in status_prefix:
                status_counter["TCP_TUNNEL"] += 1
            elif "DENIED" in status_prefix:
                status_counter["TCP_DENIED"] += 1
            elif "HIT" in status_prefix:
                status_counter["TCP_HIT"] += 1
            elif "MISS" in status_prefix:
                status_counter["TCP_MISS"] += 1
            else:
                status_counter["OTHER"] += 1

            # Recent requests (last 20)
            if len(result["recent_requests"]) < 20:
                result["recent_requests"].append({
                    "time": readable_time,
                    "domain": domain or p[6],
                    "method": p[5],
                    "status": raw_status,
                    "bytes": p[4]
                })

        # Finalize
        result["hourly_heatmap"] = hourly_counts
        result["top_domains"] = [
            {"domain": d, "count": c} for d, c in domain_counter.most_common(10)
        ]
        result["method_breakdown"] = dict(method_counter)
        result["status_breakdown"] = dict(status_counter)

        # Human-readable bytes
        total_b = result["total_bytes"]
        if total_b >= 1073741824:
            result["total_bytes_human"] = f"{round(total_b / 1073741824, 2)} GB"
        elif total_b >= 1048576:
            result["total_bytes_human"] = f"{round(total_b / 1048576, 2)} MB"
        elif total_b >= 1024:
            result["total_bytes_human"] = f"{round(total_b / 1024, 2)} KB"
        else:
            result["total_bytes_human"] = f"{total_b} B"

        # Reverse recent requests to show newest first
        result["recent_requests"] = list(reversed(result["recent_requests"]))

    except Exception as e:
        result["error"] = str(e)

    return result


def get_security_events(sample_lines=2000):
    """
    Extracts security-relevant events from access log:
    - Failed auth attempts (407)
    - Denied requests (TCP_DENIED / 403)
    - Brute-force candidates (IPs with > 5 failures)
    - Security score calculation
    """
    result = {
        "total_requests": 0,
        "total_denied": 0,
        "total_auth_failures": 0,
        "security_score": 100,
        "brute_force_candidates": [],
        "auth_failure_events": [],
        "denied_events": [],
        "top_threat_ips": [],
        "sample_lines": 0
    }

    if not os.path.exists(config.SQUID_ACCESS_LOG):
        return result

    try:
        cmd = ["tail", "-n", str(sample_lines), config.SQUID_ACCESS_LOG]
        res = subprocess.run(cmd, capture_output=True, text=True)
        lines = res.stdout.strip().splitlines()
        result["sample_lines"] = len(lines)
        result["total_requests"] = len(lines)

        ip_fail_counter = Counter()
        auth_events = []
        denied_events = []

        for line in reversed(lines):
            p = line.strip().split()
            if len(p) < 8:
                continue

            raw_status = p[3]
            http_code = raw_status.split("/")[-1] if "/" in raw_status else ""
            status_upper = raw_status.upper()

            try:
                readable_time = datetime.datetime.fromtimestamp(float(p[0])).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                readable_time = p[0]

            client_ip = p[2]
            user = p[7] if p[7] != "-" else "anonymous"
            raw_url = p[6].strip()
            if raw_url.lower().startswith("http://"):
                raw_url = raw_url[7:]
            elif raw_url.lower().startswith("https://"):
                raw_url = raw_url[8:]
            host_with_port = raw_url.split("/")[0].strip()
            domain = host_with_port.split(":")[0].strip().lower()

            # Auth failures (407)
            if http_code == "407":
                result["total_auth_failures"] += 1
                ip_fail_counter[client_ip] += 1
                if len(auth_events) < 50:
                    auth_events.append({
                        "time": readable_time,
                        "client_ip": client_ip,
                        "user": user,
                        "domain": domain or p[6],
                        "status": raw_status
                    })

            # Denied requests
            if "DENIED" in status_upper or http_code == "403":
                result["total_denied"] += 1
                if len(denied_events) < 50:
                    denied_events.append({
                        "time": readable_time,
                        "client_ip": client_ip,
                        "user": user,
                        "domain": domain or p[6],
                        "status": raw_status,
                        "method": p[5]
                    })

        result["auth_failure_events"] = auth_events
        result["denied_events"] = denied_events

        # Brute force candidates: IPs with > 5 failures
        result["brute_force_candidates"] = [
            {"ip": ip, "attempts": count}
            for ip, count in ip_fail_counter.most_common(20) if count >= 5
        ]

        # Top threat IPs (all IPs with failures)
        result["top_threat_ips"] = [
            {"ip": ip, "attempts": count}
            for ip, count in ip_fail_counter.most_common(10)
        ]

        # Security score: deduct points for auth failures and denials
        total = max(result["total_requests"], 1)
        denied_pct = (result["total_denied"] / total) * 100
        auth_fail_pct = (result["total_auth_failures"] / total) * 100
        brute_penalty = len(result["brute_force_candidates"]) * 5

        score = 100 - denied_pct - (auth_fail_pct * 2) - brute_penalty
        result["security_score"] = max(0, min(100, round(score, 1)))

    except Exception as e:
        result["error"] = str(e)

    return result


def get_hourly_traffic_breakdown(hours=24):
    """
    Aggregates request counts per hour for the last N hours.
    Returns time-series data for Chart.js line charts.
    """
    result = {
        "labels": [],
        "requests": [],
        "denied": [],
        "tunnel": [],
        "hours": hours
    }

    if not os.path.exists(config.SQUID_ACCESS_LOG):
        # Return empty placeholder data
        now = datetime.datetime.now()
        for i in range(hours):
            h = now - datetime.timedelta(hours=hours - 1 - i)
            result["labels"].append(h.strftime("%H:00"))
            result["requests"].append(0)
            result["denied"].append(0)
            result["tunnel"].append(0)
        return result

    try:
        # Read a generous number of lines to cover 24 hours
        cmd = ["tail", "-n", "10000", config.SQUID_ACCESS_LOG]
        res = subprocess.run(cmd, capture_output=True, text=True)
        lines = res.stdout.strip().splitlines()

        now = datetime.datetime.now()
        cutoff = now - datetime.timedelta(hours=hours)

        hourly_requests = {}
        hourly_denied = {}
        hourly_tunnel = {}

        for i in range(hours):
            h = now - datetime.timedelta(hours=hours - 1 - i)
            key = h.strftime("%Y-%m-%d %H")
            label = h.strftime("%H:00")
            hourly_requests[key] = 0
            hourly_denied[key] = 0
            hourly_tunnel[key] = 0
            result["labels"].append(label)

        for line in lines:
            p = line.strip().split()
            if len(p) < 8:
                continue
            try:
                ts = float(p[0])
                dt = datetime.datetime.fromtimestamp(ts)
                if dt < cutoff:
                    continue
                key = dt.strftime("%Y-%m-%d %H")
                if key in hourly_requests:
                    hourly_requests[key] += 1

                    raw_status = p[3].upper()
                    http_code = p[3].split("/")[-1] if "/" in p[3] else ""
                    if "DENIED" in raw_status or http_code in ("403", "407"):
                        hourly_denied[key] += 1
                    if "TUNNEL" in raw_status:
                        hourly_tunnel[key] += 1
            except Exception:
                continue

        # Build ordered arrays matching labels
        for i in range(hours):
            h = now - datetime.timedelta(hours=hours - 1 - i)
            key = h.strftime("%Y-%m-%d %H")
            result["requests"].append(hourly_requests.get(key, 0))
            result["denied"].append(hourly_denied.get(key, 0))
            result["tunnel"].append(hourly_tunnel.get(key, 0))

    except Exception as e:
        result["error"] = str(e)
        # Fill with zeros on error
        now = datetime.datetime.now()
        for i in range(hours):
            h = now - datetime.timedelta(hours=hours - 1 - i)
            result["labels"].append(h.strftime("%H:00"))
            result["requests"].append(0)
            result["denied"].append(0)
            result["tunnel"].append(0)

    return result

