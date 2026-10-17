#!/usr/bin/env python3
"""
Generate the Raspberry Pi Central TV Streaming Server Installation Guide PDF.
Strict rules:
- Zero emojis.
- Clean typography and layout with embedded CiSAI logo.
- Comprehensive step-by-step guide for Ubuntu 24.04 on Raspberry Pi 4/5.
- Print-optimized CSS for multi-page A4.
"""

import base64
import os
import subprocess
import sys

def main():
    workspace_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    logo_path = os.path.join(workspace_dir, "public", "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
    else:
        logo_b64 = ""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Raspberry Pi Central TV Streaming Server Installation Guide - CiSAI</title>
<style>
  @page {{
    size: A4;
    margin: 12mm 14mm 12mm 14mm;
  }}

  * {{
    box-sizing: border-box;
    -webkit-print-color-adjust: exact !important;
    print-color-adjust: exact !important;
  }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    background-color: #ffffff;
    line-height: 1.5;
    font-size: 10.5px;
    margin: 0;
    padding: 0;
  }}

  .header-container {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 8px;
    margin-bottom: 12px;
  }}

  .header-brand {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .header-logo {{
    height: 42px;
    width: auto;
    object-fit: contain;
  }}

  .header-title-box {{
    display: flex;
    flex-direction: column;
  }}

  .org-tag {{
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #2563eb;
  }}

  .main-title {{
    font-size: 16px;
    font-weight: 800;
    color: #0f172a;
    margin: 0;
    line-height: 1.2;
  }}

  .header-meta {{
    text-align: right;
    font-size: 8.5px;
    color: #64748b;
  }}

  .meta-tag {{
    display: inline-block;
    padding: 2px 7px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 4px;
    color: #1e40af;
    font-weight: 600;
    margin-bottom: 3px;
  }}

  h2 {{
    font-size: 13px;
    font-weight: 700;
    color: #0f172a;
    border-left: 3.5px solid #2563eb;
    padding-left: 8px;
    margin: 14px 0 6px 0;
    page-break-after: avoid;
  }}

  h3 {{
    font-size: 11px;
    font-weight: 700;
    color: #1e3a8a;
    margin: 10px 0 4px 0;
    page-break-after: avoid;
  }}

  p {{
    margin: 0 0 6px 0;
    color: #334155;
  }}

  ul, ol {{
    margin: 0 0 8px 0;
    padding-left: 20px;
    color: #334155;
  }}

  li {{
    margin-bottom: 3px;
  }}

  code {{
    font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
    font-size: 9.5px;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1px 4px;
    border-radius: 3px;
    border: 1px solid #e2e8f0;
  }}

  pre {{
    font-family: ui-monospace, "SFMono-Regular", Menlo, Monaco, Consolas, monospace;
    font-size: 9px;
    background-color: #0f172a;
    color: #e2e8f0;
    padding: 7px 10px;
    border-radius: 5px;
    overflow-x: auto;
    margin: 5px 0 8px 0;
    line-height: 1.4;
    page-break-inside: avoid;
    border: 1px solid #1e293b;
  }}

  pre .cmd {{
    color: #38bdf8;
    font-weight: 600;
  }}

  pre .arg {{
    color: #facc15;
  }}

  pre .comment {{
    color: #94a3b8;
    font-style: italic;
  }}

  .card {{
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 5px;
    padding: 8px 11px;
    margin-bottom: 8px;
    page-break-inside: avoid;
  }}

  .card-header {{
    font-weight: 700;
    font-size: 11px;
    color: #0f172a;
    margin-bottom: 5px;
  }}

  .alert-info {{
    background-color: #eff6ff;
    border-left: 3.5px solid #2563eb;
    border-top: 1px solid #dbeafe;
    border-right: 1px solid #dbeafe;
    border-bottom: 1px solid #dbeafe;
    border-radius: 4px;
    padding: 7px 10px;
    margin-bottom: 8px;
    page-break-inside: avoid;
  }}

  .alert-success {{
    background-color: #f0fdf4;
    border-left: 3.5px solid #16a34a;
    border-top: 1px solid #dcfce7;
    border-right: 1px solid #dcfce7;
    border-bottom: 1px solid #dcfce7;
    border-radius: 4px;
    padding: 7px 10px;
    margin-bottom: 8px;
    page-break-inside: avoid;
  }}

  .alert-warn {{
    background-color: #fffbeb;
    border-left: 3.5px solid #f59e0b;
    border-top: 1px solid #fef3c7;
    border-right: 1px solid #fef3c7;
    border-bottom: 1px solid #fef3c7;
    border-radius: 4px;
    padding: 7px 10px;
    margin-bottom: 8px;
    page-break-inside: avoid;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 6px 0 10px 0;
    font-size: 9.5px;
    page-break-inside: avoid;
  }}

  th, td {{
    padding: 5px 8px;
    text-align: left;
    border: 1px solid #cbd5e1;
  }}

  th {{
    background-color: #f1f5f9;
    font-weight: 700;
    color: #0f172a;
  }}

  tr:nth-child(even) td {{
    background-color: #f8fafc;
  }}

  .grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 9px;
    margin-bottom: 8px;
    page-break-inside: avoid;
  }}

  .footer-note {{
    margin-top: 14px;
    text-align: center;
    font-size: 8px;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    padding-top: 6px;
  }}
