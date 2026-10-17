#!/usr/bin/env python3
# ==============================================================================
# Innspark SARG-Style Log Analyzer & HTML Report Web Server
# Serves visual audit reports on Port 8082
# ==============================================================================

import os
import time
import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

LOG_PATH = os.getenv("ACCESS_LOG_PATH", "/shared-logs/access.log")
OUTPUT_DIR = os.getenv("SARG_OUTPUT_DIR", "/shared-sarg")
PORT = int(os.getenv("SARG_PORT", "8082"))

def generate_html_report():
    """Parses Squid access log and generates an HTML analysis dashboard."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    index_file = os.path.join(OUTPUT_DIR, "index.html")

    total_requests = 0
    total_bytes = 0
    users_traffic = {}
    domains_traffic = {}
    status_codes = {}
    recent_rows = []

    if os.path.isfile(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 8:
                    total_requests += 1
                    try:
                        size = int(parts[4])
                    except ValueError:
                        size = 0
                    total_bytes += size

                    user = parts[7] if parts[7] != "-" else "anonymous"
                    users_traffic[user] = users_traffic.get(user, 0) + size

                    url = parts[6]
                    domain = url.split("://")[-1].split("/")[0].split(":")[0]
                    domains_traffic[domain] = domains_traffic.get(domain, 0) + 1

                    status = parts[3]
                    status_codes[status] = status_codes.get(status, 0) + 1

                    try:
                        ts_str = datetime.datetime.fromtimestamp(float(parts[0])).strftime("%H:%M:%S")
                    except Exception:
                        ts_str = parts[0]

                    recent_rows.append((ts_str, parts[2], user, status, domain, size))

    top_users = sorted(users_traffic.items(), key=lambda x: x[1], reverse=True)[:10]
    top_domains = sorted(domains_traffic.items(), key=lambda x: x[1], reverse=True)[:10]
    recent_rows = recent_rows[-20:][::-1]

    # Format bytes
    if total_bytes < 1024:
        size_display = f"{total_bytes} B"
    elif total_bytes < 1024 * 1024:
        size_display = f"{total_bytes / 1024:.2f} KB"
    else:
        size_display = f"{total_bytes / (1024 * 1024):.2f} MB"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Innspark SARG Proxy Reports</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0b0f19; color: #f8fafc; padding: 24px; margin: 0; }}
        h1 {{ color: #00d2ff; font-size: 22px; margin-bottom: 4px; }}
        .subtitle {{ color: #94a3b8; font-size: 13px; margin-bottom: 24px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: #161f32; border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 18px; }}
        .card h3 {{ font-size: 11px; text-transform: uppercase; color: #94a3b8; margin: 0 0 6px 0; }}
        .card .value {{ font-size: 24px; font-weight: 800; color: #ffffff; }}
        .tables-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; }}
        th {{ background: rgba(255,255,255,0.03); color: #94a3b8; padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.08); }}
        td {{ padding: 10px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #e2e8f0; }}
        tr:hover {{ background: rgba(255,255,255,0.02); }}
        .badge {{ padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; }}
        .badge-ok {{ background: rgba(16,185,129,0.2); color: #10b981; }}
        .badge-err {{ background: rgba(244,63,94,0.2); color: #f43f5e; }}
        .badge-auth {{ background: rgba(245,158,11,0.2); color: #f59e0b; }}
    </style>
</head>
<body>
    <h1>⚡ Innspark SARG Audit Reports</h1>
    <div class="subtitle">Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} from /var/log/squid/access.log</div>

    <div class="grid">
        <div class="card">
            <h3>Total HTTP Requests</h3>
            <div class="value">{total_requests}</div>
        </div>
        <div class="card">
            <h3>Total Bandwidth</h3>
            <div class="value">{size_display}</div>
        </div>
        <div class="card">
            <h3>Unique Active Users</h3>
            <div class="value">{len(users_traffic)}</div>
        </div>
        <div class="card">
            <h3>Domains Accessed</h3>
            <div class="value">{len(domains_traffic)}</div>
        </div>
    </div>

    <div class="tables-grid">
        <div class="card">
            <h3>Top Users by Bandwidth</h3>
            <table>
                <tr><th>User (LDAP)</th><th>Bytes</th></tr>
                {''.join(f"<tr><td><strong>{u}</strong></td><td>{b:,} B</td></tr>" for u, b in top_users) if top_users else '<tr><td colspan="2">No records</td></tr>'}
            </table>
        </div>

        <div class="card">
            <h3>Top Requested Domains</h3>
            <table>
                <tr><th>Destination Domain</th><th>Hits</th></tr>
                {''.join(f"<tr><td>{d}</td><td>{c}</td></tr>" for d, c in top_domains) if top_domains else '<tr><td colspan="2">No records</td></tr>'}
            </table>
        </div>
    </div>

    <div class="card">
        <h3>Recent Proxy Audit Log</h3>
        <table>
            <tr><th>Time</th><th>Client IP</th><th>User</th><th>Status</th><th>Target Domain</th><th>Bytes</th></tr>
            {''.join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td><strong>{r[2]}</strong></td><td><span class='badge {'badge-ok' if '200' in r[3] else 'badge-auth' if '407' in r[3] else 'badge-err'}'>{r[3]}</span></td><td>{r[4]}</td><td>{r[5]}</td></tr>" for r in recent_rows) if recent_rows else '<tr><td colspan="6">No recent requests recorded</td></tr>'}
        </table>
    </div>
</body>
</html>
"""
    with open(index_file, "w", encoding="utf-8") as f:
        f.write(html_content)

def background_periodic_generator():
    """Re-analyzes logs every 5 seconds."""
    while True:
        try:
            generate_html_report()
        except Exception as e:
            print(f"[SARG] Error generating report: {e}")
        time.sleep(5)

class StaticHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)

if __name__ == "__main__":
    generate_html_report()
    t = threading.Thread(target=background_periodic_generator, daemon=True)
    t.start()
    print(f"Starting Innspark SARG Report Server on http://0.0.0.0:{PORT}...")
    server = HTTPServer(("0.0.0.0", PORT), StaticHandler)
    server.serve_forever()
