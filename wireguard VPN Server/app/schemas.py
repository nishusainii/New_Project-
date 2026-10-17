from typing import Optional
from pydantic import BaseModel, Field

class PeerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80, description="Friendly peer name / device name")
    allowed_ips: Optional[str] = Field(None, description="Client VPN IP (e.g. 172.29.250.11/32). If omitted, next IP is auto-assigned.")

    public_key: Optional[str] = Field(None, description="Existing public key. If omitted, a keypair is automatically generated.")
    psk: Optional[str] = Field(None, description="Pre-shared key. If true/empty, can be auto-generated or left blank.")
    generate_psk: bool = Field(False, description="Whether to automatically generate a pre-shared key.")
    keepalive: int = Field(25, ge=0, le=3600)
    endpoint: Optional[str] = Field(None)
    device_type: str = Field("laptop", description="Device category: laptop, phone, desktop, server")
    tunnel_mode: str = Field("full", description="full (0.0.0.0/0) or split (VPN subnet only)")
    custom_allowed_ips: Optional[str] = Field(None, description="Optional custom AllowedIPs for client config")

class PeerUpdate(BaseModel):
    name: Optional[str] = None
    allowed_ips: Optional[str] = None
    enabled: Optional[bool] = None
    keepalive: Optional[int] = None
    endpoint: Optional[str] = None
    device_type: Optional[str] = None
    tunnel_mode: Optional[str] = None

class ServerUpdate(BaseModel):
    address: str
    listen_port: int
    endpoint: Optional[str] = None
    dns: Optional[str] = None
    mtu: int = 1420
    extra_directives: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class FirewallPolicyUpdate(BaseModel):
    client_isolation: bool
    internet_access: bool
    allow_dns: bool
    default_forward_policy: str = "drop"
    mss_clamping: Optional[bool] = True
    drop_invalid: Optional[bool] = True
    icmp_limit: Optional[bool] = True
    log_dropped: Optional[bool] = False
    auto_backup: Optional[bool] = True

class WireGuardAclCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    peer_id: Optional[int] = None
    src_cidr: Optional[str] = None
    dst_cidr: str = "any"
    proto: str = "all" # all, tcp, udp, icmp
    ports: Optional[str] = None # e.g. 80,443
    action: str = "accept" # accept, drop, reject

class CustomRuleCreate(BaseModel):
    family: str = "inet"
    table: str = "wiregate"
    chain: str = "wg_forward"
    statement: str = Field(..., min_length=3)
    comment: Optional[str] = None

class ValidateConfigInput(BaseModel):
    config: str
