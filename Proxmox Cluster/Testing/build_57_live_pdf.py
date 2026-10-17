#!/usr/bin/env python3
"""
Build a publication-grade PDF report from the FRESH 57-step live test results
(fresh_live_test_results.json) produced by run_57_step_live_suite.py.

Reuses the proven Chrome-headless HTML->PDF pipeline.
Usage: python3 build_57_live_pdf.py [results.json]
"""

import os
import sys
import json
import subprocess
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "fresh_live_test_results.json")
HTML_OUT = os.path.join(HERE, "PROXMOX_CLUSTER_LIVE_TEST_REPORT.html")
PDF_OUT = os.path.join(HERE, "PROXMOX_CLUSTER_LIVE_TEST_REPORT.pdf")

with open(RESULTS) as f:
    steps = json.load(f)

passed = [s for s in steps if s.get("verdict") == "PASS"]
failed = [s for s in steps if s.get("verdict") == "FAIL"]
skipped = [s for s in steps if "SKIPPED" in s.get("title", "").upper() or "SKIPPED" in s.get("desc", "").upper()]

# Summary stats
def fmt_time(sec):
    if sec is None:
        return "—"
    return f"{sec}s"

rows_html = []
for s in steps:
    verdict = s.get("verdict", "PENDING")
    # If the step is a skipped one, override verdict for display
    if "SKIPPED" in s.get("title", "").upper() or "SKIPPED" in s.get("desc", "").upper():
        verdict = "SKIPPED"
    badge = "badge-pass" if verdict == "PASS" else ("badge-fail" if verdict == "FAIL" else "badge-warn")
    if verdict == "SKIPPED":
        badge = "badge-skip"
    # Build command list (fault + recovery), dedupe
    cmds = s.get("commands", [])
    cmds_html = "<br>".join([f"<code>{c}</code>" for c in cmds]) if cmds else "<i>read-only / none</i>"
    # Telemetry (verification) — show key health lines
    tel = s.get("telemetry", {})
    tel_parts = []
    for k, v in tel.items():
        if isinstance(v, str) and len(v) > 300:
            v = v[:300] + "…"
        tel_parts.append(f"<code style='font-size:10px;'>{k}</code> → <span style='font-size:10px;'>{v}</span>")
    tel_html = "<br>".join(tel_parts) if tel_parts else "<i>none</i>"
    rec_time = fmt_time(s.get("recovery_time_sec"))
    pre = s.get("pre_health", "")
    rows_html.append(f"""
      <tr>
        <td style="font-family:'JetBrains Mono'; font-weight:700;">{s.get('step','?')}</td>
        <td><strong>{s.get('title','')}</strong><br><span style="font-size:10px;color:#8b949e;">{s.get('desc','')}</span></td>
        <td style="font-size:10px; font-family:'JetBrains Mono';">{cmds_html}</td>
        <td style="font-size:10px;">{tel_html}</td>
        <td style="font-family:'JetBrains Mono'; font-size:11px;">{rec_time}</td>
        <td style="font-size:10px;color:#8b949e;">{pre}</td>
        <td><span class="{badge}">{verdict}</span></td>
      </tr>""")

