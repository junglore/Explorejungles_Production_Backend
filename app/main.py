"""
Main FastAPI application with Admin Panel
"""

import structlog
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.core.error_handlers import register_error_handlers
from app.db.database import create_tables, get_db_session
from app.api.routes import api_router
# Modern admin panel using FastAPI routes
from app.models.user import User

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Junglore Backend API with Admin Panel...")
    try:
        # Initialize logging
        from app.core.logging_config import logging_config
        
        # Initialize cache
        from app.core.cache import cache_manager
        try:
            await cache_manager.initialize()
        except Exception as e:
            logger.warning(f"Cache initialization failed (non-critical): {e}")
        
        await create_tables()
        await create_default_admin()
        
        # Start leaderboard background jobs (disable for initial deployment)
        try:
            from app.services.leaderboard_jobs import job_manager
            await job_manager.start()
            logger.info("Background jobs started")
        except Exception as e:
            logger.warning(f"Background jobs failed to start (non-critical): {e}")
        
        logger.info("Junglore Backend API started successfully!")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Junglore Backend API...")
    try:
        # Stop leaderboard background jobs
        from app.services.leaderboard_jobs import job_manager
        await job_manager.stop()
        logger.info("Background jobs stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping background jobs: {e}")

async def create_default_admin():
    """Create default admin user if not exists"""
    try:
        from sqlalchemy import select
        async with get_db_session() as db:
            # Check if admin user exists
            result = await db.execute(
                select(User).where(User.email == settings.ADMIN_USERNAME)
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                # Create admin user
                hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
                admin = User(
                    email=settings.ADMIN_USERNAME,
                    hashed_password=hashed_password,
                    username="admin",
                    is_active=True,
                    is_superuser=True
                )
                db.add(admin)
                await db.commit()
                logger.info("Default admin user created")
            else:
                # Check if admin password needs to be updated to match environment variable
                if not verify_password(settings.ADMIN_PASSWORD, admin_user.hashed_password):
                    logger.info("Updating admin password to match environment variable")
                    admin_user.hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
                    await db.commit()
                    logger.info("Admin password updated successfully")
                else:
                    logger.info("Admin user already exists with correct password")
    except Exception as e:
        logger.error(f"Error creating default admin user: {e}")

# Create FastAPI application
app = FastAPI(
    title="Junglore Backend API",
    description="Wildlife Conservation Platform API with Admin Panel",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Add session middleware for admin panel
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=86400  # 24 hours
)

# Custom middleware to force HTTPS in redirect Location headers (PRODUCTION ONLY)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers

class ForceHTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # If it's a redirect (307, 308, 301, 302, 303), force HTTPS in Location header
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if location and location.startswith("http://"):
                # Replace http:// with https://
                response.headers["location"] = location.replace("http://", "https://", 1)
        
        return response

# Only add HTTPS redirect middleware in production
if settings.ENVIRONMENT == "production":
    app.add_middleware(ForceHTTPSRedirectMiddleware)
    logger.info("HTTPS redirect middleware enabled (production mode)")

# Security middleware disabled for development - will implement later
# from app.middleware.security import SecurityHeadersMiddleware, HTTPSRedirectMiddleware
# from app.middleware.rate_limiting import RateLimitMiddleware

# Add rate limiting (disabled for development)
# app.add_middleware(RateLimitMiddleware, default_limit=100, default_window=60)

# Add security headers (disabled for development)
# app.add_middleware(SecurityHeadersMiddleware, force_https=False)

# Add HTTPS redirect (disabled for development)
# app.add_middleware(HTTPSRedirectMiddleware, force_https=True)

# Add large upload middleware
from app.middleware.large_upload import LargeUploadMiddleware
app.add_middleware(LargeUploadMiddleware, max_size=100 * 1024 * 1024)  # 100MB for video/podcast uploads

# Configure for large requests
import os
# Set environment variable for large request handling
os.environ["MAX_CONTENT_LENGTH"] = str(100 * 1024 * 1024)  # 100MB

# Patch multipart library globally
from app.utils.large_multipart import patch_multipart_globally
patch_success = patch_multipart_globally()
if not patch_success:
    logger.warning("Failed to patch multipart library globally")

# Add security middleware
allowed_hosts = ["localhost", "127.0.0.1", "*.junglore.com", "*.railway.app", "*.vercel.app"]
if settings.ENVIRONMENT == "production":
    # Add production domains
    allowed_hosts.extend(["*.railway.app", "*.vercel.app"])

app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=allowed_hosts
)

# Add CORS middleware - handle production vs development
cors_origins = []

# Parse CORS_ORIGINS environment variable
if settings.CORS_ORIGINS:
    parsed_origins = settings.CORS_ORIGINS.split(",")
    cors_origins = [origin.strip() for origin in parsed_origins if origin.strip()]

# Always ensure Vercel frontend URL is included
vercel_url = "https://junglore-ke-frontend.vercel.app"
if vercel_url not in cors_origins:
    cors_origins.append(vercel_url)

