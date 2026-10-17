#!/usr/bin/env python3
"""
Generate the Raspberry Pi Production Implementation Specification PDF.
Strict rules:
- Zero emojis.
- Clean vector layout and embedded CiSAI logo.
- Print-optimized CSS for multi-page A4.
"""

import base64
import os
import subprocess
import sys

def main():
    logo_path = os.path.join(os.path.dirname(__file__), "public", "logo.png")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
    else:
        logo_b64 = ""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Raspberry Pi Production Implementation Specification - CiSAI Central TV Streaming</title>
<style>
  @page {{
    size: A4;
    margin: 14mm 14mm 14mm 14mm;
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
    font-size: 11px;
    margin: 0;
    padding: 0;
  }}

  .header-container {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 10px;
    margin-bottom: 14px;
  }}

  .header-brand {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}

  .header-logo {{
    height: 44px;
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
    font-size: 17px;
    font-weight: 800;
    color: #0f172a;
    margin: 0;
    line-height: 1.2;
  }}

  .header-meta {{
    text-align: right;
    font-size: 9px;
    color: #64748b;
  }}

  .meta-tag {{
    display: inline-block;
    padding: 2px 7px;
    border-radius: 4px;
    background: #eff6ff;
    color: #1d4ed8;
    font-weight: 700;
    font-size: 8.5px;
    margin-bottom: 3px;
    border: 1px solid #bfdbfe;
  }}

  h2 {{
    font-size: 13.5px;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    margin-top: 16px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }}

  h3 {{
    font-size: 12px;
    font-weight: 700;
    color: #1e3a8a;
    margin-top: 10px;
    margin-bottom: 4px;
  }}

  p {{
    margin: 0 0 6px 0;
    color: #334155;
    text-align: justify;
  }}

  ul, ol {{
    margin: 0 0 8px 0;
    padding-left: 18px;
    color: #334155;
  }}

  li {{
    margin-bottom: 3px;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 10px 0;
    font-size: 9.5px;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
  }}

  th, td {{
    padding: 5px 7px;
    text-align: left;
    border: 1px solid #cbd5e1;
    vertical-align: top;
  }}

  th {{
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
    text-transform: uppercase;
    font-size: 8.5px;
    letter-spacing: 0.03em;
  }}

  tr:nth-child(even) td {{
    background-color: #f8fafc;
  }}

  .grid-2 {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin: 8px 0;
  }}

  .card {{
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 8px 10px;
    background: #ffffff;
  }}

  .card-header {{
    font-weight: 700;
    font-size: 10.5px;
    color: #0f172a;
    margin-bottom: 4px;
    border-bottom: 1px solid #f1f5f9;
    padding-bottom: 3px;
  }}

  .card-body {{
    font-size: 9.5px;
    color: #475569;
    line-height: 1.4;
  }}

  code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 9px;
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1px 4px;
    border-radius: 3px;
    border: 1px solid #e2e8f0;
  }}

  pre {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 8.5px;
    background-color: #0f172a;
    color: #f8fafc;
    padding: 7px 9px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 5px 0;
    line-height: 1.35;
  }}

  .diagram-container {{
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 8px;
    margin: 8px 0;
    text-align: center;
  }}

  .diagram-caption {{
    font-size: 8.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #64748b;
    margin-top: 5px;
  }}

  .page-break {{
    page-break-before: always;
    break-before: page;
  }}

  .no-break {{
    page-break-inside: avoid;
    break-inside: avoid;
  }}
