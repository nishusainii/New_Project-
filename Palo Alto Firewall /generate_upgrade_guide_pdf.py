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
            self.drawString(54, 11 * inch - 36, "Palo Alto Networks PAN-OS — Enterprise Software Upgrade Standard Operating Procedure")
            self.setFont("Helvetica", 8)
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "SOP: PAN-OS-UPG-01 | Oct 2026")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 44, 8.5 * inch - 54, 44)
        
        self.setFont("Helvetica", 8)
        self.drawString(54, 30, "Confidential — Network Operations & Security Engineering | Prepared by Nishu Saini")
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
    accent_green = colors.HexColor("#276749")    # Forest green
    accent_red = colors.HexColor("#C53030")      # Warning red
    accent_orange = colors.HexColor("#DD6B20")   # Warning orange
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
        spaceAfter=8
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=14.5,
        textColor=primary_color,
        spaceBefore=9,
        spaceAfter=4,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12.5,
        textColor=secondary_color,
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.2,
        leading=11,
        textColor=dark_neutral,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.8,
        leading=10.5,
        textColor=dark_neutral
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
        fontSize=7.2,
        leading=9.2,
        textColor=dark_neutral
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.2,
        textColor=dark_neutral
    )

    table_cell_code = ParagraphStyle(
        'TableCellCode',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=6.8,
        leading=8.8,
        textColor=primary_color
    )

    def create_code_block(code_str):
        p = Preformatted(
            code_str,
            ParagraphStyle(
                'PreformattedCode',
                fontName='Courier',
                fontSize=7.0,
                leading=8.8,
                textColor=code_text
            )
        )
        t = Table([[p]], colWidths=[7.0 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), code_bg),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#4A5568")),
        ]))
        return t

    def create_callout(text, title="CRITICAL REQUIREMENT", border_c=secondary_color, bg_c=callout_bg):
        content = [
            Paragraph(f"<b>{title}</b>", ParagraphStyle('CTitle', parent=callout_style, fontName='Helvetica-Bold', textColor=border_c)),
            Spacer(1, 2),
            Paragraph(text, callout_style)
        ]
        t = Table([[content]], colWidths=[7.0 * inch])
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

    def create_gui_card(step_num, title, action_text, note=""):
        content_items = [
            Paragraph(f"<b>STEP {step_num}: {title}</b>", ParagraphStyle('GTitle', parent=callout_style, fontName='Helvetica-Bold', fontSize=8.2, textColor=accent_green)),
            Spacer(1, 2),
            Paragraph(action_text, callout_style)
        ]
        if note:
            content_items.append(Spacer(1, 2))
            content_items.append(Paragraph(f"<b>[OPERATIONAL NOTE]:</b> {note}", ParagraphStyle('GNote', parent=callout_style, textColor=secondary_color)))

        t = Table([[content_items]], colWidths=[7.0 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FFF4")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#9AE6B4")),
            ('LINELEFT', (0,0), (0,-1), 3.0, accent_green)
        ]))
        return t

    story = []

    # TITLE & HEADER
    story.append(Paragraph("Palo Alto Networks PAN-OS — Complete Upgrade Runbook", title_style))
    story.append(Paragraph(
        "Comprehensive Enterprise Standard Operating Procedure: Pre-Upgrade Readiness, Sequential Major Version Pathways, Web GUI &amp; CLI Execution, HA Zero-Downtime Failover, and Disaster Rollback",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8, spaceBefore=0))

    # METADATA BLOCK
    meta_data = [
        [Paragraph("Document ID:", table_cell_bold), Paragraph("SOP-PAN-UPG-01", table_cell), Paragraph("Hardware &amp; VM:", table_cell_bold), Paragraph("PA-220 / 400 / 800 / 3200 / 5200 / 7000 / PA-VM", table_cell)],
        [Paragraph("Release Trains:", table_cell_bold), Paragraph("PAN-OS 9.1 &rarr; 10.0 &rarr; 10.1 &rarr; 10.2 &rarr; 11.0 &rarr; 11.1", table_cell), Paragraph("HA Deployment:", table_cell_bold), Paragraph("Active/Passive &amp; Standalone Appliances", table_cell)],
        [Paragraph("Classification:", table_cell_bold), Paragraph("Critical Infrastructure Maintenance", table_cell), Paragraph("Lead Engineer:", table_cell_bold), Paragraph("Nishu Saini (Innspark Solutions)", table_cell)],
    ]
    meta_table = Table(meta_data, colWidths=[1.3 * inch, 2.2 * inch, 1.4 * inch, 2.1 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # SECTION 1: CRITICAL GOLDEN RULES OF PAN-OS UPGRADES
    story.append(Paragraph("1. Fundamental Architectural Rules &amp; Version Hop Constraints", h1_style))
    story.append(Paragraph(
        "Upgrading Palo Alto PAN-OS requires adherence to strict architectural rules. Violating upgrade rules can result in XML schema corruption, "
        "failed configuration commits, daemon crashes, or unbootable storage partitions. The following core principles govern every upgrade:",
        body_style
    ))

    rules_box = (
        "<b>1. Sequential Upgrade Path (NO Major Version Skipping):</b> You cannot hop directly across major versions (e.g. 9.1.x directly to 10.2.x is prohibited). "
        "You must traverse every intermediate major release: <b>9.1.x &rarr; 10.0.x &rarr; 10.1.x &rarr; 10.2.x</b>.<br/>"
        "<b>2. Base (.0) Image Requirement:</b> To install any maintenance release (e.g., 10.1.10), the major release <b>base image (10.1.0) must be downloaded</b> onto local flash storage. "
        "However, <i>you do not need to install or reboot into the .0 base image</i>; download the .0 base image, then download and install your target maintenance release directly.<br/>"
        "<b>3. Dynamic Updates Prerequisite:</b> The Applications and Threats database must be updated to the latest available package before triggering any PAN-OS software upgrade.<br/>"
        "<b>4. Panorama Central Management Rule:</b> If managed centrally via Panorama, Panorama must ALWAYS be upgraded to a version equal to or higher than the firewalls it manages."
    )
    story.append(create_callout(rules_box, title="GOLDEN RULES OF PAN-OS UPGRADES", border_c=accent_red, bg_c=colors.HexColor("#FFF5F5")))
    story.append(Spacer(1, 8))

    # UPGRADE PATHWAY TABLE
    path_data = [
        [Paragraph("Starting Release", table_header), Paragraph("Target Release", table_header), Paragraph("Mandatory Step-by-Step Upgrade Sequence", table_header)],
        [
            Paragraph("PAN-OS 9.1.x", table_cell_code),
            Paragraph("PAN-OS 10.1.x (Recommended)", table_cell_bold),
            Paragraph("1. Download 10.0.0 (Base) &rarr; Download &amp; Install 10.0.x &rarr; Reboot.<br/>2. Download 10.1.0 (Base) &rarr; Download &amp; Install 10.1.10 &rarr; Reboot.", table_cell)
        ],
        [
            Paragraph("PAN-OS 10.1.x", table_cell_code),
            Paragraph("PAN-OS 10.2.x", table_cell_bold),
            Paragraph("1. Download 10.2.0 (Base) &rarr; Download &amp; Install target 10.2.x (e.g. 10.2.8-h3) &rarr; Reboot.", table_cell)
        ],
        [
            Paragraph("PAN-OS 10.2.x", table_cell_code),
            Paragraph("PAN-OS 11.0.x / 11.1.x", table_cell_bold),
            Paragraph("1. Download 11.0.0 (Base) &rarr; Install 11.0.x &rarr; Reboot &rarr; Download 11.1.0 &rarr; Install 11.1.x &rarr; Reboot.", table_cell)
        ],
    ]
    path_table = Table(path_data, colWidths=[1.3 * inch, 1.7 * inch, 4.0 * inch])
    path_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(path_table)
    story.append(Spacer(1, 8))

    # SECTION 2: PRE-UPGRADE READINESS & SAFETY CHECKLIST
    story.append(Paragraph("2. Pre-Upgrade Preparation &amp; Readiness Checklist", h1_style))
    story.append(Paragraph(
        "Execute these pre-flight checks before scheduling the maintenance window:",
        body_style
    ))

    pre_checks = [
        [Paragraph("Check Item", table_header), Paragraph("Action / CLI Verification Command", table_header), Paragraph("Success Criterion", table_header)],
        [
            Paragraph("1. Full Off-Box Backup", table_cell_bold),
            Paragraph("<code>save config to Pre_Upgrade_Backup.xml</code><br/>Export named configuration snapshot via Web GUI to external drive.", table_cell),
            Paragraph("Verified XML backup file stored outside the firewall.", table_cell)
        ],
        [
            Paragraph("2. Disk Space Audit", table_cell_bold),
            Paragraph("<code>show system disk-space</code><br/>Check <code>/opt/pancfg</code> and <code>/</code> partitions.", table_cell),
            Paragraph("Partition utilization must be below 85%. Delete stale software images if needed.", table_cell)
        ],
        [
            Paragraph("3. Clean Old Software", table_cell_bold),
            Paragraph("<code>delete software version &lt;old-version&gt;</code><br/>Purge outdated versions from flash storage.", table_cell),
            Paragraph("At least 3.0 GB of free space available on root/panos partition.", table_cell)
        ],
        [
            Paragraph("4. Dynamic Updates", table_cell_bold),
            Paragraph("<code>request content upgrade check</code><br/>Install latest <i>Applications and Threats</i> package.", table_cell),
            Paragraph("App/Threat engine version current and status = Completed.", table_cell)
        ],
        [
            Paragraph("5. Candidate Config", table_cell_bold),
            Paragraph("<code>show config diff</code>", table_cell),
            Paragraph("No uncommitted changes in candidate buffer prior to upgrade.", table_cell)
        ],
        [
            Paragraph("6. Active Sessions &amp; HA", table_cell_bold),
            Paragraph("<code>show session info</code><br/><code>show high-availability state</code>", table_cell),
            Paragraph("Firewall healthy; HA synchronization state = <b>synchronized</b>.", table_cell)
        ],
    ]
    pre_table = Table(pre_checks, colWidths=[1.4 * inch, 3.4 * inch, 2.2 * inch])
    pre_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(pre_table)
    story.append(Spacer(1, 8))

    # SECTION 3: STEP-BY-STEP WEB GUI UPGRADE PROCEDURE
    story.append(Paragraph("3. Web GUI Step-by-Step Upgrade Procedure", h1_style))

    # GUI Step 1
    g1 = (
        "1. In the Web GUI, navigate to: <b>Device</b> &rarr; <b>Dynamic Updates</b>.<br/>"
        "2. Click <b>Check Now</b> at the bottom of the screen.<br/>"
        "3. Locate the latest version of <b>Applications and Threats</b>.<br/>"
        "4. Click <b>Download</b>, and once finished, click <b>Install</b>.<br/>"
        "5. Verify task completion in the <b>Tasks</b> window (Status = Completed)."
    )
    story.append(create_gui_card("1", "Update Content Engine (Applications & Threats)", g1))
    story.append(Spacer(1, 5))

    # GUI Step 2
    g2 = (
        "1. In the Web GUI, navigate to: <b>Device</b> &rarr; <b>Software</b>.<br/>"
        "2. Click <b>Check Now</b> at the bottom of the screen to poll Palo Alto cloud update servers.<br/>"
        "3. Locate the <b>Base Image (.0)</b> of the next major version (e.g., <code>PanOS_10.1.0</code>).<br/>"
        "4. In the <i>Action</i> column, click <b>Download</b>.<br/>"
        "5. <i>Crucial:</i> Once the download finishes, <b>DO NOT CLICK INSTALL</b> on the .0 base image."
    )
    story.append(create_gui_card("2", "Download Mandatory Base (.0) Image", g2, "Base images must only be downloaded, not installed."))
    story.append(Spacer(1, 5))

    # GUI Step 3
    g3 = (
        "1. In the same <b>Device</b> &rarr; <b>Software</b> window, locate the target maintenance release (e.g., <code>PanOS_10.1.10</code>).<br/>"
        "2. Click <b>Download</b>. Monitor the task progress via the bottom-right <b>Tasks</b> window.<br/>"
        "3. Once downloaded, click <b>Install</b> in the Action column.<br/>"
        "4. An installation pop-up will appear asking: <i>'Do you want to reboot the device after installation?'</i><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• If inside your maintenance window: Select <b>Yes</b> to automatically reboot.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• If staging ahead of time: Select <b>No</b> (reboot later manually via Device &rarr; Operations &rarr; Reboot)."
    )
    story.append(create_gui_card("3", "Download and Install Target Maintenance Release", g3))
    story.append(Spacer(1, 5))

    # GUI Step 4
    g4 = (
        "1. During reboot, the management plane will be offline for approximately 5 to 10 minutes (hardware platforms may take 12–15 minutes).<br/>"
        "2. Ping the management IP continuously: <code>ping -t 172.17.0.50</code>.<br/>"
        "3. Once ICMP replies resume, navigate to <b><code>https://172.17.0.50</code></b> and log into the Web GUI.<br/>"
        "4. On the <b>Dashboard</b>, inspect the <b>General Information</b> widget:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <b>Software Version:</b> Confirm it reflects the new target version (e.g. <code>10.1.10</code>).<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <b>Application Version:</b> Confirm current.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;• <b>Threat Version:</b> Confirm current."
    )
    story.append(create_gui_card("4", "Reboot and Post-Upgrade Dashboard Verification", g4))
    story.append(Spacer(1, 8))

    # SECTION 4: COMPLETE CLI COMMAND SEQUENCE
    story.append(Paragraph("4. Alternative PAN-OS CLI Commands (Direct Terminal Execution)", h1_style))
    story.append(Paragraph(
        "For network engineers performing upgrades via SSH or serial console, use this verified end-to-end command sequence:",
        body_style
    ))

    cmd_upgrade = """# Phase 1: Pre-Upgrade Verification & Content Update
admin@PA-1> show system info
admin@PA-1> show system disk-space
admin@PA-1> request content upgrade check
admin@PA-1> request content upgrade download latest
admin@PA-1> request content upgrade install version latest

# Phase 2: Query Cloud Servers & Download Base Software Image
admin@PA-1> request system software check
admin@PA-1> request system software download version 10.1.0

# Phase 3: Download and Install Target Maintenance Release
admin@PA-1> request system software download version 10.1.10
admin@PA-1> request system software install version 10.1.10

# Phase 4: Monitor Software Installation Job
admin@PA-1> show jobs all
# (Look for job type: 'SWInstall', Status: 'FIN', Result: 'OK')

# Phase 5: Initiate Graceful System Reboot
admin@PA-1> request restart system
# Press 'y' to confirm system restart

# Phase 6: Post-Reboot Verification & Validation
admin@PA-1> show system info | match sw-version
# (Expected: sw-version: 10.1.10)
admin@PA-1> show routing route summary
admin@PA-1> show session info"""
    story.append(create_code_block(cmd_upgrade))
    story.append(Spacer(1, 8))

    # SECTION 5: AIR-GAPPED / OFFLINE UPGRADE WORKFLOW
    story.append(Paragraph("5. Air-Gapped / Offline Upgrade Method (No Internet Access)", h1_style))
    story.append(Paragraph(
        "For isolated defense, financial, or SCADA environments where the firewall MGT interface cannot access the public internet:",
        body_style
    ))

    offline_box = (
        "<b>1. Download from Support Portal:</b> On an internet-connected workstation, log into <code>support.paloaltonetworks.com</code> &rarr; <i>Updates</i> &rarr; <i>Software Updates</i>. Download both the Base image (.0) and target maintenance release (.xfr / .panos).<br/>"
        "<b>2. Upload via Web GUI:</b> Navigate to <b>Device &rarr; Software &rarr; Upload</b>. Click Browse, select the downloaded image file, and click OK.<br/>"
        "<b>3. Upload via SCP (CLI):</b> From terminal, SCP the software package directly into the firewall's panos repository:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>scp PanOS_10.1.10 admin@172.17.0.50:/opt/panrepo/</code><br/>"
        "<b>4. Install via CLI:</b> <code>request system software install file PanOS_10.1.10</code> followed by <code>request restart system</code>."
    )
    story.append(create_callout(offline_box, title="OFFLINE / AIR-GAPPED DEPLOYMENT RUNBOOK", border_c=accent_orange, bg_c=colors.HexColor("#FFFAF0")))
    story.append(Spacer(1, 8))

    # SECTION 6: HIGH AVAILABILITY (HA) ZERO-DOWNTIME UPGRADE
    story.append(Paragraph("6. High Availability (HA Active/Passive) Zero-Downtime Upgrade Sequence", h1_style))
    story.append(Paragraph(
        "In production environments with Active/Passive HA pairs, perform the upgrade without dropping live customer traffic using this exact sequence:",
        body_style
    ))

    ha_data = [
        [Paragraph("Step", table_header), Paragraph("Target Appliance", table_header), Paragraph("Action Performed", table_header), Paragraph("Traffic Impact", table_header)],
        [
            Paragraph("1. Pre-Check", table_cell_bold),
            Paragraph("Both Nodes (FW-A &amp; FW-B)", table_cell),
            Paragraph("Verify HA sync: <code>show high-availability state</code>. Ensure sync = synchronized.", table_cell),
            Paragraph("None (FW-A active).", table_cell)
        ],
        [
            Paragraph("2. Upgrade Passive", table_cell_bold),
            Paragraph("<b>Passive Peer (FW-B)</b>", table_cell),
            Paragraph("Download base and target images on FW-B. Install target version and reboot FW-B.", table_cell),
            Paragraph("None (FW-A handles 100% traffic).", table_cell)
        ],
        [
            Paragraph("3. Verify Passive", table_cell_bold),
            Paragraph("Passive Peer (FW-B)", table_cell),
            Paragraph("FW-B boots into new PAN-OS. Verify status = <b>Passive</b> and HA sync = <b>synchronized</b>.", table_cell),
            Paragraph("None (FW-A handles 100% traffic).", table_cell)
        ],
        [
            Paragraph("4. Controlled Failover", table_cell_bold),
            Paragraph("Active Peer (FW-A)", table_cell),
            Paragraph("Suspend FW-A to gracefully shift traffic: <code>request high-availability state suspend</code>.", table_cell),
            Paragraph("Sub-second failover to FW-B.", table_cell)
        ],
        [
            Paragraph("5. Upgrade Former Active", table_cell_bold),
            Paragraph("<b>Suspended Peer (FW-A)</b>", table_cell),
            Paragraph("Download base and target images on FW-A. Install target version and reboot FW-A.", table_cell),
            Paragraph("None (FW-B handles 100% traffic).", table_cell)
        ],
        [
            Paragraph("6. Restore Normal State", table_cell_bold),
            Paragraph("Former Active (FW-A)", table_cell),
            Paragraph("Once FW-A boots: <code>request high-availability state functional</code>. Both peers now run identical new PAN-OS.", table_cell),
            Paragraph("Full HA redundancy restored.", table_cell)
        ],
    ]
    ha_table = Table(ha_data, colWidths=[1.1 * inch, 1.8 * inch, 2.7 * inch, 1.4 * inch])
    ha_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(ha_table)
    story.append(Spacer(1, 8))

    # SECTION 7: EMERGENCY ROLLBACK PROCEDURE
    story.append(Paragraph("7. Disaster Recovery: Emergency Rollback to Previous PAN-OS Release", h1_style))
    story.append(Paragraph(
        "Palo Alto firewalls employ a dual-boot partition architecture (sysroot0 and sysroot1). "
        "When you upgrade, the new OS is written to the inactive partition, leaving the previous working operating system intact on the alternate partition. "
        "If severe unexpected packet drops or daemon instability occur post-upgrade:",
        body_style
    ))

    cmd_rollback = """# Method A: Software Revert via Running CLI (Within Current Session)
admin@PA-1> request system software revert
# System prompts: 'Are you sure you want to revert to the previous software version? (y or n)'
# Press 'y' -> PAN-OS switches the bootloader pointer to the previous partition.
admin@PA-1> request restart system

# Method B: Rollback via Maintenance Mode (maint) Console
# 1. Connect serial console (9600-8-N-1) -> Reboot appliance.
# 2. Type 'maint' at boot countdown -> Select 'Continue'.
# 3. Navigate to: 'Select Root Partition' (or 'Boot Inactive Partition').
# 4. Choose the previous working sysroot partition (shows previous PAN-OS version) -> Select 'Reboot'."""
    story.append(create_code_block(cmd_rollback))
    story.append(Spacer(1, 8))

    # FINAL CALLOUT
    story.append(create_callout(
        "<b>Post-Upgrade Maintenance Window Closure:</b> Monitor firewall CPU utilization (<code>show running resource-monitor</code>) "
        "and data plane packet buffers for 60 minutes post-upgrade. Verify all IPSec VPN tunnels (<code>show vpn ike-sa</code>, <code>show vpn ipsec-sa</code>) "
        "and external BGP/OSPF peerings are fully established before declaring maintenance completion.",
        title="OPERATIONAL SIGNOFF & VALIDATION",
        border_c=accent_green,
        bg_c=colors.HexColor("#F0FFF4")
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {output_pdf}")

if __name__ == "__main__":
    output_filename = "Palo_Alto_PANOS_Upgrade_Guide.pdf"
    build_pdf(output_filename)
