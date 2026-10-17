"""WireGate - nftables firewall service layer & core engine.
Modeled after enterprise production change procedures (12-step safe mutation pipeline,
marker-delimited managed sections, dry-run syntax validation, timestamped JSON backups,
and automated rollback on error).
"""

import datetime
import difflib
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import tempfile
import time
from typing import Dict, List, Optional, Tuple

from app.core.config import DATA_DIR, WG_INTERFACE

# ---------------------------------------------------------------------------
# File paths and constants
# ---------------------------------------------------------------------------
NFT_CONF = os.environ.get("NFT_CONF", "/etc/nftables.conf")

def _resolve_act_nft() -> str:
    env_path = os.environ.get("NFT_ACT_PATH") or os.environ.get("ACT_NFT")
    if env_path and not env_path.endswith(".acl.nft"):
        return env_path
    try:
        os.makedirs("/etc/nftables", exist_ok=True)
    except Exception:
        pass
    return "/etc/nftables/acl.nft"

ACT_NFT = _resolve_act_nft()
FW_BACKUP_DIR = os.environ.get("FW_BACKUP_DIR", str(DATA_DIR / "firewall" / "backups"))
FW_DISABLED_PATH = os.environ.get("FW_DISABLED_PATH", str(DATA_DIR / "firewall" / "disabled.json"))

DEFAULT_ACL_TEMPLATE = """# /etc/nftables/acl.nft - WireGuard Access Control & Firewall Rules
# Loaded automatically by /etc/nftables.conf via: include "/etc/nftables/acl.nft"

table inet wiregate {
    chain input {
        type filter hook input priority filter; policy accept;
        # Allow established and related connections
        ct state established,related accept comment "Allow established traffic"
        # Allow loopback interface
        iif "lo" accept comment "Allow loopback"
        # Allow incoming WireGuard UDP traffic
        udp dport 443 accept comment "WireGuard Inbound Tunnel"
    }

    chain forward {
        type filter hook forward priority filter; policy accept;
        # Allow established and related connections
        ct state established,related accept comment "Allow established forwarding"
        # WireGuard Client Isolation (uncomment to prevent peers from reaching each other)
        # iifname "wg0" oifname "wg0" drop comment "WireGuard Client Isolation"
        # Allow VPN clients to access external network
        iifname "wg0" oifname != "wg0" accept comment "WireGuard Outbound Internet"
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        # NAT Masquerade for outbound VPN traffic
        ip saddr 172.29.250.0/24 oifname != "wg0" masquerade comment "WireGuard NAT Masquerade"
    }
}
"""

FAMILIES = ("ip", "ip6", "inet", "arp", "bridge", "netdev")
IDENT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,30}$")
RULE_CHARS_RE = re.compile(r"^[A-Za-z0-9 \t.,_:/{}[\]=!\"'*+@?%^()-]+$")
MAX_RULE_LEN = 512

ACTION_KEYWORDS = (
    "accept", "drop", "reject", "return", "continue",
    "jump", "goto", "log", "counter", "limit", "notrack",
    "masquerade", "snat", "dnat", "redirect", "queue", "synproxy",
)
VERDICT_KEYWORDS = (
    "accept", "drop", "reject", "return", "continue", "jump", "goto",
    "masquerade", "snat", "dnat", "redirect", "queue", "notrack", "synproxy",
    "log",
)
COUNTER_RE = re.compile(r"\bcounter packets (\d+) bytes (\d+)\b")
RULE_LINE_RE = re.compile(r"^\s+(.+?)\s*# handle (\d+)\s*$")
CHAIN_HEAD_RE = re.compile(r"^\s+chain\s+([A-Za-z0-9_.-]+)\s*\{")
TABLE_HEAD_RE = re.compile(r"^table\s+([A-Za-z0-9]+)\s+([A-Za-z0-9_.-]+)\s*\{")
CHAIN_TYPE_RE = re.compile(
    r"^\s+type\s+(\S+)\s+hook\s+(\S+)\s+priority\s+([^;]+);(?:\s*policy\s+(\S+);)?")
POLICY_RE = re.compile(r"^\s+policy\s+(\S+);")
IFBIND_RE = re.compile(
    r"\b(iifname|oifname)\s+(?:\"([^\"]+)\"|([A-Za-z0-9_./-]+))")

# Managed Section Markers
SECTION_HEAD = "# >>> WIREGATE MANAGED SECTION (auto-generated) - do not edit by hand"
SECTION_TAIL = "# <<< WIREGATE MANAGED SECTION END"

ACTIVE_RULE_RE = re.compile(
    r"^add rule (\S+) (\S+) (\S+) (.+?)\s+# wiregate:id:([0-9a-f]+)$")
DISABLED_RULE_RE = re.compile(
    r"^# wiregate:id:([0-9a-f]+) disabled by:(\S+) at:(\S+) (\S+) (\S+) (\S+) (.+)$")

MANAGED_TABLES = (
    {
        "family": "inet", "name": "wiregate",
        "chains": (
            {"name": "wg_input", "type": "filter", "hook": "input",
             "priority": "filter", "policy": "accept"},
            {"name": "wg_forward", "type": "filter", "hook": "forward",
             "priority": "filter", "policy": "drop"},
            {"name": "wg_nat", "type": "nat", "hook": "postrouting",
             "priority": "srcnat", "policy": "accept"},
        ),
    },
)

CAP_NET_ADMIN_BIT = 1 << 12
_HOST_IFACE_PREFIXES = (
    "docker", "veth", "br-", "virbr", "enp", "ens", "eno", "enx",
    "wl", "ww", "tun", "tap", "wg", "bond", "team",
)

