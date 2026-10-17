# Proxmox VE SDN - Complete CLI Command Reference & Guide

This guide provides all terminal commands to install, configure, manage, automate, and troubleshoot **Software-Defined Networking (SDN)** in Proxmox VE directly from the command line (`pvesdn`, `pvesh`, and Linux networking tools).

---

## 1. Prerequisites & Package Installation

Run these commands on **all cluster nodes** to install SDN components, DHCP services, and BGP/FRR routing:

```bash
# Update repositories
apt update

# Install SDN core packages, ifupdown2, DHCP (dnsmasq), and Routing (FRR)
apt install -y libpve-network-perl ifupdown2 dnsmasq frr-pythontools frr

# Disable default systemd-resolved to prevent port 53 conflict with dnsmasq (if using SDN DHCP)
systemctl disable --now systemd-resolved
```

---

## 2. Core CLI Tool: `pvesdn`

Proxmox provides the dedicated `pvesdn` command-line utility for managing all SDN objects.

### A. Managing SDN Zones

#### 1. Simple Zone (Isolated / Local NAT)
```bash
# Create Simple Zone
pvesdn zone create localzone --type simple

# Create Simple Zone with automatic IPAM
pvesdn zone create localzone --type simple --ipam pve
```

#### 2. VLAN Zone (802.1q Trunking over physical bridge)
```bash
# Create VLAN Zone tied to physical bridge vmbr0
pvesdn zone create vlan-zone --type vlan --bridge vmbr0 --ipam pve
```

#### 3. QinQ Zone (Stacked VLANs / Double Tagging)
```bash
# Create QinQ Zone on tag 100
pvesdn zone create qinq-zone --type qinq --bridge vmbr0 --tag 100 --vlan-protocol 802.1q --ipam pve
```

#### 4. VXLAN Zone (L2 over L3 Mesh Overlay)
```bash
# Create VXLAN Zone with list of peer node IPs
pvesdn zone create vxlan-zone --type vxlan --peers 192.168.1.10,192.168.1.11,192.168.1.12 --ipam pve
```

#### 5. EVPN Zone (BGP EVPN Controller-driven)
```bash
# First create BGP Controller (see Section C below), then:
pvesdn zone create evpn-zone --type evpn --controller bgp-ctrl --vrf-vxlan 10000 --mac 02:00:00:00:00:01 --ipam pve
```

#### Zone Management Commands:
```bash
# List all Zones
pvesdn zone list

# Delete a Zone
pvesdn zone delete <zone_name>
```

---

### B. Managing VNets (Virtual Networks / Bridges)

VNets act as virtual bridges attached to a Zone.

```bash
# Create a VNet attached to a Zone
pvesdn vnet create vnet10 --zone vxlan-zone --tag 10

# Create a VNet with VLAN tag on a VLAN Zone
pvesdn vnet create vnet100 --zone vlan-zone --tag 100

# Create a VNet with custom alias
pvesdn vnet create vnet-dev --zone localzone --alias "Development Network"

# List all VNets
pvesdn vnet list

# Delete a VNet
pvesdn vnet delete vnet10
```

---

### C. Managing Subnets, DHCP & SNAT / Gateways

Subnets are created within VNets to provide IP ranges, default routing, and DHCP.

```bash
# 1. Create a basic Subnet with Gateway
pvesdn subnet create vnet10 10.10.10.0/24 --gateway 10.10.10.1

# 2. Create a Subnet with SNAT (Outbound Internet NAT via host)
pvesdn subnet create vnet10 10.10.10.0/24 --gateway 10.10.10.1 --snat 1

# 3. Create a Subnet with SNAT and automatic DHCP IP range
pvesdn subnet create vnet10 10.10.10.0/24 \
  --gateway 10.10.10.1 \
  --snat 1 \
  --dhcp-range start-address=10.10.10.50,end-address=10.10.10.200 \
  --dhcp-dns-server 1.1.1.1

# List subnets in a VNet
pvesdn subnet list vnet10

# Delete a Subnet
pvesdn subnet delete vnet10 10.10.10.0/24
```

