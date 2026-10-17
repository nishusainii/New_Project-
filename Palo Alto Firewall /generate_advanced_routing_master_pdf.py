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
            self.drawString(44, 11 * inch - 36, "Palo Alto Networks PAN-OS — Complete 72-Topic Advanced Routing Master Curriculum")
            self.setFont("Helvetica", 8)
            self.drawRightString(8.5 * inch - 44, 11 * inch - 36, "CLI, GUI, Concept & Examples | Oct 2026")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(44, 11 * inch - 42, 8.5 * inch - 44, 11 * inch - 42)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(44, 38, 8.5 * inch - 44, 38)
        
        self.setFont("Helvetica", 8)
        self.drawString(44, 26, "Confidential — Enterprise Routing Architecture & PCNSE Certification Manual | Prepared by Nishu Saini")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 44, 26, page_str)
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
    accent_green = colors.HexColor("#276749")    # Forest green
    dark_neutral = colors.HexColor("#2D3748")    # Charcoal body text
    code_bg = colors.HexColor("#1A202C")         # Dark slate code background
    code_text = colors.HexColor("#E2E8F0")       # Light code font
    border_color = colors.HexColor("#CBD5E0")

    title_style = ParagraphStyle(
        'DocTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=16, leading=20,
        textColor=primary_color, spaceAfter=2
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=8.5, leading=11.5,
        textColor=secondary_color, spaceAfter=6
    )

    h1_style = ParagraphStyle(
        'H1', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=11, leading=14,
        textColor=primary_color, spaceBefore=8, spaceAfter=3, keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9.0, leading=12,
        textColor=secondary_color, spaceBefore=6, spaceAfter=2, keepWithNext=True
    )

    topic_title_style = ParagraphStyle(
        'TopicTitle', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=8.5, leading=11,
        textColor=primary_color, spaceBefore=6, spaceAfter=2, keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.5, leading=10,
        textColor=dark_neutral, spaceAfter=2
    )

    concept_style = ParagraphStyle(
        'Concept', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.2, leading=9.5,
        textColor=dark_neutral
    )

    example_style = ParagraphStyle(
        'Example', parent=styles['Normal'],
        fontName='Helvetica-Oblique', fontSize=7.2, leading=9.5,
        textColor=colors.HexColor("#2C5282")
    )

    callout_style = ParagraphStyle(
        'Callout', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.2, leading=9.5,
        textColor=dark_neutral
    )

    table_header = ParagraphStyle(
        'TableHeader', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=7.2, leading=9.2,
        textColor=colors.white
    )

    table_cell = ParagraphStyle(
        'TableCell', parent=styles['Normal'],
        fontName='Helvetica', fontSize=7.0, leading=9.0,
        textColor=dark_neutral
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=7.0, leading=9.0,
        textColor=dark_neutral
    )

    def create_code_block(code_str):
        p = Preformatted(
            code_str,
            ParagraphStyle(
                'PreformattedCode',
                fontName='Courier',
                fontSize=6.8,
                leading=8.5,
                textColor=code_text
            )
        )
        t = Table([[p]], colWidths=[7.28 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), code_bg),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#4A5568")),
        ]))
        return t

    def create_gui_box(gui_text):
        p = Paragraph(f"<b>Web GUI Step-by-Step Navigation:</b><br/>{gui_text}", callout_style)
        t = Table([[p]], colWidths=[7.28 * inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FFF4")),
            ('TOPPADDING', (0,0), (-1,-1), 3.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
            ('LEFTPADDING', (0,0), (-1,-1), 7),
            ('RIGHTPADDING', (0,0), (-1,-1), 7),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#9AE6B4")),
            ('LINELEFT', (0,0), (0,-1), 3.0, accent_green)
        ]))
        return t

    def render_topic(topic_num, title, meaning, example, cli_commands, gui_steps):
        flowables = []
        flowables.append(Paragraph(f"<b>Topic {topic_num}: {title}</b>", topic_title_style))
        flowables.append(Paragraph(f"<b>📖 Meaning &amp; Architectural Concept:</b> {meaning}", concept_style))
        flowables.append(Spacer(1, 1))
        flowables.append(Paragraph(f"<b>💡 Concrete Real-World Example:</b> {example}", example_style))
        flowables.append(Spacer(1, 1))
        flowables.append(create_code_block(cli_commands))
        flowables.append(Spacer(1, 2))
        flowables.append(create_gui_box(gui_steps))
        flowables.append(Spacer(1, 5))
        return flowables

    story = []

    # TITLE & HEADER
    story.append(Paragraph("Palo Alto Networks PAN-OS — Advanced Routing &amp; Configuration Master Guide", title_style))
    story.append(Paragraph(
        "Complete 72-Topic Engineering Field Manual: Detailed Technical Meanings, Concrete Real-World Examples, PAN-OS CLI Syntax, and Web GUI Step-by-Step Paths across IPv4/IPv6 Static, RIP, OSPF, BGP, Path Monitoring, and Multi-Area Topologies",
        subtitle_style
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=6, spaceBefore=0))

    # METADATA BLOCK
    meta_data = [
        [Paragraph("Document ID:", table_cell_bold), Paragraph("PAN-ENG-ROUTING-72", table_cell), Paragraph("Platform Support:", table_cell_bold), Paragraph("PA-220 / 400 / 800 / 3200 / 5200 / PA-VM", table_cell)],
        [Paragraph("Target OS Train:", table_cell_bold), Paragraph("PAN-OS 9.1 / 10.x / 11.x (Virtual Router)", table_cell), Paragraph("Routing Protocols:", table_cell_bold), Paragraph("Static, RIPv2, OSPFv2, BGPv4, IPv6 OSPFv3, MP-BGP", table_cell)],
        [Paragraph("Scope:", table_cell_bold), Paragraph("Enterprise Production &amp; PCNSE Certification", table_cell), Paragraph("Lead Engineer:", table_cell_bold), Paragraph("Nishu Saini (Innspark Solutions)", table_cell)],
    ]
    meta_table = Table(meta_data, colWidths=[1.3 * inch, 2.2 * inch, 1.4 * inch, 2.38 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F7FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # Import topics database
    import topics_data
    all_topics = topics_data.get_all_72_topics()

    current_module = ""
    for item in all_topics:
        mod_name = item['module']
        if mod_name != current_module:
            current_module = mod_name
            story.append(Paragraph(current_module, h1_style))
            story.append(Spacer(1, 2))

        story.extend(render_topic(
            item['num'],
            item['title'],
            item['meaning'],
            item['example'],
            item['cli'],
            item['gui']
        ))

    # FINAL COMPLIANCE CALLOUT
    story.append(Spacer(1, 8))
    final_card = (
        "<b>Architectural Certification Sign-Off:</b> This manual covers all 72 routing modules required for production data center deployments "
        "and Palo Alto Networks PCNSA / PCNSE professional certifications. Every command, technical concept, and GUI navigation path adheres to the PAN-OS Virtual Router "
        "standards across standalone, High Availability, and multi-tenant Virtual System (vsys) topologies."
    )
    callout_p = Paragraph(f"<b>ENGINEERING STANDARDS &amp; CURRICULUM COMPLIANCE</b><br/>{final_card}", callout_style)
    callout_t = Table([[callout_p]], colWidths=[7.28 * inch])
    callout_t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FFF4")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#9AE6B4")),
        ('LINELEFT', (0,0), (0,-1), 3.0, accent_green)
    ]))
    story.append(callout_t)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {output_pdf}")

if __name__ == "__main__":
    output_filename = "PDF_Documentation/03_Lab_Configuration_Manuals/Palo_Alto_Advanced_Routing_Master_Guide.pdf"
    build_pdf(output_filename)