</style>
</head>
<body>

  <!-- ==================== PAGE 1 ==================== -->
  <div class="header-container">
    <div class="header-brand">
      <img src="data:image/png;base64,{logo_b64}" class="header-logo" alt="CiSAI Logo">
      <div class="header-title-box">
        <span class="org-tag">Centre for Innovation & Systems AI (CiSAI)</span>
        <h1 class="main-title">Raspberry Pi Production Implementation Specification</h1>
      </div>
    </div>
    <div class="header-meta">
      <div class="meta-tag">Hardware & OS Runbook</div>
      <div>Doc Ref: CiSAI-ENG-RPI-PROD-2026-V1</div>
      <div>Target Hardware: Raspberry Pi 5 / Pi 4B</div>
      <div>OS: Ubuntu 24.04 LTS / RPi OS 64-bit</div>
    </div>
  </div>

  <h2>1. Overview & Dual Operational Roles</h2>
  <p>
    This document defines the production engineering requirements for migrating the <strong>CiSAI Central TV Streaming Platform</strong> to Raspberry Pi single-board computers (SBC). The Raspberry Pi can be deployed in two distinct enterprise roles:
  </p>

  <div class="grid-2">
    <div class="card">
      <div class="card-header">Role A: TV Display Kiosk Receiver (Client)</div>
      <div class="card-body">
        <ul>
          <li>Mounted behind any commercial or non-smart TV via HDMI.</li>
          <li>Boots automatically into full-screen, hardware-accelerated Chromium kiosk.</li>
          <li>Autonomously plays 24/7 continuous video loops, sub-second live WebRTC streams, and emergency alert banners.</li>
          <li>Zero human maintenance required; recovers automatically from power outages.</li>
        </ul>
      </div>
    </div>
    <div class="card">
      <div class="card-header">Role B: Branch Edge Server / Relay (Host)</div>
      <div class="card-body">
        <ul>
          <li>Deploys Docker Compose stack (Node.js Controller + MediaMTX).</li>
          <li>Acts as a lightweight central streaming controller for up to 30 TV screens.</li>
          <li>Acts as a Branch Edge Relay for remote offices (e.g., Delhi branch), downloading 1 stream from Headquarters and distributing it locally over branch LAN.</li>
        </ul>
      </div>
    </div>
  </div>

  <h2>2. Hardware Bill of Materials (BOM) & Prerequisites</h2>
  <p>
    In 24/7 enterprise production, consumer power bricks and budget MicroSD cards are the primary causes of hardware failure. Adhere strictly to these production specifications:
  </p>

  <table>
    <thead>
      <tr>
        <th style="width: 20%;">Component</th>
        <th style="width: 32%;">Recommended Production Spec</th>
        <th style="width: 48%;">Engineering Justification</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Single Board Computer</strong></td>
        <td><strong>Raspberry Pi 5 (8GB RAM)</strong><br>(Pi 4B 4GB accepted for 1080p only)</td>
        <td>Pi 5 features VideoCore VII GPU supporting dual 4K 60FPS HEVC/H.264 hardware decoding and 2.5x higher CPU throughput.</td>
      </tr>
      <tr>
        <td><strong>Power Supply Unit (PSU)</strong></td>
        <td><strong>Official Raspberry Pi 27W USB-C</strong><br>(5.1V / 5.0A Power Delivery)</td>
        <td>Under-voltage drops trigger Wi-Fi card resets and kernel throttling. Standard 15W phone chargers are strictly prohibited.</td>
      </tr>
      <tr>
        <td><strong>Storage Drive</strong></td>
        <td><strong>M.2 NVMe SSD via PCIe HAT+</strong><br>(128GB or 256GB PCIe Gen 2/3)</td>
        <td>MicroSD cards suffer flash memory degradation and filesystem corruption from sudden power cutoffs. NVMe SSD provides 500+ MB/s and 10+ year endurance.</td>
      </tr>
      <tr>
        <td><strong>Thermal Solution</strong></td>
        <td><strong>Official Active Cooler</strong><br>(Aluminum heatsink + PWM blower)</td>
        <td>Prevents thermal throttling, which triggers at 80°C and reduces video frame rates. Maintains board below 55°C under continuous 4K load.</td>
      </tr>
      <tr>
        <td><strong>Display Connectivity</strong></td>
        <td><strong>Micro-HDMI to HDMI 2.0 Premium</strong><br>(Triple shielded, 4K 60Hz rated)</td>
        <td>Ensures clean digital signal transmission and bidirectional HDMI-CEC signaling for automated TV power scheduling.</td>
      </tr>
      <tr>
        <td><strong>Network Interface</strong></td>
        <td><strong>Gigabit Ethernet (CAT6)</strong><br>Optional: PoE+ HAT (Power over Ethernet)</td>
        <td>Eliminates wireless radio interference and allows powering the entire display board directly through the network switch.</td>
      </tr>
    </tbody>
  </table>

  <!-- ==================== PAGE 2 ==================== -->
  <div class="page-break"></div>

  <h2>3. Operating System Architecture: Ubuntu vs. Raspberry Pi OS</h2>

  <table>
    <thead>
      <tr>
        <th style="width: 22%;">Evaluation Metric</th>
        <th style="width: 38%;">Ubuntu 24.04 LTS Desktop (64-bit)</th>
        <th style="width: 40%;">Raspberry Pi OS 64-bit (Debian Bookworm)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Display Kiosk Role</strong></td>
        <td>Good. GNOME desktop requires ~800MB RAM idle.</td>
        <td><strong>Optimal.</strong> Lightweight labwc/Wayfire uses &lt;220MB RAM, leaving maximum memory for 4K video decoders.</td>
      </tr>
      <tr>
        <td><strong>Server & Docker Role</strong></td>
        <td><strong>Optimal.</strong> Industry-standard Canonical enterprise support, standardized kernel, and automated security patch channels.</td>
        <td>Supported. Requires standard Debian Docker repositories.</td>
      </tr>
      <tr>
        <td><strong>Boot Speed to Kiosk</strong></td>
        <td>Approx. 28-35 seconds to launch browser.</td>
        <td><strong>Fast.</strong> 12-16 seconds cold boot directly into full-screen video.</td>
      </tr>
      <tr>
        <td><strong>Hardware Acceleration</strong></td>
        <td>Mesa V3D driver enabled.</td>
        <td>Native Broadcom firmware tuning included by default.</td>
      </tr>
    </tbody>
  </table>

  <h2>4. TV Display Kiosk Setup Runbook (Step-by-Step)</h2>

  <h3>4.1 OS Installation & Base Provisioning</h3>
  <ol>
    <li>Flash <strong>Raspberry Pi OS (64-bit)</strong> or <strong>Ubuntu Desktop 24.04 LTS</strong> using the official Raspberry Pi Imager.</li>
    <li>In Advanced Options: Set hostname (e.g., <code>tv-boardroom-pi</code>), create standard administrative user, configure Wi-Fi credentials, and enable SSH.</li>
    <li>Boot the board and install core display utilities:
      <pre>sudo apt-get update && sudo apt-get install -y chromium-browser unclutter xdotool cec-utils watchdog</pre>
    </li>
  </ol>

  <h3>4.2 Creating the Autonomous Kiosk Launcher Script</h3>
  <p>Create <code>/opt/start-kiosk.sh</code> to launch Chromium with screen-blanking suppressed and zero-touch autoplay:</p>
  <pre>sudo tee /opt/start-kiosk.sh &gt; /dev/null &lt;&lt; 'EOF'
