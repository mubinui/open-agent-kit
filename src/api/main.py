"""Main FastAPI application entry point."""

import time
import uuid
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from src.api.rate_limiting import limiter, rate_limit_exceeded_handler, rate_limiting_middleware
from src.audit_logging import bind_correlation_ids, clear_correlation_ids, configure_logging
from src.config.settings import get_settings
from src.config.config_loader import get_config_loader
from src.observability.metrics import track_http_request
from src.observability.tracing import configure_tracing, instrument_fastapi

# Configure logging first
configure_logging()

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    settings = get_settings()
    logger.info(
        "orchestration_service_starting",
        log_level=settings.app.log_level,
        environment=settings.app.environment,
    )
    
    # Initialize centralized config loader with hot-reload if enabled
    enable_hot_reload = settings.app.environment == "development"
    try:
        config_loader = get_config_loader(enable_hot_reload=enable_hot_reload)
        logger.info(
            "config_loader_initialized",
            hot_reload=enable_hot_reload,
            config_dir=str(config_loader.config_dir),
        )
    except Exception as e:
        logger.error("config_loader_initialization_failed", error=str(e))
    
    # Configure OpenTelemetry tracing
    try:
        configure_tracing()
        instrument_fastapi(app)
    except Exception as e:
        logger.warning("tracing_configuration_failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("orchestration_service_shutting_down")
    
    # Stop config loader file watcher
    try:
        config_loader = get_config_loader()
        config_loader.stop_file_watcher()
    except Exception as e:
        logger.warning("config_loader_cleanup_failed", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="Orchestration Service",
    description="Production-grade multi-agent orchestration platform built on Microsoft Autogen 0.2",
    version="0.1.0",
    lifespan=lifespan,
)


# Configure CORS middleware
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all incoming requests with correlation IDs and timing."""
    request_id = str(uuid.uuid4())
    
    # Add request_id to request state for use in handlers
    request.state.request_id = request_id
    
    # Bind correlation IDs to logging context
    bind_correlation_ids(request_id=request_id)
    
    # Log request
    start_time = time.time()
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client_host=request.client.host if request.client else None,
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Track metrics
        track_http_request(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            duration=duration,
        )
        
        # Log response
        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_seconds=duration,
        )
        
        # Add request_id to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
        
    except Exception as exc:
        duration = time.time() - start_time
        
        # Track metrics for failed requests
        track_http_request(
            method=request.method,
            endpoint=request.url.path,
            status=500,
            duration=duration,
        )
        
        logger.error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            duration_seconds=duration,
            error=str(exc),
            exc_info=True,
        )
        raise
    finally:
        # Clear correlation IDs to prevent context leakage
        clear_correlation_ids()


@app.middleware("http")
async def jwt_validation_middleware(request: Request, call_next):
    """Middleware to validate JWT tokens (Keycloak or internal) and add user context."""
    settings = get_settings()
    
    # Skip auth for public endpoints
    public_paths = ["/", "/docs", "/openapi.json", "/health", "/metrics", "/api/v1/auth/token"]
    
    if request.url.path in public_paths or request.url.path.startswith("/static"):
        return await call_next(request)
    
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
        # Add token to request state for use in dependencies
        request.state.auth_token = token
        
        # Extract custom headers for Service2-style calls (x-client-ref, x-client-username)
        from src.api.keycloak_auth import extract_client_headers
        roles, username = extract_client_headers(request)
        request.state.client_roles = roles
        request.state.client_username = username
        
        # Validate via Keycloak if enabled
        if settings.keycloak.enabled:
            from src.api.keycloak_auth import validate_keycloak_token
            try:
                token_data = await validate_keycloak_token(token)
                request.state.keycloak_user = token_data
                request.state.keycloak_authenticated = True
                logger.debug(
                    "keycloak_token_validated",
                    username=token_data.preferred_username,
                    roles=token_data.roles,
                )
            except Exception as e:
                logger.warning("keycloak_validation_failed", error=str(e))
                request.state.keycloak_authenticated = False
        else:
            # Log authentication attempt for internal JWT
            logger.debug("jwt_validation_attempt", path=request.url.path)
    
    return await call_next(request)


# Add rate limiting middleware
app.middleware("http")(rate_limiting_middleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with structured error responses."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.warning(
        "validation_error",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        errors=exc.errors(),
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "error_message": "Request validation failed",
            "error_type": "ValidationError",
            "request_id": request_id,
            "timestamp": time.time(),
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions with structured error responses."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "error_message": "An unexpected error occurred",
            "error_type": type(exc).__name__,
            "request_id": request_id,
            "timestamp": time.time(),
            "details": None,  # Don't expose internal error details in production
        },
    )


# Include routers
from src.api.routers import agents, api_providers, auth, configs, health, prompts, sessions, tools, workflows

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(agents.router)
app.include_router(tools.router)
app.include_router(workflows.router)
app.include_router(prompts.router)
app.include_router(api_providers.router)
app.include_router(configs.router)
app.include_router(health.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "service": "Orchestration Service",
        "version": "0.1.0",
        "description": "Production-grade multi-agent orchestration platform built on Microsoft Autogen 0.2",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