</style>
</head>
<body>

  <!-- Header -->
  <div class="header-container">
    <div class="header-brand">
      {'<img src="data:image/png;base64,' + logo_b64 + '" class="header-logo" alt="CiSAI Logo">' if logo_b64 else ''}
      <div class="header-title-box">
        <span class="org-tag">Centre for Innovation & Systems AI</span>
        <h1 class="main-title">Raspberry Pi Server Installation & Operations Guide</h1>
      </div>
    </div>
    <div class="header-meta">
      <div class="meta-tag">Production Reference: Pi-4/5 LTS</div><br>
      Target OS: Ubuntu 24.04 LTS (64-bit)<br>
      Host IP: <YOUR_PI_IP> &bull; Port: 8080 / 8443
    </div>
  </div>

  <!-- Section 1 -->
  <h2>1. Overview and Architecture</h2>
  <p>
    This document outlines the complete deployment procedure for running the <strong>Central TV Streaming & Signage Hub Server</strong> directly on a Raspberry Pi host. Once deployed, administrative personnel and operators can access the central control portal from any laptop on the corporate network without installing local client software.
  </p>

  <div class="grid-2">
    <div class="card">
      <div class="card-header">Core Server Responsibilities</div>
      <ul>
        <li><strong>Web Application Portal:</strong> Serves responsive Admin Console, Executive Dashboard, and Presenter interfaces via HTTP/HTTPS.</li>
        <li><strong>Device Fleet Registry:</strong> Manages real-time bidirectional WebSocket connections with all connected TV endpoints.</li>
        <li><strong>Media Library Manager:</strong> Stores and delivers 1080p/4K signage videos with dual-buffer seamless looping.</li>
      </ul>
    </div>
    <div class="card">
      <div class="card-header">MediaMTX Live Streaming Engine</div>
      <ul>
        <li><strong>WebRTC (WHEP/WHIP):</strong> Sub-300ms ultra-low latency real-time screen sharing and camera broadcast.</li>
        <li><strong>HLS Server:</strong> Low-latency segmented streaming fallback for legacy browser players.</li>
        <li><strong>RTSP / RTMP Ingest:</strong> Ingestion points for OBS Studio, hardware encoders, and IP security cameras.</li>
      </ul>
    </div>
  </div>

  <!-- Section 2 -->
  <h2>2. Hardware & Operating System Prerequisites</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 25%;">Component</th>
        <th style="width: 35%;">Recommended Specification</th>
        <th style="width: 40%;">Verified Target Environment</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Hardware Platform</strong></td>
        <td>Raspberry Pi 5 (8GB) or Pi 4 Model B (4GB/8GB)</td>
        <td>Raspberry Pi 4 / 5 (8GB RAM, aarch64)</td>
      </tr>
      <tr>
        <td><strong>Operating System</strong></td>
        <td>Ubuntu Server 24.04 LTS Noble Numbat (64-bit)</td>
        <td>Ubuntu 24.04.5 LTS (Kernel 6.8.0-1064-raspi)</td>
      </tr>
      <tr>
        <td><strong>Storage</strong></td>
        <td>Class 10 A2 MicroSD or M.2 NVMe SSD (32GB+)</td>
        <td>32GB High-Speed Storage (23GB Free)</td>
      </tr>
      <tr>
        <td><strong>Network</strong></td>
        <td>Gigabit Ethernet (Static IP Recommended)</td>
        <td>Ethernet Interface: <code><YOUR_PI_IP></code></td>
      </tr>
      <tr>
        <td><strong>Power Supply</strong></td>
        <td>Official 27W USB-C Power Adapter (Pi 5) / 15W (Pi 4)</td>
        <td>Stable regulated power line</td>
      </tr>
    </tbody>
  </table>

  <!-- Section 3 -->
  <h2>3. Step-by-Step Installation Procedure</h2>

  <h3>3.1 Initial System Updates and Core Package Installation</h3>
  <p>Connect to the Raspberry Pi over SSH and install the required runtimes, build tools, and FFmpeg:</p>
  <pre><span class="comment"># Connect to Raspberry Pi</span>
