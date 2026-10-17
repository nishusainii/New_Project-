#!/usr/bin/env python3
# ============================================================
#  refresh-dashboard.py
#  ------------------------------------------------------------
#  Rebuilds EVERY data block of the deployed dashboard.html from
#  the freshly generated SARG report, so all sections (subtitle,
#  KPIs, top consumers, sites, platform mix, denied hotspots,
#  alerts, insights, leaderboard, totals, footer) always match
#  the current report period — not a stale hand-tuned snapshot.
#
#  It replaces content between AUTO markers in dashboard.html:
#     <!-- AUTO:NAME --> ... <!-- /AUTO:NAME -->   (HTML blocks)
#     // AUTO:NAME       ... // /AUTO:NAME         (JS arrays)
#
#  Usage:
#     refresh-dashboard.py --report <report-dir> --dashboard <dashboard.html>
#
#  Exit status: 0 on success/partial success; 2 if the report's
#  index.html cannot be parsed (caller falls back to KPI-only).
# ============================================================
import argparse
import datetime
import html as html_mod
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ------------------------------------------------------------
# small helpers
# ------------------------------------------------------------
MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
    "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
}


def parse_report_folder(name):
    """
    Parses a SARG report folder name like '17Sep2026-17Sep2026', '06Oct2026-07Oct2026', or with '.1'.
    Returns a dict with metadata, or None if not matching SARG date format.
    """
    m = re.match(r"^(\d{2})([A-Za-z]{3})(\d{4})-(\d{2})([A-Za-z]{3})(\d{4})(?:\.\d+)?$", name)
    if not m:
        return None
    d1, mon1, y1, d2, mon2, y2 = m.groups()
    m_num1 = MONTH_MAP.get(mon1.lower(), "01")
    m_num2 = MONTH_MAP.get(mon2.lower(), "01")
    try:
        dt1 = datetime.date(int(y1), int(m_num1), int(d1))
        dt2 = datetime.date(int(y2), int(m_num2), int(d2))
    except ValueError:
        return None

    days_diff = (dt2 - dt1).days
    # A daily report is either same-day (dt1 == dt2) or consecutive-day overnight (dt2 - dt1 == 1)
    is_daily = (days_diff in (0, 1))

    # The effective date of the daily activity is dt1 (e.g. 06Oct-07Oct covers 06 Oct daily traffic)
    effective_date = dt1
    iso = effective_date.strftime("%Y-%m-%d")

    if is_daily:
        label = f"{effective_date.day} {mon1.capitalize()} {y1}"
    else:
        label = f"{int(d1)} {mon1.capitalize()} - {int(d2)} {mon2.capitalize()} {y2}"

    return {
        "folder": name,
        "is_single_day": is_daily,
        "iso": iso,
        "label": label,
        "date": effective_date,
        "days_diff": days_diff,
    }


TAG = re.compile(r"<[^>]+>")
MULT = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
GB   = {"": 1 / 1024**3, "K": 1 / 1024**2, "M": 1 / 1024, "G": 1.0, "T": 1024.0}


def clean(s):
    return html_mod.unescape(TAG.sub("", s or "")).strip()


def parse_count(s):
    """'557.22K' -> 572236 ; '18' -> 18"""
    m = re.match(r"^\s*([0-9]*\.?[0-9]+)\s*([KMGT])?\s*$", s)
    return int(float(m.group(1)) * MULT[m.group(2) or ""]) if m else 0


def parse_gb(s):
    """'494.10G' -> 494.10 GB ; '587.72M' -> 0.57395 GB"""
    m = re.match(r"^\s*([0-9]*\.?[0-9]+)\s*([KMGT])?\s*$", s)
    return float(m.group(1)) * GB[m.group(2) or ""] if m else 0.0


def fmt_total(g):
    return f"{g/1024:.2f} TB" if g >= 1024 else f"{g:.1f} GB"


def fmt_conn(c):
    if c >= 1_000_000:
        return f"{c/1_000_000:.2f}M"
    if c >= 1_000:
        return f"{c/1_000:.2f}K"
    return str(c)


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def fmt_date_str(d_str):
    parts = d_str.split("/")
    if len(parts) == 3:
        try:
            p0, p1, y = int(parts[0]), int(parts[1]), str(parts[2]).strip()
            if len(y) == 2:
                y = f"20{y}"
            if p0 > 12 and 1 <= p1 <= 12:
                d, m = p0, p1
            elif p1 > 12 and 1 <= p0 <= 12:
                m, d = p0, p1
            else:
                m, d = p0, p1
            mon = MONTHS[m - 1] if 1 <= m <= 12 else str(m)
            return f"{d:02d} {mon} {y}", f"{y}-{m:02d}-{d:02d}"
        except Exception:
            pass
    return d_str, d_str


def fmt_bytes_disp(gb):
    if gb >= 1024:
        return f"{gb/1024:.2f} TB"
    elif gb >= 1:
        return f"{gb:.2f} GB"
    elif gb >= 1/1024:
        return f"{gb*1024:.2f} MB"
    elif gb > 0:
        return f"{gb*1024*1024:.2f} KB"
    return "0 B"


