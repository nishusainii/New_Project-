"""
Innspark / CiSai Squid Proxy Management Portal - nftables Firewall Manager
Provides robust viewing, structured rule management, raw editing, validation (nft -c -f),
atomic reloading (nft -f /etc/nftables.conf), and automated backups.
"""

import os
import re
import time
import json
import shutil
import subprocess
import config

NFTABLES_CONF = getattr(config, "NFTABLES_CONF", "/etc/nftables.conf")
NFT_BACKUP_DIR = os.path.join(getattr(config, "BACKUP_DIR", "/etc/squid/squid_backups/portal_backups"), "nftables")

def ensure_nft_backup_dir():
    try:
        os.makedirs(NFT_BACKUP_DIR, exist_ok=True)
    except Exception:
        pass

def backup_nftables_conf(reason="Manual update"):
    """Creates a timestamped snapshot of /etc/nftables.conf."""
    ensure_nft_backup_dir()
    if not os.path.exists(NFTABLES_CONF):
        return None
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_reason = re.sub(r"[^a-zA-Z0-9_\-]", "_", reason)[:30]
    backup_file = os.path.join(NFT_BACKUP_DIR, f"nftables_{timestamp}_{safe_reason}.conf")
    try:
        shutil.copy2(NFTABLES_CONF, backup_file)
        return backup_file
    except Exception:
        return None

def get_nftables_status():
    """Returns the operational status of nftables on the system."""
    status = {
        "active": False,
        "service_status": "inactive",
        "has_binary": False,
        "rules_count": 0,
        "tables_count": 0,
        "chains_count": 0,
        "conf_exists": os.path.exists(NFTABLES_CONF),
        "conf_mtime": None
    }

    # Check binary
    which_nft = shutil.which("nft")
    if which_nft:
        status["has_binary"] = True

    # Check systemd service status
    try:
        res = subprocess.run(["systemctl", "is-active", "nftables"], capture_output=True, text=True, timeout=5)
        status["service_status"] = res.stdout.strip()
        status["active"] = (res.stdout.strip() == "active")
    except Exception:
        status["service_status"] = "unknown"

    # Check conf file modified time
    if os.path.exists(NFTABLES_CONF):
        try:
            mtime = os.path.getmtime(NFTABLES_CONF)
            status["conf_mtime"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))
        except Exception:
            pass

    # Quick count of tables/chains/rules
    try:
        res_list = subprocess.run(["nft", "list", "ruleset"], capture_output=True, text=True, timeout=5)
        if res_list.returncode == 0:
            out = res_list.stdout
            status["tables_count"] = len(re.findall(r'^\s*table\s+', out, re.MULTILINE))
            status["chains_count"] = len(re.findall(r'^\s*chain\s+', out, re.MULTILINE))
            status["rules_count"] = len([l for l in out.splitlines() if l.strip() and not l.strip().startswith(('table', 'chain', '{', '}', '#', 'type', 'flush'))])
            if status["tables_count"] > 0:
                status["active"] = True
    except Exception:
        pass

    return status

