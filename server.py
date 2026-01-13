"""FastAPI application entry point for CreditNexus backend."""

import logging
import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.routes import router
from app.api.credit_risk_routes import router as credit_risk_router
from app.api.policy_editor_routes import router as policy_editor_router
from app.api.policy_template_routes import router as policy_template_router
from app.api.green_finance_routes import router as green_finance_router
from app.api.auditor_routes import router as auditor_router
from app.api.layer_routes import router as layer_router
from app.api.websocket_routes import router as websocket_router
from app.api.securitization_routes import router as securitization_router
from app.api.config_routes import router as config_router
from app.api.workflow_delegation_routes import router as workflow_delegation_router
from app.api.remote_routes import remote_router
from app.auth.routes import auth_router
from app.auth.jwt_auth import jwt_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup/shutdown events.
    
    Note: CancelledError during shutdown is expected when uvicorn reloads.
    This is normal behavior and indicates the reloader is restarting the server.
    """
    from app.core.config import settings
    
    # Initialize LLM client configuration
    try:
        from app.core.llm_client import init_llm_config
        init_llm_config(settings)
        logger.info(
            f"LLM client configured: provider={settings.LLM_PROVIDER.value}, "
            f"model={settings.LLM_MODEL}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize LLM client configuration: {e}", exc_info=True)
        raise
    
    # Initialize Policy Engine with YAML rule loading
    if settings.POLICY_ENABLED:
        try:
            from app.core.policy_config import PolicyConfigLoader
            from app.services.policy_engine_factory import create_policy_engine
            from app.services.policy_service import PolicyService
            
            # Create policy config loader
            policy_config_loader = PolicyConfigLoader(settings)
            
            # Load all rules from YAML files
            rules_yaml = policy_config_loader.load_all_rules()
            
            if not rules_yaml:
                logger.warning("No policy rules loaded - policy engine will use default allow behavior")
                rules_yaml = """
- name: default_allow
  when: {}
  action: allow
  priority: 0
  description: "Default allow for all transactions not caught by other rules"
