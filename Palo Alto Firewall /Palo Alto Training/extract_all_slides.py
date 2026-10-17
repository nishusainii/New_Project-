import os
import subprocess
import time

# Directory
slides_dir = "/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /Palo Alto Training/extracted_slides"
os.makedirs(slides_dir, exist_ok=True)

# Key presentation slide timestamps across the 11-hour course
slide_timestamps = [
    ("00_05_00", "00:05:00", "Course Introduction & Syllabus Overview"),
    ("00_12_30", "00:12:30", "Evolution of Firewalls (Packet Filters vs NGFW)"),
    ("00_22_00", "00:22:00", "Port Hopping & Application Evasion Tactics"),
    ("00_32_00", "00:32:00", "Single-Pass Parallel Processing (SP3) Architecture"),
    ("00_45_00", "00:45:00", "Control Plane vs Data Plane Physical Isolation"),
    ("00_55_00", "00:55:00", "Four Core Pillars: App-ID, User-ID, Content-ID, WildFire"),
    ("01_08_00", "01:08:00", "Zero-Day Threat Protection & Cloud Sandboxing"),
    ("01_18_00", "01:18:00", "Palo Alto WildFire Detonation Architecture"),
    ("01_35_00", "01:35:00", "Stateless ACLs vs Dedicated Firewall Engines"),
    ("01_48_00", "01:48:00", "Proxy Architectures: Explicit vs Transparent Proxies"),
    ("02_02_00", "02:02:00", "Stateful Inspection & In-Memory State Tables"),
    ("02_15_00", "02:15:00", "Deployment Modes: Layer 3 Routed vs Virtual Wire (V-Wire)"),
    ("02_25_00", "02:25:00", "Firewall Generations & Nir Zuk History"),
    ("02_35_00", "02:35:00", "UTM Multi-Pass Bottlenecks vs Single-Pass Acceleration"),
    ("02_48_00", "02:48:00", "Palo Alto Hardware Appliance Portfolios (PA-220 to PA-7000)"),
    ("03_00_00", "03:00:00", "Port Matrix: MGT, Console, HA1, HA2, HSCI & Data Ports"),
    ("03_12_00", "03:12:00", "Hands-On Lab Topology Design & GNS3/VM Setup"),
    ("03_30_00", "03:30:00", "Initial PAN-OS Access & CLI Command Structure"),
    ("03_50_00", "03:50:00", "Candidate Configuration vs Running Configuration & Commit"),
    ("04_15_00", "04:15:00", "Security Zones & Default Rule Evaluation (Inter vs Intra)"),
    ("04_40_00", "04:40:00", "Interface Configuration & Management Profiles"),
    ("05_05_00", "05:05:00", "Virtual Routers, Static Routing & Default Gateways"),
    ("05_30_00", "05:30:00", "Path Monitoring & Dynamic WAN Failover (Palo Alto IP SLA)"),
    ("06_00_00", "06:00:00", "NAT Deep Dive: Source NAT (DIPP/PAT) & Dynamic Pool"),
    ("06_30_00", "06:30:00", "Destination NAT (Port Forwarding) & Inbound Web Publishing"),
    ("07_00_00", "07:00:00", "U-Turn NAT (Hairpinning) for Internal Access"),
    ("07_30_00", "07:30:00", "App-ID Mechanics & Layer 7 Protocol Decoders"),
    ("08_00_00", "08:00:00", "Policy Optimizer & Migrating Port-Based Rules to App-ID"),
    ("08_30_00", "08:30:00", "Content-ID Suite: Antivirus, Anti-Spyware & DNS Sinkholing"),
    ("09_00_00", "09:00:00", "Vulnerability Protection (IPS) & URL Filtering Profiles"),
    ("09_30_00", "09:30:00", "User-ID Integration with Active Directory (WMI/WinRM/Syslog)"),
    ("10_00_00", "10:00:00", "SSL/TLS Decryption (Forward Proxy vs Inbound Inspection)"),
    ("10_30_00", "10:30:00", "Site-to-Site IPsec VPN (IKEv1/IKEv2 Phase 1 & 2)"),
    ("11_00_00", "11:00:00", "High Availability (Active/Passive) & Clustering Failover")
]

print("Fetching video stream URL using yt-dlp...")
get_url_cmd = ["/tmp/yt-dlp", "-f", "134", "-g", "https://www.youtube.com/watch?v=4dOI1u6FA0w"]
res = subprocess.run(get_url_cmd, capture_output=True, text=True)
video_url = res.stdout.strip()

if not video_url:
    print("Error: Could not retrieve video stream URL.")
    exit(1)

print(f"Video stream URL obtained. Extracting {len(slide_timestamps)} slides...")

extracted = []
for file_id, ts, title in slide_timestamps:
    out_img = os.path.join(slides_dir, f"slide_{file_id}.jpg")
    if os.path.exists(out_img) and os.path.getsize(out_img) > 1000:
        print(f"Already exists: {out_img}")
        extracted.append((out_img, ts, title))
        continue
    
    cmd = [
        "ffmpeg", "-ss", ts, "-i", video_url,
        "-vframes", "1", "-q:v", "2", out_img, "-y"
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=25)
        if os.path.exists(out_img) and os.path.getsize(out_img) > 1000:
            print(f"Extracted [{ts}] -> {out_img} ({title})")
            extracted.append((out_img, ts, title))
        else:
            print(f"Failed extracting [{ts}]")
    except Exception as e:
        print(f"Error on [{ts}]: {e}")

print(f"Extraction complete. Total slides captured: {len(extracted)}")