def get_nftables_ruleset():
    """
    Parses and returns structured nftables tables, chains, rules with handles,
    along with the raw /etc/nftables.conf content.
    """
    raw_config = ""
    if os.path.exists(NFTABLES_CONF):
        try:
            with open(NFTABLES_CONF, "r", encoding="utf-8", errors="ignore") as f:
                raw_config = f.read()
        except Exception as e:
            raw_config = f"# Error reading {NFTABLES_CONF}: {str(e)}"

    # Try listing active ruleset with handles
    active_ruleset_text = ""
    tables = []
    chains = []
    rules = []

    try:
        res = subprocess.run(["nft", "-a", "list", "ruleset"], capture_output=True, text=True, timeout=8)
        if res.returncode == 0:
            active_ruleset_text = res.stdout
        else:
            active_ruleset_text = raw_config
    except Exception:
        active_ruleset_text = raw_config

    # Parse text into structured hierarchy
    current_table = None
    current_chain = None

    for line in active_ruleset_text.splitlines():
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("#") or trimmed == "flush ruleset":
            continue

        # Table match: table <family> <name> {
        t_match = re.match(r"^table\s+([a-zA-Z0-9_\-]+)\s+([a-zA-Z0-9_\-]+)\s*\{?", trimmed)
        if t_match:
            current_table = {
                "family": t_match.group(1),
                "name": t_match.group(2)
            }
            tables.append(current_table)
            current_chain = None
            continue

        # Chain match: chain <name> {
        c_match = re.match(r"^chain\s+([a-zA-Z0-9_\-]+)\s*\{?", trimmed)
        if c_match and current_table:
            current_chain = {
                "table_family": current_table["family"],
                "table_name": current_table["name"],
                "name": c_match.group(1),
                "type": "filter",
                "hook": "none",
                "priority": "0",
                "policy": "accept"
            }
            chains.append(current_chain)
            continue

        if trimmed == "}":
            if current_chain is not None:
                current_chain = None
            elif current_table is not None:
                current_table = None
            continue

        # Chain properties: type filter hook forward priority 0; policy accept;
        if current_chain and trimmed.startswith("type "):
            type_m = re.search(r'type\s+([a-zA-Z0-9_\-]+)', trimmed)
            hook_m = re.search(r'hook\s+([a-zA-Z0-9_\-]+)', trimmed)
            prio_m = re.search(r'priority\s+([a-zA-Z0-9_\-\+]+)', trimmed)
            pol_m = re.search(r'policy\s+([a-zA-Z0-9_\-]+)', trimmed)

            if type_m: current_chain["type"] = type_m.group(1)
            if hook_m: current_chain["hook"] = hook_m.group(1)
            if prio_m: current_chain["priority"] = prio_m.group(1)
            if pol_m: current_chain["policy"] = pol_m.group(1)
            continue

        # Rule match inside a chain
        if current_table and current_chain:
            # Extract handle if present (# handle 12)
            handle = None
            rule_content = trimmed
            h_match = re.search(r'#\s*handle\s+(\d+)', trimmed)
            if h_match:
                handle = int(h_match.group(1))
                rule_content = re.sub(r'#\s*handle\s+\d+', '', trimmed).strip()

            # Extract comment if present (comment "...")
            comment = ""
            cm_match = re.search(r'comment\s+"([^"]+)"', rule_content)
            if cm_match:
                comment = cm_match.group(1)

            # Extract verdict/action
            action = "other"
            if re.search(r'\baccept\b', rule_content): action = "accept"
            elif re.search(r'\bdrop\b', rule_content): action = "drop"
            elif re.search(r'\breject\b', rule_content): action = "reject"
            elif re.search(r'\bmasquerade\b', rule_content): action = "masquerade"
            elif re.search(r'\bdnat\b', rule_content): action = "dnat"
            elif re.search(r'\bsnat\b', rule_content): action = "snat"
            elif re.search(r'\bredirect\b', rule_content): action = "redirect"

            rules.append({
                "table_family": current_table["family"],
                "table_name": current_table["name"],
                "chain_name": current_chain["name"],
                "handle": handle,
                "rule_raw": rule_content,
                "action": action,
                "comment": comment
            })

    return {
        "status": get_nftables_status(),
        "tables": tables,
        "chains": chains,
        "rules": rules,
        "raw_config": raw_config,
        "active_ruleset_text": active_ruleset_text
    }

def validate_nftables(content=None):
    """
    Validates nftables syntax using 'nft -c -f <file>'.
    Returns (is_valid, message, error_output).
    """
    which_nft = shutil.which("nft")
    if not which_nft:
        return False, "nft command line utility is not installed.", "nft: command not found"

    test_file = None
    if content is not None:
        test_file = f"/tmp/nft_test_{int(time.time())}_{os.getpid()}.conf"
        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            return False, f"Failed to write temporary test file: {str(e)}", str(e)
    else:
        test_file = NFTABLES_CONF
        if not os.path.exists(test_file):
            return False, f"Configuration file {NFTABLES_CONF} not found.", "File not found"

    try:
        # Note: Order is 'nft -c -f <file>'
        res = subprocess.run(["nft", "-c", "-f", test_file], capture_output=True, text=True, timeout=10)
        is_valid = (res.returncode == 0)
        err = res.stderr.strip()
        out = res.stdout.strip()
        msg = "Syntax is valid ✓" if is_valid else (err or "Syntax validation failed")
        return is_valid, msg, err
    except Exception as e:
        return False, f"Error validating syntax: {str(e)}", str(e)
    finally:
        if content is not None and test_file and os.path.exists(test_file):
            try:
                os.remove(test_file)
            except Exception:
                pass

