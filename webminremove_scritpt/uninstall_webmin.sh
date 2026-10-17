#!/usr/bin/env bash
# ==============================================================================
# Script Name : uninstall_webmin.sh
# Description : Completely uninstalls and purges Webmin, its dependencies, 
#               configuration directories, logs, repository entries, and services.
# Supported OS: Debian, Ubuntu, CentOS, RHEL, Rocky Linux, AlmaLinux, Fedora, SUSE
# ==============================================================================

set -euo pipefail

# Text formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Require root privileges
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root or with sudo."
    exit 1
fi

echo "=========================================================="
echo "          COMPLETE WEBMIN REMOVAL SCRIPT                  "
echo "=========================================================="
log_info "Host: $(hostname -f 2>/dev/null || hostname)"
log_info "Date: $(date)"

# 2. Stop and disable Webmin systemd services
log_info "Stopping and disabling Webmin service..."
if systemctl list-units --full -all | grep -Fq 'webmin.service'; then
    systemctl stop webmin 2>/dev/null || true
    systemctl disable webmin 2>/dev/null || true
fi

# Kill any stubborn miniserv.pl processes
if pgrep -f "miniserv.pl" >/dev/null 2>&1; then
    log_warn "Terminating lingering Webmin (miniserv.pl) processes..."
    pkill -9 -f "miniserv.pl" || true
fi

# 3. Check for Webmin's built-in uninstaller
if [[ -x /etc/webmin/uninstall.sh ]]; then
    log_info "Found official Webmin uninstaller at /etc/webmin/uninstall.sh. Executing..."
    printf "y\n" | /etc/webmin/uninstall.sh || true
fi

# 4. Remove via OS package manager
detect_package_manager() {
    if command -v apt-get >/dev/null 2>&1; then
        echo "apt"
    elif command -v dnf >/dev/null 2>&1; then
        echo "dnf"
    elif command -v yum >/dev/null 2>&1; then
        echo "yum"
    elif command -v zypper >/dev/null 2>&1; then
        echo "zypper"
    elif command -v rpm >/dev/null 2>&1; then
        echo "rpm"
    else
        echo "unknown"
    fi
}

PKG_MGR=$(detect_package_manager)
log_info "Detected package manager: ${PKG_MGR}"

case "$PKG_MGR" in
    apt)
        log_info "Purging Webmin packages via APT..."
        export DEBIAN_FRONTEND=noninteractive
        apt-get purge -y 'webmin*' 'usermin*' 2>/dev/null || true
        apt-get autoremove -y 2>/dev/null || true
        apt-get clean 2>/dev/null || true
        ;;
    dnf)
        log_info "Removing Webmin packages via DNF..."
        dnf remove -y webmin usermin 2>/dev/null || true
        dnf autoremove -y 2>/dev/null || true
        ;;
    yum)
        log_info "Removing Webmin packages via YUM..."
        yum remove -y webmin usermin 2>/dev/null || true
        yum autoremove -y 2>/dev/null || true
        ;;
    zypper)
        log_info "Removing Webmin packages via Zypper..."
        zypper rm -u -y webmin usermin 2>/dev/null || true
        ;;
    rpm)
        log_info "Removing Webmin via RPM..."
        rpm -e webmin usermin 2>/dev/null || true
        ;;
    *)
        log_warn "No recognized package manager found. Skipping package purge."
        ;;
esac

# 5. Clean up residual directories and files
log_info "Removing residual Webmin directories and files..."
TARGET_DIRS=(
    "/etc/webmin"
    "/etc/usermin"
    "/var/webmin"
    "/var/usermin"
    "/usr/share/webmin"
    "/usr/share/usermin"
    "/usr/libexec/webmin"
    "/usr/libexec/usermin"
    "/opt/webmin"
    "/var/log/webmin"
)

for dir in "${TARGET_DIRS[@]}"; do
    if [[ -d "$dir" || -L "$dir" ]]; then
        rm -rf "$dir"
        log_info "Removed directory: $dir"
    fi
done

# 6. Clean up service unit files and init scripts
log_info "Removing leftover service units and scripts..."
SERVICE_FILES=(
    "/etc/init.d/webmin"
    "/etc/init.d/usermin"
    "/etc/systemd/system/webmin.service"
    "/usr/lib/systemd/system/webmin.service"
    "/lib/systemd/system/webmin.service"
)

