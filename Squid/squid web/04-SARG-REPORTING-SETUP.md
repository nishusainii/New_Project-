# Server 2: SARG Reporting Setup & Protected Web Dashboard
**Target Machine:** Server 2 (`proxy.innspark.in` — e.g., `10.31.1.159`)

---

## 1. Overview

**SARG** (Squid Analysis Report Generator) analyzes `/var/log/squid/access.log` to produce granular HTML reports covering:
- **Top users** by bytes transferred and connection counts.
- **Top domains & URLs** visited.
- **Denied/blocked attempts** and security policy violations.
- **Temporal traffic distribution** (peak hours, daily/weekly consumption).

This guide sets up automated report generation and serves the reports securely over Apache with password protection.

---

## 2. Installation (Execute on Server 2)

```bash
sudo apt update
sudo apt install sarg apache2 apache2-utils -y
```

Verify the installation:
```bash
sarg --version
apache2 -v
```

---

## 3. Configure SARG (`/etc/sarg/sarg.conf`)

### Step 3.1: Create HTML Report Root
```bash
sudo mkdir -p /var/www/html/sarg
sudo chown -R www-data:www-data /var/www/html/sarg
sudo chmod 755 /var/www/html/sarg
```

### Step 3.2: Deploy Tuned `sarg.conf`
Backup original configuration and deploy the production version:
```bash
sudo cp /etc/sarg/sarg.conf /etc/sarg/sarg.conf.bak-$(date +%F)
sudo cp configs/sarg.conf /etc/sarg/sarg.conf
```

Key production parameters in `/etc/sarg/sarg.conf`:
- `access_log /var/log/squid/access.log`
- `output_dir /var/www/html/sarg`
- `date_format e` (dd/mm/yyyy)
- `topuser_sort_field BYTES reverse`
- `user_ip yes`
- `graphs yes`
- `records_without_userid ip`

---

## 4. Secure Web Access with Apache & HTTP Authentication

Proxy reports contain internal user names, browsing history, and IP addresses. **They must never be exposed publicly.**

### Step 4.1: Create Admin Credentials for SARG Web Access
```bash
# Create password file with user 'sargadmin'
sudo htpasswd -c /etc/apache2/.sarg_htpasswd sargadmin
```
*(Enter a strong password when prompted, e.g., `SargReport@Innspark2026`).*

To add additional auditors or managers later:
```bash
sudo htpasswd /etc/apache2/.sarg_htpasswd manager1
```

### Step 4.2: Configure Apache VirtualHost
Configure Apache to listen on port `8080` (or your preferred admin port) and enforce authentication for `/var/www/html/sarg`:

```bash
sudo cp configs/apache-sarg.conf /etc/apache2/sites-available/sarg.conf

# Ensure Apache listens on port 8080
if ! grep -q "Listen 8080" /etc/apache2/ports.conf; then
    echo "Listen 8080" | sudo tee -a /etc/apache2/ports.conf
fi

# Enable the SARG site and restart Apache
sudo a2ensite sarg.conf
sudo apache2ctl configtest
sudo systemctl restart apache2
```

---

## 5. Generate Initial Report & Test

### Step 5.1: Run Manual Report Generation
```bash
# Generate report immediately with verbose output
sudo sarg -x
```

### Step 5.2: Verify HTML Output
```bash
ls -l /var/www/html/sarg/
```
You should see directory timestamp folders and `index.html`.

### Step 5.3: Access the Web Dashboard
Open your web browser from an authorized management workstation:
```text
http://10.31.1.159:8080/sarg/
```
- A browser authentication modal will appear.
- **Username:** `sargadmin`
- **Password:** The password configured in Step 4.1.

---

## 6. Automate Daily, Weekly, and Monthly Reports via Cron

To ensure reports are generated automatically and prior to log rotation:

### Step 6.1: Deploy Daily SARG Script
```bash
sudo cp scripts/generate-sarg-daily.sh /usr/local/bin/generate-sarg-daily.sh
sudo chmod +x /usr/local/bin/generate-sarg-daily.sh
```

### Step 6.2: Add Cron Schedule
Open the root crontab:
```bash
sudo crontab -e
```
Add the following entries at the bottom:
```cron
# Innspark SARG Automated Report Schedules
# Daily report at 23:55 PM every day
55 23 * * * /usr/local/bin/generate-sarg-daily.sh > /var/log/sarg-cron.log 2>&1

# Weekly report at 00:15 AM every Monday
15 0 * * 1 /usr/bin/sarg -d $(date --date="7 days ago" +%d/%m/%Y)-$(date --date="yesterday" +%d/%m/%Y)

# Monthly report at 01:00 AM on the 1st of every month
0 1 1 * * /usr/bin/sarg -d $(date --date="1 month ago" +01/%m/%Y)-$(date --date="yesterday" +%d/%m/%Y)
```

---

## 7. Logrotate Coordination

Ensure Squid logs are rotated gracefully without breaking SARG reports:

Edit `/etc/logrotate.d/squid`:
```bash
cat << 'EOF' | sudo tee /etc/logrotate.d/squid
/var/log/squid/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    nocreate
    sharedscripts
    prerotate
        # Generate SARG report before rotating today's logs
        /usr/bin/sarg > /dev/null 2>&1 || true
    endscript
    postrotate
        test ! -e /var/run/squid.pid || test ! -x /usr/sbin/squid || /usr/sbin/squid -k rotate
    endscript
}
EOF
```
