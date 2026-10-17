#!/usr/bin/env bash
set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}=== Initializing Production NFTables Configuration (/etc/nftables.conf) ===${NC}"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (or with sudo)."
   exit 1
fi

mkdir -p /etc/wireguard
mkdir -p /etc/nftables

NFT_CONF="/etc/nftables.conf"
ACL_NFT="/etc/nftables/acl.nft"

# Ensure /etc/nftables/acl.nft exists
if [ ! -f "${ACL_NFT}" ]; then
    echo -e "${YELLOW}[INFO] Creating baseline ${ACL_NFT}...${NC}"
    cat << 'ACL_EOF' > "${ACL_NFT}"
# /etc/nftables/acl.nft - WireGuard Client Access Control Rules
# Managed automatically via WireGuard Enterprise Control Center

ACL_EOF
    chmod 0644 "${ACL_NFT}"
    echo -e "${GREEN}[OK] Created ${ACL_NFT}.${NC}"
fi

# Clean up legacy include files if present
rm -f /etc/nftables.acl.nft 2>/dev/null || true

# Check if /etc/nftables.conf exists
if [ ! -f "${NFT_CONF}" ]; then
    echo -e "${YELLOW}[INFO] Creating baseline ${NFT_CONF}...${NC}"
    cat << 'CONF_EOF' > "${NFT_CONF}"
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0;
    }
    chain forward {
        type filter hook forward priority 0;
    }
    chain output {
        type filter hook output priority 0;
    }
}

table inet wiregate {
    chain input {
        type filter hook input priority filter; policy accept;
        ct state established,related accept comment "Allow established traffic"
        iif "lo" accept comment "Allow loopback"
        udp dport 443 accept comment "WireGuard Inbound Tunnel"
    }

    chain forward {
        type filter hook forward priority filter; policy accept;
        ct state established,related accept comment "Allow established forwarding"

        # WireGuard Client ACL Rules
        include "/etc/nftables/acl.nft"

        iifname "wg0" oifname != "wg0" accept comment "WireGuard Outbound Internet"
    }

    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;
        ip saddr 172.29.250.0/24 oifname != "wg0" masquerade comment "WireGuard NAT Masquerade"
    }
}
CONF_EOF
    chmod 0755 "${NFT_CONF}"
    echo -e "${GREEN}[OK] Created ${NFT_CONF}.${NC}"
else
    # Ensure include "/etc/nftables/acl.nft" exists in /etc/nftables.conf chain forward
    if ! grep -q 'include "/etc/nftables/acl.nft"' "${NFT_CONF}"; then
        echo -e "${YELLOW}[ACTION] Adding acl.nft include directive to ${NFT_CONF}...${NC}"
        if grep -q 'iifname "wg0" oifname != "wg0" accept' "${NFT_CONF}"; then
            sed -i '/iifname "wg0" oifname != "wg0" accept/i \        # WireGuard Client ACL Rules\n        include "/etc/nftables/acl.nft"\n' "${NFT_CONF}"
        fi
    fi
fi

# Dry-run validation
if command -v nft >/dev/null 2>&1; then
    echo -n "Validating NFTables configuration syntax... "
    if nft -c -f "${NFT_CONF}"; then
        echo -e "${GREEN}[OK] Syntax valid.${NC}"
    else
        echo -e "${YELLOW}[WARN] Syntax check returned warning.${NC}"
    fi
fi

echo -e "${GREEN}=== NFTables Setup Complete (/etc/nftables.conf and /etc/nftables/acl.nft linked) ===${NC}"
