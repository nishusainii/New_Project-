# 📺 Central TV Streaming & Multi-Site Display Platform

An enterprise-grade, ultra-low latency (<250ms) live streaming and digital signage platform designed to run on **Laptops and Raspberry Pis** across local **LAN, Wi-Fi, and Site-to-Site VPNs** with zero internet dependencies.

---

## 🌟 Key Features

* **⚡ Ultra-Low Latency Live Streaming (< 250ms):** Stream presenter laptop screens, cameras, or videos directly to TVs over WebRTC (WHEP/WHIP) with sub-second delay.
* **🌐 Multi-Site Site-to-Site VPN Support:** Broadcast from Headquarters to TVs in branch offices (e.g., Kolkata) with automatic remote TV takeover and zero manual touch.
* **🪧 Seamless Fallback Digital Signage:** When no live broadcast is running, TVs automatically display announcements, video loops, and a digital clock without showing black screens.
* **🚨 Emergency Alert System:** Push instant, high-priority emergency banners across all connected TVs in real time.
* **🖥️ Universal Kiosk Player:** Runs in standard Chromium on Raspberry Pi OS, Ubuntu, Debian, or any HDMI-connected mini PC.
* **📦 Dual Deployment:**
  * **Option 1 (Docker):** 1-line deployment via `docker compose up -d`.
  * **Option 2 (Bare-Metal systemd):** Zero-overhead native systemd services for resource-constrained Raspberry Pis.

---

## 🚀 Quick Start (Option A: Docker Deployment)

From the project directory:

```bash
docker compose up -d
```

Check running services:
```bash
docker compose ps
```

The system will start:
* **Admin Management Console:** `http://<YOUR_IP>:8080/admin.html`
* **Presenter Broadcast Studio:** `http://<YOUR_IP>:8080/presenter.html`
* **TV Kiosk Receiver:** `http://<YOUR_IP>:8080/player.html`
* **Media Core (MediaMTX):** WebRTC on port `8889`, HLS on `8888`, RTSP on `8554`

---

## 🛠️ Quick Start (Option B: Bare-Metal / Raspberry Pi OS)

If you are running on a Raspberry Pi without Docker:

```bash
sudo ./scripts/install-systemd.sh
```

This will automatically:
1. Detect architecture (`amd64`, `arm64`, or `armv7`).
2. Download and configure the native `mediamtx` streaming binary.
3. Install Node.js dependencies and enable `tv-mediamtx.service` and `tv-manager.service`.

---

## 🖥️ Setting Up a TV Display (Raspberry Pi / Laptop connected to TV)

On the Raspberry Pi or Laptop connected to the television via HDMI:

```bash
./scripts/start-kiosk.sh <SERVER_VPN_IP>:8080 "Kolkata Office" "Main Hall TV"
```

The script:
1. Disables screen sleep and DPMS power-saving.
2. Hides the mouse cursor.
3. Launches Chromium full-screen in locked kiosk mode with sound enabled.
4. Auto-connects and registers with the Central Server over the Site-to-Site VPN.

---

## 🎥 How to Broadcast from Your Laptop

1. Open **Presenter Studio**: `http://<SERVER_IP>:8080/presenter.html` on your laptop.
2. Click **"Share Laptop Screen"** or **"Camera & Mic"**.
3. Select your target:
   * **All Sites** (Headquarters + Kolkata + Remote Branches)
   * **Headquarters Only**
   * **Kolkata Office Only**
4. Click **"Start Live Broadcast"**.
5. **Instant Takeover:** All TVs at the target sites immediately switch to your live screen.
6. When done, click **"Stop Broadcast"** — all TVs smoothly revert to their local signage loop.

---

## 🏢 Bandwidth Optimization for Branch Offices (Branch Relay)

If a branch office (e.g., Kolkata) has 5–10 TVs, pulling 10 individual streams across the Site-to-Site VPN can saturate bandwidth.

To optimize, configure 1 Raspberry Pi at the branch office as a local relay:
```bash
./scripts/branch-relay-setup.sh <HQ_VPN_IP>
```
* **WAN Usage:** Only **1 stream** travels across the Site-to-Site VPN from HQ to the Kolkata relay.
* **LAN Usage:** The Kolkata relay redistributes the stream locally to the other 9 TVs over the local office Wi-Fi/LAN.

---

## 📁 Project Structure

```
central-tv-streaming/
├── docker-compose.yml          # Docker orchestration stack
├── Dockerfile                  # Container definition for TV Manager
├── mediamtx.yml                # Low-latency WebRTC streaming configuration
├── package.json                # Node.js backend dependencies
├── server.js                   # WebSocket broker, REST API & Device Manager
├── certs/                      # Local SSL certificates for WebRTC screen share
├── public/                     # Web applications
│   ├── index.html              # Landing portal
│   ├── admin.html              # Central Admin Dashboard
│   ├── presenter.html          # In-Browser Screen Share & Broadcast Studio
│   ├── player.html             # TV Kiosk Player (WebRTC + Signage fallback)
│   ├── css/style.css           # Modern dark-theme UI styles
│   └── js/                     # Client JavaScript for admin, presenter & player
├── scripts/
│   ├── start-kiosk.sh          # TV HDMI auto-boot kiosk script
│   ├── install-systemd.sh      # Bare-metal native systemd installer
│   └── branch-relay-setup.sh   # Branch office bandwidth optimizer
└── media/                      # Directory for signage video loops and posters
```
