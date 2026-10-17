import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import APP_NAME, APP_SECRET
from app.models.database import init_db
from app.routes import api, web, firewall

BASE_DIR = Path(__file__).resolve().parent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema and default records
    init_db()
    # Ensure /etc/nftables.conf is initialized
    try:
        from app.core.nftables import NFTablesEngine
        NFTablesEngine.get_conf_file_info()
    except Exception as e:
        print(f"[WARN] Failed to initialize nftables configuration: {e}")
    yield

app = FastAPI(
    title=APP_NAME,
    description="Modern WireGuard VPN GUI Management Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Secure Session Middleware for Web UI
app.add_middleware(
    SessionMiddleware,
    secret_key=APP_SECRET,
    session_cookie="wiregate_session",
    max_age=86400 * 7, # 7 days
    same_site="lax",
    https_only=False
)

# Mount static directory
static_dir = BASE_DIR / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include Routers
app.include_router(web.router)
app.include_router(api.router)
app.include_router(firewall.router)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": APP_NAME}