summary_boxes = f"""
  <div style="display:flex; gap:14px; margin:18px 0; flex-wrap:wrap;">
    <div style="flex:1; min-width:120px; background:rgba(34,197,94,0.08); border:1px solid var(--accent-green); border-radius:10px; padding:14px; text-align:center;">
      <div style="font-size:28px; font-weight:800; color:var(--accent-green);">{len(passed)}</div>
      <div style="font-size:11px; color:var(--text-muted); letter-spacing:1px;">PASSED</div>
    </div>
    <div style="flex:1; min-width:120px; background:rgba(239,68,68,0.08); border:1px solid var(--accent-red); border-radius:10px; padding:14px; text-align:center;">
      <div style="font-size:28px; font-weight:800; color:var(--accent-red);">{len(failed)}</div>
      <div style="font-size:11px; color:var(--text-muted); letter-spacing:1px;">FAILED</div>
    </div>
    <div style="flex:1; min-width:120px; background:rgba(234,179,8,0.08); border:1px solid var(--accent-yellow); border-radius:10px; padding:14px; text-align:center;">
      <div style="font-size:28px; font-weight:800; color:var(--accent-yellow);">{len(skipped)}</div>
      <div style="font-size:11px; color:var(--text-muted); letter-spacing:1px;">SKIPPED</div>
    </div>
    <div style="flex:1; min-width:120px; background:rgba(139,148,158,0.08); border:1px solid #3d444d; border-radius:10px; padding:14px; text-align:center;">
      <div style="font-size:28px; font-weight:800; color:var(--text-body);">{len(steps)}</div>
      <div style="font-size:11px; color:var(--text-muted); letter-spacing:1px;">TOTAL</div>
    </div>
  </div>
"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Proxmox Cluster — 57-Step Live Test Report</title>
<style>
  :root {{
    --bg:#0d1117; --bg2:#161b22; --border:#30363d;
    --accent-cyan:#22d3ee; --accent-green:#22c55e; --accent-red:#ef4444; --accent-yellow:#eab308;
    --text-head:#f0f6fc; --text-body:#c9d1d9; --text-muted:#8b949e;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text-body); font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; padding:28px; }}
  .header {{ background:linear-gradient(135deg,#0d1117 0%, #161b22 60%, #1c2128 100%); border:1px solid var(--border); border-radius:14px; padding:22px 26px; margin-bottom:22px; }}
  .header h1 {{ color:var(--text-head); font-size:22px; letter-spacing:0.3px; }}
  .header .sub {{ color:var(--accent-cyan); font-size:12px; margin-top:4px; letter-spacing:1.5px; text-transform:uppercase; }}
  .header .meta {{ color:var(--text-muted); font-size:11px; margin-top:10px; line-height:1.7; }}
  .badge-pass {{ background:rgba(34,197,94,0.15); color:#4ade80; border:1px solid var(--accent-green); padding:2px 10px; border-radius:20px; font-size:10px; font-weight:700; letter-spacing:0.5px; }}
  .badge-fail {{ background:rgba(239,68,68,0.15); color:#f87171; border:1px solid var(--accent-red); padding:2px 10px; border-radius:20px; font-size:10px; font-weight:700; }}
  .badge-warn {{ background:rgba(234,179,8,0.15); color:#facc15; border:1px solid var(--accent-yellow); padding:2px 10px; border-radius:20px; font-size:10px; font-weight:700; }}
  .badge-skip {{ background:rgba(139,148,158,0.15); color:#8b949e; border:1px solid #3d444d; padding:2px 10px; border-radius:20px; font-size:10px; font-weight:700; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
  th {{ background:var(--bg2); color:var(--text-head); font-size:10px; text-transform:uppercase; letter-spacing:1px; padding:10px 8px; text-align:left; border:1px solid var(--border); }}
  td {{ padding:9px 8px; border:1px solid var(--border); font-size:11px; vertical-align:top; }}
  tr:nth-child(even) td {{ background:rgba(22,27,34,0.6); }}
  code {{ background:rgba(139,148,158,0.12); padding:1px 5px; border-radius:4px; font-family:'JetBrains Mono',Consolas,monospace; font-size:10px; color:#7ee787; word-break:break-all; }}
  .footer {{ margin-top:24px; text-align:center; color:var(--text-muted); font-size:10px; letter-spacing:1px; }}
  .section-title {{ color:var(--text-head); font-size:15px; font-weight:700; margin:18px 0 6px; }}
  .fail-note {{ background:rgba(239,68,68,0.08); border-left:3px solid var(--accent-red); padding:8px 12px; font-size:11px; margin:10px 0; }}
</style>
</head>
<body>
  <div class="header">
    <h1>Proxmox VE + Ceph + ZFS Cluster — 57-Step Live Test Report</h1>
    <div class="sub">cisai-pve &middot; prox22 / prox23 / prox24</div>
    <div class="meta">
      <b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} &nbsp;|&nbsp;
      <b>Source:</b> {os.path.basename(RESULTS)} &nbsp;|&nbsp;
      <b>Cluster:</b> 3-node, 12 OSDs, Ceph Reef, ZFS RAIDZ2 (zfs-ha) &nbsp;|&nbsp;
      <b>Method:</b> Live fault injection with auto-recovery and HEALTH_OK verification
    </div>
  </div>

  {summary_boxes}

  <div class="section-title">Fault-Injection & Resilience Test Matrix (57 steps)</div>
  <table>
    <thead>
      <tr>
        <th style="width:44px;">Step</th>
        <th style="width:200px;">Scenario</th>
        <th style="width:220px;">Commands Executed</th>
        <th>Telemetry (Verification)</th>
        <th style="width:56px;">Recovery</th>
        <th style="width:70px;">Pre-Health</th>
        <th style="width:64px;">Verdict</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows_html)}
    </tbody>
  </table>

  <div class="footer">Generated by Hermes Agent &middot; Innspark Solutions &middot; {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
</body>
</html>"""

with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Wrote {HTML_OUT}")

# Render PDF via headless Chrome (same pipeline as existing builder)
chrome = None
for cand in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
    if subprocess.run(["which", cand], capture_output=True).returncode == 0:
        chrome = cand
        break
if not chrome:
    print("No Chrome/Chromium found; HTML written but PDF skipped.")
    sys.exit(1)

subprocess.run([
    chrome, "--headless", "--disable-gpu", "--no-sandbox",
    "--run-all-compositor-stages-before-draw", "--no-pdf-header-footer",
    f"--print-to-pdf={PDF_OUT}", HTML_OUT
], check=True)
print(f"Wrote {PDF_OUT}")

# Sync to the validation report directory if present
sync_dir = "/home/nishusaini/Desktop/Innspark/Proxmox Cluster/Proxmox cluster testing /Proxmoix validation report and testing report/"
if os.path.isdir(sync_dir):
    subprocess.run(["cp", "-f", PDF_OUT, HTML_OUT, sync_dir], check=True)
    print(f"Synced to {sync_dir}")