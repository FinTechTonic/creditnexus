"""FastAPI application entry point for CreditNexus backend."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import router
from app.auth.routes import auth_router
from app.auth.jwt_auth import jwt_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    if os.environ.get("DATABASE_URL"):
        try:
            from app.db import init_db
            init_db()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    else:
        logger.warning("DATABASE_URL not set, skipping database initialization")
    yield


app = FastAPI(
    title="CreditNexus API",
    description="FINOS-Compliant Financial AI Agent for Credit Agreement Extraction",
    version="1.0.0",
    lifespan=lifespan
)

session_secret = os.environ.get("SESSION_SECRET")
is_production = os.environ.get("REPLIT_DEPLOYMENT") == "1"

if not session_secret:
    if is_production:
        raise RuntimeError("SESSION_SECRET must be set in production")
    logger.warning("SESSION_SECRET not set, generating temporary secret (not suitable for production)")
    import secrets
    session_secret = secrets.token_hex(32)

app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="creditnexus_session",
    max_age=86400 * 7,
    same_site="lax",
    https_only=is_production,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router, prefix="/api")
app.include_router(jwt_router, prefix="/api")

# Serve OpenFin manifest files
openfin_dir = Path(__file__).parent / "openfin"
if openfin_dir.exists():
    @app.get("/openfin/app.json")
    async def serve_openfin_manifest():
        """Serve the OpenFin application manifest."""
        manifest_path = openfin_dir / "app.json"
        if manifest_path.exists():
            return FileResponse(str(manifest_path), media_type="application/json")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="OpenFin manifest not found")
    
    @app.get("/openfin/{filename}")
    async def serve_openfin_file(filename: str):
        """Serve other OpenFin configuration files."""
        file_path = openfin_dir / filename
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path), media_type="application/json")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")

static_dir = Path(__file__).parent / "client" / "dist"
if static_dir.exists():
    logger.info(f"Serving static files from {static_dir}")
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the frontend application."""
        return FileResponse(str(static_dir / "index.html"))
    
    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        """Catch-all route for SPA routing."""
        file_path = static_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(static_dir / "index.html"))
else:
    logger.warning("Static files not found, running in API-only mode")
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "CreditNexus API",
            "docs": "/docs",
            "health": "/api/health"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