SAMPLE_RULESET = """\
table inet wiregate { # handle 11
        chain wg_input { # handle 1
                type filter hook input priority filter; policy accept;
                ct state established,related accept comment "Allow established and related traffic" # handle 4
                iif "lo" accept comment "Allow loopback" # handle 5
                iifname "wg0" tcp dport 53 accept comment "Allow DNS over TCP from VPN" # handle 6
                iifname "wg0" udp dport 53 accept comment "Allow DNS over UDP from VPN" # handle 7
        }
        chain wg_forward { # handle 2
                type filter hook forward priority filter; policy drop;
                ct state established,related accept comment "Allow established and related traffic" # handle 8
                iifname "wg0" oifname "wg0" drop comment "WireGuard Client Isolation" # handle 9
                iifname "wg0" oifname != "wg0" accept comment "WireGuard Outbound Internet" # handle 10
        }
        chain wg_nat { # handle 3
                type nat hook postrouting priority srcnat; policy accept;
                ip saddr 172.29.250.0/24 oifname != "wg0" masquerade comment "WireGuard NAT Masquerade" # handle 11
        }
}
"""

# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

def _new_id(n=8) -> str:
    return secrets.token_hex(n)

def _read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return ""
    except OSError as e:
        raise ValueError(f"cannot read {path}: {e}")

def _atomic_write_text(path: str, text: str):
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".wiregate-", dir=directory, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        try:
            st = os.stat(path)
            os.chmod(tmp, stat.S_IMODE(st.st_mode))
            os.chown(tmp, st.st_uid, st.st_gid)
        except OSError:
            pass
        try:
            os.replace(tmp, path)
        except OSError as err:
            # Handle Docker single-file bind mount pinned inode (EBUSY / Errno 16)
            if err.errno == 16:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            else:
                raise
    except BaseException:
        try: os.unlink(tmp)
        except OSError: pass
        raise

def _unified_diff(before: str, after: str, fromfile="before", tofile="after") -> str:
    return "\n".join(difflib.unified_diff(
        (before or "").splitlines(), (after or "").splitlines(),
        fromfile=fromfile, tofile=tofile, lineterm=""))

def _normalize_live_text(text: str) -> str:
    text = re.sub(r"\bcounter packets \d+ bytes \d+\b", "counter", text or "")
    return re.sub(r"\s+", " ", text).strip()

def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()

def _format_bytes(num: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f} {unit}" if unit != "B" else f"{int(num)} B"
        num /= 1024.0
    return f"{num:.1f} PB"

# ---------------------------------------------------------------------------
# Capabilities and Environment Discovery
# ---------------------------------------------------------------------------
def nft_available() -> bool:
    return shutil.which("nft") is not None

def cap_net_admin() -> bool:
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("CapEff:"):
                    return (int(line.split()[1], 16) & CAP_NET_ADMIN_BIT) != 0
    except (OSError, ValueError, IndexError):
        pass
    return False

def netns_marker() -> str:
    override = os.environ.get("WG_FIREWALL_NETNS", "").strip().lower()
    if override in ("host", "isolated", "unknown"):
        return override
    try:
        ifaces = {n for n in os.listdir("/sys/class/net") if n != "lo"}
    except OSError:
        return "unknown"
    if any(n.startswith(_HOST_IFACE_PREFIXES) for n in ifaces):
        return "host"
    if ifaces and all(n.startswith("eth") for n in ifaces):
        return "isolated"
    return "unknown"

def deployment_mode() -> str:
    override = os.environ.get("WG_FIREWALL_MODE", "").strip().lower()
    if override in ("direct", "agent", "simulation"):
        return override
    if nft_available() and (os.geteuid() == 0 or cap_net_admin()):
        return "direct"
    return "simulation"

def nft_capabilities(conf_path=None) -> Dict:
    conf_path = conf_path or NFT_CONF
    mode = deployment_mode()
    return {
        "nft": nft_available(),
        "uid": os.geteuid(),
        "root": os.geteuid() == 0,
        "cap_net_admin": cap_net_admin(),
        "netns": netns_marker(),
        "mode": mode,
        "simulation": mode == "simulation",
        "conf_path": conf_path,
        "conf_exists": os.path.exists(conf_path),
        "managed_path": ACT_NFT,
        "managed_exists": os.path.exists(ACT_NFT),
    }