# ------------------------------------------------------------
# SARG page parsers
# ------------------------------------------------------------
def parse_index(path):
    txt = path.read_text(encoding="utf-8", errors="replace")
    rows = []
    row_re = re.compile(
        r'<tr><td class="data">(\d+)</td><td class="data2">.*?</td>'
        r'<td class="data2"><a [^>]*>([^<]+)</a></td>'
        r'<td class="data">([^<]+)</td><td class="data">([^<]+)</td>'
        r'<td class="data">([0-9.]+)%</td><td class="data">([0-9.]+)%</td>'
        r'<td class="data">([0-9.]+)%</td><td class="data">([^<]+)</td>'
        r'<td class="data">([^<]+)</td><td class="data">([0-9.]+)%</td></tr>', re.S)
    for m in row_re.finditer(txt):
        rows.append({
            "rank": int(m.group(1)), "ip": clean(m.group(2)),
            "conn_s": m.group(3), "conn": parse_count(m.group(3)),
            "bytes_s": m.group(4), "gb": parse_gb(m.group(4)),
            "pct": float(m.group(5)), "in_pct": float(m.group(6)),
            "out_pct": float(m.group(7)), "elapsed": m.group(8),
        })
    period = ""
    m = re.search(r"Period:[^<]*", txt)
    if m:
        period = re.sub(r"^Period:[^0-9A-Za-z]+", "", m.group(0)).strip()
    gent = ""
    m = re.search(r"on ([0-9]{2}/[A-Za-z]{3}/[0-9]{4}-[0-9:]+)", txt)
    if m:
        gent = m.group(1)
    return rows, period, gent


def parse_topsites(path):
    rows = []
    if not path.exists():
        return rows
    txt = path.read_text(encoding="utf-8", errors="replace")
    ts_re = re.compile(
        r'<tr><td class="data">(\d+)</td>'
        r'<td class="data2"><a [^>]*>([^<]+)</a></td>'
        r'<td class="data">([^<]+)</td><td class="data">([^<]+)</td>'
        r'<td class="data">([^<]+)</td><td class="data">([^<]+)</td></tr>', re.S)
    for m in ts_re.finditer(txt):
        site_name = clean(m.group(2))
        cat = family_of(site_name) or "Web / Other"
        rows.append({
            "rank": int(m.group(1)),
            "site": site_name,
            "conn_s": clean(m.group(3)),
            "gb": parse_gb(clean(m.group(4))),
            "bytes_s": clean(m.group(4)),
            "time": clean(m.group(5)),
            "users": clean(m.group(6)),
            "category": cat
        })
    return rows


def parse_events(path, more_word):
    """denied.html / authfail.html: USERID | IP/NAME | DATE/TIME | SITE rows
    with carry-forward IP blocks and trailing 'N more <more_word>...' notes.
    NOTE: SARG's HTML rows are malformed — pages close header rows with
    </th> instead of </tr>, so we split on the NEXT <tr (or table end),
    not on </tr>.  A block's "N more ..." count is attributed to the last
    site seen in the block (the dominant one in hotspot blocks).
    Returns (per_ip Counter, per_site Counter, {site: Counter(clients)})."""
    per_ip, per_site = Counter(), Counter()
    site_clients = {}
    if not path.exists():
        return per_ip, per_site, site_clients
    txt = path.read_text(encoding="utf-8", errors="replace")
    cur_ip, cur_site = "", ""
    for rm in re.finditer(r"<tr[^>]*>(.*?)(?=<tr[^>]*>|</table>|\Z)", txt, re.S):
        row = rm.group(1)
        mm = re.search(r"([\d,]+)\s+more\s+" + more_word, clean(row))
        if mm:
            n = int(mm.group(1).replace(",", ""))
            if cur_ip:
                per_ip[cur_ip] += n
            if cur_site:
                per_site[cur_site] += n
                if cur_ip:
                    site_clients.setdefault(cur_site, Counter())[cur_ip] += n
            continue
        cells = re.findall(r'<td class="data2?">(.*?)</td>', row, re.S)
        if len(cells) != 4:
            continue
        ip = clean(cells[1])
        site = clean(cells[3])
        if ip:
            cur_ip = ip
        if site:
            cur_site = site
        if not re.search(r"\d{1,2}/\d{1,2}/\d{2,4}-\d{2}:\d{2}:\d{2}", cells[2]):
            continue
        if not cur_ip:
            continue
        per_ip[cur_ip] += 1
        if site:
            per_site[site] += 1
            site_clients.setdefault(site, Counter())[cur_ip] += 1
    return per_ip, per_site, site_clients


def parse_downloads(path):
    """Parses download.html to extract large file transfers and speedtests."""
    if not path.exists():
        return []
    txt = path.read_text(encoding="utf-8", errors="replace")
    records = []
    cur_ip = ""
    for m in re.finditer(r'<tr><td class="data">(.*?)</td><td class="data">(.*?)</td><td class="data">(.*?)</td><td class="data2"><a href="([^"]+)">([^<]+)</a></td></tr>', txt):
        ip_col = m.group(1).strip()
        dt_col = m.group(3).strip()
        furl = m.group(4).strip()
        ip_match = re.search(r'>([^<]+)<', ip_col)
        if ip_match:
            cur_ip = ip_match.group(1).strip()
        elif ip_col:
            cur_ip = ip_col
        fname = furl.split('/')[-1].split('?')[0] or furl
        records.append({"ip": cur_ip, "datetime": dt_col, "url": furl, "filename": fname})

    grouped = {}
    for r in records:
        u = r["url"]
        if u not in grouped:
            is_st = bool(re.search(r"speedtest|speedof|fast\.com|10mb\.zip", u, re.I))
            grouped[u] = {
                "filename": r["filename"],
                "url": u,
                "count": 0,
                "last_time": r["datetime"],
                "ips": Counter(),
                "is_speedtest": is_st
            }
        grouped[u]["count"] += 1
        grouped[u]["last_time"] = r["datetime"]
        if r["ip"]:
            grouped[u]["ips"][r["ip"]] += 1

    res = []
    for g in sorted(grouped.values(), key=lambda x: x["count"], reverse=True):
        top_ip = g["ips"].most_common(1)[0][0] if g["ips"] else ""
        res.append({
            "filename": g["filename"],
            "url": g["url"],
            "count": g["count"],
            "top_ip": top_ip,
            "last_time": g["last_time"],
            "is_speedtest": g["is_speedtest"],
            "unique_users": len(g["ips"])
        })
    return res


