"""
FastAPI main application for Sokolink Advisor.
"""
import time
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import structlog
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.config import get_settings
from app.routes import whatsapp, api
from app.utils.security import validate_environment
from app.services.database_service import db_service

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
settings = get_settings()

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    """
    # Startup
    logger.info("Starting Sokolink Advisor application", version=settings.app_version)
    
    # Validate configuration
    if not validate_environment():
        logger.error("Invalid configuration detected")
        raise RuntimeError("Invalid configuration")
    
    # Initialize database
    try:
        # Database tables are created automatically in DatabaseService.__init__
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    # Health check external services
    try:
        from app.services.whatsapp_service import whatsapp_service
        from app.services.watsonx_service import watsonx_service
        
        whatsapp_health = await whatsapp_service.health_check()
        watsonx_health = await watsonx_service.health_check()
        
        logger.info("External services health check", 
                   whatsapp=whatsapp_health["status"],
                   watsonx=watsonx_health["status"])
        
    except Exception as e:
        logger.warning("External services health check failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sokolink Advisor application")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI backend for Sokolink Advisor - WhatsApp Business API integration with IBM Watsonx Orchestrate for regulatory compliance guidance",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["yourdomain.com", "*.yourdomain.com"]
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Logging and metrics middleware.
    """
    start_time = time.time()
    
    # Log request
    logger.info("Request started",
               method=request.method,
               url=str(request.url),
               client_ip=request.client.host if request.client else None)
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    # Log response
    logger.info("Request completed",
               method=request.method,
               url=str(request.url),
               status_code=response.status_code,
               duration=duration)
    
    return response


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """
    Simple rate limiting middleware.
    """
    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/metrics"]:
        return await call_next(request)
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Simple in-memory rate limiting (in production, use Redis)
    # This is a basic implementation - for production, implement proper rate limiting
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error("Rate limiting error", error=str(e))
        return await call_next(request)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions.
    """
    logger.warning("HTTP exception",
                  status_code=exc.status_code,
                  detail=exc.detail,
                  url=str(request.url))
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": f"HTTP_{exc.status_code}",
            "error_message": exc.detail,
            "timestamp": time.time()
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors.
    """
    logger.warning("Validation error",
                  errors=exc.errors(),
                  url=str(request.url))
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "error_message": "Request validation failed",
            "details": exc.errors(),
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle general exceptions.
    """
    logger.error("Unhandled exception",
                error=str(exc),
                url=str(request.url),
                exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "error_message": "An internal error occurred",
            "timestamp": time.time()
        }
    )


# Include routers
app.include_router(whatsapp.router)
app.include_router(api.router)


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint with basic information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "timestamp": time.time(),
        "docs_url": "/docs" if settings.debug else None
    }


# Health check endpoint (public)
@app.get("/health")
async def health_check():
    """
    Public health check endpoint.
    """
    try:
        # Basic health check
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        )


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    """
    if not settings.enable_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics not enabled"
        )
    
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    """
    logger.info("Sokolink Advisor application started",
               version=settings.app_version,
               environment=settings.environment,
               debug=settings.debug)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    """
    logger.info("Sokolink Advisor application shutting down")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level=settings.log_level.lower()
    )
