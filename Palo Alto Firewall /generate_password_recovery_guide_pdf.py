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
            self.drawString(54, 11 * inch - 36, "Palo Alto Networks PAN-OS — Zero-Data-Loss Password Recovery Standard Operating Procedure")
            self.setFont("Helvetica", 8)
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "SOP: PAN-SEC-REC-01 | Oct 2026")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 44, 8.5 * inch - 54, 44)
        
        self.setFont("Helvetica", 8)
        self.drawString(54, 30, "Confidential — Network Security Operations Runbook | Prepared by Nishu Saini")
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
        fontSize=12,
        leading=15,
        textColor=primary_color,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=secondary_color,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=dark_neutral,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=dark_neutral
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=dark_neutral
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=dark_neutral
    )

    table_cell_code = ParagraphStyle(
        'TableCellCode',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=7,
        leading=9,
        textColor=primary_color
    )

    def create_code_block(code_str):
        p = Preformatted(
            code_str,
            ParagraphStyle(
                'PreformattedCode',
                fontName='Courier',
                fontSize=7.2,
                leading=9.2,
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

    def create_callout(text, title="NOTE / CRITICAL GUIDELINE", border_c=secondary_color, bg_c=callout_bg):
        content = [
            Paragraph(f"<b>{title}</b>", ParagraphStyle('CTitle', parent=callout_style, fontName='Helvetica-Bold', textColor=border_c)),
            Spacer(1, 2),
            Paragraph(text, callout_style)
        ]
        t = Table([[content]], colWidths=[7.0 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_c),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, border_c),
            ('LINELEFT', (0,0), (0,-1), 3.0, border_c)
        ]))
        return t

    def create_gui_card(step_num, title, action_text, critical_note=""):
        content_items = [
            Paragraph(f"<b>STEP {step_num}: {title}</b>", ParagraphStyle('GTitle', parent=callout_style, fontName='Helvetica-Bold', fontSize=8.5, textColor=accent_green)),
            Spacer(1, 2),
            Paragraph(action_text, callout_style)
        ]
        if critical_note:
            content_items.append(Spacer(1, 2))
            content_items.append(Paragraph(f"<b>[CRITICAL WARNING]:</b> {critical_note}", ParagraphStyle('GNote', parent=callout_style, textColor=accent_red)))

        t = Table([[content_items]], colWidths=[7.0 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FFF4")), # Light green tint
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#9AE6B4")),
            ('LINELEFT', (0,0), (0,-1), 3.0, accent_green)
        ]))
        return t

    story = []

    # TITLE & HEADER
    story.append(Paragraph("Palo Alto Networks PAN-OS — Administrator Password Recovery", title_style))
    story.append(Paragraph(
        "Zero-Data-Loss Standard Operating Procedure: Leveraging Maintenance Mode ('maint') &amp; config.xml.backup to Restore 100% of Production Policies with a New Administrative Credential",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=8, spaceBefore=0))

    # METADATA BLOCK
    meta_data = [
        [Paragraph("Document ID:", table_cell_bold), Paragraph("SOP-PAN-REC-01", table_cell), Paragraph("Appliance Models:", table_cell_bold), Paragraph("PA-220 / 400 / 800 / 3200 / 5200 / PA-VM", table_cell)],
        [Paragraph("Target OS:", table_cell_bold), Paragraph("PAN-OS 9.1 / 10.0 / 10.1 / 10.2 / 11.0+", table_cell), Paragraph("Console Baud / Port:", table_cell_bold), Paragraph("9600-8-N-1 (Physical) / TCP 5008 (GNS3)", table_cell)],
        [Paragraph("Classification:", table_cell_bold), Paragraph("Operational Runbook — Enterprise Security", table_cell), Paragraph("Lead Engineer:", table_cell_bold), Paragraph("Nishu Saini (Innspark Solutions)", table_cell)],
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

    # SECTION 1: PROBLEM CONTEXT & TECHNICAL CHALLENGE
    story.append(Paragraph("1. Operational Context: The Forgotten Administrator Password Dilemma", h1_style))
    story.append(Paragraph(
        "In enterprise network engineering, losing access to a production Palo Alto Next-Generation Firewall presents severe business risks. "
        "Unlike commercial consumer routers or standard web portals, <b>Palo Alto PAN-OS intentionally excludes any 'Forgot Password' button or web-based recovery mechanism</b> on its HTTPS management login page. "
        "This security architecture ensures that an external or unauthorized adversary cannot compromise administrative rights over the management plane.",
        body_style
    ))
    story.append(Paragraph(
        "Historically, engineers faced with a forgotten password might resort to a full factory reset (<code>request system private-data-reset</code>). "
        "However, a factory reset completely purges all configured Security Policies, NAT rules, Decryption profiles, Site-to-Site IPsec tunnels, "
        "GlobalProtect VPN certificates, and Layer 3 interfaces. This document details the <b>Zero-Data-Loss Disaster Recovery Workflow</b>: "
        "a method that safely swaps the administrative credentials while recovering <b>100% of the latest running configuration</b>.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # SECTION 2: ARCHITECTURAL PRINCIPLE
    story.append(Paragraph("2. Architectural Mechanism: How the 'config.xml.backup' Safety Net Works", h1_style))
    story.append(Paragraph(
        "The core technical mechanism that makes zero-data-loss recovery possible is built into the PAN-OS Maintenance Mode storage engine. "
        "When an engineer boots into Maintenance Mode (<code>maint</code>) and restores an older configuration XML file (where credentials are known), "
        "the PAN-OS underlying Linux kernel automatically executes a pre-commit preservation hook: it takes the current active production <code>running-config.xml</code> "
        "and saves an exact snapshot of it to local flash storage named:",
        body_style
    ))
    story.append(create_code_block("config.xml.backup"))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        "Because <code>config.xml.backup</code> contains every single policy, zone, address object, and rule that was active before the lockout, "
        "we can log in using our old credentials, load <code>config.xml.backup</code> into the <b>Candidate Configuration</b> buffer, "
        "immediately overwrite the admin password in GUI before committing, and execute a commit. The result is total recovery without data loss.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # WORKFLOW FLOWCHART TABLE
    flow_data = [
        [Paragraph("Phase", table_header), Paragraph("Operational Action", table_header), Paragraph("Storage State &amp; Mechanics", table_header)],
        [
            Paragraph("Phase 1: Boot 'maint'", table_cell_bold),
            Paragraph("Reboot firewall via console; enter <b><code>maint</code></b> at prompt.", table_cell),
            Paragraph("Bypasses active PAN-OS daemons into RAM-disk recovery kernel.", table_cell)
        ],
        [
            Paragraph("Phase 2: Restore Old Config", table_cell_bold),
            Paragraph("Select an older backup XML with a known password. Reboot.", table_cell),
            Paragraph("PAN-OS saves current config as <b><code>config.xml.backup</code></b>.", table_cell)
        ],
        [
            Paragraph("Phase 3: Web GUI Login", table_cell_bold),
            Paragraph("Open <code>https://&lt;MGT-IP&gt;</code> and log in with known old credentials.", table_cell),
            Paragraph("Firewall runs old baseline config; full GUI access is restored.", table_cell)
        ],
        [
            Paragraph("Phase 4: Load Latest Backup", table_cell_bold),
            Paragraph("Navigate to <b>Device &rarr; Setup &rarr; Operations &rarr; Load named configuration snapshot</b>. Select <code>config.xml.backup</code>.", table_cell),
            Paragraph("Loads all latest policies/NAT into <b>Candidate Config</b> buffer.", table_cell)
        ],
        [
            Paragraph("Phase 5: Task Audit", table_cell_bold),
            Paragraph("Open bottom-right <b>Tasks</b> panel. Verify Config Load is <b>Completed</b>.", table_cell),
            Paragraph("Confirms candidate buffer is 100% loaded and syntax valid.", table_cell)
        ],
        [
            Paragraph("Phase 6: Password Override", table_cell_bold),
            Paragraph("Navigate to <b>Device &rarr; Administrators &rarr; admin &rarr; Change Password</b>. Set new secure password.", table_cell),
            Paragraph("Overwrites the forgotten password inside candidate buffer <b>BEFORE commit</b>.", table_cell)
        ],
        [
            Paragraph("Phase 7: Final Commit", table_cell_bold),
            Paragraph("Click <b>Commit</b> at top-right. Commit job reaches 100% success.", table_cell),
            Paragraph("Candidate becomes Running Config. Latest setup is active with new password.", table_cell)
        ],
    ]
    flow_table = Table(flow_data, colWidths=[1.5 * inch, 2.8 * inch, 2.7 * inch])
    flow_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(flow_table)
    story.append(Spacer(1, 8))

    # SECTION 3: STEP-BY-STEP EXECUTION RUNBOOK
    story.append(Paragraph("3. Step-by-Step Tactical Execution Guide", h1_style))
    story.append(Paragraph(
        "Follow these seven exact phases in strict chronological sequence. Do not skip or alter the order of operations:",
        body_style
    ))

    # STEP 1
    step1_text = (
        "1. Attach to the serial console port of the firewall (<b>RJ-45 9600-8-N-1</b> on physical hardware, or port <b>5008</b> in GNS3/EVE-NG).<br/>"
        "2. Reboot the firewall appliance (power-cycle or send break sequence).<br/>"
        "3. As the kernel initializes, observe the serial output. When the countdown prompt appears:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<code>Hit Enter to continue...</code><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;Immediately type <b><code>maint</code></b> and press <b>Enter</b> within 5 seconds."
    )
    story.append(create_gui_card("1", "Serial Console Access & Maintenance Mode Boot", step1_text))
    story.append(Spacer(1, 5))

    # STEP 2
    step2_text = (
        "1. The PAN-OS Maintenance Recovery Tool loads into a blue/gray text-based terminal interface.<br/>"
        "2. Press <b>Enter</b> on <b>Continue</b>.<br/>"
        "3. Navigate using arrow keys to <b>Config Recovery</b> (or <b>Restore Configuration</b>).<br/>"
        "4. Select an older saved configuration XML file where the username and password are known.<br/>"
        "5. Confirm the restore. During this operation, PAN-OS copies the active running configuration to <code>config.xml.backup</code>.<br/>"
        "6. Select <b>Reboot</b> to restart the firewall into normal operational mode."
    )
    story.append(create_gui_card("2", "Load Known Configuration in 'maint' Mode & Trigger Auto-Backup", step2_text))
    story.append(Spacer(1, 5))

    # STEP 3
    step3_text = (
        "1. Allow the firewall 3–5 minutes to complete daemon startup (Management Plane, <code>mgmtsrvr</code>, and Web Server).<br/>"
        "2. Open a web browser (Google Chrome or Mozilla Firefox) and navigate to the management interface:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b><code>https://172.17.0.50</code></b> (or your OOB management IP e.g. <code>https://192.168.1.1</code>).<br/>"
        "3. Bypass the self-signed SSL certificate prompt (<b>Advanced &rarr; Proceed to IP (unsafe)</b>).<br/>"
        "4. Log in using the <b>OLD known credentials</b> from the snapshot restored in Phase 2."
    )
    story.append(create_gui_card("3", "Web GUI Authentication with Known Old Credentials", step3_text))
    story.append(Spacer(1, 5))

    # STEP 4
    step4_text = (
        "1. In the top navigation bar of the Web GUI, click the <b>Device</b> tab.<br/>"
        "2. In the left-hand navigation pane, select <b>Setup</b> &rarr; <b>Operations</b>.<br/>"
        "3. Locate the <b>Configuration Management</b> section.<br/>"
        "4. Click <b>Load named configuration snapshot</b>.<br/>"
        "5. In the modal dialog dropdown, locate and select the auto-saved backup file:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b><code>config.xml.backup</code></b><br/>"
        "6. Click <b>OK</b>."
    )
    step4_crit = "DO NOT click the 'Commit' button at this point! Clicking commit now will lock you out again with the forgotten password."
    story.append(create_gui_card("4", "Load 'config.xml.backup' into Candidate Configuration Buffer", step4_text, step4_crit))
    story.append(Spacer(1, 5))

    # STEP 5
    step5_text = (
        "1. Look at the bottom-right corner of the PAN-OS Web GUI footer bar.<br/>"
        "2. Click the <b>Tasks</b> button (icon with clipboard/checkboxes) to open the Task Manager window.<br/>"
        "3. Locate the job labeled <b>Config Load</b>.<br/>"
        "4. Verify that the <i>Status</i> column displays a green checkmark and says <b>Completed</b>, with <i>Result</i> showing <b>FIN</b> (100%).<br/>"
        "5. Click <b>Close</b> to dismiss the Task Manager."
    )
    story.append(create_gui_card("5", "Verify Job Completion in PAN-OS Task Manager", step5_text))
    story.append(Spacer(1, 5))

    # STEP 6
    step6_text = (
        "1. Navigate to <b>Device</b> &rarr; <b>Administrators</b> in the left navigation tree.<br/>"
        "2. In the Administrator Accounts table, click directly on the username <b><code>admin</code></b>.<br/>"
        "3. In the <i>Administrator</i> pop-up configuration dialog, click the <b>Change Password</b> link / checkbox.<br/>"
        "4. Type your desired <b>New Password</b> (ensure it satisfies corporate complexity: &ge; 8 characters, upper, lower, numbers, and symbols).<br/>"
        "5. Type the identical string into <b>Confirm Password</b>.<br/>"
        "6. Click <b>OK</b> to close the administrator dialog."
    )
    step6_crit = "This action updates the admin password inside the Candidate Configuration buffer BEFORE it is committed to production."
    story.append(create_gui_card("6", "Pre-Commit Administrator Password Reset", step6_text, step6_crit))
    story.append(Spacer(1, 5))

    # STEP 7
    step7_text = (
        "1. Click the blue <b>Commit</b> button located at the extreme top-right corner of the Web GUI screen.<br/>"
        "2. In the <i>Commit</i> verification window, click <b>Commit</b>.<br/>"
        "3. Monitor the commit progress bar as PAN-OS compiles and validates the configuration.<br/>"
        "4. Once the commit job reaches <b>100% (Success)</b>, close the dialog.<br/>"
        "5. <b>Verification:</b> Log out of the Web GUI and verify that you can authenticate successfully using <b>admin</b> and your <b>NEW password</b>."
    )
    story.append(create_gui_card("7", "Execute Permanent Commit & Authentication Validation", step7_text))
    story.append(Spacer(1, 8))

    # SECTION 4: CLI RECOVERY ALTERNATIVE
    story.append(Paragraph("4. Alternative PAN-OS CLI Commands (For Headless / Terminal Engineers)", h1_style))
    story.append(Paragraph(
        "For network engineers operating strictly via SSH or serial console after Phase 3, the exact equivalent CLI commands to perform Steps 4 through 7 are:",
        body_style
    ))

    cmd_cli_rec = """# 1. Enter Configuration Mode:
admin@PA-VM> configure

# 2. Load the automatically saved production backup into candidate buffer:
admin@PA-VM# load config from config.xml.backup

# 3. Immediately overwrite the admin password in the candidate buffer (DO NOT COMMIT YET):
admin@PA-VM# set mgt-config users admin password
Enter password:  <TypeYourNewPassword123!>
Confirm password: <TypeYourNewPassword123!>

# 4. Commit candidate configuration to activate all policies and the new password:
admin@PA-VM# commit

# 5. Exit configuration mode and verify active sessions and administrators:
admin@PA-VM# exit
admin@PA-VM> show admins all
admin@PA-VM> show system info"""
    story.append(create_code_block(cmd_cli_rec))
    story.append(Spacer(1, 8))

    # SECTION 5: CRITICAL GOTCHAS & TROUBLESHOOTING
    story.append(Paragraph("5. Critical Pitfalls & Operational Safety Matrix", h1_style))

    trouble_data = [
        [Paragraph("Failure Condition", table_header), Paragraph("Underlying Cause", table_header), Paragraph("Immediate Remediation Action", table_header)],
        [
            Paragraph("Immediate Re-Lockout", table_cell_bold),
            Paragraph("Engineer clicked <b>Commit</b> right after loading <code>config.xml.backup</code> without changing password first.", table_cell),
            Paragraph("Re-execute from Phase 1. Maintenance Mode will still preserve your latest configuration as a backup.", table_cell)
        ],
        [
            Paragraph("Commit Failed (Complexity)", table_cell_bold),
            Paragraph("New password does not meet PAN-OS minimum complexity requirements (length, character classes).", table_cell),
            Paragraph("Ensure password has at least 8 characters, 1 uppercase, 1 lowercase, 1 digit, and 1 special character.", table_cell)
        ],
        [
            Paragraph("Web GUI Unreachable after Reboot", table_cell_bold),
            Paragraph("Old restored snapshot had a different management IP (e.g. <code>192.168.1.1</code> instead of <code>172.17.0.50</code>).", table_cell),
            Paragraph("Connect via console, check IP with <code>show interface management</code>, or re-assign with <code>set deviceconfig system ip-address ...</code>.", table_cell)
        ],
        [
            Paragraph("Missed 'maint' Prompt", table_cell_bold),
            Paragraph("Failed to type <code>maint</code> within 5-second countdown on serial console.", table_cell),
            Paragraph("Reboot firewall again via console. Keep cursor active and type <code>maint</code> repeatedly as kernel initializes.", table_cell)
        ],
    ]
    trouble_table = Table(trouble_data, colWidths=[1.6 * inch, 2.6 * inch, 2.8 * inch])
    trouble_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), accent_red),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(trouble_table)
    story.append(Spacer(1, 10))

    # FINAL CALLOUT BOX
    final_box = (
        "<b>Zero-Data-Loss Guarantee:</b> By executing this runbook, no Security Policies, NAT rules, Zones, or VPN tunnels are discarded. "
        "The PAN-OS engine seamlessly transitions from the emergency recovery configuration back to full enterprise production status."
    )
    story.append(create_callout(final_box, title="ENGINEERING CERTIFICATION & COMPLIANCE", border_c=accent_green, bg_c=colors.HexColor("#F0FFF4")))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {output_pdf}")

if __name__ == "__main__":
    output_filename = "Palo_Alto_Password_Recovery_Guide.pdf"
    build_pdf(output_filename)