def parse_daily_and_hourly(rep_dir):
    """
    Scans the current report and all sibling reports in rep_dir.parent to extract:
    1. Daily aggregate totals for ALL users combined (daily_days).
    2. Per-user daily usage records (daily_records).
    3. Distinct dates with their total traffic and active user count (dates_list).
    4. Global 24-hour hourly traffic aggregation for the current report (hourly).
    """
    days_agg = {}
    current_rep_hourly = [0.0] * 24

    # Target folders: sibling reports in parent + current report
    parent_dir = rep_dir.parent
    target_dirs = []
    if parent_dir.exists():
        candidates = []
        for d in parent_dir.iterdir():
            if d.is_dir() and any(d.glob("*/d*.html")):
                meta = parse_report_folder(d.name)
                if meta and meta["is_single_day"]:
                    candidates.append((meta, d))
        # Deduplicate by date (prefer current rep or cleanest folder name)
        candidates.sort(key=lambda x: (x[0]["date"], x[1].resolve() == rep_dir.resolve(), not "." in x[1].name), reverse=True)
        seen_dates = set()
        for meta, d in candidates:
            if meta["iso"] not in seen_dates:
                seen_dates.add(meta["iso"])
                target_dirs.append(d)
    if rep_dir not in target_dirs:
        target_dirs.append(rep_dir)

    daily_records = []

    for r_dir in target_dirs:
        r_name = r_dir.name
        is_curr = (r_dir.resolve() == rep_dir.resolve())

        for f in r_dir.glob("*/d*.html"):
            ip_dir = f.parent.name
            ip = ip_dir.replace("_", ".")
            subnet = ".".join(ip.split(".")[:3]) + ".0/24"
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            rows = re.findall(r'<tr[^>]*><td class=["\']data["\'][^>]*>(\d{1,2}/\d{1,2}/\d{2,4})</td>(.*?)</tr>', txt, re.S)
            for date_raw, row_content in rows:
                cells = re.findall(r'<td class=["\']data["\']>([^<]*)</td>', row_content)
                if not cells:
                    continue
                total_s = cells[-1].strip()
                gb = parse_gb(total_s)
                hourly_vals = [round(parse_gb(c.strip()), 2) for c in cells[:24]]

                if is_curr:
                    for h, val in enumerate(hourly_vals):
                        current_rep_hourly[h] += val

                if gb <= 0 and not any(h > 0 for h in hourly_vals):
                    continue

                date_fmt, date_iso = fmt_date_str(date_raw)
                peak_h = hourly_vals.index(max(hourly_vals)) if max(hourly_vals) > 0 else 0

                if date_iso not in days_agg:
                    days_agg[date_iso] = {
                        "date": date_fmt,
                        "iso": date_iso,
                        "total_gb": 0.0,
                        "hourly": [0.0] * 24,
                        "report_folder": r_name,
                        "users": {}
                    }

                entry = days_agg[date_iso]
                entry["total_gb"] += gb
                for h in range(24):
                    if h < len(hourly_vals):
                        entry["hourly"][h] += hourly_vals[h]

                if ip not in entry["users"]:
                    entry["users"][ip] = {
                        "ip": ip,
                        "subnet": subnet,
                        "gb": 0.0,
                        "peak_h": peak_h,
                        "peak_gb": round(max(hourly_vals), 2),
                        "ip_dir": ip_dir,
                        "hourly": hourly_vals
                    }
                entry["users"][ip]["gb"] += gb

    # Keep only the last 5 days (most recent) for daily usage
    MAX_DAILY_DAYS = 5
    if len(days_agg) > MAX_DAILY_DAYS:
        top_isos = set(sorted(days_agg.keys(), reverse=True)[:MAX_DAILY_DAYS])
        days_agg = {iso: d for iso, d in days_agg.items() if iso in top_isos}

    total_all_days_gb = sum(d["total_gb"] for d in days_agg.values())
    max_day_gb = max((d["total_gb"] for d in days_agg.values()), default=1.0)

    daily_days = []
    daily_records = []
    for iso in sorted(days_agg.keys(), reverse=True):
        d = days_agg[iso]
        tot_gb = round(d["total_gb"], 2)
        users_list = list(d["users"].values())
        users_list.sort(key=lambda u: u["gb"], reverse=True)
        for u in users_list:
            u["gb"] = round(u["gb"], 2)
            u["bytes_s"] = fmt_bytes_disp(u["gb"])
            u["day_pct"] = round(u["gb"] * 100 / tot_gb, 1) if tot_gb > 0 else 0.0
            daily_records.append({
                "date": d["date"],
                "date_iso": d["iso"],
                "ip": u["ip"],
                "subnet": u["subnet"],
                "bytes_s": u["bytes_s"],
                "gb": u["gb"],
                "peak_h": u["peak_h"],
                "peak_gb": u["peak_gb"],
                "ip_dir": u["ip_dir"],
                "hourly": u["hourly"],
                "day_pct": u["day_pct"]
            })

        top_u = users_list[0] if users_list else None
        hourly_rounded = [round(v, 2) for v in d["hourly"]]
        peak_val = max(hourly_rounded) if hourly_rounded else 0.0
        peak_h = hourly_rounded.index(peak_val) if peak_val > 0 else 0

        daily_days.append({
            "date": d["date"],
            "iso": d["iso"],
            "total_gb": tot_gb,
            "bandwidth_str": fmt_bytes_disp(tot_gb),
            "pct_total": round(tot_gb * 100 / total_all_days_gb, 1) if total_all_days_gb > 0 else 0.0,
            "pct_peak_day": round(tot_gb * 100 / max_day_gb, 1) if max_day_gb > 0 else 0.0,
            "users_count": len(users_list),
            "top_user_ip": top_u["ip"] if top_u else "—",
            "top_user_gb": top_u["gb"] if top_u else 0.0,
            "top_user_str": top_u["bytes_s"] if top_u else "0 B",
            "top_user_dir": top_u["ip_dir"] if top_u else "",
            "peak_h": peak_h,
            "peak_gb": round(peak_val, 2),
            "peak_str": f"{peak_h:02d}:00 ({fmt_bytes_disp(peak_val)})",
            "hourly": hourly_rounded,
            "report_folder": d["report_folder"],
            "users": [
                [u["ip"], u["subnet"], u["bytes_s"], u["gb"], u["day_pct"], u["peak_h"], u["peak_gb"], u["ip_dir"], u["hourly"]]
                for u in users_list
            ]
        })

    daily_records.sort(key=lambda x: (x["date_iso"], x["gb"]), reverse=True)
    dates_list = [{"date": d["date"], "iso": d["iso"], "total_gb": d["total_gb"], "users_count": d["users_count"]} for d in daily_days]

    return daily_days, daily_records, dates_list, [round(v, 2) for v in current_rep_hourly]

