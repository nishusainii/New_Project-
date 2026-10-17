import os
import glob
import shutil

raw_dir = "/tmp/palo_raw_minutes"
dest_dir = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/extracted_slides"
os.makedirs(dest_dir, exist_ok=True)

slides_catalog = [
    ("frame_00_00_30.jpg", "slide_00_00_30_course_title.jpg", "Palo Alto Networks Course Title & Trainer Intro", "Course Introduction", [
        "Official I-Medita Palo Alto Networks 11+ Hours Training Masterclass.",
        "Instructor introduction, PCNSE / PCCET certification curriculum alignment.",
        "End-to-end hands-on training roadmap covering enterprise deployments."
    ]),
    ("frame_00_03_30.jpg", "slide_00_03_30_course_agenda.jpg", "Complete Course Agenda & Module Blueprint", "Course Introduction", [
        "Module breakdown from Next-Gen architecture to Advanced Security Profiles.",
        "Hands-on lab topology architecture and initial configuration blueprint.",
        "Deep-dive modules into App-ID, User-ID, Content-ID, NAT, VPN, and HA."
    ]),
    ("frame_00_06_30.jpg", "slide_00_06_30_lab_prerequisites.jpg", "Lab Blueprint & Network Topology Architecture", "Lab Architecture", [
        "Enterprise network topology layout: Trust LAN, Untrust WAN, DMZ, and MGT.",
        "Connecting PA-VM and physical hardware firewalls to enterprise core switches.",
        "IP subnet planning (Trust 10.1.1.0/24, Untrust 192.168.0.0/24, MGT 192.168.1.0/24)."
    ]),
    ("frame_00_09_30.jpg", "slide_00_09_30_security_threat_landscape.jpg", "The Evolution of Enterprise Security Threats", "Security Evolution", [
        "Shift from simple port scanning to sophisticated Layer 7 application attacks.",
        "Rise of ransomware, advanced persistent threats (APTs), and botnet command-and-control.",
        "Why traditional network perimeter boundaries have dissolved."
    ]),
    ("frame_00_13_30.jpg", "slide_00_13_30_firewall_evolution_history.jpg", "History & Evolution of Firewalls (Gen 1 to Gen 5)", "Security Evolution", [
        "1st Gen: Stateless Packet Filters (IP/Port ACLs without connection tracking).",
        "2nd Gen: Stateful Inspection (TCP handshake and session table tracking).",
        "3rd Gen: Application Layer Gateways & Proxies.",
        "4th Gen: UTM (Unified Threat Management) multi-engine appliances.",
        "5th Gen: Single-Pass Next-Generation Firewalls (NGFW)."
    ]),
    ("frame_00_16_30.jpg", "slide_00_16_30_traditional_firewall_limitations.jpg", "Why Port-Based Traditional Firewalls Failed", "NGFW Architecture", [
        "Modern applications do not use fixed, predictable port numbers.",
        "Dynamic port hopping (e.g. BitTorrent, Skype, Zoom, RPC).",
        "Evasive protocols tunneling over open standard ports (TCP 80 HTTP, TCP 443 HTTPS)."
    ]),
    ("frame_00_19_30.jpg", "slide_00_19_30_application_tunneling_evasion.jpg", "Application Tunneling & Evasion Techniques", "Threat Analysis", [
        "Non-web protocols wrapping inside HTTP/HTTPS payloads to bypass perimeter filters.",
        "Port hopping and SSL encryption shielding malicious payloads from traditional inspection.",
        "Need for Layer 7 payload decoders that classify traffic regardless of port."
    ]),
    ("frame_00_26_30.jpg", "slide_00_26_30_next_gen_firewall_requirements.jpg", "Core Requirements for a Next-Generation Firewall", "NGFW Architecture", [
        "Application visibility and granular control across all ports at all times.",
        "Integrated real-time threat prevention (IPS, Antivirus, Anti-Spyware, URL Filtering).",
        "User and group identity-based policies instead of static IP addresses.",
        "High-performance line-rate throughput under full inspection."
    ]),
    ("frame_00_29_30.jpg", "slide_00_29_30_single_pass_vs_utm_comparison.jpg", "Architectural Breakdown: UTM vs Palo Alto SP3", "SP3 Architecture", [
        "UTM Flaws: Sequential daisy-chaining of independent security engines (AV -> IPS -> URL).",
        "UTM Latency: Packets disassembled and reassembled multiple times causing throughput collapse.",
        "Palo Alto SP3: Single packet decode and single uniform signature matching scan."
    ]),
    ("frame_00_34_30.jpg", "slide_00_34_30_sp3_software_architecture.jpg", "Single-Pass Parallel Processing (SP3) Software Engine", "SP3 Architecture", [
        "Uniform Signature Matching: All threat signatures compiled into one unified matrix.",
        "Simultaneous parallel execution of App-ID, User-ID, and Content-ID.",
        "Consistent, predictable performance with all security features enabled."
    ]),
    ("frame_00_37_30.jpg", "slide_00_37_30_hardware_parallel_processing.jpg", "Hardware Processing Engines: NPE, SPE & SME", "Hardware Architecture", [
        "Network Processor (NPE): Wire-speed L2/L3 switching, routing, and NAT offload.",
        "Security Processor (SPE): Hardware cryptographic coprocessor for SSL/TLS and IPsec.",
        "Signature Matching Engine (SME): Custom Match Engine ASICs for parallel RegEx scanning."
    ]),
    ("frame_00_44_30.jpg", "slide_00_44_30_control_plane_data_plane_separation.jpg", "Control Plane vs Data Plane Hardware Separation", "Hardware Architecture", [
        "Management Plane: Dedicated CPU/RAM for Web GUI, CLI, Logging, and Panorama Sync.",
        "Data Plane: Dedicated multi-core CPU and ASICs for line-rate packet forwarding.",
        "Zero performance impact: Generating massive audit reports never slows network traffic."
    ]),
    ("frame_00_51_30.jpg", "slide_00_51_30_core_technologies_app_user_content.jpg", "The 4 Foundational Pillars of PAN-OS", "PAN-OS Core", [
        "App-ID: Layer 7 application classification independent of port or protocol.",
        "User-ID: Active Directory and LDAP identity-based security policies.",
        "Content-ID: Integrated stream-based Antivirus, Anti-Spyware, and IPS.",
        "WildFire: Automated cloud-based zero-day malware detonation and signature generation."
    ]),
    ("frame_01_02_30.jpg", "slide_01_02_30_zero_day_threat_landscape.jpg", "Zero-Day Attack Dynamics & The Patient Zero Problem", "Threat Prevention", [
        "Why signature-based detection fails against newly authored malware variants.",
        "The concept of 'Patient Zero' and the window of vulnerability before signatures exist.",
        "Need for automated, dynamic behavioral sandbox analysis."
    ]),
    ("frame_01_13_30.jpg", "slide_01_13_30_wildfire_cloud_detonation.jpg", "Palo Alto WildFire Sandbox Architecture", "Threat Prevention", [
        "Automated extraction and forwarding of unknown executable files to WildFire cloud.",
        "Virtual multi-OS detonation observing behavioral anomalies (registry, C2 callbacks).",
        "Worldwide distribution of newly created threat signatures in under 5 minutes."
    ]),
    ("frame_01_22_30.jpg", "slide_01_22_30_stateless_acls_vs_stateful_firewalls.jpg", "Stateless ACLs vs Dedicated Firewall Engines", "Firewall Fundamentals", [
        "Stateless router ACLs require explicit bi-directional rules (inbound and outbound).",
        "Rule explosion, administrative overhead, and security holes in stateless filtering.",
        "Inability of stateless ACLs to track TCP sequence numbers or dynamic port negotiations."
    ]),
    ("frame_01_35_30.jpg", "slide_01_35_30_packet_filtering_deep_dive.jpg", "Packet Filtering Mechanics & Header Inspection", "Firewall Fundamentals", [
        "Inspection of Layer 3 IP headers (Source/Dest IP, Protocol) and Layer 4 TCP/UDP ports.",
        "Lack of payload inspection allowing malicious data in permitted ports.",
        "Why Layer 3/4 filtering is insufficient for modern application security."
    ]),
    ("frame_01_44_30.jpg", "slide_01_44_30_proxy_architectures_explicit_transparent.jpg", "Proxy Firewalls: Explicit vs Transparent Proxy", "Firewall Fundamentals", [
        "Dual-socket termination architecture breaking direct client-to-server TCP connections.",
        "Explicit Proxy: Client browser configuration (PAC/WPAD) redirecting traffic to proxy.",
        "Transparent Proxy: Network-level interception (WCCP/PBR) without client reconfiguration.",
        "Scaling limits: Heavy RAM consumption and protocol latency on traditional proxies."
    ]),
    ("frame_01_54_30.jpg", "slide_01_54_30_stateful_inspection_mechanics.jpg", "Stateful Inspection & State Table Mechanics", "Firewall Fundamentals", [
        "Tracking TCP 3-way handshake (SYN, SYN-ACK, ACK) and connection lifecycle.",
        "Session State Table: 5-Tuple (Src IP, Dst IP, Src Port, Dst Port, Protocol) + TCP State.",
        "Fast-Path forwarding: Dynamic return traffic automatically permitted without explicit inbound rule."
    ]),
    ("frame_02_02_30.jpg", "slide_02_02_30_tcp_state_machine_tracking.jpg", "TCP State Machine Tracking & Anti-Spoofing", "Firewall Fundamentals", [
        "Validating TCP sequence and acknowledgment numbers to prevent session hijacking.",
        "Strict TCP window validation and teardown tracking (FIN / RST packets).",
        "Drop policies for out-of-state packets and malformed TCP segments."
    ]),
    ("frame_02_08_30.jpg", "slide_02_08_30_deployment_modes_overview.jpg", "Palo Alto Deployment Modes Overview", "Deployment Modes", [
        "Layer 3 Routed Mode: Full routing, NAT, and gateway functionality.",
        "Layer 2 Mode: Bridging between VLANs with Next-Gen inspection.",
        "Virtual Wire (V-Wire): Transparent inline bump-in-the-wire without IP changes.",
        "TAP Mode: Passive SPAN/mirror port traffic monitoring and visibility."
    ]),
    ("frame_02_14_30.jpg", "slide_02_14_30_virtual_wire_transparent_mode.jpg", "Virtual Wire (V-Wire / Transparent Mode) Deep Dive", "Deployment Modes", [
        "Zero network redesign: Interfaces have NO IP addresses and NO MAC addresses.",
        "Binds two physical ports into an inline transparent inspection tunnel.",
        "Ideal for immediate POC deployments and inserting security between existing core switches."
    ]),
    ("frame_02_20_30.jpg", "slide_02_20_30_firewall_generations_timeline.jpg", "Firewall Generations Timeline & Nir Zuk History", "Industry History", [
        "From Check Point FireWall-1 (1994) to Palo Alto Networks (2007+).",
        "Nir Zuk's pioneering innovations: Stateful Inspection -> Hardware IPS -> NGFW.",
        "How Palo Alto revolutionized the security industry with App-ID and SP3 architecture."
    ]),
    ("frame_02_26_30.jpg", "slide_02_26_30_utm_architecture_bottlenecks.jpg", "UTM Architecture Performance Bottlenecks", "Architecture Deep Dive", [
        "Independent proxies and scanning daemons competing for system RAM and CPU.",
        "Multiple packet disassembly/reassembly stages creating significant packet latency.",
        "Why enabling UTM security features causes a 70-80% throughput drop on legacy firewalls."
    ]),
    ("frame_02_34_30.jpg", "slide_02_34_30_palo_alto_sp3_acceleration.jpg", "Palo Alto SP3 Hardware Acceleration Advantages", "Architecture Deep Dive", [
        "Predictable wire-speed throughput regardless of how many security features are enabled.",
        "Dedicated Control Plane ensures administrative tasks never degrade packet processing.",
        "Parallel hardware coprocessors dedicated to cryptographic offload and regex threat scans."
    ]),
    ("frame_02_41_30.jpg", "slide_02_41_30_hardware_appliance_portfolio.jpg", "Palo Alto Hardware Appliance Portfolios", "Hardware Platforms", [
        "Branch Office: PA-220, PA-400 Series (PA-410, PA-440, PA-450, PA-460).",
        "Mid-Enterprise: PA-500, PA-800 Series (PA-820, PA-850), PA-3200 / PA-3400 Series.",
        "Data Center / Campus Core: PA-5200 Series (PA-5220/5250/5260), PA-5400 Series.",
        "Modular Chassis: PA-7000 Series (PA-7050, PA-7080) for mega data centers and ISPs.",
        "Virtual Firewalls: VM-Series (VM-50, VM-100, VM-300, VM-500, VM-700, VM-Flex)."
    ]),
    ("frame_02_47_30.jpg", "slide_02_47_30_hardware_port_types.jpg", "Hardware Port Types & Interface Roles", "Hardware Platforms", [
        "Management (MGT) Port: Out-of-band 10/100/1000 copper RJ-45 interface (Default IP: 192.168.1.1).",
        "Console Ports: RJ-45 Serial (9600-8-N-1) and Micro-USB for initial setup.",
        "High Availability Ports: Dedicated HA1 (Control/Heartbeat) and HA2 (Session Data Sync).",
        "HSCI Port: High-Speed Cluster Interconnect (10G/40G) on enterprise platforms.",
        "Data Plane Ports: 1G Copper, 1G/10G SFP+, 40G/100G QSFP28 interfaces."
    ]),
    ("frame_02_52_30.jpg", "slide_02_52_30_front_panel_led_diagnostics.jpg", "Front Panel LED Status Diagnostics", "Hardware Platforms", [
        "PWR LED: Green = Redundant power supplies normal; Amber = Power fault / single PSU down.",
        "STS LED: Green = PAN-OS operational; Amber = Booting / initializing; Red = System alarm.",
        "ALM LED: Off = Normal; Amber = Low severity alarm; Red = High severity hardware alarm.",
        "HA LED: Green = Active; Amber = Passive; Off = Standalone / HA disabled."
    ]),
    ("frame_02_57_30.jpg", "slide_02_57_30_console_cable_and_baud_rates.jpg", "Console Connection & Serial Parameters", "Lab Setup", [
        "Connecting via RJ-45 to DB9 / USB-to-Serial rollover console cable.",
        "PuTTY / SecureCRT Terminal Settings: Baud Rate 9600, Data Bits 8, Parity None, Stop Bits 1, Flow Control None.",
        "Default administrative credentials: admin / admin (forced password change on initial login)."
    ]),
    ("frame_03_02_30.jpg", "slide_03_02_30_initial_lab_topology_interconnect.jpg", "Hands-On Lab Topology Interconnect & Setup", "Lab Setup", [
        "Connecting Admin Management PC to MGT port via HTTPS (https://192.168.1.1).",
        "Configuring ethernet1/1 as Trust LAN interface and ethernet1/2 as Untrust WAN interface.",
        "Interconnecting firewall to core switch and upstream internet gateway."
    ])
]

copied_count = 0
for raw_name, new_name, title, cat, notes in slides_catalog:
    src_path = os.path.join(raw_dir, raw_name)
    dst_path = os.path.join(dest_dir, new_name)
    if os.path.exists(src_path):
        shutil.copyfile(src_path, dst_path)
        copied_count += 1
        print(f"Copied: {new_name}")
    else:
        print(f"Warning: {raw_name} not found!")

print(f"\nTotal curated slides organized: {copied_count} / {len(slides_catalog)}")
