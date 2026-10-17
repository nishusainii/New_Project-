#!/usr/bin/env python3
"""
Generate a clean, focused, professional PDF guide covering:
1. What Pulse Monitoring Tool does (capabilities, architecture, what it monitors).
2. Complete step-by-step installation and initial setup runbook.
3. Host and Proxmox VE / PBS integration.
"""

import os
import subprocess

OUTPUT_DIR = "/home/nishusaini/Desktop/Innspark/Pulse monitoring tools"
HTML_FILE = os.path.join(OUTPUT_DIR, "Pulse_Monitoring_Tool_Installation_and_Overview_Guide.html")
PDF_FILE = os.path.join(OUTPUT_DIR, "Pulse_Monitoring_Tool_Installation_and_Overview_Guide.pdf")

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Pulse Monitoring Tool: System Overview & Complete Installation Guide</title>
<style>
  @page {
    size: A4 portrait;
    margin: 12mm 14mm 12mm 14mm;
  }

  * {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.45;
    font-size: 9pt;
    margin: 0;
    padding: 0;
  }

  .page {
    position: relative;
    page-break-after: always;
    break-after: page;
    min-height: 270mm;
    max-height: 270mm;
    height: 270mm;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .page-last {
    page-break-after: avoid;
    break-after: avoid;
  }

  .page-content {
    flex: 1 1 auto;
  }

  /* Header & Footer */
  .doc-header {
    border-bottom: 2px solid #0284c7;
    padding-bottom: 5px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 7.5pt;
    font-weight: 700;
    color: #0369a1;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .doc-header span.org {
    color: #0f172a;
    font-weight: 800;
  }

  .doc-footer {
    border-top: 1px solid #e2e8f0;
    padding-top: 5px;
    margin-top: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 7.5pt;
    color: #64748b;
  }

  .doc-footer .confidential {
    color: #dc2626;
    font-weight: 700;
  }

  /* Typography */
  h1, h2, h3, h4 {
    color: #0f172a;
    margin-top: 0;
    font-weight: 700;
    letter-spacing: -0.2px;
  }

  h1.sec-title {
    font-size: 14pt;
    border-left: 4px solid #0284c7;
    padding-left: 8px;
    margin-bottom: 8px;
    color: #0f172a;
  }

  h2.sub-title {
    font-size: 10.5pt;
    margin-top: 8px;
    margin-bottom: 5px;
    color: #0369a1;
    display: flex;
    align-items: center;
    gap: 5px;
  }

  h3 {
    font-size: 9pt;
    margin-top: 6px;
    margin-bottom: 3px;
    color: #1e293b;
  }

  p {
    margin-top: 0;
    margin-bottom: 5px;
    color: #334155;
    text-align: justify;
  }

  /* Cover Banner */
  .cover-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-radius: 6px;
    padding: 16px 20px;
    color: #ffffff;
    margin-bottom: 12px;
    border-left: 5px solid #0284c7;
  }

  .cover-badge {
    display: inline-block;
    background: #0284c7;
    color: #ffffff;
    font-size: 7.5pt;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 8px;
  }

  .cover-title {
    font-size: 20pt;
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: 6px;
    color: #f8fafc;
  }

  .cover-desc {
    font-size: 9pt;
    color: #cbd5e1;
    line-height: 1.4;
  }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 7pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }
  .badge-success { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
  .badge-warning { background: #fef3c7; color: #b45309; border: 1px solid #fcd34d; }
  .badge-danger { background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
  .badge-info { background: #e0f2fe; color: #0369a1; border: 1px solid #7dd3fc; }
  .badge-neutral { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }

  /* Callouts */
  .callout {
    border-radius: 5px;
    padding: 6px 10px;
    margin: 5px 0;
    font-size: 8.5pt;
    line-height: 1.35;
    border-left: 3.5px solid;
  }
  .callout-info { background: #f0f9ff; border-color: #0284c7; color: #0c4a6e; }
  .callout-warning { background: #fffbeb; border-color: #d97706; color: #78350f; }
  .callout-danger { background: #fef2f2; border-color: #dc2626; color: #7f1d1d; }
  .callout-success { background: #f0fdf4; border-color: #16a34a; color: #14532d; }

  .callout-title {
    font-weight: 700;
    font-size: 8.5pt;
    margin-bottom: 2px;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  /* Tables */
  table.data-table {
    width: 100%;
    border-collapse: collapse;
    margin: 5px 0;
    font-size: 8pt;
  }
  table.data-table th {
    background: #0f172a;
    color: #ffffff;
    text-align: left;
    padding: 4px 6px;
    font-weight: 600;
    font-size: 7.5pt;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    border: 1px solid #0f172a;
  }
  table.data-table td {
    padding: 3.5px 6px;
    border: 1px solid #cbd5e1;
    color: #1e293b;
    vertical-align: top;
  }
  table.data-table tr:nth-child(even) td {
    background-color: #f8fafc;
  }

  /* Code Blocks */
  .code-block {
    background: #0f172a;
    color: #e2e8f0;
    border-radius: 4px;
    padding: 6px 9px;
    font-family: "Fira Code", "Courier New", Courier, monospace;
    font-size: 7.5pt;
    line-height: 1.35;
    margin: 4px 0;
    overflow-x: hidden;
    border: 1px solid #1e293b;
  }
  .code-block .comment { color: #94a3b8; font-style: italic; }
  .code-block .cmd { color: #38bdf8; font-weight: 600; }
  .code-block .param { color: #fde047; }
  .code-block .success { color: #4ade80; }

  .inline-code {
    background: #f1f5f9;
    color: #0f172a;
    font-family: "Fira Code", monospace;
    font-size: 7.8pt;
    padding: 1px 4px;
    border-radius: 3px;
    border: 1px solid #cbd5e1;
  }

  /* Grids & Cards */
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin: 5px 0;
  }

  .grid-3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin: 5px 0;
  }

  .card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    padding: 6px 8px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
  }

  /* Flow Diagram */
  .flow-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 6px 8px;
    margin: 5px 0;
  }
  .flow-step {
    background: #ffffff;
    border: 1px solid #94a3b8;
    border-radius: 4px;
    padding: 3px 6px;
    text-align: center;
    font-size: 7.5pt;
    font-weight: 600;
    color: #0f172a;
    flex: 1;
    margin: 0 2px;
  }
  .flow-arrow {
    color: #0284c7;
    font-size: 9pt;
    font-weight: 800;
  }

  ul.compact-list {
    margin: 2px 0 4px 0;
    padding-left: 14px;
    font-size: 8pt;
  }
  ul.compact-list li {
    margin-bottom: 2px;
    color: #334155;
  }

  /* Steps Styling */
  .step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    background: #0284c7;
    color: #ffffff;
    border-radius: 50%;
    font-size: 7.5pt;
    font-weight: 700;
    margin-right: 5px;
  }
</style>
</head>
<body>

<!-- ==================== PAGE 1: WHAT PULSE DOES & CAPABILITIES ==================== -->
<div class="page">
  <div>
    <div class="doc-header">
      <span><span class="org">INNSPARK</span> | Infrastructure Operations</span>
      <span>Pulse Monitoring Tool: System Overview & Capabilities</span>
    </div>

    <div class="page-content">
      <div class="cover-banner">
        <div class="cover-badge">Official Deployment Guide</div>
        <div class="cover-title">Pulse Monitoring Tool</div>
        <div class="cover-desc">
          A modern, consolidated infrastructure observability platform engineered specifically for virtualized, containerized, and physical compute environments. Consolidates Proxmox VE clusters, Ceph, ZFS, and Proxmox Backup Server into a unified dashboard.
        </div>
      </div>

      <h1 class="sec-title">1. What Pulse Monitoring Tool Does</h1>
      <p>
        Pulse provides unified, real-time infrastructure visibility without the operational overhead of heavy, complex enterprise agents. It acts as a central aggregator that consolidates virtual machine metrics, storage arrays, backup verification, and physical hardware health into one intuitive pane of glass.
      </p>

      <h2 class="sub-title">1.1 Core Telemetry & Consolidated Dashboard Scope</h2>
      <div class="grid-3">
        <div class="card" style="border-top: 3.5px solid #0284c7;">
          <strong style="color: #0284c7; font-size: 8pt;">Hypervisors & Guests</strong>
          <ul class="compact-list" style="margin-top: 3px;">
            <li>Proxmox clusters & individual nodes</li>
            <li>Virtual Machine (VM) and LXC status</li>
            <li>Real-time CPU, RAM, disk, & network use</li>
            <li>Allocated vs. consumed resource analysis</li>
            <li>Node, guest, & capacity alerts</li>
          </ul>
        </div>
        <div class="card" style="border-top: 3.5px solid #059669;">
          <strong style="color: #059669; font-size: 8pt;">Storage & Backups</strong>
          <ul class="compact-list" style="margin-top: 3px;">
            <li>Proxmox storage pool utilization</li>
            <li>Ceph cluster health & OSD status</li>
            <li>ZFS pools, datasets, snapshots, & replication</li>
            <li>PBS datastores, backup jobs, & verifications</li>
            <li>Replication and backup failure tracking</li>
          </ul>
        </div>
        <div class="card" style="border-top: 3.5px solid #d97706;">
          <strong style="color: #d97706; font-size: 8pt;">Physical Hardware</strong>
          <ul class="compact-list" style="margin-top: 3px;">
            <li>Drive SMART health & wear-out levels</li>
            <li>CPU & system temperature diodes</li>
            <li>Linux software RAID (<span class="inline-code">mdadm</span>) state</li>
            <li>Hardware RAID controller diagnostics</li>
            <li>Long-term metric trends & historical forecasting</li>
          </ul>
        </div>
      </div>

      <h2 class="sub-title">1.2 Two-Tier Monitoring Architecture: Agentless API vs. Host Agent</h2>
      <p>
        Pulse employs a hybrid monitoring model. It prioritizes non-intrusive API connections and reserves agent installation strictly for hardware-level telemetry:
      </p>

      <table class="data-table">
        <thead>
          <tr>
            <th style="width: 20%;">Monitoring Tier</th>
            <th style="width: 25%;">Connection Method</th>
            <th style="width: 32%;">What It Monitors</th>
            <th style="width: 23%;">When to Use</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Tier 1: Agentless API Token</strong></td>
            <td>HTTPS connection (Port 8006) using a scoped Proxmox API Token (<span class="inline-code">PVEAuditor</span>).</td>
            <td>Cluster inventory, node status, VM & container states, CPU/RAM/Disk consumption, Ceph & ZFS health.</td>
            <td><strong>Recommended default</strong> for all hypervisors. Zero daemon overhead, zero hypervisor risk.</td>
          </tr>
          <tr>
            <td><strong>Tier 2: Unified Host Agent</strong></td>
            <td>Lightweight system daemon (<span class="inline-code">pulse-agent</span>) talking to Pulse over TCP 7655.</td>
            <td>Physical drive SMART metrics, CPU/motherboard temperatures, IPMI sensors, <span class="inline-code">mdadm</span> RAID, Docker/Podman.</td>
            <td>Install on physical nodes where deep hardware diagnostics are required.</td>
          </tr>
        </tbody>
      </table>

      <h2 class="sub-title">1.3 Network Bridge Telemetry Caveat & Recommendation</h2>
      <div class="callout callout-warning">
        <div class="callout-title">Important Operational Boundary: Linux Bridges & VLANs</div>
        Pulse visualizes overall network throughput for nodes and guests. However, if your operations require fine-grained Linux bridge metrics—such as individual <span class="inline-code">vmbr0/1/2</span> throughput, VLAN-tagged bandwidth breakdown, Linux bridge port STP state, packet drops, frame errors, or bond-member health—Pulse should be complemented by <strong>Prometheus + node_exporter + Grafana</strong> or <strong>LibreNMS</strong>.
      </div>
    </div>
  </div>

  <div class="doc-footer">
    <span class="confidential">CONFIDENTIAL — INNSPARK OPERATIONS</span>
    <span>Pulse Monitoring Tool Guide</span>
    <span>PAGE 1 OF 4</span>
  </div>
</div>

<!-- ==================== PAGE 2: INSTALLATION PREREQUISITES & OFFLINE SETUP ==================== -->
<div class="page">
  <div>
    <div class="doc-header">
      <span><span class="org">INNSPARK</span> | Infrastructure Operations</span>
      <span>Pulse Server: Installation Prerequisites & Offline Deployment</span>
    </div>

    <div class="page-content">
      <h1 class="sec-title">2. Pulse Server: Prerequisites & Offline Installation</h1>

      <p>
        The Pulse monitoring server is deployed directly on a dedicated Linux VM (Ubuntu/Debian) as a native <strong>systemd</strong> service. This approach eliminates the performance overhead, storage abstractions, and port-mapping complexities associated with Docker.
      </p>

      <h2 class="sub-title">2.1 Target Environment & File Preparation</h2>
      <div class="grid-2">
        <div class="card">
          <strong style="font-size: 8pt; color: #0284c7;">System Specifications</strong>
          <table class="data-table" style="margin-top: 3px;">
            <tr><td style="font-weight: 600; width: 40%;">Target OS</td><td>Ubuntu / Debian Linux VM</td></tr>
            <tr><td style="font-weight: 600;">Service Manager</td><td>Native <span class="inline-code">systemd</span> (No Docker)</td></tr>
            <tr><td style="font-weight: 600;">Listening Port</td><td><strong>TCP 7655</strong></td></tr>
            <tr><td style="font-weight: 600;">Install Directory</td><td><span class="inline-code">/opt/pulse-install</span></td></tr>
            <tr><td style="font-weight: 600;">Config Directory</td><td><span class="inline-code">/etc/pulse</span></td></tr>
          </table>
        </div>
        <div class="card">
          <strong style="font-size: 8pt; color: #0284c7;">Required Offline Packages</strong>
          <p style="font-size: 7.5pt; margin-top: 2px;">
            Due to restricted outbound Internet on VM subnets, place these 3 files in <span class="inline-code">/opt/pulse-install</span>:
          </p>
          <ul class="compact-list" style="font-size: 7.5pt;">
            <li><span class="inline-code">install.sh</span> (Pulse installer script)</li>
            <li><span class="inline-code">pulse-v6.3.1-linux-amd64.tar.gz</span> (Release package)</li>
            <li><span class="inline-code">pulse-v6.3.1-linux-amd64.tar.gz.sshsig</span> (Signature)</li>
          </ul>
        </div>
      </div>

      <h2 class="sub-title">2.2 Step-by-Step Installation Runbook</h2>

      <div style="margin-top: 4px;">
        <span class="step-num">1</span><strong style="font-size: 8.5pt;">Pre-Installation Validation: Verify Files & Signatures</strong>
      </div>
      <p style="margin-bottom: 2px;">Confirm files exist, test archive integrity, and ensure the cryptographic signature sidecar is present:</p>
      <div class="code-block">
        <span class="cmd">cd</span> /opt/pulse-install<br>
        <span class="cmd">ls -lh</span> install.sh pulse-v6.3.1-linux-amd64.tar.gz pulse-v6.3.1-linux-amd64.tar.gz.sshsig<br><br>
        <span class="comment"># Validate that signature file is recognized</span><br>
        <span class="cmd">test -f</span> /opt/pulse-install/pulse-v6.3.1-linux-amd64.tar.gz.sshsig && <span class="cmd">echo</span> <span class="success">"Signature file found"</span><br><br>
        <span class="comment"># Test tarball integrity and script syntax</span><br>
        <span class="cmd">tar -tzf</span> /opt/pulse-install/pulse-v6.3.1-linux-amd64.tar.gz | <span class="cmd">head -10</span><br>
        <span class="cmd">bash -n</span> /opt/pulse-install/install.sh
      </div>

      <div class="callout callout-info">
        <div class="callout-title">Installer Archive Rule</div>
        The installer's <span class="inline-code">--archive PATH</span> flag automatically requires a matching <span class="inline-code">PATH.sshsig</span> in the exact same directory. Do not rename or separate these files.
      </div>

      <div style="margin-top: 6px;">
        <span class="step-num">2</span><strong style="font-size: 8.5pt;">Execute Native Local Installation</strong>
      </div>
      <p style="margin-bottom: 2px;">Run the installer pointing directly to the local archive without redownloading from GitHub:</p>
      <div class="code-block">
        <span class="cmd">cd</span> /opt/pulse-install<br>
        <span class="cmd">sudo bash</span> ./install.sh <span class="param">--version</span> v6.3.1 <span class="param">--archive</span> /opt/pulse-install/pulse-v6.3.1-linux-amd64.tar.gz
      </div>

      <div style="margin-top: 6px;">
        <span class="step-num">3</span><strong style="font-size: 8.5pt;">Verify Service & Listening Port</strong>
      </div>
      <p style="margin-bottom: 2px;">Ensure the daemon is active, enabled on system reboot, and actively listening on port 7655:</p>
      <div class="code-block">
        <span class="comment"># Verify systemd service status</span><br>
        <span class="cmd">sudo systemctl status</span> pulse <span class="param">--no-pager</span><br>
        <span class="cmd">sudo systemctl enable --now</span> pulse<br><br>
        <span class="comment"># Check TCP port 7655 and local response</span><br>
        <span class="cmd">sudo ss -lntp</span> | <span class="cmd">grep</span> 7655<br>
        <span class="cmd">curl -I</span> http://127.0.0.1:7655
      </div>
    </div>
  </div>

  <div class="doc-footer">
    <span class="confidential">CONFIDENTIAL — INNSPARK OPERATIONS</span>
    <span>Pulse Monitoring Tool Guide</span>
    <span>PAGE 2 OF 4</span>
  </div>
</div>

<!-- ==================== PAGE 3: BOOTSTRAP TOKEN & WEB CONFIGURATION ==================== -->
<div class="page">
  <div>
    <div class="doc-header">
      <span><span class="org">INNSPARK</span> | Infrastructure Operations</span>
      <span>Bootstrap Token, Security Wizard & Firewall Configuration</span>
    </div>

    <div class="page-content">
      <h1 class="sec-title">3. Initial Setup, Security Wizard & Firewall Hardening</h1>

      <p>
        After the Pulse service is active, you must retrieve the initial one-time bootstrap token, configure administrative credentials, and permit network access through the host firewall.
      </p>

      <div style="margin-top: 4px;">
        <span class="step-num">4</span><strong style="font-size: 8.5pt;">Retrieve the Initial Bootstrap Token</strong>
      </div>
      <p style="margin-bottom: 2px;">Pulse uses a one-time bootstrap token to authenticate the administrator on initial setup:</p>
      <div class="code-block">
        <span class="comment"># Retrieve the plaintext bootstrap token</span><br>
        <span class="cmd">sudo /usr/local/bin/pulse</span> bootstrap-token
      </div>

      <div class="callout callout-danger">
        <div class="callout-title">Critical Warning: Do NOT Read .bootstrap_token File Directly</div>
        Do <strong>not</strong> attempt to read <span class="inline-code">/etc/pulse/.bootstrap_token</span> with <span class="inline-code">cat</span>. In Pulse v6, that file contains an encrypted JSON snapshot rather than the usable token. Always run <span class="inline-code">sudo pulse bootstrap-token</span> to decrypt and display the valid token.
      </div>

      <div style="margin-top: 6px;">
        <span class="step-num">5</span><strong style="font-size: 8.5pt;">Firewall Configuration: Restrict Management Access</strong>
      </div>
      <p style="margin-bottom: 2px;">Secure port 7655 by allowing only your trusted administration network subnet:</p>
      <div class="code-block">
        <span class="comment"># Allow admin subnet (replace 10.31.0.0/23 with your actual management subnet)</span><br>
        <span class="cmd">sudo ufw allow from</span> 10.31.0.0/23 <span class="param">to any port</span> 7655 proto tcp<br>
        <span class="cmd">sudo ufw status</span><br><br>
        <span class="comment"># Test connectivity from your workstation</span><br>
        <span class="cmd">nc -vz</span> 10.31.0.50 7655
      </div>

      <div style="margin-top: 6px;">
        <span class="step-num">6</span><strong style="font-size: 8.5pt;">Complete Web GUI First-Time Security Wizard</strong>
      </div>
      <div class="flow-container">
        <div class="flow-step">1. Open <span class="inline-code">http://VM-IP:7655</span></div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">2. Paste Bootstrap Token</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">3. Create Admin Username/Password</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">4. Run Security Setup</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">5. Save Generated API Token</div>
      </div>

      <div class="callout callout-warning" style="margin-top: 6px;">
        <div class="callout-title">Mandatory Action: Secure the Generated API Token</div>
        During the Quick Security Setup wizard, Pulse generates an administrative API token used for automation and agent enrollment. <strong>Copy and securely store this token</strong> before navigating away from the page, as it will not be displayed again.
      </div>

      <h2 class="sub-title">3.1 Monitored Host Proxy Exclusion (NO_PROXY)</h2>
      <p>
        If monitored Linux VMs or Proxmox hosts use an internal proxy (e.g. Squid at <span class="inline-code">10.31.1.159</span>), you must explicitly bypass the proxy for Pulse server traffic. Otherwise, agents will fail to connect and display as offline:
      </p>
      <div class="code-block">
        <span class="comment"># Add to /etc/environment or profile on monitored Linux hosts:</span><br>
        <span class="cmd">export NO_PROXY</span>=<span class="param">"localhost,127.0.0.1,10.31.0.50"</span><br>
        <span class="cmd">export no_proxy</span>=<span class="param">"$NO_PROXY"</span>
      </div>
    </div>
  </div>

  <div class="doc-footer">
    <span class="confidential">CONFIDENTIAL — INNSPARK OPERATIONS</span>
    <span>Pulse Monitoring Tool Guide</span>
    <span>PAGE 3 OF 4</span>
  </div>
</div>

<!-- ==================== PAGE 4: CONNECTING SYSTEMS & HEALTH CHECKS ==================== -->
<div class="page page-last">
  <div>
    <div class="doc-header">
      <span><span class="org">INNSPARK</span> | Infrastructure Operations</span>
      <span>Adding Monitored Sources & Maintenance Checklist</span>
    </div>

    <div class="page-content">
      <h1 class="sec-title">4. Adding Systems to Monitor & Operational Health</h1>

      <p>
        Once the Pulse server is initialized, connect your infrastructure via the web dashboard at <em>Settings → Infrastructure</em>.
      </p>

      <h2 class="sub-title">4.1 Method A: Proxmox VE via API Inventory (Agentless)</h2>
      <div class="grid-2">
        <div class="card">
          <strong style="font-size: 8pt; color: #0284c7;">PVE Settings in Pulse UI</strong>
          <p style="font-size: 7.5pt; margin-top: 2px;">
            Navigate to: <em>Settings → Infrastructure → Add Source → Proxmox VE → API Inventory</em>
          </p>
          <table class="data-table" style="margin-top: 2px;">
            <tr><td style="font-weight: 600; width: 40%;">Host URL</td><td><span class="inline-code">https://10.31.x.x:8006</span></td></tr>
            <tr><td style="font-weight: 600;">Token ID Format</td><td><span class="inline-code">&lt;user&gt;@&lt;realm&gt;!&lt;name&gt;</span></td></tr>
            <tr><td style="font-weight: 600;">Configured ID</td><td><span class="inline-code">pulse-monitor@pve!pulse</span></td></tr>
            <tr><td style="font-weight: 600;">Permissions</td><td><span class="inline-code">PVEAuditor</span> on <span class="inline-code">/</span> (Read-Only)</td></tr>
            <tr><td style="font-weight: 600;">Ignore Self-Signed</td><td><strong>Enabled</strong> (Default certs)</td></tr>
          </table>
        </div>
        <div>
          <strong style="font-size: 8pt; color: #0284c7;">Pre-Flight Token Test via cURL</strong>
          <div class="code-block" style="margin-top: 2px;">
            <span class="comment"># Validate token from any Linux machine</span><br>
            <span class="cmd">curl -k \</span><br>
            &nbsp;&nbsp;<span class="param">-H</span> "Authorization: PVEAPIToken=pulse-monitor@pve!pulse=SECRET" \<br>
            &nbsp;&nbsp;https://YOUR_PROXMOX_IP:8006/api2/json/version<br><br>
            <span class="comment"># Output: { "data": { "version": "..." } }</span>
          </div>
          <div class="callout callout-info" style="margin-top: 3px;">
            <span class="inline-code">PVEAuditor</span> provides read-only visibility into VMs, storage, and nodes without granting any administrative privileges.
          </div>
        </div>
      </div>

      <h2 class="sub-title">4.2 Method B: Proxmox Backup Server (PBS) Automated Integration</h2>
      <p>
        Pulse automates PBS enrollment. In the UI, generate the PBS setup command, review it, and execute it on the PBS host as root:
      </p>
      <div class="flow-container">
        <div class="flow-step">1. UI Generates Setup Command</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">2. Run on PBS as Root</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">3. Creates <span class="inline-code">pulse-monitor@pbs</span></div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">4. Grants Read-Only <span class="inline-code">Audit</span> Role</div>
        <div class="flow-arrow">→</div>
        <div class="flow-step">5. Auto-Registers to Pulse</div>
      </div>

      <h2 class="sub-title">4.3 Method C: Standalone Linux Hosts (Unified Agent)</h2>
      <p>
        In Pulse, go to <em>Settings → Infrastructure → Install on a host</em>. Select Linux and copy the generated command. Run that command on the target VM to automatically enroll the unified agent (<span class="inline-code">pulse-agent.service</span>).
      </p>

      <h2 class="sub-title">4.4 Post-Installation Verification & Maintenance Checklist</h2>
      <div class="grid-2">
        <div class="code-block">
          <span class="comment"># Complete Server Health Check Suite:</span><br>
          <span class="cmd">sudo pulse --version</span><br>
          <span class="cmd">sudo systemctl is-active</span> pulse<br>
          <span class="cmd">sudo systemctl is-enabled</span> pulse<br>
          <span class="cmd">sudo ss -lntp</span> | <span class="cmd">grep</span> 7655<br>
          <span class="cmd">sudo journalctl -u</span> pulse <span class="param">-n 20 --no-pager</span>
        </div>
        <div class="card">
          <strong style="font-size: 8pt; color: #0284c7;">Operational Maintenance Best Practices</strong>
          <ul class="compact-list" style="font-size: 7.5pt; margin-top: 3px;">
            <li><strong>Backup Config:</strong> Regularly back up <span class="inline-code">/etc/pulse</span>.</li>
            <li><strong>Alerts:</strong> Configure thresholds under <em>Settings → Alerts</em>.</li>
            <li><strong>Updates:</strong> Run <span class="inline-code">sudo /bin/update</span> for systemd binary updates.</li>
            <li><strong>Data Retention:</strong> Set metric history retention in System Settings.</li>
          </ul>
        </div>
      </div>
    </div>
  </div>

  <div class="doc-footer">
    <span class="confidential">CONFIDENTIAL — INNSPARK OPERATIONS</span>
    <span>Pulse Monitoring Tool Guide</span>
    <span>PAGE 4 OF 4</span>
  </div>
</div>

</body>
</html>
"""

def generate_pdf():
    print(f"Writing HTML to {HTML_FILE}...")
    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Compiling PDF via Headless Chrome with --no-pdf-header-footer...")
    cmd = [
        "google-chrome",
        "--headless=new",
        "--user-data-dir=/tmp/pulse-guide-chrome-profile",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_FILE}",
        HTML_FILE
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    print("Chrome output:", res.stdout, res.stderr)
    if res.returncode != 0:
        print(f"Error compiling PDF: {res.returncode}")
        return False

    print(f"PDF generated successfully at: {PDF_FILE}")
    print("File size:", os.path.getsize(PDF_FILE), "bytes")
    return True

if __name__ == "__main__":
    success = generate_pdf()
    if not success:
        exit(1)