# ------------------------------------------------------------
# platform classification for the traffic-mix donut
# ------------------------------------------------------------
FAMILIES = [
    ("SAP User", "#06b6d4",
     ("pbs.twimg.com", "abs.twimg.com", "bsap")),
    ("Twitter / X", "#3fb9ef",
     ("twimg", "twitter", "x.com", "t.co", "twtrdns", "tweetdeck")),
    ("Meta (FB/IG/WhatsApp)", "#7c9ff7",
     ("fbcdn", "facebook", "instagram", "whatsapp", "cdninstagram", "fbsbx",
      "messenger.com", "fb.com", "fb.net")),
    ("Google services", "#3ddc97",
     ("google", "googlevideo", "youtube", "ytimg", "gstatic", "gmail",
      "googleusercontent", "gvt1", "gvt2", "gmodules", "googlesyndication",
      "doubleclick", "google-analytics", "ggpht", "android.com", "goo.gl",
      "withgoogle", "googleapis")),
    ("Dev / tools (GitHub…)", "#ffc857",
     ("github", "gitlab", "docker", "pypi.org", "npmjs", "nodesource",
      "pythonhosted", "debian", "ubuntu", "nuget", "maven", "gradle",
      "rubygems", "crates.io", "golang", "go.dev", "k8s.io", "quay.io",
      "gcr.io", "sonatype", "jfrog", "hashicorp", "terraform", "anaconda",
      "bitbucket", "sourceforge", "openai.com", "anthropic.com")),
]


def family_of(hostport):
    host = hostport.split(":")[0].lower()
    labels = host.split(".")
    for name, _c, keys in FAMILIES:
        for k in keys:
            if "." in k:                       # explicit suffix rule
                if host == k or host.endswith("." + k):
                    return name
            elif any(lbl.startswith(k) or k in lbl for lbl in labels):
                return name
    return None


# ------------------------------------------------------------
# narrative builders
# ------------------------------------------------------------
ICONS = {
    "bad":  '<span class="ai"><svg viewBox="0 0 24 24"><path d="M12 9v4m0 3.2v.3M10.3 4.1 3 17.2A2 2 0 0 0 4.8 20h14.4a2 2 0 0 0 1.7-2.8L13.7 4.1a2 2 0 0 0-3.4 0z"/></svg></span>',
    "warn": '<span class="ai"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 8v5m0 3.2v.3"/></svg></span>',
    "info": '<span class="ai"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8.2v-.3"/></svg></span>',
}


def denied_hint(site, top_client, nclients):
    if "example.com" in site:
        return f"probe loop from {top_client}" if top_client else "probe loop"
    if "mtalk.google.com" in site:
        return f"Google push msg · {nclients} hosts"
    if top_client and nclients == 1:
        return f"from {top_client}"
    if nclients:
        return f"{nclients} hosts"
    return "blocked by policy"


def build_denied(den_site, site_clients):
    if not den_site:
        return ('\n        <div class="chip"><span class="cn">No denied events recorded this period</span>'
                '<span class="cv">0 hits</span></div>\n      ')
    out = []
    for i, (site, n) in enumerate(den_site.most_common(5)):
        clients = site_clients.get(site, Counter())
        top_client = clients.most_common(1)[0][0] if clients else ""
        cls = "chip cy" if i >= 3 else "chip"
        label = f"{site} — {denied_hint(site, top_client, len(clients))}"
        out.append(f'        <div class="{cls}"><span class="cn">{html_mod.escape(label, quote=False)}</span>'
                   f'<span class="cv">≈{n:,} hits</span></div>')
    return "\n" + "\n".join(out) + "\n      "



