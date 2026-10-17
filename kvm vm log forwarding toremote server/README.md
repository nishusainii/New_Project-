# KVM Linux VM Log Forwarding to Remote Server

This directory contains automated scripts to forward all Linux system, authentication, and service logs from a KVM guest VM (running behind standard NAT) to a remote log server.

No bridge network (br0) is required. Outbound NAT traffic connects directly to the remote server.

---

## Files Included

- setup_guest_vm_forwarding.sh: Run inside the KVM guest VM to forward all logs.
- setup_remote_log_server.sh: Run on the Remote Log Server to receive and organize logs by VM hostname.
- test_log_connection.sh: Test connectivity and trigger test logs.

---

## Network Architecture

[ KVM Guest VM ]
  Internal IP: 192.168.122.x
  Service: Rsyslog (TCP sender)
        |
        v  (Outbound NAT through host virbr0)
[ Base Linux Host ]
  Physical IP: e.g. 10.31.7.48
  NAT Masquerade: Forwards outbound TCP packets
        |
        v  (LAN / WAN network)
[ Remote Log Server ]
  IP: <remote_server_ip>
  Port: 514 (TCP)
  Output: /var/log/remote-nodes/<HOSTNAME>/syslog.log

---

## Quick Setup Instructions

### Step 1: Configure the Remote Log Server (Receiver)

Copy and run the receiver script on your Remote Server:

```bash
sudo ./setup_remote_log_server.sh
```

This will:
- Enable TCP port 514 reception in Rsyslog.
- Open the port in the firewall (UFW / Firewalld).
- Automatically sort logs into `/var/log/remote-nodes/<HOSTNAME>/`.

### Step 2: Configure the KVM Guest VM (Sender)

Copy and run the guest script inside your KVM VM:

```bash
sudo ./setup_guest_vm_forwarding.sh <REMOTE_SERVER_IP>
```
Example:
```bash
sudo ./setup_guest_vm_forwarding.sh 10.31.7.50
```

This will:
- Set up Rsyslog to forward all logs over TCP port 514.
- Configure a local disk queue so logs are not lost if network drops.
- Forward systemd-journald logs to Rsyslog.
- Send an initial verification message.

### Step 3: Test and Verify

Inside the KVM VM, run the diagnostic test:

```bash
./test_log_connection.sh <REMOTE_SERVER_IP>
```

On the Remote Server, check if the logs arrived:

```bash
# View all incoming logs in real time:
sudo tail -f /var/log/remote-nodes/*/syslog.log

# Or view specific VM logs:
sudo ls -la /var/log/remote-nodes/
```

---

## Why No Bridge Network is Needed

1. NAT allows outbound connections: KVM default network (virbr0) performs IP masquerade. Any connection initiated by the VM going outward to an external IP works without custom routing or bridge interfaces.
2. Distinct Hostnames: Even though network packets show the Base Host IP on the wire, Rsyslog embeds the VM hostname into the log payload. The remote server automatically separates VM logs from Base Host logs based on the hostname.
