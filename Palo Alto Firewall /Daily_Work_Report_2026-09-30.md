Name: Nishu Saini
Date: 30/09/2026
Login Time: 09:10 AM
Logout Time: 07:00 PM

Today’s Work Summary

09:15 AM to 09:45 AM

Juniper TAC Support Coordination & 3rd-Party Service Provider LOA Alignment (Case #2026-0923-938239)

- Re-engaged with Juniper Customer Care Lead (Angelica T) regarding Case Reference ID 2026-0923-938239 for the Juniper EX2300-C compact switch (Serial Number: HV0217520242).
- Confirmed compliance classification under Juniper's framework as an on-site 3rd-Party IT service & network infrastructure management provider operating directly under Amrita Vishwa Vidyapeetham (Amritapuri Campus).
- Reaffirmed that Juniper's internal account management team is actively coordinating the formal Letter of Authorization (LOA) directly with Amrita Vishwa Vidyapeetham.
- Clarified individual software download licensing compliance: Re-confirmed that individual profile hareesh@innspark.in will receive direct software download entitlement upon LOA clearance (avoiding group mailbox restrictions on itsupport@innspark.in).
- Status: In Progress / Actively Tracking Institutional LOA Clearance & Software Portal Unlock.

09:45 AM to 12:00 PM

Palo Alto NGFW Training: Core Architecture, Deployment Modes & Hardware Platform

Key Technical Learnings:

- Proxy Architectures (Explicit vs. Transparent): Understood dual-socket TCP termination mechanics, Explicit Proxy redirection via PAC/WPAD browser settings, Transparent Proxy interception using WCCP / Policy-Based Routing (PBR), and traditional proxy hardware scaling limits.
- Stateful Inspection & Session Table Architecture: Studied TCP 3-way handshake tracking and in-memory Session State Table lookups (5-Tuple: Source/Destination IP, Source/Destination Port, Protocol + TCP state flags), along with dynamic Fast-Path forwarding for established return traffic.
- Firewall Deployment Modes: Explored Layer 3 Routed Mode (routing, NAT, default gateway), Layer 2 Virtual Wire (V-Wire / Transparent "Bump-in-the-Wire" mode allowing inline inspection with zero IP/MAC redesign for instant deployment), and TAP Mode (passive SPAN monitoring).
- Evolution of Firewall Technology: Traced progression from 1st Gen Stateless Packet Filters to 2nd Gen Stateful Inspection to 4th Gen UTM and 5th Gen Single-Pass NGFW, including Nir Zuk's industry contributions.
- UTM Bottlenecks vs. Palo Alto SP3 Engine: Analyzed performance penalties in traditional UTM multi-pass engines (repeated packet disassembly/reassembly) versus Palo Alto's Single-Pass Parallel Processing (SP3) uniform signature matching matrix and Control Plane vs. Data Plane hardware separation.
- Hardware Platform & Port Matrix: Studied hardware sizing across Branch (PA-220/400), Enterprise (PA-500/800/3200), and Data Center Chassis (PA-5200/7000); reviewed port roles (MGT 192.168.1.1, Console 9600-8-N-1, HA1 Heartbeat, HA2 Session Sync, HSCI) and front panel LED diagnostics (PWR, STS, ALM, HA).
- Virtual Systems (VSYS) Multi-Tenancy: Understood logical firewall virtualization, independent rulebases, Inter-VSYS internal routing, Shared Gateways, multi-tenant RBAC administration, and resource allocation limits.

12:00 PM to 01:40 PM

GNS3 Lab Environment Stabilization, Full Topology Reset & Multi-Segment Enterprise Routing with DHCP

Key Technical Implementation & Hands-on Work:

- Host System Performance Optimization: Diagnosed host kernel memory freezes during GNS3 node launches; resolved by upgrading system swap space from 2 GB to 16 GB (/swapfile), increasing total virtual memory capacity to ~31 GB.
- GNS3 Daemon Restoration: Re-instantiated Docker backend service (gns3-server), verified API accessibility on port 3080, initialized Palo-Alto-Lab project, and verified dedicated Out-of-Band (OOB) management connectivity to Palo Alto Web GUI at https://172.17.0.50.
- Topology Realignment & Cleanup: Removed erroneous direct cabling between Palo Alto firewall and switches (ethernet1/0 <-> Switch1, ethernet1/1 <-> Switch2) as well as temporary router-to-firewall data cables.
- CLI Terminal Fix & Full Configuration Reset:
  - Addressed browser-based Tab key trapping in GNS3 Web UI by switching to direct native Linux telnet console sessions (port 5000 for Palo Alto, port 5022 for VyOS) and disabled CLI scripting mode.
  - Flushed hardcoded static IP configs and startup scripts across all 8 VPCS client nodes (PC1–PC8).
  - Cleared all interface IP configurations on VyOS Enterprise Router.
  - Logged into Palo Alto PAN-OS (admin / Nishu@123@), wiped all candidate policies, NAT rules, zones, and interfaces, and committed with 0 configured interfaces while preserving GUI management connectivity.
- Dual-Segment Enterprise Routing & Kea DHCP Deployment:
  - Configured VyOS routing gateways: eth0 (10.0.0.2/30 - Firewall Uplink), eth1 (192.168.10.1/24 - Switch1 Gateway), and eth2 (192.168.20.1/24 - Switch2 Gateway).
  - Activated and tuned Kea DHCP server on VyOS for both subnets:
    - LAN-1 (Switch1): 192.168.10.10 – 192.168.10.50 (Gateway: 192.168.10.1, DNS: 8.8.8.8)
    - LAN-2 (Switch2): 192.168.20.10 – 192.168.20.50 (Gateway: 192.168.20.1, DNS: 8.8.8.8)
  - Resolved Kea DHCP backend syntax requirements (subnet-id) and purged orphaned shared network declarations.
- End-to-End Validation & Traffic Verification:
  - Verified PC1 successfully leased IP 192.168.10.10/24 via DHCP and achieved sub-millisecond ping response to router gateway (0.37 ms).
  - Verified PC2 successfully leased IP 192.168.20.12/24 via DHCP and confirmed gateway reachability (0.30 ms).
  - Validated full inter-segment routing across switches with PC2 (192.168.20.12 on Switch2) successfully pinging PC1 (192.168.10.10 on Switch1) at 0.43 ms.

01:40 PM to 02:30 PM

- Project Review & Technical Progress Meeting with Vishnu PA.

02:30 PM to 03:10 PM

- Lunch Break

03:10 PM to 04:00 PM

Palo Alto PAN-OS Management Architecture & Lab Virtualization Health Audit

- Analyzed console authentication behavior on hardware firewall unit (PA-HDF) vs. virtual instance (PA-VM), identifying "Login incorrect" causes related to PAN-OS mgmtsrvr daemon boot delays and lockout timers.
- Documented exact CLI and Web GUI procedures for configuring static management interface IPs for both virtual lab setups (172.17.0.50/16) and physical appliances (192.168.1.1/24 with laptop NIC configured at 192.168.1.10).
- Reviewed PAN-OS Maintenance Mode (maint) password recovery and factory reset procedures via console autoboot.
- Audited running Docker virtualization services (`docker stats`) and verified gns3-server memory footprint (~5.71 GiB) and backend QEMU hypervisor stability under multi-node load.

04:00 PM to 05:00 PM

Cisco Switch (SX350X-24F) Hardware Fan Diagnostic & Vendor Coordination

- Coordinated with Cisco vendor support team regarding hardware fan failure and environmental thermal alarms on the Cisco SX350X-24F managed switch.
- Facilitated remote technical troubleshooting by establishing a secure AnyDesk remote desktop session for the vendor engineer to perform real-time diagnostic checks.
- Bridged communication between the Cisco vendor engineer and Girish to align on troubleshooting findings, escalation procedures, and next steps.
- Extracted and compiled switch tech-support diagnostics, environmental sensor readings, and system event logs, sharing the diagnostic bundle directly with the vendor team for evaluation.
- Status: Remote diagnostics concluded; vendor confirmed switch hardware is end-of-life/out of warranty, requiring component-level resolution.

05:00 PM to 06:30 PM

Cisco SX350X-24F Component Sourcing, N+1 Redundancy & Production Thermal Safety Assessment

- Root-Cause Verification: Analyzed switch CLI outputs (`show system fans`, `show logging`), confirming physical failure on Fan 1/2 (`0 RPM`, Status: `Failure`) with alert `%Environment-A-FAN-STAT-CHNG: FAN# 2 status changed to not operational`, while Fans 1/1, 1/3, and 1/4 compensate at ~6,500–6,800 RPM.
- Component Engineering & Sourcing: Researched OEM replacement options and identified the exact factory part: Delta Electronics `AFB0412VHB` series (40x40x15mm, 12V DC, 9,500 RPM, dual ball bearing). Confirmed requirement for a 4-wire PWM model with integrated Frequency Generator / Tachometer (`AFB0412VHB-TP25` via DigiKey) to supply RPM feedback and prevent persistent firmware alarms.
- Cisco N+1 Redundancy Validation: Evaluated vendor guidance regarding running the switch in production with 3 fans below 75°C. Verified against official Cisco documentation confirming N+1 cooling redundancy (`Yellow status: A fan has failed, but the system is backed up by a redundant fan`).
- Thermal Health Audit: Polled all 6 internal temperature sensors via CLI (`show system sensors`, `show system`) and confirmed healthy operational thresholds:
  - PCB Sensors: 34°C – 37°C (Warning: 67°C / Critical: 75°C)
  - Packet Processor: 49°C (Warning: 100°C / Critical: 105°C)
  - CPU: 66°C (Warning: 105°C / Critical: 110°C)
  - PHY Ports: 31°C (Warning: 95°C / Critical: 100°C)
- Production Readiness Verdict: Confirmed overall unit thermal status is `OK` at `65°C`, validating that the switch is completely safe for production data center deployment while the replacement fan order is processed.

06:30 PM to 07:00 PM

Daily Documentation, Lab Command Reference Compilation & Work Handover

- Compiled and published the comprehensive `Palo Alto Lab Running Commands Reference Manual` PDF detailing all configuration scripts across Palo Alto PAN-OS, VyOS Router, and VPCS nodes.
- Synchronized daily task deliverables, updated engineering logs, and finalized work handover.
