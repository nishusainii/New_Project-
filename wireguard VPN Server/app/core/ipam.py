import ipaddress
from typing import List, Optional

class IPAM:
    """IP Address Management for WireGuard networks."""

    @staticmethod
    def get_next_available_ip(
        server_cidr: str,
        existing_peer_ips: List[str],
        min_host_offset: Optional[int] = None
    ) -> Optional[str]:
        """
        Finds the lowest available IPv4 address within the server subnet.
        Starts after min_host_offset (default 10, e.g. after 172.29.250.10/32 -> starts at .11+).
        """
        try:
            # Parse server interface address and network
            iface = ipaddress.ip_interface(server_cidr.strip())
            network = iface.network
            server_ip = iface.ip
        except ValueError:
            return None

        # Build set of occupied IP addresses
        occupied_ips = {server_ip}
        for peer_ip_str in existing_peer_ips:
            if not peer_ip_str:
                continue
            for item in peer_ip_str.split(","):
                item = item.strip()
                try:
                    p_iface = ipaddress.ip_interface(item)
                    occupied_ips.add(p_iface.ip)
                except ValueError:
                    pass

        # Determine start offset (default to WG_IPAM_START_OFFSET or 10)
        if min_host_offset is None:
            try:
                from app.core.config import WG_IPAM_START_OFFSET
                min_host_offset = WG_IPAM_START_OFFSET
            except Exception:
                min_host_offset = 10

        # Only apply offset if subnet has sufficient capacity
        min_ip = None
        if min_host_offset and network.num_addresses > (min_host_offset + 2):
            min_ip = network.network_address + min_host_offset

        # Iterate through all usable host addresses starting after min_ip
        for host in network.hosts():
            if min_ip and host <= min_ip:
                continue
            if host not in occupied_ips:
                return f"{host}/32"

        return None


    @staticmethod
    def validate_cidr(cidr_str: str) -> bool:
        """Validates if string is a valid IP network/interface."""
        try:
            ipaddress.ip_interface(cidr_str.strip())
            return True
        except ValueError:
            return False

    @staticmethod
    def format_allowed_ips(ip_str: str) -> str:
        """Ensures IP is formatted with CIDR (e.g. 10.8.0.2 -> 10.8.0.2/32)."""
        ip_str = ip_str.strip()
        if "/" not in ip_str:
            return f"{ip_str}/32"
        return ip_str

    @classmethod
    def get_subnet_matrix(cls, server_cidr: str, peer_records: List[dict]) -> dict:
        """
        Generates visual matrix and statistics for the entire subnet pool.
        """
        try:
            iface = ipaddress.ip_interface(server_cidr.strip())
            network = iface.network
            server_ip = iface.ip
        except ValueError:
            return {"error": "Invalid subnet"}

        # Map occupied IPs to peer details
        occupied_map = {}
        for p in peer_records:
            ips_str = p.get("allowed_ips", "")
            for item in ips_str.split(","):
                item = item.strip()
                try:
                    p_ip = ipaddress.ip_interface(item).ip
                    occupied_map[str(p_ip)] = {
                        "name": p.get("name", "Unknown"),
                        "is_active": p.get("is_active", False),
                        "enabled": p.get("enabled", True),
                        "id": p.get("id")
                    }
                except ValueError:
                    pass

        cells = []
        used_count = 0
        all_hosts = list(network.hosts())
        total_hosts = len(all_hosts)

        # For rendering, show up to first 64 or all 254
        for host in all_hosts:
            host_str = str(host)
            last_octet = host_str.split(".")[-1]
            if host == server_ip:
                cells.append({
                    "ip": host_str,
                    "octet": last_octet,
                    "status": "gateway",
                    "label": f"Gateway ({host_str})"
                })
                used_count += 1
            elif host_str in occupied_map:
                info = occupied_map[host_str]
                st = "disabled" if not info["enabled"] else ("active" if info["is_active"] else "offline")
                cells.append({
                    "ip": host_str,
                    "octet": last_octet,
                    "status": st,
                    "label": f"{info['name']} ({host_str})",
                    "peer_id": info["id"]
                })
                used_count += 1
            else:
                cells.append({
                    "ip": host_str,
                    "octet": last_octet,
                    "status": "free",
                    "label": f"Available ({host_str})"
                })

        free_count = total_hosts - used_count
        utilization = round((used_count / total_hosts) * 100, 1) if total_hosts > 0 else 0

        return {
            "network": str(network),
            "gateway": str(server_ip),
            "total_hosts": total_hosts,
            "used_hosts": used_count,
            "free_hosts": free_count,
            "utilization": utilization,
            "cells": cells
        }