for file in "${SERVICE_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        rm -f "$file"
        log_info "Removed service file: $file"
    fi
done

systemctl daemon-reload 2>/dev/null || true
systemctl reset-failed 2>/dev/null || true

# 7. Clean up repository definitions and GPG keys
log_info "Removing Webmin repositories and package signing keys..."

# Debian/Ubuntu APT sources & keys
APT_FILES=(
    "/etc/apt/sources.list.d/webmin.list"
    "/etc/apt/sources.list.d/webmin.sources"
    "/etc/apt/trusted.gpg.d/webmin.gpg"
    "/etc/apt/trusted.gpg.d/jcameron-key.gpg"
    "/usr/share/keyrings/webmin.gpg"
)

for apt_file in "${APT_FILES[@]}"; do
    if [[ -f "$apt_file" ]]; then
        rm -f "$apt_file"
        log_info "Removed APT source/key: $apt_file"
    fi
done

# Clean in-file references in /etc/apt/sources.list if any
if [[ -f /etc/apt/sources.list ]] && grep -q "webmin" /etc/apt/sources.list; then
    sed -i '/webmin/d' /etc/apt/sources.list
    log_info "Removed webmin entry from /etc/apt/sources.list"
fi

# RHEL/CentOS YUM/DNF repos
YUM_REPOS=(
    "/etc/yum.repos.d/webmin.repo"
)

for repo_file in "${YUM_REPOS[@]}"; do
    if [[ -f "$repo_file" ]]; then
        rm -f "$repo_file"
        log_info "Removed YUM repo: $repo_file"
    fi
done

# 8. Firewall cleanup (Optional / Information)
log_info "Checking firewall status for port 10000 (default Webmin port)..."
if command -v ufw >/dev/null 2>&1 && ufw status | grep -qw "active"; then
    if ufw status | grep -qw "10000"; then
        log_info "Removing UFW rule for port 10000..."
        ufw delete allow 10000/tcp 2>/dev/null || true
    fi
fi

if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
    if firewall-cmd --list-ports | grep -qw "10000/tcp"; then
        log_info "Removing firewalld rule for port 10000/tcp..."
        firewall-cmd --permanent --remove-port=10000/tcp 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
    fi
fi

# 9. Verification
echo ""
echo "=========================================================="
echo "                  VERIFICATION REPORT                     "
echo "=========================================================="

ERRORS=0

# Check process
if pgrep -f "miniserv.pl" >/dev/null 2>&1; then
    log_error "Webmin process (miniserv.pl) is still running!"
    ERRORS=$((ERRORS + 1))
else
    log_success "No Webmin processes found."
fi

# Check listening port 10000
if command -v ss >/dev/null 2>&1; then
    if ss -tulpn | grep -q ":10000\b"; then
        log_warn "Port 10000 is still in use by another service."
    else
        log_success "Port 10000 is free."
    fi
elif command -v netstat >/dev/null 2>&1; then
    if netstat -tulpn | grep -q ":10000\b"; then
        log_warn "Port 10000 is still in use by another service."
    else
        log_success "Port 10000 is free."
    fi
fi

# Check directories
REMAINING_DIRS=()
for dir in "${TARGET_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        REMAINING_DIRS+=("$dir")
    fi
done

if [[ ${#REMAINING_DIRS[@]} -gt 0 ]]; then
    log_error "Residual directories still exist: ${REMAINING_DIRS[*]}"
    ERRORS=$((ERRORS + 1))
else
    log_success "All Webmin directories successfully purged."
fi

# Check package
if command -v dpkg >/dev/null 2>&1 && dpkg -l | grep -qw "webmin"; then
    log_error "Webmin package still listed in dpkg."
    ERRORS=$((ERRORS + 1))
elif command -v rpm >/dev/null 2>&1 && rpm -qa | grep -qw "webmin"; then
    log_error "Webmin package still listed in rpm."
    ERRORS=$((ERRORS + 1))
else
    log_success "Webmin package is completely uninstalled."
fi

echo "=========================================================="
if [[ $ERRORS -eq 0 ]]; then
    log_success "Webmin has been COMPLETELY removed from this server."
    exit 0
else
    log_warn "Webmin removal completed with warnings/issues. Please review output above."
    exit 1
fi
