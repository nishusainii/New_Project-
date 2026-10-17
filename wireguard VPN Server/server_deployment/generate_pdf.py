#!/usr/bin/env python3
"""
WireGuard Enterprise Architecture & Deployment PDF Generator
Uses Headless Chromium to compile rich HTML/CSS + SVG vector flowcharts into an enterprise-grade PDF.
"""

import os
import subprocess
import sys

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(OUTPUT_DIR, "architecture_document.html")
PDF_PATH = os.path.join(OUTPUT_DIR, "WireGuard_Server_Architecture_and_Deployment_Guide.pdf")

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>WireGuard Enterprise - Architecture & Server Deployment Guide</title>
<style>
  @page {
    size: A4 portrait;
    margin: 10mm 12mm 10mm 12mm;
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 7.5pt;
      color: #64748b;
    }
  }

  * {
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1e293b;
    background: #ffffff;
    line-height: 1.4;
    font-size: 8.8pt;
    margin: 0;
    padding: 0;
  }

  /* Cover / Header Banner */
  .cover-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0369a1 100%);
    color: #ffffff;
    padding: 16px 20px;
    border-radius: 6px;
    margin-bottom: 12px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.08);
  }

  .cover-badge {
    display: inline-block;
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.25);
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 7pt;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
  }

  .cover-title {
    font-size: 18pt;
    font-weight: 800;
    margin: 0 0 4px 0;
    letter-spacing: -0.02em;
    line-height: 1.15;
  }

  .cover-subtitle {
    font-size: 10pt;
    color: #93c5fd;
    margin: 0 0 10px 0;
    font-weight: 400;
  }

  .cover-meta {
    display: flex;
    gap: 16px;
    font-size: 7.5pt;
    color: #cbd5e1;
    border-top: 1px solid rgba(255, 255, 255, 0.15);
    padding-top: 6px;
  }

  /* Headings */
  h1 {
    font-size: 12pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 1.5px solid #0284c7;
    padding-bottom: 3px;
    margin-top: 14px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 8px;
    break-after: avoid;
  }

  h2 {
    font-size: 9.5pt;
    font-weight: 700;
    color: #1e293b;
    margin-top: 8px;
    margin-bottom: 4px;
    border-left: 3px solid #0284c7;
    padding-left: 6px;
    break-after: avoid;
  }

  p {
    margin: 0 0 6px 0;
  }

  /* Grid Layouts */
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 10px;
  }

  .grid-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin-bottom: 8px;
  }

  /* Cards */
  .card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    padding: 8px 10px;
    break-inside: avoid;
  }

  .card-title {
    font-size: 8.2pt;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 2px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .card-accent { border-left: 3px solid #0284c7; }
  .card-success { border-left: 3px solid #10b981; }
  .card-warning { border-left: 3px solid #f59e0b; }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 10px;
    font-size: 7.8pt;
    break-inside: avoid;
  }

  th {
    background: #0f172a;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 5px 7px;
    border: 1px solid #1e293b;
  }

  td {
    padding: 4px 7px;
    border: 1px solid #e2e8f0;
    background: #ffffff;
  }

  tr:nth-child(even) td {
    background: #f8fafc;
  }

  /* Code & Command Blocks */
  .code-block {
    background: #0f172a;
    color: #e2e8f0;
    padding: 6px 10px;
    border-radius: 4px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 7.4pt;
    margin-bottom: 6px;
    line-height: 1.38;
    white-space: pre-wrap;
    word-break: break-all;
    border: 1px solid #1e293b;
    break-inside: avoid;
  }

  .code-comment { color: #94a3b8; font-style: italic; }
  .code-cmd { color: #38bdf8; font-weight: 600; }
  .code-param { color: #a7f3d0; }

  code {
    background: #f1f5f9;
    color: #0f172a;
    padding: 1px 4px;
    border-radius: 3px;
    font-family: monospace;
    font-size: 7.8pt;
    border: 1px solid #cbd5e1;
  }

  .page-break {
    page-break-before: always;
    break-before: page;
  }

  .no-break {
    page-break-inside: avoid;
    break-inside: avoid;
  }

  /* Diagram Box Container */
  .diagram-container {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 8px;
    margin: 8px 0;
    text-align: center;
    break-inside: avoid;
  }

  .diagram-title {
    font-size: 8pt;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  svg {
    max-width: 100%;
    height: auto;
  }
</style>
</head>
<body>

<!-- ==================== PAGE 1: ARCHITECTURE ==================== -->
<div class="cover-header">
  <span class="cover-badge">Enterprise Production Architecture & Operations</span>
  <h1 class="cover-title" style="color: #fff; border: none; padding: 0;">WireGuard Enterprise VPN Gateway</h1>
  <div class="cover-subtitle">Zero-Trust High-Throughput Linux In-Tree Gateway & FastAPI Control Plane</div>
  <div class="cover-meta">
    <div><strong>Host Server:</strong> 10.31.7.48</div>
    <div><strong>VPN Subnet:</strong> 172.29.250.0/24 (Gateway: 172.29.250.1)</div>
    <div><strong>Listen Port:</strong> UDP 443 (Firewall Bypass)</div>
    <div><strong>Version:</strong> v4.2 ZTNA Production</div>
  </div>
</div>

<h1>1. Executive Summary & Design Principles</h1>
<p>
  <strong>WireGuard Enterprise</strong> couples the line-rate throughput and cryptographic simplicity of the Linux in-tree kernel module (<code>wireguard.ko</code>) with a fully containerized Zero-Trust Network Architecture (ZTNA) control plane. Designed for high-assurance, air-gapped, and mission-critical enterprise environments, all data plane packets stay strictly within kernel space, achieving sub-millisecond latencies and eliminating user-space copying overheads.
</p>

<div class="grid-3 no-break">
  <div class="card card-accent">
    <div class="card-title">In-Tree Kernel Data Plane</div>
    <p style="font-size: 7.5pt; margin: 0; color: #475569;">
      Line-rate encryption via ChaCha20-Poly1305 and Curve25519 ECDH. Direct packet forwarding without user-space buffer bottlenecks.
    </p>
  </div>
  <div class="card card-success">
    <div class="card-title">Zero-Trust Firewall Pipeline</div>
    <p style="font-size: 7.5pt; margin: 0; color: #475569;">
      Granular per-client (/32) NFTables policy verification. Client-to-client isolation with dedicated ICMP/SSH management tunnels.
    </p>
  </div>
  <div class="card card-warning">
    <div class="card-title">Air-Gapped Independence</div>
    <p style="font-size: 7.5pt; margin: 0; color: #475569;">
      Zero external CDN or cloud dependencies. 100% self-hosted vector UI, local QR code generation, and single-tarball deployment.
    </p>
  </div>
</div>

<h1>2. High-Level System Architecture</h1>
<p>
  The architecture enforces strict decoupling between the <strong>Control Plane</strong> (FastAPI Docker container) and the <strong>Data Plane</strong> (Kernel WireGuard & NFTables).
</p>

<div class="diagram-container no-break">
  <div class="diagram-title">Figure 1: End-to-End System & Network Architecture</div>
  <svg viewBox="0 0 740 310" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="10" width="200" height="290" rx="8" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="1.5" />
    <text x="110" y="32" font-size="11" font-weight="700" fill="#0f172a" text-anchor="middle">CLIENTS (ZTNA PEERS)</text>

    <rect x="25" y="45" width="170" height="46" rx="6" fill="#ffffff" stroke="#94a3b8" />
    <text x="110" y="64" font-size="9" font-weight="600" fill="#0f172a" text-anchor="middle">Admin Workstation</text>
    <text x="110" y="79" font-size="7.5" fill="#0284c7" text-anchor="middle">172.29.250.2/32 (Full/Split)</text>

    <rect x="25" y="102" width="170" height="46" rx="6" fill="#ffffff" stroke="#94a3b8" />
    <text x="110" y="121" font-size="9" font-weight="600" fill="#0f172a" text-anchor="middle">Mobile Device (iOS/Android)</text>
    <text x="110" y="136" font-size="7.5" fill="#0284c7" text-anchor="middle">172.29.250.18/32 (QR Enrolled)</text>

    <rect x="25" y="159" width="170" height="46" rx="6" fill="#ffffff" stroke="#94a3b8" />
    <text x="110" y="178" font-size="9" font-weight="600" fill="#0f172a" text-anchor="middle">Production Database</text>
    <text x="110" y="193" font-size="7.5" fill="#0284c7" text-anchor="middle">172.29.250.11/32 (Split Tunnel)</text>

    <rect x="25" y="216" width="170" height="46" rx="6" fill="#ffffff" stroke="#94a3b8" />
    <text x="110" y="235" font-size="9" font-weight="600" fill="#0f172a" text-anchor="middle">Branch Office Router</text>
    <text x="110" y="250" font-size="7.5" fill="#0284c7" text-anchor="middle">172.29.250.20/32 (Site Gateway)</text>

    <rect x="240" y="10" width="490" height="290" rx="8" fill="#f8fafc" stroke="#0284c7" stroke-width="2" />
    <text x="485" y="32" font-size="11" font-weight="700" fill="#0369a1" text-anchor="middle">LINUX HOST SERVER (10.31.7.48 / Ubuntu 22.04+)</text>

    <rect x="255" y="45" width="220" height="245" rx="6" fill="#e2e8f0" stroke="#64748b" stroke-width="1.2" />
    <text x="365" y="63" font-size="9.5" font-weight="700" fill="#1e293b" text-anchor="middle">LINUX KERNEL DATA PLANE</text>

    <rect x="265" y="74" width="200" height="48" rx="4" fill="#0f172a" />
    <text x="365" y="93" font-size="8.5" font-weight="600" fill="#38bdf8" text-anchor="middle">wireguard.ko (Kernel Module)</text>
    <text x="365" y="108" font-size="7.2" fill="#cbd5e1" text-anchor="middle">Interface: wg0 (172.29.250.1/24 : 443/UDP)</text>

    <rect x="265" y="130" width="200" height="48" rx="4" fill="#ffffff" stroke="#94a3b8" />
    <text x="365" y="149" font-size="8.5" font-weight="600" fill="#0f172a" text-anchor="middle">nftables Subsystem</text>
    <text x="365" y="164" font-size="7.2" fill="#475569" text-anchor="middle">table inet filter (vpn_acl include)</text>

    <rect x="265" y="186" width="200" height="42" rx="4" fill="#ffffff" stroke="#94a3b8" />
    <text x="365" y="203" font-size="8.2" font-weight="600" fill="#0f172a" text-anchor="middle">IPv4 Forwarding Engine</text>
    <text x="365" y="217" font-size="7.2" fill="#16a34a" text-anchor="middle">sysctl net.ipv4.ip_forward = 1</text>

    <rect x="265" y="236" width="200" height="42" rx="4" fill="#ffffff" stroke="#94a3b8" />
    <text x="365" y="253" font-size="8.2" font-weight="600" fill="#0f172a" text-anchor="middle">NAT Postrouting (ens18)</text>
    <text x="365" y="267" font-size="7.2" fill="#475569" text-anchor="middle">Masquerade -> Internal LAN / WAN</text>

    <rect x="495" y="45" width="220" height="245" rx="6" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.2" />
    <text x="605" y="63" font-size="9.5" font-weight="700" fill="#15803d" text-anchor="middle">DOCKER CONTROL PLANE (Port 8000)</text>

    <rect x="505" y="74" width="200" height="43" rx="4" fill="#ffffff" stroke="#86efac" />
    <text x="605" y="92" font-size="8.2" font-weight="600" fill="#0f172a" text-anchor="middle">FastAPI Engine (uvicorn)</text>
    <text x="605" y="106" font-size="7.2" fill="#475569" text-anchor="middle">REST APIs + Jinja2 Templates</text>

    <rect x="505" y="125" width="200" height="43" rx="4" fill="#ffffff" stroke="#86efac" />
    <text x="605" y="143" font-size="8.2" font-weight="600" fill="#0f172a" text-anchor="middle">WireGuard Syncconf Engine</text>
    <text x="605" y="157" font-size="7.2" fill="#475569" text-anchor="middle">wg syncconf (Zero Downtime)</text>

    <rect x="505" y="176" width="200" height="43" rx="4" fill="#ffffff" stroke="#86efac" />
    <text x="605" y="194" font-size="8.2" font-weight="600" fill="#0f172a" text-anchor="middle">NFTables Mutation Pipeline</text>
    <text x="605" y="208" font-size="7.2" fill="#475569" text-anchor="middle">Dry-run (nft -c -f) & Atomic Reload</text>

    <rect x="505" y="227" width="200" height="51" rx="4" fill="#ffffff" stroke="#86efac" />
    <text x="605" y="244" font-size="8.2" font-weight="600" fill="#0f172a" text-anchor="middle">SQLite WAL Database</text>
    <text x="605" y="258" font-size="7.2" fill="#475569" text-anchor="middle">Peers, Interfaces, Rules, Audit Logs</text>
    <text x="605" y="271" font-size="6.8" fill="#64748b" text-anchor="middle">/opt/wireguard-enterprise/data/wireguard.db</text>

    <line x1="195" y1="155" x2="265" y2="98" stroke="#0284c7" stroke-width="2" stroke-dasharray="4,4" />
    <polygon points="265,98 255,96 259,105" fill="#0284c7" />

    <line x1="505" y1="145" x2="465" y2="105" stroke="#16a34a" stroke-width="1.8" />
    <polygon points="465,105 475,107 472,115" fill="#16a34a" />

    <line x1="505" y1="197" x2="465" y2="160" stroke="#16a34a" stroke-width="1.8" />
    <polygon points="465,160 476,162 471,170" fill="#16a34a" />
  </svg>
</div>

<!-- ==================== PAGE 2: FLOWCHARTS ==================== -->
<div class="page-break"></div>

<h1>3. End-to-End Client Packet Flow & Routing</h1>
<p>
  When a client sends traffic through the tunnel, packets undergo cryptographic authentication inside kernel space before being subjected to stateful inspection and Zero-Trust ACL evaluation.
</p>

<div class="diagram-container no-break">
  <div class="diagram-title">Figure 2: Ingress Packet Stateful Inspection & Routing Lifecycle</div>
  <svg viewBox="0 0 740 190" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="20" width="125" height="55" rx="5" fill="#0f172a" />
    <text x="72" y="43" font-size="8.5" font-weight="600" fill="#38bdf8" text-anchor="middle">1. Client Ingress</text>
    <text x="72" y="57" font-size="7.5" fill="#cbd5e1" text-anchor="middle">UDP 443 Packet</text>
    <text x="72" y="68" font-size="7" fill="#94a3b8" text-anchor="middle">Curve25519 Auth</text>

    <line x1="135" y1="47" x2="160" y2="47" stroke="#0284c7" stroke-width="2" />
    <polygon points="160,47 152,43 152,51" fill="#0284c7" />

    <rect x="160" y="20" width="125" height="55" rx="5" fill="#ffffff" stroke="#0284c7" stroke-width="1.5" />
    <text x="222" y="43" font-size="8.5" font-weight="600" fill="#0f172a" text-anchor="middle">2. Cryptokey Routing</text>
    <text x="222" y="57" font-size="7.5" fill="#475569" text-anchor="middle">Validate AllowedIPs</text>
    <text x="222" y="68" font-size="7" fill="#16a34a" text-anchor="middle">Match Peer /32 IP</text>

    <line x1="285" y1="47" x2="310" y2="47" stroke="#0284c7" stroke-width="2" />
    <polygon points="310,47 302,43 302,51" fill="#0284c7" />

    <rect x="310" y="10" width="130" height="75" rx="5" fill="#ffffff" stroke="#64748b" stroke-width="1.5" />
    <text x="375" y="30" font-size="8.5" font-weight="600" fill="#0f172a" text-anchor="middle">3. Forward Chain</text>
    <text x="375" y="44" font-size="7.2" fill="#475569" text-anchor="middle">ct state established? Accept</text>
    <text x="375" y="57" font-size="7.2" fill="#475569" text-anchor="middle">wg0->wg0 ICMP/SSH? Accept</text>
    <text x="375" y="72" font-size="7.2" fill="#0284c7" text-anchor="middle">Jump to vpn_acl</text>

    <line x1="440" y1="47" x2="465" y2="47" stroke="#0284c7" stroke-width="2" />
    <polygon points="465,47 457,43 457,51" fill="#0284c7" />

    <polygon points="535,10 600,47 535,85 470,47" fill="#fef3c7" stroke="#f59e0b" stroke-width="1.5" />
    <text x="535" y="44" font-size="8" font-weight="700" fill="#b45309" text-anchor="middle">4. vpn_acl</text>
    <text x="535" y="56" font-size="7.2" fill="#78350f" text-anchor="middle">Rule Match?</text>

    <line x1="535" y1="85" x2="535" y2="125" stroke="#ef4444" stroke-width="2" />
    <polygon points="535,125 531,117 539,117" fill="#ef4444" />
    <text x="555" y="107" font-size="8" font-weight="700" fill="#ef4444">NO</text>

    <rect x="475" y="125" width="120" height="45" rx="5" fill="#fef2f2" stroke="#ef4444" stroke-width="1.5" />
    <text x="535" y="145" font-size="8.5" font-weight="700" fill="#991b1b" text-anchor="middle">counter drop</text>
    <text x="535" y="159" font-size="7.2" fill="#b91c1c" text-anchor="middle">Packet Logged & Dropped</text>

    <line x1="600" y1="47" x2="630" y2="47" stroke="#16a34a" stroke-width="2" />
    <polygon points="630,47 622,43 622,51" fill="#16a34a" />
    <text x="612" y="39" font-size="8" font-weight="700" fill="#16a34a">YES</text>

    <rect x="630" y="15" width="100" height="65" rx="5" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.5" />
    <text x="680" y="35" font-size="8.5" font-weight="700" fill="#15803d" text-anchor="middle">5. Egress & NAT</text>
    <text x="680" y="50" font-size="7" fill="#166534" text-anchor="middle">NAT Masquerade</text>
    <text x="680" y="61" font-size="7" fill="#166534" text-anchor="middle">Forward to ens18</text>
    <text x="680" y="72" font-size="7" fill="#166534" text-anchor="middle">LAN / Internet Out</text>
  </svg>
</div>

<h1>4. Zero-Trust Access Control (ZTNA) & Mutation Pipeline</h1>
<p>
  Security policies are expressed in <code>/etc/nftables/acl.nft</code>, which is included inside <code>chain vpn_acl</code>. All edits from the web dashboard pass through an atomic 6-stage validation pipeline:
</p>

<div class="diagram-container no-break">
  <div class="diagram-title">Figure 3: Safe Firewall Mutation & Kernel Commit Flowchart</div>
  <svg viewBox="0 0 740 90" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="18" width="105" height="54" rx="5" fill="#ffffff" stroke="#94a3b8" />
    <text x="62" y="40" font-size="8" font-weight="700" fill="#0f172a" text-anchor="middle">1. Web UI Action</text>
    <text x="62" y="54" font-size="7" fill="#475569" text-anchor="middle">Add/Edit Client Rule</text>
    <text x="62" y="65" font-size="7" fill="#0284c7" text-anchor="middle">Flush-left Format</text>

    <line x1="115" y1="45" x2="135" y2="45" stroke="#0284c7" stroke-width="1.5" />
    <polygon points="135,45 127,42 127,48" fill="#0284c7" />

    <rect x="135" y="18" width="110" height="54" rx="5" fill="#ffffff" stroke="#94a3b8" />
    <text x="190" y="40" font-size="8" font-weight="700" fill="#0f172a" text-anchor="middle">2. REST API Ingestion</text>
    <text x="190" y="54" font-size="7" fill="#475569" text-anchor="middle">PUT /api/firewall/file</text>
    <text x="190" y="65" font-size="7" fill="#475569" text-anchor="middle">Trim & Normalize</text>

    <line x1="245" y1="45" x2="265" y2="45" stroke="#0284c7" stroke-width="1.5" />
    <polygon points="265,45 257,42 257,48" fill="#0284c7" />

    <rect x="265" y="18" width="115" height="54" rx="5" fill="#fef3c7" stroke="#f59e0b" />
    <text x="322" y="40" font-size="8" font-weight="700" fill="#b45309" text-anchor="middle">3. Snapshot Backup</text>
    <text x="322" y="54" font-size="7" fill="#78350f" text-anchor="middle">Save pre-edit config</text>
    <text x="322" y="65" font-size="7" fill="#78350f" text-anchor="middle">to /data/backups/</text>

    <line x1="380" y1="45" x2="400" y2="45" stroke="#0284c7" stroke-width="1.5" />
    <polygon points="400,45 392,42 392,48" fill="#0284c7" />

    <rect x="400" y="18" width="115" height="54" rx="5" fill="#e0f2fe" stroke="#0284c7" />
    <text x="457" y="40" font-size="8" font-weight="700" fill="#0369a1" text-anchor="middle">4. Dry-Run Check</text>
    <text x="457" y="54" font-size="7" fill="#0c4a6e" text-anchor="middle">nft -c -f /etc/nftables.conf</text>
    <text x="457" y="65" font-size="7" fill="#0c4a6e" text-anchor="middle">Kernel Syntax Parse</text>

    <line x1="515" y1="45" x2="535" y2="45" stroke="#0284c7" stroke-width="1.5" />
    <polygon points="535,45 527,42 527,48" fill="#0284c7" />

    <rect x="535" y="18" width="105" height="54" rx="5" fill="#f0fdf4" stroke="#16a34a" />
    <text x="587" y="40" font-size="8" font-weight="700" fill="#15803d" text-anchor="middle">5. Atomic Commit</text>
    <text x="587" y="54" font-size="7" fill="#166534" text-anchor="middle">nft -f /etc/nftables.conf</text>
    <text x="587" y="65" font-size="7" fill="#166534" text-anchor="middle">Zero-packet Drop</text>

    <line x1="640" y1="45" x2="660" y2="45" stroke="#0284c7" stroke-width="1.5" />
    <polygon points="660,45 652,42 652,48" fill="#0284c7" />

    <rect x="660" y="18" width="70" height="54" rx="5" fill="#ffffff" stroke="#94a3b8" />
    <text x="695" y="43" font-size="8" font-weight="700" fill="#0f172a" text-anchor="middle">6. Audit Log</text>
    <text x="695" y="58" font-size="7" fill="#475569" text-anchor="middle">DB Saved</text>
  </svg>
</div>

<!-- ==================== PAGE 3: DEPLOYMENT ==================== -->
<div class="page-break"></div>

<h1>5. Complete Server Deployment Lifecycle</h1>
<p>
  Deploying a new WireGuard Enterprise server follows a strict 4-phase sequential workflow:
</p>

<div class="diagram-container no-break">
  <div class="diagram-title">Figure 4: Automated Deployment Lifecycle Flowchart</div>
  <svg viewBox="0 0 740 90" xmlns="http://www.w3.org/2000/svg">
    <rect x="10" y="18" width="160" height="54" rx="5" fill="#ffffff" stroke="#0284c7" stroke-width="1.5" />
    <text x="90" y="40" font-size="8.5" font-weight="700" fill="#0f172a" text-anchor="middle">PHASE 1: Host Prep</text>
    <text x="90" y="54" font-size="7.2" fill="#475569" text-anchor="middle">Install WireGuard & NFTables</text>
    <text x="90" y="66" font-size="7.2" fill="#0284c7" text-anchor="middle">./setup_host.sh</text>

    <line x1="170" y1="45" x2="195" y2="45" stroke="#0284c7" stroke-width="2" />
    <polygon points="195,45 187,41 187,49" fill="#0284c7" />

    <rect x="195" y="18" width="165" height="54" rx="5" fill="#ffffff" stroke="#0284c7" stroke-width="1.5" />
    <text x="277" y="40" font-size="8.5" font-weight="700" fill="#0f172a" text-anchor="middle">PHASE 2: Kernel Sysctl</text>
    <text x="277" y="54" font-size="7.2" fill="#475569" text-anchor="middle">net.ipv4.ip_forward = 1</text>
    <text x="277" y="66" font-size="7.2" fill="#16a34a" text-anchor="middle">modprobe wireguard</text>

    <line x1="360" y1="45" x2="385" y2="45" stroke="#0284c7" stroke-width="2" />
    <polygon points="385,45 377,41 377,49" fill="#0284c7" />

    <rect x="385" y="18" width="165" height="54" rx="5" fill="#ffffff" stroke="#0284c7" stroke-width="1.5" />
    <text x="467" y="40" font-size="8.5" font-weight="700" fill="#0f172a" text-anchor="middle">PHASE 3: Firewall Setup</text>
    <text x="467" y="54" font-size="7.2" fill="#475569" text-anchor="middle">Load /etc/nftables.conf</text>
    <text x="467" y="66" font-size="7.2" fill="#0284c7" text-anchor="middle">systemctl enable nftables</text>

    <line x1="550" y1="45" x2="575" y2="45" stroke="#0284c7" stroke-width="2" />
    <polygon points="575,45 567,41 567,49" fill="#0284c7" />

    <rect x="575" y="18" width="155" height="54" rx="5" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.5" />
    <text x="652" y="40" font-size="8.5" font-weight="700" fill="#15803d" text-anchor="middle">PHASE 4: Container Run</text>
    <text x="652" y="54" font-size="7.2" fill="#166534" text-anchor="middle">docker-compose up -d</text>
    <text x="652" y="66" font-size="7.2" fill="#166534" text-anchor="middle">Health Check :8000</text>
  </svg>
</div>

<h1>6. Step-by-Step Server Deployment Commands</h1>

<h2>Step 1: Host System Preparation</h2>
<div class="code-block"><span class="code-comment"># 1. Update OS package repositories</span>
<span class="code-cmd">sudo apt-get update -y && sudo apt-get install -y</span> wireguard wireguard-tools nftables iptables-persistent docker.io docker-compose curl jq

<span class="code-comment"># 2. Enable persistent IPv4 forwarding and BBR congestion control</span>
<span class="code-cmd">sudo tee /etc/sysctl.d/99-wireguard-enterprise.conf &lt;&lt; 'EOF'</span>
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.tcp_syncookies = 1
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
EOF
<span class="code-cmd">sudo sysctl --system</span>

<span class="code-comment"># 3. Load WireGuard kernel module</span>
<span class="code-cmd">sudo modprobe wireguard</span>
<span class="code-cmd">echo "wireguard" | sudo tee -a /etc/modules-load.d/wireguard.conf</span></div>

<h2>Step 2: Directory Structure & File Permissions</h2>
<div class="code-block"><span class="code-cmd">sudo mkdir -p</span> /etc/wireguard /etc/wireguard/archive /etc/nftables /opt/wireguard-enterprise/app /opt/wireguard-enterprise/data
<span class="code-cmd">sudo chmod 700</span> /etc/wireguard
<span class="code-cmd">sudo chmod 755</span> /etc/nftables
<span class="code-cmd">sudo chmod 750</span> /opt/wireguard-enterprise</div>

<h2>Step 3: Baseline NFTables Configuration</h2>
<div class="code-block"><span class="code-comment"># Create baseline /etc/nftables/acl.nft</span>
<span class="code-cmd">sudo touch /etc/nftables/acl.nft && sudo chmod 644 /etc/nftables/acl.nft</span>

<span class="code-comment"># Copy template and atomic reload</span>
<span class="code-cmd">sudo cp server_deployment/nftables.conf.template /etc/nftables.conf</span>
<span class="code-cmd">sudo nft -c -f /etc/nftables.conf</span>   <span class="code-comment"># Syntax validation</span>
<span class="code-cmd">sudo nft -f /etc/nftables.conf</span>      <span class="code-comment"># Live atomic reload</span>
<span class="code-cmd">sudo systemctl enable --now nftables.service</span></div>

<h2>Step 4: Launching Application Container</h2>
<div class="code-block"><span class="code-comment"># Sync codebase to host location</span>
<span class="code-cmd">sudo cp -ru app/ /opt/wireguard-enterprise/</span>

<span class="code-comment"># Start container using Docker Compose with host networking</span>
<span class="code-cmd">cd server_deployment</span>
<span class="code-cmd">sudo docker-compose up -d --force-recreate</span>

<span class="code-comment"># Verify container health</span>
<span class="code-cmd">sudo docker ps -f name=wireguard-manager</span>
<span class="code-cmd">curl -s http://127.0.0.1:8000/login | grep "WireGuard"</span></div>

<!-- ==================== PAGE 4: OPERATIONS & TABLES ==================== -->
<div class="page-break"></div>

<h1>7. Network Topology & Ports Reference</h1>

<table>
  <thead>
    <tr>
      <th>Interface</th>
      <th>Network / IP</th>
      <th>Protocol & Port</th>
      <th>Purpose</th>
      <th>Access Policy</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>ens18</strong></td>
      <td>10.31.7.48/24</td>
      <td>TCP 8000</td>
      <td>Web Admin Dashboard</td>
      <td>Restricted to Management Subnet</td>
    </tr>
    <tr>
      <td><strong>ens18</strong></td>
      <td>10.31.7.48/24</td>
      <td>TCP 22</td>
      <td>Host SSH Management</td>
      <td>Restricted Admin Jump Host</td>
    </tr>
    <tr>
      <td><strong>ens18</strong></td>
      <td>10.31.7.48/24</td>
      <td>UDP 443</td>
      <td>WireGuard Encrypted Tunnel</td>
      <td>Public / Corporate WAN Allowed</td>
    </tr>
    <tr>
      <td><strong>wg0</strong></td>
      <td>172.29.250.1/24</td>
      <td>All Protocols</td>
      <td>VPN Internal Gateway</td>
      <td>Internal Virtual Interface</td>
    </tr>
    <tr>
      <td><strong>wg0 (Peers)</strong></td>
      <td>172.29.250.2-254/32</td>
      <td>ICMP / TCP 22</td>
      <td>Peer Management & Diagnostics</td>
      <td>Client-to-Client Allowed</td>
    </tr>
    <tr>
      <td><strong>wg0 (Peers)</strong></td>
      <td>172.29.250.2-254/32</td>
      <td>Dynamic Ports</td>
      <td>LAN / Target Server Access</td>
      <td>Evaluated via <code>/etc/nftables/acl.nft</code></td>
    </tr>
  </tbody>
</table>

<h1>8. Operational & Maintenance Cheatsheet</h1>

<h2>1. Container & Process Operations</h2>
<div class="code-block"><span class="code-comment"># Check container live logs</span>
<span class="code-cmd">docker logs -f --tail 50 wireguard-manager</span>

<span class="code-comment"># Restart application container with zero kernel disruption</span>
<span class="code-cmd">sudo docker restart wireguard-manager</span>

<span class="code-comment"># Execute an interactive shell inside the container</span>
<span class="code-cmd">docker exec -it wireguard-manager bash</span></div>

<h2>2. WireGuard Kernel State Inspection</h2>
<div class="code-block"><span class="code-comment"># Inspect live handshakes, endpoints, and Rx/Tx counters</span>
<span class="code-cmd">sudo wg show wg0</span>

<span class="code-comment"># Check virtual network interface details</span>
<span class="code-cmd">ip -s addr show wg0</span>
<span class="code-cmd">ip route show dev wg0</span>

<span class="code-comment"># Re-sync server config without tearing down tunnel</span>
<span class="code-cmd">sudo wg syncconf wg0 &lt;(sudo wg-quick strip /etc/wireguard/wg0.conf)</span></div>

<h2>3. Firewall & ACL Management</h2>
<div class="code-block"><span class="code-comment"># List live rules in the active kernel table</span>
<span class="code-cmd">sudo nft list ruleset</span>

<span class="code-comment"># Specifically view client ACL chain rules</span>
<span class="code-cmd">sudo nft list chain inet filter vpn_acl</span>

<span class="code-comment"># Manually validate and reload firewall rules</span>
<span class="code-cmd">sudo nft -c -f /etc/nftables.conf && sudo nft -f /etc/nftables.conf</span></div>

<h2>4. Backup & Disaster Recovery</h2>
<div class="code-block"><span class="code-comment"># 1. Immediate SQLite Database Backup</span>
<span class="code-cmd">sudo cp /opt/wireguard-enterprise/data/wireguard.db /opt/wireguard-enterprise/data/wireguard_backup_$(date +%Y%m%d%H%M%S).db</span>

<span class="code-comment"># 2. Archive Current WireGuard Configuration</span>
<span class="code-cmd">sudo cp /etc/wireguard/wg0.conf /etc/wireguard/archive/wg0_backup_$(date +%Y%m%d%H%M%S).conf</span>

<span class="code-comment"># 3. Archive Firewall Configuration</span>
<span class="code-cmd">sudo cp /etc/nftables/acl.nft /etc/wireguard/archive/acl_backup_$(date +%Y%m%d%H%M%S).nft</span></div>

<div class="card card-accent no-break" style="margin-top: 8px;">
  <div class="card-title">Production Support & Compliance Note</div>
  <p style="font-size: 7.5pt; margin: 0; color: #475569;">
    All cryptographic peer identities are stored in <code>/opt/wireguard-enterprise/data/wireguard.db</code> with client private keys encrypted using PBKDF2 AES-GCM primitives. The in-tree WireGuard data plane preserves active connections across container restarts. For troubleshooting, inspect <code>dmesg | grep wireguard</code> or contact the infrastructure administrator.
  </p>
</div>

</body>
</html>
"""

def generate_pdf():
    print(f"Writing intermediate HTML to {HTML_PATH}...")
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)

    print(f"Compiling PDF via Headless Chromium...")
    cmd = [
        "google-chrome-stable",
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={PDF_PATH}",
        HTML_PATH
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Error generating PDF: {res.stderr}")
        sys.exit(1)

    if os.path.exists(PDF_PATH):
        size_kb = os.path.getsize(PDF_PATH) / 1024
        print(f"✓ PDF successfully created: {PDF_PATH} ({size_kb:.1f} KB)")
    else:
        print("✗ PDF file was not created.")
        sys.exit(1)

if __name__ == "__main__":
    generate_pdf()