def build_alerts(users, auth_ip, auth_sites, auth_clients, den_site, site_clients, topsites_rows, hourly=None, tot_gb=0.0):
    items = []

    # 1. authentication failures
    auth_total = sum(auth_ip.values())
    if auth_total and auth_ip:
        top_ip, top_n = auth_ip.most_common(1)[0]
        share = top_n * 100 / auth_total
        # top site for THAT host (fall back to the global top auth site)
        top_site = ""
        best = 0
        for s, cc in auth_clients.items():
            if cc.get(top_ip, 0) > best:
                best, top_site = cc[top_ip], s
        if not top_site and auth_sites:
            top_site = auth_sites.most_common(1)[0][0]
        who = f"<b>{top_ip}</b>" + (f" hammering <b>{top_site}</b>" if top_site else "")
        txt = (f"<b>{auth_total:,} authentication failures</b> were logged from "
               f"<b>{len(auth_ip)} hosts</b>. One host alone — {who} — accounts for "
               f"<b>{top_n:,} (~{share:.0f}%)</b> of them")
        if len(auth_ip) > 1:
            r_ip, r_n = auth_ip.most_common(2)[1]
            txt += f"; the runner-up {r_ip} adds {r_n:,} more"
        txt += ". A job or client is very likely running without proxy credentials."
        items.append(("bad", txt))

    # 2. bandwidth spike / anomaly detection
    spikers = [u for u in users if u.get("spike_pct", 0) >= 50 and u["gb"] >= 5.0]
    if spikers:
        top_spiker = max(spikers, key=lambda x: x.get("spike_pct", 0))
        avg_p = top_spiker.get("avg_prior", 0)
        items.append(("warn",
                      f"<b>Bandwidth Spike Detected:</b> Host <b>{top_spiker['ip']}</b> consumed "
                      f"<b>{top_spiker['gb']:.1f} GB</b> today (<b>+{top_spiker['spike_pct']}%</b> "
                      f"above its 5-day baseline of {avg_p:.1f} GB/day) — verify for unexpected streaming or sync loops."))
    elif users and users[0]["gb"] >= 50.0:
        u = users[0]
        warn = (f"<b>Heavy Consumer Alert:</b> <b>{u['ip']}</b> (top user) transferred "
                f"<b>{u['conn_s']} connections / {u['gb']:.0f} GB</b>")
        try:
            hours = int(u["elapsed"].split(":")[0])
            if hours > 30:
                warn += (f" with an effective session time of ~{hours/24:.0f} days in 24 h — "
                         f"consistent with an automated sync or long-lived streaming workload")
        except (ValueError, IndexError):
            pass
        warn += "."
        items.append(("warn", warn))

    # 3. high connection velocity / scanner detection
    scanner = next((u for u in users if u["conn"] >= 40_000 and u["gb"] < 1.0), None)
    if scanner:
        items.append(("warn",
                      f"<b>High Connection Velocity:</b> Host <b>{scanner['ip']}</b> generated "
                      f"<b>{scanner['conn_s']} connections</b> with only <b>{fmt_total(scanner['gb'])}</b> "
                      f"transferred — potential automated polling script, crawler, or connection loop."))

    # 4. off-hours traffic
    if hourly:
        off_hours_gb = sum(hourly[:9]) + sum(hourly[18:])
        tot_h_gb = sum(hourly)
        if tot_h_gb > 0:
            off_pct = off_hours_gb * 100 / tot_h_gb
            if off_pct >= 25.0 and off_hours_gb >= 5.0:
                items.append(("info",
                              f"<b>Significant Off-Hours Traffic:</b> <b>{fmt_total(off_hours_gb)}</b> "
                              f"({off_pct:.1f}% of daily bandwidth) occurred outside business hours (09:00–18:00) — "
                              f"review for scheduled overnight jobs or automated sync tasks."))

    # 5. bandwidth concentration
    if len(users) >= 5 and tot_gb > 0:
        top5_gb = sum(u["gb"] for u in users[:5])
        top5_pct = top5_gb * 100 / tot_gb
        items.append(("info",
                      f"<b>Bandwidth Concentration:</b> The top 5 of {len(users)} active hosts consumed "
                      f"<b>{top5_pct:.0f}% of total network bandwidth</b> ({fmt_total(top5_gb)} combined). "
                      f"Consider traffic shaping or quotas if WAN saturation occurs."))

    # 6. speed-test loop / fallback: heaviest denied pair
    st = next((s for s in topsites_rows
               if re.search(r"speedtest|speedof|librespeed|fast\.com|10mb\.zip", s["site"], re.I)), None)
    if st:
        items.append(("info",
                      f"<b>Speed-test loop detected:</b> repeated large downloads from "
                      f"<b>{html_mod.escape(st['site'], quote=False)}</b> "
                      f"(rank #{st['rank']} in Top Sites, {st['conn_s']} connections) — "
                      f"likely a bandwidth-monitoring script."))
    elif den_site:
        (ds, dn) = den_site.most_common(1)[0]
        c = site_clients.get(ds, Counter()).most_common(1)
        via = f" attempts from client host <b>{c[0][0]}</b>" if c else ""
        items.append(("info",
                      f"<b>Blocked-traffic hotspot:</b> <b>{dn:,} denied requests</b>{via} targeting "
                      f"<b>{html_mod.escape(ds, quote=False)}</b> — see the Denied report."))

    if not items:
        items.append(("info", "All network indicators within normal operational baseline."))
    return "\n" + "\n".join(
        f'        <div class="alert {k}">\n          {ICONS[k]}\n          <div>{t}</div>\n        </div>'
        for k, t in items) + "\n      "