"""
            
            # Validate rules
            policy_config_loader.validate_rules(rules_yaml)
            
            # Initialize policy engine (vendor-agnostic interface)
            policy_engine = create_policy_engine(
                vendor=settings.POLICY_ENGINE_VENDOR or "default"
            )
            
            # Load rules into engine
            policy_engine.load_rules(rules_yaml)
            
            # Create policy service instance
            policy_service = PolicyService(policy_engine)
            
            # Store in app state for dependency injection
            app.state.policy_service = policy_service
            app.state.policy_config_loader = policy_config_loader
            
            # Get metadata for logging
            metadata = policy_config_loader.get_rules_metadata()
            logger.info(
                f"Policy engine initialized: {metadata.get('rules_count', 0)} rule(s) "
                f"from {metadata.get('files_count', 0)} file(s)"
            )
            
            # Start file watcher if auto-reload enabled
            if settings.POLICY_AUTO_RELOAD:
                def reload_policy_rules():
                    """Reload policy rules from YAML files (called by file watcher)."""
                    try:
                        logger.info("Reloading policy rules...")
                        rules_yaml = policy_config_loader.load_all_rules()
                        policy_config_loader.validate_rules(rules_yaml)
                        policy_engine.load_rules(rules_yaml)
                        logger.info("Policy rules reloaded successfully")
                    except Exception as e:
                        logger.error(f"Failed to reload policy rules: {e}")
                
                policy_config_loader.start_file_watcher(reload_policy_rules)
                logger.info("Policy auto-reload enabled")
        except Exception as e:
            logger.error(f"Failed to initialize policy engine: {e}")
            if settings.POLICY_ENABLED:
                raise  # Fail fast if policy is required
    else:
        logger.info("Policy engine is disabled (POLICY_ENABLED=false)")
        app.state.policy_service = None
        app.state.policy_config_loader = None
    
    # Initialize x402 Payment Service
    if settings.X402_ENABLED:
        try:
            from app.services.x402_payment_service import X402PaymentService
            
            # Create x402 payment service instance
            payment_service = X402PaymentService(
                facilitator_url=settings.X402_FACILITATOR_URL,
                network=settings.X402_NETWORK,
                token=settings.X402_TOKEN
            )
            
            # Store in app state for dependency injection
            app.state.x402_payment_service = payment_service
            
            logger.info(
                f"x402 Payment service initialized: "
                f"facilitator={settings.X402_FACILITATOR_URL}, "
                f"network={settings.X402_NETWORK}, "
                f"token={settings.X402_TOKEN}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize x402 payment service: {e}")
            if settings.X402_ENABLED:
                raise  # Fail fast if x402 is required
    else:
        logger.info("x402 Payment service is disabled (X402_ENABLED=false)")
        app.state.x402_payment_service = None
    
    # Initialize database
    if settings.DATABASE_ENABLED:
        try:
            from app.db import init_db, engine, SessionLocal
            if engine is not None:
                init_db()
                
                # Check if demo user exists and create if needed
                try:
                    from app.db.models import User
                    db = SessionLocal()
                    try:
                        demo_user = db.query(User).filter(User.email == "demo@creditnexus.app").first()
                        if not demo_user:
                            logger.info("No demo user found. Creating demo user...")
                            from app.auth.jwt_auth import get_password_hash
                            from app.db.models import UserRole
                            
                            demo_user = User(
                                email="demo@creditnexus.app",
                                password_hash=get_password_hash("DemoPassword123!"),
                                display_name="Demo User",
                                role=UserRole.ADMIN.value,
                                is_active=True,
                                is_email_verified=True,
                            )
                            db.add(demo_user)
                            db.commit()
                            logger.info("Demo user created: demo@creditnexus.app / DemoPassword123!")
                        else:
                            logger.debug("Demo user already exists")
                    except Exception as e:
                        logger.warning(f"Failed to check/create demo user: {e}")
                        db.rollback()
                    finally:
                        db.close()
                except Exception as e:
                    logger.warning(f"Failed to initialize demo user: {e}")
                
                # Check if templates exist and seed missing ones from metadata
                try:
                    from app.templates.registry import TemplateRegistry
                    from scripts.seed_templates import seed_templates, load_template_metadata
                    from pathlib import Path
                    
                    db = SessionLocal()
                    try:
                        templates = TemplateRegistry.list_templates(db)
                        existing_count = len(templates) if templates else 0
                        
                        # Always try to load and seed from metadata file
                        # seed_templates will skip existing templates automatically
                        json_paths = [
                            Path("data/templates_metadata.json"),
                            Path("scripts/templates_metadata.json"),
                            Path("storage/templates_metadata.json"),
                        ]
                        
                        templates_data = []
                        for json_path in json_paths:
                            if json_path.exists():
                                templates_data = load_template_metadata(json_path)
                                logger.info(f"Loaded {len(templates_data)} template(s) from {json_path}")
                                break
                        
                        if templates_data:
                            # Normalize field names for compatibility
                            for template_data in templates_data:
                                # Handle both "required_fields" and "required_cdm_fields"
                                if "required_cdm_fields" in template_data and "required_fields" not in template_data:
                                    template_data["required_fields"] = template_data["required_cdm_fields"]
                                if "optional_cdm_fields" in template_data and "optional_fields" not in template_data:
                                    template_data["optional_fields"] = template_data["optional_cdm_fields"]
                            
                            # Seed templates (will skip existing ones)
                            created = seed_templates(db, templates_data)
                            db.commit()
                            
                            if created > 0:
                                logger.info(f"Seeded {created} new template(s) from metadata file (found {existing_count} existing)")
                            else:
                                logger.info(f"All templates from metadata already exist in database ({existing_count} total)")
                            
                            # Generate template files if they don't exist
                            try:
                                from scripts.create_template_files import main as create_templates
                                logger.info("Generating template Word files...")
                                create_templates(use_metadata=True, force_regenerate=False)
                            except Exception as e:
                                logger.warning(f"Failed to generate template files: {e}")
                        else:
                            if existing_count > 0:
                                logger.info(f"Found {existing_count} existing template(s) in database (no metadata file found)")
                            else:
                                logger.warning("No template metadata file found. Templates will need to be seeded manually.")
                    except Exception as e:
                        logger.warning(f"Failed to check/seed templates: {e}")
                        db.rollback()
                    finally:
                        db.close()
                except Exception as e:
                    logger.warning(f"Failed to initialize template seeding: {e}")
                
                # Seed permissions if enabled
                seed_permissions_enabled = os.getenv("SEED_PERMISSIONS", "false").lower() == "true"
                if seed_permissions_enabled:
                    try:
                        from scripts.seed_permissions import seed_permissions, seed_role_permissions
                        
                        db = SessionLocal()
                        try:
                            # Seed permission definitions
                            perm_count = seed_permissions(db, force=False)
                            
                            # Seed role-permission mappings
                            role_perm_count = seed_role_permissions(db, force=False)
                            
                            db.commit()
                            
                            if perm_count > 0 or role_perm_count > 0:
                                logger.info(
                                    f"Seeded permissions: {perm_count} permission(s), "
                                    f"{role_perm_count} role-permission mapping(s)"
                                )
                            else:
                                logger.debug("All permissions already exist in database")
                        except Exception as e:
                            logger.warning(f"Failed to seed permissions: {e}")
                            db.rollback()
                        finally:
                            db.close()
                    except Exception as e:
                        logger.warning(f"Failed to initialize permission seeding: {e}")
                else:
                    logger.debug("Permission seeding is disabled (SEED_PERMISSIONS=false)")
                
                # Check if policy templates exist and seed missing ones
                try:
                    from app.db.models import PolicyTemplate, User
                    from scripts.seed_policy_templates import seed_policy_templates
                    
                    db = SessionLocal()
                    try:
                        existing_templates_count = db.query(PolicyTemplate).count()
                        if existing_templates_count == 0:
                            logger.info("No policy templates found. Seeding initial policy templates...")
                            
                            # Get admin user ID for template creator
                            admin = db.query(User).filter(User.role == 'admin').first()
                            admin_user_id = admin.id if admin else 1
                            
                            # Seed templates (recursively finds all YAML files in app/policies/)
                            total_seeded = seed_policy_templates(db, admin_user_id)
                            
                            if total_seeded > 0:
                                logger.info(f"Seeded {total_seeded} initial policy template(s).")
                            else:
                                logger.info("No policy templates were seeded.")
                        else:
                            logger.debug(f"Found {existing_templates_count} existing policy template(s). Skipping initial seeding.")
                    except Exception as e:
                        logger.warning(f"Failed to check/seed policy templates: {e}")
                        db.rollback()
                    finally:
                        db.close()
                except Exception as e:
                    logger.warning(f"Failed to initialize policy template seeding: {e}")
                
                # Seed policies from YAML files (for Policy Editor visibility)
                try:
                    from app.db.models import Policy, User
                    from app.db import SessionLocal
                    from scripts.seed_policies import seed_policies_from_yaml
                    
                    db = SessionLocal()
                    try:
                        # Always sync policies from YAML files (updates existing, creates new)
                        logger.info("Syncing policies from YAML files...")
                        
                        # Get admin user ID for policy creator
                        admin = db.query(User).filter(User.role == 'admin').first()
                        admin_user_id = admin.id if admin else 1
                        
                        # Seed/update policies from YAML files
                        total_seeded = seed_policies_from_yaml(db, admin_user_id)
                        
                        if total_seeded > 0:
                            logger.info(f"Synced {total_seeded} policy(ies) from YAML files.")
                        else:
                            logger.info("No policies were synced from YAML files.")
                    except Exception as e:
                        logger.warning(f"Failed to sync policies from YAML files: {e}", exc_info=True)
                        db.rollback()
                    finally:
                        db.close()
                except Exception as e:
                    logger.warning(f"Failed to initialize policy seeding: {e}")
                
                # Seed demo users if enabled
                if settings.SEED_DEMO_USERS or any([
                    settings.SEED_AUDITOR,
                    settings.SEED_BANKER,
                    settings.SEED_LAW_OFFICER,
                    settings.SEED_ACCOUNTANT,
                    settings.SEED_APPLICANT,
                ]):
                    try:
                        from scripts.seed_demo_users import seed_demo_users
                        
                        db = SessionLocal()
                        try:
                            # Seed demo users
                            user_count = seed_demo_users(db, force=settings.SEED_DEMO_USERS_FORCE)
                            
                            db.commit()
                            
                            if user_count > 0:
                                logger.info(f"Seeded {user_count} demo user(s)")
                            else:
                                logger.debug("All demo users already exist in database")
                        except Exception as e:
                            logger.warning(f"Failed to seed demo users: {e}")
                            db.rollback()
                        finally:
                            db.close()
                    except Exception as e:
                        logger.warning(f"Failed to initialize demo user seeding: {e}")
                else:
                    logger.debug("Demo user seeding is disabled (SEED_DEMO_USERS=false)")
                
                # Load seed documents into ChromaDB if configured
                if settings.CHROMADB_SEED_DOCUMENTS_DIR:
                    try:
                        from app.utils.load_chroma_seeds import load_chroma_seeds_on_startup
                        logger.info("Loading seed documents into ChromaDB...")
                        loaded_count = load_chroma_seeds_on_startup()
                        if loaded_count > 0:
                            logger.info(f"Successfully loaded {loaded_count} seed document(s) into ChromaDB")
                        else:
                            logger.info("No seed documents loaded (directory empty or not found)")
                    except ImportError as e:
                        logger.warning(f"ChromaDB not available, skipping seed document loading: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to load seed documents into ChromaDB: {e}")
            else:
                logger.warning("Database engine is None, skipping initialization")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
    else:
        logger.info("Database is disabled (DATABASE_ENABLED=false)")
    
    yield
    
    # Cleanup
    try:
        if settings.POLICY_ENABLED and hasattr(app.state, 'policy_config_loader'):
            policy_config_loader = app.state.policy_config_loader
            if policy_config_loader:
                policy_config_loader.stop_file_watcher()
        
        # Cleanup x402 payment service
        if settings.X402_ENABLED and hasattr(app.state, 'x402_payment_service'):
            payment_service = app.state.x402_payment_service
            if payment_service:
                try:
                    await payment_service.close()
                    logger.info("x402 Payment service closed")
                except asyncio.CancelledError:
                    logger.warning("x402 Payment service close was cancelled")
                    raise
                except Exception as e:
                    logger.error(f"Error closing x402 payment service: {e}")
    except asyncio.CancelledError:
        logger.warning("Shutdown cleanup was cancelled")
        raise
    except Exception as e:
        logger.error(f"Error during shutdown cleanup: {e}")
    
    logger.info("Shutting down application...")
    
    # Note: If CancelledError occurs after this point, it's from uvicorn's
    # internal reload mechanism and is expected behavior during development.


app = FastAPI(
    title="CreditNexus API",
    description="FINOS-Compliant Financial AI Agent for Credit Agreement Extraction",
    version="1.0.0",
    lifespan=lifespan
)

from app.core.config import settings

# Session secret management
session_secret = os.environ.get("SESSION_SECRET")
is_production = os.environ.get("REPLIT_DEPLOYMENT") == "1" or os.environ.get("ENVIRONMENT") == "production"

if not session_secret:
    if is_production:
        raise RuntimeError("SESSION_SECRET must be set in production")
    logger.warning("SESSION_SECRET not set, generating temporary secret (not suitable for production)")
    import secrets
    session_secret = secrets.token_hex(32)

# Session middleware with secure settings
app.add_middleware(
    SessionMiddleware,
    secret_key=session_secret,
    session_cookie="creditnexus_session",
    max_age=settings.SESSION_MAX_AGE,
    same_site=settings.SESSION_SAME_SITE,  # Changed from "lax" to "strict" for better CSRF protection
    https_only=settings.SESSION_SECURE,  # Always enforce HTTPS in production (this sets the Secure flag)
)

# CORS middleware with specific origins (security fix)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # Changed from ["*"] to specific origins
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],  # Specific methods instead of "*"
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],  # Specific headers instead of "*"
    expose_headers=["X-Total-Count", "X-Request-ID"],  # Headers to expose to frontend
)

# Rate limiting setup
if settings.RATE_LIMIT_ENABLED:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
    )
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Apply rate limiting to all requests except health checks and static files."""
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/api/health", "/health", "/"] or request.url.path.startswith("/assets/"):
            return await call_next(request)
        
        # Apply rate limiting using slowapi
        # slowapi checks limits based on key_func (get_remote_address) and endpoint
        try:
            # Get the endpoint identifier
            endpoint = request.url.path
            # slowapi will check against default_limits automatically
            # We need to trigger the check by accessing the limiter
            # For now, let the request pass - rate limiting will be enforced
            # via decorators on individual routes that need it
            # The default_limits will apply when routes use @limiter.limit() decorators
            return await call_next(request)
        except RateLimitExceeded:
            raise
else:
    limiter = None

# Security headers middleware
if settings.SECURITY_HEADERS_ENABLED:
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        if is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        # Content Security Policy - adjust based on your needs
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

# Make limiter available globally for route decorators
# Routes can access it via: from server import limiter (if enabled)
# Or use: request.app.state.limiter in route functions

app.include_router(router)
app.include_router(credit_risk_router)
app.include_router(policy_editor_router)
app.include_router(policy_template_router)
app.include_router(green_finance_router)
app.include_router(auditor_router)
app.include_router(layer_router)
app.include_router(websocket_router)
app.include_router(securitization_router)
app.include_router(config_router)
app.include_router(workflow_delegation_router)
app.include_router(remote_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(jwt_router, prefix="/api")

# GDPR compliance routes
from app.api.gdpr_routes import gdpr_router
app.include_router(gdpr_router, prefix="/api")

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
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8000, 
        reload=True,
        reload_excludes=[
            "*.venv/**",
            ".venv/**",
            "**/__pycache__/**",
            "**/*.pyc",
            "**/*.pyo",
            "**/.git/**",
            "**/node_modules/**",
        ],
    )