<span class="cmd">ssh</span> ubuntu@<YOUR_PI_IP>

<span class="comment"># Update package repositories and install runtimes</span>
<span class="cmd">sudo apt update</span> &amp;&amp; <span class="cmd">sudo apt install</span> -y \
  nodejs npm ffmpeg rsync curl jq build-essential</pre>

  <p>Verify that Node.js (v18+ LTS) and FFmpeg are correctly installed:</p>
  <pre><span class="cmd">node</span> -v     <span class="comment"># Output: v18.19.1 or higher</span>
<span class="cmd">npm</span> -v      <span class="comment"># Output: 9.2.0 or higher</span>
<span class="cmd">ffmpeg</span> -version | <span class="cmd">head</span> -n 1</pre>

  <h3>3.2 Application Directory Setup & File Synchronization</h3>
  <p>Create the designated application root at <code>/opt/central-tv-streaming</code> and configure correct ownership:</p>
  <pre><span class="cmd">sudo mkdir</span> -p /opt/central-tv-streaming
<span class="cmd">sudo chown</span> -R ubuntu:ubuntu /opt/central-tv-streaming</pre>

  <p>From your workstation, synchronize the server codebase, assets, and media repository using <code>rsync</code>:</p>
  <pre><span class="comment"># Execute from your development workstation</span>
<span class="cmd">rsync</span> -avz --exclude '.git' --exclude 'yt-dlp' --exclude 'media_4k_backup' \
  ./central-tv-streaming/ ubuntu@<YOUR_PI_IP>:/opt/central-tv-streaming/</pre>

  <p>Install production Node.js dependencies on the Raspberry Pi:</p>
  <pre><span class="cmd">cd</span> /opt/central-tv-streaming
<span class="cmd">npm install</span> --omit=dev</pre>

  <div class="alert-info">
    <strong>Included Runtime Modules:</strong> <code>express</code> (v5 web framework), <code>ws</code> (high-concurrency WebSocket engine), <code>multer</code> (chunked media upload handler), and <code>cookie-parser</code> (session authentication security).
  </div>

  <!-- Section 4 -->
  <h2>4. MediaMTX Streaming Engine Setup</h2>
  <p>
    MediaMTX is deployed as a standalone native ARM64 binary to avoid container virtualization overhead and ensure hardware-accelerated socket throughput on the Pi:
  </p>

  <pre><span class="comment"># Download native ARM64 release binary directly on the Pi</span>
