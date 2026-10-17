# Management Tools & Scripts

This folder contains the complete operational tooling for discovering, configuring, and automating Central TV displays across LAN and Wi-Fi networks.

---

## Tool Index

### 1. `tv-detect.sh` & `tv-network-detector.js`
- **Purpose:** High-speed parallel subnet scanner and automated Smart TV setup.
- **What it does:** Scans the local subnet for Smart TVs listening on port 3001, prompts for pairing on screen if needed, saves the permanent client key, and automatically launches the TV browser to `player.html`.
- **Usage:**
  ```bash
  # Auto-launch all detected TVs:
  ./tv-detect.sh --all

  # Interactive mode:
  ./tv-detect.sh

  # Connect to specific TV IP:
  ./tv-detect.sh 192.168.0.170 "Conference-Room-TV"
  ```

---

### 2. `start-kiosk.sh`
- **Purpose:** Full-screen kiosk launcher for Raspberry Pi 4 / 5 and Ubuntu Desktop Mini PCs.
- **What it does:** Launches Chromium in full-screen kiosk mode with hardware acceleration enabled, disabled cursor (`unclutter`), disabled power-saving/sleep, and automatic crash recovery.
- **Usage:**
  ```bash
  ./start-kiosk.sh
  ```

---

### 3. `install-systemd.sh`
- **Purpose:** Automated systemd service installer for edge display kiosks.
- **What it does:** Registers `tv-kiosk.service` to auto-boot the kiosk player on system startup without requiring manual desktop login.
- **Usage:**
  ```bash
  sudo ./install-systemd.sh
  ```

---

### 4. `branch-relay-setup.sh`
- **Purpose:** Branch office WAN bandwidth optimizer.
- **What it does:** Deploys a lightweight local media proxy cache in remote branch offices (e.g. Delhi office) so that multiple local TVs pull streams locally from 1 upstream connection rather than duplicating WAN traffic.
- **Usage:**
  ```bash
  sudo ./branch-relay-setup.sh
  ```
