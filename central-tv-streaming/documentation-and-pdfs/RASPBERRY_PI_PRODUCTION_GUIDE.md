# Raspberry Pi Production Implementation Specification & Deployment Guide
**Centre for Innovation & Systems AI (CiSAI)**  
**Document Reference:** CiSAI-ENG-RPI-PROD-2026-V1  
**Target Hardware:** Raspberry Pi 5 / Raspberry Pi 4B  
**Operating Systems:** Ubuntu 24.04 LTS (Desktop/Server) / Raspberry Pi OS 64-bit  

---

## 1. Executive Overview & Purpose

This document provides the complete hardware specification, operating system configuration, software tuning, and production hardening required to deploy the Central TV Streaming & Signage Platform onto Raspberry Pi hardware.

The Raspberry Pi can serve two critical operational roles:
1. **Dedicated TV Display Kiosk Endpoint:** Attached to the back of any commercial TV or standard monitor via HDMI, booting autonomously into a full-screen, hardware-accelerated video kiosk without human intervention.
2. **Edge Branch Relay or Compact Central Server:** Running the lightweight Docker container stack (Node.js Controller + MediaMTX) to orchestrate video streams for an entire branch office.

---

## 2. Hardware Bill of Materials (BOM) & Prerequisites

To ensure 24/7 reliability in industrial and commercial environments, consumer-grade accessories (such as cheap phone chargers and generic SD cards) must be avoided.

### 2.1 Recommended Production Hardware Stack

| Component | Minimum Specification (1080p Playback) | Recommended Specification (4K 60FPS / Server) | Technical Rationale |
| :--- | :--- | :--- | :--- |
| **Single Board Computer** | Raspberry Pi 4 Model B (4GB RAM) | **Raspberry Pi 5 (8GB RAM)** | Pi 5 provides 2-3x CPU throughput and VideoCore VII GPU for 4K 60fps HEVC/H.264 decoding. |
| **Power Supply** | Official 15W USB-C (5.1V / 3.0A) | **Official 27W USB-C (5.1V / 5.0A)** | Under-voltage causes CPU throttling, Wi-Fi drops, and sudden reboots under heavy video loads. |
| **Storage (Critical)** | High-Endurance MicroSD (SanDisk Max Endurance 64GB) | **M.2 NVMe SSD via PCIe HAT+ (128GB / 256GB)** | Standard SD cards corrupt during sudden power loss. NVMe SSD provides 500+ MB/s and industrial endurance. |
| **Thermal Cooling** | Passive Aluminum Armor Heatsink Case | **Official Active Cooler (Heatsink + PWM Fan)** | Prevents thermal throttling (which begins at 80°C), maintaining peak hardware acceleration. |
| **Display Cable** | Micro-HDMI to Standard HDMI (1.5m) | **Micro-HDMI to HDMI 2.0 Premium High Speed** | Required for 4K 60Hz video bandwidth and HDMI-CEC signals. |
| **Network Interface** | Gigabit Ethernet (CAT6) or 5 GHz Wi-Fi | **Gigabit Ethernet (CAT6) with PoE+ HAT (Optional)** | PoE (Power over Ethernet) allows powering the Pi directly through the network switch cable. |

---

## 3. Operating System Selection: Ubuntu Desktop vs. Raspberry Pi OS

| Parameter | Ubuntu 24.04 LTS Desktop (64-bit) | Raspberry Pi OS 64-bit (Debian Bookworm) | Recommended Choice |
| :--- | :--- | :--- | :--- |
| **Kiosk Display Client** | Supported (GNOME / Mutter) | **Optimal (labwc / Wayfire / X11)** | **Raspberry Pi OS Lite / Desktop:** Uses less RAM (under 250MB baseline) and boots in under 12 seconds. |
| **Central Docker Server** | **Optimal (Enterprise standard)** | Supported | **Ubuntu 24.04 LTS:** Standardized package ecosystem, Canonical kernel updates, and enterprise Docker support. |
| **GPU Acceleration** | Broadcom V3D driver included | Native firmware optimized | Both support hardware video decoding. |

---

## 4. Raspberry Pi as a TV Kiosk Client: Setup Runbook

When using the Raspberry Pi as a dedicated TV client attached to an HDMI display:

### 4.1 Step 1: Flashing the Operating System
1. Download and run **Raspberry Pi Imager** on your computer.
2. Choose OS: **Raspberry Pi OS (64-bit)** or **Ubuntu Desktop 24.04 LTS**.
3. In OS Customization settings:
   * Set hostname (e.g., `tv-boardroom-pi` or `tv-reception-pi`).
   * Configure username and strong password.
   * Configure Wi-Fi SSID and password (if not using wired Ethernet).
   * Enable **SSH** for remote administration.
4. Flash onto the NVMe SSD or High-Endurance SD card.

### 4.2 Step 2: System Dependencies & Utilities
Boot the Raspberry Pi and run:
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y chromium-browser unclutter xdotool cec-utils watchdog
```

### 4.3 Step 3: Automated Auto-Boot Kiosk Configuration
Create the auto-start launcher script at `/opt/start-kiosk.sh`:
```bash
sudo tee /opt/start-kiosk.sh > /dev/null << 'EOF'
#!/usr/bin/env bash
# Disable screen blanking, screensaver, and energy saving DPMS
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor after 0.5s of inactivity
unclutter -idle 0.5 -root &

