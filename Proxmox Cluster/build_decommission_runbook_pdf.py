import os
import subprocess

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Proxmox VE Cluster - Test VM & SDN Decommissioning Runbook</title>
<style>
  @page {
    size: A4 portrait;
    margin: 8mm 10mm 10mm 10mm;
    @bottom-right {
      content: "Page " counter(page) " of " counter(pages);
      font-size: 7.5pt;
      color: #64748b;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    }
    @bottom-left {
      content: "Innspark / CISAI Infrastructure • Test VM & SDN Decommissioning Runbook (cisai-pve)";
      font-size: 7.5pt;
      color: #64748b;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    }
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #0f172a;
    line-height: 1.35;
    font-size: 8.2pt;
    margin: 0;
    padding: 0;
    background: #ffffff;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  .header-card {
    background: linear-gradient(135deg, #090d16 0%, #1e293b 55%, #b91c1c 100%);
    color: white;
    padding: 12px 16px;
    border-radius: 6px;
    margin-bottom: 12px;
  }
  .header-card h1 {
    margin: 0 0 3px 0;
    font-size: 13.5pt;
    font-weight: 800;
    letter-spacing: -0.3px;
  }
  .header-card .subtitle {
    font-size: 8.8pt;
    color: #fecaca;
    margin-bottom: 8px;
    font-weight: 500;
  }
  .meta-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    font-size: 7.5pt;
    background: rgba(255, 255, 255, 0.08);
    padding: 6px 10px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.15);
  }
  .meta-item strong {
    color: #f87171;
    display: block;
    margin-bottom: 1px;
    text-transform: uppercase;
    font-size: 6.5pt;
    letter-spacing: 0.5px;
  }

  .section-title {
    font-size: 9.8pt;
    font-weight: 800;
    color: #0f172a;
    border-bottom: 2px solid #b91c1c;
    padding-bottom: 3px;
    margin-top: 12px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .section-title span.badge {
    font-size: 7pt;
    font-weight: 600;
    background: #fee2e2;
    color: #991b1b;
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid #fecaca;
  }

  .callout-info {
    background: #f8fafc;
    border-left: 3px solid #0284c7;
    padding: 6px 10px;
    border-radius: 0 4px 4px 0;
    margin-bottom: 8px;
    font-size: 7.8pt;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 8px;
    font-size: 7.6pt;
  }
  table th {
    background: #f1f5f9;
    color: #334155;
    font-weight: 700;
    text-align: left;
    padding: 4px 7px;
    border: 1px solid #cbd5e1;
  }
  table td {
    padding: 4px 7px;
    border: 1px solid #e2e8f0;
    vertical-align: top;
  }
  table tr:nth-child(even) {
    background: #f8fafc;
  }

  pre {
    background: #0f172a;
    color: #f8fafc;
    padding: 6px 8px;
    border-radius: 4px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 7pt;
    line-height: 1.25;
    margin: 4px 0 6px 0;
    white-space: pre-wrap;
    word-break: break-all;
    border: 1px solid #1e293b;
  }
  code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    background: #f1f5f9;
    color: #b91c1c;
    padding: 1px 3px;
    border-radius: 3px;
    font-size: 7.2pt;
  }

  .step-box {
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 6px 8px;
    margin-bottom: 8px;
    background: #ffffff;
    page-break-inside: avoid;
  }
  .step-header {
    font-weight: 700;
    font-size: 8.5pt;
    color: #b91c1c;
    margin-bottom: 3px;
    display: flex;
    justify-content: space-between;
  }
  .step-desc {
    font-size: 7.5pt;
    color: #475569;
    margin-bottom: 4px;
  }

  .page-break {
    page-break-after: always;
  }
</style>
</head>
<body>

<!-- Header Card -->
<div class="header-card">
  <h1>Proxmox VE Cluster — Test VM & SDN Decommissioning Runbook</h1>
  <div class="subtitle">Complete Command Execution Guide, HA Disarmament, Storage Purge & Network Teardown</div>
  <div class="meta-grid">
    <div class="meta-item">
      <strong>Target Cluster</strong>
      cisai-pve (prox022, prox023, prox024)
    </div>
    <div class="meta-item">
      <strong>Action Scope</strong>
      9000-Series VMs & VXLAN SDN
    </div>
    <div class="meta-item">
      <strong>Storage Reclaimed</strong>
      ~43 GiB Ceph/ZFS Space Freed
    </div>
    <div class="meta-item">
      <strong>Production State</strong>
      VMs 100, 102, 106, 103, 104 Intact
    </div>
  </div>
</div>

<div class="callout-info">
  <strong>Operational Purpose:</strong> Following completion of datacenter physical resiliency and performance testing, this document records the exact procedure and commands executed to cleanly purge all synthetic 9000-series test VMs, disarm High Availability (HA) manager tracking, delete ZFS storage replication jobs, and permanently decommission the overlay VXLAN Software-Defined Network (SDN).
</div>

<div class="section-title">
  <span>1. Decommissioned Artifacts Inventory</span>
  <span class="badge">Purged Resources</span>
</div>

<table>
  <thead>
    <tr>
      <th>Resource Type</th>
      <th>Identifier / Name</th>
      <th>Resident Node</th>
      <th>Underlying Storage / Network</th>
      <th>Purge Result</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Virtual Machine</strong></td>
      <td>VM 9001 (ha-test-ceph-ubuntu2204)</td>
      <td>prox022</td>
      <td>Ceph RBD (32GB pool ceph)</td>
      <td>Stopped & Purged</td>
    </tr>
    <tr>
      <td><strong>Virtual Machine</strong></td>
      <td>VM 9002 (zfs-test-prox24-ubuntu2204)</td>
      <td>prox024</td>
      <td>Ceph RBD (32GB pool ceph)</td>
      <td>Stopped & Purged</td>
    </tr>
    <tr>
      <td><strong>Virtual Machine</strong></td>
      <td>VM 9003 (zfs-benchmark-prod-vm)</td>
      <td>prox023</td>
      <td>ZFS Zvol (32GB pool zfs-ha)</td>
      <td>Stopped & Purged</td>
    </tr>
    <tr>
      <td><strong>Virtual Machine</strong></td>
      <td>VM 9004 (vm-9004-test)</td>
      <td>prox023</td>
      <td>Ceph RBD (32GB pool ceph)</td>
      <td>Stopped & Purged</td>
    </tr>
    <tr>
      <td><strong>HA Service</strong></td>
      <td>vm:9001, vm:9002, vm:9003, vm:9004</td>
      <td>Cluster-wide</td>
      <td>pve-ha-crm / pve-ha-lrm</td>
      <td>Disarmed & Removed</td>
    </tr>
    <tr>
      <td><strong>Replication Jobs</strong></td>
      <td>9002-0, 9002-1, 9003-0, 9003-1</td>
      <td>Cluster-wide</td>
      <td>pvesr storage replication</td>
      <td>Deleted</td>
    </tr>
    <tr>
      <td><strong>SDN VXLAN Zone</strong></td>
      <td>myzone (MTU 1450, tag 10010)</td>
      <td>All 3 Nodes</td>
      <td>192.168.10.x Full-Mesh Peers</td>
      <td>Deleted & Unmounted</td>
    </tr>
    <tr>
      <td><strong>SDN VNet & Subnet</strong></td>
      <td>vnet10 & myzone-10.10.10.0-24</td>
      <td>All 3 Nodes</td>
      <td>Kernel bridge & overlay tunnel</td>
      <td>Interfaces Deleted</td>
    </tr>
  </tbody>
</table>

<div class="section-title">
  <span>2. Step-by-Step Command Execution Guide</span>
  <span class="badge">CLI Runbook</span>
</div>

<div class="step-box">
  <div class="step-header">Phase 1: Delete Storage Replication Jobs</div>
  <div class="step-desc">Removes periodic ZFS volume synchronization schedules from <code>/etc/pve/replication.cfg</code> before destroying VMs.</div>
  <pre><code># Run on cluster master (prox022):
pvesr delete 9002-0
pvesr delete 9002-1
pvesr delete 9003-0
pvesr delete 9003-1</code></pre>
</div>

<div class="step-box">
  <div class="step-header">Phase 2: Disarm High Availability (HA) Manager</div>
  <div class="step-desc">Removes test VMs from the cluster watchdog CRM. Without this step, killing a VM would trigger an automated HA fence or restart attempt.</div>
  <pre><code># Run on cluster master (prox022):
ha-manager remove vm:9001
ha-manager remove vm:9002
ha-manager remove vm:9003
ha-manager remove vm:9004</code></pre>
</div>

<div class="step-box">
  <div class="step-header">Phase 3: Stop and Purge Test VMs with Storage Disks</div>
  <div class="step-desc">Executes forceful shutdown and triggers storage backend garbage collection (<code>--purge 1</code>).</div>
  <pre><code># 1. On prox022 (hosts VM 9001):
qm stop 9001 --skiplock 1
qm destroy 9001 --purge 1 --skiplock 1

# 2. On prox024 (hosts VM 9002):
qm stop 9002 --skiplock 1
qm destroy 9002 --purge 1 --skiplock 1

# 3. On prox023 (hosts VMs 9003 and 9004):
qm stop 9003 --skiplock 1
qm destroy 9003 --purge 1 --skiplock 1

qm stop 9004 --skiplock 1
qm destroy 9004 --purge 1 --skiplock 1</code></pre>
</div>

<div class="page-break"></div>

<div class="step-box">
  <div class="step-header">Phase 4: Completely Remove Proxmox SDN (VXLAN)</div>
  <div class="step-desc">Tears down cluster SDN definitions, eliminates boot-persistence scripts, and deletes live Linux kernel interfaces.</div>
  <pre><code># Step 4.1: Delete cluster SDN configs & IPAM state (run on prox022):
rm -f /etc/pve/sdn/zones.cfg
rm -f /etc/pve/sdn/vnets.cfg
rm -f /etc/pve/sdn/subnets.cfg
rm -f /etc/pve/sdn/pve-ipam-state.json
rm -f /etc/pve/sdn/.running-config

# Step 4.2: Delete network interface persistence files (run on prox022, prox023, prox024):
rm -f /etc/network/interfaces.d/sdn

# Step 4.3: Tear down live kernel interfaces (run on prox022, prox023, prox024):
ip link set vnet10 down 2>/dev/null || true
ip link delete vnet10 2>/dev/null || true
ip link delete vxlan_vnet10 2>/dev/null || true</code></pre>
</div>

<div class="section-title">
  <span>3. Post-Cleanup Verification Commands & Health Audit</span>
  <span class="badge">Verification Table</span>
</div>

<table>
  <thead>
    <tr>
      <th>Verification Command</th>
      <th>Target Validation Check</th>
      <th>Expected Output</th>
      <th>Live Audit Result</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>qm list</code></td>
      <td>Confirm 9000-series VMs are absent</td>
      <td>Only VMs 100, 102, 106, 103, 104</td>
      <td><strong>✔ PASSED (9000s Absent)</strong></td>
    </tr>
    <tr>
      <td><code>ha-manager status</code></td>
      <td>Confirm HA service list is clean</td>
      <td>Zero test VM services registered</td>
      <td><strong>✔ PASSED (0 Test Services)</strong></td>
    </tr>
    <tr>
      <td><code>pvesr list</code></td>
      <td>Confirm replication queue</td>
      <td>Empty table</td>
      <td><strong>✔ PASSED (No Jobs)</strong></td>
    </tr>
    <tr>
      <td><code>ip -br link | grep -E "vnet|vxlan"</code></td>
      <td>Confirm SDN kernel teardown</td>
      <td>Empty output (no links)</td>
      <td><strong>✔ PASSED (Clean)</strong></td>
    </tr>
    <tr>
      <td><code>ls -la /etc/pve/sdn</code></td>
      <td>Confirm cluster SDN directory</td>
      <td>Total 0 (clean directory)</td>
      <td><strong>✔ PASSED (Empty)</strong></td>
    </tr>
    <tr>
      <td><code>ceph status</code></td>
      <td>Verify Ceph storage state</td>
      <td>HEALTH_OK • 12/12 OSDs up & in</td>
      <td><strong>✔ PASSED (HEALTH_OK)</strong></td>
    </tr>
  </tbody>
</table>

<div class="section-title">
  <span>4. Surviving Production Workloads (100% Intact)</span>
  <span class="badge">Active Services</span>
</div>

<table>
  <thead>
    <tr>
      <th>VMID</th>
      <th>Virtual Machine Name</th>
      <th>Host Node</th>
      <th>Allocated Memory</th>
      <th>Boot Storage Backend</th>
      <th>Operational Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>100</strong></td>
      <td>windows</td>
      <td>prox022</td>
      <td>40,960 MB</td>
      <td>local-lvm:vm-100-disk-1</td>
      <td>Running (PID 44173)</td>
    </tr>
    <tr>
      <td><strong>102</strong></td>
      <td>testdontremove</td>
      <td>prox022</td>
      <td>20,480 MB</td>
      <td>local-lvm:vm-102-disk-0</td>
      <td>Running (PID 900303)</td>
    </tr>
    <tr>
      <td><strong>106</strong></td>
      <td>2026090578-jishnua-ubuntu24</td>
      <td>prox022</td>
      <td>32,768 MB</td>
      <td>local-lvm:vm-106-disk-0 (250GB)</td>
      <td>Running (PID 1958557)</td>
    </tr>
    <tr>
      <td><strong>103</strong></td>
      <td>115-gouthamoshibu-ubuntu24</td>
      <td>prox024</td>
      <td>10,240 MB</td>
      <td>local-lvm:vm-103-disk-0 (150GB)</td>
      <td>Running (PID 3714007)</td>
    </tr>
    <tr>
      <td><strong>104</strong></td>
      <td>2026090558-gouthamoshibu-ubuntu24</td>
      <td>prox024</td>
      <td>10,240 MB</td>
      <td>local-lvm:vm-104-disk-0 (150GB)</td>
      <td>Running (PID 3776614)</td>
    </tr>
  </tbody>
</table>

</body>
</html>
"""

base_dir = "/home/nishusaini/Desktop/Innspark/Proxmox Cluster"
html_path = os.path.join(base_dir, "Proxmox_Cluster_Test_VM_and_SDN_Decommissioning_Runbook.html")
pdf_path = os.path.join(base_dir, "Proxmox_Cluster_Test_VM_and_SDN_Decommissioning_Runbook.pdf")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"HTML saved: {html_path}")
print("Rendering PDF via headless Chrome...")

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
print("Chrome returncode:", res.returncode)
if os.path.exists(pdf_path):
    print(f"Successfully generated PDF: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
else:
    print("PDF generation error:", res.stderr)
