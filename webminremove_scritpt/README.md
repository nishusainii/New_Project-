# Complete Webmin Removal Scripts

Automated tools to cleanly and completely purge **Webmin** across 4 servers directly from your local machine using **IP, Username, and Password** (**no sudo required on your local machine**).

---

## What Gets Removed on Remote Servers

1. **Services & Processes**:
   - Webmin systemd service stopped, disabled, and removed (`webmin.service`).
   - Lingering background processes killed (`miniserv.pl`).
2. **Official Uninstaller**:
   - Executes `/etc/webmin/uninstall.sh` if it exists.
3. **Package Manager Purge**:
   - Debian/Ubuntu: `apt-get purge --auto-remove -y webmin*`
   - RHEL/CentOS/Rocky/AlmaLinux/Fedora: `dnf/yum remove -y webmin`
   - SUSE: `zypper rm -u -y webmin`
4. **Configuration & Residual Data Directories**:
   - `/etc/webmin`, `/etc/usermin`
   - `/var/webmin`, `/var/usermin`
   - `/usr/share/webmin`, `/usr/share/usermin`
   - `/usr/libexec/webmin`, `/usr/libexec/usermin`
   - `/opt/webmin`, `/var/log/webmin`
5. **Repositories & GPG Keys**:
   - `/etc/apt/sources.list.d/webmin*`
   - `/etc/apt/trusted.gpg.d/webmin*`, `/usr/share/keyrings/webmin.gpg`
   - `/etc/yum.repos.d/webmin.repo`
6. **Firewall Rules**:
   - Removes port 10000 allow rules in `ufw` and `firewalld` (if active).
7. **Verification**:
   - Checks processes, ports, residual directories, and package status, printing a clear verification summary.

---

## How to Run from Your Local Machine (No Local Sudo Needed)

### Step 1: Configure Your 4 Servers
Open [`remove_webmin_multi_server.py`](file:///home/nishusaini/Desktop/Innspark/Web/remove_webmin_multi_server.py) and update the `SERVERS` list with your server details:

```python
SERVERS = [
    {
        "host": "192.168.1.10",
        "user": "root",
        "password": "YourPassword1",  # Or leave "" to be prompted securely
        "port": 22,
    },
    {
        "host": "192.168.1.11",
        "user": "root",
        "password": "YourPassword2",
        "port": 22,
    },
    {
        "host": "192.168.1.12",
        "user": "ubuntu",
        "password": "YourPassword3",
        "port": 22,
    },
    {
        "host": "192.168.1.13",
        "user": "ubuntu",
        "password": "YourPassword4",
        "port": 22,
    },
]
```

> **Note**:
> - If you leave `"password": ""`, the script will prompt you securely in the terminal so you don't have to save passwords in plain text.
> - If the user is non-root (e.g., `ubuntu`), the script automatically handles `sudo` on the remote server using the provided password.

---

### Step 2: Run the Script

You can execute either:
```bash
./remove_webmin_multi_server.sh
```
or:
```bash
python3 remove_webmin_multi_server.py
```
*(No `sudo` is required on your local machine!)*
