import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable, Preformatted,
    Image as RLImage
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
            self.drawString(44, 11 * inch - 36, "Enterprise Firewall Architectural Comparison Matrix — Palo Alto vs CheckPoint vs Fortinet vs Cisco FTD vs Cisco ASA")
            self.setFont("Helvetica", 8)
            self.drawRightString(8.5 * inch - 44, 11 * inch - 36, "Visual Benchmark & Audit | Oct 2026")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(44, 11 * inch - 42, 8.5 * inch - 44, 11 * inch - 42)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(44, 40, 8.5 * inch - 44, 40)
        
        self.setFont("Helvetica", 8)
        self.drawString(44, 28, "Confidential — Network Architecture & Security Strategy | Prepared by Nishu Saini")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 44, 28, page_str)
        self.restoreState()

def build_pdf(output_pdf):
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=letter,
        leftMargin=44,
        rightMargin=44,
        topMargin=48,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#1A365D")   # Deep navy
    secondary_color = colors.HexColor("#2B6CB0") # Medium blue
    dark_neutral = colors.HexColor("#2D3748")    # Charcoal body text
    border_color = colors.HexColor("#CBD5E0")
    callout_bg = colors.HexColor("#EDF2F7")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=primary_color,
        spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=secondary_color,
        spaceAfter=6
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13.5,
        textColor=primary_color,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.8,
        leading=11.5,
        textColor=secondary_color,
        spaceBefore=5,
        spaceAfter=2,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=dark_neutral,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.5,
        textColor=dark_neutral
    )

    th_style = ParagraphStyle(
        'TH',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.white,
        alignment=1 # Center
    )

    th_feature = ParagraphStyle(
        'THF',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.white,
        alignment=0 # Left
    )

    table_header = th_feature

    td_feature = ParagraphStyle(
        'TDF',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.8,
        textColor=dark_neutral
    )

    td_yes = ParagraphStyle(
        'TDYes',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor("#22543D"),
        alignment=1
    )

    td_no = ParagraphStyle(
        'TDNo',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor("#742A2A"),
        alignment=1
    )

    td_na = ParagraphStyle(
        'TDNa',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor("#718096"),
        alignment=1
    )

    td_named = ParagraphStyle(
        'TDNamed',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.2,
        leading=7.8,
        textColor=colors.HexColor("#1A365D"),
        alignment=1
    )

    def val_p(val):
        v = val.strip()
        if v == "YES":
            return Paragraph("YES", td_yes)
        elif v == "NO":
            return Paragraph("NO", td_no)
        elif v == "NA":
            return Paragraph("NA", td_na)
        elif v.startswith("YES"):
            return Paragraph(f"<b>{v}</b>", td_named)
        else:
            return Paragraph(f"<b>{v}</b>", td_named)

    def create_callout(text, title="KEY ARCHITECTURAL TAKEAWAY", border_c=secondary_color, bg_c=callout_bg):
        content = [
            Paragraph(f"<b>{title}</b>", ParagraphStyle('CTitle', parent=callout_style, fontName='Helvetica-Bold', textColor=border_c)),
            Spacer(1, 2),
            Paragraph(text, callout_style)
        ]
        t = Table([[content]], colWidths=[7.28 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_c),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('BOX', (0,0), (-1,-1), 0.5, border_c),
            ('LINELEFT', (0,0), (0,-1), 3.0, border_c)
        ]))
        return t

    story = []

    # TITLE & HEADER
    story.append(Paragraph("Enterprise Next-Generation Firewall Comparison Matrix", title_style))
    story.append(Paragraph(
        "Comprehensive 46-Point Architectural Feature Benchmark with Hardware Profiles: Palo Alto vs. CheckPoint vs. Fortinet vs. Cisco FTD vs. Cisco ASA",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=6, spaceBefore=0))

    # SECTION 1: HARDWARE GALLERY & ARCHITECTURE OVERVIEW
    story.append(Paragraph("1. Hardware Appliance Gallery &amp; Platform Architecture Overview", h1_style))
    story.append(Paragraph(
        "This visual benchmark compares the five leading enterprise security appliances currently deployed in mission-critical networks:",
        body_style
    ))

    # PLATFORM HIGHLIGHTS WITH ACTUAL HARDWARE IMAGES
    platform_data = [
        [
            Paragraph("Hardware Appliance", table_header),
            Paragraph("Platform Name", table_header),
            Paragraph("Core Architecture", table_header),
            Paragraph("Primary Differentiator &amp; Strategic Role", table_header)
        ],
        [
            RLImage('assets/fw_palo_alto.png', width=1.15 * inch, height=0.55 * inch),
            Paragraph("<b>Palo Alto Networks</b><br/>PA-Series NGFW", td_feature),
            Paragraph("PAN-OS<br/>(Single-Pass SP3 Architecture)", body_style),
            Paragraph("Native Layer 7 classification (App-ID, User-ID, Content-ID) processed in a single hardware pass. Gold standard for Zero-Trust.", body_style)
        ],
        [
            RLImage('assets/fw_checkpoint.png', width=1.15 * inch, height=0.55 * inch),
            Paragraph("<b>CheckPoint</b><br/>Quantum Security Gateway", td_feature),
            Paragraph("Gaia OS<br/>(Software Blade Modular Engine)", body_style),
            Paragraph("Pioneer of stateful inspection. Highly modular software blades (Threat Emulation, SandBlast, Identity Awareness) with unified multi-domain SMS.", body_style)
        ],
        [
            RLImage('assets/fw_fortinet.png', width=1.15 * inch, height=0.55 * inch),
            Paragraph("<b>Fortinet</b><br/>FortiGate Enterprise NGFW", td_feature),
            Paragraph("FortiOS<br/>(Custom ASIC Acceleration: NP/CP)", body_style),
            Paragraph("Custom hardware ASICs delivering industry-leading SSL inspection throughput, wire-speed latency, and built-in Secure SD-WAN.", body_style)
        ],
        [
            RLImage('assets/fw_cisco_ftd.png', width=1.2 * inch, height=0.54 * inch),
            Paragraph("<b>Cisco FTD</b><br/>Firepower Threat Defense", td_feature),
            Paragraph("FXOS / Snort 3<br/>(Dual Unified Engine)", body_style),
            Paragraph("Combines Cisco ASA underlying networking with Snort 3 next-gen IPS and Security Intelligence, orchestrated centrally via FMC.", body_style)
        ],
        [
            RLImage('assets/fw_cisco_asa.png', width=1.2 * inch, height=0.58 * inch),
            Paragraph("<b>Cisco ASA</b><br/>Adaptive Security Appliance", td_feature),
            Paragraph("Cisco ASA OS<br/>(Traditional Stateful Packet Filter)", body_style),
            Paragraph("Legacy Layer 3/4 stateful firewall. Lacks native L7 App-ID, sandboxing, SSL decryption, or user identity without add-on modules.", body_style)
        ],
    ]
    p_table = Table(platform_data, colWidths=[1.3 * inch, 1.4 * inch, 1.8 * inch, 2.78 * inch])
    p_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(p_table)
    story.append(Spacer(1, 7))

    # SECTION 2: THE 46-POINT FEATURE COMPARISON MATRIX (ORGANIZED BY DOMAIN)
    story.append(Paragraph("2. Detailed 46-Feature Architectural Matrix (Transcribed &amp; Audited)", h1_style))
    story.append(Paragraph(
        "Below is the comprehensive 46-row feature audit transcribed directly from the engineering comparison matrix, featuring appliance visual headers:",
        body_style
    ))

    # TABLE BUILDER WITH HARDWARE IMAGES IN HEADER
    def build_matrix_table_with_images(rows):
        header_row = [
            Paragraph("Feature / Capability", th_feature),
            [RLImage('assets/fw_palo_alto.png', width=0.82 * inch, height=0.42 * inch), Spacer(1, 1), Paragraph("Palo Alto<br/>NGFW", th_style)],
            [RLImage('assets/fw_checkpoint.png', width=0.82 * inch, height=0.42 * inch), Spacer(1, 1), Paragraph("CheckPoint<br/>NGFW", th_style)],
            [RLImage('assets/fw_fortinet.png', width=0.88 * inch, height=0.42 * inch), Spacer(1, 1), Paragraph("Fortinet<br/>NGFW", th_style)],
            [RLImage('assets/fw_cisco_ftd.png', width=0.92 * inch, height=0.42 * inch), Spacer(1, 1), Paragraph("Cisco FTD<br/>NGFW", th_style)],
            [RLImage('assets/fw_cisco_asa.png', width=0.92 * inch, height=0.44 * inch), Spacer(1, 1), Paragraph("Cisco ASA<br/>Legacy", th_style)]
        ]
        table_content = [header_row]
        for f_name, pa, cp, ft, ftd, asa in rows:
            table_content.append([
                Paragraph(f_name, td_feature),
                val_p(pa),
                val_p(cp),
                val_p(ft),
                val_p(ftd),
                val_p(asa)
            ])
        t = Table(table_content, colWidths=[1.88 * inch, 1.08 * inch, 1.08 * inch, 1.08 * inch, 1.08 * inch, 1.08 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('BOX', (0,0), (-1,-1), 0.5, border_color),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 2.0),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.0),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('VALIGN', (0,0), (-1,0), 'MIDDLE'),
        ]))
        return t

    def build_matrix_table_compact(rows):
        header_row = [
            Paragraph("Feature / Capability", th_feature),
            Paragraph("Palo Alto<br/>NGFW", th_style),
            Paragraph("CheckPoint<br/>NGFW", th_style),
            Paragraph("Fortinet<br/>NGFW", th_style),
            Paragraph("Cisco FTD<br/>NGFW", th_style),
            Paragraph("Cisco ASA<br/>Legacy", th_style)
        ]
        table_content = [header_row]
        for f_name, pa, cp, ft, ftd, asa in rows:
            table_content.append([
                Paragraph(f_name, td_feature),
                val_p(pa),
                val_p(cp),
                val_p(ft),
                val_p(ftd),
                val_p(asa)
            ])
        t = Table(table_content, colWidths=[1.88 * inch, 1.08 * inch, 1.08 * inch, 1.08 * inch, 1.08 * inch, 1.08 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), primary_color),
            ('BOX', (0,0), (-1,-1), 0.5, border_color),
            ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
            ('TOPPADDING', (0,0), (-1,-1), 1.8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.8),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
        ]))
        return t

    # DOMAIN 1: CORE PLATFORM & MANAGEMENT (WITH IMAGES IN HEADER)
    story.append(Paragraph("Domain A: Core Platform Classification &amp; Management Interface", h2_style))
    domain_a = [
        ("NGFW (Next-Gen Firewall)", "YES", "YES", "YES", "YES", "NO"),
        ("Stateful Firewall", "YES", "YES", "YES", "YES", "YES"),
        ("CLI Management", "YES", "YES", "YES", "YES*", "YES"),
        ("GUI Management", "YES", "YES", "YES", "YES", "YES (ASDM)"),
    ]
    story.append(build_matrix_table_with_images(domain_a))
    story.append(Spacer(1, 5))

    # DOMAIN 2: LAYER 3 ROUTING PROTOCOLS (IPv4 & IPv6)
    story.append(Paragraph("Domain B: Dynamic &amp; Static Routing Protocols (IPv4 &amp; IPv6)", h2_style))
    domain_b = [
        ("IPv4 Static Routing", "YES", "YES", "YES", "YES", "YES"),
        ("IPv4 Default Routing", "YES", "YES", "YES", "YES", "YES"),
        ("RIP (Routing Info Protocol)", "YES", "YES", "YES", "NA", "YES"),
        ("OSPF (Open Shortest Path First)", "YES", "YES", "YES", "YES", "YES"),
        ("BGP (Border Gateway Protocol)", "YES", "YES", "YES", "YES", "YES"),
        ("IS-IS (Intermediate System)", "NA", "YES", "YES", "NA", "YES"),
        ("EIGRP (Cisco Proprietary)", "NA", "NA", "NA", "YES", "YES"),
        ("IPv6 Static Routing", "YES", "YES", "YES", "YES", "YES"),
        ("IPv6 Default Routing", "YES", "YES", "YES", "YES", "YES"),
        ("RIPng (IPv6 RIP)", "NA", "YES", "YES", "NA", "NA"),
        ("OSPFv3 (IPv6 OSPF)", "YES", "YES", "YES", "YES", "YES"),
        ("MP-BGP (Multiprotocol BGP)", "YES", "YES", "YES", "YES*", "YES"),
        ("IS-ISv6", "NA", "NA", "YES", "NA", "YES"),
        ("EIGRPv6", "NA", "NA", "NA", "NA", "NA"),
    ]
    story.append(build_matrix_table_compact(domain_b))
    story.append(Spacer(1, 5))

    # DOMAIN 3: NETWORK ADDRESS TRANSLATION (NAT) ARCHITECTURES
    story.append(Paragraph("Domain C: Network Address Translation (NAT) &amp; PAT Flavors", h2_style))
    domain_c = [
        ("Static NAT", "YES", "YES", "YES", "YES", "YES"),
        ("Dynamic NAT", "YES", "NA", "NA", "YES", "YES"),
        ("PAT / Overload / Hide NAT", "YES", "YES", "YES", "YES", "YES"),
        ("Static PAT (Port Forwarding)", "YES", "NA", "YES", "YES", "YES"),
        ("Identity NAT (NAT Exemption)", "NA", "NA", "NA", "YES", "YES"),
        ("U-NAT (Hairpin / U-Turn NAT)", "YES", "NA", "NA", "NA", "NA"),
        ("Twice NAT (Source + Dest NAT)", "NA", "NA", "NA", "YES", "YES"),
    ]
    story.append(build_matrix_table_compact(domain_c))
    story.append(Spacer(1, 5))

    # DOMAIN 4: VPN & REMOTE ACCESS CAPABILITIES
    story.append(Paragraph("Domain D: Virtual Private Network (VPN) Technologies", h2_style))
    domain_d = [
        ("Site-to-Site IPsec VPN", "YES", "YES", "YES", "YES", "YES"),
        ("SSL VPN (Client / Portal)", "YES", "YES", "YES", "YES", "YES"),
        ("IPSec Remote Access VPN", "NA", "YES", "YES", "NA", "YES"),
        ("Full Mesh Dynamic VPN", "YES (LSVPN)", "YES", "YES (ADVPN)", "NA", "NA"),
        ("VPN Load Balancing", "NA", "NA", "NA", "NA", "YES"),
    ]
    story.append(build_matrix_table_compact(domain_d))
    story.append(Spacer(1, 5))

    # DOMAIN 5: HIGH AVAILABILITY, CLUSTERING & LAYER 2 INTERFACES
    story.append(Paragraph("Domain E: High Availability, Redundancy &amp; Deployment Modes", h2_style))
    domain_e = [
        ("VRRP (Virtual Router Redundancy)", "NA", "YES", "YES", "NA", "NA"),
        ("HA Active-Passive", "YES", "YES", "YES", "YES", "YES"),
        ("HA Active-Active", "YES", "YES", "YES", "YES", "YES"),
        ("Firewall Clustering", "YES", "YES", "YES", "NA", "YES"),
        ("Transparent Firewall (Layer 2)", "NA", "YES", "YES", "YES", "YES"),
        ("Virtual Wire (V-Wire Mode)", "YES", "NA", "YES", "NA", "NA"),
        ("Server Load Balancing (SLB)", "NA", "NA", "YES", "NA", "NA"),
    ]
    story.append(build_matrix_table_compact(domain_e))
    story.append(Spacer(1, 5))

    # DOMAIN 6: NEXT-GENERATION SECURITY ENGINES & CENTRAL MANAGEMENT
    story.append(Paragraph("Domain F: Next-Generation Inspection Engines &amp; Central Orchestration", h2_style))
    domain_f = [
        ("SSL Decryption / Inspection", "YES (SSL Decrypt)", "YES (HTTP Insp.)", "YES (HTTP Insp.)", "YES (SSL Policy)", "NO"),
        ("Application Control", "YES (APP-ID)", "YES", "YES", "YES", "NO"),
        ("Content Control / DLP", "YES (Content-ID)", "YES (Content Aware)", "YES", "YES (Malware Policy)", "NO"),
        ("URL Filtering", "YES (PAN-DB)", "YES (URL Filtering)", "YES", "YES", "NO"),
        ("SandBox Threat Emulation", "YES (WildFire)", "YES (SandBlast)", "YES (FortiSandbox)", "YES (Security Intell.)", "NO"),
        ("Directory / Identity Integration", "YES (User-ID)", "YES (Identity Aware)", "YES (FSSO)", "YES (Identity Policy)", "NO"),
        ("Traffic &amp; Flow Monitoring", "YES", "YES", "YES", "YES", "NO"),
        ("Central Orchestration / NMS", "YES (Panorama)", "YES (SMS)", "YES (FMG)", "YES (FMC)", "NO"),
    ]
    story.append(build_matrix_table_compact(domain_f))
    story.append(Spacer(1, 8))

    # SECTION 3: KEY ARCHITECTURAL TAKEAWAYS & COMPETITIVE ANALYSIS
    story.append(Paragraph("3. Strategic Engineering Analysis &amp; Technical Insights", h1_style))

    analysis_text = (
        "<b>1. Cisco ASA Obsolescence in Modern Threat Defenses:</b> For rows 38 through 45 (SSL Decryption, Application Control, Content-ID, "
        "Sandboxing, User-ID, and Centralized Orchestration), <b>Cisco ASA is scored 'NO' across the board</b>. Cisco ASA was engineered "
        "in the 2000s as a Layer 3/4 stateful port filter. It cannot inspect encrypted TLS 1.3 flows, classify modern cloud applications, or correlate active directory identities.<br/>"
        "<b>2. Palo Alto's SP3 Single-Pass Ecosystem:</b> Palo Alto pioneered the Next-Gen market with dedicated hardware architectures: "
        "<b>App-ID</b> (identifies applications regardless of port, protocol, or SSL encryption), <b>Content-ID</b> (stream-based virus, spyware, and vulnerability scanning), "
        "<b>User-ID</b> (binds IP addresses to Active Directory users and groups), and <b>WildFire</b> (cloud-scale sandbox detonation engine).<br/>"
        "<b>3. Full Mesh VPN Architecture:</b> In dynamic multi-site architectures, Palo Alto leverages <b>LSVPN (Large Scale VPN)</b> with GlobalProtect satellites, "
        "whereas Fortinet utilizes <b>ADVPN (Auto Discovery VPN)</b> with BGP shortcut routing. Cisco FTD lacks an automated dynamic full-mesh solution equivalent to DMVPN.<br/>"
        "<b>4. Central Management Comparison:</b> Every top enterprise vendor provides a dedicated orchestration platform: "
        "Palo Alto employs <b>Panorama</b> (unifying device templates and device groups), CheckPoint utilizes <b>SMS (Security Management Server)</b>, "
        "Fortinet uses <b>FortiManager (FMG)</b>, and Cisco FTD relies upon <b>FMC (Firepower Management Center)</b>."
    )
    story.append(create_callout(analysis_text, title="ENTERPRISE EVALUATION & STRATEGIC TAKEAWAYS", border_c=primary_color, bg_c=colors.HexColor("#F7FAFC")))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {output_pdf}")

if __name__ == "__main__":
    output_filename = "PDF_Documentation/01_Architecture_and_Comparison/Enterprise_Firewall_Comparison_Matrix.pdf"
    build_pdf(output_filename)