def apply_nftables_conf(content=None, backup_reason="Save and apply ruleset"):
    """
    Atomically saves and applies nftables configuration:
    1. Validates syntax with 'nft -c -f'.
    2. Backs up existing /etc/nftables.conf.
    3. Writes new content.
    4. Applies live with 'nft -f /etc/nftables.conf'.
    5. Triggers systemctl reload nftables.
    """
    if content is not None:
        is_valid, msg, err = validate_nftables(content)
        if not is_valid:
            return False, f"Syntax validation failed: {msg}", err

        # Backup current config
        backup_file = backup_nftables_conf(backup_reason)

        # Write atomically
        tmp_target = f"/tmp/nft_new_{int(time.time())}.conf"
        try:
            with open(tmp_target, "w", encoding="utf-8") as f:
                f.write(content)
            shutil.copy2(tmp_target, NFTABLES_CONF)
            os.remove(tmp_target)
            try:
                os.chmod(NFTABLES_CONF, 0o644)
            except Exception:
                pass
        except Exception as e:
            if os.path.exists(tmp_target):
                os.remove(tmp_target)
            return False, f"Failed to save {NFTABLES_CONF}: {str(e)}", str(e)

    # Apply configuration live
    try:
        res = subprocess.run(["nft", "-f", NFTABLES_CONF], capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            return False, f"Failed to apply ruleset with 'nft -f': {res.stderr.strip()}", res.stderr.strip()

        # Reload systemd service if active
        try:
            subprocess.run(["systemctl", "reload", "nftables"], capture_output=True, timeout=8)
        except Exception:
            pass

        return True, "Ruleset validated and applied live successfully with zero downtime.", ""
    except Exception as e:
        return False, f"Error executing nft command: {str(e)}", str(e)

def add_rule_to_conf(table_family, table_name, chain_name, rule_statement, comment=None):
    """
    Appends a rule statement to the specified table/chain in /etc/nftables.conf,
    validates the result, and applies it atomically.
    """
    if not os.path.exists(NFTABLES_CONF):
        return False, f"{NFTABLES_CONF} does not exist.", "File not found"

    with open(NFTABLES_CONF, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    full_rule = rule_statement.strip()
    if comment and 'comment' not in full_rule:
        full_rule += f' comment "{comment}"'

    # Locate the table and chain block
    new_lines = []
    in_target_table = False
    in_target_chain = False
    table_family = table_family.strip()
    table_name = table_name.strip()
    chain_name = chain_name.strip()
    inserted = False

    t_pattern = re.compile(rf'^\s*table\s+{re.escape(table_family)}\s+{re.escape(table_name)}\s*\{{?')
    c_pattern = re.compile(rf'^\s*chain\s+{re.escape(chain_name)}\s*\{{?')

    for line in lines:
        trimmed = line.strip()
        
        if not in_target_table and t_pattern.match(trimmed):
            in_target_table = True
            new_lines.append(line)
            continue

        if in_target_table and not in_target_chain and c_pattern.match(trimmed):
            in_target_chain = True
            new_lines.append(line)
            continue

        # If inside target chain and reached closing brace of chain
        if in_target_table and in_target_chain and trimmed == "}":
            # Insert rule right before closing brace
            indent = "        "
            new_lines.append(f"{indent}{full_rule}\n")
            new_lines.append(line)
            in_target_chain = False
            inserted = True
            continue

        if in_target_table and not in_target_chain and trimmed == "}":
            in_target_table = False
            new_lines.append(line)
            continue

        new_lines.append(line)

    if not inserted:
        # If target chain wasn't found, try appending structured block or report error
        return False, f"Could not locate chain '{chain_name}' inside table '{table_family} {table_name}' in {NFTABLES_CONF}.", "Chain not found in file"

    new_content = "".join(new_lines)
    return apply_nftables_conf(new_content, backup_reason=f"Add rule to {table_name}/{chain_name}")

def delete_rule_from_ruleset(table_family, table_name, chain_name, handle=None, rule_text=None):
    """
    Deletes a rule by handle using 'nft delete rule ... handle <id>'
    and persists the updated live ruleset to /etc/nftables.conf.
    """
    table_family = table_family.strip()
    table_name = table_name.strip()
    chain_name = chain_name.strip()

    if handle is not None:
        cmd = ["nft", "delete", "rule", table_family, table_name, chain_name, "handle", str(handle)]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode != 0:
                return False, f"Failed to delete rule: {res.stderr.strip()}", res.stderr.strip()

            # Save live ruleset back to /etc/nftables.conf
            res_dump = subprocess.run(["nft", "list", "ruleset"], capture_output=True, text=True, timeout=10)
            if res_dump.returncode == 0 and res_dump.stdout.strip():
                backup_nftables_conf(f"Delete rule handle {handle}")
                with open(NFTABLES_CONF, "w", encoding="utf-8") as f:
                    f.write("#!/usr/sbin/nft -f\n\nflush ruleset\n\n" + res_dump.stdout.strip() + "\n")

            return True, f"Rule handle {handle} deleted successfully.", ""
        except Exception as e:
            return False, f"Error deleting rule: {str(e)}", str(e)

    # If no handle provided, try removing by line matching in /etc/nftables.conf
    if rule_text and os.path.exists(NFTABLES_CONF):
        with open(NFTABLES_CONF, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        clean_rule = rule_text.strip()
        new_lines = [l for l in lines if clean_rule not in l.strip()]
        if len(new_lines) < len(lines):
            new_content = "".join(new_lines)
            return apply_nftables_conf(new_content, backup_reason="Delete rule by text match")

    return False, "Must provide a valid rule handle or rule text to delete.", "Missing identifier"