---

### D. Applying & Reloading SDN Changes

Any changes made to Zones, VNets, or Subnets remain pending until applied.

```bash
# Apply and deploy SDN configuration across the cluster
pvesdn reload

# Check current SDN deployment status
pvesdn status
```

---

## 3. Managing SDN with `pvesh` (Cluster API CLI)

You can also use Proxmox's built-in API shell `pvesh` to automate SDN via scripts or JSON outputs:

```bash
# Get all SDN zones in JSON format
pvesh get /cluster/sdn/zones --output-format json

# Create a zone via API
pvesh create /cluster/sdn/zones --zone myvlan --type vlan --bridge vmbr0

# Create a VNet via API
pvesh create /cluster/sdn/vnets --vnet vnet20 --zone myvlan --tag 20

# Create a Subnet via API
pvesh create /cluster/sdn/vnets/vnet20/subnets --subnet 192.168.20.0/24 --gateway 192.168.20.1 --snat 1

# Trigger SDN Reload / Apply via API
pvesh put /cluster/sdn/reload
```

---

## 4. Connecting VMs and LXC Containers to SDN VNets

Once a VNet is applied, it behaves as a network bridge (e.g. `vnet10`). Attach guests using `qm` or `pct`:

```bash
# Attach VM (ID: 100) network adapter 0 to VNet
qm set 100 --net0 virtio,bridge=vnet10,firewall=1

# Attach LXC container (ID: 200) network adapter 0 with DHCP
pct set 200 --net0 name=eth0,bridge=vnet10,ip=dhcp,firewall=1

# Set static IP on LXC container attached to SDN VNet
pct set 200 --net0 name=eth0,bridge=vnet10,ip=10.10.10.25/24,gw=10.10.10.1
```

---

## 5. Configuration Files (Cluster Shared in `/etc/pve/sdn/`)

SDN configurations are stored in the cluster-wide Proxmox Cluster File System (pmxcfs):

| File Path | Description |
|---|---|
| `/etc/pve/sdn/zones.cfg` | Defined SDN Zones |
| `/etc/pve/sdn/vnets.cfg` | Defined Virtual Networks (VNets) |
| `/etc/pve/sdn/subnets.cfg` | Subnet IP prefixes, Gateways, SNAT, DHCP ranges |
| `/etc/pve/sdn/controllers.cfg` | BGP / EVPN / ISIS Routing controllers |
| `/etc/pve/sdn/ipam.cfg` | IPAM plugins (PVE, NetBox, phpIPAM) |
| `/etc/pve/sdn/dns.cfg` | PowerDNS / SDN DNS server settings |/home/nishusaini/Desktop/Innspark/Proxmox Cluster/Proxmox SDN/Proxmox_SDN_CLI_Commands.md
| `/etc/network/interfaces.d/sdn` | Locally generated network interface definitions |

You can view configurations directly:
```bash
cat /etc/pve/sdn/zones.cfg
cat /etc/pve/sdn/vnets.cfg
cat /etc/pve/sdn/subnets.cfg
```

---

## 6. Inspection, Verification & Troubleshooting Commands

```bash
# 1. View SDN generated interface definitions on local node
cat /etc/network/interfaces.d/sdn

# 2. Check active Linux network bridges and interfaces
ip -details link show vnet10
bridge link
bridge vlan show

# 3. Check routing table & NAT firewall rules
ip route show
iptables -t nat -L -n -v | grep -i vnet
nft list ruleset | grep -i sdn

# 4. Check DHCP leases (dnsmasq)
cat /var/lib/misc/dnsmasq.leases
journalctl -u dnsmasq -e

# 5. Check EVPN / BGP routing state (FRR)
vtysh -c "show ip bgp summary"
vtysh -c "show evpn vni"
vtysh -c "show bgp l2vpn evpn route"

# 6. Check cluster status & synchronization
pvecm status
systemctl status pve-cluster
```
