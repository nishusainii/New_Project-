import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
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
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "Palo Alto Firewall (PAN-OS) — Engineering Study Notes")
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "Training Reference: 00:00:00 – 02:40:00")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 44, 8.5 * inch - 54, 44)
        
        self.drawString(54, 30, "Palo Alto Networks Engineering Reference | Prepared by Nishu Saini")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 30, page_str)
        self.restoreState()

def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Palette
    PRIMARY = colors.HexColor("#1A365D")     # Deep Navy
    SECONDARY = colors.HexColor("#DD6B20")   # PAN Orange
    DARK_TEXT = colors.HexColor("#2D3748")
    MUTED_TEXT = colors.HexColor("#4A5568")
    BG_LIGHT = colors.HexColor("#F7FAFC")
    BORDER_COLOR = colors.HexColor("#E2E8F0")
    ACCENT_BLUE = colors.HexColor("#2B6CB0")
    HIGHLIGHT_BG = colors.HexColor("#EDF2F7")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=PRIMARY,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=MUTED_TEXT,
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=DARK_TEXT,
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'Bullet_Custom',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=DARK_TEXT,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=2
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    table_body_style = ParagraphStyle(
        'TableBody',
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=DARK_TEXT
    )

    table_body_bold = ParagraphStyle(
        'TableBodyBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10.5,
        textColor=PRIMARY
    )

    story = []

    # Title Banner Block
    meta_table_data = [
        [
            Paragraph("<b>PALO ALTO FIREWALL (PAN-OS) — ENGINEERING STUDY NOTES</b>", title_style),
        ],
        [
            Paragraph("<b>Scope:</b> Video Training Modules (00:00:00 to 02:40:00) &nbsp;|&nbsp; <b>Level:</b> PCNSA / PCNSE Core Fundamentals &nbsp;|&nbsp; <b>Author:</b> Nishu Saini", subtitle_style)
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[504])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('LINEBEFORE', (0,0), (0,-1), 4, SECONDARY),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # 1. Why Next-Generation Firewalls
    story.append(Paragraph("1. Why Next-Generation Firewalls (NGFW)?", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    story.append(Paragraph("• <b>Traditional Firewalls (L3/L4 / Stateful Inspection):</b> Only check Source IP, Destination IP, Protocol, and Port Number. Modern applications easily bypass them by tunneling over standard ports (Port 80 HTTP / 443 HTTPS) or using dynamic port hopping (BitTorrent, Skype).", bullet_style))
    story.append(Paragraph("• <b>Palo Alto NGFW Approach:</b> Inspects traffic at <b>Layer 7 (Application Layer)</b>. Security policies are enforced based on <b>Application (App-ID) + User (User-ID) + Threat Content (Content-ID)</b>, NOT just port numbers.", bullet_style))
    story.append(Spacer(1, 6))

    # 2. Single-Pass Parallel Processing
    story.append(Paragraph("2. Core Architecture: Single-Pass Parallel Processing (SP3)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    story.append(Paragraph("• <b>Legacy UTM (Multi-Pass Architecture):</b> Packets pass sequentially through separate engines (Firewall → IPS → Antivirus → URL Filtering). Packets are buffered, decoded, and re-encrypted multiple times, causing severe latency and throughput drop.", bullet_style))
    story.append(Paragraph("• <b>Palo Alto SP3 (Single-Pass Architecture):</b> Packets are decoded and verified only once. <b>App-ID, User-ID, Content-ID, and Policy Lookup</b> are evaluated simultaneously in parallel at the hardware level, providing consistent throughput and predictable low latency.", bullet_style))
    story.append(Spacer(1, 6))

    # 3. Hardware Plane Separation
    story.append(Paragraph("3. Hardware Plane Separation (Control Plane vs. Data Plane)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    story.append(Paragraph("• <b>Control / Management Plane:</b> Has dedicated CPU & RAM for Web GUI, CLI, logging, reporting, APIs, and Panorama. Heavy reporting or admin logins <i>never</i> slow down packet forwarding.", bullet_style))
    story.append(Paragraph("• <b>Data Plane (Datapath):</b> Purpose-built network processors and ASICs handle hardware switching, routing, signature matching, and line-rate forwarding.", bullet_style))
    story.append(Spacer(1, 6))

    # 4. The 4 Core Pillars of PAN-OS
    story.append(Paragraph("4. The Four Core Pillars of PAN-OS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    
    pillars_data = [
        [Paragraph("Pillar", table_header_style), Paragraph("Key Function", table_header_style), Paragraph("Engineering Impact", table_header_style)],
        [Paragraph("<b>App-ID</b>", table_body_bold), Paragraph("Identifies application via Layer 7 payload signatures regardless of port or SSL.", table_body_style), Paragraph("Blocks unauthorized port-hopping apps hiding on port 80/443.", table_body_style)],
        [Paragraph("<b>User-ID</b>", table_body_bold), Paragraph("Maps IP addresses to Active Directory / LDAP usernames and groups.", table_body_style), Paragraph("Enables rules like 'Allow Dev-Team SSH' instead of dynamic IP subnets.", table_body_style)],
        [Paragraph("<b>Content-ID</b>", table_body_bold), Paragraph("Deep packet inspection for Antivirus, Anti-Spyware, Vulnerability Protection, File Blocking, and URL Filtering.", table_body_style), Paragraph("Blocks exploits, malware payloads, and C2 callbacks in a single stream.", table_body_style)],
        [Paragraph("<b>WildFire</b>", table_body_bold), Paragraph("Automated cloud sandbox for zero-day malware analysis.", table_body_style), Paragraph("Generates and distributes global threat signatures within minutes.", table_body_style)],
    ]
    p_table = Table(pillars_data, colWidths=[70, 234, 200])
    p_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(p_table)
    story.append(Spacer(1, 8))

    # 5. Initial Setup & Commit Engine
    story.append(Paragraph("5. Initial Setup & The Commit Engine", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    story.append(Paragraph("• <b>Default Access:</b> Dedicated <code>MGT</code> port with IP <code>192.168.1.1/24</code>, username/password: <code>admin</code> / <code>admin</code>.", bullet_style))
    story.append(Paragraph("• <b>Candidate Config vs. Running Config:</b> Changes in GUI/CLI are stored in a draft <i>Candidate Configuration</i>. You must execute <b>Commit</b> to compile and activate changes into the active <i>Running Configuration</i>. Uncommitted changes can be reverted instantly.", bullet_style))
    story.append(Spacer(1, 6))

    # 6. Security Zones & 5 Interface Modes
    story.append(Paragraph("6. Security Zones & 5 Interface Modes", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    story.append(Paragraph("• <b>Zone Rules:</b> <b>Intra-Zone</b> (within same zone, e.g. Trust $\\rightarrow$ Trust) is <b>ALLOWED</b> by default. <b>Inter-Zone</b> (between different zones, e.g. Trust $\\rightarrow$ Untrust) is <b>DENIED</b> by default.", bullet_style))

    modes_data = [
        [Paragraph("Interface Mode", table_header_style), Paragraph("How It Works", table_header_style), Paragraph("Primary Use Case", table_header_style)],
        [Paragraph("<b>Layer 3 (L3)</b>", table_body_bold), Paragraph("Routed mode with IP addresses, routing protocols (OSPF/BGP), and Virtual Routers.", table_body_style), Paragraph("Standard firewall gateway, NAT, and VPN termination.", table_body_style)],
        [Paragraph("<b>Virtual Wire (V-Wire)</b>", table_body_bold), Paragraph("Transparent inline mode. Pairs 2 ports with zero IP or MAC address changes.", table_body_style), Paragraph("Drop-in inspection into existing network without changing subnets.", table_body_style)],
        [Paragraph("<b>Layer 2 (L2)</b>", table_body_bold), Paragraph("Performs Layer 2 MAC switching and VLAN bridging between ports.", table_body_style), Paragraph("Internal network segmentation and switching.", table_body_style)],
        [Paragraph("<b>TAP Mode</b>", table_body_bold), Paragraph("Connects to switch SPAN/mirror port for passive packet capture and analysis.", table_body_style), Paragraph("Passive traffic monitoring and threat visibility without blocking.", table_body_style)],
        [Paragraph("<b>HA Mode</b>", table_body_bold), Paragraph("Dedicated ports for cluster sync (HA1 Control/Heartbeat, HA2 Session Data).", table_body_style), Paragraph("Active/Passive and Active/Active high availability clusters.", table_body_style)],
    ]
    m_table = Table(modes_data, colWidths=[90, 230, 184])
    m_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(m_table)
    story.append(Spacer(1, 8))

    # 7. Layer 3 Routing & Virtual Routers
    story.append(Paragraph("7. Layer 3 Routing, Virtual Routers (VR) & Sub-interfaces", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    story.append(Paragraph("• <b>Virtual Routers (VR):</b> Logical routing instances (e.g. <code>default</code>) that decouple routing tables from physical hardware.", bullet_style))
    story.append(Paragraph("• <b>802.1Q Sub-interfaces:</b> Allows a single physical port (e.g. <code>ethernet1/2</code>) to carry multiple VLANs (e.g. <code>ethernet1/2.10</code> for VLAN 10, <code>ethernet1/2.20</code> for VLAN 20) and route between them through security policies.", bullet_style))
    story.append(Paragraph("• <b>Static Routing:</b> Configured under <i>Network → Virtual Routers → Static Routes</i> (Destination: <code>0.0.0.0/0</code>, Interface: egress port, Next-Hop: gateway IP).", bullet_style))
    story.append(Spacer(1, 6))

    # 8. Security Policy Rules & Interface Profiles
    story.append(Paragraph("8. Security Policy Rules & Interface Management Profiles", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    story.append(Paragraph("• <b>Rule Processing:</b> <b>Top-to-Bottom, First-Match</b>. Once a packet matches all 6 criteria (Source Zone/IP, User, Dest Zone/IP, App-ID, Service/Port), processing terminates and the action (<code>Allow</code>/<code>Deny</code>) is enforced.", bullet_style))
    story.append(Paragraph("• <b>Logging Standard:</b> Always select <b>Log at Session End</b> to record complete byte counts, session duration, and NAT mappings without log flooding.", bullet_style))
    story.append(Paragraph("• <b>Interface Management Profile:</b> Firewall data interfaces <b>block ping/HTTPS to themselves by default</b>. To allow ping, create an Interface Management Profile with <code>Ping</code> enabled under <i>Network → Network Profiles → Interface Management</i> and attach it to the interface.", bullet_style))
    story.append(Spacer(1, 8))

    # Quick Revision Cheat Sheet Table
    story.append(Paragraph("9. Quick Revision Cheat Sheet Table", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceAfter=4, spaceBefore=1))
    
    cheat_data = [
        [Paragraph("Topic / Feature", table_header_style), Paragraph("Key Concept / Definition", table_header_style), Paragraph("Golden Exam / Lab Rule", table_header_style)],
        [Paragraph("<b>SP3</b>", table_body_bold), Paragraph("Single-pass parallel hardware scanning", table_body_style), Paragraph("Eliminates UTM multi-pass latency bottlenecks.", table_body_style)],
        [Paragraph("<b>Plane Separation</b>", table_body_bold), Paragraph("Control Plane (Mgmt) != Data Plane (Traffic)", table_body_style), Paragraph("Heavy reporting/GUI never degrades packet forwarding.", table_body_style)],
        [Paragraph("<b>Commit</b>", table_body_bold), Paragraph("Candidate Config -> Running Config", table_body_style), Paragraph("Changes only take effect after clicking Commit.", table_body_style)],
        [Paragraph("<b>Inter-Zone</b>", table_body_bold), Paragraph("Traffic between different security zones", table_body_style), Paragraph("DENIED by default (requires explicit rule).", table_body_style)],
        [Paragraph("<b>Intra-Zone</b>", table_body_bold), Paragraph("Traffic within the exact same security zone", table_body_style), Paragraph("ALLOWED by default.", table_body_style)],
        [Paragraph("<b>Mgmt Profile</b>", table_body_bold), Paragraph("Ping/SSH/HTTPS permissions on data interfaces", table_body_style), Paragraph("Must be assigned to ping firewall interface IP.", table_body_style)],
    ]
    c_table = Table(cheat_data, colWidths=[90, 200, 214])
    c_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PRIMARY),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(c_table)

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {filename}")

if __name__ == "__main__":
    out_dir = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall "
    target_pdf = os.path.join(out_dir, "Palo_Alto_NGFW_Training_Architecture_Guide.pdf")
    build_pdf(target_pdf)
    
    desktop_dir = "/home/nishusaini/Desktop/Innspark"
    desktop_pdf = os.path.join(desktop_dir, "Palo_Alto_NGFW_Training_Architecture_Guide.pdf")
    import shutil
    shutil.copyfile(target_pdf, desktop_pdf)
    print(f"Copied to: {desktop_pdf}")