def build_insights(users, mix, tot_gb, in_pct, den_site, site_clients):
    n_users = len(users)
    lead = max((m for m in mix if m[1] > 0), key=lambda m: m[1], default=None)
    ins = []
    if lead and tot_gb:
        ins.append(("ins",
                    f"<b>{html_mod.escape(lead[0])} leads the traffic mix:</b> it accounts for "
                    f"<span class=\"hl\">{lead[1]/tot_gb*100:.0f}% of all bytes</span> "
                    f"({lead[1]:.1f} GB of {fmt_total(tot_gb)})."))
    out_gb = tot_gb * (100 - in_pct) / 100 if tot_gb else 0
    ins.append(("ins green",
                f"<b>Cache is working hard:</b> a <span class=\"hl\">{in_pct:.2f}% hit ratio</span> "
                f"means only ≈{out_gb:.2f} GB actually left to the internet — the proxy is "
                f"highly effective at deduplicating content."))
    if len(users) >= 5 and tot_gb:
        top5_gb = sum(u["gb"] for u in users[:5])
        ins.append(("ins amber",
                    f"<b>Concentration risk:</b> the top 5 of {n_users} users consumed "
                    f"<span class=\"hl\">{top5_gb/tot_gb*100:.0f}% of bandwidth</span> "
                    f"({top5_gb:.0f} GB combined). Consider per-user quotas for heavy streaming endpoints."))
    if len(users) >= 10:
        subs = Counter(".".join(u["ip"].split(".")[:3]) for u in users[:10])
        (sub, cnt) = subs.most_common(1)[0]
        if cnt >= 3:
            ins.append(("ins",
                        f"<b>Heavy hitters cluster in {sub}.x:</b> {cnt} of the top 10 consumers "
                        f"live on the {sub}.0 subnet — the busiest segment by far."))
    if den_site:
        (ds, dn) = den_site.most_common(1)[0]
        dn_tot = sum(den_site.values())
        c = site_clients.get(ds, Counter()).most_common(1)
        via = f" from {c[0][0]}" if c else ""
        ins.append(("ins red",
                    f"<b>Policy enforcement is active:</b> <span class=\"hl\">{dn_tot:,} denials</span>, "
                    f"dominated by {html_mod.escape(ds, quote=False)}{via} (≈{dn:,})."))
    small = sum(1 for u in users if u["gb"] < 1)
    if small and n_users:
        ins.append(("ins",
                    f"<b>Long tail is tiny:</b> {small} of {n_users} users used under 1 GB each — "
                    f"the network is driven by a small power-user core."))
    return "\n" + "\n".join(f'    <div class="{k}">{t}</div>' for k, t in ins) + "\n  "


# ------------------------------------------------------------
# AUTO-marker replacement
# ------------------------------------------------------------
def replace_blocks(doc, name, content):
    """Replace the inner text of every AUTO:<name> block (HTML or JS comment form)."""
    pats = [
        re.compile(r"(<!--\s*AUTO:" + name + r"\s*-->).*?(<!--\s*/AUTO:" + name + r"\s*-->)", re.S),
        re.compile(r"(//\s*AUTO:" + name + r"\s*).*?(//\s*/AUTO:" + name + r"\s*)", re.S),
    ]
    found = False
    for p in pats:
        if p.search(doc):
            found = True
            doc = p.sub(lambda m: m.group(1) + content + m.group(2), doc)
    if not found:
        print(f"    note: marker AUTO:{name} not found — block left unchanged", file=sys.stderr)
    return doc


def patch_attr(doc, rid, value):
    return re.sub(r'(id="' + rid + r'">)[^<]*', lambda m: m.group(1) + value, doc)


