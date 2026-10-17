#!/usr/bin/env python3
import os
import subprocess
import base64

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOGO_PATH = os.path.join(ROOT_DIR, 'public', 'assets', 'innspark-logo.png')
HTML_OUT = os.path.join(ROOT_DIR, 'deploy', 'suse_guide_print.html')
PDF_OUT = os.path.join(ROOT_DIR, 'SUSE_Linux_Offline_Package_Installation_Guide.pdf')
PUB_PDF = os.path.join(ROOT_DIR, 'public', 'SUSE_Linux_Offline_Package_Installation_Guide.pdf')

# Read logo as base64
with open(LOGO_PATH, 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode('utf-8')

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SUSE Linux Enterprise - Offline Package Installation SOP</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

  @page {{
    size: A4 portrait;
    margin: 14mm 14mm 14mm 14mm;
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

  .header-bar {{
    border-bottom: 2px solid #0284c7;
    padding-bottom: 10px;
    margin-bottom: 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}

  .logo-img {{
    height: 34px;
    width: auto;
  }}

  .doc-meta {{
    text-align: right;
    font-size: 7.5pt;
    color: #64748b;
    line-height: 1.3;
  }}

  .badge {{
    display: inline-block;
    background: #0284c7;
    color: #ffffff;
    font-size: 7pt;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}

  h1 {{
    font-size: 17pt;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.5px;
    margin-bottom: 4px;
  }}

  .subtitle {{
    font-size: 9.5pt;
    color: #475569;
    margin-bottom: 14px;
  }}

  h2 {{
    font-size: 11.5pt;
    font-weight: 700;
    color: #0369a1;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    margin-top: 14px;
    margin-bottom: 7px;
    page-break-after: avoid;
  }}

  h3 {{
    font-size: 9.5pt;
    font-weight: 700;
    color: #0f172a;
    margin-top: 9px;
    margin-bottom: 4px;
    page-break-after: avoid;
  }}

  p {{
    margin-bottom: 6px;
    color: #334155;
  }}

  ul, ol {{
    margin-left: 18px;
    margin-bottom: 8px;
    color: #334155;
  }}

  li {{
    margin-bottom: 3px;
  }}

  .code-block {{
    background: #0f172a;
    color: #f8fafc;
    font-family: 'JetBrains Mono', monospace;
    font-size: 7.8pt;
    padding: 8px 10px;
    border-radius: 5px;
    margin: 6px 0 8px 0;
    line-height: 1.45;
    white-space: pre-wrap;
    word-break: break-all;
    border-left: 3px solid #38bdf8;
    page-break-inside: avoid;
  }}

  code {{
    font-family: 'JetBrains Mono', monospace;
    background: #f1f5f9;
    color: #0369a1;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 8pt;
  }}

  .callout {{
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-left: 4px solid #0284c7;
    padding: 8px 11px;
    border-radius: 4px;
    margin: 8px 0;
    font-size: 8.5pt;
    page-break-inside: avoid;
  }}

  .callout-title {{
    font-weight: 700;
    color: #0369a1;
    margin-bottom: 3px;
  }}

  .callout-tip {{
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-left: 4px solid #16a34a;
  }}
  .callout-tip .callout-title {{
    color: #15803d;
  }}

  .callout-warning {{
    background: #fffbeb;
    border: 1px solid #fde68a;
    border-left: 4px solid #d97706;
  }}
  .callout-warning .callout-title {{
    color: #b45309;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 10px 0;
    font-size: 8pt;
    page-break-inside: avoid;
  }}

  th {{
    background: #0f172a;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    padding: 5px 8px;
    border: 1px solid #334155;
  }}

  td {{
    padding: 5px 8px;
    border: 1px solid #e2e8f0;
    color: #334155;
    vertical-align: top;
  }}

  tr:nth-child(even) {{
    background: #f8fafc;
  }}

  .page-break {{
    page-break-before: always;
  }}

  .footer-bar {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    border-top: 1px solid #e2e8f0;
    padding-top: 6px;
    font-size: 7pt;
    color: #94a3b8;
    display: flex;
    justify-content: space-between;
  }}

  .cmd-comment {{
    color: #94a3b8;
    font-style: italic;
  }}
</style>
</head>
<body>

  <!-- HEADER -->
  <div class="header-bar">
    <img src="data:image/png;base64,{logo_b64}" class="logo-img" alt="Innspark Logo">
    <div class="doc-meta">
      <span class="badge">STANDARD OPERATING PROCEDURE</span><br>
      REF: INN-SOP-SUSE-OFFLINE-PKG-V1.0<br>
      APPLICABLE: SUSE Linux Enterprise Server (SLES) 12 / 15 / openSUSE
    </div>
  </div>

  <h1>SUSE Linux Enterprise Server (SLES)</h1>
  <p class="subtitle">Offline Package Installation Guide: Installing Packages (e.g., <code>libcap</code>) from ISO/DVD Without an Active SUSE Subscription</p>

  <!-- CHAPTER 1 -->
  <h2>1. Overview & Objective</h2>
  <p>In high-security, air-gapped, or trial enterprise environments, servers running <strong>SUSE Linux Enterprise Server (SLES)</strong> may not have access to the public internet or an active SUSE Customer Center (SCC) subscription. When trying to install packages using default repositories, the package manager (<code>zypper</code>) fails with registration errors.</p>
  <p>This technical guide provides the exact procedure to utilize the <strong>official SUSE installation ISO file or physical DVD</strong> as a fully functional local offline repository to install packages such as <strong><code>libcap</code></strong>, <strong><code>libcap-progs</code></strong>, or any other core system library without requiring a commercial subscription or external internet connectivity.</p>

  <div class="callout callout-tip">
    <div class="callout-title">Key Advantage of Using the Installation Media</div>
    The official SUSE ISO contains thousands of signed, official enterprise RPM packages. By mounting the media as a local repository, <code>zypper</code> automatically resolves internal dependencies, validates cryptographic hashes, and installs the exact versions supported by the operating system kernel.
  </div>

  <!-- CHAPTER 2 -->
  <h2>2. Quick Command Reference (For <code>/mnt/dvd</code>)</h2>
  <p>If you have already mounted your SUSE installation ISO or DVD to <code>/mnt/dvd</code>, execute the following commands in sequence as root or with <code>sudo</code>:</p>

  <table>
    <thead>
      <tr>
        <th style="width: 28%;">Step / Action</th>
        <th style="width: 48%;">Command to Execute</th>
        <th style="width: 24%;">Purpose</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>1. Add Local Repository</strong></td>
        <td><code>sudo zypper addrepo -c /mnt/dvd "SUSE_Local_ISO"</code></td>
        <td>Registers <code>/mnt/dvd</code> into Zypper package manager</td>
      </tr>
      <tr>
        <td><strong>2. Refresh Repositories</strong></td>
        <td><code>sudo zypper refresh</code></td>
        <td>Reads package catalogs and metadata (press 'a' to trust)</td>
      </tr>
      <tr>
        <td><strong>3. Install libcap Packages</strong></td>
        <td><code>sudo zypper install -y libcap2 libcap-progs</code></td>
        <td>Installs library, <code>setcap</code>, and <code>getcap</code> utilities</td>
      </tr>
      <tr>
        <td><strong>4. Verify Installation</strong></td>
        <td><code>rpm -q libcap2 libcap-progs && which setcap</code></td>
        <td>Confirms package installation and executable paths</td>
      </tr>
    </tbody>
  </table>

  <!-- CHAPTER 3 -->
  <h2>3. Detailed Step-by-Step Implementation</h2>

  <h3>Step 3.1: Mount the ISO or DVD Media</h3>
  <p>If the ISO is a file on the disk (e.g. <code>/root/SLE-15-SP4-Full-x86_64.iso</code>), mount it as a loopback filesystem to <code>/mnt/dvd</code>:</p>
  <div class="code-block"><span class="cmd-comment"># Create the mount point if it does not already exist</span>
sudo mkdir -p /mnt/dvd

<span class="cmd-comment"># Mount the ISO image (replace with your ISO file location)</span>
sudo mount -o loop /path/to/SUSE_installation.iso /mnt/dvd

<span class="cmd-comment"># Verify that the directory contains the media contents</span>
ls -la /mnt/dvd</div>

  <h3>Step 3.2: Register the Local Repository in Zypper</h3>
  <p>Inform the Zypper package manager of the new repository on <code>/mnt/dvd</code>:</p>
  <div class="code-block">sudo zypper addrepo -c /mnt/dvd "SUSE_Local_ISO"</div>
  <p><em>The <code>-c</code> (or <code>--check</code>) flag validates that a valid repository metadata catalog is located at that path.</em></p>

  <h3>Step 3.3: Refresh Zypper Metadata</h3>
  <p>Update the package database from the newly added local repository:</p>
  <div class="code-block">sudo zypper refresh</div>
  <p>When prompted to trust the repository signing key:</p>
  <div class="code-block">New repository or package signing key received:
Do you want to (a)lways trust, trust (t)emporarily, or (d)isown the key? [a/t/d/?] (a): <strong>a</strong></div>
  <p>Type <code>a</code> (Always trust) and press Enter.</p>

  <div class="page-break"></div>

  <!-- CHAPTER 3 CONTINUED -->
  <h2>3. Detailed Step-by-Step Implementation (Continued)</h2>

  <h3>Step 3.4: Search and Install <code>libcap</code></h3>
  <p>Search for the available <code>libcap</code> packages in the local repository:</p>
  <div class="code-block">sudo zypper search libcap</div>
  <p>Proceed to install the core library (<code>libcap2</code>) and userland tools (<code>libcap-progs</code>):</p>
  <div class="code-block">sudo zypper install -y libcap2 libcap-progs</div>

  <h3>Step 3.5: Verify Capability Utilities</h3>
  <p>Verify that the package is properly registered in the RPM database and verify binary utilities:</p>
  <div class="code-block"><span class="cmd-comment"># Check RPM database</span>
rpm -q libcap2 libcap-progs

<span class="cmd-comment"># Confirm setcap and getcap tools are available</span>
which setcap getcap

<span class="cmd-comment"># Test capability assignment support</span>
setcap -v cap_net_bind_service=+ep /path/to/binary || echo "Cap utilities active"</div>

  <!-- CHAPTER 4 -->
  <h2>4. Alternative Method: Direct RPM Package Installation</h2>
  <p>If you prefer not to register a repository in Zypper, you can extract and install the exact RPM files directly from the mounted media:</p>

  <div class="code-block"><span class="cmd-comment"># 1. Search for the exact libcap RPM files within the mounted ISO</span>
find /mnt/dvd -name "*libcap*.rpm"

<span class="cmd-comment"># Example output found on SLES installation media:</span>
<span class="cmd-comment"># /mnt/dvd/x86_64/libcap2-2.xx-xx.x86_64.rpm</span>
<span class="cmd-comment"># /mnt/dvd/x86_64/libcap-progs-2.xx-xx.x86_64.rpm</span>

<span class="cmd-comment"># 2. Install directly using zypper (resolves any local sub-dependencies)</span>
sudo zypper install /mnt/dvd/x86_64/libcap2-*.rpm /mnt/dvd/x86_64/libcap-progs-*.rpm

<span class="cmd-comment"># OR using standalone RPM tool directly:</span>
sudo rpm -Uvh /mnt/dvd/x86_64/libcap2-*.rpm /mnt/dvd/x86_64/libcap-progs-*.rpm</div>

  <!-- CHAPTER 5 -->
  <h2>5. Troubleshooting & Special Cases</h2>

  <h3>Issue 1: "Repository type can not be determined"</h3>
  <p>On some versions of SLES (especially SLES 12/15 unified installer media), you may need to explicitly inform Zypper that the repository follows YaST2 media layout:</p>
  <div class="code-block"><span class="cmd-comment"># Explicitly define YaST2 repository format</span>
sudo zypper addrepo -t yast2 /mnt/dvd "SUSE_Local_ISO"</div>

  <h3>Issue 2: "Mount: /mnt/dvd is busy"</h3>
  <p>If you need to unmount the media after installation, make sure no terminals or processes are inside <code>/mnt/dvd</code>:</p>
  <div class="code-block">cd /root
sudo umount /mnt/dvd</div>

  <h3>Issue 3: Managing Existing Unregistered Repositories</h3>
  <p>If Zypper attempts to contact external SUSE servers that fail due to missing subscription, you can disable the external repositories temporarily or prioritize the local ISO:</p>
  <div class="code-block"><span class="cmd-comment"># List all repositories and their status</span>
zypper lr -d

<span class="cmd-comment"># Set high priority (lower number = higher priority) for Local ISO</span>
sudo zypper mr -p 50 "SUSE_Local_ISO"</div>

  <!-- CHAPTER 6 -->
  <h2>6. Post-Installation Cleanup & Maintenance</h2>
  <table>
    <thead>
      <tr>
        <th>Action</th>
        <th>Command</th>
        <th>Recommendation</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>Disable Local Repo</strong></td>
        <td><code>sudo zypper mr -d "SUSE_Local_ISO"</code></td>
        <td>Disable when DVD is unmounted to prevent warning messages</td>
      </tr>
      <tr>
        <td><strong>Enable Local Repo</strong></td>
        <td><code>sudo zypper mr -e "SUSE_Local_ISO"</code></td>
        <td>Re-enable anytime additional packages need to be installed</td>
      </tr>
      <tr>
        <td><strong>Remove Local Repo</strong></td>
        <td><code>sudo zypper removerepo "SUSE_Local_ISO"</code></td>
        <td>Use if installation media is permanently removed from the server</td>
      </tr>
      <tr>
        <td><strong>Unmount Media</strong></td>
        <td><code>sudo umount /mnt/dvd</code></td>
        <td>Frees the loop device and disc image</td>
      </tr>
    </tbody>
  </table>

  <div class="callout callout-tip" style="margin-top: 15px;">
    <div class="callout-title">Enterprise Security & Compliance Verification</div>
    Installing packages from the official SUSE ISO preserves the integrity of your server's security baselines. Every package installed via this SOP has been cryptographically signed with the official SUSE GPG package signing key, ensuring zero risk of unvetted or compromised third-party binaries.
  </div>

  <div style="margin-top: 25px; border-top: 1px solid #cbd5e1; padding-top: 8px; font-size: 7.5pt; color: #64748b; display: flex; justify-content: space-between;">
    <span>Document Ref: INN-SOP-SUSE-OFFLINE-PKG-V1.0</span>
    <span>Innspark Surveillance & Infrastructure Solutions</span>
  </div>

</body>
</html>
"""

# Write HTML template
with open(HTML_OUT, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"[+] Generated HTML print template at {HTML_OUT}")

# Render PDF using headless Chrome
print("[+] Rendering PDF with Headless Chrome...")
chrome_cmd = [
    "google-chrome",
    "--headless",
    "--disable-gpu",
    "--no-sandbox",
    "--no-pdf-header-footer",
    f"--print-to-pdf={PDF_OUT}",
    HTML_OUT
]

res = subprocess.run(chrome_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
if res.returncode == 0:
    pdf_size_kb = os.path.getsize(PDF_OUT) // 1024
    print(f"[✔] Successfully generated PDF: {PDF_OUT} ({pdf_size_kb} KB)")
    
    # Copy to public
    subprocess.run(["cp", PDF_OUT, PUB_PDF])
    print(f"[✔] Copied to public download directory: {PUB_PDF}")
else:
    print(f"[X] Failed to generate PDF: {res.stderr.decode('utf-8')}")
