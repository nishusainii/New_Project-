#!/usr/bin/env python3
"""
Generate the Central TV Streaming & Signage Hub - User GUI Guide PDF.
Strict rules:
- Zero emojis.
- Clean typography and layout with embedded CiSAI logo.
- Comprehensive step-by-step guide for using the GUI (Admin, Presenter, Dashboard).
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
<title>Central TV Streaming Hub - User Operations Guide - CiSAI</title>
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
      {f'<img src="data:image/png;base64,{logo_b64}" class="header-logo" alt="CiSAI Logo">' if logo_b64 else ''}
      <div class="header-title-box">
        <span class="org-tag">Centre for Innovation & Systems AI</span>
        <h1 class="main-title">Central TV Streaming Hub - User Operations Guide</h1>
      </div>
    </div>
    <div class="header-meta">
      <div class="meta-tag">User Manual: Web Portals</div><br>
      Target Audience: Operations & Presenters<br>
    </div>
  </div>

  <!-- Section 1 -->
  <h2>1. Platform Overview & User Access Roles</h2>
  <p>
    The Central TV Streaming Hub provides a centralized system to manage, monitor, and stream content to all connected Smart TVs across corporate headquarters and remote branch offices. The system enforces Role-Based Access Control (RBAC) to separate fleet infrastructure management from day-to-day media operations and live broadcasting.
  </p>

  <div class="grid-2">
    <div class="card">
      <div class="card-header">Portal Interfaces</div>
      <ul>
        <li><strong>Presenter Studio:</strong> Real-time screen/camera broadcasting and direct media loop video uploads.</li>
        <li><strong>Admin Console:</strong> Complete fleet discovery, TV settings, channel management, and emergency broadcast controls.</li>
        <li><strong>Executive Dashboard:</strong> Real-time telemetry monitoring active TVs and streaming codecs.</li>
      </ul>
    </div>
    <div class="card">
      <div class="card-header">Portal Access & Automated Routing</div>
      <p>Authenticate at <code>http://&lt;SERVER_IP&gt;:8080/login.html</code> (or HTTPS <code>:8443</code>). The portal automatically evaluates your user role and directs you to the appropriate console.</p>
    </div>
  </div>

  <h3>1.1 User Roles and Permissions Matrix</h3>
  <table>
    <thead>
      <tr>
        <th style="width: 18%;">User Role</th>
        <th style="width: 18%;">Default Credentials</th>
        <th style="width: 32%;">Permitted Capabilities</th>
        <th style="width: 32%;">Restricted / Guarded Actions</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Streamer / Operator</strong><br><span style="font-size: 8.5px; color: #2563eb;">Content & Broadcast</span></td>
        <td><code>streamer</code><br><code>streamer123</code></td>
        <td>
          &bull; Upload videos to continuous signage loop<br>
          &bull; Delete and reorder signage loop videos<br>
          &bull; Live screen sharing & camera broadcast (WebRTC)<br>
          &bull; Force TVs to switch between live stream & signage<br>
          &bull; Synchronize video playback across all screens
        </td>
        <td>
          &bull; Cannot delete or decommission TV displays<br>
          &bull; Cannot run network subnet discovery scans<br>
          &bull; Cannot create/modify channel definitions<br>
          &bull; Cannot trigger emergency alert banners
        </td>
      </tr>
      <tr>
        <td><strong>Administrator</strong><br><span style="font-size: 8.5px; color: #16a34a;">System & Fleet Control</span></td>
        <td><code>admin</code><br><code>admin123</code></td>
        <td>
          &bull; Full system access to all fleet management tools<br>
          &bull; Network TV discovery & auto-launch<br>
          &bull; TV display settings, reboots, and decommissioning<br>
          &bull; Emergency facility-wide alert dispatch<br>
          &bull; All streamer & media operations capabilities
        </td>
        <td>
          <em>Unrestricted full administrative privileges across all APIs and endpoints.</em>
        </td>
      </tr>
    </tbody>
  </table>

  <!-- Section 2 -->
  <h2>2. Using the Live Presenter & Media Studio</h2>
  <p>
    The Presenter Studio (<code>/presenter.html</code>) is the primary workspace for content operators and meeting presenters. It combines real-time low-latency video streaming with direct media loop management.
  </p>

  <h3>2.1 Live Broadcasting (Screen & Camera)</h3>
  <ol>
    <li>Log in as <code>streamer</code> (or <code>admin</code>) to enter the Presenter Studio.</li>
    <li>Select your source: Click <strong>"Share Laptop Screen"</strong> or <strong>"Camera & Mic"</strong>. When prompted by your browser, grant media capture permissions.</li>
    <li>Select the <strong>Broadcast Destination</strong>: Choose between <em>All Sites (HQ + Remote)</em>, <em>Headquarters Only</em>, or <em>Remote Site Only</em>.</li>
    <li>Click the <strong>"Start Live Broadcast"</strong> button. Within 250 milliseconds, all target TVs will interrupt their current playback and switch seamlessly to your live video feed.</li>
    <li>When finished, click <strong>"Stop Broadcast"</strong>. Target TVs will automatically return to the 24/7 digital signage loop without any manual intervention.</li>
  </ol>

  <h3>2.2 Signage Media Uploads & Playlist Loop Management</h3>
  <p>
    Streamers can manage the continuous video playlist directly from the Presenter Studio without requiring access to the administrative fleet console:
  </p>
  <ul>
    <li><strong>Upload Videos:</strong> Choose one or more MP4, WebM, or MKV files using the file selector and click <strong>"Upload Videos to Loop"</strong>. Files are automatically verified and added to the round-robin loop.</li>
    <li><strong>Sync All to Video 1:</strong> Click this button to simultaneously synchronize all TV displays across all offices to restart at the beginning of the playlist loop.</li>
    <li><strong>Force Signage Loop:</strong> Immediately instructs any TVs currently on external channels to return to the corporate signage playlist.</li>
    <li><strong>Delete Videos:</strong> Remove outdated announcement videos directly from the loop queue.</li>
  </ul>

  <!-- Section 3 -->
  <h2>3. Using the Admin Console (Fleet Management)</h2>
  <p>The Admin Console (<code>/admin.html</code>) is restricted to the <code>admin</code> user and provides hardware-level fleet management.</p>

  <div class="grid-2">
    <div class="card">
      <div class="card-header">Fleet Discovery & Telemetry</div>
      <ul>
        <li><strong>Auto-Scan Subnet:</strong> Run <code>Scan & Auto-Connect Network TVs</code> to probe local subnets and automatically launch the TV player software on LG WebOS displays.</li>
        <li><strong>Remote Display Reload:</strong> Send instant reload signals to refresh the player software on specific screens.</li>
        <li><strong>Prune Offline Displays:</strong> Clean up decommissioned TV records with a single click.</li>
      </ul>
    </div>
    <div class="card">
      <div class="card-header">Emergency Broadcast Override</div>
      <ul>
        <li><strong>Emergency Alert Banner:</strong> Broadcast critical facility announcements with red audio-visual banners across every screen.</li>
        <li><strong>Channel Definitions:</strong> Configure new streaming channels (RTSP cameras, dashboard web URLs, or custom WebRTC feeds).</li>
      </ul>
    </div>
  </div>

  <!-- Section 4 -->
  <h2>4. Executive Dashboard & Telemetry</h2>
  <p>The Executive Dashboard (<code>/dashboard.html</code>) provides a high-level operational overview for IT NOC displays, showing connected display counts, current playback mode, and media server responsiveness.</p>

  <!-- Section 5 -->
  <h2>5. Troubleshooting & Operations Reference</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 28%;">Symptom</th>
        <th style="width: 22%;">Likely Cause</th>
        <th style="width: 50%;">Resolution Procedure</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Login failed or rejected</strong></td>
        <td>Incorrect credentials or locked account</td>
        <td>Verify username and password (<code>streamer</code> / <code>streamer123</code> for media ops; <code>admin</code> / <code>admin123</code> for fleet). Wait 5 minutes if rate-limited.</td>
      </tr>
      <tr>
        <td><strong>Streamer redirected from Admin Console</strong></td>
        <td>Enforced RBAC security policy</td>
        <td>Normal behavior. The <code>streamer</code> role is restricted to Presenter Studio. Use the <code>admin</code> account if fleet configuration is required.</td>
      </tr>
      <tr>
        <td><strong>Live broadcast shows black screen</strong></td>
        <td>WebRTC UDP packet block</td>
        <td>Ensure internal firewall allows UDP port <code>8189</code> between presenter laptop and the central hub server.</td>
      </tr>
      <tr>
        <td><strong>Video loop skips or stutters</strong></td>
        <td>Unoptimized codec or high bitrate</td>
        <td>Ensure uploaded videos use H.264 video codec at 1080p (1920x1080) 30fps. Unoptimized 4K high-bitrate files should be re-encoded.</td>
      </tr>
    </tbody>
  </table>

  <div class="footer-note">
    <strong>CiSAI - Centre for Innovation & Systems AI</strong> &bull; User Operations & GUI Guide &bull; 2026
  </div>

</body>
</html>
"""

    output_dir = os.path.join(workspace_dir, "documentation-and-pdfs")
    os.makedirs(output_dir, exist_ok=True)
    output_html = os.path.join(output_dir, "user_gui_operations_guide.html")
    output_pdf = os.path.join(output_dir, "User_GUI_Operations_Guide.pdf")

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
        dest_pdf = os.path.join(prod_pkg_dir, "User_GUI_Operations_Guide.pdf")
        with open(output_pdf, "rb") as src, open(dest_pdf, "wb") as dst:
            dst.write(src.read())
        print(f"Copied to: {dest_pdf}")
    else:
        print(f"ERROR: {res.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    main()
