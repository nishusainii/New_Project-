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
            self.drawString(54, 11 * inch - 36, "Palo Alto & VyOS Enterprise Network Lab — Execution Command Manual")
            self.setFont("Helvetica", 8)
            self.drawRightString(8.5 * inch - 54, 11 * inch - 36, "Date: 30-Sep-2026 | Session: 12:00 – 13:50")
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
    
    c_primary = colors.HexColor("#1A365D")   # Deep navy
    c_accent = colors.HexColor("#2B6CB0")    # Blue
    c_dark = colors.HexColor("#2D3748")      # Charcoal
    c_light_bg = colors.HexColor("#F7FAFC")  # Off white
    c_code_bg = colors.HexColor("#1A202C")   # Terminal black
    c_code_text = colors.HexColor("#68D391") # Terminal green
    c_border = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#718096"),
        spaceAfter=12
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=c_accent,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=c_dark,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_dark,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10.5,
        textColor=c_code_text
    )

    def make_code_box(code_text):
        p = Preformatted(code_text, code_style)
        t = Table([[p]], colWidths=[504])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), c_code_bg),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#2D3748")),
        ]))
        return t

    story = []

    # Title & Metadata Banner
    story.append(Paragraph("Enterprise Network Lab: Running Command Manual", title_style))
    story.append(Paragraph("Palo Alto PAN-OS • VyOS Enterprise Router • GNS3 Architecture • VPCS Clients", subtitle_style))
    
    meta_data = [
        [
            Paragraph("<b>Author / Engineer:</b> Nishu Saini", body_style),
            Paragraph("<b>Lab Target:</b> Palo-Alto-Lab", body_style),
            Paragraph("<b>Date:</b> September 30, 2026", body_style)
        ],
        [
            Paragraph("<b>Time Window:</b> 12:00 PM – 01:50 PM", body_style),
            Paragraph("<b>VyOS Version:</b> 1.5-rolling (Kea DHCP)", body_style),
            Paragraph("<b>Firewall:</b> PA-VM PAN-OS 10.x", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[168, 168, 168])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), c_light_bg),
        ('BOX', (0,0), (-1,-1), 1, c_border),
        ('INNERGRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # SECTION 1
    story.append(Paragraph("1. Host Performance & Memory Optimization Commands", h1_style))
    story.append(Paragraph("Executed on Linux host to resolve GNS3 kernel out-of-memory freeze issues by expanding virtual swap memory from 2 GB to 16 GB.", body_style))
    
    cmd_sec1 = """# 1. Inspect initial RAM & Swap footprint
free -h
vmstat -s | head -20
ps aux --sort=-%mem | head -15

# 2. Safely deactivate legacy swap file
sudo swapoff /swapfile

# 3. Allocate 16 GB high-speed swap space
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 4. Verify upgraded swap capacity (Total Virtual Memory: ~31 GB)
swapon --show
free -h"""
    story.append(make_code_box(cmd_sec1))
    story.append(Spacer(1, 10))

    # SECTION 2
    story.append(Paragraph("2. GNS3 Docker Backend & REST API Management", h1_style))
    story.append(Paragraph("Used for container daemon orchestration, project state queries, and topology link manipulation.", body_style))
    
    cmd_sec2 = """# 1. Check Docker container state and restart GNS3 backend
docker ps
docker compose up -d
docker logs --tail 25 gns3-server

# 2. Query GNS3 REST API for active projects and node inventory
curl -s http://127.0.0.1:3080/v2/version
curl -s http://127.0.0.1:3080/v2/projects
curl -s -X POST http://127.0.0.1:3080/v2/projects/700ebbc6-f5cb-4230-b2cf-2b0f57d94006/open

# 3. Disconnect erroneous links via REST API (Firewall-to-Switch cables)
# Delete PA-VM-1 ethernet1/0 <-> Switch1 e0
curl -X DELETE http://127.0.0.1:3080/v2/projects/700ebbc6-f5cb-4230-b2cf-2b0f57d94006/links/1ce3530d-2c3c-4936-a2d3-47cf28abca6f

# Delete PA-VM-1 ethernet1/1 <-> Switch2 e0
curl -X DELETE http://127.0.0.1:3080/v2/projects/700ebbc6-f5cb-4230-b2cf-2b0f57d94006/links/8fa87283-4a38-4bfb-9fff-22ea258b1eb4

# Delete Router-to-Firewall temporary cable (eth0 <-> ethernet1/3)
curl -X DELETE http://127.0.0.1:3080/v2/projects/700ebbc6-f5cb-4230-b2cf-2b0f57d94006/links/42e5e1f2-6fa1-4094-8975-ebd40a068d0e"""
    story.append(make_code_box(cmd_sec2))
    story.append(Spacer(1, 10))

    # SECTION 3
    story.append(Paragraph("3. Console Access & Port Mapping Reference", h1_style))
    story.append(Paragraph("Direct local telnet console endpoints bypassing web browser key interception (enables native Tab completion):", body_style))
    
    port_table_data = [
        ["Device Node", "Role", "Telnet Port", "Credentials", "Management / Access"],
        ["PA-VM-1", "Next-Gen Firewall", "127.0.0.1:5000", "admin / Nishu@123@", "Web GUI: https://172.17.0.50"],
        ["VyOS Router", "Enterprise Router", "127.0.0.1:5022", "vyos / vyos", "Full CLI Routing & DHCP"],
        ["PC1", "VPCS Client (LAN 1)", "127.0.0.1:5002", "No Auth", "DHCP: 192.168.10.10/24"],
        ["PC2", "VPCS Client (LAN 2)", "127.0.0.1:5004", "No Auth", "DHCP: 192.168.20.12/24"],
        ["PC8", "VPCS Client (LAN 1)", "127.0.0.1:5018", "No Auth", "Cleaned VPCS instance"]
    ]
    t_ports = Table(port_table_data, colWidths=[90, 104, 85, 105, 120])
    t_ports.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), c_accent),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, c_light_bg]),
        ('GRID', (0,0), (-1,-1), 0.5, c_border),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_ports)
    story.append(Spacer(1, 12))

    story.append(PageBreak())

    # SECTION 4
    story.append(Paragraph("4. Palo Alto Networks (PAN-OS) CLI Commands", h1_style))
    story.append(Paragraph("Operational status diagnostics and dependency-ordered configuration deletion.", body_style))
    
    cmd_sec4 = """# 1. Operational Mode Status Commands
admin@PA-VM> show interface management       # Verify MGT IP (172.17.0.50)
admin@PA-VM> show interface hardware         # View physical interfaces
admin@PA-VM> show interface all              # View logical interfaces
admin@PA-VM> set cli scripting-mode off       # Enable interactive CLI
admin@PA-VM> set cli pager on                # Enable terminal pager

# 2. Configuration Reset (Dependency Order - Avoids Server Ref Errors)
admin@PA-VM> configure

# Step A: Delete Security & NAT Policies
delete rulebase security rules Allow-InterLAN
delete rulebase security rules Allow-Outbound-Internet.
delete rulebase security rules Allow-Inbound-From-Laptop
delete rulebase nat rules Outbound-NAT

# Step B: Delete Virtual Router Static Routes & Interface Attachments
delete network virtual-router default routing-table ip static-route Default-Gateway
delete network virtual-router default interface

# Step C: Delete Security Zones
delete zone Trust-L1
delete zone Trust-L2
delete zone Untrust

# Step D: Delete Hardware Interface Configurations & Imports
delete import network interface
delete network interface ethernet ethernet1/1
delete network interface ethernet ethernet1/2
delete network interface ethernet ethernet1/3

# Step E: Commit Clean Configuration
commit
run show jobs id 22                          # Monitor commit job progress (FIN OK)
exit"""
    story.append(make_code_box(cmd_sec4))
    story.append(Spacer(1, 10))

    # SECTION 5
    story.append(Paragraph("5. VyOS Enterprise Router Commands", h1_style))
    story.append(Paragraph("Gateway interface provisioning, static routing, and Kea dual-subnet DHCP server deployment.", body_style))
    
    cmd_sec5 = """# 1. Log in to VyOS Console (vyos / vyos)
configure

# 2. Clean Existing Interface Configurations
delete interfaces ethernet eth0 address
delete interfaces ethernet eth1 address
delete interfaces ethernet eth2 address

# 3. Configure Enterprise Layer 3 Gateways
set interfaces ethernet eth0 address 10.0.0.2/30       # Uplink to Palo Alto
set interfaces ethernet eth1 address 192.168.10.1/24   # Gateway for Switch1 (LAN 1)
set interfaces ethernet eth2 address 192.168.20.1/24   # Gateway for Switch2 (LAN 2)

# 4. Default Gateway pointing to Palo Alto Firewall
set protocols static route 0.0.0.0/0 next-hop 10.0.0.1

# 5. Kea DHCP Server Pool 1 (Switch1 / LAN-1: 192.168.10.0/24)
set service dhcp-server shared-network-name LAN-POOL subnet 192.168.10.0/24 subnet-id 1
set service dhcp-server shared-network-name LAN-POOL subnet 192.168.10.0/24 option default-router 192.168.10.1
set service dhcp-server shared-network-name LAN-POOL subnet 192.168.10.0/24 option name-server 8.8.8.8
set service dhcp-server shared-network-name LAN-POOL subnet 192.168.10.0/24 range 0 start 192.168.10.10
set service dhcp-server shared-network-name LAN-POOL subnet 192.168.10.0/24 range 0 stop 192.168.10.50

# 6. Kea DHCP Server Pool 2 (Switch2 / LAN-2: 192.168.20.0/24)
set service dhcp-server shared-network-name LAN2-POOL subnet 192.168.20.0/24 subnet-id 2
set service dhcp-server shared-network-name LAN2-POOL subnet 192.168.20.0/24 option default-router 192.168.20.1
set service dhcp-server shared-network-name LAN2-POOL subnet 192.168.20.0/24 option name-server 8.8.8.8
set service dhcp-server shared-network-name LAN2-POOL subnet 192.168.20.0/24 range 0 start 192.168.20.10
set service dhcp-server shared-network-name LAN2-POOL subnet 192.168.20.0/24 range 0 stop 192.168.20.50

# 7. Commit and Persist Configuration to Flash
commit
save
exit

# 8. Operational Verification Commands
show interfaces
show service dhcp-server"""
    story.append(make_code_box(cmd_sec5))
    story.append(Spacer(1, 10))

    # SECTION 6
    story.append(Paragraph("6. VPCS Client Commands & Traffic Verification", h1_style))
    story.append(Paragraph("Commands executed on end-host VPCS stations (PC1 on Switch1 and PC2 on Switch2):", body_style))
    
    cmd_sec6 = """# --- ON PC1 (Switch1 / LAN-1) ---
PC1> clear ip                                # Flush stale configuration
PC1> dhcp                                    # Discover & lease IP from VyOS
# Output: DORA IP 192.168.10.10/24 GW 192.168.10.1
PC1> show ip                                 # Verify IP, Mask, Gateway, DNS
PC1> ping 192.168.10.1                       # Ping local VyOS gateway (0.37 ms)

# --- ON PC2 (Switch2 / LAN-2) ---
PC2> clear ip                                # Flush stale configuration
PC2> dhcp                                    # Discover & lease IP from VyOS
# Output: DORA IP 192.168.20.12/24 GW 192.168.20.1
PC2> show ip                                 # Verify IP, Mask, Gateway, DNS
PC2> ping 192.168.20.1                       # Ping local VyOS gateway (0.30 ms)

# --- INTER-SWITCH / INTER-VLAN ROUTING VALIDATION ---
PC2> ping 192.168.10.10                      # Ping across VyOS to PC1 on Switch1
# 84 bytes from 192.168.10.10 icmp_seq=1 ttl=63 time=3.409 ms
# 84 bytes from 192.168.10.10 icmp_seq=2 ttl=63 time=0.439 ms (SUCCESS)"""
    story.append(make_code_box(cmd_sec6))
    story.append(Spacer(1, 10))

    # SECTION 7: Planned Firewall Uplink Commands
    story.append(Paragraph("7. Planned Next Steps: Palo Alto Point-to-Point Uplink", h1_style))
    story.append(Paragraph("Commands to configure Palo Alto ethernet1/1 and route return traffic back to LAN 1 & LAN 2:", body_style))

    cmd_sec7 = """admin@PA-VM> configure

# 1. Create Ping Management Profile
set network profiles interface-management-profile allow-ping ping yes

# 2. Configure Point-to-Point Uplink Interface (ethernet1/1)
set network interface ethernet ethernet1/1 layer3 ip 10.0.0.1/30
set network interface ethernet ethernet1/1 layer3 interface-management-profile allow-ping
set network virtual-router default interface ethernet1/1
set zone Router-Zone network layer3 ethernet1/1

# 3. Add Return Routes for Internal LANs via VyOS (10.0.0.2)
set network virtual-router default routing-table ip static-route LAN1-Route destination 192.168.10.0/24 interface ethernet1/1 nexthop ip-address 10.0.0.2
set network virtual-router default routing-table ip static-route LAN2-Route destination 192.168.20.0/24 interface ethernet1/1 nexthop ip-address 10.0.0.2

# 4. Security Policy & Commit
set rulebase security rules Allow-All to any from any source any destination any application any service any action allow
commit"""
    story.append(make_code_box(cmd_sec7))

    # Build the PDF using NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF: {output_pdf}")

if __name__ == "__main__":
    out_pdf = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo_Alto_Lab_Running_Commands_Reference.pdf"
    build_pdf(out_pdf)
