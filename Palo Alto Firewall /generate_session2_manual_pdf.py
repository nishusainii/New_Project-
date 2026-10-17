import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Palo Alto NGFW & Multi-Router Enterprise Lab — Advanced Operations Manual")
            self.setFont("Helvetica", 8)
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "Date: 01-Oct-2026 | Session: 11:45 – 13:30")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 44, 8.5 * inch - 54, 44)
        
        self.setFont("Helvetica", 8)
        self.drawString(54, 30, "Confidential — Network Operations & Engineering | Prepared by Nishu Saini")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 30, page_str)
        self.restoreState()

def build_pdf(output_pdf):
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#1A365D")   # Deep navy
    secondary_color = colors.HexColor("#2B6CB0") # Medium blue
    dark_neutral = colors.HexColor("#2D3748")    # Charcoal body text
    code_bg = colors.HexColor("#1A202C")         # Dark slate code background
    code_text = colors.HexColor("#E2E8F0")       # Light code font
    callout_bg = colors.HexColor("#EDF2F7")      # Light gray callout box
    border_color = colors.HexColor("#CBD5E0")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=secondary_color,
        spaceAfter=10
    )

    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=primary_color
    )

    meta_val = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=dark_neutral
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=primary_color,
        spaceBefore=11,
        spaceAfter=4,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11.5,
        textColor=dark_neutral,
        spaceAfter=5
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11.5,
        textColor=colors.HexColor("#2C5282")
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7,
        leading=9.5,
        textColor=code_text
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9.5,
        textColor=dark_neutral
    )

    table_cell_code = ParagraphStyle(
        'TableCellCode',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#2C5282")
    )

    def create_code_block(code_str):
        p = Preformatted(code_str.strip(), code_style)
        t = Table([[p]], colWidths=[7.0 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), code_bg),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#4A5568")),
        ]))
        return t

    def create_callout(text_str):
        p = Paragraph(f"<b>Key Takeaway / Operational Best Practice:</b> {text_str}", callout_style)
        t = Table([[p]], colWidths=[7.0 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), callout_bg),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
            ('LINELEFT', (0,0), (0,-1), 3.0, secondary_color)
        ]))
        return t

    story = []

    # Title & Header
    story.append(Paragraph("Palo Alto NGFW & Multi-Router Enterprise Lab", title_style))
    story.append(Paragraph("Comprehensive Technical Reference: Routing, Interfaces, Sessions, Policies, Backup & Lifecycle Operations", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=6))

    # Meta Table
    meta_data = [
        [
            Paragraph("Engineer / Author:", meta_label), Paragraph("Nishu Saini", meta_val),
            Paragraph("Lab Date:", meta_label), Paragraph("01-Oct-2026", meta_val)
        ],
        [
            Paragraph("Operational Session:", meta_label), Paragraph("11:45 AM – 01:30 PM IST", meta_val),
            Paragraph("Target Platform:", meta_label), Paragraph("Palo Alto PAN-OS 10.x & VyOS 1.5", meta_val)
        ],
        [
            Paragraph("Firewall Instance:", meta_label), Paragraph("PA-VM-1 (PA-VM / QEMU)", meta_val),
            Paragraph("Security Architecture:", meta_label), Paragraph("4-Zone Star Topology (Inside, DMZ1, Outside, DMZ2)", meta_val)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[1.3 * inch, 2.2 * inch, 1.3 * inch, 2.2 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # MODULE 1: ROUTING TABLES & FIB
    story.append(Paragraph("1. Routing Architecture: Route Table (RIB), Forwarding Information Base (FIB) & CLI Paging", h1_style))
    story.append(Paragraph(
        "Palo Alto distinguishes between the <b>Routing Information Base (RIB)</b> managed by the control plane routing engine, "
        "and the <b>Forwarding Information Base (FIB)</b> installed into the data plane hardware. Use these commands to audit route state:",
        body_style
    ))

    cmd_routing = """# 1. View all active routing table entries in the control plane (RIB):
admin@PA-1> show routing route

# 2. View routes filtered by a specific Virtual Router or Type:
admin@PA-1> show routing route virtual-router default
admin@PA-1> show routing route type connect
admin@PA-1> show routing route type static

# 3. View the active Data Plane Forwarding Information Base (FIB):
admin@PA-1> show routing fib

# 4. Disable pagination pausing (prevents '--more--' or 'lines 1-23' screen hangs):
admin@PA-1> set cli pager off

# 5. Route Summary (shows total route counts and memory footprint per protocol):
admin@PA-1> show routing summary

# 6. Hardware Forwarding Lookup Simulation (tests exact egress interface and next-hop):
admin@PA-1> test routing fib-lookup ip 192.168.2.1 virtual-router default"""
    story.append(create_code_block(cmd_routing))
    story.append(Spacer(1, 5))

    fib_data = [
        [Paragraph("Flag / Column", table_header), Paragraph("Technical Meaning", table_header), Paragraph("Operational Impact", table_header)],
        [Paragraph("u", table_cell_code), Paragraph("Up / Active", table_cell), Paragraph("Route is alive, installed, and actively forwarding packets in the data plane.")],
        [Paragraph("h", table_cell_code), Paragraph("Host Route (/32)", table_cell), Paragraph("Represents the firewall's own local interface IP address.")],
        [Paragraph("g", table_cell_code), Paragraph("Gateway Route", table_cell), Paragraph("Indicates a next-hop gateway address is required to forward traffic.")],
        [Paragraph("e", table_cell_code), Paragraph("ECMP Route", table_cell), Paragraph("Equal-Cost Multi-Path active across multiple peer uplinks.")],
        [Paragraph("nexthop: 0.0.0.0", table_cell_code), Paragraph("Directly Connected", table_cell), Paragraph("Target subnet resides directly on the physical interface without intermediate hops.")],
    ]
    fib_table = Table(fib_data, colWidths=[1.4 * inch, 1.8 * inch, 3.8 * inch])
    fib_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(fib_table)
    story.append(Spacer(1, 8))

    # MODULE 2: PRE-COMMIT AUDITING & CONFIGURATION VALIDATION
    story.append(Paragraph("2. Enterprise Configuration Discipline: Pre-Commit Diff Auditing & Job Tracking", h1_style))
    story.append(Paragraph(
        "In production enterprise environments, changes must be audited and syntax-checked before committing to prevent accidental outages:",
        body_style
    ))

    cmd_audit = """admin@PA-1> configure

# 1. Audit pending changes against the running configuration (shows + additions and - deletions):
admin@PA-1# show config diff

# 2. Perform a full syntax and dependency validation check prior to commit:
admin@PA-1# validate full

# 3. Commit changes with a descriptive audit message for compliance logging:
admin@PA-1# commit description "Configured 4 Layer-3 interfaces, zones, and ping management profile"

# 4. Track background commit, software download, or report jobs:
admin@PA-1> show jobs all
admin@PA-1> show jobs id 14"""
    story.append(create_code_block(cmd_audit))
    story.append(Spacer(1, 8))

    # MODULE 3: SYSTEM SETTINGS & MANAGEMENT CONFIGURATION
    story.append(Paragraph("3. Core System Identity, Hostname, DNS, NTP & Static Management IP Setup", h1_style))
    story.append(Paragraph(
        "To establish Out-of-Band (OOB) management on a freshly deployed or factory-reset firewall, configure identity, "
        "DNS nameservers, NTP, and static IP addressing using the strict PAN-OS multi-line hierarchy:",
        body_style
    ))
    cmd_sys = """admin@PA-VM> configure

# 1. System Hostname & Domain Name
set deviceconfig system hostname PA-NGFW-Lab
set deviceconfig system domain innspark.local

# 2. Timezone & System Clock Synchronization
set deviceconfig system timezone Asia/Kolkata
set deviceconfig system ntp-servers primary-ntp-server ntp-server-address time.google.com

# 3. Domain Name System (DNS) Resolvers
set deviceconfig system dns-setting servers primary 8.8.8.8 secondary 8.8.4.4

# 4. Out-of-Band (OOB) Static Management Interface Setup (Verified Working Commands)
admin@PA-VM# set deviceconfig system type static
admin@PA-VM# set deviceconfig system ip-address 172.17.0.50
admin@PA-VM# set deviceconfig system netmask 255.255.0.0
admin@PA-VM# set deviceconfig system default-gateway 172.17.0.1
admin@PA-VM# set deviceconfig system dns-setting servers primary 8.8.8.8
admin@PA-VM# commit

# 5. Management Plane Security Hardening (Disable Unencrypted Protocols)
set deviceconfig system service disable-telnet yes
set deviceconfig system service disable-http yes

exit"""
    story.append(create_code_block(cmd_sys))
    story.append(Spacer(1, 6))
    story.append(create_callout(
        "<b>Critical PAN-OS Syntax Rule:</b> In PAN-OS CLI, <code>set deviceconfig system type static</code> is a standalone command. "
        "Appending <code>ip-address</code> directly after <code>static</code> on the same line produces an <b>'Invalid syntax'</b> error. "
        "Always execute <code>set deviceconfig system type static</code>, followed by separate statements for <code>ip-address</code>, "
        "<code>netmask</code>, and <code>default-gateway</code>, then commit."
    ))
    story.append(Spacer(1, 8))

    # MODULE 4: DATA PLANE & ZONES
    story.append(Paragraph("4. Enterprise Data Plane: Layer 3 Interfaces, Virtual Router & Security Zones", h1_style))
    cmd_data = """admin@PA-1> configure
# ==============================================================================
# 1. CREATE INTERFACE MANAGEMENT PROFILE (ALLOW PING FOR DIAGNOSTICS)
# ==============================================================================
set network profiles interface-management-profile Allow-Ping ping yes

# ==============================================================================
# 2. CONFIGURE LAYER 3 DATA INTERFACES & ATTACH PROFILE
# ==============================================================================
# Ethernet1/1: Peer to Router-1 (INSIDE / Trust LAN)
set network interface ethernet ethernet1/1 layer3 ip 192.168.1.2/24
set network interface ethernet ethernet1/1 layer3 interface-management-profile Allow-Ping
set network interface ethernet ethernet1/1 comment "Uplink-Router1-INSIDE"

# Ethernet1/2: Peer to Router-2 (DMZ1 Segment)
set network interface ethernet ethernet1/2 layer3 ip 192.168.2.2/24
set network interface ethernet ethernet1/2 layer3 interface-management-profile Allow-Ping
set network interface ethernet ethernet1/2 comment "Uplink-Router2-DMZ1"

# Ethernet1/3: Peer to Router-3 (OUTSIDE / External)
set network interface ethernet ethernet1/3 layer3 ip 192.168.3.2/24
set network interface ethernet ethernet1/3 layer3 interface-management-profile Allow-Ping
set network interface ethernet ethernet1/3 comment "Uplink-Router3-OUTSIDE"

# Ethernet1/4: Peer to Router-4 (DMZ2 Segment)
set network interface ethernet ethernet1/4 layer3 ip 192.168.4.2/24
set network interface ethernet ethernet1/4 layer3 interface-management-profile Allow-Ping
set network interface ethernet ethernet1/4 comment "Uplink-Router4-DMZ2"

# ==============================================================================
# 3. BIND INTERFACES TO VIRTUAL ROUTER 'default'
# ==============================================================================
set network virtual-router default interface [ ethernet1/1 ethernet1/2 ethernet1/3 ethernet1/4 ]

# ==============================================================================
# 4. CREATE SECURITY ZONES & BIND INTERFACES
# ==============================================================================
set zone INSIDE network layer3 ethernet1/1
set zone DMZ1 network layer3 ethernet1/2
set zone OUTSIDE network layer3 ethernet1/3
set zone DMZ2 network layer3 ethernet1/4

commit
exit"""
    story.append(create_code_block(cmd_data))
    story.append(Spacer(1, 8))

    # MODULE 5: ARP & PING CONNECTIVITY
    story.append(Paragraph("5. Layer 2 ARP Cache Verification & End-to-End ICMP Diagnostics", h1_style))
    cmd_arp_ping = """# 1. Inspect the Global ARP Table:
admin@PA-1> show arp all

interface         ip              mac                status   ttl
----------------------------------------------------------------------
ethernet1/1       192.168.1.1     0c:e1:c3:5e:00:00  c        1142
ethernet1/2       192.168.2.1     0c:bc:d4:39:00:00  c        1185
ethernet1/3       192.168.3.1     0c:ab:92:1b:00:00  c        1190
ethernet1/4       192.168.4.1     0c:86:af:4e:00:00  c        1195

# 2. Execute Bidirectional Ping Tests from Palo Alto CLI (Syntax: count BEFORE host):
admin@PA-1> ping source 192.168.1.2 count 4 host 192.168.1.1  # INSIDE (Router 1) -> 0% loss
admin@PA-1> ping source 192.168.2.2 count 4 host 192.168.2.1  # DMZ1   (Router 2) -> 0% loss
admin@PA-1> ping source 192.168.3.2 count 4 host 192.168.3.1  # OUTSIDE(Router 3) -> 0% loss
admin@PA-1> ping source 192.168.4.2 count 4 host 192.168.4.1  # DMZ2   (Router 4) -> 0% loss

# 3. Complementary Ping Verification from VyOS Routers (e.g., Router 1):
vyos@vyos# run ping 192.168.1.2 count 4
4 packets transmitted, 4 received, 0% packet loss, time 3005ms (rtt ~3.1 ms)"""
    story.append(create_code_block(cmd_arp_ping))
    story.append(Spacer(1, 5))

    arp_data = [
        [Paragraph("ARP Status", table_header), Paragraph("Technical Condition", table_header), Paragraph("Troubleshooting Action", table_header)],
        [Paragraph("c (Complete)", table_cell_code), Paragraph("Successful Layer 2 resolution", table_cell), Paragraph("Hardware link, carrier, and IP addressing are 100% operational.")],
        [Paragraph("i (Incomplete)", table_cell_code), Paragraph("Broadcast sent; zero reply received", table_cell), Paragraph("Check for disconnected GNS3 virtual cables, carrier down, or IP subnet mismatch.")],
        [Paragraph("s (Static)", table_cell_code), Paragraph("Manually configured entry", table_cell), Paragraph("Permanent entry programmed into hardware; does not expire.")],
    ]
    arp_table = Table(arp_data, colWidths=[1.4 * inch, 2.2 * inch, 3.4 * inch])
    arp_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(arp_table)
    story.append(Spacer(1, 8))

    # MODULE 6: SESSION TABLE & SECURITY POLICY SIMULATION
    story.append(Paragraph("6. Stateful Flow Inspection: Session Table Auditing & Policy Simulation", h1_style))
    story.append(Paragraph(
        "Palo Alto is a stateful NGFW. Beyond pinging, engineers must inspect active sessions and verify policy compliance:",
        body_style
    ))

    cmd_sessions = """# 1. View all active stateful sessions passing through the firewall:
admin@PA-1> show session all

# 2. Filter live sessions by specific source IP, destination IP, or protocol:
admin@PA-1> show session all filter source 192.168.1.1
admin@PA-1> show session all filter destination 192.168.2.1

# 3. Inspect a specific session ID in deep detail (shows NAT, bytes, packets, and decrypt state):
admin@PA-1> show session id 45892

# 4. Simulate a Security Policy match without generating live packet traffic:
admin@PA-1> test security-policy-match from INSIDE to DMZ1 source 192.168.1.1 destination 192.168.2.1 protocol 1
# (Outputs the exact rule name matched, action: allow/deny, and applied security profiles)"""
    story.append(create_code_block(cmd_sessions))
    story.append(Spacer(1, 8))

    # MODULE 7: HYPERVISOR TROUBLESHOOTING
    story.append(Paragraph("7. Virtualization Engineering: Resolving QEMU Carrier Loss & Stale uBridge Tunnels", h1_style))
    cmd_ubridge = """# 1. Diagnosing Link State on VyOS Linux Guest:
vyos@vyos:~$ ip link show eth0
2: eth0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 ... state DOWN

# 2. Forcing Virtual Link Up via QEMU Monitor (e.g., port 42799):
(qemu) set_link virtio-net-pci.0 on

# 3. Purging Stale GNS3 uBridge Tunnel Endpoints via Control Socket (port 37833):
bridge delete QEMU-8eb8f3fd-374f-4fda-8e2f-3f2872764f78-1

# 4. Re-establishing Virtual Link via GNS3 REST API:
curl -X POST http://localhost:3080/v2/projects/{project_id}/links \\
  -H "Content-Type: application/json" \\
  -d '{"nodes": [{"node_id": "PA_ID", "adapter_number": 1, "port_number": 0},
                 {"node_id": "ROUTER_ID", "adapter_number": 0, "port_number": 0}]}'"""
    story.append(create_code_block(cmd_ubridge))
    story.append(Spacer(1, 8))

    # MODULE 8: 10 CORE OPERATIONAL PROCEDURES (CLI & WEB GUI)
    story.append(Paragraph("8. Initial Configuration: 10 Core Procedures (CLI Commands & Web GUI Step-by-Step Guide)", h1_style))
    story.append(Paragraph(
        "A complete operational curriculum detailing both the precise PAN-OS CLI syntax and the exact Web GUI navigation paths "
        "for staging, accessing, securing, backing up, restoring, and managing the firewall lifecycle.",
        body_style
    ))

    def create_gui_box(gui_text):
        p = Paragraph(f"<b>Web GUI Navigation Steps:</b><br/>{gui_text}", callout_style)
        t = Table([[p]], colWidths=[7.0 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FFF4")), # Light green tint
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#9AE6B4")),
            ('LINELEFT', (0,0), (0,-1), 3.0, colors.HexColor("#38A169")) # Green border
        ]))
        return t

    ten_topics = [
        (
            "Topic 1: Initial Configuration: Basics — Lab Setup",
            """# 1. Physical / Logical Topology Allocations:
# - PA ethernet1/1: 192.168.1.2/24 (Zone: INSIDE)  <---> Router 1 eth0 (192.168.1.1/24)
# - PA ethernet1/2: 192.168.2.2/24 (Zone: DMZ1)    <---> Router 2 eth0 (192.168.2.1/24)
# - PA ethernet1/3: 192.168.3.2/24 (Zone: OUTSIDE) <---> Router 3 eth0 (192.168.3.1/24)
# - PA ethernet1/4: 192.168.4.2/24 (Zone: DMZ2)    <---> Router 4 eth0 (192.168.4.1/24)
# - PA management:  172.17.0.50/16 (OOB Mgmt)     <---> NAT1 Node (docker0 172.17.0.1/16)

# 2. Initial Firewall Identity & Lab Baseline CLI Commands:
admin@PA-VM> configure
admin@PA-VM# set deviceconfig system hostname PA-VM-LAB
admin@PA-VM# set deviceconfig system domain innspark.local
admin@PA-VM# set deviceconfig system timezone Asia/Kolkata
admin@PA-VM# commit""",
            "<b>GNS3 Canvas & Web GUI Setup Steps:</b><br/>"
            "1. <b>Topology Placement:</b> Drag PA-VM-1, 4 VyOS Enterprise Routers, and 1 NAT node onto the GNS3 canvas.<br/>"
            "2. <b>Cabling:</b> Interconnect PA-VM ethernet1/0 to Router-1 eth0, ethernet1/1 to Router-2 eth0, ethernet1/2 to Router-3 eth0, ethernet1/3 to Router-4 eth0, and management to NAT1 node.<br/>"
            "3. <b>Power On:</b> Start all nodes and verify green status LEDs.<br/>"
            "4. <b>Web GUI Baseline Setup:</b> Navigate to <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Management</b> &rarr; Click <b>Gear (⚙️)</b> on <i>General Settings</i> &rarr; Set Hostname: <code>PA-VM-LAB</code>, Domain: <code>innspark.local</code> &rarr; Click <b>OK</b> &rarr; <b>Commit</b>."
        ),
        (
            "Topic 2: Initial Configuration: Basics — How to Access Palo Alto Firewall",
            """# 1. Console Access (Serial / GNS3 Telnet Port 5008):
$ telnet 127.0.0.1 5008
PA-VM login: admin
Password: admin (or Nishu@123@)

# 2. Secure Shell (SSH) Access over Management IP:
$ ssh admin@172.17.0.50 (or ssh admin@192.168.1.1)

# 3. Mandatory First-Login Password Change Prompt:
Enter old password: admin
Enter new password: <SecurePassword123>
Confirm password:   <SecurePassword123>""",
            "<b>Web GUI Access Steps:</b><br/>"
            "1. Connect PC Ethernet adapter to the MGT port and configure static IP <code>172.17.0.10/16</code> (or <code>192.168.1.10/24</code>).<br/>"
            "2. Open Chrome or Firefox and navigate to <b><code>https://172.17.0.50</code></b> (or <code>https://192.168.1.1</code>).<br/>"
            "3. Bypass SSL certificate warning by clicking <b>Advanced</b> &rarr; <b>Proceed to 172.17.0.50 (unsafe)</b>.<br/>"
            "4. Enter administrator credentials to log into the Palo Alto Dashboard."
        ),
        (
            "Topic 3: Initial Configuration: Basics — How to Enable Telnet",
            """# A. Enable Telnet on Management (MGT) Port:
admin@PA-1> configure
admin@PA-1# delete deviceconfig system service disable-telnet
admin@PA-1# commit

# B. Enable Telnet on Data Ports (via Interface Management Profile):
admin@PA-1# set network profiles interface-management-profile Allow-Telnet telnet yes
admin@PA-1# set network interface ethernet ethernet1/1 layer3 interface-management-profile Allow-Telnet
admin@PA-1# commit""",
            "<b>Web GUI Steps:</b><br/>"
            "<b>On MGT Port:</b> Go to <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Management</b> &rarr; Click <b>Gear (⚙️)</b> on <i>Management Interface Settings</i> &rarr; Check <b>Telnet</b> &rarr; Click <b>OK</b> &rarr; <b>Commit</b>.<br/>"
            "<b>On Data Ports:</b> Go to <b>Network</b> &rarr; <b>Network Profiles</b> &rarr; <b>Interface Mgmt</b> &rarr; Click <b>Add</b> &rarr; Name: <code>Allow-Telnet</code> &rarr; Check <b>Telnet</b> &rarr; Click <b>OK</b>. Then go to <b>Network</b> &rarr; <b>Interfaces</b> &rarr; Click target port &rarr; <b>Advanced</b> &rarr; Select Management Profile: <code>Allow-Telnet</code> &rarr; <b>Commit</b>."
        ),
        (
            "Topic 4: Initial Configuration: Basics — How to Enable SSH",
            """# A. Enable SSH on Management (MGT) Port (Enabled by default):
admin@PA-1> configure
admin@PA-1# delete deviceconfig system service disable-ssh
admin@PA-1# commit

# B. Enable SSH on Data Ports (via Interface Management Profile):
admin@PA-1# set network profiles interface-management-profile Allow-SSH ssh yes
admin@PA-1# set network interface ethernet ethernet1/1 layer3 interface-management-profile Allow-SSH
admin@PA-1# commit""",
            "<b>Web GUI Steps:</b><br/>"
            "<b>On MGT Port:</b> Go to <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Management</b> &rarr; Click <b>Gear (⚙️)</b> on <i>Management Interface Settings</i> &rarr; Verify <b>SSH</b> checkbox is enabled &rarr; Click <b>OK</b> &rarr; <b>Commit</b>.<br/>"
            "<b>On Data Ports:</b> Go to <b>Network</b> &rarr; <b>Network Profiles</b> &rarr; <b>Interface Mgmt</b> &rarr; Click <b>Add</b> &rarr; Check <b>SSH</b> &rarr; Bind to interface under <b>Network</b> &rarr; <b>Interfaces</b> &rarr; <b>Commit</b>."
        ),
        (
            "Topic 5: Initial Configuration: Basics — How to Enable HTTP",
            """# A. Enable Plaintext HTTP on Management (MGT) Port (Disabled by default for security):
admin@PA-1> configure
admin@PA-1# delete deviceconfig system service disable-http
admin@PA-1# commit

# B. Enable HTTP on Data Ports (via Interface Management Profile):
admin@PA-1# set network profiles interface-management-profile Allow-HTTP http yes
admin@PA-1# set network interface ethernet ethernet1/1 layer3 interface-management-profile Allow-HTTP
admin@PA-1# commit""",
            "<b>Web GUI Steps:</b><br/>"
            "<b>On MGT Port:</b> Go to <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Management</b> &rarr; Click <b>Gear (⚙️)</b> on <i>Management Interface Settings</i> &rarr; Check <b>HTTP</b> checkbox &rarr; Click <b>OK</b> &rarr; <b>Commit</b>.<br/>"
            "<b>On Data Ports:</b> Go to <b>Network</b> &rarr; <b>Network Profiles</b> &rarr; <b>Interface Mgmt</b> &rarr; Click <b>Add</b> &rarr; Check <b>HTTP</b> &rarr; Attach profile to interface &rarr; <b>Commit</b>."
        ),
        (
            "Topic 6: Initial Configuration: Basics — How to Enable HTTPS",
            """# A. Enable Secure HTTPS on Management (MGT) Port (Enabled by default):
admin@PA-1> configure
admin@PA-1# delete deviceconfig system service disable-https
admin@PA-1# commit

# B. Enable HTTPS Web GUI on Data Ports:
admin@PA-1# set network profiles interface-management-profile Allow-HTTPS https yes
admin@PA-1# set network interface ethernet ethernet1/1 layer3 interface-management-profile Allow-HTTPS
admin@PA-1# commit""",
            "<b>Web GUI Steps:</b><br/>"
            "<b>On MGT Port:</b> Go to <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Management</b> &rarr; Click <b>Gear (⚙️)</b> on <i>Management Interface Settings</i> &rarr; Ensure <b>HTTPS</b> is checked &rarr; Click <b>OK</b> &rarr; <b>Commit</b>.<br/>"
            "<b>On Data Ports:</b> Go to <b>Network</b> &rarr; <b>Network Profiles</b> &rarr; <b>Interface Mgmt</b> &rarr; Check <b>HTTPS</b> &rarr; Apply profile to interface &rarr; <b>Commit</b>."
        ),
        (
            "Topic 7: Initial Configuration: Basics — How to Verify Connectivity",
            """# 1. Physical & Logical Interface Verification:
admin@PA-1> show interface all
admin@PA-1> show interface ethernet1/1

# 2. Layer 2 ARP Resolution Table:
admin@PA-1> show arp all

# 3. Layer 3 Routing Table & FIB Audit:
admin@PA-1> show routing route
admin@PA-1> show routing fib

# 4. Bidirectional Ping Tests:
admin@PA-1> ping source 192.168.1.2 count 4 host 192.168.1.1

# 5. Route Simulation Lookup:
admin@PA-1> test routing fib-lookup ip 192.168.2.1 virtual-router default""",
            "<b>Web GUI Steps:</b><br/>"
            "1. <b>Interface State:</b> Go to <b>Network</b> &rarr; <b>Interfaces</b> &rarr; Verify green link LEDs, IP addresses, and Zones.<br/>"
            "2. <b>ARP Table:</b> Go to <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; Click <code>default</code> &rarr; Click <b>More Runtime Stats</b> &rarr; Select <b>ARP</b> tab.<br/>"
            "3. <b>Routing Table:</b> Go to <b>Network</b> &rarr; <b>Virtual Routers</b> &rarr; Click <code>default</code> &rarr; Click <b>More Runtime Stats</b> &rarr; Select <b>Routing Table</b> tab.<br/>"
            "4. <b>Traffic Monitoring:</b> Go to <b>Monitor</b> &rarr; <b>Logs</b> &rarr; <b>Traffic</b> to observe live sessions and flow state."
        ),
        (
            "Topic 8: Initial Configuration: Basics — How to Take Backup",
            """# Method A: Save Named Snapshot Locally on Flash:
admin@PA-1> configure
admin@PA-1# save config to Backup_Lab_20261001.xml
admin@PA-1# exit

# Method B: Export Configuration to Remote SCP Server:
admin@PA-1> scp export configuration from running-config.xml to user@192.168.1.100:/backups/

# Method C: Export Configuration to Remote TFTP Server:
admin@PA-1> tftp export configuration from running-config.xml to 192.168.1.100""",
            "<b>Web GUI Steps:</b><br/>"
            "1. Navigate to <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Operations</b>.<br/>"
            "2. Under <i>Configuration Management</i>, click <b>Save named configuration snapshot</b> &rarr; Enter name <code>Backup_20261001.xml</code> &rarr; Click <b>OK</b>.<br/>"
            "3. Under <i>Export</i>, click <b>Export named configuration snapshot</b> &rarr; Select <code>running-config.xml</code> (or your named snapshot) &rarr; Click <b>OK</b> &rarr; Download `.xml` file to your PC."
        ),
        (
            "Topic 9: Initial Configuration: Basics — How to Reset With Factory Default",
            """# Method A: Soft Reset via Running CLI:
admin@PA-1> request system private-data-reset
# System prompts: 'Do you want to continue? (y or n)'. Press 'y'.
# Firewall formats /dev/vda6, purges all policies/IPs, and reboots to default 192.168.1.1.

# Method B: Automated Boot to Maintenance Mode:
admin@PA-1> debug system maintenance-mode on
admin@PA-1> request restart system

# Method C: Hard Reset via Console Maintenance Mode:
# Connect serial console (9600-8-N-1) -> Reboot -> Type 'maint' at autoboot prompt -> Select 'Factory Default' -> Reboot.""",
            "<b>Web GUI Steps:</b><br/>"
            "1. Navigate to <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Operations</b>.<br/>"
            "2. Under <i>Device Operations</i>, click <b>Revert to default factory settings</b>.<br/>"
            "3. Click <b>Yes</b> to confirm the warning prompt.<br/>"
            "4. The firewall will format user partitions, wipe all certificates/rules, and reboot to factory IP <code>192.168.1.1</code>."
        ),
        (
            "Topic 10: Initial Configuration: Basics — How to Restore Config",
            """# Method A: Load from Locally Saved Snapshot (CLI):
admin@PA-1> configure
admin@PA-1# load config from Backup_Lab_20261001.xml
admin@PA-1# commit
admin@PA-1# exit

# Method B: Merge Partial Configuration:
admin@PA-1# load config partial mode merge from Backup_Lab_20261001.xml from-xpath ...""",
            "<b>Web GUI Steps:</b><br/>"
            "1. Navigate to <b>Device</b> &rarr; <b>Setup</b> &rarr; <b>Operations</b>.<br/>"
            "2. Under <i>Configuration Management</i>, click <b>Import named configuration snapshot</b> &rarr; Click <b>Browse</b> &rarr; Select your backup `.xml` file &rarr; Click <b>OK</b>.<br/>"
            "3. Click <b>Load named configuration snapshot</b> &rarr; Select the imported `.xml` file from dropdown &rarr; Click <b>OK</b>.<br/>"
            "4. Click <b>Commit</b> at the top-right to apply and activate the restored configuration."
        ),
    ]

    for title, code_snippet, gui_instructions in ten_topics:
        story.append(Paragraph(title, h2_style))
        story.append(create_code_block(code_snippet))
        story.append(Spacer(1, 2))
        story.append(create_gui_box(gui_instructions))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 8))

    # MODULE 9: MAINTENANCE MODE & FACTORY RESET INTERNALS
    story.append(Paragraph("9. Maintenance Mode Architecture & Factory Reset Internals (The 'tune2fs' Phase)", h1_style))
    cmd_maint = """# 1. Inspecting Remote Maintenance Boot Flag:
admin@PA-1> debug system maintenance-mode show
Maintenance-mode boot is disabled

# 2. Instructing Firewall to Boot Directly into Maintenance Mode on Next Reboot:
admin@PA-1> debug system maintenance-mode on
Maintenance-mode boot is enabled for next reboot

# 3. Triggering System Reboot:
admin@PA-1> request restart system

# 4. Checking Management Server Daemon Status (Confirms Readiness for Login):
admin@PA-1> show management-server status
# (Outputs: running - confirms mgmtsrvr is ready, eliminating 'Login incorrect')

# 5. Monitoring Disk Space Across Partitions:
admin@PA-1> show system disk-space"""
    story.append(create_code_block(cmd_maint))
    story.append(Spacer(1, 6))

    story.append(create_callout(
        "<b>Why PA-VM Appears Frozen on 'tune2fs -c /dev/vda6' During Factory Reset:</b><br/>"
        "Partition <code>/dev/vda6</code> stores all firewall logs, session state databases, and reporting structures. "
        "During a factory reset, the kernel formats and rebuilds this multi-gigabyte volume from scratch. "
        "In virtualized environments (QEMU), this takes between <b>5 to 10 minutes</b> with zero console output. "
        "<b>Never power off or reset the VM during this stage</b>, as interrupting it corrupts the virtual disk filesystem. "
        "Once completed, the firewall boots normally and presents the <code>PA-VM login:</code> prompt."
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {output_pdf}")

if __name__ == '__main__':
    target_path = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo_Alto_Session2_Commands_and_Operations_Manual.pdf"
    build_pdf(target_path)