<span class="cmd">curl</span> -sL https://github.com/bluenviron/mediamtx/releases/download/v1.9.0/mediamtx_v1.9.0_linux_arm64v8.tar.gz | \
  <span class="cmd">tar</span> -xz -C /opt/central-tv-streaming/ mediamtx

<span class="cmd">chmod</span> +x /opt/central-tv-streaming/mediamtx</pre>

  <p>Ensure the configuration file at <code>/opt/central-tv-streaming/mediamtx.yml</code> contains verified settings:</p>
  <pre><span class="comment"># /opt/central-tv-streaming/mediamtx.yml</span>
logLevel: info
logDestinations: [stdout]

api: yes
apiAddress: :9997

rtsp: yes
rtspAddress: :8554
protocols: [udp, multicast, tcp]

rtmp: yes
rtmpAddress: :1935

hls: yes
hlsAddress: :8888
hlsSegmentCount: 7
hlsSegmentDuration: 1s
hlsPartDuration: 200ms

webrtc: yes
webrtcAddress: :8889
webrtcEncryption: no
webrtcAllowOrigin: "*"
webrtcLocalUDPAddress: :8189
webrtcIPsFromInterfaces: yes
webrtcHandshakeTimeout: 10s

paths:
  all:</pre>

  <!-- Section 5 -->
  <h2>5. Systemd Daemon Configuration & Auto-Boot</h2>
  <p>
    To ensure high availability and automatic recovery following power outages or network reboots, two systemd services are created:
  </p>

  <h3>5.1 MediaMTX Service: <code>/etc/systemd/system/mediamtx.service</code></h3>
  <pre>[Unit]
Description=MediaMTX Streaming Core (RTSP, RTMP, WebRTC, HLS)
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/central-tv-streaming
ExecStart=/opt/central-tv-streaming/mediamtx /opt/central-tv-streaming/mediamtx.yml
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target</pre>

  <h3>5.2 Central TV Server Service: <code>/etc/systemd/system/central-tv-server.service</code></h3>
  <pre>[Unit]
Description=CiSAI Central TV Streaming & Signage Hub Server
After=network.target network-online.target mediamtx.service
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/central-tv-streaming
ExecStart=/usr/bin/node server.js
Restart=always
RestartSec=3
Environment=NODE_ENV=production
Environment=HTTP_PORT=8080
Environment=HTTPS_PORT=8443
Environment=MEDIAMTX_HOST=127.0.0.1
Environment=MEDIAMTX_WEBRTC_PORT=8889
Environment=MEDIAMTX_HLS_PORT=8888
Environment=ADMIN_USER=admin
Environment=ADMIN_PASSWORD=admin123
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target</pre>

  <h3>5.3 Enabling and Launching Services</h3>
  <pre><span class="cmd">sudo systemctl</span> daemon-reload
