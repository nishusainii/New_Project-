# Cisco Router & Switch Integration Guide for GNS3 Lab

This guide explains how to include and configure **Cisco Routers** and **Cisco Switches** in your GNS3 Palo Alto Firewall lab environment.

---

## 🏗️ 1. Supported Cisco Image Types in GNS3

There are 3 primary ways to run Cisco Routers and Switches in GNS3:

| Image Type | Best For | Recommended Images | Placement Folder |
| :--- | :--- | :--- | :--- |
| **1. Cisco IOSv / IOSvL2 (QEMU/KVM)** *(Recommended)* | Modern enterprise routing & Catalyst switching | • `vios-adventerprisek9-m.vmdk.SPA.156-2.T.qcow2` (Router)<br>• `vios_l2-adventerprisek9-m.03.2017.qcow2` (Switch) | `gns3-data/images/QEMU/` |
| **2. Cisco Dynamips (.image / .bin)** | Lightweight classic Cisco IOS | • `c7200-adventerprisek9-mz.152-4.M11.image` (Router)<br>• `c3725-adventerprisek9-mz.124-15.T14.image` (Switch via NM-16ESW module) | `gns3-data/images/Dynamips/` |
| **3. Cisco IOL / IOU (IOS on Linux)** | High density switching & routing | • `i86bi-linux-l2-adventerprisek9-15.2d.bin` (L2 Switch)<br>• `i86bi-linux-l3-adventerprisek9-15.4.1T.bin` (L3 Router) | `gns3-data/images/IOU/` |

---

## 🛠️ 2. Step-by-Step Setup in GNS3

### Option A: Adding Cisco IOSv / IOSvL2 Switch (QEMU/KVM - Recommended)
1. Copy your `.qcow2` image into `/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /gns3-data/images/QEMU/`.
2. Open GNS3 $\rightarrow$ **Edit** $\rightarrow$ **Preferences** $\rightarrow$ **QEMU VMs** $\rightarrow$ Click **New**.
3. Name the VM:
   - For Switch: `Cisco-IOSvL2-Switch`
   - For Router: `Cisco-IOSv-Router`
4. Assign RAM & CPU:
   - RAM: **1024 MB** (1 GB)
   - vCPUs: **1**
5. Disk Image: Select the existing `.qcow2` image from the QEMU directory.
6. Network Adapters:
   - Switch: **8 adapters** (`virtio-net-pci` or `e1000`)
   - Router: **4 adapters** (`virtio-net-pci` or `e1000`)
7. Category: Choose **Switches** (for IOSvL2) or **Routers** (for IOSv).

---

### Option B: Adding Cisco c7200 Router or c3725 EtherSwitch (Dynamips)
1. Copy your decompressed `.image` or `.bin` into `/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /gns3-data/images/Dynamips/`.
2. Open GNS3 $\rightarrow$ **Edit** $\rightarrow$ **Preferences** $\rightarrow$ **IOS routers** (under Dynamips) $\rightarrow$ Click **New**.
3. Select **New Image** $\rightarrow$ Browse to your `.image` file.
4. Set Name: `Cisco 7200 Router` or `Cisco 3725 EtherSwitch`.
5. Slot Configuration:
   - **For c7200 Router**: Slot 0: `C7200-IO-2FE`, Slot 1: `PA-GE` (GigabitEthernet).
   - **For c3725 Switch**: Slot 0: `GT96100-FE`, Slot 1: `NM-16ESW` *(This 16-port module turns the router into a hardware-featured Cisco Switch!)*.
6. Calculate **Idle-PC**: Click **Idle-PC finder** to ensure CPU usage remains near 0%.

---

## 🌐 3. Recommended Enterprise Lab Topology

Integrate Cisco Routers and Switches with your Palo Alto Firewall (`PA-VM-1`) as follows:

```
                            [ Cloud / Internet NAT ]
                                       │
                                       ▼
                       [ Cisco 7200 / IOSv WAN Router ]
                                       │
                            (IP: 192.168.0.1/24)
                                       │
                                       ▼
                     [ Palo Alto PA-VM-1 Firewall ]
                       Untrust: ethernet1/2 (192.168.0.254/24)
                       Trust:   ethernet1/1 (10.1.1.254/24)
                       MGT:     management  (192.168.1.1/24)
                                       │
                                       ▼
                       [ Cisco IOSvL2 / c3725 Switch ]
                       Trunk Port (Gi0/0) / Access VLANs
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
             [ VLAN 10 (Users) ]                [ VLAN 20 (Servers) ]
             PC1 (10.1.10.10)                   DMZ Web (10.1.20.10)
```

---

## 📂 4. Pre-Created Image Directories

The following directories are ready for your Cisco image files:
- 📁 **Dynamips (c7200 / c3725)**: `/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /gns3-data/images/Dynamips/`
- 📁 **QEMU (IOSv / IOSvL2 / vIOS)**: `/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /gns3-data/images/QEMU/`
- 📁 **IOU / IOL (L2/L3 IOL)**: `/home/nishusaini/Desktop/Innspark/Palo Alto Firewall /gns3-data/images/IOU/`