# ------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", required=True)
    ap.add_argument("--dashboard", required=True)
    a = ap.parse_args()

    rep, dashp = Path(a.report), Path(a.dashboard)
    idx = rep / "index.html"
    if not idx.exists() or not dashp.exists():
        print(f"refresh-dashboard: missing {idx} or {dashp}", file=sys.stderr)
        return 2

    users, period, gent = parse_index(idx)
    if not users:
        print(f"refresh-dashboard: no user rows parsed from {idx}", file=sys.stderr)
        return 2

    topsites_rows = parse_topsites(rep / "topsites.html")
    den_ip, den_site, den_clients = parse_events(rep / "denied.html", "denied")
    auth_ip, auth_site, auth_cli = parse_events(rep / "authfail.html", "authentication")
    downloads = parse_downloads(rep / "download.html")
    daily_days, daily_records, dates_list, hourly = parse_daily_and_hourly(rep)

    tot_gb   = sum(u["gb"] for u in users)
    tot_conn = sum(u["conn"] for u in users)
    in_pct   = (sum(u["gb"] * u["in_pct"] for u in users) / tot_gb) if tot_gb else 0.0
    out_pct  = 100.0 - in_pct
    in_gb    = tot_gb * in_pct / 100
    out_gb   = tot_gb * out_pct / 100
    denied_n = sum(den_ip.values())
    auth_n   = sum(auth_ip.values())

    # ---- baseline & spike calculation per user ---------------------------
    user_priors = {}
    for d in daily_days:
        if d.get("report_folder") != rep.name:
            for urow in d.get("users", []):
                u_ip = urow[0]
                u_gb = float(urow[3])
                user_priors.setdefault(u_ip, []).append(u_gb)

    for u in users:
        priors = user_priors.get(u["ip"], [])
        if priors:
            avg_p = sum(priors) / len(priors)
            u["avg_prior"] = round(avg_p, 2)
            if avg_p >= 0.5:
                u["spike_pct"] = round((u["gb"] - avg_p) / avg_p * 100)
            else:
                u["spike_pct"] = 0
        else:
            u["avg_prior"] = 0.0
            u["spike_pct"] = 0

    # ---- subnets aggregation ----------------------------------------------
    subnets_map = defaultdict(lambda: {"gb": 0.0, "conn": 0, "users": 0})
    for u in users:
        parts = u["ip"].split(".")
        subnet = ".".join(parts[:3]) + ".x" if len(parts) == 4 else "Other"
        subnets_map[subnet]["gb"] += u["gb"]
        subnets_map[subnet]["conn"] += u["conn"]
        subnets_map[subnet]["users"] += 1
        u["subnet"] = subnet
        u["ip_dir"] = u["ip"].replace(".", "_")

    subnets_list = []
    for s_name, s_data in sorted(subnets_map.items(), key=lambda x: x[1]["gb"], reverse=True):
        subnets_list.append({
            "name": s_name,
            "gb": round(s_data["gb"], 2),
            "pct": round(s_data["gb"] * 100 / tot_gb, 1) if tot_gb else 0.0,
            "users": s_data["users"],
            "conn": fmt_conn(s_data["conn"])
        })

    # ---- traffic mix ------------------------------------------------------
    fam_gb = {name: 0.0 for name, _c, _k in FAMILIES}
    for s in topsites_rows:
        fam = family_of(s["site"])
        if fam:
            fam_gb[fam] += s["gb"]
    mix = [(name, round(fam_gb[name], 1), color)
           for name, color, _k in FAMILIES if fam_gb[name] > 0]
    else_gb = max(tot_gb - sum(fam_gb.values()), 0.0)
    mix.append(("Everything else", round(else_gb, 1), "#46637f"))

    # ---- JS data block ----------------------------------------------------
    def js_users():
        rows = []
        for u in users:
            rows.append([
                u["ip"], u["conn_s"], round(u["gb"], 2), u["pct"],
                f"{u['in_pct']:.2f}", f"{u['out_pct']:.2f}",
                u.get("subnet", ""), u.get("ip_dir", u["ip"].replace(".", "_")),
                u.get("elapsed", ""),
                u.get("spike_pct", 0),
                u.get("avg_prior", 0.0)
            ])
        return ",\n  ".join(json.dumps(r, separators=(",", ":")) for r in rows)

    def site_bytes_disp(bs):
        m = re.match(r"^([0-9.]+)([KMGT]?)$", bs)
        if not m:
            return html_mod.escape(bs, quote=True)
        return m.group(1) + " " + ({"K": "KB", "M": "MB", "G": "GB", "T": "TB"}.get(m.group(2), "B"))

    def js_sites():
        rows = []
        for s in topsites_rows:
            cat = s.get("category") or family_of(s["site"]) or "Web / Other"
            rows.append([
                s["site"],
                s["conn_s"],
                site_bytes_disp(s["bytes_s"]),
                int(s["users"] or 0),
                cat,
                round(s["gb"], 2),
                s.get("time", ""),
                s["rank"]
            ])
        return ",\n  ".join(json.dumps(r, separators=(",", ":")) for r in rows)

    def js_daily():
        rows = []
        for r in daily_records:
            rows.append([
                r["date"], r["ip"], r["subnet"], r["bytes_s"], r["gb"],
                r["peak_h"], r["peak_gb"], r["ip_dir"], r["day_pct"],
                r["hourly"], r["date_iso"]
            ])
        return ",\n  ".join(json.dumps(row, separators=(",", ":")) for row in rows)

    available_reports = []
    parent_dir = rep.resolve().parent
    if parent_dir and parent_dir.is_dir():
        candidates = []
        for d in parent_dir.iterdir():
            if d.is_dir() and (d / "index.html").exists() and d.name != "images":
                meta = parse_report_folder(d.name)
                if meta and meta["is_single_day"]:
                    candidates.append((meta, d))

        # Sort candidates descending by date
        # Deduplicate by ISO date if duplicate folders exist (.1, .2, etc.)
        candidates.sort(key=lambda x: (x[0]["date"], x[1].name == rep.name, not "." in x[1].name), reverse=True)
        seen_dates = set()
        unique_reports = []
        for meta, d in candidates:
            if meta["iso"] not in seen_dates:
                seen_dates.add(meta["iso"])
                unique_reports.append({
                    "folder": d.name,
                    "label": meta["label"],
                    "iso": meta["iso"],
                    "active": (d.name == rep.name)
                })

        # Keep strictly the last 6 single-day reports in the switcher dropdown
        if len(unique_reports) > 6:
            if not any(r["active"] for r in unique_reports[:6]):
                active_item = next((r for r in unique_reports if r["active"]), None)
                available_reports = unique_reports[:5]
                if active_item:
                    available_reports.append(active_item)
            else:
                available_reports = unique_reports[:6]
        else:
            available_reports = unique_reports

    js_mix = ",\n  ".join(
        '{n:%s, v:%s, c:"%s"}' % (json.dumps(n), v, c) for n, v, c in mix)

    peak_val = max(hourly) if hourly else 0.0
    peak_hr = hourly.index(peak_val) if peak_val > 0 else 0
    peak_info = {"hour": peak_hr, "gb": round(peak_val, 2), "formatted": f"{peak_hr:02d}:00 ({fmt_total(peak_val)})"}

    data_block = (
        "\nconst USERS = window.USERS = [\n  " + js_users() + "\n];\n\n"
        "const SITES = window.SITES = [\n  " + js_sites() + "\n];\n\n"
        f"const DAILY_DAYS = window.DAILY_DAYS = {json.dumps(daily_days)};\n\n"
        "const DAILY_USERS = window.DAILY_USERS = [\n  " + js_daily() + "\n];\n\n"
        f"const DAILY_DATES = window.DAILY_DATES = {json.dumps(dates_list)};\n"
        f"const AVAILABLE_REPORTS = window.AVAILABLE_REPORTS = {json.dumps(available_reports)};\n"
        "const MIX = window.MIX = [\n  " + js_mix + "\n];\n"
        f'const CACHE_IN = window.CACHE_IN = {in_pct:.2f}, CACHE_OUT = window.CACHE_OUT = {out_pct:.2f}, MIX_BIG = window.MIX_BIG = "{fmt_total(tot_gb)}";\n'
        f"const HOURLY = window.HOURLY = {json.dumps(hourly)};\n"
        f"const SUBNETS = window.SUBNETS = {json.dumps(subnets_list)};\n"
        f"const DOWNLOADS = window.DOWNLOADS = {json.dumps(downloads[:15])};\n"
        f"const PEAK_HOUR = window.PEAK_HOUR = {json.dumps(peak_info)};\n"
    )

    # ---- KPI-style display values -----------------------------------------
    if tot_gb >= 1024:
        bw_v, bw_d, bw_u = f"{tot_gb/1024:.2f}", "2", "T"
    elif tot_gb >= 1:
        bw_v, bw_d, bw_u = f"{tot_gb:.2f}", "2", "G"
    else:
        bw_v, bw_d, bw_u = f"{tot_gb*1024:.0f}", "0", "MB"
    if tot_conn >= 1_000_000:
        cn_v, cn_d, cn_u = f"{tot_conn/1_000_000:.2f}", "2", "M"
    elif tot_conn >= 1_000:
        cn_v, cn_d, cn_u = f"{tot_conn/1_000:.2f}", "2", "K"
    else:
        cn_v, cn_d, cn_u = str(tot_conn), "0", ""
    gent_disp = gent.replace("-", " · ", 1)

    headsub = (f"Squid proxy traffic analysis · SARG 2.4.0 · Period {period} · "
               f"{len(users)} users · {fmt_total(tot_gb)} · {fmt_conn(tot_conn)} connections")

    tfoot = ('<tr>\n        <td></td><td><b>TOTAL</b></td><td></td>'
             f'<td>{fmt_conn(tot_conn)}</td><td class="numcell">{fmt_total(tot_gb)}</td>'
             f'<td>100%</td><td>{in_pct:.2f}% / {out_pct:.2f}%</td><td></td>\n      </tr>')

    # ---- patch the dashboard ----------------------------------------------
    doc = dashp.read_text(encoding="utf-8", errors="replace")
    doc = replace_blocks(doc, "PERIOD", period)
    doc = replace_blocks(doc, "HEADSUB", headsub)
    doc = replace_blocks(doc, "DENIED", build_denied(den_site, den_clients))
    doc = replace_blocks(doc, "ALERTS", build_alerts(users, auth_ip, auth_site, auth_cli, den_site, den_clients, topsites_rows, hourly, tot_gb))
    if "AUTO:INSIGHTS" in doc:
        doc = replace_blocks(doc, "INSIGHTS", build_insights(users, mix, tot_gb, in_pct, den_site, den_clients))
    doc = replace_blocks(doc, "TFOOT", tfoot)
    doc = replace_blocks(doc, "DATA", data_block)

    def set_kpi(doc, rid, v, d, u):
        return re.sub(
            r'(id="' + rid + r'" data-count=")[^"]*(" data-dec=")[^"]*(" data-suffix=")[^"]*',
            lambda m: m.group(1) + v + m.group(2) + d + m.group(3) + u, doc)

    doc = set_kpi(doc, "kpi-bw",   bw_v, bw_d, bw_u)
    doc = set_kpi(doc, "kpi-conn", cn_v, cn_d, cn_u)
    doc = re.sub(r'(id="kpi-users" data-count=")[^"]*',  lambda m: m.group(1) + str(len(users)), doc)
    doc = re.sub(r'(id="kpi-cache" data-count=")[^"]*',  lambda m: m.group(1) + f"{in_pct:.2f}", doc)
    doc = re.sub(r'(id="kpi-denied" data-count=")[^"]*', lambda m: m.group(1) + str(denied_n), doc)
    doc = re.sub(r'(id="kpi-auth" data-count=")[^"]*',   lambda m: m.group(1) + str(auth_n), doc)

    auth_share = 0
    if auth_n:
        auth_share = round(auth_ip.most_common(1)[0][1] * 100 / auth_n)
    doc = patch_attr(doc, "foot-bw",       f"≈{tot_gb:,.2f} GB transferred in the period")
    doc = patch_attr(doc, "foot-conn",     "requests through the proxy")
    doc = patch_attr(doc, "foot-users",    "distinct client IPs in the logs")
    doc = patch_attr(doc, "foot-cache",    f"only ≈{out_gb:.2f} GB left to the internet")
    doc = patch_attr(doc, "foot-denied",   "blocked by Squid policy")
    doc = patch_attr(doc, "foot-auth",
                     f"from {len(auth_ip)} hosts · one host ≈ {auth_share}%" if auth_n
                     else "failed logins recorded")
    doc = patch_attr(doc, "badge-period",  period)
    doc = patch_attr(doc, "badge-time",    gent_disp)
    doc = patch_attr(doc, "stat-incache",  f"≈{in_gb:,.1f} GB")
    doc = patch_attr(doc, "stat-outcache", f"≈{out_gb:.2f} GB")
    doc = patch_attr(doc, "stat-total",    fmt_total(tot_gb))

    dashp.write_text(doc, encoding="utf-8")
    print(f"refresh-dashboard: rebuilt from {idx.parent.name}: "
          f"{fmt_total(tot_gb)}, {tot_conn} conns, {len(users)} users, "
          f"{in_pct:.2f}% cache, {denied_n} denied, {auth_n} auth failures")
    return 0


if __name__ == "__main__":
    sys.exit(main())