# ---------------------------------------------------------------------------
# Ruleset Parser & Statistics Engine
# ---------------------------------------------------------------------------
def raw_ruleset() -> Tuple[str, bool]:
    mode = deployment_mode()
    if mode == "direct":
        try:
            res = subprocess.run(["nft", "--handle", "list", "ruleset"],
                                 capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout, False
        except Exception:
            pass
    return SAMPLE_RULESET.rstrip("\n"), True

def _detect_verdict(text: str) -> str:
    verdict = ""
    for token in re.split(r"\s+", text):
        if token in VERDICT_KEYWORDS:
            verdict = token
    return verdict

def _classify_chain(chain: Dict) -> str:
    hook = chain.get("hook") or ""
    if chain.get("type") == "nat":
        return "nat"
    if hook in ("input", "forward", "output"):
        return hook
    if hook in ("prerouting", "postrouting"):
        return "nat"
    return "other"

def parse_ruleset(text: str) -> List[Dict]:
    tables = []
    table = None
    chain = None
    for line in text.splitlines():
        stripped = line.strip()
        m = TABLE_HEAD_RE.match(line)
        if m and chain is None:
            table = {"family": m.group(1), "name": m.group(2), "chains": []}
            tables.append(table)
            continue
        if stripped == "}":
            if chain is not None:
                chain = None
            else:
                table = None
            continue
        if table is None:
            continue
        m = CHAIN_HEAD_RE.match(line)
        if m and chain is None:
            chain = {"name": m.group(1), "type": "", "hook": "",
                     "priority": "", "policy": "", "rules": []}
            table["chains"].append(chain)
            continue
        if chain is None:
            continue
        m = CHAIN_TYPE_RE.match(line)
        if m:
            chain["type"] = m.group(1)
            chain["hook"] = m.group(2)
            chain["priority"] = m.group(3).strip()
            chain["policy"] = m.group(4) or ""
            continue
        m = POLICY_RE.match(line)
        if m:
            chain["policy"] = m.group(1)
            continue
        m = RULE_LINE_RE.match(line)
        if m:
            rule_text = m.group(1).strip()
            packets, bytes_count, has_counter = 0, 0, False
            cm = COUNTER_RE.search(rule_text)
            if cm:
                has_counter = True
                packets, bytes_count = int(cm.group(1)), int(cm.group(2))
            chain["rules"].append({
                "handle": int(m.group(2)),
                "family": table["family"],
                "table": table["name"],
                "chain": chain["name"],
                "text": rule_text,
                "packets": packets,
                "bytes": bytes_count,
                "has_counter": has_counter,
                "verdict": _detect_verdict(rule_text),
                "interfaces": [{"dir": b.group(1), "name": b.group(2) or b.group(3)}
                               for b in IFBIND_RE.finditer(rule_text)],
            })
    for tab in tables:
        for ch in tab["chains"]:
            ch["category"] = _classify_chain(ch)
            for rule in ch["rules"]:
                rule["category"] = ch["category"]
    return tables

def compute_stats(tables: List[Dict]) -> Dict:
    stats = {
        "tables": len(tables),
        "chains": 0, "rules": 0, "nat_rules": 0,
        "packets": 0, "bytes": 0,
        "accepted_packets": 0, "accepted_bytes": 0,
        "dropped_packets": 0, "dropped_bytes": 0,
        "policies": {},
        "interfaces": {},
    }
    for tab in tables:
        for ch in tab["chains"]:
            stats["chains"] += 1
            if ch.get("hook"):
                stats["policies"][ch["hook"]] = ch.get("policy") or "-"
            for rule in ch["rules"]:
                stats["rules"] += 1
                if rule["category"] == "nat":
                    stats["nat_rules"] += 1
                stats["packets"] += rule["packets"]
                stats["bytes"] += rule["bytes"]
                if rule["verdict"] == "accept":
                    stats["accepted_packets"] += rule["packets"]
                    stats["accepted_bytes"] += rule["bytes"]
                elif rule["verdict"] in ("drop", "reject"):
                    stats["dropped_packets"] += rule["packets"]
                    stats["dropped_bytes"] += rule["bytes"]
                for bind in rule["interfaces"]:
                    entry = stats["interfaces"].setdefault(bind["name"], {
                        "rules": 0, "packets": 0, "bytes": 0,
                        "accept": 0, "drop": 0})
                    entry["rules"] += 1
                    entry["packets"] += rule["packets"]
                    entry["bytes"] += rule["bytes"]
                    if rule["verdict"] == "accept":
                        entry["accept"] += rule["packets"]
                    elif rule["verdict"] in ("drop", "reject"):
                        entry["drop"] += rule["packets"]
    return stats

# ---------------------------------------------------------------------------
# ManagedSection System
# ---------------------------------------------------------------------------
class ManagedSection:
    HEAD = SECTION_HEAD
    TAIL = SECTION_TAIL

    def __init__(self, path=None):
        self.path = path or ACT_NFT

    def read(self) -> str:
        return _read_file(self.path)

    def exists(self) -> bool:
        return os.path.isfile(self.path)

    def split(self, text=None) -> Tuple[str, str, str, bool]:
        text = self.read() if text is None else text
        head = text.find(self.HEAD)
        if head < 0:
            return text, "", "", False
        tail = text.find(self.TAIL, head + len(self.HEAD))
        if tail < 0:
            return text[:head], text[head:], "", True
        end = tail + len(self.TAIL)
        return text[:head], text[head:end], text[end:], True

    def records(self, text=None) -> List[Dict]:
        text = self.read() if text is None else text
        _, section, _, _ = self.split(text)
        records = []
        for raw in section.splitlines():
            line = raw.strip()
            if not line:
                continue
            m = ACTIVE_RULE_RE.match(line)
            if m:
                records.append({
                    "id": m.group(5),
                    "family": m.group(1), "table": m.group(2),
                    "chain": m.group(3), "text": m.group(4).strip(),
                    "active": True,
                })
                continue
            m = DISABLED_RULE_RE.match(line)
            if m:
                records.append({
                    "id": m.group(1),
                    "disabled_by": m.group(2), "disabled_at": m.group(3),
                    "family": m.group(4), "table": m.group(5),
                    "chain": m.group(6), "text": m.group(7).strip(),
                    "active": False,
                })
        return records

    def render(self, records: List[Dict]) -> str:
        lines = [self.HEAD, ""]
        for tab in MANAGED_TABLES:
            lines.append(f"add table {tab['family']} {tab['name']}")
            lines.append(f"flush table {tab['family']} {tab['name']}")
            for ch in tab["chains"]:
                lines.append(
                    f"add chain {tab['family']} {tab['name']} {ch['name']} "
                    f"{{ type {ch['type']} hook {ch['hook']} priority "
                    f"{ch['priority']}; policy {ch['policy']}; }}")
        lines.append("")
        for r in records:
            if r["active"]:
                lines.append(
                    f"add rule {r['family']} {r['table']} {r['chain']} "
                    f"{r['text']} # wiregate:id:{r['id']}")
            else:
                lines.append(
                    f"# wiregate:id:{r['id']} disabled by:"
                    f"{r.get('disabled_by', '?')} at:{r.get('disabled_at', '?')} "
                    f"{r['family']} {r['table']} {r['chain']} {r['text']}")
        lines.append(self.TAIL)
        return "\n".join(lines) + "\n"

    def propose(self, records: List[Dict]) -> str:
        before, _, after, _ = self.split()
        new_section = self.render(records)
        if not before and not after:
            return new_section
        if before and not before.endswith("\n"):
            before = before + "\n"
        return before + new_section + after

class DisabledRuleStore:
    def __init__(self, path=None):
        self.path = path or FW_DISABLED_PATH
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def list(self) -> List[Dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                return json.load(fh).get("rules", [])
        except Exception:
            return []

    def _save(self, rules: List[Dict]):
        _atomic_write_text(self.path, json.dumps({"rules": rules}, indent=2))

    def add(self, rule: Dict, username: str) -> Dict:
        rules = self.list()
        record = {
            "id": rule.get("id") or _new_id(8),
            "family": rule["family"], "table": rule["table"],
            "chain": rule["chain"], "text": rule["text"],
            "disabled_by": username, "disabled_at": _now_iso(),
        }
        rules = [r for r in rules if r.get("id") != record["id"]]
        rules.append(record)
        self._save(rules)
        return record

    def pop(self, rule_id: str) -> Optional[Dict]:
        rules = self.list()
        record = next((r for r in rules if r.get("id") == rule_id), None)
        if record:
            self._save([r for r in rules if r.get("id") != rule_id])
        return record

# ---------------------------------------------------------------------------
# Backups Management
# ---------------------------------------------------------------------------
def create_backup(backup_dir=None, prefix="manual") -> Dict:
    backup_dir = backup_dir or FW_BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = f"{prefix}-{stamp}.json"
    conf_text = _read_file(NFT_CONF)
    managed_text = _read_file(ACT_NFT)
    manifest = {
        "format": "wiregate-firewall-backup",
        "version": 2,
        "created": _now_iso(),
        "conf_path": NFT_CONF,
        "managed_path": ACT_NFT,
        "conf": conf_text,
        "managed": managed_text,
        "conf_sha256": _sha256(conf_text),
        "managed_sha256": _sha256(managed_text),
        "ruleset": "",
        "simulated": deployment_mode() == "simulation",
    }
    try:
        manifest["ruleset"] = raw_ruleset()[0]
    except Exception:
        pass
    with open(os.path.join(backup_dir, name), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return {"name": name, "simulated": manifest["simulated"]}

def list_backups(backup_dir=None) -> List[Dict]:
    backup_dir = backup_dir or FW_BACKUP_DIR
    result = []
    try:
        names = sorted(os.listdir(backup_dir), reverse=True)
    except OSError:
        return result
    for name in names:
        if not (name.endswith(".json") or name.endswith(".nft")):
            continue
        path = os.path.join(backup_dir, name)
        try:
            stat_info = os.stat(path)
        except OSError:
            continue
        created = datetime.datetime.fromtimestamp(
            stat_info.st_mtime, datetime.timezone.utc).isoformat(timespec="seconds")
        result.append({"name": name, "size": stat_info.st_size, "created": created})
    return result

def restore_backup(backup_dir=None, name="") -> Dict:
    backup_dir = backup_dir or FW_BACKUP_DIR
    path = os.path.join(backup_dir, name)
    if not os.path.isfile(path):
        raise ValueError(f"Backup {name} not found")
    with open(path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if manifest.get("format") != "wiregate-firewall-backup":
        raise ValueError("Invalid backup format")

    managed_path = manifest.get("managed_path") or ACT_NFT
    conf_path = manifest.get("conf_path") or NFT_CONF

    _atomic_write_text(managed_path, manifest.get("managed") or "")
    _atomic_write_text(conf_path, manifest.get("conf") or "")

    # Validate syntax
    is_valid, err = NFTablesEngine.validate_ruleset(manifest.get("conf") or "")
    if not is_valid:
        raise ValueError(f"Restored configuration syntax invalid: {err}")

    # Scoped apply
    return {"ok": True, "name": name, "message": "Restored and validated successfully"}

# ---------------------------------------------------------------------------
# Validation & Rule Builder
# ---------------------------------------------------------------------------
def validate_rule_text(rule_text: str, family: str = "inet", table: str = "wiregate", chain: str = "wg_forward", semantic: bool = True) -> Dict:
    text = (rule_text or "").strip()
    checks = []
    if not text:
        raise ValueError("Rule text is required")
    if len(text) > MAX_RULE_LEN:
        raise ValueError(f"Rule is too long (max {MAX_RULE_LEN} chars)")
    checks.append("length")
    if not RULE_CHARS_RE.match(text):
        raise ValueError("Rule contains forbidden characters")
    checks.append("charset")
    tokens = set(re.split(r"\s+", text))
    if not tokens & set(ACTION_KEYWORDS):
        raise ValueError("Rule has no action keyword")
    checks.append("action-keyword")

    if semantic and nft_available():
        test_script = f"table {family} {table} {{\n  chain {chain} {{\n    {text}\n  }}\n}}\n"
        is_valid, msg = NFTablesEngine.validate_ruleset(test_script)
        if not is_valid:
            raise ValueError(f"NFTables dry-run syntax error: {msg}")
        checks.append("nft -c dry-run")

    return {"ok": True, "checks": checks}

# ---------------------------------------------------------------------------
# The Main NFTablesEngine Class (Unified Facade)
# ---------------------------------------------------------------------------
class NFTablesEngine:
    """Core manager for NFTables firewall configuration, atomic application, and WireGuard ACLs."""

    TABLE_FAMILY = "inet"
    TABLE_NAME = "wiregate"

    @classmethod
    def is_nft_available(cls) -> bool:
        return nft_available()

    @classmethod
    def capabilities(cls) -> Dict:
        return nft_capabilities()

    @classmethod
    def raw_ruleset(cls) -> Tuple[str, bool]:
        return raw_ruleset()

    @classmethod
    def parse_ruleset(cls, text: str) -> List[Dict]:
        return parse_ruleset(text)

    @classmethod
    def compute_stats(cls, tables: List[Dict]) -> Dict:
        return compute_stats(tables)

    @classmethod
    def get_ruleset(cls) -> Dict:
        text, simulated = raw_ruleset()
        tables = parse_ruleset(text)
        stats = compute_stats(tables)
        sec = ManagedSection()
        records = sec.records() if sec.exists() else []
        disabled_store = DisabledRuleStore()
        disabled = [r for r in records if not r["active"]] or disabled_store.list()
        return {
            "tables": tables,
            "stats": stats,
            "disabled": disabled,
            "managed": records,
            "raw": text,
            "simulated": simulated,
            "collected": _now_iso(),
        }

    @classmethod
    def create_backup(cls, prefix="manual") -> Dict:
        return create_backup(FW_BACKUP_DIR, prefix=prefix)

    @classmethod
    def list_backups(cls) -> List[Dict]:
        return list_backups(FW_BACKUP_DIR)

    @classmethod
    def restore_backup(cls, name: str) -> Dict:
        return restore_backup(FW_BACKUP_DIR, name)

    @classmethod
    def validate_ruleset(cls, config_text: str) -> Tuple[bool, str]:
        """Validates an NFTables configuration using dry-run syntax check (`nft -c -f`)."""
        if not cls.is_nft_available():
            return False, "nftables binary ('nft') is not available on this system."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nft", delete=False) as tmp:
            tmp.write(config_text)
            tmp_path = tmp.name

        try:
            proc = subprocess.run(
                ["nft", "-c", "-f", tmp_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0:
                return True, "NFTables syntax and ruleset are valid."
            else:
                err_msg = proc.stderr.strip() or proc.stdout.strip()
                clean_err = err_msg.replace(tmp_path, "ruleset.nft")
                return False, clean_err
        except Exception as e:
            return False, f"Validation execution failed: {str(e)}"
        finally:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass

    @classmethod
    def compile_ruleset(
        cls,
        server_subnet: str = "10.8.0.0/24",
        interface: str = "wg0",
        client_isolation: bool = True,
        internet_access: bool = True,
        allow_dns: bool = True,
        default_forward_policy: str = "drop",
        acls: Optional[List[dict]] = None,
        custom_rules: Optional[List[dict]] = None,
        mss_clamping: bool = True,
        drop_invalid: bool = True,
        icmp_limit: bool = True,
        log_dropped: bool = False
    ) -> str:
        acls = acls or []
        custom_rules = custom_rules or []

        subnet_clean = server_subnet.strip()
        if "/32" in subnet_clean:
            subnet_clean = subnet_clean.replace("/32", "/24")

        lines = [
            "# WireGate NFTables Firewall Configuration",
            "# Auto-generated by WireGate Control Center",
            "",
            f"table {cls.TABLE_FAMILY} {cls.TABLE_NAME} {{",
            "",
            "    # WireGuard Local Input Chain",
            "    chain wg_input {",
            "        type filter hook input priority filter; policy accept;",
            "        ct state established,related accept comment \"Allow established and related traffic\"",
            "        iif \"lo\" accept comment \"Allow loopback\"",
            "        udp dport 443 accept comment \"Allow WireGuard Inbound UDP 443 on ens19\"",
        ]

        if drop_invalid:
            lines.append('        ct state invalid drop comment "Drop invalid conntrack states"')

        if icmp_limit:
            lines.append('        icmp type echo-request limit rate 10/second accept comment "Rate limit ICMP ping"')

        if allow_dns:
            lines.extend([
                f'        iifname "{interface}" meta l4proto tcp tcp dport 53 accept comment "Allow DNS over TCP from VPN"',
                f'        iifname "{interface}" meta l4proto udp udp dport 53 accept comment "Allow DNS over UDP from VPN"',
            ])

        for rule in custom_rules:
            if rule.get("enabled", True) and rule.get("chain") == "wg_input":
                stmt = rule["statement"].strip().rstrip(";")
                comment = f' comment "{rule.get("comment")}"' if rule.get("comment") else ""
                lines.append(f"        {stmt}{comment}")

        lines.extend([
            "    }",
            "",
            "    # WireGuard Forwarding & ACL Chain",
            "    chain wg_forward {",
            f"        type filter hook forward priority filter; policy {default_forward_policy};",
            "        ct state established,related accept comment \"Allow established and related traffic\"",
        ])

        if drop_invalid:
            lines.append('        ct state invalid drop comment "Drop invalid conntrack states"')

        if mss_clamping:
            lines.append(f'        iifname "{interface}" tcp flags syn / syn,rst tcp option maxseg size set rt mtu comment "Clamp TCP MSS to PMTU"')

        if client_isolation:
            lines.append(f'        iifname "{interface}" oifname "{interface}" drop comment "WireGuard Client Isolation"')

        for acl in acls:
            if not acl.get("enabled", True):
                continue
            rule_parts = []
            src = acl.get("src_cidr", "").strip()
            if src and src.lower() != "any":
                rule_parts.append(f"ip saddr {src}")
            dst = acl.get("dst_cidr", "").strip()
            if dst and dst.lower() != "any":
                rule_parts.append(f"ip daddr {dst}")

            proto = (acl.get("proto") or "all").lower().strip()
            ports = (acl.get("ports") or "").strip()
            if proto in ["tcp", "udp"]:
                rule_parts.append(f"meta l4proto {proto}")
                if ports and ports.lower() != "any":
                    if "," in ports or "-" in ports:
                        rule_parts.append(f"{proto} dport {{ {ports} }}")
                    else:
                        rule_parts.append(f"{proto} dport {ports}")
            elif proto == "icmp":
                rule_parts.append("meta l4proto icmp")

            action = (acl.get("action") or "accept").lower().strip()
            rule_parts.append(action)
            name = acl.get("name", "ACL Rule").replace('"', "'")
            rule_parts.append(f'comment "WireGuard ACL: {name}"')
            lines.append(f"        {' '.join(rule_parts)}")

        for rule in custom_rules:
            if rule.get("enabled", True) and rule.get("chain") == "wg_forward":
                stmt = rule["statement"].strip().rstrip(";")
                comment = f' comment "{rule.get("comment")}"' if rule.get("comment") else ""
                lines.append(f"        {stmt}{comment}")

        if internet_access:
            lines.append(f'        iifname "{interface}" oifname != "{interface}" accept comment "WireGuard Outbound Internet"')

        if log_dropped:
            lines.append('        log prefix "[NFT-FORWARD-DROP]: "')

        lines.extend([
            "    }",
            "",
            "    # WireGuard NAT Postrouting Chain",
            "    chain wg_nat {",
            "        type nat hook postrouting priority srcnat; policy accept;",
        ])

        if internet_access:
            lines.append(f'        ip saddr {subnet_clean} oifname != "{interface}" masquerade comment "WireGuard NAT Masquerade"')

        for rule in custom_rules:
            if rule.get("enabled", True) and rule.get("chain") == "wg_nat":
                stmt = rule["statement"].strip().rstrip(";")
                comment = f' comment "{rule.get("comment")}"' if rule.get("comment") else ""
                lines.append(f"        {stmt}{comment}")

        lines.extend([
            "    }",
            "}",
            ""
        ])
        return "\n".join(lines)

    @classmethod
    def apply_ruleset(cls, config_text: str) -> Tuple[bool, str]:
        is_valid, val_msg = cls.validate_ruleset(config_text)
        if not is_valid:
            return False, f"Validation failed: {val_msg}"

        backup_content = None
        try:
            bk_proc = subprocess.run(
                ["nft", "list", "table", cls.TABLE_FAMILY, cls.TABLE_NAME],
                capture_output=True,
                text=True
            )
            if bk_proc.returncode == 0:
                backup_content = bk_proc.stdout
        except Exception:
            pass

        atomic_script = f"table {cls.TABLE_FAMILY} {cls.TABLE_NAME}\ndelete table {cls.TABLE_FAMILY} {cls.TABLE_NAME}\n" + config_text

        with tempfile.NamedTemporaryFile(mode="w", suffix=".nft", delete=False) as tmp:
            tmp.write(atomic_script)
            tmp_path = tmp.name

        try:
            proc = subprocess.run(
                ["nft", "-f", tmp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if proc.returncode != 0:
                err_msg = proc.stderr.strip() or proc.stdout.strip()
                if backup_content:
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".nft", delete=False) as rb_tmp:
                        rb_tmp.write(backup_content)
                        rb_path = rb_tmp.name
                    subprocess.run(["nft", "-f", rb_path], capture_output=True)
                    try: os.remove(rb_path)
                    except Exception: pass
                    return False, f"Apply failed: {err_msg} (Rolled back to previous ruleset)"
                return False, f"Apply failed: {err_msg}"

            return True, "NFTables ruleset safely applied to kernel."
        except Exception as e:
            return False, f"Error executing nft command: {str(e)}"
        finally:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass

    @classmethod
    def get_active_ruleset_text(cls) -> str:
        text, _ = raw_ruleset()
        return text

    @classmethod
    def delete_rule_by_handle(cls, family: str, table: str, chain: str, handle: int) -> Tuple[bool, str]:
        if not cls.is_nft_available():
            return False, "nftables is not available."
        try:
            proc = subprocess.run(
                ["nft", "delete", "rule", family, table, chain, "handle", str(handle)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.returncode == 0:
                return True, f"Rule handle {handle} deleted from {table}/{chain}."
            else:
                return False, f"Delete failed: {proc.stderr.strip()}"
        except Exception as e:
            return False, f"Error deleting rule: {str(e)}"

    @classmethod
    def add_rule_to_chain(cls, family: str, table: str, chain: str, statement: str) -> Tuple[bool, str]:
        if not cls.is_nft_available():
            return False, "nftables is not available."
        clean_stmt = statement.strip().rstrip(";")
        try:
            # First dry-run validate rule syntax
            test_ruleset = f"table {family} {table} {{\n    chain {chain} {{\n        {clean_stmt}\n    }}\n}}"
            valid, val_err = cls.validate_ruleset(test_ruleset)
            if not valid:
                return False, f"Rule syntax invalid: {val_err}"

            cmd = f"nft add rule {family} {table} {chain} {clean_stmt}"
            proc = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0:
                return True, f"Rule successfully added to {chain}."
            else:
                return False, f"Failed to add rule: {proc.stderr.strip() or proc.stdout.strip()}"
        except Exception as e:
            return False, f"Error adding rule: {str(e)}"

    @classmethod
    def replace_rule_by_handle(cls, family: str, table: str, chain: str, handle: int, statement: str) -> Tuple[bool, str]:
        if not cls.is_nft_available():
            return False, "nftables is not available."
        clean_stmt = statement.strip().rstrip(";")
        try:
            test_ruleset = f"table {family} {table} {{\n    chain {chain} {{\n        {clean_stmt}\n    }}\n}}"
            valid, val_err = cls.validate_ruleset(test_ruleset)
            if not valid:
                return False, f"Rule syntax invalid: {val_err}"

            cmd = f"nft replace rule {family} {table} {chain} handle {handle} {clean_stmt}"
            proc = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0:
                return True, f"Rule handle #{handle} updated successfully."
            else:
                return False, f"Failed to update rule: {proc.stderr.strip() or proc.stdout.strip()}"
        except Exception as e:
            return False, f"Error updating rule: {str(e)}"

    @classmethod
    def get_acl_file_info(cls) -> dict:
        path = ACT_NFT
        content = ""
        exists = os.path.exists(path)
        if exists:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"# Error reading file {path}: {e}"
        else:
            content = DEFAULT_ACL_TEMPLATE
            try:
                _atomic_write_text(path, content)
                exists = True
            except Exception:
                pass

        included = False
        try:
            if os.path.exists(NFT_CONF):
                with open(NFT_CONF, "r", encoding="utf-8") as f:
                    conf_text = f.read()
                    name = os.path.basename(path)
                    included = any(
                        line.strip().startswith("include") and (name in line or "act.nft" in line or "acl.nft" in line)
                        for line in conf_text.splitlines()
                    )
        except Exception:
            pass

        return {
            "path": path,
            "content": content,
            "exists": exists,
            "lines": len(content.splitlines()),
            "characters": len(content),
            "included_in_conf": included,
            "conf_path": NFT_CONF,
        }

    @classmethod
    def get_conf_file_info(cls) -> dict:
        path = NFT_CONF
        content = ""
        exists = os.path.exists(path)
        if exists:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"# Error reading file {path}: {e}"
        else:
            content = """#!/usr/sbin/nft -f\n\nflush ruleset\n\ntable inet filter {\n    chain input {\n        type filter hook input priority filter; policy accept;\n    }\n    chain forward {\n        type filter hook forward priority filter; policy accept;\n    }\n    chain output {\n        type filter hook output priority filter; policy accept;\n    }\n}\n\ninclude "/etc/nftables/acl.nft"\n"""
            try:
                _atomic_write_text(path, content)
                exists = True
            except Exception:
                pass

        return {
            "path": path,
            "content": content,
            "exists": exists,
            "lines": len(content.splitlines()),
            "characters": len(content),
        }

    @classmethod
    def save_conf_file(cls, content: str) -> Tuple[bool, str]:
        path = NFT_CONF
        try:
            if os.path.exists(path):
                try:
                    create_backup(FW_BACKUP_DIR, prefix="pre_edit_conf")
                    # Also create on-disk backup file
                    ts = int(time.time())
                    bak_path = f"{path}.bak.{ts}"
                    shutil.copy2(path, bak_path)
                except Exception:
                    pass
            _atomic_write_text(path, content)
            return True, f"File {path} successfully saved."
        except Exception as e:
            return False, f"Failed to save {path}: {str(e)}"

    @classmethod
    def save_acl_file(cls, content: str) -> Tuple[bool, str]:
        path = ACT_NFT
        try:
            if os.path.exists(path):
                try:
                    create_backup(FW_BACKUP_DIR, prefix="pre_edit_acl")
                    # Also create on-disk backup file
                    ts = int(time.time())
                    bak_path = f"{path}.bak.{ts}"
                    shutil.copy2(path, bak_path)
                    # Retain last 10 on-disk backups
                    dir_name = os.path.dirname(path)
                    base_name = os.path.basename(path)
                    baks = sorted([
                        os.path.join(dir_name, f) for f in os.listdir(dir_name)
                        if f.startswith(f"{base_name}.bak.")
                    ])
                    for old_bak in baks[:-10]:
                        try: os.remove(old_bak)
                        except Exception: pass
                except Exception:
                    pass
            _atomic_write_text(path, content)
            return True, f"File {path} successfully saved."
        except Exception as e:
            return False, f"Failed to save {path}: {str(e)}"

    @classmethod
    def import_kernel_rules(cls) -> Tuple[bool, str, List[dict]]:
        """
        Reads live ruleset from kernel (`nft list ruleset`), extracts table inet wiregate
        or custom forward ACL rules, and returns them for inspection/import.
        """
        if not cls.is_nft_available():
            return False, "nftables binary is not available on this system.", []

        try:
            output = ""
            proc = subprocess.run(["nft", "list", "table", "inet", "wiregate"], capture_output=True, text=True, timeout=5)
            if proc.returncode == 0 and proc.stdout.strip():
                output = proc.stdout
            else:
                proc2 = subprocess.run(["nft", "list", "ruleset"], capture_output=True, text=True, timeout=5)
                if proc2.returncode == 0 and proc2.stdout.strip():
                    output = proc2.stdout

            if not output:
                return False, "No active rules found in kernel.", []

            extracted_rules = []
            tables = parse_ruleset(output)
            for tab in tables:
                for ch in tab.get("chains", []):
                    if ch.get("name") in ["forward", "wg_forward"]:
                        for r in ch.get("rules", []):
                            text = r.get("text", "").strip()
                            if "ct state established" in text:
                                continue
                            if text.startswith('iifname "wg0" oifname != "wg0"'):
                                continue
                            extracted_rules.append({
                                "table": tab.get("name", "wiregate"),
                                "chain": ch.get("name", "forward"),
                                "statement": text,
                                "verdict": r.get("verdict", "accept")
                            })

            return True, f"Extracted {len(extracted_rules)} rules from kernel.", extracted_rules
        except Exception as e:
            return False, f"Failed to read kernel rules: {str(e)}", []

    @classmethod
    def merge_rules_into_conf_file(cls, rules_text: str) -> Tuple[bool, str]:
        """
        Safely merges rule statements into /etc/nftables.conf.
        Validates the entire file with `nft -c -f` before saving.
        """
        if not rules_text or not rules_text.strip():
            return False, "No rules provided to import."

        path = NFT_CONF
        existing_content = _read_file(path)
        if not existing_content or not existing_content.strip():
            existing_content = "#!/usr/sbin/nft -f\n\nflush ruleset\n"

        clean_lines = []
        for line in rules_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("table ") or line_str.startswith("chain ") or line_str in ["}", "{", "};"]:
                continue
            clean_lines.append("        " + line_str)

        if not clean_lines:
            new_content = existing_content.rstrip() + "\n\n" + rules_text.strip() + "\n"
        else:
            formatted_rules = "\n".join(clean_lines)
            if "chain forward {" in existing_content:
                target_marker = 'iifname "wg0" oifname != "wg0" accept'
                if target_marker in existing_content:
                    parts = existing_content.split(target_marker, 1)
                    new_content = parts[0] + "# Imported Rules\n" + formatted_rules + "\n        " + target_marker + parts[1]
                else:
                    idx = existing_content.rfind("chain forward {")
                    brace_end = existing_content.find("}", idx)
                    if brace_end > 0:
                        new_content = existing_content[:brace_end] + "\n        # Imported Rules\n" + formatted_rules + "\n    " + existing_content[brace_end:]
                    else:
                        new_content = existing_content + "\n" + formatted_rules
            else:
                new_content = existing_content.rstrip() + "\n\n" + formatted_rules + "\n"

        is_valid, msg = cls.validate_ruleset_file(new_content, target="conf")
        if not is_valid:
            return False, f"Import aborted: Syntax validation failed with proposed rules: {msg}"

        ok, save_msg = cls.save_conf_file(new_content)
        if not ok:
            return False, f"Failed to save {path}: {save_msg}"

        return True, f"Successfully merged rules into {path}."

    @classmethod
    def merge_rules_into_acl_file(cls, rules_text: str) -> Tuple[bool, str]:
        """
        Safely merges rule statements into /etc/nftables/acl.nft.
        Validates the entire file with `nft -c -f` before writing.
        """
        if not rules_text or not rules_text.strip():
            return False, "No rules provided to import."

        path = ACT_NFT
        existing_content = _read_file(path) or ""

        clean_lines = []
        for line in rules_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("table ") or line_str.startswith("chain ") or line_str in ["}", "{", "};"]:
                continue
            clean_lines.append(line_str)

        if not clean_lines:
            new_content = existing_content.rstrip() + "\n\n" + rules_text.strip() + "\n"
        else:
            new_content = existing_content.rstrip() + "\n\n" + "\n".join(clean_lines) + "\n"

        is_valid, msg = cls.validate_ruleset_file(new_content, target="acl")
        if not is_valid:
            return False, f"Import aborted: Syntax validation failed with proposed rules: {msg}"

        ok, save_msg = cls.save_acl_file(new_content)
        if not ok:
            return False, f"Failed to save {path}: {save_msg}"

        return True, f"Successfully merged rules into {path}."

    @classmethod
    def validate_ruleset_file(cls, content: Optional[str] = None, target: str = "conf") -> Tuple[bool, str]:
        """Validates ruleset content with `nft -c -f`."""
        if not cls.is_nft_available():
            return False, "nftables binary ('nft') is not available on this system."

        target_file = NFT_CONF if target == "conf" else ACT_NFT
        wrapped_lines_offset = 0

        if content is not None:
            val_content = content
            # If target is "acl" and content does not declare a table/chain wrapper, wrap it
            if target == "acl" and not re.search(r"^\s*table\s+", content, re.MULTILINE):
                val_content = "table inet filter {\n    chain vpn_acl {\n" + content + "\n    }\n}\n"
                wrapped_lines_offset = 2

            with tempfile.NamedTemporaryFile(mode="w", suffix=".nft", delete=False) as tmp:
                tmp.write(val_content)
                tmp_path = tmp.name
        else:
            if target == "acl":
                disk_text = _read_file(target_file)
                if disk_text and not re.search(r"^\s*table\s+", disk_text, re.MULTILINE):
                    wrapped = "table inet filter {\n    chain vpn_acl {\n" + disk_text + "\n    }\n}\n"
                    wrapped_lines_offset = 2
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".nft", delete=False) as tmp:
                        tmp.write(wrapped)
                        tmp_path = tmp.name
                else:
                    tmp_path = target_file
            else:
                tmp_path = target_file

        try:
            proc = subprocess.run(
                ["nft", "-c", "-f", tmp_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            base_name = os.path.basename(target_file)
            if proc.returncode == 0:
                return True, f"NFTables syntax is valid for {base_name}. No errors found."
            else:
                err_msg = proc.stderr.strip() or proc.stdout.strip()
                if wrapped_lines_offset > 0:
                    def _adj_line(m):
                        ln = max(1, int(m.group(1)) - wrapped_lines_offset)
                        return f"{base_name}:{ln}"
                    clean_err = re.sub(rf"{re.escape(tmp_path)}:(\d+)", _adj_line, err_msg)
                else:
                    clean_err = err_msg.replace(tmp_path, base_name)
                return False, clean_err
        except Exception as e:
            return False, f"Validation execution failed: {str(e)}"
        finally:
            if tmp_path != target_file and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except Exception: pass

    @classmethod
    def reload_ruleset_file(cls, content: Optional[str] = None, target: str = "conf") -> Tuple[bool, str]:
        """Validates first, saves (if content provided), and safely reloads via `nft -f`."""
        if not cls.is_nft_available():
            return False, "nftables binary ('nft') is not available on this system."

        target_file = NFT_CONF if target == "conf" else ACT_NFT

        # If content provided, validate it first!
        if content is not None:
            is_valid, val_msg = cls.validate_ruleset_file(content, target=target)
            if not is_valid:
                return False, f"Reload aborted: Syntax error in {os.path.basename(target_file)}: {val_msg}"
            if target == "conf":
                ok, save_msg = cls.save_conf_file(content)
            else:
                ok, save_msg = cls.save_acl_file(content)
            if not ok:
                return False, f"Reload aborted: {save_msg}"

        # If target is acl, reloading /etc/nftables.conf reloads both conf and acl atomically
        reload_target = NFT_CONF
        if not os.path.exists(reload_target):
            reload_target = target_file

        try:
            proc = subprocess.run(
                ["nft", "-f", reload_target],
                capture_output=True,
                text=True,
                timeout=10
            )
            if proc.returncode == 0:
                return True, f"NFTables ruleset ({os.path.basename(target_file)}) successfully applied and reloaded into kernel."
            else:
                err_msg = proc.stderr.strip() or proc.stdout.strip()
                return False, f"Reload failed: {err_msg}"
        except Exception as e:
            return False, f"Error executing nft reload: {str(e)}"

    @classmethod
    def link_acl_into_conf(cls) -> Tuple[bool, str]:
        try:
            path = ACT_NFT  # /etc/nftables/acl.nft
            conf = NFT_CONF
            if not os.path.exists(conf):
                return False, f"Config file {conf} does not exist."
            with open(conf, "r", encoding="utf-8") as f:
                content = f.read()
            if 'include "/etc/nftables.acl.nft"' in content:
                content = content.replace('include "/etc/nftables.acl.nft"', f'include "{path}"')
                with open(conf, "w", encoding="utf-8") as f:
                    f.write(content)
                return True, f"Updated include directive to \"{path}\" in {conf}."
            if f'include "{path}"' in content:
                return True, f"Include directive already present in {conf}."
            with open(conf, "a", encoding="utf-8") as f:
                f.write(f'\ninclude "{path}"\n')
            return True, f"Successfully linked include \"{path}\" into {conf}."
        except Exception as e:
            return False, f"Failed to link include into {NFT_CONF}: {str(e)}"

