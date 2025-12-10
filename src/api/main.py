"""
FastAPI Application Main
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import yaml
from pathlib import Path

from .routes import auth, calls, accounts, websocket
from ..database.database import init_db

app = FastAPI(
    title="SIP Trunking API",
    description="REST API for SIP Trunking SaaS Platform",
    version="1.0.0"
)

# Load CORS config
cors_origins = ["*"]
try:
    config_path = Path("config/server_config.yaml")
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if config and 'api' in config:
                cors_origins = config['api'].get('cors_origins', ["*"])
except Exception:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["SIP Accounts"])
app.include_router(calls.router, prefix="/api/v1/calls", tags=["Calls"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    """Serve the dashboard HTML."""
    # Try multiple possible paths
    possible_paths = [
        Path(__file__).parent.parent.parent / "web" / "dashboard.html",  # From src/api/main.py
        Path("web") / "dashboard.html",  # From project root
        Path(".") / "web" / "dashboard.html",  # Relative to current directory
    ]
    
    for dashboard_path in possible_paths:
        if dashboard_path.exists():
            return FileResponse(dashboard_path, media_type="text/html")
    
    # Fallback to JSON response if dashboard not found
    return {
        "message": "SIP Trunking API",
        "version": "1.0.0",
        "docs": "/docs",
        "dashboard": "Dashboard not found. Please ensure web/dashboard.html exists."
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

