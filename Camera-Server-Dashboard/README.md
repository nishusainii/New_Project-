# INNCCTV // 24-Camera Surveillance Operations Center (SOC)

A high-performance, dark-themed Security Operations Center (SOC) dashboard engineered for monitoring **24 IP cameras across a 4-floor commercial building** with ultra-low-latency WebRTC streaming, 2D architectural floor plan blueprints, and digital PTZ controls.

---

## 🏛️ System Architecture

- **Web Dashboard**: Vanilla HTML5, CSS3 Glassmorphism SOC design system, and modular JavaScript (`public/`).
- **Media Streaming Gateway**: Embedded **MediaMTX** (formerly `rtsp-simple-server`) converting raw camera RTSP streams into ultra-low-latency **WebRTC (WHEP)** and **HLS** for native browser playback without plugins or extra software.
- **Backend API & WebSockets**: Node.js & Express server handling camera inventory, TCP ping reachability tests, live telemetry, and real-time motion detection event streaming (`server/`).
- **Interactive 2D Floor Plan Engine**: Architectural blueprint layouts for Floor 1 to Floor 4 with camera positions and dynamic Field of View (FOV) coverage cones (`public/js/floorMap.js`).

---

## 🚀 Quick Start

### 1. Launch the Server and Streaming Gateway
To start the entire stack with a single command:

```bash
cd /home/nishusaini/Desktop/Innspark/Camera-Server-Dashboard
./start.sh
```

Or using `npm`:
```bash
npm start
```

### 2. Stop the Server and Streaming Gateway
To cleanly stop all background processes and release all ports:
```bash
./stop.sh
```
Or using `npm`:
```bash
npm stop
```

### 2. Access the Dashboard
Open your web browser and navigate to:
```
http://localhost:3000
```
If you are not logged in, you will be automatically directed to the **Innspark Delhi Office SOC Login Portal**:
```
http://localhost:3000/login.html
```

### 🔐 Default Login Credentials (Innspark Delhi Office)

| Role | Username | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Chief Security Officer (Admin)** | `admin` | `innspark@2026` | Full Control (Add/Edit Cams, Batch Setup, PTZ, Snapshots) |
| **Surveillance Officer (Operator)** | `operator` | `innspark@2026` | Monitoring & PTZ Control, Snapshots |
| **Floor Supervisor** | `supervisor` | `innspark@2026` | Floor-level monitoring & Snapshots |

*(Quick 1-click role fill buttons are also available directly on the login screen for rapid access)*

---

## 📡 Port & Network Map

| Service | Port | Description |
| :--- | :--- | :--- |
| **Web Dashboard & REST API** | `3000` | Surveillance Operations Center web interface & camera management API |
| **WebRTC (WHEP) Gateway** | `8889` | Ultra-low latency (<250ms) video streaming directly to browser `<video>` tags |
| **HLS Stream Gateway** | `8888` | Low-latency HLS video fallback |
| **RTSP Ingestion / Restream**| `8554` | RTSP server & proxy |
| **MediaMTX Control API** | `9997` | Dynamic stream management API |

---

## 🏢 4-Floor Camera Distribution (24 Cameras)

All 24 cameras come pre-configured out-of-the-box with realistic zones, metadata, and simulated CCTV feeds:

| Floor | Zone Name | Cameras | Key Locations |
| :--- | :--- | :--- | :--- |
| **Floor 1** | Ground Reception & Logistics | 6 | Main Entrance Lobby, Visitor Reception, Elevator Bank, West Fire Exit, Loading Dock Bay, South Parking Ramp ANPR |
| **Floor 2** | Engineering & Workspaces | 6 | Open Workstations, Boardroom Alpha, IDF/Server Closet, Atrium Lobby, Cafeteria Lounge, North Stairwell |
| **Floor 3** | R&D Labs & High Security | 6 | Cleanroom Airlock, Hardware Test Bay, Central Data Vault, F3 Elevator Core, Agile Squad Pods, South Terrace Exit |
| **Floor 4** | Executive Suite & NOC Plant | 6 | 24/7 Security NOC Floor, Mainframe Server Hall A, Executive Boardroom, HVAC Plant Deck, Diesel Generator Bay, Rooftop Helipad PTZ |

---

## ⚙️ How to Connect Your Real IP Cameras

### Option 1: Edit an Individual Camera via the UI
1. Hover over any camera card and click the **Pencil icon** (or click **Add Camera** in the top bar).
2. Enter your camera's:
   - **Camera IP Address** (e.g. `192.168.1.101`)
   - **RTSP Port** (typically `554`)
   - **Complete RTSP URL**:
     - *Hikvision*: `rtsp://admin:password@192.168.1.101:554/Streaming/Channels/101`
     - *Dahua*: `rtsp://admin:password@192.168.1.101:554/cam/realmonitor?channel=1&subtype=0`
     - *Generic ONVIF*: `rtsp://admin:password@192.168.1.101:554/h264Preview_01_main`
3. Click **Test Connection** to verify TCP/RTSP socket reachability.
4. Click **Save Camera**. MediaMTX will immediately register the stream.

### Option 2: Batch Configure an Entire Floor's Cameras
1. Click **Batch Setup** in the top navigation bar.
2. Select your target floor (or all 4 floors).
3. Set your subnet prefix (e.g. `192.168.1.`) and credentials (`admin` / `password`).
4. Click **Apply to Cameras** to automatically update all cameras on that floor in one step.

### Option 3: Direct JSON File Configuration
You can also directly edit [config/cameras.json](file:///home/nishusaini/Desktop/Innspark/Camera-Server-Dashboard/config/cameras.json). Changes are automatically loaded upon server restart.

---

## 🎮 Key Dashboard Controls & Features

1. **Floor Bar Navigation**:
   - `All Floors (24 CAMS)`: Full 24-camera building matrix overview.
   - `Floor 1`, `Floor 2`, `Floor 3`, `Floor 4`: Isolates the 6 cameras on that specific floor.
2. **View Mode Switcher**:
   - **Live Grid**: High-density video monitoring wall.
   - **2D Floor Map**: Architectural blueprint view displaying each camera's physical location and Field of View (FOV) cone. Click any camera pin to preview or focus.
3. **Grid Layout Selector**:
   - Switch between **1x1** (Single focus), **2x2** (Quad), **3x3**, **4x4**, **Floor (6)**, and **Full (24)**.
4. **Patrol / Tour Mode**:
   - Click the **Patrol Tour** button in the header to activate unattended automated cycling between all 4 floors every 7 seconds.
5. **Digital PTZ Controls**:
   - Pan Left/Right, Tilt Up/Down, and Zoom (1x to 4x) directly from the camera modal.
6. **Instant Snapshot Capture**:
   - Click the camera icon on any tile to download an instant timestamped high-resolution JPEG snapshot.
