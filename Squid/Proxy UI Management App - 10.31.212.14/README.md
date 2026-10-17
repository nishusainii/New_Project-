# Innspark Squid Proxy Management Portal — Dedicated Node 2 (`10.31.212.14`)

Dedicated codebase specifically configured and optimized for the **Audit Proxy Server (`10.31.212.14`)**.

---

## Server Specifications & Network Architecture

| Parameter | Configuration |
| :--- | :--- |
| **Server Hostname** | `offsec-asianetproxy` |
| **IP Address** | `10.31.212.14` |
| **Proxy Port** | **Port 8085** |
| **Active Interface** | `ens18` |
| **Default Gateway** | `10.31.212.1` |
| **Portal Web Port** | `http://10.31.212.14:5000` |
| **SSH Access** | `user1` / `cyberdrift` |
| **Firewall / Network Mode** | **Restricted / Isolated Egress** (Direct public web browsing is denied at firewall; traffic permitted strictly to whitelisted IP destinations like FortiGate SSL-VPN `182.19.54.189:4433`, `13.235.72.170`, `3.21.193.9`). |

---

## Key Customizations in this Codebase

1. **Firewall-Aware Health Probes:**
   * Standard proxy nodes probe public Google/gstatic endpoints. Because `10.31.212.14` has firewall-restricted egress, this codebase tests the local gateway (`10.31.212.1`), socket listener on 8085, and direct destination reachability to `13.235.72.170`.
   * Port 8085 displays **`ONLINE (AUDIT GATEWAY ACTIVE)`** without triggering false "NO INTERNET" alarms.

2. **Accurate Bandwidth Analytics on `ens18`:**
   * Tracks Port 8085 bandwidth directly from interface `ens18` via `vnstat` and `/proc/net/dev` fallback.
   * Tracks daily and monthly data volume, active connections, and unique client counts.

3. **Domain & IP Target Extraction:**
   * Full IP addresses (`13.235.72.170`, `3.21.193.9`, etc.) are recognized and aggregated as first-class destinations in Top Domains and live telemetry streams (unlike standard web proxies which only count `.com`/`.org` domain names).

4. **Intelligent Low-Traffic / Idle Log Fallback:**
   * On low-traffic or intermittent audit servers, if no requests occurred in the chosen time window (e.g. 15 minutes), the dashboard and log streams automatically display the latest audit events with an idle fallback indicator `(Latest Audit Logs · Idle in last 15 Mins)`.

5. **OpenFortiVPN & Allowed IPs Management:**
   * Full management of `/etc/squid/allowed_ips.txt` and `/etc/squid/openfortivpn_clients.txt`.

6. **SARG Report Auto-Unlock:**
   * Authenticated portal admins automatically bypass the static SARG PIN gate when accessing analytics reports.

---

## One-Click Deployment to `10.31.212.14`

To sync any changes made in this folder directly to the remote server, simply run:

```bash
python3 deploy_to_212_14.py
```

This packages the code, securely uploads it to `10.31.212.14`, updates `/opt/innspark-squid-portal/`, sets permissions, and restarts the systemd service.