<span class="cmd">sudo systemctl</span> enable --now mediamtx.service
<span class="cmd">sudo systemctl</span> enable --now central-tv-server.service</pre>

  <!-- Section 6 -->
  <h2>6. Verification & Network Access from Laptops</h2>
  <p>
    Once started, the central server is accessible over the local network. Open any web browser on your connected laptop and navigate to the following endpoints:
  </p>

  <table>
    <thead>
      <tr>
        <th style="width: 25%;">Portal Interface</th>
        <th style="width: 45%;">Network URL</th>
        <th style="width: 30%;">Purpose & Usage</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Admin Control Console</strong></td>
        <td><code>http://<YOUR_PI_IP>:8080/admin.html</code></td>
        <td>Fleet control, media playlist management, channel switching, TV reboot</td>
      </tr>
      <tr>
        <td><strong>Executive Dashboard</strong></td>
        <td><code>http://<YOUR_PI_IP>:8080/dashboard.html</code></td>
        <td>Multi-screen live operations monitoring & telemetry</td>
      </tr>
      <tr>
        <td><strong>Live Presenter / Screen Cast</strong></td>
        <td><code>http://<YOUR_PI_IP>:8080/presenter.html</code></td>
        <td>Real-time screen broadcasting & microphone streaming</td>
      </tr>
      <tr>
        <td><strong>TV Player Endpoint</strong></td>
        <td><code>http://<YOUR_PI_IP>:8080/player.html?name=TV1&site=HQ</code></td>
        <td>Display screen client player with seamless loop engine</td>
      </tr>
      <tr>
        <td><strong>Encrypted HTTPS Portal</strong></td>
        <td><code>https://<YOUR_PI_IP>:8443</code></td>
        <td>Secure TLS encrypted management access</td>
      </tr>
    </tbody>
  </table>

  <div class="card" style="margin-top: 10px;">
    <div class="card-header">Role-Based Access Control (RBAC) Accounts</div>
    <table>
      <thead>
        <tr>
          <th>Role</th>
          <th>Username</th>
          <th>Password</th>
          <th>Permitted Operations</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Administrator</strong></td>
          <td><code>admin</code></td>
          <td><code>admin123</code></td>
          <td>Full system control, device fleet discovery, TV deletion, alerts, channel setup</td>
        </tr>
        <tr>
          <td><strong>Streamer / Operator</strong></td>
          <td><code>streamer</code></td>
          <td><code>streamer123</code></td>
          <td>Upload videos to loop, live presenter screen/camera stream, TV sync & override</td>
        </tr>
      </tbody>
    </table>
    <div style="font-size: 8.5px; color: #64748b; margin-top: 4px;">
      <em>Credentials can be configured via environment variables <code>ADMIN_USER</code>, <code>ADMIN_PASSWORD</code>, <code>STREAMER_USER</code>, <code>STREAMER_PASSWORD</code> in systemd or via <code>data/users.json</code>.</em>
    </div>
  </div>

  <!-- Section 6.1: Dual-NIC Network Configuration -->
  <h3>6.1 Dual-Interface Network Configuration (Netplan)</h3>
  <p>
    Production Raspberry Pi hubs utilize dual network interfaces to segregate internet/egress streaming traffic from the internal TV management VLAN:
  </p>
  <table>
    <thead>
      <tr>
        <th style="width: 25%;">Interface</th>
        <th style="width: 25%;">IP / Netmask</th>
        <th style="width: 25%;">Gateway & Metric</th>
        <th style="width: 25%;">DNS Nameservers</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>eth0</strong> (Built-in Port)</td>
        <td><code>10.31.93.5/23</code> (255.255.254.0)</td>
        <td><code>10.31.93.2</code> (Metric: 100)</td>
        <td><code>8.8.8.8</code></td>
      </tr>
      <tr>
        <td><strong>enx...</strong> (USB Adapter)</td>
        <td><code>10.31.1.190/23</code> (255.255.254.0)</td>
        <td><code>10.31.0.1</code> (Metric: 200)</td>
        <td><code>10.31.4.1</code>, <code>10.31.4.3</code></td>
      </tr>
    </tbody>
  </table>

  <p>Verified Netplan configuration file (<code>/etc/netplan/50-cloud-init.yaml</code>):</p>
  <pre><span class="comment"># /etc/netplan/50-cloud-init.yaml</span>
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: false
      addresses:
        - 10.31.93.5/23
      routes:
        - to: default
          via: 10.31.93.2
          metric: 100
      nameservers:
        addresses:
          - 8.8.8.8
    enx207bd28aa480:
      match:
        macaddress: 20:7b:d2:8a:a4:80
      set-name: enx207bd28aa480
      dhcp4: false
      addresses:
        - 10.31.1.190/23
      routes:
        - to: default
          via: 10.31.0.1
          metric: 200
      nameservers:
        addresses:
          - 10.31.4.1
          - 10.31.4.3</pre>

  <p>Apply changes with: <code>sudo netplan apply</code></p>

  <!-- Section 7 -->
  <h2>7. Operations, Maintenance & Troubleshooting</h2>

  <div class="grid-2">
    <div class="card">
      <div class="card-header">Service Health Check Commands</div>
      <pre><span class="comment"># Check server status</span>
