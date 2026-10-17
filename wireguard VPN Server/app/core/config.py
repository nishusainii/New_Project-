import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

APP_NAME = os.environ.get("APP_NAME", "WireGate Control Center")
APP_SECRET = os.environ.get("APP_SECRET", "wireguard-management-secret-change-in-prod-32bytes")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# WireGuard Execution Mode: 'direct' (runs wg CLI), 'agent' (host agent via HTTP HMAC), 'dry-run' (mock/preview)
WG_EXECUTION_MODE = os.environ.get("WG_EXECUTION_MODE", "direct")
WG_INTERFACE = os.environ.get("WG_INTERFACE", "wg0")
WG_CONFIG_PATH = os.environ.get("WG_CONFIG_PATH", "/etc/wireguard/wg0.conf")
WG_DEFAULT_ADDRESS = os.environ.get("WG_DEFAULT_ADDRESS", "172.29.250.1/24")
WG_DEFAULT_PORT = int(os.environ.get("WG_DEFAULT_PORT", "443"))
WG_DEFAULT_DNS = os.environ.get("WG_DEFAULT_DNS", "")
WG_DEFAULT_ENDPOINT = os.environ.get("WG_DEFAULT_ENDPOINT", "")
WG_DEFAULT_MTU = int(os.environ.get("WG_DEFAULT_MTU", "1420"))
WG_IPAM_START_OFFSET = int(os.environ.get("WG_IPAM_START_OFFSET", "10"))


# Host Agent settings (if used)
WG_AGENT_URL = os.environ.get("WG_AGENT_URL", "http://host.docker.internal:9081")
WG_AGENT_TOKEN = os.environ.get("WG_AGENT_TOKEN", "")

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR}/wireguard.db")
