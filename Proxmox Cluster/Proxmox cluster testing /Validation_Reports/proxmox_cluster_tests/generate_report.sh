#!/usr/bin/env bash
# =============================================================================
# generate_report.sh — Proxmox Cluster Failure Test Report Generator
# Reads all scenario_0*.json results → generates HTML report
# =============================================================================
set -uo pipefail

RESULTS_DIR="$(dirname "$0")/results"
LOG_DIR="$(dirname "$0")/logs"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
HTML_REPORT="$RESULTS_DIR/PROXMOX_CLUSTER_VALIDATION_REPORT_${TIMESTAMP}.html"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()  { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*"; }
ok()   { echo -e "${GREEN}[✔] $*${NC}"; }
warn() { echo -e "${YELLOW}[⚠] $*${NC}"; }

sec_to_min() {
    local s="$1"
    if [ "$s" = "null" ] || [ -z "$s" ] || [ "$s" = "N/A" ]; then
        echo "N/A"
    elif [[ "$s" =~ ^[0-9]+$ ]]; then
        if [ "$s" -lt 60 ]; then
            echo "${s}s"
        else
            echo "$((s/60))m $((s%60))s"
        fi
    else
        echo "$s"
    fi
}

result_badge() {
    if [ "$1" = "PASS" ]; then
        echo '<span class="badge pass">✔ PASS</span>'
    elif [ "$1" = "PARTIAL" ]; then
        echo '<span class="badge partial">⚠ PARTIAL</span>'
    else
        echo '<span class="badge fail">✘ FAIL</span>'
    fi
}

# ── Read Latest Results ───────────────────────────────────────────────────────
log "Reading result files from $RESULTS_DIR..."

S1_FILE=$(ls "$RESULTS_DIR"/scenario_01_*.json 2>/dev/null | sort | tail -1 || echo "")
S2_FILE=$(ls "$RESULTS_DIR"/scenario_02_*.json 2>/dev/null | sort | tail -1 || echo "")
S3_FILE=$(ls "$RESULTS_DIR"/scenario_03_*.json 2>/dev/null | sort | tail -1 || echo "")
BASELINE=$(ls "$RESULTS_DIR"/baseline_*.json  2>/dev/null | sort | tail -1 || echo "")

read_json() { local f="$1" k="$2"
    jq -r "$k // \"N/A\"" "$f" 2>/dev/null || echo "N/A"; }

# Scenario 1 data
S1_RESULT="N/A"; S1_TS="N/A"; S1_QUORUM="N/A"; S1_FENCE="N/A"; S1_VM="N/A"; S1_CEPH="N/A"; S1_RECOVERY="N/A"; S1_TOTAL="N/A"; S1_NODES="N/A"
if [ -n "$S1_FILE" ] && [ -f "$S1_FILE" ]; then
    S1_RESULT=$(read_json "$S1_FILE" ".result")
    S1_TS=$(read_json "$S1_FILE" ".timestamp_start")
    S1_QUORUM=$(sec_to_min "$(read_json "$S1_FILE" ".fault_phase_timings.t_quorum_lost_sec // .timings.t_quorum_lost_sec")")
    S1_FENCE=$(sec_to_min "$(read_json "$S1_FILE" ".fault_phase_timings.t_prox23_offline_sec // .timings.t_fence_triggered_sec")")
    S1_VM=$(sec_to_min "$(read_json "$S1_FILE" ".recovery_phase_timings.t_vms_restarted_sec // .timings.t_vm_restarted_sec")")
    S1_CEPH=$(sec_to_min "$(read_json "$S1_FILE" ".fault_phase_timings.t_ceph_degraded_sec // .timings.t_ceph_degraded_sec")")
    S1_RECOVERY=$(sec_to_min "$(read_json "$S1_FILE" ".recovery_phase_timings.t_ceph_healthy_sec // .timings.t_full_recovery_sec")")
    S1_TOTAL=$(sec_to_min "$(read_json "$S1_FILE" ".recovery_phase_timings.t_total_recovery_sec // .timings.t_total_test_sec")")
    S1_NODES=$(read_json "$S1_FILE" ".nodes_shutdown | join(\", \")")
fi

# Scenario 2 data
S2_RESULT="N/A"; S2_TS="N/A"; S2_UNREACH="N/A"; S2_FENCE="N/A"; S2_FAILOVER="N/A"; S2_OSD_DOWN="N/A"; S2_REJOIN="N/A"; S2_RECOVERY="N/A"; S2_TOTAL="N/A"; S2_NODE="N/A"
if [ -n "$S2_FILE" ] && [ -f "$S2_FILE" ]; then
    S2_RESULT=$(read_json "$S2_FILE" ".result")
    S2_TS=$(read_json "$S2_FILE" ".timestamp_start")
    S2_UNREACH=$(sec_to_min "$(read_json "$S2_FILE" ".fault_phase_timings.t_node_unreachable_sec // .timings.t_node_unreachable_sec")")
    S2_FENCE=$(sec_to_min "$(read_json "$S2_FILE" ".fault_phase_timings.t_ha_fencing_triggered_sec // .timings.t_fence_triggered_sec")")
    S2_FAILOVER=$(sec_to_min "$(read_json "$S2_FILE" ".fault_phase_timings.t_vm_failover_running_sec // .timings.t_vm_failover_sec")")
    S2_OSD_DOWN=$(sec_to_min "$(read_json "$S2_FILE" ".fault_phase_timings.t_ceph_osd_down_sec // .timings.t_ceph_osd_down_sec")")
    S2_REJOIN=$(sec_to_min "$(read_json "$S2_FILE" ".recovery_phase_timings.t_prox24_online_sec // .timings.t_node_rejoin_sec")")
    S2_RECOVERY=$(sec_to_min "$(read_json "$S2_FILE" ".recovery_phase_timings.t_ceph_healthy_sec // .timings.t_full_recovery_sec")")
    S2_TOTAL=$(sec_to_min "$(read_json "$S2_FILE" ".recovery_phase_timings.t_total_recovery_sec // .timings.t_total_test_sec")")
    S2_NODE=$(read_json "$S2_FILE" ".target_node // .isolated_node")
fi

# Scenario 3 data
S3_RESULT="N/A"; S3_TS="N/A"; S3_OSD1_DOWN="N/A"; S3_ALL_DOWN="N/A"; S3_PG_INACT="N/A"; S3_FAULT_DUR="N/A"
S3_OSD1_UP="N/A"; S3_ALL_UP="N/A"; S3_PG_CLEAN="N/A"; S3_RECOVERY="N/A"; S3_TOTAL="N/A"; S3_IFACE="N/A"
if [ -n "$S3_FILE" ] && [ -f "$S3_FILE" ]; then
    S3_RESULT=$(read_json "$S3_FILE" ".result")
    S3_TS=$(read_json "$S3_FILE" ".timestamp_start")
    S3_OSD1_DOWN=$(sec_to_min "$(read_json "$S3_FILE" ".fault_phase.t_first_osd_down_sec")")
    S3_ALL_DOWN=$(sec_to_min "$(read_json "$S3_FILE" ".fault_phase.t_all_osds_down_sec")")
    S3_PG_INACT=$(sec_to_min "$(read_json "$S3_FILE" ".fault_phase.t_pg_inactive_sec")")
    S3_FAULT_DUR=$(sec_to_min "$(read_json "$S3_FILE" ".fault_phase.fault_duration_sec")")
    S3_OSD1_UP=$(sec_to_min "$(read_json "$S3_FILE" ".recovery_phase.t_first_osd_up_from_restore_sec // .recovery_phase.t_first_osd_up_sec")")
    S3_ALL_UP=$(sec_to_min "$(read_json "$S3_FILE" ".recovery_phase.t_all_12_osds_up_from_restore_sec // .recovery_phase.t_all_osds_up_sec")")
    S3_PG_CLEAN=$(sec_to_min "$(read_json "$S3_FILE" ".recovery_phase.t_all_33_pgs_clean_from_restore_sec // .recovery_phase.t_pgs_clean_sec")")
    S3_RECOVERY=$(sec_to_min "$(read_json "$S3_FILE" ".recovery_phase.t_ceph_health_ok_from_restore_sec // .recovery_phase.t_recovery_from_restore_sec // .recovery_phase.t_full_recovery_sec")")
    S3_TOTAL=$(sec_to_min "$(read_json "$S3_FILE" ".recovery_phase.t_total_test_duration_sec // .t_total_test_sec")")
    S3_IFACE=$(read_json "$S3_FILE" ".ceph_interface")
fi

CLUSTER_IP="10.31.6.172"
REPORT_DATE=$(date '+%d %B %Y, %H:%M:%S IST')

# ── Generate HTML ─────────────────────────────────────────────────────────────
log "Generating HTML report → $HTML_REPORT"

cat > "$HTML_REPORT" << HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Proxmox Cluster Failure & Recovery Validation Report</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

  :root {
    --bg-primary:    #0a0e1a;
    --bg-secondary:  #0d1220;
    --bg-card:       #111827;
    --bg-card2:      #0f1621;
    --border:        #1e2d45;
    --border-glow:   #1a3a6e;
    --accent-blue:   #3b82f6;
    --accent-cyan:   #06b6d4;
    --accent-green:  #10b981;
    --accent-yellow: #f59e0b;
    --accent-red:    #ef4444;
    --accent-purple: #8b5cf6;
    --text-primary:  #f0f4ff;
    --text-secondary:#94a3b8;
    --text-muted:    #4b5e7e;
    --pass-color:    #10b981;
    --warn-color:    #f59e0b;
    --fail-color:    #ef4444;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Inter', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    background-image:
      radial-gradient(ellipse 80% 40% at 50% -10%, rgba(59,130,246,0.12) 0%, transparent 60%),
      radial-gradient(ellipse 50% 30% at 80% 100%, rgba(6,182,212,0.08) 0%, transparent 60%);
  }

  /* ── Header ─────────────────────────────────────────────────────────────── */
  .report-header {
    background: linear-gradient(135deg, #0d1b3e 0%, #071020 50%, #0a1628 100%);
    border-bottom: 1px solid var(--border-glow);
    padding: 40px 60px 36px;
    position: relative;
    overflow: hidden;
  }
  .report-header::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(90deg, transparent, rgba(59,130,246,0.04), transparent);
    animation: shimmer 4s infinite;
  }
  @keyframes shimmer { 0%,100%{opacity:0} 50%{opacity:1} }

  .header-top {
    display: flex; justify-content: space-between; align-items: flex-start;
    flex-wrap: wrap; gap: 20px; position: relative; z-index: 1;
  }
  .header-logo {
    display: flex; align-items: center; gap: 14px;
  }
  .logo-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #3b82f6, #06b6d4);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 26px; box-shadow: 0 0 24px rgba(59,130,246,0.4);
  }
  .logo-text h1 { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
  .logo-text p  { font-size: 12px; color: var(--text-secondary); margin-top: 2px; }
  .header-meta { text-align: right; }
  .cluster-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.3);
    border-radius: 8px; padding: 6px 12px;
    font-size: 13px; font-family: 'JetBrains Mono', monospace;
    color: var(--accent-cyan);
  }
  .dot-live {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--accent-green);
    box-shadow: 0 0 8px var(--accent-green);
    animation: pulse-dot 2s infinite;
  }
  @keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(1.3)} }

  .report-title-section { margin-top: 28px; position: relative; z-index: 1; }
  .report-title-section h2 {
    font-size: 36px; font-weight: 800; letter-spacing: -1px;
    background: linear-gradient(135deg, #f0f4ff, #94c3f7);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .report-subtitle {
    font-size: 14px; color: var(--text-secondary); margin-top: 8px;
  }
  .report-meta-row {
    display: flex; gap: 32px; margin-top: 20px; flex-wrap: wrap;
  }
  .meta-item { display: flex; flex-direction: column; gap: 3px; }
  .meta-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
  .meta-value { font-size: 14px; font-weight: 600; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }

  /* ── Content ─────────────────────────────────────────────────────────────── */
  .content { max-width: 1200px; margin: 0 auto; padding: 40px 40px 60px; }

  /* ── Summary Cards ───────────────────────────────────────────────────────── */
  .summary-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;
    margin-bottom: 40px;
  }
  .summary-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px; padding: 24px 28px;
    position: relative; overflow: hidden;
    transition: transform 0.2s, border-color 0.2s;
  }
  .summary-card:hover { transform: translateY(-2px); border-color: var(--border-glow); }
  .summary-card::after {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    border-radius: 16px 16px 0 0;
  }
  .card-s1::after { background: linear-gradient(90deg, #ef4444, #f97316); }
  .card-s2::after { background: linear-gradient(90deg, #f59e0b, #eab308); }
  .card-s3::after { background: linear-gradient(90deg, #8b5cf6, #6366f1); }

  .card-icon { font-size: 32px; margin-bottom: 12px; }
  .card-title { font-size: 13px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
  .card-scenario { font-size: 16px; font-weight: 700; margin: 6px 0; }
  .card-result  { margin-top: 14px; }

  /* ── Badges ──────────────────────────────────────────────────────────────── */
  .badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 14px; border-radius: 20px;
    font-size: 13px; font-weight: 700; letter-spacing: 0.5px;
  }
  .badge.pass    { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
  .badge.partial { background: rgba(245,158,11,0.15); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }
  .badge.fail    { background: rgba(239,68,68,0.15);  color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
  .badge.info    { background: rgba(59,130,246,0.15); color: #3b82f6; border: 1px solid rgba(59,130,246,0.3); }

  /* ── Section Titles ──────────────────────────────────────────────────────── */
  .section-title {
    font-size: 20px; font-weight: 700;
    display: flex; align-items: center; gap: 10px;
    margin: 40px 0 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }
  .section-icon {
    width: 36px; height: 36px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
  }
  .icon-red    { background: rgba(239,68,68,0.15); }
  .icon-yellow { background: rgba(245,158,11,0.15); }
  .icon-purple { background: rgba(139,92,246,0.15); }
  .icon-blue   { background: rgba(59,130,246,0.15); }

  /* ── Timeline Tables ─────────────────────────────────────────────────────── */
  .scenario-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 30px;
  }
  .scenario-header {
    padding: 20px 28px;
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid var(--border);
  }
  .scenario-header-left h3 { font-size: 17px; font-weight: 700; }
  .scenario-header-left p  { font-size: 13px; color: var(--text-secondary); margin-top: 3px; }

  .timeline-table { width: 100%; border-collapse: collapse; }
  .timeline-table th {
    background: rgba(30,45,69,0.5);
    padding: 12px 20px; font-size: 12px;
    color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;
    font-weight: 600; text-align: left;
  }
  .timeline-table td {
    padding: 14px 20px; border-bottom: 1px solid rgba(30,45,69,0.5);
    font-size: 14px;
  }
  .timeline-table tr:last-child td { border-bottom: none; }
  .timeline-table tr:hover td { background: rgba(59,130,246,0.03); }

  .event-label {
    display: flex; align-items: center; gap: 8px; font-weight: 500;
  }
  .event-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  }
  .dot-red    { background: #ef4444; box-shadow: 0 0 6px #ef4444; }
  .dot-yellow { background: #f59e0b; box-shadow: 0 0 6px #f59e0b; }
  .dot-green  { background: #10b981; box-shadow: 0 0 6px #10b981; }
  .dot-blue   { background: #3b82f6; box-shadow: 0 0 6px #3b82f6; }
  .dot-purple { background: #8b5cf6; box-shadow: 0 0 6px #8b5cf6; }
  .dot-cyan   { background: #06b6d4; box-shadow: 0 0 6px #06b6d4; }

  .time-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 15px; font-weight: 600;
    color: var(--accent-cyan);
  }
  .time-na { color: var(--text-muted); font-style: italic; }

  /* ── Observations ────────────────────────────────────────────────────────── */
  .obs-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
    padding: 20px 28px; border-top: 1px solid var(--border);
  }
  .obs-item {
    background: rgba(30,45,69,0.3); border-radius: 10px;
    padding: 14px 16px;
  }
  .obs-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
  .obs-value { font-size: 14px; font-weight: 600; margin-top: 4px; color: var(--accent-cyan); font-family: 'JetBrains Mono', monospace; }

  /* ── Expectations vs Actual ──────────────────────────────────────────────── */
  .eval-table { width: 100%; border-collapse: collapse; }
  .eval-table th {
    padding: 12px 20px; font-size: 12px;
    color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px;
    font-weight: 600; text-align: left;
    background: rgba(30,45,69,0.5); border-bottom: 1px solid var(--border);
  }
  .eval-table td {
    padding: 14px 20px; border-bottom: 1px solid rgba(30,45,69,0.4);
    font-size: 14px;
  }
  .eval-table tr:last-child td { border-bottom: none; }

  /* ── Footer ──────────────────────────────────────────────────────────────── */
  .report-footer {
    text-align: center; padding: 40px;
    color: var(--text-muted); font-size: 12px;
    border-top: 1px solid var(--border);
  }
  .report-footer a { color: var(--accent-blue); text-decoration: none; }

  /* ── Responsive ──────────────────────────────────────────────────────────── */
  @media (max-width: 768px) {
    .summary-grid { grid-template-columns: 1fr; }
    .obs-grid { grid-template-columns: 1fr; }
    .report-header { padding: 24px; }
    .content { padding: 20px; }
    .report-title-section h2 { font-size: 24px; }
  }

  @media print {
    body { background: #fff; color: #000; }
    .report-header { background: #f0f4ff; }
    .scenario-card, .summary-card { border-color: #ccc; }
  }
</style>
</head>
<body>

<!-- ─── HEADER ──────────────────────────────────────────────────────────── -->
<div class="report-header">
  <div class="header-top">
    <div class="header-logo">
      <div class="logo-icon">🖥️</div>
      <div class="logo-text">
        <h1>Proxmox Cluster Validation</h1>
        <p>Failure Scenario Testing &amp; Recovery Analysis</p>
      </div>
    </div>
    <div class="header-meta">
      <div class="cluster-badge">
        <span class="dot-live"></span>
        Cluster: $CLUSTER_IP
      </div>
      <div style="font-size:12px; color:var(--text-muted); margin-top:8px; text-align:right;">
        Generated: $REPORT_DATE
      </div>
    </div>
  </div>

  <div class="report-title-section">
    <h2>Cluster Resilience &amp; Recovery Validation Report</h2>
    <p class="report-subtitle">
      Comprehensive failure injection testing — 3-Node Proxmox Cluster with Ceph Storage
    </p>
    <div class="report-meta-row">
      <div class="meta-item">
        <span class="meta-label">Cluster IP</span>
        <span class="meta-value">$CLUSTER_IP</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Cluster Nodes</span>
        <span class="meta-value">3 Nodes</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Ceph Interface</span>
        <span class="meta-value">nic3</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Scenarios Tested</span>
        <span class="meta-value">3 / 3</span>
      </div>
      <div class="meta-item">
        <span class="meta-label">Test Date</span>
        <span class="meta-value">$(date '+%Y-%m-%d')</span>
      </div>
    </div>
  </div>
</div>

<!-- ─── CONTENT ─────────────────────────────────────────────────────────── -->
<div class="content">

  <!-- Summary Cards -->
  <div class="summary-grid">
    <div class="summary-card card-s1">
      <div class="card-icon">🔌</div>
      <div class="card-title">Scenario 1</div>
      <div class="card-scenario">Dual Node Hardware Shutdown</div>
      <p style="font-size:13px; color:var(--text-secondary);">2 of 3 nodes powered off simultaneously</p>
      <div class="card-result">$(result_badge "$S1_RESULT")</div>
      <div style="margin-top:12px; font-size:13px; color:var(--text-secondary);">
        Full Recovery: <span style="color:var(--accent-cyan); font-family:'JetBrains Mono',monospace; font-weight:600;">$S1_RECOVERY</span>
      </div>
    </div>

    <div class="summary-card card-s2">
      <div class="card-icon">🌐</div>
      <div class="card-title">Scenario 2</div>
      <div class="card-scenario">Single Node Network Isolation</div>
      <p style="font-size:13px; color:var(--text-secondary);">Node $S2_NODE network completely blocked</p>
      <div class="card-result">$(result_badge "$S2_RESULT")</div>
      <div style="margin-top:12px; font-size:13px; color:var(--text-secondary);">
        VM Failover: <span style="color:var(--accent-cyan); font-family:'JetBrains Mono',monospace; font-weight:600;">$S2_FAILOVER</span>
      </div>
    </div>

    <div class="summary-card card-s3">
      <div class="card-icon">💾</div>
      <div class="card-title">Scenario 3</div>
      <div class="card-scenario">Full Ceph Network Outage</div>
      <p style="font-size:13px; color:var(--text-secondary);">$S3_IFACE interface down on all 3 nodes</p>
      <div class="card-result">$(result_badge "$S3_RESULT")</div>
      <div style="margin-top:12px; font-size:13px; color:var(--text-secondary);">
        Ceph Recovery: <span style="color:var(--accent-cyan); font-family:'JetBrains Mono',monospace; font-weight:600;">$S3_RECOVERY</span>
      </div>
    </div>
  </div>

  <!-- ═══ SCENARIO 1 ════════════════════════════════════════════════════════ -->
  <div class="section-title">
    <div class="section-icon icon-red">🔌</div>
    Scenario 1 — Dual Node Hardware Shutdown
  </div>

  <div class="scenario-card">
    <div class="scenario-header">
      <div class="scenario-header-left">
        <h3>2-Node Simultaneous Poweroff</h3>
        <p>Nodes: $S1_NODES &nbsp;|&nbsp; Started: $S1_TS</p>
      </div>
      $(result_badge "$S1_RESULT")
    </div>
    <table class="timeline-table">
      <thead>
        <tr>
          <th>Event</th>
          <th>Time from Fault (T0)</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-red"></span> T0 — Fault Injected</div></td>
          <td><span class="time-value">0s</span></td>
          <td>SSH poweroff issued to both nodes simultaneously</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-yellow"></span> Quorum Lost</div></td>
          <td><span class="time-value $([ "$S1_QUORUM" = "N/A" ] && echo time-na)">$S1_QUORUM</span></td>
          <td>Cluster quorum fell below 50% threshold</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-yellow"></span> HA Fence Triggered</div></td>
          <td><span class="time-value $([ "$S1_FENCE" = "N/A" ] && echo time-na)">$S1_FENCE</span></td>
          <td>HA Manager initiated fencing on lost nodes</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-red"></span> Ceph Degraded</div></td>
          <td><span class="time-value $([ "$S1_CEPH" = "N/A" ] && echo time-na)">$S1_CEPH</span></td>
          <td>Ceph OSDs on shutdown nodes evicted; PGs degraded</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-green"></span> VMs Restarted</div></td>
          <td><span class="time-value $([ "$S1_VM" = "N/A" ] && echo time-na)">$S1_VM</span></td>
          <td>VMs from failed nodes restarted on surviving node</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-green"></span> Full Cluster Recovery</div></td>
          <td><span class="time-value $([ "$S1_RECOVERY" = "N/A" ] && echo time-na)">$S1_RECOVERY</span></td>
          <td>All nodes online, Ceph healthy, VMs running</td>
        </tr>
      </tbody>
    </table>
    <div class="obs-grid">
      <div class="obs-item">
        <div class="obs-label">Total Test Duration</div>
        <div class="obs-value">$S1_TOTAL</div>
      </div>
      <div class="obs-item">
        <div class="obs-label">Nodes Affected</div>
        <div class="obs-value">$S1_NODES</div>
      </div>
      <div class="obs-item">
        <div class="obs-label">Expected HA Recovery Target</div>
        <div class="obs-value">&lt; 5 minutes</div>
      </div>
      <div class="obs-item">
        <div class="obs-label">Observed Result</div>
        <div class="obs-value">$S1_RESULT</div>
      </div>
    </div>
  </div>

  <!-- ═══ SCENARIO 2 ════════════════════════════════════════════════════════ -->
  <div class="section-title">
    <div class="section-icon icon-yellow">🌐</div>
    Scenario 2 — Single Node Network Isolation
  </div>

  <div class="scenario-card">
    <div class="scenario-header">
      <div class="scenario-header-left">
        <h3>Node Network Blackhole (iptables DROP)</h3>
        <p>Isolated Node: $S2_NODE &nbsp;|&nbsp; Started: $S2_TS</p>
      </div>
      $(result_badge "$S2_RESULT")
    </div>
    <table class="timeline-table">
      <thead>
        <tr><th>Event</th><th>Time from Fault (T0)</th><th>Description</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-red"></span> T0 — Network Isolated</div></td>
          <td><span class="time-value">0s</span></td>
          <td>iptables DROP rules applied on $S2_NODE — all traffic blocked</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-yellow"></span> Node Unreachable</div></td>
          <td><span class="time-value $([ "$S2_UNREACH" = "N/A" ] && echo time-na)">$S2_UNREACH</span></td>
          <td>Ping to $S2_NODE confirmed unreachable</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-yellow"></span> HA Fence Triggered</div></td>
          <td><span class="time-value $([ "$S2_FENCE" = "N/A" ] && echo time-na)">$S2_FENCE</span></td>
          <td>HA Manager fenced $S2_NODE due to missed heartbeats</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-red"></span> Ceph OSD Down</div></td>
          <td><span class="time-value $([ "$S2_OSD_DOWN" = "N/A" ] && echo time-na)">$S2_OSD_DOWN</span></td>
          <td>Ceph OSDs on $S2_NODE marked down by monitors</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-green"></span> VM Failover Complete</div></td>
          <td><span class="time-value $([ "$S2_FAILOVER" = "N/A" ] && echo time-na)">$S2_FAILOVER</span></td>
          <td>VMs from $S2_NODE restarted on surviving nodes</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-cyan"></span> Node Rejoined</div></td>
          <td><span class="time-value $([ "$S2_REJOIN" = "N/A" ] && echo time-na)">$S2_REJOIN</span></td>
          <td>Network restored; $S2_NODE rejoined cluster</td>
        </tr>
        <tr>
          <td><div class="event-label"><span class="event-dot dot-green"></span> Full Recovery</div></td>
          <td><span class="time-value $([ "$S2_RECOVERY" = "N/A" ] && echo time-na)">$S2_RECOVERY</span></td>
          <td>Cluster quorum full, Ceph healthy, all VMs running</td>
        </tr>
      </tbody>
    </table>
    <div class="obs-grid">
      <div class="obs-item"><div class="obs-label">Total Duration</div><div class="obs-value">$S2_TOTAL</div></div>
      <div class="obs-item"><div class="obs-label">Isolated Node</div><div class="obs-value">$S2_NODE</div></div>
      <div class="obs-item"><div class="obs-label">HA Recovery Target</div><div class="obs-value">&lt; 3 minutes</div></div>
      <div class="obs-item"><div class="obs-label">Result</div><div class="obs-value">$S2_RESULT</div></div>
    </div>
  </div>

  <!-- ═══ SCENARIO 3 ════════════════════════════════════════════════════════ -->
  <div class="section-title">
    <div class="section-icon icon-purple">💾</div>
    Scenario 3 — Full Ceph Network Outage
  </div>

  <div class="scenario-card">
    <div class="scenario-header">
      <div class="scenario-header-left">
        <h3>Ceph Interface ($S3_IFACE) Down on All 3 Nodes</h3>
        <p>Started: $S3_TS</p>
      </div>
      $(result_badge "$S3_RESULT")
    </div>
    <table class="timeline-table">
      <thead>
        <tr><th>Phase</th><th>Event</th><th>Time (T0)</th><th>Description</th></tr>
      </thead>
      <tbody>
        <tr style="background:rgba(239,68,68,0.04);">
          <td rowspan="4" style="vertical-align:top; font-weight:600; color:var(--accent-red);">FAULT PHASE</td>
          <td><div class="event-label"><span class="event-dot dot-red"></span> $S3_IFACE Down</div></td>
          <td><span class="time-value">0s</span></td>
          <td>Ceph network interface disabled on all 3 nodes simultaneously</td>
        </tr>
        <tr style="background:rgba(239,68,68,0.04);">
          <td><div class="event-label"><span class="event-dot dot-yellow"></span> First OSD Down</div></td>
          <td><span class="time-value $([ "$S3_OSD1_DOWN" = "N/A" ] && echo time-na)">$S3_OSD1_DOWN</span></td>
          <td>First OSD evicted by Ceph monitors</td>
        </tr>
        <tr style="background:rgba(239,68,68,0.04);">
          <td><div class="event-label"><span class="event-dot dot-red"></span> All OSDs Down</div></td>
          <td><span class="time-value $([ "$S3_ALL_DOWN" = "N/A" ] && echo time-na)">$S3_ALL_DOWN</span></td>
          <td>All OSDs marked down — Ceph I/O completely frozen</td>
        </tr>
        <tr style="background:rgba(239,68,68,0.04);">
          <td><div class="event-label"><span class="event-dot dot-red"></span> PGs Inactive</div></td>
          <td><span class="time-value $([ "$S3_PG_INACT" = "N/A" ] && echo time-na)">$S3_PG_INACT</span></td>
          <td>Placement groups became inactive/unreadable</td>
        </tr>
        <tr style="background:rgba(16,185,129,0.04);">
          <td rowspan="4" style="vertical-align:top; font-weight:600; color:var(--accent-green);">RECOVERY PHASE</td>
          <td><div class="event-label"><span class="event-dot dot-cyan"></span> $S3_IFACE Restored</div></td>
          <td><span class="time-value">$S3_FAULT_DUR</span></td>
          <td>Ceph network interface brought back UP on all nodes</td>
        </tr>
        <tr style="background:rgba(16,185,129,0.04);">
          <td><div class="event-label"><span class="event-dot dot-green"></span> First OSD Up</div></td>
          <td><span class="time-value $([ "$S3_OSD1_UP" = "N/A" ] && echo time-na)">$S3_OSD1_UP</span></td>
          <td>First OSD re-established connection to monitors</td>
        </tr>
        <tr style="background:rgba(16,185,129,0.04);">
          <td><div class="event-label"><span class="event-dot dot-green"></span> All OSDs Up</div></td>
          <td><span class="time-value $([ "$S3_ALL_UP" = "N/A" ] && echo time-na)">$S3_ALL_UP</span></td>
          <td>All OSDs back in cluster</td>
        </tr>
        <tr style="background:rgba(16,185,129,0.04);">
          <td><div class="event-label"><span class="event-dot dot-green"></span> All PGs Clean</div></td>
          <td><span class="time-value $([ "$S3_PG_CLEAN" = "N/A" ] && echo time-na)">$S3_PG_CLEAN</span></td>
          <td>All PGs active+clean — Ceph HEALTH_OK</td>
        </tr>
      </tbody>
    </table>
    <div class="obs-grid">
      <div class="obs-item"><div class="obs-label">Fault Window Duration</div><div class="obs-value">$S3_FAULT_DUR</div></div>
      <div class="obs-item"><div class="obs-label">Full Ceph Recovery</div><div class="obs-value">$S3_RECOVERY</div></div>
      <div class="obs-item"><div class="obs-label">Recovery Target</div><div class="obs-value">&lt; 10 minutes</div></div>
      <div class="obs-item"><div class="obs-label">Result</div><div class="obs-value">$S3_RESULT</div></div>
    </div>
  </div>

  <!-- ═══ SUMMARY TABLE ═════════════════════════════════════════════════════ -->
  <div class="section-title">
    <div class="section-icon icon-blue">📊</div>
    Overall Recovery SLA Evaluation
  </div>

  <div class="scenario-card">
    <table class="eval-table">
      <thead>
        <tr>
          <th>Scenario</th>
          <th>Key Metric</th>
          <th>Target SLA</th>
          <th>Measured</th>
          <th>Verdict</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>1. Dual Node Shutdown</strong></td>
          <td>Quorum Lost</td>
          <td>Detected &lt; 60s</td>
          <td class="time-value">$S1_QUORUM</td>
          <td>$(result_badge "$S1_RESULT")</td>
        </tr>
        <tr>
          <td></td>
          <td>HA Fence</td>
          <td>&lt; 2 min</td>
          <td class="time-value">$S1_FENCE</td>
          <td>—</td>
        </tr>
        <tr>
          <td></td>
          <td>VM Restart</td>
          <td>&lt; 5 min</td>
          <td class="time-value">$S1_VM</td>
          <td>—</td>
        </tr>
        <tr>
          <td><strong>2. Node Network Down</strong></td>
          <td>HA Fence Trigger</td>
          <td>&lt; 90s</td>
          <td class="time-value">$S2_FENCE</td>
          <td>$(result_badge "$S2_RESULT")</td>
        </tr>
        <tr>
          <td></td>
          <td>VM Failover</td>
          <td>&lt; 3 min</td>
          <td class="time-value">$S2_FAILOVER</td>
          <td>—</td>
        </tr>
        <tr>
          <td></td>
          <td>Node Re-Join</td>
          <td>&lt; 5 min after restore</td>
          <td class="time-value">$S2_REJOIN</td>
          <td>—</td>
        </tr>
        <tr>
          <td><strong>3. Ceph Network Outage</strong></td>
          <td>First OSD Down</td>
          <td>Detected &lt; 60s</td>
          <td class="time-value">$S3_OSD1_DOWN</td>
          <td>$(result_badge "$S3_RESULT")</td>
        </tr>
        <tr>
          <td></td>
          <td>All OSDs Recovered</td>
          <td>&lt; 5 min after restore</td>
          <td class="time-value">$S3_ALL_UP</td>
          <td>—</td>
        </tr>
        <tr>
          <td></td>
          <td>Ceph HEALTH_OK</td>
          <td>&lt; 10 min from restore</td>
          <td class="time-value">$S3_RECOVERY</td>
          <td>—</td>
        </tr>
      </tbody>
    </table>
  </div>

</div><!-- /content -->

<!-- ─── FOOTER ───────────────────────────────────────────────────────────── -->
<div class="report-footer">
  <p>Proxmox Cluster Failure &amp; Recovery Validation Report &nbsp;|&nbsp; Cluster: $CLUSTER_IP &nbsp;|&nbsp; Generated: $REPORT_DATE</p>
  <p style="margin-top:6px;">Tested by InnoSpark Infrastructure Team &nbsp;|&nbsp; All times measured from T0 (fault injection point)</p>
</div>

</body>
</html>
HTMLEOF

ok "HTML Report generated: $HTML_REPORT"
echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║  Report ready: ${NC}$HTML_REPORT"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Open with:  xdg-open \"$HTML_REPORT\"${NC}"
echo ""