# Target Central Server URL (Replace with your server IP)
SERVER_IP="192.168.0.151:8080"
TV_NAME="Pi-Display-1"
SITE="Headquarters"
TARGET_URL="http://${SERVER_IP}/player.html?name=${TV_NAME}&site=${SITE}"

# Launch Chromium in pure kiosk mode with zero user-gesture autoplay
exec chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --check-for-update-interval=31536000 \
    --autoplay-policy=no-user-gesture-required \
    --enable-features=OverlayScrollbar \
    --hide-scrollbars \
    --enable-gpu-rasterization \
    --ignore-gpu-blocklist \
    --app="${TARGET_URL}"
EOF

sudo chmod +x /opt/start-kiosk.sh
```

### 4.4 Step 4: Systemd Kiosk Supervisor Service
To ensure the display player starts automatically on boot and auto-restarts within 3 seconds if closed or crashed:
```bash
sudo tee /etc/systemd/system/tv-kiosk.service > /dev/null << 'EOF'
[Unit]
Description=CiSAI Central TV Kiosk Display Player
After=network-online.target graphical.target
Wants=network-online.target

[Service]
Type=simple
User=nishusaini
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/nishusaini/.Xauthority
ExecStart=/opt/start-kiosk.sh
Restart=always
RestartSec=3
KillMode=process

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable tv-kiosk.service
```

---

## 5. Hardware & Software Reliability Improvements

To transition from prototype to production reliability, apply these four enterprise enhancements:

### 5.1 Hardware Watchdog Timer (Automatic Hang Recovery)
The Broadcom SoC contains a hardware watchdog timer. If the Linux kernel ever freezes, the hardware chip automatically reboots the board within 15 seconds.

1. Enable the hardware module in `/etc/modules`:
   ```bash
   echo "bcm2835_wdt" | sudo tee -a /etc/modules
   ```
2. Configure `/etc/watchdog.conf`:
   ```ini
   watchdog-device = /dev/watchdog
   watchdog-timeout = 15
   max-load-1 = 24
   ```
3. Enable and start the watchdog service:
   ```bash
   sudo systemctl enable watchdog
   sudo systemctl restart watchdog
   ```

### 5.2 Read-Only Root Filesystem (OverlayFS)
Commercial TVs are frequently powered off abruptly by staff using master wall switches. To prevent SD card or disk filesystem corruption:
* In **Raspberry Pi OS**: Run `sudo raspi-config` &rarr; **Performance Options** &rarr; **Overlay File System** &rarr; **Enable**.
* When enabled, the OS runs in read-only mode, redirecting writes to temporary RAM. Power can be cut at any time without corrupting system files.

### 5.3 Automated TV Power Scheduling via HDMI-CEC
Using the included `cec-utils`, the Raspberry Pi can turn the physical TV panel ON and OFF over the HDMI cable, eliminating the need for physical TV remotes:

* Turn TV ON:
  ```bash
  echo 'on 0' | cec-client -s -d 1
  ```
* Turn TV OFF (Standby):
  ```bash
  echo 'standby 0' | cec-client -s -d 1
  ```
* Automate using cron (`sudo crontab -e`):
  ```cron
  # Power ON TV at 08:00 AM (Monday to Friday)
  0 8 * * 1-5 echo 'on 0' | cec-client -s -d 1
  # Power OFF TV at 08:00 PM (Monday to Friday)
  0 20 * * 1-5 echo 'standby 0' | cec-client -s -d 1
  ```

### 5.4 Wi-Fi Power Management Disabling
By default, Linux Wi-Fi chips enter a sleep state after a few seconds of idle time, causing latency spikes. Disable Wi-Fi power saving permanently:
```bash
sudo iw dev wlan0 set power_save off
```
Add to `/etc/rc.local` or NetworkManager dispatcher to persist across reboots.

---

## 6. Raspberry Pi as the Central Streaming Server

If deploying the Raspberry Pi 5 as the central controller hosting Docker:

```bash
# 1. Install Docker and Docker Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Clone repository to /opt
sudo git clone <repo_url> /opt/central-tv-streaming
cd /opt/central-tv-streaming

# 3. Launch Docker Compose Stack
docker compose up -d

# 4. Verify status
docker compose ps
```
The server will operate on:
* **HTTP Admin:** `http://<PI_IP>:8080/admin.html`
* **TV Player:** `http://<PI_IP>:8080/player.html`
* **WebRTC Streaming:** Port `8889` (TCP) and `8189` (UDP)

---

## 7. Production Maintenance & Health Checklist

| Frequency | Task | Procedure |
| :--- | :--- | :--- |
| **Continuous** | Temperature Monitoring | Run `vcgencmd measure_temp` (Optimal: below 65°C under full load). |
| **Continuous** | Watchdog Liveness | Verify watchdog daemon status: `systemctl status watchdog`. |
| **Monthly** | Security Kernel Patches | `sudo apt update && sudo apt --only-upgrade install linux-image-*`. |
| **Monthly** | Media Cache Cleanup | Verify free space on `/opt/central-tv-streaming/media`: `df -h`. |
| **Quarterly** | HDMI-CEC Signal Check | Verify CEC link response: `echo 'scan' \| cec-client -s -d 1`. |
