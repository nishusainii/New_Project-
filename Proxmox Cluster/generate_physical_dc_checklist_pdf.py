import os
import subprocess

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Proxmox VE Cluster - Datacenter Physical Testing & Command Runbook</title>
<style>
  @page {
    size: A4 portrait;
    margin: 5mm 7mm 7mm 7mm;
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 7pt;
      color: #64748b;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    }
    @bottom-left {
      content: "Innspark / CISAI Infrastructure • 3-Node Physical Command Runbook (cisai-pve)";
      font-size: 7pt;
      color: #64748b;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    }
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #0f172a;
    line-height: 1.20;
    font-size: 7pt;
    margin: 0;
    padding: 0;
    background: #ffffff;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  /* Header */
  .header-card {
    background: linear-gradient(135deg, #090d16 0%, #1e293b 55%, #0284c7 100%);
    color: white;
    padding: 7px 10px;
    border-radius: 4px;
    margin-bottom: 4px;
  }
  .header-card h1 {
    margin: 0 0 1px 0;
    font-size: 11.5pt;
    font-weight: 800;
    letter-spacing: -0.2px;
  }
  .header-card .subtitle {
    font-size: 7.2pt;
    color: #bae6fd;
    margin-bottom: 3px;
    font-weight: 500;
  }
  .meta-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 4px;
    background: rgba(255, 255, 255, 0.08);
    padding: 3px 5px;
    border-radius: 3px;
    border: 1px solid rgba(255, 255, 255, 0.15);
  }
  .meta-item .label {
    font-size: 4.8pt;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #94a3b8;
  }
  .meta-item .value {
    font-size: 6.5pt;
    font-weight: 700;
    color: #ffffff;
  }

  /* Section Titles */
  .section-title {
    font-size: 8pt;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 1.5px solid #0284c7;
    padding-bottom: 1px;
    margin: 5px 0 3px 0;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .section-title .badge {
    background: #0284c7;
    color: white;
    font-size: 5.2pt;
    padding: 1px 3px;
    border-radius: 2px;
    font-weight: 700;
    text-transform: uppercase;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 4px;
    font-size: 6.4pt;
  }
  th {
    background: #f1f5f9;
    color: #334155;
    font-weight: 700;
    text-align: left;
    padding: 2px 3.5px;
    border: 1px solid #cbd5e1;
    font-size: 6pt;
    text-transform: uppercase;
  }
  td {
    padding: 2px 3.5px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
  }
  tr:nth-child(even) td {
    background-color: #f8fafc;
  }

  /* 3-Node Cards Grid */
  .node-matrix-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    margin-bottom: 4px;
  }
  .node-matrix-card {
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    background: #f8fafc;
    padding: 3px 4px;
  }
  .node-matrix-title {
    font-weight: 800;
    font-size: 7.2pt;
    color: #0f172a;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 1px;
    margin-bottom: 2px;
    display: flex;
    justify-content: space-between;
  }
  .node-test-item {
    margin-bottom: 3px;
    font-size: 6.3pt;
    line-height: 1.18;
  }
  .node-test-header {
    font-weight: 700;
    color: #0f172a;
  }
  .mini-cmd {
    background: #090d16;
    color: #38bdf8;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 5.8pt;
    padding: 1.5px 3px;
    border-radius: 2px;
    margin: 1px 0;
    border-left: 2px solid #38bdf8;
    word-break: break-all;
    line-height: 1.15;
  }

  /* Badges */
  .badge-run {
    display: inline-block;
    background: #0f172a;
    color: #38bdf8;
    font-family: ui-monospace, monospace;
    font-size: 5.5pt;
    font-weight: 700;
    padding: 1px 3px;
    border-radius: 2px;
    border: 1px solid #334155;
  }
  .badge-action {
    display: inline-block;
    background: #b91c1c;
    color: #ffffff;
    font-family: ui-monospace, monospace;
    font-size: 5.5pt;
    font-weight: 700;
    padding: 1px 3px;
    border-radius: 2px;
  }
  .badge-restore {
    display: inline-block;
    background: #15803d;
    color: #ffffff;
    font-family: ui-monospace, monospace;
    font-size: 5.5pt;
    font-weight: 700;
    padding: 1px 3px;
    border-radius: 2px;
  }
  .status-tag {
    display: inline-block;
    padding: 1px 3px;
    border-radius: 2px;
    font-size: 5.5pt;
    font-weight: 700;
  }
  .tag-success { background: #dcfce7; color: #15803d; }
  .tag-pending { background: #fef3c7; color: #b45309; }
  .tag-info    { background: #e0f2fe; color: #0369a1; }
  .tag-danger  { background: #fee2e2; color: #b91c1c; }

  /* Test Box */
  .test-box {
    border: 1px solid #cbd5e1;
    border-radius: 3px;
    margin-bottom: 3px;
    background: #ffffff;
    page-break-inside: avoid;
  }
  .test-box-header {
    background: #f8fafc;
    padding: 2px 4px;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 750;
    font-size: 7pt;
  }
  .test-box-body {
    padding: 2.5px 4px;
  }

  /* Code & Command Boxes */
  .cmd-block {
    background: #090d16;
    color: #f8fafc;
    padding: 2px 4px;
    border-radius: 2px;
    margin: 1px 0 2px 0;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 6.2pt;
    border-left: 2px solid #38bdf8;
    line-height: 1.18;
  }
  .cmd-block .cmd { color: #38bdf8; font-weight: 700; }
  .cmd-block .out { color: #86efac; }
  .cmd-block .comment { color: #94a3b8; }
  .cmd-block .param { color: #fde047; }

  .check-circle {
    display: inline-block;
    width: 7.5px;
    height: 7.5px;
    border: 1.2px solid #0284c7;
    border-radius: 2px;
    vertical-align: middle;
    margin-right: 2px;
  }

  .signoff-box {
    border: 1px dashed #64748b;
    border-radius: 3px;
    padding: 3px 5px;
    margin-top: 3px;
    background: #f8fafc;
    page-break-inside: avoid;
  }
  .signoff-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    margin-top: 2px;
    font-size: 6.2pt;
  }
  .signoff-field {
    border-bottom: 1px solid #94a3b8;
    padding-bottom: 1px;
  }

  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<!-- Header Card -->
<div class="header-card">
  <h1>PROXMOX VE CLUSTER — DATACENTER PHYSICAL TESTING RUNBOOK</h1>
  <div class="subtitle">Complete Node-by-Node Execution Commands, 19 Excel Scenarios & Real-Time Verification Matrix</div>
  <div class="meta-grid">
    <div class="meta-item">
      <div class="label">Cluster Name</div>
      <div class="value">cisai-pve</div>
    </div>
    <div class="meta-item">
      <div class="label">CRM Master Node</div>
      <div class="value">prox22 (10.31.6.172)</div>
    </div>
    <div class="meta-item">
      <div class="label">Storage Backend</div>
      <div class="value">Ceph (12 OSDs) + ZFS RAIDZ2</div>
    </div>
    <div class="meta-item">
      <div class="label">Execution Date</div>
      <div class="value">September 24, 2026</div>
    </div>
  </div>
</div>

<!-- Section 1: Detailed 3-Node Matrix WITH Exact Commands Inside Each Card -->
<div class="section-title">
  <span class="badge">Coverage</span> 1. Dedicated 3-Node Physical Test Distribution & Exact Node Commands
</div>

<div class="node-matrix-grid">
  <!-- Node 1: prox22 -->
  <div class="node-matrix-card" style="border-top: 2.5px solid #0284c7;">
    <div class="node-matrix-title">
      <span>prox22 (CRM Leader)</span>
      <span class="status-tag tag-info">Node ID: 2</span>
    </div>
    <div style="font-size: 5.8pt; color: #475569; margin-bottom: 2px;">
      Host: <strong>10.31.6.172</strong> &bull; BMC: <strong>10.31.5.78</strong> &bull; 10G: <strong>192.168.10.22</strong>
    </div>

    <!-- Item 1 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> Pre-Flight Leader Health Check:</div>
      <div class="mini-cmd">pvecm status &amp;&amp; ceph -s &amp;&amp; ha-manager status</div>
    </div>

    <!-- Item 2 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> Single PSU Pull (Redundant Power):</div>
      <div class="mini-cmd">Unplug PSU 1 &rarr; dmesg -T | tail -n 10 &amp;&amp; pvecm status</div>
    </div>

    <!-- Item 3 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-01/07 Live Ceph HDD Hot-Pull (osd.0):</div>
      <div class="mini-cmd">Unlatch Slot 1 &rarr; ceph health detail &amp;&amp; ceph osd tree</div>
    </div>

    <!-- Item 4 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-04 Drive Slot Swap (Slot 1 &rarr; 3):</div>
      <div class="mini-cmd">ls -l /dev/disk/by-id/wwn-* &amp;&amp; lsblk -o NAME,WWN</div>
    </div>

    <!-- Item 5 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-09 Dual-Node Survivor Safe Freeze:</div>
      <div class="mini-cmd">pvecm status (1 vote) &amp;&amp; ls -la /etc/pve (read-only)</div>
    </div>
  </div>

  <!-- Node 2: prox23 -->
  <div class="node-matrix-card" style="border-top: 2.5px solid #0284c7;">
    <div class="node-matrix-title">
      <span>prox23 (Member Node)</span>
      <span class="status-tag tag-info">Node ID: 3</span>
    </div>
    <div style="font-size: 5.8pt; color: #475569; margin-bottom: 2px;">
      Host: <strong>10.31.6.173</strong> &bull; BMC: <strong>10.31.5.61</strong> &bull; 10G: <strong>192.168.10.23</strong>
    </div>

    <!-- Item 1 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> Single PSU Pull (Redundant Power):</div>
      <div class="mini-cmd">Unplug PSU 1 &rarr; ipmitool -H 10.31.5.61 sel elist</div>
    </div>

    <!-- Item 2 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-13 ZFS OS Boot Mirror SSD Pull:</div>
      <div class="mini-cmd">Unlatch OS SSD &rarr; zpool status rpool (DEGRADED)</div>
    </div>

    <!-- Item 3 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-14 SSD Re-insert &amp; Resilver Scrub:</div>
      <div class="mini-cmd">zpool online rpool &lt;ssd&gt; &amp;&amp; zpool scrub rpool</div>
    </div>

    <!-- Item 4 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-09 Dual-Node Drop Participant:</div>
      <div class="mini-cmd">Pull power with prox24 &rarr; Restore &rarr; pvecm status</div>
    </div>

    <!-- Item 5 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> Secondary HA VM Migration Target:</div>
      <div class="mini-cmd">qm list &amp;&amp; systemctl status pve-ha-lrm</div>
    </div>
  </div>

  <!-- Node 3: prox24 -->
  <div class="node-matrix-card" style="border-top: 2.5px solid #0284c7;">
    <div class="node-matrix-title">
      <span>prox24 (Member Node)</span>
      <span class="status-tag tag-info">Node ID: 1</span>
    </div>
    <div style="font-size: 5.8pt; color: #475569; margin-bottom: 2px;">
      Host: <strong>10.31.6.174</strong> &bull; BMC: <strong>10.31.5.62</strong> &bull; 10G: <strong>192.168.10.24</strong>
    </div>

    <!-- Item 1 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> Single PSU Pull (0 Packet Drop):</div>
      <div class="mini-cmd">Unplug PSU 1 &rarr; ping 10.31.6.174 (0% loss)</div>
    </div>

    <!-- Item 2 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-08 Dual-PSU Hard Power Cut (HA Failover):</div>
      <div class="mini-cmd">Pull BOTH cords &rarr; On prox22: ha-manager status</div>
    </div>

    <!-- Item 3 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-10 10G DAC Storage Cable Pull:</div>
      <div class="mini-cmd">Unplug DAC &rarr; ip a show nic3 &amp;&amp; ping 10.31.6.172</div>
    </div>

    <!-- Item 4 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> TC-11 1G Management Cable Pull:</div>
      <div class="mini-cmd">Unplug RJ45 &rarr; Watchdog fences node in 60s</div>
    </div>

    <!-- Item 5 -->
    <div class="node-test-item">
      <div class="node-test-header"><span class="check-circle"></span> Clean Auto-Rejoin Verification:</div>
      <div class="mini-cmd">Replug &rarr; pvecm status (3/3 votes) &amp;&amp; ceph -s</div>
    </div>
  </div>
</div>

<!-- Section 2: Complete 19-Scenario Excel Traceability Matrix with Exact Commands -->
<div class="section-title">
  <span class="badge">Excel Matrix</span> 2. Traceability of All 19 Scenarios in `Manual Test Case proxmox.xlsx` & Commands
</div>

<table>
  <thead>
    <tr>
      <th>TC #</th>
      <th>Excel Test Condition</th>
      <th>Steps</th>
      <th>Target Node</th>
      <th>Exact Terminal Command to Execute / Verify</th>
      <th>Expected Physical Result</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>TC-01</strong></td>
      <td>Remove 1 Disk from 1 Server</td>
      <td>1–3</td>
      <td><code>prox22</code></td>
      <td><code>ceph osd tree; watch -n 1 "ceph -s; ceph health detail"</code></td>
      <td>Unlatch Slot 1 (/dev/sdb); Ceph flags HEALTH_WARN; 0 VM freeze.</td>
    </tr>
    <tr>
      <td><strong>TC-02</strong></td>
      <td>Remove 2 Disks from 1 Server</td>
      <td>4–6</td>
      <td><code>prox22</code></td>
      <td><code>ceph health detail; rbd bench-write --pool ceph testimg</code></td>
      <td>Pull Slot 1 & 2; 3x replica keeps data 100% accessible.</td>
    </tr>
    <tr>
      <td><strong>TC-03</strong></td>
      <td>Remove 3 Disks from 1 Server</td>
      <td>7–9</td>
      <td><code>prox22</code></td>
      <td><code>ceph osd tree; ceph pg stat; qm status 9001</code></td>
      <td>Pull Slot 1, 2, 3; degraded PGs remain readable via prox23/24.</td>
    </tr>
    <tr>
      <td><strong>TC-04</strong></td>
      <td>Slot One to Slot Three Swap</td>
      <td>10–12</td>
      <td><code>prox22</code></td>
      <td><code>ls -l /dev/disk/by-id/wwn-*; lsblk -o NAME,WWN,SERIAL</code></td>
      <td>Move drive from Slot 1 &rarr; 3; IT-mode auto-detects permanent WWN.</td>
    </tr>
    <tr>
      <td><strong>TC-05</strong></td>
      <td>Remove All Disks from Node</td>
      <td>13–15</td>
      <td><code>prox24</code></td>
      <td><code>ceph osd tree | grep prox24; ping -c 3 10.31.6.174</code></td>
      <td>Unseat all 4 Ceph drives; node stays up; VMs read from prox22/23.</td>
    </tr>
    <tr>
      <td><strong>TC-06</strong></td>
      <td>Remove 2 Disks Across 2 Nodes</td>
      <td>16–18</td>
      <td><code>prox22,23</code></td>
      <td><code>ceph -s; ceph health detail; fio --name=test --size=1G ...</code></td>
      <td>Pull 1 drive on prox22 + 1 on prox23; min_size 2 safeguards data.</td>
    </tr>
    <tr>
      <td><strong>TC-07</strong></td>
      <td>Hot Remove Disks While Running</td>
      <td>19–21</td>
      <td><code>prox22</code></td>
      <td><code>dmesg -wT; rbd-nbd map ceph/testimg; fio --rw=randwrite ...</code></td>
      <td>Pull drive during active fio run; kernel releases SCSI cleanly.</td>
    </tr>
    <tr>
      <td><strong>TC-08</strong></td>
      <td>Simulate Node Failure (Power Off)</td>
      <td>22–24</td>
      <td><code>prox24</code></td>
      <td><code>ha-manager status; watch -n 1 "pvecm status; qm list"</code></td>
      <td>Pull BOTH power cords on prox24; HA auto-restarts VM in 60–120s.</td>
    </tr>
    <tr>
      <td><strong>TC-09</strong></td>
      <td>Dual Node Failure (Power Off 2)</td>
      <td>25–27</td>
      <td><code>prox23,24</code></td>
      <td><code>pvecm status; ha-manager status; ls -la /etc/pve</code></td>
      <td>Pull power on prox23 & 24; prox22 (1 vote) enters read-only freeze.</td>
    </tr>
    <tr>
      <td><strong>TC-10</strong></td>
      <td>Network Failure (One Cable)</td>
      <td>28–30</td>
      <td><code>prox24</code></td>
      <td><code>ip a show nic3; ping -c 3 10.31.6.172; pvecm status</code></td>
      <td>Unplug 10G DAC; management ping OK (3/3 votes); Ceph isolates.</td>
    </tr>
    <tr>
      <td><strong>TC-11</strong></td>
      <td>Network Failure (Two Cables/Mgmt)</td>
      <td>31–33</td>
      <td><code>prox24</code></td>
      <td><code>watch -n 1 "pvecm status"; dmesg -T | grep -i watchdog</code></td>
      <td>Unplug 1G Mgmt RJ45; hardware watchdog reboots node & HA migrates.</td>
    </tr>
    <tr>
      <td><strong>TC-12</strong></td>
      <td>Software Disk Failure (ZFS)</td>
      <td>35–37</td>
      <td><code>prox24</code></td>
      <td><code>zpool offline zfs-ha &lt;disk&gt;; dd if=/dev/urandom of=/dev/zvol/...</code></td>
      <td>Degraded pool sustains 957 MB/s unbuffered writes with 0 errors.</td>
    </tr>
    <tr>
      <td><strong>TC-13</strong></td>
      <td>Physical Disk Failure (ZFS SSD)</td>
      <td>38–40</td>
      <td><code>prox23</code></td>
      <td><code>zpool status rpool; pveversion -v; systemctl status pveproxy</code></td>
      <td>Pull 1 OS Boot SSD; rpool enters DEGRADED; host stays 100% up.</td>
    </tr>
    <tr>
      <td><strong>TC-14</strong></td>
      <td>Replace a Disk with a New One</td>
      <td>41–43</td>
      <td><code>prox23</code></td>
      <td><code>zpool online rpool &lt;disk&gt;; zpool scrub rpool; zpool status</code></td>
      <td>Re-insert SSD; zpool scrub finishes resilver in &lt; 10s with 0 errors.</td>
    </tr>
    <tr>
      <td><strong>TC-15</strong></td>
      <td>Disk Pull During Live Migration</td>
      <td>41b–43b</td>
      <td><code>prox22 &rarr; 24</code></td>
      <td><code>qm migrate 9001 prox24 --online 1; ceph osd out &lt;osd&gt;</code></td>
      <td>RAM live migration over 10G DAC completes in 23ms despite drive loss.</td>
    </tr>
    <tr>
      <td><strong>TC-16</strong></td>
      <td>Multiple OSD Failures Exceeding Min</td>
      <td>44–46</td>
      <td>Cluster</td>
      <td><code>ceph osd pool get ceph min_size; ceph health detail</code></td>
      <td>Verified min_size 2 prevents split-brain write corruption.</td>
    </tr>
    <tr>
      <td><strong>TC-17</strong></td>
      <td>Ceph Monitor Failure</td>
      <td>47–49</td>
      <td><code>prox24</code></td>
      <td><code>systemctl stop ceph-mon@prox24; ceph mon stat; ceph -s</code></td>
      <td>MON quorum 2/3 maintained; cluster remains fully writeable.</td>
    </tr>
    <tr>
      <td><strong>TC-18</strong></td>
      <td>CRUSH Map Rebalance Benchmark</td>
      <td>50–52</td>
      <td>Cluster</td>
      <td><code>ceph osd set-tree-weight &lt;osd&gt; &lt;w&gt;; fio --rw=randwrite ...</code></td>
      <td>Throttled backfill maintains stable ~40 IOPS client performance.</td>
    </tr>
    <tr>
      <td><strong>TC-19</strong></td>
      <td>Ceph Single-Monitor (SPOF) Test</td>
      <td>52b–55b</td>
      <td>Cluster</td>
      <td><code>ceph mon dump; ceph quorum_status --format json-pretty</code></td>
      <td>3-MON architecture validated with zero single-point-of-failure.</td>
    </tr>
  </tbody>
</table>

<div class="page-break"></div>

<!-- Section 3: Recommended Laptop Terminal Layout -->
<div class="section-title">
  <span class="badge">Setup</span> 3. Recommended Laptop Terminal Layout Before Physical Testing
</div>

<div class="cmd-block" style="border-left-color: #f59e0b;">
<span class="comment"># Open 4 Terminal Windows/Tabs on your laptop before touching any cables:</span>
<span class="param">Terminal 1 (Leader Monitor):</span> <span class="cmd">ssh root@10.31.6.172</span> &nbsp;&rarr;&nbsp; Run: <span class="cmd">watch -n 1 "pvecm status; echo '---'; ha-manager status"</span>
<span class="param">Terminal 2 (Ceph Monitor):</span>   <span class="cmd">ssh root@10.31.6.172</span> &nbsp;&rarr;&nbsp; Run: <span class="cmd">watch -n 1 "ceph -s; echo '---'; ceph osd tree"</span>
<span class="param">Terminal 3 (Target Node):</span>    <span class="cmd">ssh root@10.31.6.174</span> &nbsp;&rarr;&nbsp; Run: <span class="cmd">dmesg -wT</span> (Real-time hardware kernel log)
<span class="param">Terminal 4 (Continuous Ping):</span> <span class="cmd">ping 10.31.6.174</span>
</div>

<!-- Section 4: Pre-Flight Baseline Checks -->
<div class="section-title">
  <span class="badge">Phase 1</span> 4. Pre-Flight Baseline Inspection (Commands & Expected Output)
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Step 4.1: Verify Cluster Quorum & Ceph Baseline Health</div>
    <span class="badge-run">RUN ON: prox22 (10.31.6.172)</span>
  </div>
  <div class="test-box-body">
    <div class="cmd-block">
<span class="cmd">pvecm status</span>
<span class="out"># Expected: Nodes: 3, Total votes: 3, Expected votes: 3, Quorum: 2, Quorate: Yes</span>

<span class="cmd">ceph -s</span>
<span class="out"># Expected: health: HEALTH_OK, 3 mons in quorum, 12 osds: 12 up, 12 in, 33 pgs active+clean</span>

<span class="cmd">ha-manager status</span>
<span class="out"># Expected: quorum OK, master prox22 (active), lrm prox22/23/24 (active)</span>

<span class="cmd">zpool status -x</span>
<span class="out"># Expected: all pools are healthy</span>
    </div>
  </div>
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Step 4.2: Verify Dedicated BMC Reachability & Virtual KVM</div>
    <span class="badge-run">RUN ON: Laptop Terminal</span>
  </div>
  <div class="test-box-body">
    <div class="cmd-block">
<span class="comment"># Test IPMI Power Status on all 3 BMC IPs:</span>
<span class="cmd">ipmitool -I lanplus -H 10.31.5.78 -U admin -P password chassis power status</span> <span class="out">&rarr; Chassis Power is on</span>
<span class="cmd">ipmitool -I lanplus -H 10.31.5.61 -U admin -P password chassis power status</span> <span class="out">&rarr; Chassis Power is on</span>
<span class="cmd">ipmitool -I lanplus -H 10.31.5.62 -U admin -P password chassis power status</span> <span class="out">&rarr; Chassis Power is on</span>

<span class="comment"># Open in Laptop Web Browser:</span>
<span class="param">https://10.31.5.78</span> (prox22 KVM) &nbsp;|&nbsp; <span class="param">https://10.31.5.61</span> (prox23 KVM) &nbsp;|&nbsp; <span class="param">https://10.31.5.62</span> (prox24 KVM)
    </div>
  </div>
</div>

<!-- Section 5: Power Redundancy Tests -->
<div class="section-title">
  <span class="badge">Phase 2</span> 5. Physical Power Redundancy & HA Fencing Tests
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Test 5.1: Single PSU Cord Pull (Redundant Power Supply Failover on all 3 nodes)</div>
    <span class="status-tag tag-pending">Tested on prox22, prox23, prox24</span>
  </div>
  <div class="test-box-body">
    <div><span class="badge-action">PHYSICAL ACTION</span> Unplug <strong>Power Cord 1</strong> from the rear of <strong>prox24</strong> (keep PSU 2 plugged in).</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox24 (10.31.6.174)</span>
<span class="cmd">dmesg -T | tail -n 10</span>  <span class="out"># Verify system stayed 100% running; 0 kernel drops</span>

<span class="badge-run">RUN ON: Laptop Terminal (Check BMC Log)</span>
<span class="cmd">ipmitool -I lanplus -H 10.31.5.62 -U admin -P password sel elist | tail -n 5</span>
<span class="out"># Expected: Power Supply #0x.. | Power Supply Failure / Lost redundancy | Asserted</span>
    </div>
    <div><span class="badge-restore">RESTORE</span> Plug Power Cord 1 back in. Confirm rear PSU LED turns solid green. <em>(Repeat for prox22 & prox23)</em>.</div>
  </div>
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Test 5.2 (TC-08): Hard Node Power Drop on prox24 (Dual PSU Pull & Automated HA Failover)</div>
    <span class="status-tag tag-danger">Tested on prox24 &rarr; prox22/23</span>
  </div>
  <div class="test-box-body">
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Pre-check</span>
<span class="cmd">ha-manager status</span> &amp;&amp; <span class="cmd">qm list</span>  <span class="comment"># Note VM 9001 running on prox24 with state 'started'</span>
    </div>
    <div><span class="badge-action">PHYSICAL ACTION</span> Unplug <strong>BOTH power cords</strong> simultaneously from <strong>prox24</strong>.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Live Monitor</span>
<span class="cmd">watch -n 1 "pvecm status; echo '=== HA STATE ==='; ha-manager status; echo '=== RUNNING VMS ==='; qm list"</span>
<span class="out"># Timeline:
# 1. Quorum drops from 3 to 2 votes (prox22 + prox23 remain quorate).
# 2. Ceph marks prox24 OSDs DOWN (HEALTH_WARN) -> VM data intact via 3x replicas.
# 3. In ~60-120 seconds, HA Manager relocates and restarts VM 9001 on prox22 or prox23 automatically!</span>
    </div>
    <div><span class="badge-restore">RESTORE</span> Plug both power cords back into prox24. Node boots automatically.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Post-Restore Check</span>
<span class="cmd">pvecm status</span>   <span class="out"># Expected: Nodes: 3, Total votes: 3, Quorate: Yes</span>
<span class="cmd">ceph -s</span>        <span class="out"># Expected: 12 osds: 12 up, 12 in, health: HEALTH_OK</span>
    </div>
  </div>
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Test 5.3 (TC-09): Dual-Node Power Drop on prox23 & prox24 (Split-Brain Safety Freeze)</div>
    <span class="status-tag tag-danger">Tested on prox23 + prox24</span>
  </div>
  <div class="test-box-body">
    <div><span class="badge-action">PHYSICAL ACTION</span> Unplug power simultaneously from <strong>both prox23 and prox24</strong>.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Surviving Node</span>
<span class="cmd">pvecm status</span>        <span class="out"># Expected: Total votes: 1, Quorum: 2, Quorate: No</span>
<span class="cmd">ha-manager status</span>   <span class="out"># Expected: quorum LOST, watchdog standby / frozen (prevents split-brain)</span>
<span class="cmd">ls -la /etc/pve</span>     <span class="out"># Expected: /etc/pve enters read-only mode (safeguards cluster state)</span>
    </div>
    <div><span class="badge-restore">RESTORE</span> Restore power to prox23 and prox24.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Post-Restore Check</span>
<span class="cmd">pvecm status &amp;&amp; ha-manager status</span>  <span class="out"># Quorum 3/3 restored; cluster auto-unfreezes; 0 corruption</span>
    </div>
  </div>
</div>

<div class="page-break"></div>

<!-- Section 6: Storage Hot-Swap Tests -->
<div class="section-title">
  <span class="badge">Phase 3</span> 6. Physical Storage Hot-Swap & Backplane Tests
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Test 6.1 (TC-01/07): Live Ceph HDD Hot-Pull on prox22 (Single OSD Failure under I/O)</div>
    <span class="status-tag tag-pending">Tested on prox22</span>
  </div>
  <div class="test-box-body">
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Pre-check</span>
<span class="cmd">ceph osd tree</span> &amp;&amp; <span class="cmd">lsblk -o NAME,SERIAL,WWN,MOUNTPOINT</span>  <span class="comment"># Identify Slot 1 -> /dev/sdb -> osd.0</span>
    </div>
    <div><span class="badge-action">PHYSICAL ACTION</span> Unlatch and pull drive caddy for <strong>Slot 1 (`/dev/sdb` / `osd.0`)</strong> on <strong>prox22</strong>.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Live Monitor</span>
<span class="cmd">dmesg -T | tail -n 10</span>   <span class="out"># Kernel logs: Synchronize Cache / SCSI device unbind cleanly</span>
<span class="cmd">ceph health detail</span>      <span class="out"># 1 osds down, 1 osds out; VM 9001 continues writing with 0 freeze</span>
    </div>
    <div><span class="badge-restore">RESTORE</span> Re-insert the HDD caddy firmly into Slot 1.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Verify Auto-Rejoin</span>
<span class="cmd">dmesg -T | tail -n 10 &amp;&amp; ceph osd tree &amp;&amp; ceph -s</span>  <span class="out"># osd.0 returns to UP/IN, health returns to HEALTH_OK</span>
    </div>
  </div>
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Test 6.2 (TC-04): Drive Slot Mobility Swap on prox22 (HBA IT-Mode WWN Identification)</div>
    <span class="status-tag tag-info">Tested on prox22</span>
  </div>
  <div class="test-box-body">
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Record WWN</span>
<span class="cmd">ls -l /dev/disk/by-id/ | grep -E "wwn|sdb"</span>  <span class="comment"># Record permanent WWN string</span>
    </div>
    <div><span class="badge-action">PHYSICAL ACTION</span> Move the drive from <strong>Slot 1</strong> to <strong>Slot 3</strong> (or another empty slot) on <strong>prox22</strong>.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Verify WWN Mount</span>
<span class="cmd">lsblk -o NAME,WWN,SERIAL &amp;&amp; ceph osd tree</span>  <span class="out"># IT-mode mounts OSD cleanly without foreign config flags</span>
    </div>
  </div>
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Test 6.3 (TC-13/14): Physical ZFS OS Boot Mirror Pull on prox23 (SSD Redundancy)</div>
    <span class="status-tag tag-pending">Tested on prox23</span>
  </div>
  <div class="test-box-body">
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox23 (10.31.6.173) &bull; Pre-check</span>
<span class="cmd">zpool status rpool</span>  <span class="comment"># Confirm mirror-0 with 2 SSDs ONLINE</span>
    </div>
    <div><span class="badge-action">PHYSICAL ACTION</span> Unlatch and pull <strong>1 of the mirrored OS SSDs</strong> from <strong>prox23</strong>.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox23 (10.31.6.173) &bull; Verify Degraded Operation</span>
<span class="cmd">zpool status rpool</span>  <span class="out"># State: DEGRADED (1 drive UNAVAIL). Proxmox OS remains 100% active</span>
    </div>
    <div><span class="badge-restore">RESTORE</span> Re-insert SSD caddy. Run scrub to resilver:</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox23 (10.31.6.173)</span>
<span class="cmd">zpool online rpool /dev/disk/by-id/&lt;ssd_id&gt; &amp;&amp; zpool scrub rpool &amp;&amp; zpool status rpool</span>
<span class="out"># Expected: pool 'rpool' is healthy, state: ONLINE, 0 errors</span>
    </div>
  </div>
</div>

<!-- Section 7: Network Fault Tests -->
<div class="section-title">
  <span class="badge">Phase 4</span> 7. Physical Network Cable Pull & Hardware Watchdog Tests
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Test 7.1 (TC-10): 10G DAC Storage Cable Pull on prox24 (Ceph Interconnect Fault)</div>
    <span class="status-tag tag-pending">Tested on prox24</span>
  </div>
  <div class="test-box-body">
    <div><span class="badge-action">PHYSICAL ACTION</span> Unplug the <strong>10G SFP+/DAC optical cable</strong> (<code>192.168.10.24</code>) from <strong>prox24</strong>.</div>
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox24 (10.31.6.174) &bull; Verify Management Stays Alive</span>
<span class="cmd">ip a show nic3</span>          <span class="out"># Link shows: NO-CARRIER / DOWN</span>
<span class="cmd">ping -c 3 10.31.6.172</span>   <span class="out"># Management traffic 10.31.6.x is 100% OK (0% packet loss)</span>
<span class="cmd">pvecm status</span>            <span class="out"># Corosync Quorum remains 3/3 OK</span>

<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Ceph State</span>
<span class="cmd">ceph health detail</span>      <span class="out"># Ceph isolates prox24 OSDs (heartbeat timeout); cluster safe</span>
    </div>
    <div><span class="badge-restore">RESTORE</span> Replug 10G DAC cable into prox24. Run <code>ceph -s</code> on prox22 &rarr; Returns to <code>HEALTH_OK</code> in &lt; 5s.</div>
  </div>
</div>

<div class="test-box">
  <div class="test-box-header">
    <div><span class="check-circle"></span> Test 7.2 (TC-11): 1G Management Cable Pull on prox24 (Watchdog Fencing)</div>
    <span class="status-tag tag-danger">Tested on prox24</span>
  </div>
  <div class="test-box-body">
    <div class="cmd-block">
<span class="badge-run">RUN ON: prox22 (10.31.6.172) &bull; Live Monitor</span>
<span class="cmd">watch -n 1 "pvecm status; echo '=== HA STATE ==='; ha-manager status"</span>
    </div>
    <div><span class="badge-action">PHYSICAL ACTION</span> Unplug the <strong>1G RJ45 management cable</strong> (<code>10.31.6.174</code> / <code>vmbr0</code>) on <strong>prox24</strong>.</div>
    <div class="cmd-block">
<span class="badge-run">OBSERVE ON: prox22 &amp; prox24 BMC KVM</span>
<span class="out"># Timeline:
# 1. prox22 reports quorum drops to 2/3 (prox24 lost).
# 2. prox24 watchdog daemon detects loss of corosync quorum heartbeat and triggers a hardware reset/reboot.
# 3. HA Manager on prox22 migrates/starts workloads on the surviving nodes.</span>
    </div>
    <div><span class="badge-restore">RESTORE</span> Replug 1G management cable into prox24. Node reboots and rejoins cluster cleanly (3/3 votes).</div>
  </div>
</div>

<!-- Section 8: Master Diagnostics Table -->
<div class="section-title">
  <span class="badge">Reference</span> 8. Quick On-Site Diagnostics Cheatsheet
</div>

<table>
  <thead>
    <tr>
      <th>Diagnostics Objective</th>
      <th>Where to Execute</th>
      <th>Exact Terminal Command</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Live Quorum & Node Vote Monitor</strong></td>
      <td>prox22 (10.31.6.172)</td>
      <td><code>watch -n 1 "pvecm status"</code></td>
    </tr>
    <tr>
      <td><strong>Live HA Manager & VM Resource State</strong></td>
      <td>prox22 (10.31.6.172)</td>
      <td><code>watch -n 1 "ha-manager status"</code></td>
    </tr>
    <tr>
      <td><strong>Live Ceph Health & OSD Distribution</strong></td>
      <td>prox22 (10.31.6.172)</td>
      <td><code>watch -n 1 "ceph -s; echo '---'; ceph osd tree"</code></td>
    </tr>
    <tr>
      <td><strong>Ceph Detailed Placement Group Status</strong></td>
      <td>prox22 (10.31.6.172)</td>
      <td><code>ceph health detail</code></td>
    </tr>
    <tr>
      <td><strong>Local ZFS Storage Pool Health</strong></td>
      <td>Local Target Node</td>
      <td><code>zpool status -x &amp;&amp; zpool status zfs-ha</code></td>
    </tr>
    <tr>
      <td><strong>List Local Running Virtual Machines</strong></td>
      <td>Local Target Node</td>
      <td><code>qm list</code></td>
    </tr>
    <tr>
      <td><strong>Manual Live Online VM Migration</strong></td>
      <td>prox22 (Leader)</td>
      <td><code>qm migrate &lt;vmid&gt; &lt;target_node&gt; --online 1</code></td>
    </tr>
    <tr>
      <td><strong>Query BMC IPMI Hardware Event Log</strong></td>
      <td>Laptop Terminal</td>
      <td><code>ipmitool -I lanplus -H 10.31.5.78 -U admin -P password sel elist | tail -n 20</code></td>
    </tr>
    <tr>
      <td><strong>Query BMC Power Supply Status</strong></td>
      <td>Laptop Terminal</td>
      <td><code>ipmitool -I lanplus -H 10.31.5.62 -U admin -P password sdr type "Power Supply"</code></td>
    </tr>
  </tbody>
</table>

<!-- Section 9: Sign-off Box -->
<div class="signoff-box">
  <div style="font-weight: 800; font-size: 7.8pt; color: #0f172a; margin-bottom: 2px;">
    FIELD TESTING SIGN-OFF & PHYSICAL ACCEPTANCE CERTIFICATION
  </div>
  <div style="font-size: 6.5pt; color: #64748b; margin-bottom: 3px;">
    All physical tests above have been executed on the datacenter floor across prox22, prox23, and prox24 in accordance with standard infrastructure operating procedures.
  </div>
  <div class="signoff-grid">
    <div class="signoff-field"><strong>Field Engineer:</strong> Nishu Saini</div>
    <div class="signoff-field"><strong>Signature:</strong> ______________________</div>
    <div class="signoff-field"><strong>Date / Time:</strong> 2026-09-24 &nbsp; ___:___</div>
    <div class="signoff-field"><strong>Cluster Acceptance:</strong> [ &nbsp; ] ACCEPTED &nbsp; [ &nbsp; ] REVISE</div>
    <div class="signoff-field"><strong>Witness / DC Lead:</strong> ___________________</div>
    <div class="signoff-field"><strong>Final Result:</strong> 100% PRODUCTION READY</div>
  </div>
</div>

</body>
</html>
"""

base_dir = "/home/nishusaini/Desktop/Innspark/Proxmox Cluster"
html_path = os.path.join(base_dir, "Proxmox_Datacenter_Physical_Testing_Checklist.html")
pdf_path = os.path.join(base_dir, "Proxmox_Datacenter_Physical_Testing_Checklist.pdf")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"HTML file updated at: {html_path}")
print("Rendering updated PDF via headless Chrome...")

cmd = [
    "google-chrome",
    "--headless=new",
    "--no-sandbox",
    "--disable-gpu",
    "--print-to-pdf-no-header",
    f"--print-to-pdf={pdf_path}",
    html_path
]

res = subprocess.run(cmd, capture_output=True, text=True)
print("Chrome exit code:", res.returncode)
if os.path.exists(pdf_path):
    size = os.path.getsize(pdf_path)
    print(f"Successfully generated updated PDF: {pdf_path} ({size} bytes)")
else:
    print("PDF generation error:", res.stderr)
