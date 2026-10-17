import os
import subprocess

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    @page {
        size: letter;
        margin: 14mm 12mm 14mm 12mm;
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
            font-size: 7.5pt;
            color: #718096;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        @bottom-left {
            content: "Palo Alto Networks (PAN-OS) Master Training Manual | Innspark Solutions";
            font-size: 7.5pt;
            color: #718096;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #2D3748;
        line-height: 1.35;
        font-size: 8.5pt;
        margin: 0;
        padding: 0;
    }

    .header-banner {
        background: linear-gradient(135deg, #0B1E33 0%, #1A365D 50%, #FA582D 100%);
        color: white;
        padding: 16px 20px;
        border-radius: 6px;
        margin-bottom: 12px;
    }

    .header-banner h1 {
        margin: 0 0 4px 0;
        font-size: 16pt;
        font-weight: 700;
        letter-spacing: -0.3px;
        color: #FFFFFF;
    }

    .header-banner .subtitle {
        font-size: 9pt;
        color: #E2E8F0;
        margin: 0 0 8px 0;
        font-weight: 400;
    }

    .meta-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        background: rgba(255, 255, 255, 0.1);
        padding: 6px 10px;
        border-radius: 4px;
        font-size: 7.5pt;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .meta-item strong {
        color: #FBD38D;
        display: block;
        font-size: 6.8pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 1px;
    }

    h2 {
        color: #0B1E33;
        font-size: 10.5pt;
        font-weight: 700;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 2px;
        margin-top: 14px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        page-break-after: avoid;
    }

    h2 .badge {
        background: #ED8936;
        color: white;
        font-size: 7pt;
        font-weight: 600;
        padding: 1px 6px;
        border-radius: 8px;
    }

    h3 {
        color: #2B6CB0;
        font-size: 9pt;
        font-weight: 600;
        margin-top: 8px;
        margin-bottom: 3px;
        page-break-after: avoid;
    }

    p {
        margin: 0 0 5px 0;
    }

    ul, ol {
        margin: 0 0 6px 0;
        padding-left: 16px;
    }

    li {
        margin-bottom: 2px;
    }

    strong {
        color: #1A202C;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        margin: 6px 0 8px 0;
        font-size: 7.8pt;
        page-break-inside: avoid;
    }

    th {
        background: #0B1E33;
        color: white;
        text-align: left;
        padding: 4px 6px;
        font-weight: 600;
        border: 1px solid #0B1E33;
    }

    td {
        padding: 4px 6px;
        border: 1px solid #E2E8F0;
        vertical-align: top;
    }

    tr:nth-child(even) {
        background-color: #F7FAFC;
    }

    .diagram-box {
        background: #1A202C;
        color: #68D391;
        font-family: "Courier New", Courier, monospace;
        font-size: 6.8pt;
        line-height: 1.16;
        padding: 6px 10px;
        border-radius: 4px;
        margin: 6px 0;
        white-space: pre;
        border-left: 3px solid #FA582D;
        page-break-inside: avoid;
        overflow-x: hidden;
    }

    .callout {
        background: #FEFCBF;
        border-left: 3px solid #D69E2E;
        padding: 6px 10px;
        border-radius: 0 3px 3px 0;
        margin: 6px 0;
        font-size: 7.8pt;
        page-break-inside: avoid;
    }

    .callout strong {
        color: #744210;
    }

    .page-break {
        page-break-before: always;
    }

    .highlight-card {
        background: #EDF2F7;
        border: 1px solid #CBD5E0;
        border-left: 3px solid #2B6CB0;
        padding: 6px 10px;
        border-radius: 0 3px 3px 0;
        margin: 6px 0;
    }

    .section-title {
        background: #0B1E33;
        color: white;
        padding: 4px 8px;
        font-size: 9pt;
        font-weight: 700;
        border-radius: 3px;
        margin-top: 10px;
        margin-bottom: 4px;
    }
</style>
</head>
<body>

<div class="header-banner">
    <h1>Palo Alto Networks (PAN-OS) Master Engineering Guide</h1>
    <div class="subtitle">Complete Technical Course Synthesis & Architecture Reference (11+ Hours Video Master Analysis)</div>
    <div class="meta-grid">
        <div class="meta-item">
            <strong>Training Source</strong>
            11+ Hours Palo Alto Course (IMEDITA)
        </div>
        <div class="meta-item">
            <strong>Scope</strong>
            End-to-End Complete Curriculum
        </div>
        <div class="meta-item">
            <strong>Target Certifications</strong>
            PCNSA & PCNSE Blueprint
        </div>
        <div class="meta-item">
            <strong>Author / Reference</strong>
            Nishu Saini | Innspark Solutions
        </div>
    </div>
</div>

<h2>Table of Contents & Curriculum Map <span class="badge">Master Curriculum</span></h2>
<table>
    <thead>
        <tr>
            <th style="width: 12%;">Module</th>
            <th style="width: 38%;">Curriculum Topic</th>
            <th style="width: 50%;">Core Architectural Highlights</th>
        </tr>
    </thead>
    <tbody>
        <tr><td><strong>Module 1</strong></td><td>Firewall Evolution & Why NGFW?</td><td>Port hopping, SSL tunneling, stateful limitations, Layer 7 inspection model.</td></tr>
        <tr><td><strong>Module 2</strong></td><td>Palo Alto Architecture (SP3 Engine)</td><td>Single-Pass software engine, Control vs Data plane, NPE/SPE/SME hardware processors.</td></tr>
        <tr><td><strong>Module 3</strong></td><td>Packet Processing Flow (Life of a Packet)</td><td>Ingress, Session Setup (Slow-Path), Fast-Path, App-ID, Content-ID, Egress NAT.</td></tr>
        <tr><td><strong>Module 4</strong></td><td>Initial Setup & Commit Engine Lifecycle</td><td>MGT port (192.168.1.1), Candidate vs Running Config, Commit lock & validation.</td></tr>
        <tr><td><strong>Module 5</strong></td><td>Security Zones & 5 Interface Modes</td><td>Layer 3, Virtual Wire (V-Wire), Layer 2, TAP, HA; Inter-zone vs Intra-zone defaults.</td></tr>
        <tr><td><strong>Module 6</strong></td><td>Layer 3 Routing, Virtual Routers & VLANs</td><td>Virtual Routers (VR), 802.1Q Sub-interfaces, Static Routes, Path Monitoring (IP SLA), OSPF/BGP.</td></tr>
        <tr><td><strong>Module 7</strong></td><td>Network Address Translation (NAT) Deep Dive</td><td>Source NAT (DIPP/Dynamic/Static), Destination NAT (Port Forwarding), U-Turn NAT.</td></tr>
        <tr><td><strong>Module 8</strong></td><td>App-ID™ (Application Identification)</td><td>Layer 7 decoders, heuristics, App-ID dependency, Policy Optimizer, App Groups.</td></tr>
        <tr><td><strong>Module 9</strong></td><td>Content-ID™ & Security Profiles Suite</td><td>Antivirus, Anti-Spyware (DNS Sinkholing), Vulnerability (IPS), URL Filtering, File Blocking, DLP.</td></tr>
        <tr><td><strong>Module 10</strong></td><td>WildFire™ Cloud Threat Intelligence</td><td>Zero-Day malware detonation, 5-min global signatures, Patient Zero, WF-500 private cloud.</td></tr>
        <tr><td><strong>Module 11</strong></td><td>User-ID™ (Identity-Based Enforcement)</td><td>Active Directory WMI/WinRM integration, Syslog listener, GlobalProtect, User-ID Agent.</td></tr>
        <tr><td><strong>Module 12</strong></td><td>SSL/TLS Decryption Architecture</td><td>Inbound Inspection (Internal servers), SSL Forward Proxy (Outbound clients), Decryption Exclusions.</td></tr>
        <tr><td><strong>Module 13</strong></td><td>Site-to-Site & GlobalProtect™ VPNs</td><td>IPsec VPN (IKEv1/IKEv2 Phase 1 & 2), GlobalProtect Portal & Gateway, Split/Full Tunnel.</td></tr>
        <tr><td><strong>Module 14</strong></td><td>High Availability (HA) & Clustering</td><td>Active/Passive & Active/Active, HA1 (Control) & HA2 (Data), HSCI link, Preemption, Failover triggers.</td></tr>
        <tr><td><strong>Module 15</strong></td><td>Hardware Models, Port Matrix & Panorama</td><td>PA-220 to PA-7000 series, VM-Series, MGT/Console/HSCI ports, Centralized Panorama management.</td></tr>
    </tbody>
</table>

<div class="page-break"></div>

<h2>Module 1: Firewall Evolution & Why Next-Generation Firewalls? <span class="badge">Module 1</span></h2>
<h3>1. The Limitations of Legacy Firewalls (Packet Filters & Stateful Inspection)</h3>
<ul>
    <li><strong>Layer 3 / Layer 4 Blindness:</strong> Traditional firewalls (Cisco ASA, router ACLs) inspect only 5-tuples (Source IP, Dest IP, Source Port, Dest Port, Protocol). They assume port 80 is web traffic and port 25 is mail.</li>
    <li><strong>Port-Hopping & Application Evasion:</strong> Modern applications (BitTorrent, Skype, Telegram, Tor, evasion tools) dynamically negotiate random high-order ports to bypass static port security.</li>
    <li><strong>The Port 80 / 443 Problem:</strong> Today, over 95% of enterprise traffic (SaaS apps, social media, Office 365, AWS console, as well as malware Command & Control) runs over standard HTTP (port 80) and SSL/TLS HTTPS (port 443). Legacy firewalls cannot distinguish between legitimate business traffic and data exfiltration over port 443.</li>
</ul>

<h3>2. The Next-Generation Firewall (NGFW) Paradigm</h3>
<p>Palo Alto Networks reinvented network security by making <strong>Application Classification (App-ID)</strong> the primary classification key. Traffic is classified by <em>Application</em>, <em>User</em>, and <em>Content</em> regardless of what port, protocol, or encryption is used.</p>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 2: Palo Alto Architecture (SP3 Engine & Hardware Processors) <span class="badge">Module 2</span></h2>
<p>Palo Alto firewalls achieve line-rate throughput via <strong>Single-Pass Parallel Processing (SP3)</strong>, physically isolating management from traffic processing.</p>

<div class="diagram-box">
+===================================================================================================================+
|                                    PALO ALTO HARDWARE & SOFTWARE ARCHITECTURE (SP3)                               |
+===================================================================================================================+
|                                                                                                                   |
|   ┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┐   |
|   │                                    CONTROL PLANE (MANAGEMENT PLANE)                                       │   |
|   │   - Dedicated Multi-Core CPU & RAM (Completely isolated from traffic processing)                          │   |
|   │   - Dedicated Hard Drive / SSD for Logging, Reporting, PAN-OS System Image, and Configuration Database    │   |
|   │   - Handles: Web GUI (HTTPS:443), CLI (SSH/Console), API, Dynamic Routing Protocols, Panorama Sync       │   |
|   └───────────────────────────────────────────────────────────────────────────────────────────────────────────┘   |
|                                                     ▲                                                             |
|                                 Internal High-Speed Bus (Heartbeats/Sync)                                         |
|                                                     ▼                                                             |
|   ┌───────────────────────────────────────────────────────────────────────────────────────────────────────────┐   |
|   │                                         DATA PLANE (DATAPATH)                                             │   |
|   │                                                                                                           │   |
|   │   ┌───────────────────────────┐    ┌───────────────────────────┐    ┌─────────────────────────────────┐   │   |
|   │   │ NETWORK PROCESSOR (NPE)   │    │ SECURITY PROCESSOR (SPE)  │    │ SIGNATURE MATCHING ENGINE (SME) │   │   |
|   │   │ ───────────────────────── │    │ ───────────────────────── │    │ ─────────────────────────────── │   │   |
|   │   │ • Route & MAC Lookup      │    │ • Hardware SSL/TLS Crypto │    │ • Custom ASIC Match Engine (ME) │   │   |
|   │   │ • Layer 2 - Layer 4 QoS   │    │ • IPsec VPN Acceleration  │    │ • Deep Packet IPS & Vulnerability│  │   |
|   │   │ • Hardware NAT Rewriting  │    │ • Hardware Decryption     │    │ • Antivirus & Anti-Spyware Scan │   │   |
|   │   │ • Flow Control & Session  │    │   (Forward & Inbound Proxy)│   │ • Uniform Regex Signature Scan  │   │   |
|   │   └───────────────────────────┘    └───────────────────────────┘    └─────────────────────────────────┘   │   |
|   │                                                 ▲                                                         │   |
|   │                                                 │                                                         │   |
|   │   ┌─────────────────────────────────────────────┴─────────────────────────────────────────────────────┐   │   |
|   │   │                           MULTI-CORE SECURITY ENGINE (DATA PLANE CPU)                             │   │   |
|   │   │ ───────────────────────────────────────────────────────────────────────────────────────────────── │   │   |
|   │   │ • App-ID Classification (L7 Decoder)   • User-ID Mapping Engine       • Policy Rule Evaluation    │   │   |
|   │   │ • Stateful Session Table Lookup        • Threat Content Inspection   • QoS / Bandwidth Shaping   │   │   |
|   │   └───────────────────────────────────────────────────────────────────────────────────────────────────┘   │   |
|   └───────────────────────────────────────────────────────────────────────────────────────────────────────────┘   |
+===================================================================================================================+
</div>

<h3>Hardware Subsystem Roles:</h3>
<ul>
    <li><strong>Network Processor (NPE):</strong> Dedicated ASIC managing Layer 2 switching, Layer 3 routing, MAC table lookup, hardware NAT address rewriting, and QoS tagging. Offloads basic networking from CPU.</li>
    <li><strong>Security Processor (SPE):</strong> Hardware cryptographic acceleration for SSL/TLS decryption (inbound & outbound) and IPsec VPN tunneling. Prevents CPU exhaustion during heavy crypto loads.</li>
    <li><strong>Signature Matching Engine (SME):</strong> Purpose-built Match Engine (ME) ASICs running high-speed parallel Regular Expression (RegEx) matching for Content-ID threat scans.</li>
    <li><strong>Multi-Core Security Engine:</strong> High-performance multicore data plane processors dedicated to Layer 7 App-ID protocol decoders, User-ID mapping, and security rule evaluation.</li>
</ul>

<div class="page-break"></div>

<h2>Module 3: Packet Processing Flow (Life of a Packet) <span class="badge">Module 3</span></h2>
<p>Every packet entering PAN-OS traverses a deterministic 4-stage hardware pipeline:</p>

<div class="diagram-box">
+───────────────────────────────────────────────────────────────────────────────────────────────────────────────────+
|                                    PALO ALTO PACKET PROCESSING FLOW (LIFE OF A PACKET)                            |
+───────────────────────────────────────────────────────────────────────────────────────────────────────────────────+
|                                                                                                                   |
|  [ INGRESS STAGE ]                                                                                                |
|   1. Ingress Packet Arrival ──> L2/L3 Header Sanity Check ──> Determine Ingress Interface & Zone                 |
|   2. Check State Table for Active Session:                                                                        |
|         │                                                                                                         |
|         ├── [ SESSION MATCH FOUND: FAST PATH ] ────────────────────────────────────────────────────────┐          |
|         │    - Validate TCP Sequence & Ack Numbers                                                     │          |
|         │    - Fast-Path Flow to Content-ID                                                            │          |
|         │                                                                                              │          |
|         └── [ NO SESSION MATCH: SLOW PATH / NEW SYN PACKET ]                                           │          |
|              - Forwarding Route Lookup & Egress Interface/Zone Determination                           │          |
|              - NAT Policy Evaluation (Pre-NAT Source/Dest vs Post-NAT Mapping)                         │          |
|              - Security Policy Rulebase Evaluation (Top-to-Bottom First Match)                         │          |
|              - IF ALLOWED: Allocate Session ID, populate Session State Table                           │          |
|              - IF DENIED: Silently Drop or Send TCP Reset                                              │          |
|                                                                                                        │          |
|  [ APP-ID STAGE ] <────────────────────────────────────────────────────────────────────────────────────┘          |
|   3. Layer 7 Protocol Decoders Analyze Initial Packets (Payload Signatures & Behavioral Analysis)                 |
|   4. Application Identified (e.g. SSL ──> Facebook ──> Facebook-Chat)                                             |
|   5. Dynamic Security Policy Re-evaluation based on confirmed App-ID                                              |
|                                                                                                                   |
|  [ CONTENT-ID & SECURITY PROFILES STAGE ]                                                                         |
|   6. If SSL Decryption Enabled: Decrypt packet once using Hardware Crypto Engine (SPE)                            |
|   7. Parallel Deep Inspection: Antivirus + Anti-Spyware + Vulnerability Protection + URL Filtering + File Blocking|
|   8. Forward Unknown Suspicious Files to WildFire Cloud Sandbox                                                   |
|                                                                                                                   |
|  [ EGRESS STAGE ]                                                                                                 |
|   9. Apply NAT Translations (Source IP/Port DIPP, Static 1:1, or Destination NAT)                                 |
|  10. Egress Interface Packet Transmission & Log Generation at Session End                                         |
+───────────────────────────────────────────────────────────────────────────────────────────────────────────────────+
</div>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 4: Initial Setup & The Commit Engine <span class="badge">Module 4</span></h2>
<ul>
    <li><strong>Out-of-Band Management:</strong> Dedicated <code>MGT</code> Ethernet port. Default IP: <code>192.168.1.1/24</code>, username: <code>admin</code>, password: <code>admin</code>.</li>
    <li><strong>Serial Console Settings:</strong> <code>9600 Baud, 8 Data Bits, No Parity, 1 Stop Bit, No Flow Control (9600-8-N-1)</code>.</li>
    <li><strong>Candidate vs. Running Config:</strong> Changes made in Web GUI or CLI are saved into a draft <em>Candidate Configuration</em>. Running traffic continues on the active <em>Running Configuration</em>. Executing a <strong>Commit</strong> validates syntax, compiles the rules into hardware ASICs, and transitions the candidate into the active running configuration.</li>
    <li><strong>Revert & Config Locks:</strong> Uncommitted changes can be discarded instantly. Multi-admin environments utilize <em>Config Locks</em> and <em>Commit Locks</em> to prevent collision.</li>
</ul>

<div class="page-break"></div>

<h2>Module 5: Security Zones & 5 Interface Modes <span class="badge">Module 5</span></h2>

<h3>1. Zero-Trust Security Zone Defaults</h3>
<ul>
    <li><strong>Intra-Zone Default (Allow):</strong> Traffic between interfaces in the <em>same zone</em> (e.g., Trust $\rightarrow$ Trust) is permitted by default.</li>
    <li><strong>Inter-Zone Default (Deny):</strong> Traffic between <em>different zones</em> (e.g., Trust $\rightarrow$ Untrust) is dropped by default until an explicit security rule is committed.</li>
</ul>

<h3>2. The 5 Interface Deployment Modes</h3>
<table>
    <thead>
        <tr>
            <th style="width: 22%;">Interface Mode</th>
            <th style="width: 20%;">Layer Operation</th>
            <th style="width: 28%;">Network Configuration</th>
            <th style="width: 30%;">Operational Use Case</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Layer 3 (L3)</strong></td>
            <td>Layer 3 (Routed)</td>
            <td>Has IP addresses, participates in OSPF/BGP/Static routing, NAT, and VPN.</td>
            <td>Standard perimeter edge firewall gateway, inter-VLAN routing.</td>
        </tr>
        <tr>
            <td><strong>Virtual Wire (V-Wire)</strong></td>
            <td>Layer 2 (Bump-in-Wire)</td>
            <td>Zero IP/MAC addresses. Binds two ports logically together.</td>
            <td>Transparent inline insertion between switches and routers without changing subnets.</td>
        </tr>
        <tr>
            <td><strong>Layer 2 (L2)</strong></td>
            <td>Layer 2 (Bridged)</td>
            <td>Performs Layer 2 MAC forwarding and VLAN switching across ports.</td>
            <td>Internal network segmentation without routing.</td>
        </tr>
        <tr>
            <td><strong>TAP Mode</strong></td>
            <td>Passive (SPAN)</td>
            <td>Connects to switch mirror port; receives traffic copies. Cannot block.</td>
            <td>Proof of Concept (POC) evaluations, passive threat visibility.</td>
        </tr>
        <tr>
            <td><strong>HA Mode</strong></td>
            <td>Clustering</td>
            <td>HA1 (Heartbeat/Config) and HA2 (Session state replication).</td>
            <td>Active/Passive or Active/Active resilient clustering.</td>
        </tr>
    </tbody>
</table>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 6: Layer 3 Routing, Virtual Routers & Path Monitoring <span class="badge">Module 6</span></h2>
<ul>
    <li><strong>Virtual Routers (VR):</strong> Logical routing instances inside PAN-OS (e.g., <code>default</code>). Supports multiple isolated routing tables on a single physical firewall.</li>
    <li><strong>802.1Q Sub-interfaces:</strong> Single physical port (e.g., <code>ethernet1/2</code>) carries multiple tagged VLANs (e.g., <code>ethernet1/2.10</code> for VLAN 10, <code>ethernet1/2.20</code> for VLAN 20) with zone assignments and inter-VLAN security enforcement.</li>
    <li><strong>Static & Default Routing:</strong> Static routes require Destination (e.g., <code>0.0.0.0/0</code>), Egress Interface, and Next-Hop IP.</li>
    <li><strong>Path Monitoring (Palo Alto IP SLA):</strong> Attaches ICMP ping probes to next-hop IP destinations. If the upstream ISP stops responding, PAN-OS automatically withdraws the static route and fails over to the backup WAN link.</li>
</ul>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 7: Network Address Translation (NAT) In-Depth <span class="badge">Module 7</span></h2>
<p>Palo Alto separates NAT Policy from Security Policy. The Security Policy references <strong>Pre-NAT IP addresses</strong> and <strong>Post-NAT Zones</strong>.</p>
<table>
    <thead>
        <tr>
            <th style="width: 25%;">NAT Type</th>
            <th style="width: 35%;">Configuration Method</th>
            <th style="width: 40%;">Practical Use Case</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Dynamic IP and Port (DIPP / PAT)</strong></td>
            <td>Source NAT translated to Interface IP or IP pool with dynamic port multiplexing (up to 64k sessions per IP).</td>
            <td>Standard outbound internet access for internal LAN endpoints.</td>
        </tr>
        <tr>
            <td><strong>Dynamic IP (No PAT)</strong></td>
            <td>1-to-1 dynamic mapping from a pool of public IPs. If pool is exhausted, new sessions are queued/dropped.</td>
            <td>Strict applications that break with port translation.</td>
        </tr>
        <tr>
            <td><strong>Static 1:1 NAT (Bi-directional)</strong></td>
            <td>Direct permanent 1-to-1 mapping between a private server IP and a public IP.</td>
            <td>Inbound servers (Web servers, Mail servers) needing consistent public addressing.</td>
        </tr>
        <tr>
            <td><strong>Destination NAT (Port Forwarding)</strong></td>
            <td>Translates public destination IP and port to private internal server IP and port.</td>
            <td>Publishing internal DMZ web services (e.g., Public IP:443 $\rightarrow$ 10.1.1.50:8443).</td>
        </tr>
        <tr>
            <td><strong>U-Turn NAT (Hairpinning)</strong></td>
            <td>Allows internal LAN clients to reach internal DMZ servers using the server's public IP address.</td>
            <td>Internal users accessing corporate services via public DNS records.</td>
        </tr>
    </tbody>
</table>

<div class="page-break"></div>

<h2>Module 8: App-ID™ (Application Identification) <span class="badge">Module 8</span></h2>
<ul>
    <li><strong>Application Decoders & Heuristics:</strong> App-ID inspects the initial 4–6 packets of a stream to determine the exact application signature. If traffic shifts (e.g., SSL handshake becomes Facebook, then Facebook-Chat), App-ID updates dynamically and re-evaluates security policy.</li>
    <li><strong>Application Dependency:</strong> Many sub-applications require parent applications (e.g., <code>facebook-chat</code> requires <code>facebook-base</code> and <code>ssl</code>). PAN-OS alerts admins to automatically add required dependencies.</li>
    <li><strong>Policy Optimizer:</strong> Built-in tool that analyzes legacy port-based rules (e.g., port 80/443 `any`), identifies all active App-IDs running over time, and allows 1-click conversion to tight App-ID rules.</li>
</ul>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 9: Content-ID™ & Security Profiles Suite <span class="badge">Module 9</span></h2>
<p>Security Profiles are attached directly to <em>Allow</em> rules in the Security Policy to perform inline threat prevention:</p>
<table>
    <thead>
        <tr>
            <th style="width: 25%;">Security Profile</th>
            <th style="width: 45%;">Inspection Capabilities</th>
            <th style="width: 30%;">Recommended Action</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>Antivirus Profile</strong></td>
            <td>Stream-based virus/malware inspection across HTTP, HTTPS, FTP, SMB, SMTP, IMAP, POP3.</td>
            <td>Reset-both / Drop for all protocol decoders.</td>
        </tr>
        <tr>
            <td><strong>Anti-Spyware Profile</strong></td>
            <td>Identifies Command and Control (C2) botnet traffic. Features <strong>DNS Sinkholing</strong> to divert malicious DNS queries to a dummy IP.</td>
            <td>Block high/critical; DNS Sinkhole enabled.</td>
        </tr>
        <tr>
            <td><strong>Vulnerability Protection</strong></td>
            <td>Intrusion Prevention System (IPS) stopping buffer overflows, remote code execution (RCE), SQL injection, and OS exploits.</td>
            <td>Reset-both for server & client protections.</td>
        </tr>
        <tr>
            <td><strong>URL Filtering Profile</strong></td>
            <td>Categorizes websites into 80+ categories. Supports actions: <code>allow</code>, <code>alert</code>, <code>block</code>, <code>continue</code> (warning page), <code>override</code> (password bypass).</td>
            <td>Block malware, phishing, adult, and command-and-control categories.</td>
        </tr>
        <tr>
            <td><strong>File Blocking Profile</strong></td>
            <td>Inspects true file magic numbers (not just extension) to block dangerous uploads/downloads (e.g., <code>.exe</code>, <code>.dll</code>, <code>.bat</code>, <code>.scr</code>, multi-level zip).</td>
            <td>Block executables; alert on office docs.</td>
        </tr>
        <tr>
            <td><strong>Data Filtering (DLP)</strong></td>
            <td>Scans outbound traffic for confidential patterns (Credit Card Luhn algorithms, SSNs, custom regex).</td>
            <td>Block or alert security operations.</td>
        </tr>
    </tbody>
</table>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 10: WildFire™ Cloud Threat Intelligence & Sandboxing <span class="badge">Module 10</span></h2>
<ul>
    <li><strong>Zero-Day Detonation:</strong> Files without existing Antivirus signatures are streamed to the WildFire cloud sandbox, executed inside virtual machines, and observed for registry modifications, process injection, and outbound C2 beacons.</li>
    <li><strong>5-Minute Global Signature Turnaround:</strong> When a novel zero-day malware is detonated, WildFire generates a global signature and distributes it to all Palo Alto firewalls worldwide in under 5 minutes.</li>
    <li><strong>Private Cloud Appliance (WF-500):</strong> On-premise hardware sandbox for enterprises with strict compliance regulations prohibiting cloud file streaming.</li>
</ul>

<div class="page-break"></div>

<h2>Module 11: User-ID™ (Identity-Based Security Enforcement) <span class="badge">Module 11</span></h2>
<ul>
    <li><strong>User-to-IP Mapping Mechanisms:</strong>
        <ol>
            <li><strong>Active Directory / Windows Event Log Monitoring:</strong> User-ID Agent queries domain controller Security Event Logs (Events 4624/4625) via WMI/WinRM.</li>
            <li><strong>Syslog Listening:</strong> Parses authentication logs from VPN concentrators, wireless controllers (Aruba/Cisco), and 802.1X RADIUS servers.</li>
            <li><strong>Captive Portal:</strong> Web authentication challenge for unmapped or guest devices.</li>
            <li><strong>GlobalProtect Client:</strong> Automatically passes client username upon VPN connection.</li>
        </ol>
    </li>
    <li><strong>Group Mapping:</strong> Queries Active Directory via LDAP to enumerate domain security groups, enabling policies like <code>Allow 'Finance-Dept' access to SAP-Accounting</code>.</li>
</ul>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 12: SSL/TLS Decryption Architecture <span class="badge">Module 12</span></h2>
<p>Because over 90% of threats hide inside encrypted HTTPS tunnels, SSL Decryption is mandatory for full Content-ID visibility.</p>
<table>
    <thead>
        <tr>
            <th style="width: 25%;">Decryption Type</th>
            <th style="width: 40%;">Architecture & Certificate Requirements</th>
            <th style="width: 35%;">Use Case</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>SSL Forward Proxy</strong></td>
            <td>Firewall acts as Man-in-the-Middle for outbound client sessions. Requires an Enterprise Subordinate CA certificate trusted by client endpoints.</td>
            <td>Inspecting outbound employee web browsing to internet destinations.</td>
        </tr>
        <tr>
            <td><strong>SSL Inbound Inspection</strong></td>
            <td>Firewall holds the private key and server certificate of internal web servers. No client-side certificate installation required.</td>
            <td>Protecting internal DMZ web and e-commerce servers from incoming attacks.</td>
        </tr>
        <tr>
            <td><strong>Decryption Exclusions</strong></td>
            <td>Bypasses decryption for sensitive categories based on privacy regulations (e.g., <code>financial-services</code>, <code>health-and-medicine</code>).</td>
            <td>Compliance with HIPAA, GDPR, and banking privacy laws.</td>
        </tr>
    </tbody>
</table>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 13: Site-to-Site & GlobalProtect™ VPNs <span class="badge">Module 13</span></h2>

<h3>1. Site-to-Site IPsec VPN</h3>
<ul>
    <li><strong>Route-Based VPN:</strong> Uses virtual <code>tunnel.x</code> interfaces assigned to a VPN security zone. Traffic is routed into the tunnel interface via standard static or dynamic routes.</li>
    <li><strong>IKE Phase 1 (ISAKMP):</strong> Authenticates peers and creates a secure management tunnel (IKEv1 / IKEv2, Pre-Shared Key or Certificate, DH Group 14/19/20, AES-256-GCM).</li>
    <li><strong>IKE Phase 2 (IPsec SA):</strong> Negotiates data encryption parameters (ESP, AES-GCM-256, SHA-256, Perfect Forward Secrecy PFS).</li>
</ul>

<h3>2. GlobalProtect™ Remote Access VPN</h3>
<ul>
    <li><strong>GlobalProtect Portal:</strong> Provides client authentication, downloads software agent, and pushes configuration (Gateways, agent settings).</li>
    <li><strong>GlobalProtect Gateway:</strong> Terminates SSL/IPsec VPN tunnels, assigns virtual IP pool addresses to remote clients, and enforces security policies.</li>
    <li><strong>Split Tunnel vs. Full Tunnel:</strong> Split tunnel sends only corporate subnets through VPN while internet traffic goes direct; Full tunnel forces all client traffic through the firewall for centralized security inspection.</li>
</ul>

<div class="page-break"></div>

<h2>Module 14: High Availability (HA) & Clustering <span class="badge">Module 14</span></h2>

<h3>1. HA Deployment Modes</h3>
<ul>
    <li><strong>Active/Passive (Recommended):</strong> One firewall actively processes all traffic while the peer sits in standby. Upon failure, the passive unit takes over in &lt;1 second with zero session drop.</li>
    <li><strong>Active/Active:</strong> Both firewalls simultaneously process traffic. Requires complex routing (VRRP, ECMP) and session ownership management.</li>
</ul>

<h3>2. HA Physical & Logical Links</h3>
<div class="diagram-box">
+---------------------------------------------------------------------------------------------------+
|                               HIGH AVAILABILITY CLUSTER LINKS                                     |
|                                                                                                   |
|    [ FIREWALL-A (Active) ]                                           [ FIREWALL-B (Passive) ]     |
|    ┌─────────────────────┐                                           ┌─────────────────────┐      |
|    │   HA1 (Control)     │ <─────── Heartbeats & Config Sync ──────> │   HA1 (Control)     │      |
|    │   HA1-Backup        │ <─────── Secondary Heartbeat (Mgmt) ────> │   HA1-Backup        │      |
|    │   HA2 (Data Link)   │ <─────── Session & State Table Sync ────> │   HA2 (Data Link)   │      |
|    │   HA2-Backup        │ <─────── UDP/IP Data Replication ───────> │   HA2-Backup        │      |
|    └─────────────────────┘                                           └─────────────────────┘      |
+---------------------------------------------------------------------------------------------------+
</div>

<ul>
    <li><strong>HA1 Link (Control Plane):</strong> Synchronizes configuration changes and exchanges keepalive heartbeats (uses TCP port 28769 and TCP port 28260 for config sync).</li>
    <li><strong>HA2 Link (Data Plane):</strong> Synchronizes active session state tables, NAT mappings, and IPsec SAs at line-rate (uses native Ethernet protocol 0x7261 or UDP port 28443).</li>
    <li><strong>HSCI Port:</strong> Dedicated High Speed Chassis Interconnect (10G/40G) combining HA1/HA2 on high-end appliances (PA-3200 to PA-7000).</li>
    <li><strong>Election Mechanics:</strong> Device Priority (lower number wins active role), Preemption (forces preferred primary firewall to take back active state upon recovery).</li>
    <li><strong>Failover Triggers:</strong> Heartbeat loss, Link Monitoring (monitors specific physical uplinks), and Path Monitoring (monitors next-hop ping reachability).</li>
</ul>

<hr style="border: 0; border-top: 1px solid #E2E8F0; margin: 8px 0;"/>

<h2>Module 15: Hardware Appliance Portfolio & Panorama™ <span class="badge">Module 15</span></h2>

<h3>1. Appliance Portfolios</h3>
<ul>
    <li><strong>PA-400 / PA-220 Series:</strong> Small/branch office. High security performance in quiet/fanless form factors.</li>
    <li><strong>PA-800 / PA-3200 / PA-3400 Series:</strong> Enterprise campus and regional headquarters. High connection density with 10G SFP+ uplinks and redundant power supplies.</li>
    <li><strong>PA-5200 / PA-5400 / PA-7000 Series:</strong> Data center core and carrier grade with modular Network Processing Cards (NPC).</li>
    <li><strong>VM-Series:</strong> Virtual appliances (VM-50 to VM-Flex) running natively in VMware ESXi, KVM, Nutanix, AWS, Azure, GCP, and GNS3/EVE-NG lab environments.</li>
</ul>

<h3>2. Panorama™ Centralized Management</h3>
<ul>
    <li><strong>Device Groups:</strong> Hierarchical organization of firewalls to push shared Security Policies, NAT rules, and Objects (Shared $\rightarrow$ Parent $\rightarrow$ Child Device Groups).</li>
    <li><strong>Templates & Template Stacks:</strong> Pushes device and network configurations (Interfaces, Virtual Routers, HA settings, Zones) across multi-site firewall fleets.</li>
    <li><strong>Centralized Logging & Reporting:</strong> Aggregates log storage from hundreds of firewalls into a single pane of glass for compliance audits.</li>
</ul>

<div class="highlight-card">
    <strong style="color: #0B1E33; font-size: 9.5pt;">Master Architectural Principles for Enterprise Engineers:</strong>
    <ul style="margin-top: 4px; margin-bottom: 0;">
        <li><strong>Single-Pass Software:</strong> Decodes and evaluates packet headers and payloads only once, scanning App-ID, User-ID, and Content-ID in parallel.</li>
        <li><strong>Hardware Separation:</strong> Control Plane CPU is completely isolated from the Data Plane network/security ASICs; high management overhead never drops data traffic.</li>
        <li><strong>Zero-Trust Security Base:</strong> Inter-Zone traffic is denied by default; security rules must explicitly validate Application + User + Security Profiles.</li>
        <li><strong>Deterministic Prevention:</strong> Real-time hardware RegEx engines and automated 5-minute WildFire sandboxing deliver proactive threat prevention.</li>
    </ul>
</div>

</body>
</html>
"""

html_path = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/notes_master.html"
pdf_path = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/Palo_Alto_Firewall_Training_Notes_1hr_to_2hr40m.pdf"

with open(html_path, "w") as f:
    f.write(html_content)

print("Master Course HTML generated. Rendering Complete Multi-Module PDF via Google Chrome Headless...")

cmd = [
    "google-chrome",
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={pdf_path}",
    html_path
]

subprocess.run(cmd, check=True)
print(f"Successfully generated Master PDF: {pdf_path}")

# Also copy to Desktop root
subprocess.run(["cp", pdf_path, "/home/nishusaini/Desktop/Innspark/Palo_Alto_Firewall_Training_Notes_1hr_to_2hr40m.pdf"], check=True)
print("Updated all target PDF locations.")