#!/usr/bin/env bash
# Suppress screen blanking and energy saving DPMS
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor after 0.5s of inactivity
unclutter -idle 0.5 -root &

# Target Server URL (Replace with your Central Server IP)
SERVER_IP="192.168.0.151:8080"
DEVICE_NAME="Pi-Display-1"
SITE="Headquarters"
TARGET_URL="http://${{SERVER_IP}}/player.html?name=${{DEVICE_NAME}}&site=${{SITE}}"

# Launch Chromium in dedicated kiosk mode
exec chromium-browser \\
    --kiosk \\
    --noerrdialogs \\
    --disable-infobars \\
    --disable-session-crashed-bubble \\
    --check-for-update-interval=31536000 \\
    --autoplay-policy=no-user-gesture-required \\
    --enable-features=OverlayScrollbar \\
    --hide-scrollbars \\
    --enable-gpu-rasterization \\
    --ignore-gpu-blocklist \\
    --app="${{TARGET_URL}}"
EOF

sudo chmod +x /opt/start-kiosk.sh</pre>

  <h3>4.3 Configuring Systemd Kiosk Supervisor Daemon</h3>
  <p>Create a systemd unit at <code>/etc/systemd/system/tv-kiosk.service</code> to ensure automatic boot and crash recovery:</p>
  <pre>sudo tee /etc/systemd/system/tv-kiosk.service &gt; /dev/null &lt;&lt; 'EOF'
