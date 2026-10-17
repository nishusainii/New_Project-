"""
sslvpn - Custom SSL VPN server/client (pure Python stdlib).

An SSL VPN that tunnels raw IP packets over a TLS 1.2/1.3 connection.
Fully customizable via JSON config: auth modes, per-user ACLs, bandwidth
throttling, IP pools and TLS settings.
"""

__version__ = "1.0.0"
__author__ = "Innspark Testing Project"

PROTOCOL_VERSION = 1