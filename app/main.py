"""
CareerCopilot AI - Main Application Entry Point

Production-grade FastAPI application with:
- Structured observability (logging, tracing)
- Security middleware (rate limiting, sanitization)
- AI orchestration layer
- Explainable analysis outputs
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import engine, Base, SessionLocal
from app.models import all_models  # Import models to register them
from app.services.seeder import seed_templates

# Middleware imports
from app.middleware.security import (
    RateLimitMiddleware,
    InputSanitizationMiddleware,
    SecurityHeadersMiddleware,
    CORS_CONFIG
)
from app.middleware.observability import (
    RequestTracingMiddleware,
    StructuredLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    logger
)

# Create tables (for dev purposes - use Alembic in prod)
Base.metadata.create_all(bind=engine)

# Application version
APP_VERSION = "2.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # =========================================================================
    # STARTUP
    # =========================================================================
    logger.info(
        "Application starting",
        version=APP_VERSION,
        environment=settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else "development"
    )
    
    # Seed initial data
    db = SessionLocal()
    try:
        seed_templates(db)
        logger.info("Database seeding completed")
    except Exception as e:
        logger.error("Database seeding failed", error=str(e))
    finally:
        db.close()
    
    # Initialize AI orchestrator (lazy loading)
    try:
        from app.ai.orchestrator import AIOrchestrator
        app.state.ai_orchestrator = AIOrchestrator()
        logger.info("AI orchestrator initialized")
    except Exception as e:
        logger.warning("AI orchestrator initialization skipped", error=str(e))
        app.state.ai_orchestrator = None
    
    logger.info("Application startup complete")
    
    yield
    
    # =========================================================================
    # SHUTDOWN
    # =========================================================================
    logger.info("Application shutting down")


# =============================================================================
# APPLICATION FACTORY
# =============================================================================

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered career copilot for resume optimization and job matching",
    version=APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)


# =============================================================================
# MIDDLEWARE STACK (order matters - last added = first executed)
# =============================================================================

# 1. CORS (must be first to handle preflight)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_CONFIG.get("allow_origins", settings.BACKEND_CORS_ORIGINS),
    allow_credentials=CORS_CONFIG.get("allow_credentials", True),
    allow_methods=CORS_CONFIG.get("allow_methods", ["*"]),
    allow_headers=CORS_CONFIG.get("allow_headers", ["*"]),
    expose_headers=CORS_CONFIG.get("expose_headers", [])
)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. Request tracing (assigns request IDs)
app.add_middleware(RequestTracingMiddleware)

# 4. Performance monitoring
app.add_middleware(PerformanceMonitoringMiddleware, slow_threshold_ms=2000)

# 5. Rate limiting (configurable per endpoint)
app.add_middleware(
    RateLimitMiddleware,
    default_rate=100,  # 100 requests per minute
    default_burst=20,
    endpoint_limits={
        r"/api/v1/analyze.*": {"rate": 20, "burst": 5},  # Stricter for AI endpoints
        r"/api/v1/chat.*": {"rate": 30, "burst": 10},
        r"/api/v1/resume/upload": {"rate": 10, "burst": 3}
    },
    exempt_paths=["/health", "/api/v1/docs", "/api/v1/openapi.json"]
)

# 6. Input sanitization
app.add_middleware(InputSanitizationMiddleware, strict_mode=False)


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with structured logging"""
    request_id = getattr(request.state, "request_id", None)
    
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        path=str(request.url.path),
        error_type=type(exc).__name__,
        error_message=str(exc)
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again.",
            "request_id": request_id
        },
        headers={"X-Request-ID": request_id} if request_id else {}
    )


# =============================================================================
# ROUTES
# =============================================================================

# API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    """Root endpoint - API info"""
    return {
        "name": "CareerCopilot AI API",
        "version": APP_VERSION,
        "status": "operational",
        "docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint for load balancers"""
    return {
        "status": "healthy",
        "version": APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "connected",
            "ai": "ready" if hasattr(app.state, "ai_orchestrator") and app.state.ai_orchestrator else "not_configured"
        }
    }


@app.get("/ready")
def readiness_check():
    """Readiness check - verifies all services are ready"""
    checks = {
        "database": False,
        "ai_orchestrator": False
    }
    
    # Check database
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        checks["database"] = True
    except Exception:
        pass
    
    # Check AI orchestrator
    if hasattr(app.state, "ai_orchestrator") and app.state.ai_orchestrator:
        checks["ai_orchestrator"] = True
    
    all_ready = all(checks.values())
    
    return JSONResponse(
        status_code=200 if all_ready else 503,
        content={
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