[Unit]
Description=CiSAI Central TV Kiosk Display Player
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=nishusaini
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/nishusaini/.Xauthority
ExecStart=/opt/start-kiosk.sh
Restart=always
RestartSec=3

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload && sudo systemctl enable tv-kiosk.service</pre>

  <!-- ==================== PAGE 3 ==================== -->
  <div class="page-break"></div>

  <h2>5. Production Hardening & Reliability Engineering</h2>

  <h3>5.1 Hardware Watchdog Timer (Automatic Hang Recovery)</h3>
  <p>
    The Broadcom BCM2712/BCM2711 processor includes a hardware watchdog circuit. If an operating system lockup or memory freeze occurs, the chip automatically power-cycles the board within 15 seconds without human intervention:
  </p>
  <pre># 1. Enable watchdog kernel module
echo "bcm2835_wdt" | sudo tee -a /etc/modules

# 2. Configure watchdog daemon in /etc/watchdog.conf
sudo tee -a /etc/watchdog.conf &gt; /dev/null &lt;&lt; 'EOF'
watchdog-device = /dev/watchdog
watchdog-timeout = 15
max-load-1 = 24
EOF

# 3. Enable and activate service
sudo systemctl enable watchdog && sudo systemctl restart watchdog</pre>

  <h3>5.2 Read-Only Root Filesystem (OverlayFS Protection)</h3>
  <p>
    In physical buildings, televisions are often switched off by master circuit breakers at night. Abrupt power loss corrupts writable filesystems. Enabling OverlayFS solves this permanently:
  </p>
  <ul>
    <li>On <strong>Raspberry Pi OS</strong>: Run <code>sudo raspi-config</code> &rarr; <strong>Performance Options</strong> &rarr; <strong>Overlay File System</strong> &rarr; <strong>Enable</strong>.</li>
    <li>When enabled, the OS mounts the physical disk as read-only. All operating writes occur in temporary RAM. The board can be power-cycled millions of times with zero risk of filesystem corruption.</li>
  </ul>

  <h3>5.3 Automated TV Panel Power Control via HDMI-CEC</h3>
  <p>
    Using <code>cec-client</code>, the Raspberry Pi can send Consumer Electronics Control (CEC) commands directly through the HDMI cable to power commercial TV screens ON in the morning and OFF in the evening, extending display lifespan:
  </p>

  <div class="grid-2">
    <div class="card">
      <div class="card-header">Manual CEC Commands</div>
      <div class="card-body">
        <code>echo 'on 0' | cec-client -s -d 1</code> (Power ON TV)<br><br>
        <code>echo 'standby 0' | cec-client -s -d 1</code> (Power OFF TV)
      </div>
    </div>
    <div class="card">
      <div class="card-header">Automated Schedule (Crontab)</div>
      <div class="card-body">
        <code>0 8 * * 1-5 echo 'on 0' | cec-client -s -d 1</code> (08:00 AM ON)<br><br>
        <code>0 20 * * 1-5 echo 'standby 0' | cec-client -s -d 1</code> (08:00 PM OFF)
      </div>
    </div>
  </div>

  <h3>5.4 Disabling Wi-Fi Power Saving Mode</h3>
  <p>
    By default, Linux Wi-Fi drivers put the wireless radio into low-power sleep mode during packet lulls, causing streaming latency spikes. Disable power saving permanently:
  </p>
  <pre>sudo iw dev wlan0 set power_save off</pre>

  <h2>6. Production Deployment Summary</h2>
  <div class="card">
    <div class="card-header">Pre-Flight Production Checklist</div>
    <div class="card-body">
      1. Official 27W Power Supply connected (zero under-voltage warnings in <code>dmesg</code>).<br>
      2. M.2 NVMe SSD installed and verified with <code>lsblk</code>.<br>
      3. Active Cooler fan spinning smoothly below 55°C (<code>vcgencmd measure_temp</code>).<br>
      4. Auto-boot kiosk systemd service active (<code>systemctl status tv-kiosk.service</code>).<br>
      5. Broadcom hardware watchdog armed (<code>systemctl status watchdog</code>).<br>
      6. OverlayFS read-only root enabled for abrupt power cut immunity.
    </div>
  </div>

  <div style="margin-top: 18px; text-align: center; font-size: 8.5px; color: #64748b;">
    <strong>CiSAI - Centre for Innovation & Systems AI</strong> &bull; Raspberry Pi Production Specification &bull; 2026
  </div>

</body>
</html>
"""

    output_html = "pi_production_guide.html"
    output_pdf = "Raspberry_Pi_Production_Implementation_Guide.pdf"

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
    else:
        print(f"ERROR: {res.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()
