import urllib.request
import json

templates = [
    {
        "name": "VyOS Enterprise Router",
        "category": "router",
        "compute_id": "local",
        "template_type": "qemu",
        "symbol": ":/symbols/router.svg",
        "qemu_path": "/usr/bin/qemu-system-x86_64",
        "ram": 1024,
        "cpus": 1,
        "adapters": 4,
        "adapter_type": "virtio-net-pci",
        "port_name_format": "eth{0}",
        "first_port_name": "eth0",
        "cdrom_image": "vyos-1.5-rolling-amd64.iso",
        "hda_disk_image": "empty10G.qcow2",
        "hda_disk_interface": "virtio",
        "boot_priority": "cd",
        "console_type": "telnet",
        "options": "-cpu host",
        "usage": "Default login: vyos / vyos"
    },
    {
        "name": "Alpine Linux Router",
        "category": "router",
        "compute_id": "local",
        "template_type": "qemu",
        "symbol": ":/symbols/router.svg",
        "qemu_path": "/usr/bin/qemu-system-x86_64",
        "ram": 512,
        "cpus": 1,
        "adapters": 4,
        "adapter_type": "virtio-net-pci",
        "port_name_format": "eth{0}",
        "first_port_name": "eth0",
        "cdrom_image": "alpine-virt-3.20.3-x86_64.iso",
        "boot_priority": "c",
        "console_type": "telnet",
        "options": "-cpu host",
        "usage": "Default login: root (no password)"
    },
    {
        "name": "CirrOS Test Node",
        "category": "guest",
        "compute_id": "local",
        "template_type": "qemu",
        "symbol": ":/symbols/computer.svg",
        "qemu_path": "/usr/bin/qemu-system-x86_64",
        "ram": 256,
        "cpus": 1,
        "adapters": 1,
        "adapter_type": "virtio-net-pci",
        "port_name_format": "eth{0}",
        "first_port_name": "eth0",
        "hda_disk_image": "cirros-0.6.2-x86_64-disk.qcow2",
        "hda_disk_interface": "virtio",
        "boot_priority": "c",
        "console_type": "telnet",
        "options": "-cpu host",
        "usage": "Default login: cirros / cubswin:)"
    }
]

for t in templates:
    req = urllib.request.Request(
        "http://127.0.0.1:3080/v2/templates",
        data=json.dumps(t).encode(),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            name = data.get('name')
            t_id = data.get('template_id')
            print(f"Successfully Registered Template: {name} (Template ID: {t_id})")
    except Exception as e:
        print(f"Error registering {t['name']}: {e}")
