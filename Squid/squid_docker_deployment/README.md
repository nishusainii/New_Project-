# Production-Safe Squid Monitoring Setup

Deploy **Node Exporter**, **Squid Exporter**, and **Blackbox Exporter** in Docker containers to monitor your production Squid proxy on a remote Grafana server without interrupting production traffic.

---

## 1. Why this approach is 100% safe for production

1. **Zero Service Restarts**: Squid never needs to be stopped or restarted.
2. **Resource Capping**: Each container is constrained (`cpus: 0.2`, `memory: 128M`), preventing CPU starvation or OOM incidents.
3. **Zero Network Overhead**: Uses `network_mode: host` to eliminate Docker bridge NAT overhead and allow direct loopback communication (`127.0.0.1`) with Squid.
4. **Isolated Metrics Exposure**: Metrics are exposed on independent ports (`9100`, `9301`, `9115`), which do not interfere with Squid proxy ports (`3128`, `88xx`, etc.).

---

## 2. Pre-Flight Check on Squid Server

### A. Ensure Squid allows `localhost manager`
Verify in your `/etc/squid/squid.conf` that `manager` access is allowed for localhost:
```squid
http_access allow localhost manager
http_access deny manager
```
*(If you need to make changes to `squid.conf`, reload it **without restarting** using: `squid -k reconfigure` or `systemctl reload squid`)*.

### B. Test Cache Manager locally
Run:
```bash
squidclient -p 3128 mgr:info
```
If you see Squid server statistics, the Squid Exporter will work immediately out of the box.

---

## 3. Deploying the Exporters

Navigate to this directory on the Squid server:
```bash
cd /home/nishusaini/squid_docker_deployment
```

### A. (Optional) Set Environment Variables
If Squid is on a non-standard port (not 3128):
```bash
cp .env.example .env
# Edit .env and set SQUID_PORT=your_port
```

### B. Start Containers in Background
```bash
docker compose up -d
```

### C. Verify Running Status
```bash
docker compose ps
```

---

## 4. Local Health Verification

Verify each exporter responds on loopback:

1. **Node Exporter (Port 9100)**:
   ```bash
   curl -s http://127.0.0.1:9100/metrics | head -n 10
   ```
2. **Squid Exporter (Port 9301)**:
   ```bash
   curl -s http://127.0.0.1:9301/metrics | grep squid_
   ```
3. **Blackbox Exporter (Port 9115)**:
   - TCP probe to Squid:
     ```bash
     curl -s "http://127.0.0.1:9115/probe?target=127.0.0.1:3128&module=tcp_connect" | grep probe_success
     ```
   - HTTP probe through Squid:
     ```bash
     curl -s "http://127.0.0.1:9115/probe?target=http://www.google.com&module=squid_http_proxy" | grep probe_success
     ```
   *(A value of `probe_success 1` indicates success)*.

---

## 5. Security & Firewall Configuration

Ensure exporter ports are **only accessible from your remote Prometheus/Grafana server**:

### Using UFW:
```bash
PROMETHEUS_IP="<REMOTE_PROMETHEUS_SERVER_IP>"

sudo ufw allow from $PROMETHEUS_IP to any port 9100 proto tcp comment "Prometheus Node Exporter"
sudo ufw allow from $PROMETHEUS_IP to any port 9301 proto tcp comment "Prometheus Squid Exporter"
sudo ufw allow from $PROMETHEUS_IP to any port 9115 proto tcp comment "Prometheus Blackbox Exporter"
```

### Or using iptables:
```bash
PROMETHEUS_IP="<REMOTE_PROMETHEUS_SERVER_IP>"

sudo iptables -A INPUT -p tcp -s $PROMETHEUS_IP -m multiport --dports 9100,9301,9115 -j ACCEPT
sudo iptables -A INPUT -p tcp -m multiport --dports 9100,9301,9115 -j DROP
```

---

## 6. Remote Prometheus Configuration

On your **remote monitoring server**, edit `/etc/prometheus/prometheus.yml` and append the contents from `prometheus-squid-scrape.yml`.

Replace `<SQUID_SERVER_IP>` with your Squid server's IP address.

Reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
# or
sudo systemctl reload prometheus
```

---

## 7. Recommended Grafana Dashboards

In Grafana (`Dashboards -> New -> Import`):

| Exporter | Recommended Dashboard ID | Name | What it Monitors |
| :--- | :--- | :--- | :--- |
| **Node Exporter** | **1860** | *Node Exporter Full* | Host CPU, RAM, Disk I/O, Network Throughput, System Load |
| **Squid Exporter** | **12501** or **2304** | *Squid Prometheus Exporter* | Cache Hit Rate, Request Rates, Open File Descriptors, Client Count, Bandwidth |
| **Blackbox Exporter**| **7587** or **13659** | *Prometheus Blackbox Exporter* | Port Up/Down status, Response Latency, HTTP Probe Success Through Proxy |
