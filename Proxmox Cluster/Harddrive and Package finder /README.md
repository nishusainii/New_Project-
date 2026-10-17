# 🏷️ Proxmox Hard Drive & Storage Role Sticker Finder

> **Tool for Data Center Engineers & System Administrators to identify and label physical hard drives in Proxmox clusters (Ceph OSDs, ZFS Pools, Host OS, and Free Drives).**

---

## 📌 Why This Tool Was Created

When you are in front of physical rackmount servers with sticker labels in your hand, you cannot see Linux device letters (`/dev/sda`, `/dev/sdb`). 

Instead, you need:
1. **The Physical Serial Number** (printed on every drive label and tray).
2. **The Exact Storage Role**:
   - 🟧 **Ceph Storage OSD** (OSD ID: `OSD.0`, `OSD.1`, `OSD.2`..., BlueStore block/db)
   - 🟦 **ZFS Storage Pool** (Pool name: `tank`, `rpool`, vdev: `mirror-0`, `raidz2-0`)
   - 🟩 **Proxmox Host OS** (`pve-root`, `/boot`, `/boot/efi`, `local-lvm`)
   - 🟪 **Free / Unused Disks** (Available for new Ceph OSD or ZFS expansion)
3. **Physical Bay / Slot Locator**:
   - Identification of backplane bay / port
   - **Active LED Blinking**: Ability to blink the drive bay LED directly from the terminal so you can visually confirm the drive in the server rack before pasting the sticker!

---

## 📁 Files Included in This Suite

