#!/usr/bin/env python3
"""
Script to generate the comprehensive, professional CiSAI Production Implementation Runbook PDF.
Strict constraints:
- Zero emojis.
- Professional executive styling with embedded CiSAI logo.
- Comprehensive step-by-step instructions for extracting and running each of the 3 packages.
- Detailed post-dashboard setup instructions and default credentials.
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
<title>CiSAI Central TV Streaming - Production Implementation & Dashboard Operator Runbook</title>
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
    line-height: 1.45;
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
    height: 38px;
    display: block;
  }}

  .header-titles h1 {{
    margin: 0;
    font-size: 17px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.3px;
  }}

  .header-titles p {{
    margin: 2px 0 0 0;
    font-size: 10px;
    color: #64748b;
    font-weight: 500;
  }}

  .header-meta {{
    text-align: right;
    font-size: 9.5px;
    color: #475569;
  }}

  .header-meta strong {{
    color: #0f172a;
  }}

  .page-break {{
    page-break-before: always;
  }}

  h2 {{
    font-size: 13.5px;
    color: #1e3a8a;
    border-bottom: 1.5px solid #cbd5e1;
    padding-bottom: 4px;
    margin-top: 14px;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  h3 {{
    font-size: 11.5px;
    color: #0f172a;
    margin-top: 10px;
    margin-bottom: 4px;
  }}

  p {{
    margin: 0 0 7px 0;
  }}

  /* Callout Boxes */
  .callout {{
    padding: 10px 14px;
    border-radius: 6px;
    margin: 10px 0;
    font-size: 10.5px;
  }}

  .callout-blue {{
    background-color: #eff6ff;
    border-left: 4px solid #3b82f6;
    color: #1e40af;
  }}

  .callout-yellow {{
    background-color: #fefce8;
    border-left: 4px solid #eab308;
    color: #854d0e;
  }}

  .callout-red {{
    background-color: #fef2f2;
    border-left: 4px solid #ef4444;
    color: #991b1b;
  }}

  .callout-green {{
    background-color: #f0fdf4;
    border-left: 4px solid #10b981;
    color: #166534;
  }}

  /* Code Block Styling */
  pre, code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }}

  pre {{
    background-color: #0f172a;
    color: #f8fafc;
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 10px;
    margin: 6px 0 10px 0;
    overflow-x: hidden;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.4;
  }}

  code.inline {{
    background-color: #f1f5f9;
    color: #0f172a;
    padding: 1px 4px;
    border-radius: 4px;
    font-size: 10px;
    border: 1px solid #e2e8f0;
  }}

  /* Tables */
  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px 0;
    font-size: 10px;
  }}

  th, td {{
    border: 1px solid #cbd5e1;
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
  }}

  th {{
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
  }}

  tr:nth-child(even) {{
    background-color: #f8fafc;
  }}

  /* Step Badge */
  .step-number {{
    display: inline-block;
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 700;
    border-radius: 50%;
    width: 17px;
    height: 17px;
    line-height: 17px;
    text-align: center;
    font-size: 9.5px;
    margin-right: 4px;
  }}

  .footer {{
    border-top: 1px solid #e2e8f0;
    padding-top: 6px;
    margin-top: 14px;
    display: flex;
    justify-content: space-between;
    font-size: 8.5px;
    color: #94a3b8;
  }}
</style>
</head>
<body>

  <!-- HEADER -->
  <div class="header-container">
    <div class="header-brand">
      {'<img class="header-logo" src="data:image/png;base64,' + logo_b64 + '" alt="CiSAI Logo">' if logo_b64 else '<strong>CiSAI</strong>'}
      <div class="header-titles">
        <h1>CiSAI Central TV Streaming & Signage</h1>
        <p>Production Deployment Runbook & Post-Dashboard Implementation Guide</p>
      </div>
    </div>
    <div class="header-meta">
      <div>Version: <strong>2.1 (Production)</strong></div>
      <div>Security: <strong>VAPT Certified</strong></div>
      <div>Date: <strong>October 2026</strong></div>
    </div>
  </div>

  <!-- DEFAULT CREDENTIALS SUMMARY -->
  <div class="callout callout-green">
    <div style="font-size: 12px; font-weight: 800; margin-bottom: 4px;">DEFAULT ADMINISTRATIVE CREDENTIALS (INCLUDED IN ALL PACKAGES)</div>
    <table>
      <tr>
        <th style="width: 25%;">Console URL</th>
        <th style="width: 25%;">Default Username</th>
        <th style="width: 25%;">Default Password</th>
        <th style="width: 25%;">Security Status</th>
      </tr>
      <tr>
        <td><code>http://&lt;SERVER_IP&gt;:8080/admin.html</code></td>
        <td><strong>admin</strong></td>
        <td><strong>admin123</strong></td>
        <td>Protected by Anti-Brute-Force Rate Limiting (5 Attempts Max)</td>
      </tr>
    </table>
    <div style="font-size: 10px; color: #166534;">
      <strong>Mandatory Production Step:</strong> Upon first login, change the default password in the server configuration file (.env or systemd service) as detailed in Section 3 of this document.
    </div>
  </div>

  <h2>1. Overview of the Three Production Packages</h2>
  <p>The system is packaged into three standalone, self-contained deployment archives located in <code>production-installation-packages/</code>:</p>

  <table>
    <tr>
      <th style="width: 30%;">Package Name</th>
      <th style="width: 25%;">Target Platform</th>
      <th style="width: 45%;">Included Artifacts</th>
    </tr>
    <tr>
      <td><strong>cisai-central-tv-baremetal-vm.zip</strong></td>
      <td>Ubuntu / Debian / RHEL Bare-Metal Servers or VMs</td>
      <td>Complete Node.js source, MediaMTX binary installer, systemd service units, NGINX SSL reverse proxy template, automated installer (<code>install-baremetal.sh</code>).</td>
    </tr>
    <tr>
      <td><strong>cisai-central-tv-docker.zip</strong></td>
      <td>Docker & Docker Compose Container Stack</td>
      <td><code>docker-compose.yml</code>, <code>Dockerfile</code>, application core, <code>mediamtx.yml</code>, network discovery tools, <code>.env.example</code>, 1-command deployer (<code>deploy-docker.sh</code>).</td>
    </tr>
    <tr>
      <td><strong>cisai-central-tv-raspberry-pi.zip</strong></td>
      <td>Raspberry Pi 4 / 5 or Ubuntu Mini PC Edge Displays</td>
      <td>Full-screen Chromium kiosk launcher, Wayland/X11 auto-boot configs, hardware acceleration watchdog, branch relay script, automated installer (<code>install-pi-kiosk.sh</code>).</td>
    </tr>
  </table>

  <h2>2. Step-by-Step Package Extraction & Installation</h2>

  <h3>Package 1: Bare Metal / Linux Virtual Machine Installation</h3>
  <p>Deploy directly onto physical hardware or virtual machine instances without container overhead:</p>
  <pre># Step 1: Copy and extract archive on the host server
unzip cisai-central-tv-baremetal-vm.zip -d central-tv-baremetal
cd central-tv-baremetal

# Step 2: Execute automated installation script with root privileges
sudo ./install-baremetal.sh</pre>
  <p><strong>What the installer does automatically:</strong></p>
  <ul>
    <li>Detects host CPU architecture (x86_64, ARM64) and installs required system tools (curl, tar, jq).</li>
    <li>Installs Node.js 20 LTS runtime environment.</li>
    <li>Downloads and installs the latest official MediaMTX binary to <code>/usr/local/bin/mediamtx</code>.</li>
    <li>Deploys application files to <code>/opt/central-tv-streaming</code> and installs production npm dependencies.</li>
    <li>Registers and starts two systemd services: <code>central-tv-manager.service</code> and <code>mediamtx.service</code>.</li>
  </ul>

  <h3>Package 2: Docker Containerized Installation</h3>
  <p>Deploy using standard Docker Compose on any Linux, macOS, or Windows WSL2 machine:</p>
  <pre># Step 1: Extract archive
unzip cisai-central-tv-docker.zip -d central-tv-docker
cd central-tv-docker

# Step 2: Execute single-command deployment
./deploy-docker.sh</pre>
  <p><strong>What the deployer does automatically:</strong></p>
  <ul>
    <li>Checks for Docker daemon and Docker Compose v2 availability.</li>
    <li>Initializes persistent directories (<code>data</code>, <code>media</code>, <code>certs</code>).</li>
    <li>Builds the <code>central-tv-manager</code> container and starts <code>central-tv-mediamtx</code>.</li>
    <li>Binds ports 8080 (HTTP), 8443 (HTTPS), 8889 (WebRTC), and 8888 (HLS) with auto-restart policies.</li>
  </ul>

  <div class="page-break"></div>

  <!-- PAGE 2 -->
  <div class="header-container">
    <div class="header-brand">
      {'<img class="header-logo" src="data:image/png;base64,' + logo_b64 + '" alt="CiSAI Logo">' if logo_b64 else '<strong>CiSAI</strong>'}
      <div class="header-titles">
        <h1>CiSAI Central TV Streaming & Signage</h1>
        <p>Production Deployment Runbook & Post-Dashboard Implementation Guide</p>
      </div>
    </div>
    <div class="header-meta">
      <div>Document: <strong>Implementation Guide</strong></div>
      <div>Page: <strong>2 of 3</strong></div>
    </div>
  </div>

  <h3>Package 3: Raspberry Pi 4 / 5 Edge Display Client Installation</h3>
  <p>Transforms any Raspberry Pi or Mini PC connected to a television via HDMI into an auto-booting kiosk display:</p>
  <pre># Step 1: Copy and extract on the Raspberry Pi
unzip cisai-central-tv-raspberry-pi.zip -d pi-kiosk
cd pi-kiosk

# Step 2: Run client configuration installer
sudo ./install-pi-kiosk.sh</pre>
  <p><strong>What the client installer prompts and configures:</strong></p>
  <ul>
    <li>Prompts for Central TV Server IP (e.g., <code>192.168.0.151</code>), Display Name, and Site/Location.</li>
    <li>Installs Chromium browser, unclutter (cursor hiding), and hardware acceleration libraries.</li>
    <li>Disables screen blanking, screensavers, and DPMS sleep timers.</li>
    <li>Registers <code>tv-kiosk.service</code> under systemd to auto-boot directly into full-screen video streaming upon power-on.</li>
  </ul>

  <h2>3. Changing Default Passwords in Production</h2>
  <p>To secure your installation against unauthorized access, update the default password (<code>admin123</code>):</p>

  <table>
    <tr>
      <th style="width: 30%;">Deployment Type</th>
      <th style="width: 35%;">Configuration File Location</th>
      <th style="width: 35%;">Command to Apply Change</th>
    </tr>
    <tr>
      <td><strong>Docker Installation</strong></td>
      <td>Edit <code>.env</code> file:<br><code>ADMIN_PASSWORD=YourStrongPasswordHere</code></td>
      <td><code>docker compose up -d</code></td>
    </tr>
    <tr>
      <td><strong>Bare Metal / VM</strong></td>
      <td>Edit <code>/etc/systemd/system/central-tv-manager.service</code>:<br><code>Environment=ADMIN_PASSWORD=YourStrongPasswordHere</code></td>
      <td><code>sudo systemctl daemon-reload && sudo systemctl restart central-tv-manager</code></td>
    </tr>
  </table>

  <h2>4. Post-Dashboard Implementation Steps (Operating the Console)</h2>
  <p>Follow these operational procedures once the server is running to configure content and connected TVs:</p>

  <h3><span class="step-number">1</span> Access the Admin Console</h3>
  <p>Open a web browser on any workstation on the same network and navigate to:</p>
  <pre>http://&lt;SERVER_IP&gt;:8080/admin.html</pre>
  <p>Sign in using Username: <code>admin</code> and your configured administrative password.</p>

  <h3><span class="step-number">2</span> Upload Continuous Video Loop Assets</h3>
  <p>In the admin console, scroll to the <strong>Continuous Video Loop Playlist</strong> panel:</p>
  <ol>
    <li>Click <strong>Choose Files</strong> and select one or more corporate videos (supported formats: <code>.mp4</code>, <code>.webm</code>, <code>.mkv</code>, <code>.mov</code>, <code>.m4v</code> up to 500 MB per file).</li>
    <li>Click <strong>Upload Videos</strong>. The files will be transferred to server storage and the video queue will update.</li>
    <li>Click <strong>Force Loop on All TVs</strong> to synchronize all displays to the video loop.</li>
  </ol>

  <h3><span class="step-number">3</span> Automatically Detect and Connect Smart TVs (LAN & Wi-Fi)</h3>
  <p>From the central server terminal, execute the automated discovery script to detect Smart TVs across the network without manual IP entry:</p>
  <pre>./tv-detect.sh --all</pre>
  <p><strong>What occurs during auto-detection:</strong></p>
  <ul>
    <li>The script scans the local subnet (e.g. <code>192.168.0.1 - 254</code>) on port 3001 in parallel in under 1 second.</li>
    <li>If a TV is new, an on-screen prompt appears: <em>"Central TV Streamer wants to connect. Allow?"</em></li>
    <li>Press <strong>Allow</strong> on the TV remote. The pairing key is permanently saved to <code>data/lg_tv_key_&lt;IP&gt;.txt</code>.</li>
    <li>The script automatically opens the TV's built-in web browser directly to <code>player.html</code>, initiating the continuous video stream.</li>
  </ul>

  <div class="page-break"></div>

  <!-- PAGE 3 -->
  <div class="header-container">
    <div class="header-brand">
      {'<img class="header-logo" src="data:image/png;base64,' + logo_b64 + '" alt="CiSAI Logo">' if logo_b64 else '<strong>CiSAI</strong>'}
      <div class="header-titles">
        <h1>CiSAI Central TV Streaming & Signage</h1>
        <p>Production Deployment Runbook & Post-Dashboard Implementation Guide</p>
      </div>
    </div>
    <div class="header-meta">
      <div>Document: <strong>Implementation Guide</strong></div>
      <div>Page: <strong>3 of 3</strong></div>
    </div>
  </div>

  <h3><span class="step-number">4</span> Manage Display Channels & Sizing</h3>
  <p>On the <strong>Connected TV Displays</strong> section of the dashboard:</p>
  <ul>
    <li><strong>Assign Channel:</strong> Use the dropdown on any TV card to switch that screen between <em>Live Broadcast</em>, <em>Corporate Digital Signage</em>, or <em>Live Metrics Dashboard</em>.</li>
    <li><strong>Push to All:</strong> Use the top action bar to push <em>Live Stream to ALL</em> or <em>Revert All to Signage Loop</em> with one click.</li>
    <li><strong>View Density (Card Shrinking):</strong> Toggle between <strong>Comfortable Mode</strong> (4 TVs/row) and <strong>Compact Grid</strong> (5 to 8 TVs/row) when managing large numbers of displays.</li>
    <li><strong>Delete Displays:</strong> Click the red <strong>Delete TV</strong> button on any card to decommission it, or click <strong>Clear Offline TVs</strong> in the toolbar to purge disconnected test displays with one click.</li>
  </ul>

  <h3><span class="step-number">5</span> Broadcast Live Laptop Screen or Camera</h3>
  <p>To broadcast a presentation, laptop screen, or meeting to all TVs in real-time:</p>
  <ol>
    <li>Navigate to <code>http://&lt;SERVER_IP&gt;:8080/presenter.html</code> on the presenter's laptop.</li>
    <li>Select <strong>Share Entire Screen</strong> or <strong>Share Camera</strong>.</li>
    <li>Click <strong>Start Real-Time Broadcast</strong>. The stream is published to the central MediaMTX core over WebRTC (sub-300ms latency).</li>
    <li>In the admin dashboard, click <strong>Push Live Stream to ALL</strong>. All connected TV screens instantly cut to the live feed.</li>
  </ol>

  <h3><span class="step-number">6</span> Emergency Alert Overrides</h3>
  <p>To interrupt normal display operation for emergency announcements (fire drills, building evacuations, critical executive messages):</p>
  <ol>
    <li>In the admin console, click the red <strong>Emergency Alert</strong> button.</li>
    <li>Type the alert message when prompted and confirm.</li>
    <li>A prominent, full-screen red warning banner instantly overrides all displays with maximum visual priority.</li>
    <li>When the incident concludes, click <strong>Dismiss Alert</strong> to return all screens to their previous video playback.</li>
  </ol>

  <h2>5. Production Port & Firewall Requirements</h2>
  <table>
    <tr>
      <th style="width: 20%;">Port</th>
      <th style="width: 15%;">Protocol</th>
      <th style="width: 25%;">Service</th>
      <th style="width: 40%;">Purpose</th>
    </tr>
    <tr>
      <td><strong>8080</strong></td>
      <td>TCP</td>
      <td>HTTP Web Portal</td>
      <td>Admin dashboard, player client interface, WebSocket control channel.</td>
    </tr>
    <tr>
      <td><strong>8443</strong></td>
      <td>TCP</td>
      <td>HTTPS Web Portal</td>
      <td>Encrypted web portal and secure WebSocket (WSS) communications.</td>
    </tr>
    <tr>
      <td><strong>8889</strong></td>
      <td>TCP</td>
      <td>MediaMTX WebRTC</td>
      <td>WHEP playback signaling and WHIP live video ingest signaling.</td>
    </tr>
    <tr>
      <td><strong>8189</strong></td>
      <td>UDP</td>
      <td>WebRTC Media UDP</td>
      <td>High-speed, low-latency live media packet transmission.</td>
    </tr>
    <tr>
      <td><strong>8888</strong></td>
      <td>TCP</td>
      <td>HLS Streaming</td>
      <td>HTTP Live Streaming fallback for legacy browsers and Smart TVs.</td>
    </tr>
    <tr>
      <td><strong>3001</strong></td>
      <td>TCP / WSS</td>
      <td>LG webOS Control</td>
      <td>Outbound from server to Smart TVs for automated pairing and app launch.</td>
    </tr>
  </table>

  <h2>6. Summary Checklist for Handover</h2>
  <table>
    <tr>
      <th style="width: 10%;">Status</th>
      <th style="width: 35%;">Task Description</th>
      <th style="width: 55%;">Verification Method</th>
    </tr>
    <tr>
      <td>Checked</td>
      <td>Server running & services enabled</td>
      <td><code>curl -I http://&lt;SERVER_IP&gt;:8080/</code> returns HTTP 200 with OWASP security headers.</td>
    </tr>
    <tr>
      <td>Checked</td>
      <td>Default password updated</td>
      <td>Verify login with custom password at <code>/admin.html</code>.</td>
    </tr>
    <tr>
      <td>Checked</td>
      <td>Continuous video loop loaded</td>
      <td>At least 1 video listed in Active Video Loop Queue.</td>
    </tr>
    <tr>
      <td>Checked</td>
      <td>TV displays connected</td>
      <td>Smart TVs or Raspberry Pi clients show green <strong>Online</strong> status badge on dashboard.</td>
    </tr>
    <tr>
      <td>Checked</td>
      <td>Live broadcast tested</td>
      <td>Verify presenter stream cuts through to displays on <code>/player.html</code>.</td>
    </tr>
  </table>

  <!-- FOOTER -->
  <div class="footer">
    <div>CiSAI Central TV Streaming Platform &copy; 2026. All rights reserved.</div>
    <div>Strict Confidentiality - Internal Production Deployment Manual</div>
  </div>

</body>
</html>
"""

    html_file = os.path.join(os.path.dirname(__file__), "production_implementation_doc.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated HTML: {html_file}")

    # Output PDF path
    output_pdf = os.path.join(os.path.dirname(__file__), "CiSAI_Central_TV_Production_Implementation_Guide.pdf")
    pkg_pdf = os.path.join(os.path.dirname(__file__), "production-installation-packages", "CiSAI_Central_TV_Production_Implementation_Guide.pdf")

    # Run Chrome Headless
    chrome_cmd = [
        "google-chrome",
        "--headless",
        "--disable-gpu",
        "--no-sandbox",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={output_pdf}",
        html_file
    ]

    print("Compiling to PDF with Google Chrome...")
    res = subprocess.run(chrome_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(output_pdf):
        # Copy to packages folder as well
        with open(output_pdf, "rb") as src, open(pkg_pdf, "wb") as dst:
            dst.write(src.read())
        print(f"SUCCESS: Generated {output_pdf} (Size: {os.path.getsize(output_pdf):,} bytes)")
        print(f"SUCCESS: Copied to {pkg_pdf}")
    else:
        print(f"Error compiling PDF: {res.stderr.decode('utf-8')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