<span class="cmd">systemctl status</span> central-tv-server.service

<span class="comment"># Check streaming engine</span>
<span class="cmd">systemctl status</span> mediamtx.service

<span class="comment"># Inspect live application logs</span>
<span class="cmd">sudo journalctl</span> -u central-tv-server.service -f</pre>
    </div>
    <div class="card">
      <div class="card-header">System Resource Verification</div>
      <pre><span class="comment"># Check RAM usage (Under 600MB typical)</span>
<span class="cmd">free</span> -h

<span class="comment"># Check disk space</span>
<span class="cmd">df</span> -h /

<span class="comment"># Check CPU temperature</span>
<span class="cmd">cat</span> /sys/class/thermal/thermal_zone0/temp</pre>
    </div>
  </div>

  <div class="card">
    <div class="card-header">Port Allocation Reference</div>
    <table>
      <thead>
        <tr>
          <th>Port</th>
          <th>Protocol</th>
          <th>Service</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>8080</code></td>
          <td>TCP</td>
          <td>Node.js Express / WebSocket</td>
          <td>HTTP Web Console, Device WebSocket API, Media streaming</td>
        </tr>
        <tr>
          <td><code>8443</code></td>
          <td>TCP</td>
          <td>Node.js HTTPS</td>
          <td>Secure TLS Web Console</td>
        </tr>
        <tr>
          <td><code>8889</code></td>
          <td>TCP</td>
          <td>MediaMTX WebRTC</td>
          <td>WebRTC HTTP Signaling (WHIP/WHEP)</td>
        </tr>
        <tr>
          <td><code>8189</code></td>
          <td>UDP</td>
          <td>MediaMTX ICE</td>
          <td>WebRTC Low-Latency Video Packets</td>
        </tr>
        <tr>
          <td><code>8888</code></td>
          <td>TCP</td>
          <td>MediaMTX HLS</td>
          <td>HTTP Live Streaming segmented video</td>
        </tr>
        <tr>
          <td><code>8554</code></td>
          <td>TCP/UDP</td>
          <td>MediaMTX RTSP</td>
          <td>RTSP video feed ingestion</td>
        </tr>
        <tr>
          <td><code>1935</code></td>
          <td>TCP</td>
          <td>MediaMTX RTMP</td>
          <td>RTMP video ingestion for OBS Studio</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="footer-note">
    <strong>CiSAI - Centre for Innovation & Systems AI</strong> &bull; Raspberry Pi Server Installation Specification &bull; 2026
  </div>

</body>
</html>
"""

    output_dir = os.path.join(workspace_dir, "documentation-and-pdfs")
    os.makedirs(output_dir, exist_ok=True)
    output_html = os.path.join(output_dir, "pi_server_installation_guide.html")
    output_pdf = os.path.join(output_dir, "Raspberry_Pi_Server_Installation_Guide.pdf")

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML: {output_html}")

    chrome_cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output_pdf}",
        output_html
    ]
    print("Compiling to PDF with Google Chrome...")
    res = subprocess.run(chrome_cmd, capture_output=True, text=True)
    if res.returncode == 0:
        size = os.path.getsize(output_pdf)
        print(f"SUCCESS: Generated {output_pdf} (Size: {size:,} bytes)")
        
        # Also copy to production-installation-packages
        prod_pkg_dir = os.path.join(workspace_dir, "production-installation-packages")
        os.makedirs(prod_pkg_dir, exist_ok=True)
        dest_pdf = os.path.join(prod_pkg_dir, "Raspberry_Pi_Server_Installation_Guide.pdf")
        with open(output_pdf, "rb") as src, open(dest_pdf, "wb") as dst:
            dst.write(src.read())
        print(f"Copied to: {dest_pdf}")
    else:
        print(f"ERROR: {res.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()
