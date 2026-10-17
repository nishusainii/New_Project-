import os
import glob
import subprocess

slides_dir = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/extracted_slides"
images = sorted(glob.glob(os.path.join(slides_dir, "*.jpg")))

print(f"Found {len(images)} slide screenshots in {slides_dir}")

html_head = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    @page {
        size: letter landscape;
        margin: 10mm 12mm 10mm 12mm;
        @bottom-right {
            content: "Slide " counter(page) " of " counter(pages);
            font-size: 8pt;
            color: #718096;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        @bottom-left {
            content: "Palo Alto Networks Complete 11+ Hours Video Slide Notes | Innspark Solutions";
            font-size: 8pt;
            color: #718096;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        color: #2D3748;
        background: #F7FAFC;
        margin: 0;
        padding: 0;
    }

    .slide-container {
        page-break-after: always;
        height: 96vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px 20px;
        box-sizing: border-box;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .slide-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 2px solid #FA582D;
        padding-bottom: 6px;
        margin-bottom: 10px;
    }

    .slide-title {
        font-size: 13pt;
        font-weight: 700;
        color: #0F2942;
        margin: 0;
    }

    .slide-timestamp {
        background: #0F2942;
        color: #FBD38D;
        font-size: 8.5pt;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 4px;
        font-family: monospace;
    }

    .slide-content-grid {
        display: grid;
        grid-template-columns: 1.2fr 1fr;
        gap: 16px;
        flex-grow: 1;
        align-items: center;
    }

    .slide-image-box {
        text-align: center;
        background: #1A202C;
        border-radius: 6px;
        padding: 6px;
        border: 1px solid #CBD5E0;
    }

    .slide-image-box img {
        max-width: 100%;
        max-height: 380px;
        object-fit: contain;
        border-radius: 4px;
    }

    .slide-notes-box {
        background: #F8FAFC;
        border-left: 4px solid #2B6CB0;
        padding: 12px 16px;
        border-radius: 0 6px 6px 0;
        font-size: 8.5pt;
        line-height: 1.4;
    }

    .slide-notes-box h4 {
        margin: 0 0 6px 0;
        color: #2B6CB0;
        font-size: 9.5pt;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .slide-notes-box ul {
        margin: 0;
        padding-left: 16px;
    }

    .slide-notes-box li {
        margin-bottom: 4px;
    }

    .cover-slide {
        page-break-after: always;
        height: 96vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background: linear-gradient(135deg, #0F2942 0%, #1A365D 60%, #FA582D 100%);
        color: white;
        text-align: center;
        border-radius: 8px;
        padding: 40px;
        box-sizing: border-box;
    }

    .cover-slide h1 {
        font-size: 26pt;
        margin: 0 0 10px 0;
        font-weight: 800;
        color: #FFFFFF;
    }

    .cover-slide .subtitle {
        font-size: 14pt;
        color: #E2E8F0;
        margin-bottom: 24px;
    }

    .cover-meta {
        background: rgba(255,255,255,0.15);
        padding: 12px 24px;
        border-radius: 6px;
        font-size: 10pt;
        border: 1px solid rgba(255,255,255,0.2);
    }
</style>
</head>
<body>

<div class="cover-slide">
    <h1>PALO ALTO NETWORKS (PAN-OS)</h1>
    <div class="subtitle">Complete Presentation Slides & Architecture Master Deck (11+ Hours Video Course)</div>
    <div class="cover-meta">
        <strong>Source:</strong> I-MEDITA 11+ Hours Training Course &nbsp;|&nbsp; 
        <strong>Format:</strong> High-Resolution Presentation Slide Captures + In-Depth Engineering Notes &nbsp;|&nbsp; 
        <strong>Compiled for:</strong> Nishu Saini (Innspark Solutions)
    </div>
</div>
"""

slide_topics = {
    # 00:00:00 to 03:05:00 Curated Minute-by-Minute Slides
    "slide_00_00_30_course_title.jpg": ("Course Title & Instructor Masterclass Introduction", "00:00:30", [
        "Comprehensive Palo Alto Networks Next-Generation Firewall Training (11+ Hours).",
        "PCNSE & PCCET certification alignment with real-world enterprise architectures.",
        "Instructor introduction and course expectations."
    ]),
    "slide_00_03_30_course_agenda.jpg": ("Complete Training Curriculum & Agenda Blueprint", "00:03:30", [
        "Roadmap covering Firewall Architecture, SP3, Hardware Engines, and Deployment Modes.",
        "Hands-on lab modules: Routing, NAT, Security Policies, App-ID, User-ID, Content-ID, VPN, and HA.",
        "Prerequisites and foundational networking concepts review."
    ]),
    "slide_00_05_00.jpg": ("Course Overview & Architecture Blueprint", "00:05:00", [
        "Complete roadmap of Next-Generation Firewall concepts and lab blueprint.",
        "Evolution from traditional firewalls to Palo Alto Single-Pass Architecture.",
        "Hands-on configuration walkthroughs covering routing, NAT, policies, and VPN."
    ]),
    "slide_00_06_30_lab_prerequisites.jpg": ("Enterprise Lab Topology Blueprint & IP Planning", "00:06:30", [
        "Network topology layout: Trust LAN (10.1.1.0/24), Untrust WAN (192.168.0.0/24), and MGT (192.168.1.0/24).",
        "Interconnecting PA-VM / PA-500 firewalls to Cisco core switches and edge routers.",
        "Setting up management access workstations for Web GUI and CLI console."
    ]),
    "slide_00_09_30_security_threat_landscape.jpg": ("Enterprise Security Threat Landscape Evolution", "00:09:30", [
        "Evolution of threats: From simple port scans to sophisticated Layer 7 application exploits.",
        "Rise of ransomware, advanced persistent threats (APTs), and dynamic botnets.",
        "Why traditional network perimeter boundaries have dissolved in modern enterprises."
    ]),
    "slide_00_12_30.jpg": ("Evolution of Network Security & Firewalls", "00:12:30", [
        "1st Gen Packet Filtering vs 2nd Gen Stateful Inspection vs 5th Gen NGFW.",
        "Why port-based security failed to stop modern application-level threats.",
        "Application visibility as the foundational security baseline."
    ]),
    "slide_00_13_30_firewall_evolution_history.jpg": ("History & Evolution of Firewalls (Gen 1 to Gen 5)", "00:13:30", [
        "1st Gen: Stateless Packet Filters (IP/Port ACLs without connection tracking).",
        "2nd Gen: Stateful Inspection (TCP 3-way handshake and session table tracking).",
        "3rd Gen: Application Layer Gateways & Proxies.",
        "4th Gen: UTM (Unified Threat Management) multi-engine appliances.",
        "5th Gen: Single-Pass Next-Generation Firewalls (NGFW)."
    ]),
    "slide_00_15_30.jpg": ("Traditional Security Pitfalls & Port Evasion", "00:15:30", [
        "How evasive applications bypass legacy port-based access controls.",
        "Port hopping and dynamic protocol negotiation across non-standard ports.",
        "The need for Layer 7 protocol decoders and heuristic classifiers."
    ]),
    "slide_00_16_30_traditional_firewall_limitations.jpg": ("Why Port-Based Traditional Firewalls Failed", "00:16:30", [
        "Modern applications do not use fixed, predictable port numbers.",
        "Dynamic port hopping protocols (BitTorrent, Skype, Zoom, RPC).",
        "Evasive protocols tunneling over open standard ports (TCP 80 HTTP, TCP 443 HTTPS)."
    ]),
    "slide_00_19_30_application_tunneling_evasion.jpg": ("Application Tunneling & Evasion Techniques", "00:19:30", [
        "Non-web protocols wrapping inside HTTP/HTTPS payloads to bypass perimeter filters.",
        "Port hopping and SSL encryption shielding malicious payloads from traditional inspection.",
        "Need for Layer 7 payload decoders that classify traffic regardless of port."
    ]),
    "slide_00_22_00.jpg": ("Port Hopping & Application Evasion Tactics", "00:22:00", [
        "Applications bypassing traditional firewalls using non-standard dynamic ports.",
        "Tunneling evasive data over standard HTTP (port 80) and HTTPS (port 443).",
        "Why App-ID decodes payloads regardless of port numbers."
    ]),
    "slide_00_26_30_next_gen_firewall_requirements.jpg": ("Core Requirements for Next-Generation Firewalls", "00:26:30", [
        "Application visibility and granular control across all ports at all times.",
        "Integrated real-time threat prevention (IPS, Antivirus, Anti-Spyware, URL Filtering).",
        "User and group identity-based policies instead of static IP addresses.",
        "High-performance line-rate throughput under full inspection."
    ]),
    "slide_00_29_30_single_pass_vs_utm_comparison.jpg": ("Architectural Breakdown: UTM vs Palo Alto SP3", "00:29:30", [
        "UTM Flaws: Sequential daisy-chaining of independent security engines (AV -> IPS -> URL).",
        "UTM Latency: Packets disassembled and reassembled multiple times causing throughput collapse.",
        "Palo Alto SP3: Single packet decode and single uniform signature matching scan."
    ]),
    "slide_00_32_00.jpg": ("Single-Pass Parallel Processing (SP3) Architecture", "00:32:00", [
        "Single packet decode and uniform signature matching matrix.",
        "Parallel hardware evaluation of App-ID, User-ID, and Content-ID.",
        "Elimination of UTM multi-pass latency bottlenecks."
    ]),
    "slide_00_34_30_sp3_software_architecture.jpg": ("SP3 Software Engine & Uniform Signature Scan", "00:34:30", [
        "Uniform Signature Matching: All threat signatures compiled into one unified matrix.",
        "Simultaneous parallel execution of App-ID, User-ID, and Content-ID.",
        "Consistent, predictable performance with all security features enabled."
    ]),
    "slide_00_37_30_hardware_parallel_processing.jpg": ("Hardware Processing Engines: NPE, SPE & SME", "00:37:30", [
        "Network Processor (NPE): Wire-speed L2/L3 switching, routing, and NAT offload.",
        "Security Processor (SPE): Hardware cryptographic coprocessor for SSL/TLS and IPsec.",
        "Signature Matching Engine (SME): Custom Match Engine ASICs for parallel RegEx scanning."
    ]),
    "slide_00_44_30_control_plane_data_plane_separation.jpg": ("Control Plane vs Data Plane Hardware Separation", "00:44:30", [
        "Management Plane: Dedicated CPU/RAM for Web GUI, CLI, Logging, and Panorama Sync.",
        "Data Plane: Dedicated multi-core CPU and ASICs for line-rate packet forwarding.",
        "Zero performance impact: Generating massive audit reports never slows network traffic."
    ]),
    "slide_00_45_00.jpg": ("Control Plane vs Data Plane Architecture", "00:45:00", [
        "Dedicated Control Plane CPU/RAM for GUI, CLI, logging, and reporting.",
        "Dedicated Data Plane ASICs (NPE, SPE, SME) for line-rate packet forwarding.",
        "Heavy administrative reporting never causes packet drops or latency."
    ]),
    "slide_00_51_30_core_technologies_app_user_content.jpg": ("The 4 Foundational Pillars of PAN-OS", "00:51:30", [
        "App-ID: Layer 7 application classification independent of port or protocol.",
        "User-ID: Active Directory and LDAP identity-based security policies.",
        "Content-ID: Integrated stream-based Antivirus, Anti-Spyware, and IPS.",
        "WildFire: Automated cloud-based zero-day malware detonation and signature generation."
    ]),
    "slide_00_55_00.jpg": ("The 4 Core Pillars of PAN-OS", "00:55:00", [
        "App-ID: Layer 7 application classification without port reliance.",
        "User-ID: Active Directory & LDAP identity-based policy enforcement.",
        "Content-ID: Integrated stream-based Antivirus, Anti-Spyware, and IPS.",
        "WildFire: Automated zero-day cloud sandboxing."
    ]),
    "slide_01_02_30_zero_day_threat_landscape.jpg": ("Zero-Day Attacks & The Patient Zero Threat Model", "01:02:30", [
        "Why signature-based detection fails against newly authored malware variants.",
        "The concept of 'Patient Zero' and the window of vulnerability before signatures exist.",
        "Need for automated, dynamic behavioral sandbox analysis."
    ]),
    "slide_01_08_00.jpg": ("Zero-Day Attack Threat Landscape", "01:08:00", [
        "Why hash and signature comparison fails against unknown malware.",
        "The need for dynamic behavioral detonation environments.",
        "The Patient Zero threat model in enterprise networks."
    ]),
    "slide_01_13_30_wildfire_cloud_detonation.jpg": ("Palo Alto WildFire Sandbox Architecture", "01:13:30", [
        "Automated extraction and forwarding of unknown executable files to WildFire cloud.",
        "Virtual multi-OS detonation observing behavioral anomalies (registry, C2 callbacks).",
        "Worldwide distribution of newly created threat signatures in under 5 minutes."
    ]),
    "slide_01_18_00.jpg": ("Palo Alto WildFire Detonation Architecture", "01:18:00", [
        "Automated streaming of unknown executables/scripts to WildFire sandbox.",
        "Virtual multi-OS detonation observing registry and C2 behaviors.",
        "Global 5-minute signature distribution worldwide."
    ]),
    "slide_01_22_30_stateless_acls_vs_stateful_firewalls.jpg": ("Stateless ACLs vs Dedicated Stateful Firewalls", "01:22:30", [
        "Stateless router ACLs require explicit bi-directional rules (inbound and outbound).",
        "Rule explosion, administrative overhead, and security holes in stateless filtering.",
        "Inability of stateless ACLs to track TCP sequence numbers or dynamic port negotiations."
    ]),
    "slide_01_35_00.jpg": ("Stateless ACLs vs Dedicated Firewall Engines", "01:35:00", [
        "Stateless packet filters requiring separate inbound and outbound rules.",
        "Rule explosion and security vulnerabilities in stateless router ACLs.",
        "Bidirectional connection tracking fundamentals."
    ]),
    "slide_01_35_30_packet_filtering_deep_dive.jpg": ("Packet Filtering Mechanics & Header Inspection", "01:35:30", [
        "Inspection of Layer 3 IP headers (Source/Dest IP, Protocol) and Layer 4 TCP/UDP ports.",
        "Lack of payload inspection allowing malicious data in permitted ports.",
        "Why Layer 3/4 filtering is insufficient for modern application security."
    ]),
    "slide_01_44_30_proxy_architectures_explicit_transparent.jpg": ("Proxy Architectures: Explicit vs Transparent", "01:44:30", [
        "Dual-socket termination architecture breaking direct client-to-server TCP connections.",
        "Explicit Proxy: Client browser configuration (PAC/WPAD) redirecting traffic to proxy.",
        "Transparent Proxy: Network-level interception (WCCP/PBR) without client reconfiguration.",
        "Scaling limits: Heavy RAM consumption and protocol latency on traditional proxies."
    ]),
    "slide_01_48_00.jpg": ("Proxy Architectures: Explicit vs Transparent", "01:48:00", [
        "Dual-socket termination mechanics breaking direct client-server links.",
        "Explicit Proxy (browser PAC settings) vs Transparent Proxy (inline WCCP).",
        "Caching benefits vs protocol restrictions and RAM scaling limits."
    ]),
    "slide_01_54_30_stateful_inspection_mechanics.jpg": ("Stateful Inspection & Session Table Architecture", "01:54:30", [
        "Tracking TCP 3-way handshake (SYN, SYN-ACK, ACK) and connection lifecycle.",
        "Session State Table: 5-Tuple (Src IP, Dst IP, Src Port, Dst Port, Protocol) + TCP State.",
        "Fast-Path forwarding: Dynamic return traffic automatically permitted without explicit inbound rule."
    ]),
    "slide_02_02_00.jpg": ("Stateful Inspection & State Table Mechanics", "02:02:00", [
        "In-memory State Table (Session Table) tracking 5-tuples and TCP state flags.",
        "Fast-Path forwarding for established sessions bypassing full policy lookup.",
        "TCP Sequence and Acknowledgment validation against session hijacking."
    ]),
    "slide_02_02_30_tcp_state_machine_tracking.jpg": ("TCP State Machine Tracking & Anti-Spoofing", "02:02:30", [
        "Validating TCP sequence and acknowledgment numbers to prevent session hijacking.",
        "Strict TCP window validation and teardown tracking (FIN / RST packets).",
        "Drop policies for out-of-state packets and malformed TCP segments."
    ]),
    "slide_02_08_30_deployment_modes_overview.jpg": ("Palo Alto Deployment Modes Overview", "02:08:30", [
        "Layer 3 Routed Mode: Full routing, NAT, and gateway functionality.",
        "Layer 2 Mode: Bridging between VLANs with Next-Gen inspection.",
        "Virtual Wire (V-Wire): Transparent inline bump-in-the-wire without IP changes.",
        "TAP Mode: Passive SPAN/mirror port traffic monitoring and visibility."
    ]),
    "slide_02_14_30_virtual_wire_transparent_mode.jpg": ("Virtual Wire (V-Wire / Transparent Mode) Deep Dive", "02:14:30", [
        "Zero network redesign: Interfaces have NO IP addresses and NO MAC addresses.",
        "Binds two physical ports into an inline transparent inspection tunnel.",
        "Ideal for immediate POC deployments and inserting security between existing core switches."
    ]),
    "slide_02_15_00.jpg": ("Deployment Modes: Routed vs Virtual Wire (V-Wire)", "02:15:00", [
        "Layer 3 Routed mode acting as enterprise gateway with NAT and routing.",
        "Virtual Wire (V-Wire) 'Bump-in-the-Wire' transparent inline inspection.",
        "Zero IP redesign for immediate proof-of-concept (POC) integration."
    ]),
    "slide_02_20_30_firewall_generations_timeline.jpg": ("Firewall Generations Timeline & Nir Zuk History", "02:20:30", [
        "From Check Point FireWall-1 (1994) to Palo Alto Networks (2007+).",
        "Nir Zuk's pioneering innovations: Stateful Inspection -> Hardware IPS -> NGFW.",
        "How Palo Alto revolutionized the security industry with App-ID and SP3 architecture."
    ]),
    "slide_02_25_00.jpg": ("Firewall Generations & Nir Zuk History", "02:25:00", [
        "Nir Zuk's industry legacy: Check Point -> OneSecure IPS -> NetScreen/Juniper -> Palo Alto.",
        "Architecting Palo Alto Networks from scratch to solve application evasion.",
        "Transition from UTM multi-engine boxes to Single-Pass Next-Gen Firewalls."
    ]),
    "slide_02_26_30_utm_architecture_bottlenecks.jpg": ("UTM Architecture Performance Bottlenecks", "02:26:30", [
        "Independent proxies and scanning daemons competing for system RAM and CPU.",
        "Multiple packet disassembly/reassembly stages creating significant packet latency.",
        "Why enabling UTM security features causes a 70-80% throughput drop on legacy firewalls."
    ]),
    "slide_02_34_30_palo_alto_sp3_acceleration.jpg": ("Palo Alto SP3 Hardware Acceleration Advantages", "02:34:30", [
        "Predictable wire-speed throughput regardless of how many security features are enabled.",
        "Dedicated Control Plane ensures administrative tasks never degrade packet processing.",
        "Parallel hardware coprocessors dedicated to cryptographic offload and regex threat scans."
    ]),
    "slide_02_35_00.jpg": ("UTM Multi-Pass Flaws vs Single-Pass Acceleration", "02:35:00", [
        "Traditional UTM daisy-chaining packet disassembly and reassembly penalties.",
        "How SP3 evaluates all threat signatures in a single scan cycle.",
        "Predictable throughput under full Next-Generation security inspection."
    ]),
    "slide_02_41_30_hardware_appliance_portfolio.jpg": ("Palo Alto Hardware Appliance Portfolios", "02:41:30", [
        "Branch Office: PA-220, PA-400 Series (PA-410, PA-440, PA-450, PA-460).",
        "Mid-Enterprise: PA-500, PA-800 Series (PA-820, PA-850), PA-3200 / PA-3400 Series.",
        "Data Center / Campus Core: PA-5200 Series (PA-5220/5250/5260), PA-5400 Series.",
        "Modular Chassis: PA-7000 Series (PA-7050, PA-7080) for mega data centers and ISPs.",
        "Virtual Firewalls: VM-Series (VM-50, VM-100, VM-300, VM-500, VM-700, VM-Flex)."
    ]),
    "slide_02_47_30_hardware_port_types.jpg": ("Hardware Port Types & Interface Roles", "02:47:30", [
        "Management (MGT) Port: Out-of-band 10/100/1000 copper RJ-45 interface (Default IP: 192.168.1.1).",
        "Console Ports: RJ-45 Serial (9600-8-N-1) and Micro-USB for initial setup.",
        "High Availability Ports: Dedicated HA1 (Control/Heartbeat) and HA2 (Session Data Sync).",
        "HSCI Port: High-Speed Cluster Interconnect (10G/40G) on enterprise platforms.",
        "Data Plane Ports: 1G Copper, 1G/10G SFP+, 40G/100G QSFP28 interfaces."
    ]),
    "slide_02_48_00.jpg": ("Palo Alto Hardware Appliance Portfolios", "02:48:00", [
        "Branch Series: PA-220 & PA-400 Series (fanless options).",
        "Enterprise Series: PA-500, PA-800, and PA-3200 / PA-3400 Series.",
        "Data Center & Modular Chassis: PA-5200, PA-5400, and PA-7000 Series.",
        "Virtual Appliances: VM-Series for ESXi, KVM, AWS, Azure, and GNS3."
    ]),
    "slide_02_52_30_front_panel_led_diagnostics.jpg": ("Front Panel LED Status Diagnostics", "02:52:30", [
        "PWR LED: Green = Redundant power supplies normal; Amber = Power fault / single PSU down.",
        "STS LED: Green = PAN-OS operational; Amber = Booting / initializing; Red = System alarm.",
        "ALM LED: Off = Normal; Amber = Low severity alarm; Red = High severity hardware alarm.",
        "HA LED: Green = Active; Amber = Passive; Off = Standalone / HA disabled."
    ]),
    "slide_02_57_30_console_cable_and_baud_rates.jpg": ("Console Connection & Serial Parameters", "02:57:30", [
        "Connecting via RJ-45 to DB9 / USB-to-Serial rollover console cable.",
        "PuTTY / SecureCRT Terminal Settings: Baud Rate 9600, Data Bits 8, Parity None, Stop Bits 1, Flow Control None.",
        "Default administrative credentials: admin / admin (forced password change on initial login)."
    ]),
    "slide_03_00_00.jpg": ("Hardware Port Matrix & Front Panel LEDs", "03:00:00", [
        "Dedicated Out-of-Band MGT Port (192.168.1.1/24) and Console (9600-8-N-1).",
        "HA1 (Control/Heartbeat), HA2 (Data Sync), and HSCI (10G/40G) ports.",
        "Front-panel LED diagnostics: PWR, STS (Green=Ready, Amber=Boot), ALM, HA."
    ]),
    "slide_03_02_30_initial_lab_topology_interconnect.jpg": ("Hands-On Lab Topology Interconnect & Setup", "03:02:30", [
        "Connecting Admin Management PC to MGT port via HTTPS (https://192.168.1.1).",
        "Configuring ethernet1/1 as Trust LAN interface and ethernet1/2 as Untrust WAN interface.",
        "Interconnecting firewall to core switch and upstream internet gateway."
    ]),
    "slide_03_12_00.jpg": ("Hands-On Enterprise Lab Topology Design", "03:12:00", [
        "Architecture of Trust LAN (10.1.1.0/24), Untrust WAN (192.168.0.0/24), and MGT.",
        "Connecting admin PC via HTTPS/SSH to PA-VM-1 / PA-500 management port.",
        "Core switch and ISP router interconnection layout."
    ]),
    "slide_03_30_00.jpg": ("Initial PAN-OS Access & CLI Command Structure", "03:30:00", [
        "Default login credentials (admin/admin) and forced password change.",
        "Operational mode vs Configuration mode (`configure`) commands.",
        "`show`, `set`, `request`, and `test` command taxonomy."
    ]),
    "slide_03_50_00.jpg": ("Candidate Config, Running Config & Commit Engine", "03:50:00", [
        "Candidate Configuration draft changes vs active Running Configuration.",
        "Commit operation compiling rules into hardware ASICs.",
        "Reverting uncommitted changes and utilizing multi-admin config locks."
    ]),
    "slide_03_58_00_vsys_intro.jpg": ("Virtual Systems (VSYS) Fundamentals & Overview", "03:58:00", [
        "Logical partitioning of a single physical firewall into multiple independent virtual firewalls.",
        "Complete isolation of traffic, routing tables, security rules, NAT, and administrators.",
        "Ideal for Managed Service Providers (MSPs), large multi-division enterprises, and compliance segregation."
    ]),
    "slide_04_02_00_vsys_concept.jpg": ("Virtual Systems Multi-Tenancy Architecture", "04:02:00", [
        "Each VSYS operates as a standalone security domain with its own zones, virtual routers, and policies.",
        "Shared physical hardware acceleration (SP3 engine, Single-Pass classification) across all virtual systems.",
        "Eliminates hardware sprawl while maintaining strict isolation between tenant environments."
    ]),
    "slide_04_05_00_vsys.jpg": ("VSYS Hardware Support, Platform Matrix & Licenses", "04:05:00", [
        "Supported on PA-3000, PA-3200, PA-3400, PA-5000, PA-5200, PA-5400, PA-7000 Series, and VM-300 / VM-Flex.",
        "Base VSYS included by default with optional multi-vsys expansion licenses (e.g. up to 225 on PA-7000).",
        "Note: Entry-level branch models (PA-220, PA-400) do not support multi-VSYS."
    ]),
    "slide_04_08_00_vsys_architecture.jpg": ("VSYS Partitioning: Independent Policies, NAT & Objects", "04:08:00", [
        "Independent Rulebase: Tenant A cannot view or modify Tenant B's Security or NAT policies.",
        "Dedicated Object Repositories: Custom address objects, service groups, and URL categories per VSYS.",
        "Global Shared Objects: Master administrator can publish global security profiles accessible across all VSYS."
    ]),
    "slide_04_12_00_vsys_intervsys.jpg": ("Inter-VSYS Routing & Internal Packet Exchange", "04:12:00", [
        "Routing traffic between distinct VSYS instances internally inside the firewall without physical loopback cables.",
        "Utilizes internal Virtual Routers or Shared Gateways for ultra-low latency, line-rate inter-tenant routing.",
        "Enforces Security Policies and Content-ID threat inspection on all inter-VSYS traffic flows."
    ]),
    "slide_04_15_00.jpg": ("Security Zones & Policy Rule Evaluation", "04:15:00", [
        "Zero-Trust zone model: Intra-zone allowed, Inter-zone denied by default.",
        "Top-to-bottom, first-match rule processing mechanics.",
        "Rule anatomy: Source Zone/IP, User, Dest Zone/IP, App-ID, Service, Action."
    ]),
    "slide_04_18_00_vsys_shared_gw.jpg": ("Shared Gateways & Centralized WAN Edge Architecture", "04:18:00", [
        "Shared Gateway allows multiple VSYS tenants to share a single public internet uplink and public IP pool.",
        "Centralized perimeter security enforcement while delegating internal departmental policies to individual VSYS.",
        "Simplifies WAN management and reduces public IP subnet consumption."
    ]),
    "slide_04_20_00_vsys.jpg": ("Interface & Zone Binding to Virtual Systems", "04:20:00", [
        "Binding physical interfaces, 802.1Q sub-interfaces, and VLAN interfaces to specific VSYS instances.",
        "Security zones are strictly scoped within their parent VSYS (e.g. `vsys1-Trust`, `vsys2-Trust`).",
        "VLAN tagging allows multiple tenants to share trunked physical switch links into separate VSYS."
    ]),
    "slide_04_25_00_vsys_admin_mgmt.jpg": ("Multi-Tenant Administrator Roles & Role-Based Access", "04:25:00", [
        "Superuser (Device Administrator): Full control over all VSYS, hardware settings, and global objects.",
        "VSYS Administrator: Restricted strictly to managing their designated virtual system(s).",
        "Tenant isolation prevents unauthorized changes or audit visibility into other departments or clients."
    ]),
    "slide_04_30_00_vsys_resource_limit.jpg": ("Resource Allocation: Session, Rule & NAT Limits per VSYS", "04:30:00", [
        "Resource Profiles prevent a single rogue tenant from exhausting firewall CPU or session memory (Noisy Neighbor).",
        "Enforceable limits per VSYS: Max concurrent sessions, Security Rules, NAT Rules, VPN Tunnels, and Decryption sessions.",
        "Dynamic real-time monitoring and alerting when a VSYS approaches its configured resource threshold."
    ]),
    "slide_04_40_00.jpg": ("Interface Configuration & Management Profiles", "04:40:00", [
        "Assigning Layer 3 interfaces to Virtual Routers and Security Zones.",
        "Default block of ping/SSH on data plane interface IP addresses.",
        "Creating and applying Interface Management Profiles to permit ICMP ping."
    ]),
    "slide_05_05_00.jpg": ("Virtual Routers & Static Routing Configuration", "05:05:00", [
        "Decoupling routing tables using Virtual Routers (e.g. `default`).",
        "Configuring default route (0.0.0.0/0) pointing to upstream ISP gateway.",
        "Administrative distance, route metrics, and 802.1Q tagged sub-interfaces."
    ]),
    "slide_05_30_00.jpg": ("Path Monitoring & Dynamic WAN Failover (IP SLA)", "05:30:00", [
        "Attaching ICMP ping probes to next-hop gateway monitoring.",
        "Automatic route withdrawal and failover to backup ISP on line failure.",
        "Configuring probe intervals and failure thresholds."
    ]),
    "slide_06_00_00.jpg": ("Source NAT: Dynamic IP and Port (DIPP / PAT)", "06:00:00", [
        "Translating private LAN subnets to public interface IP with port multiplexing.",
        "Pre-NAT Source/Destination vs Post-NAT interface translation.",
        "Up to 64,000 concurrent sessions per IP address."
    ]),
    "slide_06_30_00.jpg": ("Destination NAT: Inbound Port Forwarding", "06:30:00", [
        "Publishing internal DMZ servers to public internet.",
        "Translating public destination IP:port to private server IP:port.",
        "Security policy configuration matching pre-NAT destination IP and post-NAT zone."
    ]),
    "slide_07_00_00.jpg": ("U-Turn NAT (Hairpinning) for Internal Access", "07:00:00", [
        "Allowing internal LAN users to access internal servers via public IP/DNS.",
        "Source NAT + Destination NAT dual-translation on the same physical interface.",
        "Preventing asymmetric routing drops inside the LAN."
    ]),
    "slide_07_30_00.jpg": ("App-ID™ Protocol Decoders & Heuristics", "07:30:00", [
        "Payload inspection across initial packets to classify exact application.",
        "Handling application shifts (e.g. SSL -> Facebook -> Facebook-Chat).",
        "App-ID dependencies and parent/child application definitions."
    ]),
    "slide_08_00_00.jpg": ("Policy Optimizer & App-ID Migration", "08:00:00", [
        "Analyzing legacy port-based rules (`any` application on port 80/443).",
        "Built-in Policy Optimizer monitoring observed App-IDs over time.",
        "1-click migration to tight, least-privilege App-ID rules."
    ]),
    "slide_08_30_00.jpg": ("Content-ID™ Suite: Antivirus, Anti-Spyware & DNS Sinkholing", "08:30:00", [
        "Stream-based Antivirus across HTTP, FTP, SMB, SMTP, and POP3.",
        "Anti-Spyware blocking C2 botnet communication.",
        "DNS Sinkholing diverting malicious domain queries to decoy IP for threat isolation."
    ]),
    "slide_09_00_00.jpg": ("Vulnerability Protection (IPS) & URL Filtering", "09:00:00", [
        "IPS signatures preventing buffer overflows, RCE, and OS exploits.",
        "URL Filtering across 80+ web categories.",
        "Action controls: `allow`, `alert`, `block`, `continue` (warning), and `override`."
    ]),
    "slide_09_30_00.jpg": ("User-ID™ Integration with Active Directory", "09:30:00", [
        "User-ID Agent querying Windows Event Logs (Events 4624/4625) via WMI/WinRM.",
        "Syslog listener parsing VPN, 802.1X, and wireless authentication.",
        "LDAP group mapping for role-based security rules."
    ]),
    "slide_10_00_00.jpg": ("SSL/TLS Decryption: Forward Proxy vs Inbound Inspection", "10:00:00", [
        "SSL Forward Proxy: Enterprise Subordinate CA inspecting outbound employee traffic.",
        "SSL Inbound Inspection: Protecting internal servers using private keys.",
        "Decryption exclusions for financial and healthcare compliance."
    ]),
    "slide_10_30_00.jpg": ("Site-to-Site IPsec VPN (IKEv1 / IKEv2)", "10:30:00", [
        "Route-based VPN architecture using virtual `tunnel.x` interfaces.",
        "IKE Phase 1 (ISAKMP management tunnel) & IKE Phase 2 (IPsec SA data encryption).",
        "DH Groups, AES-256-GCM encryption, and Perfect Forward Secrecy (PFS)."
    ]),
    "slide_11_00_00.jpg": ("High Availability (Active/Passive) & Clustering Failover", "11:00:00", [
        "Active/Passive cluster state synchronization and sub-second failover.",
        "HA1 Control Link (Config & Heartbeats) and HA2 Data Link (Session State Table).",
        "Device Priority, Preemption, Link Monitoring, and Path Monitoring failover triggers."
    ])
}

html_body = ""

for img_path in images:
    img_name = os.path.basename(img_path)
    title, ts, bullets = slide_topics.get(img_name, (
        f"Training Slide: {img_name}", "Full Course", [
            "Comprehensive Next-Generation Firewall concepts and configuration.",
            "Architectural deep-dive and real-world deployment walkthrough."
        ]
    ))
    
    bullets_html = "".join([f"<li>{b}</li>" for b in bullets])
    
    html_body += f"""
    <div class="slide-container">
        <div class="slide-header">
            <h3 class="slide-title">{title}</h3>
            <span class="slide-timestamp">Timestamp: {ts}</span>
        </div>
        <div class="slide-content-grid">
            <div class="slide-image-box">
                <img src="{img_path}" alt="{title}"/>
            </div>
            <div class="slide-notes-box">
                <h4>Core Concepts & Key Highlights</h4>
                <ul>
                    {bullets_html}
                </ul>
            </div>
        </div>
    </div>
    """

html_full = html_head + html_body + "</body></html>"

out_html = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/slides_presentation_master.html"
out_pdf = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/Palo_Alto_Complete_Presentation_SlideDeck.pdf"

with open(out_html, "w") as f:
    f.write(html_full)

print(f"Generated visual slides HTML with {len(images)} slides. Converting to Presentation PDF via Chrome...")

cmd = [
    "google-chrome",
    "--headless",
    "--disable-gpu",
    "--no-pdf-header-footer",
    f"--print-to-pdf={out_pdf}",
    out_html
]

subprocess.run(cmd, check=True)
print(f"Successfully generated Visual Slide Deck PDF: {out_pdf}")

# Copy to Desktop root
subprocess.run(["cp", out_pdf, "/home/nishusaini/Desktop/Innspark/Palo_Alto_Complete_Presentation_SlideDeck.pdf"], check=True)
print("Updated Desktop root copy.")
