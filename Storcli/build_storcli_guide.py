import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable
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
        
        header_line_color = colors.HexColor("#CBD5E1")
        footer_line_color = colors.HexColor("#CBD5E1")
        text_muted = colors.HexColor("#64748B")
        
        # Header on pages > 1
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#0F2942"))
            self.drawString(36, 756, "StorCLI Complete Engineering Reference & Administration Manual")
            self.setFont("Helvetica", 8)
            self.setFillColor(text_muted)
            self.drawRightString(576, 756, "LSI / Broadcom MegaRAID")
            self.setStrokeColor(header_line_color)
            self.setLineWidth(0.75)
            self.line(36, 748, 576, 748)

        # Footer on all pages
        self.setStrokeColor(footer_line_color)
        self.setLineWidth(0.75)
        self.line(36, 38, 576, 38)
        
        self.setFont("Helvetica", 7.5)
        self.setFillColor(text_muted)
        self.drawString(36, 26, "Hardware RAID, Controller, Environmental & Disk Health Diagnostics Manual")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 26, page_text)
        
        self.restoreState()


def create_storcli_pdf(output_filename):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    PRIMARY = colors.HexColor("#0F2942")     # Deep Navy
    SECONDARY = colors.HexColor("#0284C7")   # Sky Blue
    ACCENT_BG = colors.HexColor("#F8FAFC")   # Ultra light background
    BORDER_COLOR = colors.HexColor("#CBD5E1")
    
    ALERT_BG = colors.HexColor("#FEF2F2")
    ALERT_BORDER = colors.HexColor("#FCA5A5")
    ALERT_TEXT = colors.HexColor("#991B1B")
    
    WARN_BG = colors.HexColor("#FFFBEB")
    WARN_BORDER = colors.HexColor("#FCD34D")
    WARN_TEXT = colors.HexColor("#92400E")
    
    TIP_BG = colors.HexColor("#F0FDF4")
    TIP_BORDER = colors.HexColor("#86EFAC")
    TIP_TEXT = colors.HexColor("#166534")

    style_title = ParagraphStyle(
        'CoverTitle',
        fontName='Helvetica-Bold',
        fontSize=19,
        leading=22,
        textColor=PRIMARY,
        spaceAfter=2
    )
    
    style_subtitle = ParagraphStyle(
        'CoverSubtitle',
        fontName='Helvetica',
        fontSize=9,
        leading=12.5,
        textColor=SECONDARY,
        spaceAfter=5
    )

    style_h1 = ParagraphStyle(
        'H1_Custom',
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13.5,
        textColor=PRIMARY,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    style_h2 = ParagraphStyle(
        'H2_Custom',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=SECONDARY,
        spaceBefore=5,
        spaceAfter=2,
        keepWithNext=True
    )

    style_body = ParagraphStyle(
        'Body_Custom',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=3
    )

    style_tbl_cell = ParagraphStyle(
        'TableCell',
        fontName='Helvetica',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor("#1E293B")
    )

    style_tbl_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Helvetica-Bold',
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor("#1E293B")
    )

    style_tbl_cmd = ParagraphStyle(
        'TableCmd',
        fontName='Courier-Bold',
        fontSize=7.2,
        leading=9,
        textColor=colors.HexColor("#0284C7")
    )

    style_tbl_header = ParagraphStyle(
        'TableHead',
        fontName='Helvetica-Bold',
        fontSize=7.8,
        leading=10,
        textColor=colors.white
    )

    def make_table(rows, widths):
        tbl = Table(rows, colWidths=widths)
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), PRIMARY),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ACCENT_BG]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('TOPPADDING', (0,0), (-1,-1), 2.2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2.2),
            ('LEFTPADDING', (0,0), (-1,-1), 4.5),
            ('RIGHTPADDING', (0,0), (-1,-1), 4.5),
        ]))
        return tbl

    def callout_box(text, box_type="warn"):
        if box_type == "alert":
            bg, border, tc, prefix = ALERT_BG, ALERT_BORDER, ALERT_TEXT, "<b>CRITICAL / WARNING: </b>"
        elif box_type == "tip":
            bg, border, tc, prefix = TIP_BG, TIP_BORDER, TIP_TEXT, "<b>PRO TIP: </b>"
        else:
            bg, border, tc, prefix = WARN_BG, WARN_BORDER, WARN_TEXT, "<b>IMPORTANT NOTE: </b>"

        st = ParagraphStyle('Callout', fontName='Helvetica', fontSize=7.2, leading=10, textColor=tc)
        tbl = Table([[Paragraph(prefix + text, st)]], colWidths=[540])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('BOX', (0,0), (-1,-1), 1, border),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 5),
            ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ]))
        return tbl

    story = []

    # =========================================================================
    # PAGE 1: Title, Syntax Hierarchy, Controller Health & Alarms
    # =========================================================================
    story.append(Paragraph("StorCLI Diagnostics & Administration Guide", style_title))
    story.append(Paragraph("Enterprise Technical Manual: MegaRAID Controllers, Physical Disk Diagnostics, Cache Tuning & Automation", style_subtitle))
    
    meta_data = [
        [
            Paragraph("<b>Utility:</b> <code>storcli</code> / <code>storcli64</code>", style_tbl_cell),
            Paragraph("<b>Target HW:</b> LSI / Broadcom SAS, SATA, NVMe MegaRAID & HBA", style_tbl_cell),
            Paragraph("<b>Platforms:</b> Linux (Debian/RHEL/Proxmox), ESXi", style_tbl_cell)
        ]
    ]
    meta_tbl = Table(meta_data, colWidths=[150, 240, 150])
    meta_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 4))

    # SECTION 1
    story.append(Paragraph("1. StorCLI Syntax, Hierarchy & Global Output Modes", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))
    story.append(Paragraph("StorCLI targets hardware hierarchically: <code>storcli /cx[/ex]/sx|vx|dx action [options]</code>.", style_body))

    st_data = [
        [Paragraph("Target Notation", style_tbl_header), Paragraph("Hardware Level & Target Scope", style_tbl_header), Paragraph("Standard Diagnostic Command Example", style_tbl_header)],
        [Paragraph("<b>/c0</b> or <b>/call</b>", style_tbl_cell_bold), Paragraph("Target specific controller (0) or all controllers", style_tbl_cell), Paragraph("<code>storcli /c0 show status</code>", style_tbl_cmd)],
        [Paragraph("<b>/e252</b> or <b>/eall</b>", style_tbl_cell_bold), Paragraph("Target backplane enclosure (e.g. Enclosure 252)", style_tbl_cell), Paragraph("<code>storcli /c0/eall show</code>", style_tbl_cmd)],
        [Paragraph("<b>/s0</b> or <b>/sall</b>", style_tbl_cell_bold), Paragraph("Target physical drive slot (e.g. Slot 0) or all slots", style_tbl_cell), Paragraph("<code>storcli /c0/e252/s0 show all</code>", style_tbl_cmd)],
        [Paragraph("<b>/v0</b> or <b>/vall</b>", style_tbl_cell_bold), Paragraph("Target Virtual Drive (RAID array) or all arrays", style_tbl_cell), Paragraph("<code>storcli /c0/v0 show all</code>", style_tbl_cmd)],
        [Paragraph("<b>/d0</b> or <b>/dall</b>", style_tbl_cell_bold), Paragraph("Target Drive Group (disk pool)", style_tbl_cell), Paragraph("<code>storcli /c0/d0 show</code>", style_tbl_cmd)],
        [Paragraph("<b>/fall</b>", style_tbl_cell_bold), Paragraph("Foreign RAID configurations across all drives", style_tbl_cell), Paragraph("<code>storcli /c0/fall show</code>", style_tbl_cmd)],
        [Paragraph("<b>/cv</b> or <b>/bbu</b>", style_tbl_cell_bold), Paragraph("CacheVault flash module or Battery Backup Unit", style_tbl_cell), Paragraph("<code>storcli /c0/cv show all</code>", style_tbl_cmd)],
    ]
    story.append(make_table(st_data, [105, 215, 220]))
    story.append(Spacer(1, 3))
    story.append(callout_box("Append <b>J</b> to any command (e.g., <code>storcli /c0 show J</code>) for clean JSON output suitable for automated Python/Bash monitoring scripts.", "tip"))
    story.append(Spacer(1, 5))

    # SECTION 2
    story.append(Paragraph("2. Controller Health, Diagnostics & Alarm Management", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))
    
    ctrl_data = [
        [Paragraph("Command", style_tbl_header), Paragraph("Diagnostic Purpose & Expected Output", style_tbl_header)],
        [Paragraph("<code>storcli show</code>", style_tbl_cmd), Paragraph("Enumerate all installed controllers, model names, PCI slots, firmware versions, and overall status.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 show status</code>", style_tbl_cmd), Paragraph("Summary controller status, memory size, BIOS/firmware versions, and BBU status.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 show health</code>", style_tbl_cmd), Paragraph("Displays controller operational health (Healthy, Degraded, Failed) and fault conditions.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 show all</code>", style_tbl_cmd), Paragraph("Comprehensive controller dump: ROC temperature, memory error counts, PHY errors, PCIe link speed.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 show events filter=warning,error,critical</code>", style_tbl_cmd), Paragraph("Inspect filtered event log: captures disk dropouts, rebuild events, parity errors, and bus resets.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 show termlog</code>", style_tbl_cmd), Paragraph("Displays live firmware terminal boot/runtime diagnostics log (essential for controller crash debugging).", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 show alarms</code>", style_tbl_cmd), Paragraph("Check status of the physical hardware audible chassis alarm buzzer.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 set alarm=silence</code>", style_tbl_cmd), Paragraph("Mutes / silences the active sounding hardware buzzer during an ongoing drive failure.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 set alarm=off</code>", style_tbl_cmd), Paragraph("Permanently disables the controller audible alarm buzzer.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0 flushcache</code>", style_tbl_cmd), Paragraph("Flushes dirty cache blocks to disk before shutdown or maintenance.", style_tbl_cell)],
    ]
    story.append(make_table(ctrl_data, [205, 335]))

    # PAGE BREAK TO PAGE 2
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: Physical Disk Diagnostics, Errors, LED & Drive States
    # =========================================================================
    story.append(Paragraph("3. Physical Disk Diagnostics, Error Counters & SMART Health", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))
    story.append(Paragraph("Physical disk diagnostics must be evaluated regularly to detect bad sectors and prevent multi-drive failures.", style_body))

    pd_data = [
        [Paragraph("Command", style_tbl_header), Paragraph("Operational Function", style_tbl_header), Paragraph("Key Diagnostic Output", style_tbl_header)],
        [Paragraph("<code>storcli /c0/eall/sall show</code>", style_tbl_cmd), Paragraph("List all physical drives across all slots", style_tbl_cell), Paragraph("State (Onln, UGood, UBad, Failed), Type, Capacity.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0/eX/sX show all</code>", style_tbl_cmd), Paragraph("Detailed diagnostic page for drive in Encl X, Slot X", style_tbl_cell), Paragraph("Media/Other error counters, SMART alerts, Temp, SN.", style_tbl_cell)],
        [Paragraph("<code>storcli /c0/eX/sX show smart</code>", style_tbl_cmd), Paragraph("Query drive internal SMART attributes", style_tbl_cell), Paragraph("SMART Alert Trip: <b>No</b> (Healthy) / <b>Yes</b> (Failing).", style_tbl_cell)],
        [Paragraph("<code>storcli /c0/eX/sX show error</code>", style_tbl_cmd), Paragraph("Display hardware error statistics recorded by firmware", style_tbl_cell), Paragraph("Media Error Count, Other Error Count, Predictive Fail.", style_tbl_cell)],
    ]
    story.append(make_table(pd_data, [165, 185, 190]))
    story.append(Spacer(1, 4))

    pd_metric_data = [
        [Paragraph("Diagnostic Counter", style_tbl_header), Paragraph("Threshold", style_tbl_header), Paragraph("Meaning & Recommended Engineering Action", style_tbl_header)],
        [
            Paragraph("<b>Media Error Count</b>", style_tbl_cell_bold),
            Paragraph("<b>0</b>", style_tbl_cell),
            Paragraph("Uncorrectable bad sectors on disk media. Any value &gt; 0 indicates surface degradation. Schedule replacement.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Other Error Count</b>", style_tbl_cell_bold),
            Paragraph("<b>0</b>", style_tbl_cell),
            Paragraph("Communication errors between drive & backplane (SAS PHY CRC errors, bad slot, or cabling noise).", style_tbl_cell)
        ],
        [
            Paragraph("<b>Predictive Failure Count</b>", style_tbl_cell_bold),
            Paragraph("<b>0</b>", style_tbl_cell),
            Paragraph("SMART internal algorithms indicate imminent disk crash. Replace drive immediately before array breaks.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Drive Temperature</b>", style_tbl_cell_bold),
            Paragraph("&lt; 50°C", style_tbl_cell),
            Paragraph("Operating temperature. Temperatures sustained &gt; 55°C degrade flash/bearings and require cooling review.", style_tbl_cell)
        ],
    ]
    story.append(make_table(pd_metric_data, [125, 60, 355]))
    story.append(Spacer(1, 6))

    # SECTION 4
    story.append(Paragraph("4. Physical Drive Identification (LED), Slot States & Modes", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    state_data = [
        [Paragraph("Task / Action", style_tbl_header), Paragraph("Command Syntax", style_tbl_header), Paragraph("Operational Function & Safety Note", style_tbl_header)],
        [
            Paragraph("<b>Blink Drive LED (Locate)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX start locate</code>", style_tbl_cmd),
            Paragraph("Flashes drive tray LED to physically identify the target disk in server chassis.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Stop Blinking LED</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX stop locate</code>", style_tbl_cmd),
            Paragraph("Stops flashing locator LED once disk is identified.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Set Drive Offline</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX set offline</code>", style_tbl_cmd),
            Paragraph("Safely unmounts and isolates drive from active RAID array before physical extraction.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Mark Drive Missing</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX set missing</code>", style_tbl_cmd),
            Paragraph("Marks offline slot as missing so array can prepare for replacement insertion.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Spin Down (Safe Removal)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX spin down</code>", style_tbl_cmd),
            Paragraph("Parks disk actuator arms and spins down spindle before hot-pulling.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Fix Unconfigured Bad</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX set good [force]</code>", style_tbl_cmd),
            Paragraph("Transitions drive from <b>UBad</b> (Unconfigured Bad) to <b>UGood</b> (Unconfigured Good).", style_tbl_cell)
        ],
        [
            Paragraph("<b>Set Pass-Through (JBOD)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX set jbod</code>", style_tbl_cmd),
            Paragraph("Sets drive to raw pass-through mode (required for ZFS, Ceph, and software-defined storage).", style_tbl_cell)
        ],
        [
            Paragraph("<b>Set RAID Mode (Good)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX set good</code>", style_tbl_cmd),
            Paragraph("Reverts JBOD drive to Unconfigured Good state for RAID array assignment.", style_tbl_cell)
        ],
    ]
    story.append(make_table(state_data, [135, 195, 210]))

    # PAGE BREAK TO PAGE 3
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: Virtual Drives, RAID Recipes, Hot Spares & Foreign Configurations
    # =========================================================================
    story.append(Paragraph("5. Virtual Drive (VD) Diagnostics & Array Operations", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    vd_data = [
        [Paragraph("Action", style_tbl_header), Paragraph("Command Syntax", style_tbl_header), Paragraph("Description & Details", style_tbl_header)],
        [
            Paragraph("<b>List All Virtual Drives</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/vall show</code>", style_tbl_cmd),
            Paragraph("Summary table: VD ID, RAID Type, State (Optl, Dgrd, PdFail), Total Size, Cache Policy.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Deep VD Diagnostics</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 show all</code>", style_tbl_cmd),
            Paragraph("Stripe size, Bad Blocks Table presence, Read/Write Policy (WB/WT), Access policy (RW/RO).", style_tbl_cell)
        ],
        [
            Paragraph("<b>Start Consistency Check (CC)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 start cc</code>", style_tbl_cmd),
            Paragraph("Scans parity data across array and fixes silent corruption. Crucial monthly maintenance.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Monitor CC Progress</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 show cc</code>", style_tbl_cmd),
            Paragraph("Shows % completed and estimated time remaining for consistency check.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Start VD Initialization</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 start init [full]</code>", style_tbl_cmd),
            Paragraph("Initializes new virtual drive. Fast init by default; full init writes zeros to entire array.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Delete Virtual Drive</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 del [force]</code>", style_tbl_cmd),
            Paragraph("Destroys virtual drive volume (ALL DATA PERMANENTLY ERASED).", style_tbl_cell)
        ],
    ]
    story.append(make_table(vd_data, [135, 195, 210]))
    story.append(Spacer(1, 4))

    raid_create_data = [
        [Paragraph("Target RAID Configuration", style_tbl_header), Paragraph("Creation Command Syntax (Direct, WriteBack, ReadAhead)", style_tbl_header)],
        [Paragraph("<b>RAID 0 (Stripe)</b>", style_tbl_cell_bold), Paragraph("<code>storcli /c0 add vd type=raid0 drives=252:0,252:1 [Direct] [WB] [ra]</code>", style_tbl_cmd)],
        [Paragraph("<b>RAID 1 (Mirror)</b>", style_tbl_cell_bold), Paragraph("<code>storcli /c0 add vd type=raid1 drives=252:0,252:1</code>", style_tbl_cmd)],
        [Paragraph("<b>RAID 5 (Single Parity)</b>", style_tbl_cell_bold), Paragraph("<code>storcli /c0 add vd type=raid5 drives=252:0-4 pdperarray=5</code>", style_tbl_cmd)],
        [Paragraph("<b>RAID 6 (Dual Parity)</b>", style_tbl_cell_bold), Paragraph("<code>storcli /c0 add vd type=raid6 drives=252:0-5 pdperarray=6</code>", style_tbl_cmd)],
        [Paragraph("<b>RAID 10 (Striped Mirror)</b>", style_tbl_cell_bold), Paragraph("<code>storcli /c0 add vd type=raid10 drives=252:0-3 pdperarray=2</code>", style_tbl_cmd)],
    ]
    story.append(make_table(raid_create_data, [140, 400]))
    story.append(Spacer(1, 6))

    # SECTION 6
    story.append(Paragraph("6. Hot Spares & Rebuild Management", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    rb_data = [
        [Paragraph("Operation", style_tbl_header), Paragraph("Command", style_tbl_header), Paragraph("Details & Engineering Notes", style_tbl_header)],
        [
            Paragraph("<b>Assign Global Hot Spare</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/e252/s4 add hotsparedrive</code>", style_tbl_cmd),
            Paragraph("Designates standby spare for any degraded RAID array on controller 0.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Assign Dedicated Hot Spare</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/e252/s4 add hotsparedrive dgv=0</code>", style_tbl_cmd),
            Paragraph("Binds spare drive exclusively to Drive Group 0.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Start Manual Rebuild</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/e252/s1 start rebuild</code>", style_tbl_cmd),
            Paragraph("Initiates RAID parity reconstruction onto replacement drive in Slot 1.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Monitor Rebuild Progress</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/e252/s1 show rebuild</code>", style_tbl_cmd),
            Paragraph("Displays rebuild % completion, elapsed time, and ETA.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Set Rebuild Priority Rate</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0 set rebuildrate=40</code>", style_tbl_cmd),
            Paragraph("Sets rebuild bandwidth percentage (1-100%). Default is 30%.", style_tbl_cell)
        ],
    ]
    story.append(make_table(rb_data, [135, 195, 210]))
    story.append(Spacer(1, 6))

    # SECTION 7
    story.append(Paragraph("7. Foreign Configuration Diagnostics & Array Migration", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    foreign_data = [
        [Paragraph("Step / Action", style_tbl_header), Paragraph("Command Syntax", style_tbl_header), Paragraph("Impact & Recovery Procedure", style_tbl_header)],
        [
            Paragraph("<b>1. Detect Foreign Arrays</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/fall show</code>", style_tbl_cmd),
            Paragraph("Scans all slots and reports any drives holding foreign RAID metadata.", style_tbl_cell)
        ],
        [
            Paragraph("<b>2. Preview Foreign Layout</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/fall preview</code>", style_tbl_cmd),
            Paragraph("Simulates what virtual drives will be reconstructed before committing import.", style_tbl_cell)
        ],
        [
            Paragraph("<b>3. Import Foreign Array</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/fall import</code>", style_tbl_cmd),
            Paragraph("<b>DATA RECOVERY:</b> Imports foreign metadata and restores access to the Virtual Drives.", style_tbl_cell)
        ],
        [
            Paragraph("<b>4. Clear Foreign Metadata</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/fall clear</code>", style_tbl_cmd),
            Paragraph("<b>WIPES RAID HEADER:</b> Erases foreign metadata to reuse the disks as fresh spares.", style_tbl_cell)
        ],
    ]
    story.append(make_table(foreign_data, [135, 195, 210]))

    # PAGE BREAK TO PAGE 4
    story.append(PageBreak())

    # =========================================================================
    # PAGE 4: Advanced Cache Tuning, Capacity Expansion, Disk Sanitization & Environmental
    # =========================================================================
    story.append(Paragraph("8. Advanced Cache Policy Tuning & Performance Optimization", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))
    story.append(Paragraph("Tuning controller cache algorithms maximizes IOPS and throughput while ensuring data safety.", style_body))

    cache_data = [
        [Paragraph("Cache Setting", style_tbl_header), Paragraph("Command Syntax", style_tbl_header), Paragraph("Performance & Safety Trade-off", style_tbl_header)],
        [
            Paragraph("<b>Write-Back Cache</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 set wrcache=WB</code>", style_tbl_cmd),
            Paragraph("Writes acknowledge immediately in controller RAM. Maximum performance (Requires BBU/CV).", style_tbl_cell)
        ],
        [
            Paragraph("<b>Write-Through Cache</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 set wrcache=WT</code>", style_tbl_cmd),
            Paragraph("Writes acknowledge only after reaching physical disk. Safe without BBU, slower write speed.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Read Ahead (RA)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 set rdcache=RA</code>", style_tbl_cmd),
            Paragraph("Reads sequential blocks into controller cache. Accelerates sequential streaming read workloads.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Direct / Cached I/O</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 set iopolicy=Direct</code>", style_tbl_cmd),
            Paragraph("<b>Direct:</b> Bypasses cache buffer for random small blocks. <b>Cached:</b> Buffers all reads in RAM.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Disk On-Board Cache</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 set pdcache=on|off</code>", style_tbl_cmd),
            Paragraph("Enables/Disables drive internal volatile RAM cache. Must be OFF unless protected by UPS.", style_tbl_cell)
        ],
    ]
    story.append(make_table(cache_data, [135, 195, 210]))
    story.append(Spacer(1, 6))

    # SECTION 9: OCE & Disk Sanitization
    story.append(Paragraph("9. Online Expansion, RAID Migration & Secure Disk Sanitization", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    adv_data = [
        [Paragraph("Operation", style_tbl_header), Paragraph("Command Syntax", style_tbl_header), Paragraph("Operational Function", style_tbl_header)],
        [
            Paragraph("<b>Online Capacity Expansion</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 expand size=500</code>", style_tbl_cmd),
            Paragraph("Expands virtual drive size live by 500GB without taking array offline.", style_tbl_cell)
        ],
        [
            Paragraph("<b>RAID Level Migration (RLM)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 start migrate type=raid5 option=add drives=252:2</code>", style_tbl_cmd),
            Paragraph("Converts RAID 1 to RAID 5 live by adding disk 252:2 on the fly.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Monitor Migration Progress</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 show migrate</code>", style_tbl_cmd),
            Paragraph("Displays live % progress for RAID Level Migration or OCE expansion.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Instant Crypto Erase (SED)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX start erase crypto</code>", style_tbl_cmd),
            Paragraph("Cryptographically wipes Self-Encrypting Drive (SED) instantaneously.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Full Zero Wipe / Sanitize</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX start erase thorough</code>", style_tbl_cmd),
            Paragraph("Overwrites disk sectors with patterns for secure decommissioning (DoD compliant).", style_tbl_cell)
        ],
        [
            Paragraph("<b>Monitor Erase Progress</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eX/sX show erase</code>", style_tbl_cmd),
            Paragraph("Displays disk zero-wipe % progress and estimated completion time.", style_tbl_cell)
        ],
    ]
    story.append(make_table(adv_data, [135, 205, 200]))
    story.append(Spacer(1, 6))

    # SECTION 10: Environmental & Config Backup
    story.append(Paragraph("10. Enclosure Environmental Monitoring & Config Backups", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    env_data = [
        [Paragraph("Feature / Task", style_tbl_header), Paragraph("Command Syntax", style_tbl_header), Paragraph("Diagnostic Purpose", style_tbl_header)],
        [
            Paragraph("<b>Enclosure Sensor Temps</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eall show temp</code>", style_tbl_cmd),
            Paragraph("Displays backplane temperature sensors and overheating alerts.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Backplane Fan RPMs</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eall show fan</code>", style_tbl_cmd),
            Paragraph("Monitors cooling fan tachometers and detects failed fan modules.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Power Supply Status (PSU)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/eall show psu</code>", style_tbl_cmd),
            Paragraph("Displays redundant power supply AC input health and failure alerts.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Backup Controller Config</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0 dump file=ctrl0_backup.xml</code>", style_tbl_cmd),
            Paragraph("Exports entire RAID configuration and drive mappings to XML backup.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Restore Controller Config</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0 restore file=ctrl0_backup.xml</code>", style_tbl_cmd),
            Paragraph("Restores array settings onto a replacement controller card.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Set System Boot Drive</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/v0 set bootdrive=on</code>", style_tbl_cmd),
            Paragraph("Configures Virtual Drive 0 as primary BIOS boot volume.", style_tbl_cell)
        ],
    ]
    story.append(make_table(env_data, [135, 205, 200]))

    # PAGE BREAK TO PAGE 5
    story.append(PageBreak())

    # =========================================================================
    # PAGE 5: Patrol Read & BBU, Runbooks, Automation Script & State Reference
    # =========================================================================
    story.append(Paragraph("11. Patrol Read & CacheVault / Battery Backup (BBU)", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    pr_bbu_data = [
        [Paragraph("Component", style_tbl_header), Paragraph("Command", style_tbl_header), Paragraph("Purpose & Maintenance Practice", style_tbl_header)],
        [
            Paragraph("<b>Patrol Read Status</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0 show patrolread</code>", style_tbl_cmd),
            Paragraph("Displays Patrol Read status (Active/Stopped), mode, and schedule.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Start Patrol Read</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0 start patrolread</code>", style_tbl_cmd),
            Paragraph("Forces an immediate background surface sector scan of all member physical disks.", style_tbl_cell)
        ],
        [
            Paragraph("<b>CacheVault Status (CV)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/cv show all</code>", style_tbl_cmd),
            Paragraph("Displays flash/supercapacitor state: Temperature, Voltage, Learn cycle, SOH.", style_tbl_cell)
        ],
        [
            Paragraph("<b>BBU Status (Battery)</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/bbu show all</code>", style_tbl_cmd),
            Paragraph("Displays battery charge level, replacement flags, and calibration health.", style_tbl_cell)
        ],
        [
            Paragraph("<b>Start BBU Learn Cycle</b>", style_tbl_cell_bold),
            Paragraph("<code>storcli /c0/bbu start learn</code>", style_tbl_cmd),
            Paragraph("Calibrates battery capacity. (Note: Controller drops to Write-Through cache during learn).", style_tbl_cell)
        ],
    ]
    story.append(make_table(pr_bbu_data, [130, 200, 210]))
    story.append(Spacer(1, 5))

    # SECTION 12: Incident Response Runbooks
    story.append(Paragraph("12. Incident Response & Troubleshooting Runbooks", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    story.append(Paragraph("Runbook A: Replacing a Failed Drive in a Degraded Array", style_h2))
    rb1_steps = (
        "<b>1. Identify failed disk slot:</b> <code>storcli /c0/eall/sall show</code> (Look for <code>Failed</code> or <code>UBad</code>)<br/>"
        "<b>2. Blink chassis LED:</b> <code>storcli /c0/e252/s2 start locate</code> &nbsp;|&nbsp; <b>3. Pull bad disk and insert replacement</b><br/>"
        "<b>4. Stop locator LED:</b> <code>storcli /c0/e252/s2 stop locate</code> &nbsp;|&nbsp; <b>5. If UBad:</b> <code>storcli /c0/e252/s2 set good force</code><br/>"
        "<b>6. If Foreign:</b> <code>storcli /c0/fall clear</code> &nbsp;|&nbsp; <b>7. Start rebuild:</b> <code>storcli /c0/e252/s2 start rebuild</code> &nbsp;|&nbsp; <b>8. Monitor:</b> <code>storcli /c0/e252/s2 show rebuild</code>"
    )
    story.append(Table([[Paragraph(rb1_steps, style_body)]], colWidths=[540], style=[
        ('BACKGROUND', (0,0), (-1,-1), ACCENT_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Runbook B: Proactive Replacement on Predictive Failure (PdFail)", style_h2))
    rb2_steps = (
        "<b>1. Locate drive:</b> <code>storcli /c0/eall/sall show</code> (State: <code>PdFail</code>) &nbsp;|&nbsp; <b>2. Take offline:</b> <code>storcli /c0/e252/s1 set offline</code><br/>"
        "<b>3. Mark missing:</b> <code>storcli /c0/e252/s1 set missing</code> &nbsp;|&nbsp; <b>4. Spin down:</b> <code>storcli /c0/e252/s1 spin down</code><br/>"
        "<b>5. Physical replacement</b> &nbsp;|&nbsp; <b>6. Set Good:</b> <code>storcli /c0/e252/s1 set good force</code> &nbsp;|&nbsp; <b>7. Start Rebuild:</b> <code>storcli /c0/e252/s1 start rebuild</code>"
    )
    story.append(Table([[Paragraph(rb2_steps, style_body)]], colWidths=[540], style=[
        ('BACKGROUND', (0,0), (-1,-1), ACCENT_BG),
        ('BOX', (0,0), (-1,-1), 1, BORDER_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(Spacer(1, 5))

    # SECTION 13: Automation Script
    story.append(Paragraph("13. Automated Health Audit Script (storcli_admin_diag.sh)", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))
    script_info = (
        "An automated administration & diagnostics tool is included in this repository: <code>storcli_admin_diag.sh</code>.<br/>"
        "• <b>Run interactive management menu:</b> <code>sudo ./storcli_admin_diag.sh</code><br/>"
        "• <b>Automated cron health audit:</b> <code>sudo ./storcli_admin_diag.sh --audit</code> (Generates timestamped log in <code>./storcli_reports/</code>)<br/>"
        "• <b>Chassis drive locate:</b> <code>sudo ./storcli_admin_diag.sh --locate 0 252 1</code> &nbsp;|&nbsp; <b>Silence alarm:</b> <code>sudo ./storcli_admin_diag.sh --silence 0</code>"
    )
    story.append(Table([[Paragraph(script_info, style_body)]], colWidths=[540], style=[
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FDF4")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#86EFAC")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(Spacer(1, 5))

    # SECTION 14: State Acronyms
    story.append(Paragraph("14. State Acronyms & Diagnostic Status Reference", style_h1))
    story.append(HRFlowable(width="100%", thickness=1, color=PRIMARY, spaceBefore=1, spaceAfter=4))

    acronym_data = [
        [Paragraph("Code", style_tbl_header), Paragraph("Full Name", style_tbl_header), Paragraph("Severity", style_tbl_header), Paragraph("Meaning & Required Engineering Action", style_tbl_header)],
        [Paragraph("<b>Onln</b>", style_tbl_cell_bold), Paragraph("Online", style_tbl_cell), Paragraph("NORMAL", style_tbl_cell_bold), Paragraph("Physical drive is functioning normally within a Virtual Drive.", style_tbl_cell)],
        [Paragraph("<b>Optl</b>", style_tbl_cell_bold), Paragraph("Optimal", style_tbl_cell), Paragraph("NORMAL", style_tbl_cell_bold), Paragraph("Virtual drive has all member disks healthy with full redundancy.", style_tbl_cell)],
        [Paragraph("<b>UGood</b>", style_tbl_cell_bold), Paragraph("Unconfigured Good", style_tbl_cell), Paragraph("STANDBY", style_tbl_cell_bold), Paragraph("Healthy drive not part of any array; ready for allocation/spare.", style_tbl_cell)],
        [Paragraph("<b>UBad</b>", style_tbl_cell_bold), Paragraph("Unconfigured Bad", style_tbl_cell), Paragraph("ERROR", style_tbl_cell_bold), Paragraph("Drive has errors or unrecognized config. Run <code>set good force</code>.", style_tbl_cell)],
        [Paragraph("<b>Dgrd</b>", style_tbl_cell_bold), Paragraph("Degraded", style_tbl_cell), Paragraph("WARNING", style_tbl_cell_bold), Paragraph("Virtual drive has 1+ failed drives. Operating on parity. Rebuild ASAP.", style_tbl_cell)],
        [Paragraph("<b>PdFail</b>", style_tbl_cell_bold), Paragraph("Predictive Failure", style_tbl_cell), Paragraph("WARNING", style_tbl_cell_bold), Paragraph("SMART error threshold exceeded. Replace disk before fatal crash.", style_tbl_cell)],
        [Paragraph("<b>Rbld</b>", style_tbl_cell_bold), Paragraph("Rebuilding", style_tbl_cell), Paragraph("ACTIVE", style_tbl_cell_bold), Paragraph("Parity data is actively being reconstructed onto replacement disk.", style_tbl_cell)],
        [Paragraph("<b>Offln</b>", style_tbl_cell_bold), Paragraph("Offline", style_tbl_cell), Paragraph("ERROR", style_tbl_cell_bold), Paragraph("Drive or array taken offline. Virtual drive is inaccessible if offline.", style_tbl_cell)],
        [Paragraph("<b>Frgn</b>", style_tbl_cell_bold), Paragraph("Foreign", style_tbl_cell), Paragraph("NOTICE", style_tbl_cell_bold), Paragraph("Drive holds RAID metadata from another controller. Import or Clear.", style_tbl_cell)],
        [Paragraph("<b>JBOD</b>", style_tbl_cell_bold), Paragraph("Just a Bunch of Disks", style_tbl_cell), Paragraph("RAW MODE", style_tbl_cell_bold), Paragraph("Raw pass-through mode bypassing RAID engine (used for ZFS/Ceph).", style_tbl_cell)],
    ]
    story.append(make_table(acronym_data, [50, 110, 70, 310]))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {output_filename}")

if __name__ == "__main__":
    output_path = "/home/nishusaini/Desktop/Innspark/T/StorCLI_Diagnostics_and_Administration_Guide.pdf"
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
    create_storcli_pdf(output_path)