if settings.ENVIRONMENT != "production":
    # Development origins
    cors_origins.extend([
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ])

# Remove duplicates while preserving order
cors_origins = list(dict.fromkeys(cors_origins))

# Log CORS origins for debugging
logger.info(f"CORS Origins configured: {cors_origins}")
logger.info(f"Environment: {settings.ENVIRONMENT}")
logger.info(f"Raw CORS_ORIGINS env var: {settings.CORS_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)

# Register error handlers
register_error_handlers(app)

# Define base directory
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "app" / "admin" / "templates"

# Log directory paths for debugging
logger = structlog.get_logger()
logger.info("Directory paths", 
           base_dir=str(BASE_DIR),
           static_dir=str(STATIC_DIR), 
           uploads_dir=str(UPLOADS_DIR),
           templates_dir=str(TEMPLATES_DIR))

# Verify directories exist
for name, path in [("static", STATIC_DIR), ("uploads", UPLOADS_DIR), ("templates", TEMPLATES_DIR)]:
    if not path.exists():
        logger.warning(f"{name} directory does not exist", path=str(path))
        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created {name} directory", path=str(path))

# Include modern admin panel
from app.admin import admin_router
app.include_router(admin_router, prefix="/admin", tags=["admin"])

# Mount static files for uploads
# app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
# Conditional file serving: R2 or local
USE_R2_STORAGE_RAW = settings.USE_R2_STORAGE
logger.info(f"USE_R2_STORAGE setting value: '{USE_R2_STORAGE_RAW}'")
USE_R2_STORAGE = USE_R2_STORAGE_RAW.lower() == 'true'
logger.info(f"R2 storage enabled status: {USE_R2_STORAGE}")

if USE_R2_STORAGE:
    # Serve files from R2 via redirect
    logger.info("R2 storage enabled - files will be served from Cloudflare R2")
    
    import boto3
    from botocore.exceptions import ClientError
    
    @app.get("/uploads/{file_path:path}")
    async def serve_from_r2(file_path: str):
        """Generate presigned URL for R2 file access"""
        try:
            # Clean path (handle both "images/photo.jpg" and "/uploads/images/photo.jpg")
            clean_path = file_path.lstrip('/')
            if clean_path.startswith('uploads/'):
                clean_path = clean_path[8:]  # Remove 'uploads/' prefix
            
            # Initialize R2 client
            r2_client = boto3.client(
                's3',
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name='auto'
            )
            
            # Generate presigned URL (valid for 1 hour)
            presigned_url = r2_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.R2_BUCKET_NAME,
                    'Key': clean_path
                },
                ExpiresIn=3600
            )
            
            # 307 = Temporary Redirect (preserves HTTP method)
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url=presigned_url, status_code=307)
            
        except ClientError as e:
            logger.error(f"R2 file access error: {e}")
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="File not found")
else:
    # Serve files from local disk (development mode)
    logger.info("Local storage enabled - files will be served from disk")
    # Mount static files for uploads
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


# Mount static files for quiz covers and other static content
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount static files for admin panel
app.mount("/admin/static", StaticFiles(directory=str(STATIC_DIR)), name="admin_static")

# Mount static files for admin templates
app.mount("/admin/templates", StaticFiles(directory=str(TEMPLATES_DIR)), name="admin_templates")

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Search routes are already included in api_router

# Include analytics routes
from app.api.endpoints.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])

# Include settings API routes
from app.api.settings_api import router as settings_api_router
app.include_router(settings_api_router, prefix="/api/v1", tags=["settings"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Junglore Backend API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "admin": "/admin"
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint for Railway"""
    return {
        "status": "healthy", 
        "service": "junglore-backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@app.get("/debug/cors")
async def debug_cors():
    """Debug endpoint to check CORS configuration"""
    cors_origins = []
    
    if settings.CORS_ORIGINS:
        parsed_origins = settings.CORS_ORIGINS.split(",")
        cors_origins = [origin.strip() for origin in parsed_origins if origin.strip()]
    
    vercel_url = "https://junglore-ke-frontend.vercel.app"
    if vercel_url not in cors_origins:
        cors_origins.append(vercel_url)
    
    cors_origins = list(dict.fromkeys(cors_origins))
    
    return {
        "status": "debug_info",
        "cors_origins": cors_origins,
        "environment": settings.ENVIRONMENT,
        "raw_cors_origins_env": settings.CORS_ORIGINS,
        "cors_origins_length": len(cors_origins),
        "vercel_url_included": vercel_url in cors_origins
    }

# Simple middleware to protect admin routes using presence of session cookie
@app.middleware("http")
async def admin_auth_middleware(request, call_next):
    path = request.url.path
    if path.startswith("/admin") and not path.startswith("/admin/login"):
        # Check for session cookie presence
        has_session_cookie = "session" in request.cookies
        if not has_session_cookie:
            return RedirectResponse(url="/admin/login")
    return await call_next(request)

# Note: This file is imported by start_with_large_limits.py
# To start the server, run: python3 start_with_large_limits.py