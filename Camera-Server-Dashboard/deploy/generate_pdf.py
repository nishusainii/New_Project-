#!/usr/bin/env python3
import os
import subprocess
import base64

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOGO_PATH = os.path.join(ROOT_DIR, 'public', 'assets', 'innspark-logo.png')
HTML_OUT = os.path.join(ROOT_DIR, 'deploy', 'manual_print.html')
PDF_OUT = os.path.join(ROOT_DIR, 'Innspark_CCTV_Deployment_Manual.pdf')
PUB_PDF = os.path.join(ROOT_DIR, 'public', 'Innspark_CCTV_Deployment_Manual.pdf')

# Read logo as base64
with open(LOGO_PATH, 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode('utf-8')

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Innspark CCTV Dashboard - Deployment, Systemctl & VAPT Manual</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

  @page {{
    size: A4 portrait;
    margin: 14mm 14mm 14mm 14mm;
    @bottom-right {{
      content: counter(page);
    }}
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #1e293b;
    line-height: 1.5;
    font-size: 9pt;
    background: #ffffff;
  }}

  .cover-header {{
    border-bottom: 2px solid #0284c7;
    padding-bottom: 10px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .logo-img {{
    height: 36px;
    width: auto;
  }}

  .doc-meta {{
    text-align: right;
    font-family: 'JetBrains Mono', monospace;
    font-size: 7.5pt;
    color: #64748b;
  }}

  .doc-badge {{
    display: inline-block;
    background: #e0f2fe;
    color: #0369a1;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 7pt;
    margin-bottom: 3px;
  }}

  h1.main-title {{
    font-size: 18pt;
    font-weight: 800;
    color: #0f172a;
    line-height: 1.25;
    margin-bottom: 4px;
  }}

  p.subtitle {{
    font-size: 9.5pt;
    color: #475569;
    margin-bottom: 14px;
  }}

  h2 {{
    font-size: 11.5pt;
    font-weight: 700;
    color: #0369a1;
    border-left: 4px solid #0284c7;
    padding-left: 8px;
    margin: 14px 0 6px 0;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }}

  h3 {{
    font-size: 9.5pt;
    font-weight: 600;
    color: #0f172a;
    margin: 10px 0 3px 0;
  }}

  p, ul, ol {{
    margin-bottom: 6px;
  }}

  ul, ol {{
    padding-left: 18px;
  }}

  li {{
    margin-bottom: 2px;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px 0;
    font-size: 8pt;
  }}

  th, td {{
    border: 1px solid #cbd5e1;
    padding: 5px 8px;
    text-align: left;
  }}

  th {{
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
  }}

  tr:nth-child(even) {{
    background-color: #f8fafc;
  }}

  .code-block {{
    background-color: #0f172a;
    color: #f1f5f9;
    border-radius: 5px;
    padding: 7px 10px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 7.8pt;
    line-height: 1.4;
    margin: 4px 0 8px 0;
    overflow-x: hidden;
    white-space: pre-wrap;
    word-break: break-all;
    border-left: 3px solid #38bdf8;
  }}

  .cmd-comment {{
    color: #94a3b8;
  }}

  .callout {{
    background-color: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-left: 4px solid #22c55e;
    border-radius: 5px;
    padding: 6px 10px;
    margin: 8px 0;
    font-size: 8pt;
  }}

  .callout-title {{
    font-weight: 700;
    color: #15803d;
    margin-bottom: 2px;
  }}

  .page-break {{
    page-break-before: always;
  }}

  .avoid-break {{
    page-break-inside: avoid;
  }}

  .footer-stamp {{
    margin-top: 20px;
    padding-top: 8px;
    border-top: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    font-family: 'JetBrains Mono', monospace;
    font-size: 7.5pt;
    color: #94a3b8;
  }}
</style>
</head>
<body>

  <!-- HEADER -->
  <div class="cover-header">
    <img src="data:image/png;base64,{logo_b64}" alt="Innspark Logo" class="logo-img">
    <div class="doc-meta">
      <span class="doc-badge">UNIVERSAL LINUX DEPLOYMENT</span><br>
      DELHI REGIONAL OFFICE // 4 FLOORS<br>
      REF: INN-CCTV-SYSTEMCTL-V1.0
    </div>
  </div>

  <h1 class="main-title">24-Camera Surveillance Operations Center</h1>
  <p class="subtitle">Complete Linux Server Deployment, Systemd / Systemctl Configuration, and VAPT Hardening Manual</p>

  <!-- CHAPTER 1 -->
  <h2>1. System Specifications & Compatibility</h2>
  <p>Engineered to run seamlessly across <strong>ANY modern Linux distribution</strong> (Ubuntu 20.04/22.04/24.04, Debian 11/12, RHEL 8/9, Rocky Linux, AlmaLinux, CentOS Stream, Fedora, openSUSE):</p>
  <ul>
    <li><strong>Architecture:</strong> x86_64 (64-bit Linux).</li>
    <li><strong>Processor:</strong> Minimum 4 CPU Cores (8 Cores recommended for high-volume 24-channel viewing).</li>
    <li><strong>System Memory:</strong> Minimum 8 GB RAM (16 GB recommended).</li>
    <li><strong>Storage:</strong> Fast NVMe/SSD with minimum 20 GB free space.</li>
    <li><strong>Runtime Stack:</strong> Node.js LTS (v20+) + Embedded MediaMTX (v1.21.2) RTSP/WebRTC gateway.</li>
  </ul>

  <!-- CHAPTER 2 -->
  <div class="avoid-break">
    <h2>2. Network & Firewall Port Allocation</h2>
    <table>
      <thead>
        <tr>
          <th>Port</th>
          <th>Protocol</th>
          <th>Scope</th>
          <th>Service / Description</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>3000</strong></td>
          <td>TCP</td>
          <td>Internal / Proxy</td>
          <td>Node.js Express Web Dashboard & REST API</td>
        </tr>
        <tr>
          <td><strong>80 / 443</strong></td>
          <td>TCP</td>
          <td>Public / LAN</td>
          <td>HTTP / HTTPS Nginx Reverse Proxy & WebSockets</td>
        </tr>
        <tr>
          <td><strong>8554</strong></td>
          <td>TCP</td>
          <td>LAN / Subnet</td>
          <td>MediaMTX RTSP Ingestion & Camera Proxy</td>
        </tr>
        <tr>
          <td><strong>8889</strong></td>
          <td>TCP</td>
          <td>LAN / WAN</td>
          <td>MediaMTX WebRTC (WHEP) HTTP Signaling</td>
        </tr>
        <tr>
          <td><strong>8189</strong></td>
          <td>UDP</td>
          <td>LAN / WAN</td>
          <td>MediaMTX WebRTC ICE Media Streaming</td>
        </tr>
        <tr>
          <td><strong>8888</strong></td>
          <td>TCP</td>
          <td>LAN / WAN</td>
          <td>MediaMTX Low-Latency HLS Fallback Stream</td>
        </tr>
        <tr>
          <td><strong>9997</strong></td>
          <td>TCP</td>
          <td><strong>Localhost Only</strong></td>
          <td>MediaMTX Dynamic REST Control API (Bound to 127.0.0.1)</td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- CHAPTER 3 -->
  <div class="avoid-break">
    <h2>3. Automated 1-Command Production Setup</h2>
    <p>To deploy the entire stack automatically on any Linux server (creates unprivileged user, extracts files, installs dependencies, and configures systemd):</p>
    <div class="code-block"><span class="cmd-comment"># 1. Unzip the deployment archive</span>
unzip inncctv-enterprise-linux.zip -d /tmp/inncctv-pkg
cd /tmp/inncctv-pkg

<span class="cmd-comment"># 2. Run the automated installer with root privileges</span>
sudo bash deploy/setup-server.sh</div>
  </div>

  <div class="page-break"></div>

  <!-- CHAPTER 4 -->
  <h2>4. Step-by-Step Manual Linux Deployment</h2>
  <p>If you prefer full control over every step on your Linux server, run the following commands:</p>

  <h3>Step 4.1: Install Prerequisites (Ubuntu/Debian)</h3>
  <div class="code-block">sudo apt-get update -y && sudo apt-get upgrade -y
sudo apt-get install -y curl wget unzip ffmpeg ufw nginx</div>

  <h3>Step 4.1 (Alternative): Install Prerequisites (RHEL / Rocky / AlmaLinux)</h3>
  <div class="code-block">sudo dnf check-update -y && sudo dnf install -y epel-release
sudo dnf install -y curl wget unzip ffmpeg firewalld nginx</div>

  <h3>Step 4.2: Install Node.js LTS (v20+)</h3>
  <div class="code-block">curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs   # On RHEL: sudo dnf install -y nodejs
node -v && npm -v</div>

  <h3>Step 4.3: Create Dedicated System User (Security Hardening)</h3>
  <div class="code-block">sudo useradd -r -s /usr/sbin/nologin -d /opt/inncctv inncctv</div>

  <h3>Step 4.4: Deploy Files to <code>/opt/inncctv</code></h3>
  <div class="code-block">sudo mkdir -p /opt/inncctv
sudo unzip inncctv-enterprise-linux.zip -d /opt/inncctv/</div>

  <h3>Step 4.5: Install Node.js Production Dependencies</h3>
  <div class="code-block">cd /opt/inncctv
sudo npm install --omit=dev</div>

  <h3>Step 4.6: Set Executable Flags & Folder Permissions</h3>
  <div class="code-block">sudo chmod +x /opt/inncctv/bin/mediamtx
sudo chmod +x /opt/inncctv/start.sh /opt/inncctv/stop.sh
sudo chown -R inncctv:inncctv /opt/inncctv</div>

  <!-- CHAPTER 5 -->
  <div class="page-break"></div>
  <h2>5. Systemctl Configuration & Service Management (ANY Linux Machine)</h2>
  <p>The systemd service unit ensures the CCTV dashboard runs 24/7 in the background, recovers automatically from any unexpected crash, and boots automatically upon server power-on.</p>

  <div class="callout">
    <div class="callout-title">One-Click Automatic Systemd Setup (Recommended)</div>
    You can install and start the systemctl service immediately with one command from the project root:<br/>
    <code>sudo ./install-systemd.sh</code><br/>
    <em>To uninstall later, run: <code>sudo ./uninstall-systemd.sh</code></em>
  </div>

  <h3>5.1: The Production Service Unit File (<code>/etc/systemd/system/inncctv.service</code>)</h3>
  <div class="code-block">[Unit]
Description=Innspark Enterprise 24-Camera Surveillance Operations Center
After=network.target remote-fs.target nss-lookup.target

[Service]
Type=simple
User=inncctv
Group=inncctv
WorkingDirectory=/opt/inncctv
ExecStart=/usr/bin/env node /opt/inncctv/server/index.js
Restart=always
RestartSec=5s

# Production Environment Variables
Environment=NODE_ENV=production
Environment=PORT=3000
Environment=ADMIN_PASSWORD=innspark@2026
Environment=INNCCTV_SECRET=innspark_secure_production_token_secret_key_2026

# CIS Benchmark Linux Sandboxing
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
PrivateTmp=true
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target</div>

  <h3>5.2: Complete Systemctl Command Reference</h3>
  <table>
    <thead>
      <tr>
        <th>Action</th>
        <th>Linux Command</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Install Unit File</strong></td>
        <td><code>sudo cp /opt/inncctv/deploy/inncctv.service /etc/systemd/system/</code></td>
        <td>Copies unit file to systemd directory</td>
      </tr>
      <tr>
        <td><strong>Reload Systemd</strong></td>
        <td><code>sudo systemctl daemon-reload</code></td>
        <td>Notifies systemd of new/changed service unit</td>
      </tr>
      <tr>
        <td><strong>Enable Auto-Boot</strong></td>
        <td><code>sudo systemctl enable inncctv.service</code></td>
        <td>Configures service to launch on server boot</td>
      </tr>
      <tr>
        <td><strong>Start Service</strong></td>
        <td><code>sudo systemctl start inncctv.service</code></td>
        <td>Launches dashboard & streaming gateway</td>
      </tr>
      <tr>
        <td><strong>Check Live Status</strong></td>
        <td><code>sudo systemctl status inncctv.service</code></td>
        <td>Displays active state, uptime, PID & recent logs</td>
      </tr>
      <tr>
        <td><strong>Restart Service</strong></td>
        <td><code>sudo systemctl restart inncctv.service</code></td>
        <td>Gracefully restarts dashboard & camera streams</td>
      </tr>
      <tr>
        <td><strong>Stop Service</strong></td>
        <td><code>sudo systemctl stop inncctv.service</code></td>
        <td>Safely stops all monitoring & camera feeds</td>
      </tr>
      <tr>
        <td><strong>Check Boot Status</strong></td>
        <td><code>sudo systemctl is-enabled inncctv.service</code></td>
        <td>Verifies service will start on server reboot</td>
      </tr>
      <tr>
        <td><strong>Stream Live Logs</strong></td>
        <td><code>sudo journalctl -u inncctv.service -f</code></td>
        <td>Follows live console & camera connection logs</td>
      </tr>
      <tr>
        <td><strong>Inspect Errors</strong></td>
        <td><code>sudo journalctl -u inncctv.service -p err -e</code></td>
        <td>Filters and displays recent error events</td>
      </tr>
    </tbody>
  </table>

  <div class="callout">
    <div class="callout-title">Universal Compatibility Note</div>
    By utilizing <code>ExecStart=/usr/bin/env node</code>, the service automatically detects the correct Node.js binary location on any Linux distribution (whether installed under <code>/usr/bin/node</code>, <code>/usr/local/bin/node</code>, or custom paths).
  </div>

  <div class="page-break"></div>

  <!-- CHAPTER 6 -->
  <h2>6. Nginx Reverse Proxy & SSL/TLS Configuration</h2>
  <p>To serve the dashboard over standard port 80/443 with WebSocket upgrading and TLS encryption:</p>
  <div class="code-block"><span class="cmd-comment"># Copy pre-configured Nginx reverse proxy configuration</span>
sudo cp /opt/inncctv/deploy/nginx-inncctv.conf /etc/nginx/sites-available/inncctv
sudo ln -sf /etc/nginx/sites-available/inncctv /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

<span class="cmd-comment"># Obtain Free SSL Certificate via Let's Encrypt / Certbot</span>
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d cctv.yourcompany.com</div>

  <!-- CHAPTER 7 -->
  <h2>7. VAPT & Security Hardening Verification</h2>
  <div class="callout">
    <div class="callout-title">VAPT Compliance Summary</div>
    The dashboard includes active defenses for OWASP Top 10 web vulnerabilities including anti-brute-force rate limiting, scrypt salted password hashing, HMAC-SHA256 tokens, strict CSP headers, and input sanitization against shell command injection.
  </div>

  <h3>Verification Commands (Run in Terminal to Validate):</h3>
  <div class="code-block"><span class="cmd-comment"># 1. Verify Security Headers (Information Disclosure Protection)</span>
curl -s -I http://localhost:3000/ | grep -E "(X-Frame|X-Content|X-XSS|Content-Security|X-Powered-By)"

<span class="cmd-comment"># 2. Test Input Injection Sanitization (Should return HTTP 400 Bad Request)</span>
curl -s -X POST http://localhost:3000/api/cameras \\
  -H "Content-Type: application/json" \\
  -d '{{"name":"Test","floor":1,"ip":"invalid-ip","rtspUrl":"rtsp://evil;rm -rf /"}}'

<span class="cmd-comment"># 3. Test Anti-Brute-Force Rate Limiting (Triggers lockout after 5 failed attempts)</span>
for i in {{1..6}}; do
  curl -s -X POST http://localhost:3000/api/auth/login \\
    -H "Content-Type: application/json" \\
    -d '{{"username":"admin","password":"wrongpassword"}}'
  echo ""
done</div>

  <!-- CHAPTER 8 -->
  <h2>8. Operations, Backup & Credentials</h2>
  <p><strong>Default Access:</strong> URL: <code>http://&lt;SERVER_IP&gt;:3000</code> &nbsp;|&nbsp; User: <code>admin</code> &nbsp;|&nbsp; Password: <code>innspark@2026</code></p>
  <div class="code-block"><span class="cmd-comment"># Backup 24-camera configuration to file</span>
sudo cp /opt/inncctv/config/cameras.json /opt/cameras_backup_$(date +%F).json

<span class="cmd-comment"># Restore configuration from backup</span>
sudo cp /opt/cameras_backup_2026-10-15.json /opt/inncctv/config/cameras.json
sudo systemctl restart inncctv.service</div>

  <!-- FOOTER -->
  <div class="footer-stamp">
    <span>Innspark Solutions // Security Operations Center</span>
    <span>Document Ref: INN-CCTV-SYSTEMCTL-V1.0 // Delhi Office</span>
  </div>

</body>
</html>
"""

with open(HTML_OUT, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"[+] Generated HTML print template at {HTML_OUT}")

# Render to PDF using Headless Chrome
chrome_cmd = [
    'google-chrome',
    '--headless',
    '--disable-gpu',
    '--no-sandbox',
    '--no-pdf-header-footer',
    f'--print-to-pdf={PDF_OUT}',
    HTML_OUT
]

print("[+] Rendering PDF with Headless Chrome...")
res = subprocess.run(chrome_cmd, capture_output=True, text=True)
if res.returncode == 0 and os.path.exists(PDF_OUT):
    subprocess.run(['cp', PDF_OUT, PUB_PDF])
    size_kb = os.path.getsize(PDF_OUT) // 1024
    print(f"[✔] Successfully generated PDF: {PDF_OUT} ({size_kb} KB)")
else:
    print(f"[-] Error generating PDF: {res.stderr}")