| File | Purpose |
|------|---------|
| [`harddrive-sticker-finder.sh`](file:///home/nishusaini/Desktop/Innspark/Proxmox%20Cluster/Harddrive%20and%20Package%20finder%20/harddrive-sticker-finder.sh) | **Master executable bash script** with live scanner, interactive TUI, LED blinker, and label generator. |
| [`cluster_drive_stickers_viewer.html`](file:///home/nishusaini/Desktop/Innspark/Proxmox%20Cluster/Harddrive%20and%20Package%20finder%20/cluster_drive_stickers_viewer.html) | **Interactive Visual Viewer & Chassis Layout**: Color-coded 12/24-bay front panel, live search by serial number, and print-ready sticker cards. |
| [`stickers_preview.pdf`](file:///home/nishusaini/Desktop/Innspark/Proxmox%20Cluster/Harddrive%20and%20Package%20finder%20/stickers_preview.pdf) | **Sample Print-Ready PDF** with cut-out sticker cards for your 3-node cluster. |

---

## 🚀 Quick Start Guide

### Step 1: Copy Script to Your Proxmox Node(s)

From your management workstation, copy the script to your server (or run it directly over SSH):

```bash
# Option A: Copy to the node (e.g. prox22)
scp harddrive-sticker-finder.sh root@10.31.6.172:/root/
ssh root@10.31.6.172

# Option B: Run directly over SSH without copying
ssh root@10.31.6.172 'bash -s -- -s' < harddrive-sticker-finder.sh
```

| Node Hostname | IP Address | Roles Scanned |
|---|---|---|
| **prox22** | `10.31.6.172` | 4 × Ceph OSDs (0, 3, 6, 9) + 7 × ZFS `zfs-ha` + 1 Spare + 1 OS SSD |
| **prox23** | `10.31.6.173` | 4 × Ceph OSDs (1, 4, 7, 10) + 7 × ZFS `zfs-ha` + 1 Spare + 1 OS SSD |
| **prox24** | `10.31.6.174` | 4 × Ceph OSDs (2, 5, 8, 11) + 7 × ZFS `zfs-ha` + 1 Spare + 1 OS SSD |

---

### Step 2: Run the Interactive Menu

On any node (or via SSH), simply run:
```bash
sudo ./harddrive-sticker-finder.sh
```

You will see the intuitive TUI dashboard:
```text
======================================================================
       PROXMOX HARD DRIVE STICKER & STORAGE FINDER
       Identify Ceph, ZFS, OS & Unused drives for physical labeling
======================================================================
  Current Host : prox22
  Total Disks  : 13
----------------------------------------------------------------------
  1)  View Storage Role & Serial Number Table (Live Scan)
  2)  Generate Printable Sticker Cut-Out Labels (.txt)
  3)  Generate Visual HTML Sticker Sheet (.html)
  4)  Export to CSV (for Excel / Label Printers)
  5)  Blink Drive LED / Physical Bay Locator (Verify before pasting!)
  6)  Run Cluster-Wide Scan (All Proxmox Nodes)
  7)  Check / Install Missing Helper Packages
  8)  Exit
----------------------------------------------------------------------
Select an option [1-8]: 
```

---

## ⚡ CLI One-Liner Commands

You can also run directly with command-line flags:

### 1. View Live Terminal Table
```bash
sudo ./harddrive-sticker-finder.sh --scan
```
**Live Cluster Scan Output (from prox22 @ 10.31.6.172):**
```text
BAY / BUS       DEVICE     SERIAL NUMBER      SIZE      TYPE         STORAGE ROLE   ROLE DETAILS / POOL / OSD
--------------------------------------------------------------------------------------------------------------------
Slot 0          /dev/sda   ZYDGFEW6           18.2T     HDD          CEPH           CEPH OSD.0 (BlueStore block)
Slot 1          /dev/sdb   ZYDG4WXP           18.2T     HDD          CEPH           CEPH OSD.3 (BlueStore block)
Slot 2          /dev/sdc   ZYDG0CL3           18.2T     HDD          CEPH           CEPH OSD.6 (BlueStore block)
Slot 3          /dev/sdd   ZYDFZ35V           18.2T     HDD          CEPH           CEPH OSD.9 (BlueStore block)
Slot 4          /dev/sde   ZYDG62WJ           18.2T     HDD          ZFS            ZFS: zfs-ha (raidz2-0, ONLINE)
Slot 5          /dev/sdf   ZYDG2VVR           18.2T     HDD          ZFS            ZFS: zfs-ha (raidz2-0, ONLINE)
Slot 6          /dev/sdg   ZYDFV3PC           18.2T     HDD          ZFS            ZFS: zfs-ha (raidz2-0, ONLINE)
Slot 7          /dev/sdh   ZYDGDMT3           18.2T     HDD          ZFS            ZFS: zfs-ha (raidz2-0, ONLINE)
Slot 8          /dev/sdi   ZYDGBV46           18.2T     HDD          ZFS            ZFS: zfs-ha (raidz2-0, ONLINE)
Slot 9          /dev/sdj   ZYDG6AWH           18.2T     HDD          ZFS            ZFS: zfs-ha (raidz2-0, ONLINE)
Slot 10         /dev/sdk   ZYDFWL9E           18.2T     HDD          ZFS            ZFS: zfs-ha (raidz2-0, ONLINE)
Slot 11         /dev/sdl   ZYDFW4AP           18.2T     HDD          FREE           Standby / Spare Raw Disk
Rear OS         /dev/sdm   00153b996d278a19   893.8G    SATA/SAS SSD PVE-OS         Proxmox Host OS (root /, EFI, local-lvm)
```

---

### 2. Blink Physical Drive LED to Locate the Bay
Before pasting a sticker, verify the physical drive slot by blinking its chassis LED for 15 seconds:

```bash
# Blink by Linux device path:
sudo ./harddrive-sticker-finder.sh --blink /dev/sda 15

# OR blink by Serial Number directly:
sudo ./harddrive-sticker-finder.sh --blink ZYDGFEW6 15
```
> **How it works on Dell PowerEdge:** Directly triggers `/opt/MegaRAID/perccli/perccli64 /c0/e252/sX start locate` to light up the drive caddy LED AND pulses high-speed non-destructive direct reads to flash the front activity LED.

---

### 3. Generate Printable Sticker Labels (Text Format)
```bash
sudo ./harddrive-sticker-finder.sh --stickers
```
Saves to `output/harddrive_stickers_<hostname>.txt` formatted for cut-out stickers:
```text
+------------------------------------------------------------------------------+
| NODE: prox22                         |  LOCATION: Slot 0                     |
+------------------------------------------------------------------------------+
| STICKER ROLE: CEPH - CEPH OSD.0 (BlueStore block)                            |
| DEVICE PATH : /dev/sda               |  CAPACITY : 18.2 TB (HDD)             |
| SERIAL NO   : ZYDGFEW6               |  MODEL    : ST20000NM007H             |
| WWN / ID    : 0x5000c500f588820f                                             |
+------------------------------------------------------------------------------+
```

---

### 4. Generate Visual HTML Sticker Sheet
```bash
sudo ./harddrive-sticker-finder.sh --html
```
Creates `output/harddrive_stickers_<hostname>.html`. Open in Google Chrome, Edge, or Firefox and press **Ctrl + P** (Print) to print stickers or save as PDF!

---

### 5. Export to CSV (for Label Printers & Excel)
```bash
sudo ./harddrive-sticker-finder.sh --csv
```
Generates a standard CSV formatted with:
- Column `Sticker_Top_Line`: e.g. `prox22 | Slot 0 | CEPH`
- Column `Sticker_Bottom_Line`: e.g. `S/N: ZYDGFEW6 (18.2 TB)`
Ready to import into **Brother P-Touch Editor**, **Dymo Label Software**, **Zebra Designer**, or **Excel**.

---

### 6. Scan All Nodes Across Cluster in One Command
```bash
# Scans 10.31.6.172, 10.31.6.173, and 10.31.6.174 automatically:
sudo ./harddrive-sticker-finder.sh --cluster
```
SSHs to each node, collects disk serials and roles, and generates a unified cluster report `output/harddrive_stickers_ALL_NODES.csv`.

---

## 🏷️ Best Practices for Sticking Labels in the Datacenter

1. **Pull the Caddy Out 1-2 cm**:
   Slide the drive tray latch and read the printed **Serial Number** on the drive label.
2. **Match with the Script / Table**:
   Find the serial number in your report (or search in `cluster_drive_stickers_viewer.html`).
3. **Double-Check with Blink**:
   Run `./harddrive-sticker-finder.sh -b <serial> 10` to make sure the LED flashes on that exact slot.
4. **Paste the Sticker**:
   Recommended label content:
   - **Top line**: `NODE-NAME` &bull; `SLOT/BAY` &bull; `ROLE` (e.g. `PROX22 | SLOT 0 | CEPH OSD.0`)
   - **Bottom line**: `S/N: ZYDGFEW6` &bull; `18.2TB HDD`

---

## 📦 Recommended Helper Packages

The script runs with standard core tools, but for advanced enclosure LED control and SMART serial lookup, install:
```bash
apt-get update && apt-get install -y smartmontools ledmon lsscsi
```
Or use the built-in command:
```bash
sudo ./harddrive-sticker-finder.sh --install-pkgs
```
