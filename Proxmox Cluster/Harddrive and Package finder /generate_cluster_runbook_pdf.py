import os
import subprocess

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Proxmox VE Cluster - Complete Command Execution Runbook</title>
<style>
  @page {
    size: A4 portrait;
    margin: 14mm 12mm 14mm 12mm;
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 8pt;
      color: #718096;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    @bottom-left {
      content: "Innspark Proxmox Cluster Runbook • Internal Technical Documentation";
      font-size: 8pt;
      color: #718096;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #1a202c;
    line-height: 1.45;
    font-size: 9.5pt;
    margin: 0;
    padding: 0;
    background: #ffffff;
  }

  /* Cover / Header Section */
  .header-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0369a1 100%);
    color: white;
    padding: 24px 28px;
    border-radius: 10px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  }
  .header-card h1 {
    margin: 0 0 6px 0;
    font-size: 20pt;
    font-weight: 800;
    letter-spacing: -0.5px;
  }
  .header-card .subtitle {
    font-size: 11pt;
    color: #93c5fd;
    margin-bottom: 14px;
    font-weight: 500;
  }
  .meta-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    background: rgba(255, 255, 255, 0.08);
    padding: 10px 14px;
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    font-size: 8.5pt;
  }
  .meta-item strong {
    display: block;
    color: #38bdf8;
    text-transform: uppercase;
    font-size: 7pt;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
  }

  /* Section Styling */
  h2 {
    color: #0f172a;
    font-size: 13pt;
    border-bottom: 2px solid #0284c7;
    padding-bottom: 4px;
    margin-top: 22px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    page-break-after: avoid;
  }
  h3 {
    color: #1e293b;
    font-size: 10.5pt;
    margin-top: 14px;
    margin-bottom: 6px;
    page-break-after: avoid;
  }

  /* Code Block Styling */
  .cmd-box {
    background: #0f172a;
    color: #f8fafc;
    border-radius: 6px;
    margin: 6px 0 10px 0;
    overflow: hidden;
    page-break-inside: avoid;
    box-shadow: 0 2px 4px rgba(0,0,0,0.08);
    border-left: 4px solid #0284c7;
  }
  .cmd-header {
    background: #1e293b;
    padding: 4px 10px;
    font-size: 7.5pt;
    color: #94a3b8;
    display: flex;
    justify-content: space-between;
    font-family: monospace;
    border-bottom: 1px solid #334155;
  }
  .cmd-header span.node-tag {
    background: #0369a1;
    color: #e0f2fe;
    padding: 1px 6px;
    border-radius: 3px;
    font-weight: 600;
  }
  pre {
    margin: 0;
    padding: 8px 12px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 8pt;
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-all;
    color: #38bdf8;
  }
  pre code {
    color: #f1f5f9;
  }
  pre .comment {
    color: #64748b;
    font-style: italic;
  }
  pre .param {
    color: #facc15;
  }

  /* Note & Alert Boxes */
  .alert-box {
    background: #f0f9ff;
    border-left: 4px solid #0284c7;
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    margin: 8px 0;
    font-size: 8.5pt;
    color: #0369a1;
    page-break-inside: avoid;
  }
  .alert-box.success {
    background: #f0fdf4;
    border-left-color: #16a34a;
    color: #15803d;
  }
  .alert-box.warning {
    background: #fffbeb;
    border-left-color: #d97706;
    color: #b45309;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0;
    font-size: 8pt;
    page-break-inside: avoid;
  }
  th, td {
    border: 1px solid #cbd5e1;
    padding: 5px 8px;
    text-align: left;
  }
  th {
    background: #f1f5f9;
    color: #334155;
    font-weight: 700;
  }
  tr:nth-child(even) {
    background: #f8fafc;
  }

  .badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 7pt;
  }
  .badge-ceph { background: #ffedd5; color: #c2410c; }
  .badge-zfs { background: #dbeafe; color: #1d4ed8; }
  .badge-spare { background: #f3e8ff; color: #7e22ce; }
  .badge-os { background: #dcfce7; color: #15803d; }
  .badge-online { background: #dcfce7; color: #166534; font-weight: bold; }
  .badge-standby { background: #cffafe; color: #0e7490; font-weight: bold; }

  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<!-- COVER / HEADER CARD -->
<div class="header-card">
  <h1>PROXMOX VE 3-NODE CLUSTER</h1>
  <div class="subtitle">Complete Command Execution & Operations Runbook (Start to Finish)</div>
  <div class="meta-grid">
    <div class="meta-item">
      <strong>Cluster Nodes</strong>
      prox22, prox23, prox24
    </div>
    <div class="meta-item">
      <strong>IP Addresses</strong>
      10.31.6.172 / 173 / 174
    </div>
    <div class="meta-item">
      <strong>Storage Stack</strong>
      Ceph 20.2 + ZFS RAID-Z2
    </div>
    <div class="meta-item">
      <strong>Environment</strong>
      PVE 9.2 (Debian 13 Linux)
    </div>
  </div>
</div>

<!-- SECTION 1: HARDWARE TOPOLOGY -->
<h2>1. Verified Physical Storage Topology & Bay Layout</h2>
<p>All three Dell PowerEdge servers feature an identical front 12-bay chassis layout mapped through Dell PERC H755 / MegaRAID controller:</p>

<table>
  <thead>
    <tr>
      <th>Chassis Bay</th>
      <th>Role</th>
      <th>Drive Specs</th>
      <th>prox22 (10.31.6.172)</th>
      <th>prox23 (10.31.6.173)</th>
      <th>prox24 (10.31.6.174)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Slot 0</strong></td>
      <td><span class="badge badge-ceph">CEPH OSD</span></td>
      <td>18.2TB Seagate HDD</td>
      <td>osd.0 (S/N: ZYDGFEW6)</td>
      <td>osd.1 (S/N: ZYDFR75F)</td>
      <td>osd.2 (S/N: ZYDFWT0C)</td>
    </tr>
    <tr>
      <td><strong>Slot 1</strong></td>
      <td><span class="badge badge-ceph">CEPH OSD</span></td>
      <td>18.2TB Seagate HDD</td>
      <td>osd.3 (S/N: ZYDG4WXP)</td>
      <td>osd.4 (S/N: ZYDG3L2Q)</td>
      <td>osd.5 (S/N: ZYDFMNJ2)</td>
    </tr>
    <tr>
      <td><strong>Slot 2</strong></td>
      <td><span class="badge badge-ceph">CEPH OSD</span></td>
      <td>18.2TB Seagate HDD</td>
      <td>osd.6 (S/N: ZYDG0CL3)</td>
      <td>osd.7 (S/N: ZYDGCX8R)</td>
      <td>osd.8 (S/N: ZYDEHZW4)</td>
    </tr>
    <tr>
      <td><strong>Slot 3</strong></td>
      <td><span class="badge badge-ceph">CEPH OSD</span></td>
      <td>18.2TB Seagate HDD</td>
      <td>osd.9 (S/N: ZYDFZ35V)</td>
      <td>osd.10 (S/N: ZYDGD4MM)</td>
      <td>osd.11 (S/N: ZYDEML2L)</td>
    </tr>
    <tr>
      <td><strong>Slots 4–10</strong></td>
      <td><span class="badge badge-zfs">ZFS RAID-Z2</span></td>
      <td>7 × 18.2TB HDDs (zfs-ha)</td>
      <td>7 Drives (ZYDG62WJ ... ZYDFWL9E)</td>
      <td>7 Drives (ZYDG1DK6 ... ZYDDT9JV)</td>
      <td>7 Drives (ZYDG9GLB ... ZYDG9GR2)</td>
    </tr>
    <tr>
      <td><strong>Slot 11</strong></td>
      <td><span class="badge badge-spare">SPARE</span></td>
      <td>18.2TB Standby Drive</td>
      <td>S/N: ZYDFW4AP</td>
      <td>S/N: ZYDG7ZYQ</td>
      <td>S/N: ZYDFHHAE</td>
    </tr>
    <tr>
      <td><strong>Rear Bay</strong></td>
      <td><span class="badge badge-os">OS ROOT</span></td>
      <td>960GB Micron SSD</td>
      <td>/dev/sdm (pve-root)</td>
      <td>/dev/sdm (pve-root)</td>
      <td>/dev/sdm (pve-root)</td>
    </tr>
  </tbody>
</table>

<!-- SECTION 2: PHASE 1 DISCOVERY -->
<h2>2. Phase 1 — Hardware Discovery & Physical Topology Mapping</h2>
<p>Commands executed to establish cluster network connectivity, inspect RAID controllers, and map Linux block devices to physical backplane slot numbers:</p>

<h3>2.1 Network Connectivity & SSH Reachability Tests</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH</span><span class="node-tag">LOCAL WORKSTATION</span></div>
  <pre><code><span class="comment"># 1. Ping and reachability test across all 3 nodes</span>
for ip in 10.31.6.172 10.31.6.173 10.31.6.174; do
    ping -c 1 -W 1 $ip 2>&amp;1 | grep "packets transmitted"
done

<span class="comment"># 2. Port 22 SSH verification</span>
for ip in 10.31.6.172 10.31.6.173 10.31.6.174; do
    nc -z -v -w 1 $ip 22 2>&amp;1
done

<span class="comment"># 3. Passwordless SSH verification & Hostname checks</span>
for ip in 10.31.6.172 10.31.6.173 10.31.6.174; do
    ssh -o ConnectTimeout=2 -o BatchMode=yes root@$ip "hostname"
done</code></pre>
</div>

<h3>2.2 Storage Controller & Physical Drive Slot Discovery (PERCCLI64)</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">prox22 (10.31.6.172)</span></div>
  <pre><code><span class="comment"># Locate Dell PERC CLI utility on Proxmox node</span>
which perccli /opt/MegaRAID/perccli/perccli64 storcli 2>/dev/null

<span class="comment"># Inspect Dell PERC Controller 0 backplane enclosure and slots</span>
/opt/MegaRAID/perccli/perccli64 /c0 /eall /sall show

<span class="comment"># Query drive slots and serial numbers on Enclosure 252</span>
/opt/MegaRAID/perccli/perccli64 /c0 /e252 /sall show all | grep -E "Drive /c0/e252/s|SN ="</code></pre>
</div>

<h3>2.3 Ceph Cluster & OSD Storage Mapping</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">prox22 (10.31.6.172)</span></div>
  <pre><code><span class="comment"># View Ceph OSD tree, hosts, and weights</span>
ceph osd tree

<span class="comment"># Correlate Ceph OSD daemon IDs to device paths and drive serial numbers</span>
ceph device ls

<span class="comment"># Extract OSD IDs and serials for automated mapping</span>
ceph device ls 2>/dev/null | awk "NR>1 {print \$2, \$3}"</code></pre>
</div>

<h3>2.4 ZFS Pool ('zfs-ha') Drive Mapping</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">ALL NODES (prox22, prox23, prox24)</span></div>
  <pre><code><span class="comment"># Check ZFS pools across the cluster</span>
for ip in 10.31.6.172 10.31.6.173 10.31.6.174; do
    echo "=== $ip ==="
    ssh root@$ip "zpool list; zfs list -o name,mountpoint 2>/dev/null"
done

<span class="comment"># Query physical disk members of 'zfs-ha' pool with persistent paths</span>
ssh root@10.31.6.172 "zpool status -P -v zfs-ha"
ssh root@10.31.6.173 "zpool status -P -v zfs-ha"
ssh root@10.31.6.174 "zpool status -P -v zfs-ha"</code></pre>
</div>


<!-- SECTION 3: STICKER FINDER & LED BLINKER -->
<h2>3. Phase 2 — Physical Hard Drive Finder & LED Blinker Deployment</h2>
<p>Developed and deployed customized automation tools to help technicians identify physical drive caddies and blink server LEDs before applying physical stickers.</p>

<h3>3.1 Deploying Finder Tooling to /output/ Across All 3 Nodes</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH / SCP</span><span class="node-tag">DEPLOY TO CLUSTER</span></div>
  <pre><code><span class="comment"># Create /output directories and deploy sticker finder scripts & dashboard</span>
for ip in 10.31.6.172 10.31.6.173 10.31.6.174; do
    echo "=== Deploying to $ip ==="
    ssh root@$ip "mkdir -p /output /output/bin"
    scp harddrive-sticker-finder.sh root@$ip:/output/harddrive-sticker-finder.sh
    scp cluster_drive_stickers_viewer.html root@$ip:/output/cluster_drive_stickers_viewer.html
    ssh root@$ip "chmod +x /output/harddrive-sticker-finder.sh && ls -lh /output"
done</code></pre>
</div>

<h3>3.2 Running Hardware Scan on Cluster Nodes</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">RUN ON EACH NODE</span></div>
  <pre><code><span class="comment"># Scan local server hardware (Outputs table with Slot, Role, Device, S/N, Model)</span>
/output/harddrive-sticker-finder.sh --scan

<span class="comment"># Remote scan execution from workstation over SSH</span>
ssh root@10.31.6.172 '/output/harddrive-sticker-finder.sh --scan'
ssh root@10.31.6.173 '/output/harddrive-sticker-finder.sh --scan'
ssh root@10.31.6.174 '/output/harddrive-sticker-finder.sh --scan'</code></pre>
</div>

<h3>3.3 Physical Drive Locator LED Blinking via Dell PERC</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">PHYSICAL IDENTIFICATION</span></div>
  <pre><code><span class="comment"># Blink drive caddy activity/locate LED by Serial Number for 15 seconds</span>
/output/harddrive-sticker-finder.sh --blink ZYDGFEW6 15

<span class="comment"># Low-level Dell PERCCLI commands used under the hood to start/stop locate:</span>
/opt/MegaRAID/perccli/perccli64 /c0/e252/s0 start locate
sleep 15
/opt/MegaRAID/perccli/perccli64 /c0/e252/s0 stop locate</code></pre>
</div>

<!-- SECTION 4: EXPORTERS INSTALLATION -->
<h2>4. Phase 3 — Prometheus Exporters Full Installation (All 3 Nodes)</h2>
<p>Step-by-step commands used to deploy, configure, and activate all 5 monitoring exporters across <code>prox22</code>, <code>prox23</code>, and <code>prox24</code>.</p>

<h3>4.1 Exporter 1: Node Exporter (Port 9100) — OS, CPU, RAM & Disk IO</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH</span><span class="node-tag">ALL 3 NODES</span></div>
  <pre><code><span class="comment"># 1. Install package via apt</span>
apt-get update &amp;&amp; apt-get install -y prometheus-node-exporter

<span class="comment"># 2. Enable and start systemd service</span>
systemctl enable --now prometheus-node-exporter

<span class="comment"># 3. Verify metrics endpoint</span>
curl -s http://localhost:9100/metrics | grep -E "node_cpu_seconds_total|node_memory_MemTotal_bytes" | head -n 5</code></pre>
</div>

<h3>4.2 Exporter 2: IPMI Exporter (Port 9290) — Dell Fans, Temps & PSUs</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH</span><span class="node-tag">ALL 3 NODES</span></div>
  <pre><code><span class="comment"># 1. Install exporter package and low-level IPMI driver tools</span>
apt-get install -y prometheus-ipmi-exporter freeipmi-tools ipmitool

<span class="comment"># 2. Load and persist kernel IPMI modules</span>
modprobe ipmi_si ipmi_devintf
cat &lt;&lt; 'EOF' > /etc/modules-load.d/ipmi.conf
ipmi_si
ipmi_devintf
EOF

<span class="comment"># 3. Configure local IPMI collection profile in /etc/default/prometheus-ipmi-exporter</span>
cat &lt;&lt; 'EOF' > /etc/default/prometheus-ipmi-exporter
ARGS="--config.file=/usr/share/doc/prometheus-ipmi-exporter/examples/ipmi_local.yml"
EOF

<span class="comment"># 4. Configure service to execute as root to access /dev/ipmi0</span>
sed -i 's/^User=prometheus/User=root/' /lib/systemd/system/prometheus-ipmi-exporter.service 2>/dev/null || true
systemctl daemon-reload
systemctl enable --now prometheus-ipmi-exporter

<span class="comment"># 5. Verify sensor metrics output</span>
curl -s http://localhost:9290/metrics | grep -E "ipmi_fan_speed_rpm|ipmi_temperature_celsius" | head -n 5</code></pre>
</div>


<h3>4.3 Exporter 3: Smartctl Exporter (Port 9633) — Drive S.M.A.R.T Health</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH</span><span class="node-tag">ALL 3 NODES</span></div>
  <pre><code><span class="comment"># 1. Ensure smartmontools is present</span>
apt-get install -y smartmontools

<span class="comment"># 2. Copy pre-built smartctl_exporter binary to system binary path</span>
cp /output/bin/smartctl_exporter /usr/local/bin/smartctl_exporter
chmod 755 /usr/local/bin/smartctl_exporter

<span class="comment"># 3. Create systemd service with Dell PERC virtual disk exclusion (--smartctl.device-exclude=sdm)</span>
cat &lt;&lt; 'EOF' > /etc/systemd/system/smartctl_exporter.service
[Unit]
Description=Prometheus Smartctl Exporter (Drive Health &amp; Temps)
Documentation=https://github.com/prometheus-community/smartctl_exporter
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/smartctl_exporter --web.listen-address=:9633 --smartctl.device-exclude=sdm
Restart=always
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

<span class="comment"># 4. Reload systemd, enable, and start</span>
systemctl daemon-reload
systemctl enable --now smartctl_exporter

<span class="comment"># 5. Verify drive health metrics</span>
curl -s http://localhost:9633/metrics | grep -E "smartctl_device_temperature|smartctl_device_status" | head -n 5</code></pre>
</div>

<h3>4.4 Exporter 4: Ceph Prometheus Exporter (Port 9283) — Ceph MGR Module</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH</span><span class="node-tag">PROXMOX / CEPH CLUSTER</span></div>
  <pre><code><span class="comment"># 1. Enable native Prometheus exporter module inside Ceph Manager</span>
ceph mgr module enable prometheus

<span class="comment"># 2. Set listening port and bind address</span>
ceph config set mgr mgr/prometheus/server_port 9283
ceph config set mgr mgr/prometheus/server_addr 0.0.0.0

<span class="comment"># 3. Check Ceph Manager status and verify active manager node</span>
ceph mgr stat

<span class="comment"># 4. Verify metric emission on the active Ceph manager (prox22)</span>
curl -s http://10.31.6.172:9283/metrics | grep -E "ceph_health_status|ceph_mon_quorum_status" | head -n 5</code></pre>
</div>

<h3>4.5 Exporter 5: ZFS Exporter (Port 9134) — 'zfs-ha' Pool & ARC Stats</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH</span><span class="node-tag">ALL 3 NODES</span></div>
  <pre><code><span class="comment"># 1. Copy pre-built zfs_exporter binary to system binary path</span>
cp /output/bin/zfs_exporter /usr/local/bin/zfs_exporter
chmod 755 /usr/local/bin/zfs_exporter

<span class="comment"># 2. Create systemd service for ZFS metrics</span>
cat &lt;&lt; 'EOF' > /etc/systemd/system/zfs_exporter.service
[Unit]
Description=Prometheus ZFS Exporter (zfs-ha Pool &amp; ARC Stats)
Documentation=https://github.com/pdf/zfs_exporter
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/zfs_exporter --web.listen-address=:9134
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

<span class="comment"># 3. Reload systemd, enable, and start</span>
systemctl daemon-reload
systemctl enable --now zfs_exporter

<span class="comment"># 4. Verify ZFS metrics</span>
curl -s http://localhost:9134/metrics | grep -E "zfs_pool_health|zfs_arc_hits" | head -n 5</code></pre>
</div>


<!-- SECTION 5: AUTOMATED HEALTH CHECK -->
<h2>5. Phase 4 — Unified Exporter Automation & Health Checker</h2>
<p>Developed <code>/output/install-cluster-exporters.sh</code> to streamline one-touch deployments and live multi-node status verifications.</p>

<h3>5.1 Local Node Health Check</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH</span><span class="node-tag">RUN ON TARGET HOST</span></div>
  <pre><code>/output/install-cluster-exporters.sh --status localhost</code></pre>
</div>

<h3>5.2 Entire Cluster Multi-Node Health Check</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>BASH</span><span class="node-tag">RUN FROM ANY NODE</span></div>
  <pre><code>/output/install-cluster-exporters.sh --status cluster</code></pre>
</div>

<div class="alert-box success">
  <strong>Live Execution Output on All 3 Nodes:</strong><br>
  • <strong>prox22 (10.31.6.172):</strong> Node (6,037 metrics) • IPMI (346 metrics) • Smartctl (733 metrics) • <strong>Ceph (358 metrics - Active MGR)</strong> • ZFS (109 metrics)<br>
  • <strong>prox23 (10.31.6.173):</strong> Node (7,769 metrics) • IPMI (346 metrics) • Smartctl (732 metrics) • <strong>Ceph (STANDBY - Active on prox22)</strong> • ZFS (109 metrics)<br>
  • <strong>prox24 (10.31.6.174):</strong> Node (7,774 metrics) • IPMI (346 metrics) • Smartctl (732 metrics) • <strong>Ceph (STANDBY - Active on prox22)</strong> • ZFS (109 metrics)
</div>

<!-- SECTION 6: CEPH HA TROUBLESHOOTING -->
<h2>6. Phase 5 — Ceph HA Architecture Diagnosis & Port 9283 Resolution</h2>
<p>When running health checks on <code>prox24</code>, port 9283 returned 0 metrics. Here are the exact diagnostic commands executed to uncover Ceph's High Availability manager behavior:</p>

<h3>6.1 Diagnosing Port 9283 and Ceph Manager State</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">CLUSTER DIAGNOSTICS</span></div>
  <pre><code><span class="comment"># 1. Check which daemon is listening on port 9283 across all 3 nodes</span>
ssh root@10.31.6.172 "ss -tulpn | grep 9283"
ssh root@10.31.6.173 "ss -tulpn | grep 9283"
ssh root@10.31.6.174 "ss -tulpn | grep 9283"

<span class="comment"># 2. Query Ceph Manager active and standby election state</span>
ceph mgr stat
<span class="comment"># Output: {"epoch": 66, "available": true, "active_name": "prox22", "num_standby": 2}</span>

<span class="comment"># 3. Inspect HTTP response code and payload size on each node</span>
curl -I -s http://10.31.6.172:9283/metrics  <span class="comment"># HTTP 200, Content-Length: 32789 (Active)</span>
curl -I -s http://10.31.6.173:9283/metrics  <span class="comment"># HTTP 200, Content-Length: 0     (Standby)</span>
curl -I -s http://10.31.6.174:9283/metrics  <span class="comment"># HTTP 200, Content-Length: 0     (Standby)</span>

<span class="comment"># 4. Check root web endpoint on standby node (prox24)</span>
curl -s http://10.31.6.174:9283/
<span class="comment"># Returns HTML pointing to active manager: &lt;a href='http://192.168.10.22:9283/metrics'&gt;</span></code></pre>
</div>

<div class="alert-box">
  <strong>Ceph Architectural Rule:</strong> Ceph Manager operates in <strong>Active/Standby mode</strong>. Only the currently elected Active MGR (<code>prox22</code>) serves cluster-wide metrics. Standby MGRs (<code>prox23</code> and <code>prox24</code>) intentionally return 0 metrics to prevent Prometheus from collecting duplicate timeseries. If <code>prox22</code> reboots, Ceph automatically fails over to <code>prox23</code> or <code>prox24</code>, which will immediately begin emitting the full metrics.
</div>


<!-- SECTION 7: DECOMMISSIONING OLD PROMETHEUS -->
<h2>7. Phase 6 — Removal of Old Standalone Prometheus Server on prox22</h2>
<p>An old standalone Prometheus installation (created August 24, 2026) was identified on <code>prox22</code> at <code>/opt/prometheus</code> listening on port 9090. Since Prometheus runs on a dedicated external server, the local instance was completely decommissioned.</p>

<h3>7.1 Inspecting Old Prometheus Files & Service</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">prox22 (10.31.6.172)</span></div>
  <pre><code><span class="comment"># Check status and file paths</span>
systemctl status prometheus --no-pager
ls -la /opt/prometheus
ls -l /etc/systemd/system/prometheus.service</code></pre>
</div>

<h3>7.2 Decommissioning & Removal Commands</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">prox22 (10.31.6.172)</span></div>
  <pre><code><span class="comment"># 1. Stop the running Prometheus server process</span>
systemctl stop prometheus

<span class="comment"># 2. Disable systemd service from booting automatically</span>
systemctl disable prometheus

<span class="comment"># 3. Delete systemd service unit file & reload daemon</span>
rm -f /etc/systemd/system/prometheus.service
systemctl daemon-reload
systemctl reset-failed

<span class="comment"># 4. Delete binary and TSDB data directory (~250MB freed)</span>
rm -rf /opt/prometheus</code></pre>
</div>

<h3>7.3 Post-Removal Verification</h3>
<div class="cmd-box">
  <div class="cmd-header"><span>SSH</span><span class="node-tag">prox22 (10.31.6.172)</span></div>
  <pre><code><span class="comment"># 1. Verify service is completely gone</span>
systemctl status prometheus --no-pager
<span class="comment"># Output: Unit prometheus.service could not be found.</span>

<span class="comment"># 2. Verify port 9090 is closed</span>
ss -tulpn | grep 9090
<span class="comment"># Output: &lt;empty&gt; (Port closed)</span>

<span class="comment"># 3. Verify directory is deleted</span>
ls -ld /opt/prometheus
<span class="comment"># Output: ls: cannot access '/opt/prometheus': No such file or directory</span>

<span class="comment"># 4. Verify all 5 cluster exporters remain 100% active</span>
/output/install-cluster-exporters.sh --status localhost</code></pre>
</div>

<!-- SECTION 8: EXTERNAL PROMETHEUS CONFIG -->
<h2>8. Phase 7 — External Prometheus Server Scrape Configuration</h2>
<p>The scrape configuration specification to place in your <strong>dedicated external Prometheus server's</strong> <code>prometheus.yml</code> file:</p>

<div class="cmd-box">
  <div class="cmd-header"><span>YAML</span><span class="node-tag">EXTERNAL PROMETHEUS CONFIGURATION</span></div>
  <pre><code><span class="param">scrape_configs</span>:
  <span class="comment"># 1. Proxmox OS &amp; System Performance (CPU, RAM, Disks, Network)</span>
  - <span class="param">job_name</span>: 'proxmox-nodes'
    <span class="param">scrape_interval</span>: 15s
    <span class="param">static_configs</span>:
      - <span class="param">targets</span>:
          - '10.31.6.172:9100'
          - '10.31.6.173:9100'
          - '10.31.6.174:9100'

  <span class="comment"># 2. Dell Server Hardware Sensors (Fans RPM, Temperatures, Power Supplies)</span>
  - <span class="param">job_name</span>: 'proxmox-ipmi'
    <span class="param">scrape_interval</span>: 30s
    <span class="param">scrape_timeout</span>: 20s
    <span class="param">static_configs</span>:
      - <span class="param">targets</span>:
          - '10.31.6.172:9290'
          - '10.31.6.173:9290'
          - '10.31.6.174:9290'

  <span class="comment"># 3. Hard Drive S.M.A.R.T Health (Drive Wear, Bad Sectors, Temperatures)</span>
  - <span class="param">job_name</span>: 'proxmox-smartctl'
    <span class="param">scrape_interval</span>: 60s
    <span class="param">scrape_timeout</span>: 45s
    <span class="param">static_configs</span>:
      - <span class="param">targets</span>:
          - '10.31.6.172:9633'
          - '10.31.6.173:9633'
          - '10.31.6.174:9633'

  <span class="comment"># 4. Ceph Cluster &amp; OSD Metrics (Scraped from Ceph MGRs with auto failover)</span>
  - <span class="param">job_name</span>: 'ceph-mgr'
    <span class="param">scrape_interval</span>: 15s
    <span class="param">static_configs</span>:
      - <span class="param">targets</span>:
          - '10.31.6.172:9283'
          - '10.31.6.173:9283'
          - '10.31.6.174:9283'

  <span class="comment"># 5. ZFS Pool Health &amp; ARC Metrics ('zfs-ha' RAID-Z2 Pool)</span>
  - <span class="param">job_name</span>: 'proxmox-zfs'
    <span class="param">scrape_interval</span>: 30s
    <span class="param">static_configs</span>:
      - <span class="param">targets</span>:
          - '10.31.6.172:9134'
          - '10.31.6.173:9134'
          - '10.31.6.174:9134'</code></pre>
</div>


<!-- SECTION 9: MASTER CHEAT SHEET -->
<h2>9. Master Quick-Reference Command Table</h2>
<p>Consolidated summary of essential operations commands across the cluster:</p>

<table>
  <thead>
    <tr>
      <th>Task / Operation</th>
      <th>Command</th>
      <th>Target Node</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Full Cluster Exporter Health</strong></td>
      <td><code>/output/install-cluster-exporters.sh --status cluster</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Local Exporter Health</strong></td>
      <td><code>/output/install-cluster-exporters.sh --status localhost</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Hard Drive Bay &amp; Role Scan</strong></td>
      <td><code>/output/harddrive-sticker-finder.sh --scan</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Blink Physical Drive LED</strong></td>
      <td><code>/output/harddrive-sticker-finder.sh --blink &lt;SERIAL&gt; 15</code></td>
      <td>Target Node</td>
    </tr>
    <tr>
      <td><strong>Check Active Ceph MGR</strong></td>
      <td><code>ceph mgr stat</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Check ZFS Pool Status</strong></td>
      <td><code>zpool status -v zfs-ha</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Restart Smartctl Exporter</strong></td>
      <td><code>systemctl restart smartctl_exporter</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Restart IPMI Exporter</strong></td>
      <td><code>systemctl restart prometheus-ipmi-exporter</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Restart ZFS Exporter</strong></td>
      <td><code>systemctl restart zfs_exporter</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Restart Node Exporter</strong></td>
      <td><code>systemctl restart prometheus-node-exporter</code></td>
      <td>Any Node</td>
    </tr>
    <tr>
      <td><strong>Verify Ceph Metrics</strong></td>
      <td><code>curl -s http://10.31.6.172:9283/metrics | head -n 10</code></td>
      <td>Active MGR</td>
    </tr>
  </tbody>
</table>

<div style="margin-top: 30px; text-align: center; font-size: 8pt; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 10px;">
  Document compiled autonomously on September 19, 2026 • Proxmox VE 3-Node Cluster Infrastructure Runbook
</div>

</body>
</html>
"""

html_path = "/home/nishusaini/Desktop/Innspark/Proxmox Cluster/Harddrive and Package finder /Proxmox_Cluster_Complete_Commands_Runbook.html"
pdf_path = "/home/nishusaini/Desktop/Innspark/Proxmox Cluster/Harddrive and Package finder /Proxmox_Cluster_Complete_Commands_Runbook.pdf"

with open(html_path, "w") as f:
    f.write(html_content)

print("HTML runbook written. Now rendering to PDF via headless Chrome...")
cmd = [
    "google-chrome",
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--print-to-pdf=" + pdf_path,
    html_path
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Chrome returncode:", res.returncode)
print("Chrome stdout:", res.stdout)
print("Chrome stderr:", res.stderr)
if os.path.exists(pdf_path):
    size = os.path.getsize(pdf_path)
    print(f"Success! PDF created at: {pdf_path} ({size} bytes)")
else:
    print("PDF generation failed.")
