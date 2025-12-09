"""FastAPI application for BugHive autonomous QA agent system.

This is the main entry point for the API gateway.
Provides RESTful endpoints for:
- Starting and monitoring crawl sessions
- Managing and validating bugs
- Reporting bugs to Linear
- Health checks
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..core.config import get_settings
from ..core.logging import setup_logging
from ..db.database import close_database, init_database
from .middleware.logging import RequestLoggingMiddleware
from .routes import bugs_router, crawl_router, health_router
from .schemas import ErrorResponse, ValidationErrorDetail, ValidationErrorResponse

# Initialize structured logging
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database connection pool, setup logging
    - Shutdown: Close database connections, cleanup resources
    """
    settings = get_settings()

    # Startup
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT.value,
        debug=settings.DEBUG,
    )

    try:
        # Initialize database (create tables if they don't exist)
        # In production, use Alembic migrations instead
        if settings.is_development:
            await init_database(drop_existing=False)
            logger.info("database_initialized")

        logger.info("application_ready")

        yield

    finally:
        # Shutdown
        logger.info("application_shutting_down")

        # Close database connections
        await close_database()
        logger.info("database_connections_closed")

        logger.info("application_shutdown_complete")


# Create FastAPI application
settings = get_settings()

app = FastAPI(
    title="BugHive API",
    description=(
        "Autonomous QA agent system for web application testing. "
        "BugHive automatically crawls your application, detects bugs using AI, "
        "and reports them to your issue tracker."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)


# ===== Middleware =====

# CORS middleware (configure allowed origins in settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)


# ===== Exception Handlers =====

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions with consistent error format.

    Args:
        request: Incoming request
        exc: HTTP exception

    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)

    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
    )

    error_response = ErrorResponse(
        error="http_error",
        detail=str(exc.detail),
        request_id=request_id,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle request validation errors with detailed field information.

    Args:
        request: Incoming request
        exc: Validation exception

    Returns:
        JSON error response with validation details
    """
    request_id = getattr(request.state, "request_id", None)

    # Convert validation errors to our format
    validation_errors = [
        ValidationErrorDetail(
            loc=list(error["loc"]),
            msg=error["msg"],
            type=error["type"],
        )
        for error in exc.errors()
    ]

    logger.warning(
        "validation_error",
        path=request.url.path,
        error_count=len(validation_errors),
        errors=exc.errors(),
    )

    error_response = ValidationErrorResponse(
        error="validation_error",
        detail="Request validation failed",
        validation_errors=validation_errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions with logging.

    Args:
        request: Incoming request
        exc: Unexpected exception

    Returns:
        JSON error response
    """
    request_id = getattr(request.state, "request_id", None)

    logger.error(
        "unexpected_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        exc_info=True,
    )

    # In production, don't expose internal error details
    detail = str(exc) if settings.DEBUG else "An unexpected error occurred"

    error_response = ErrorResponse(
        error="internal_error",
        detail=detail,
        request_id=request_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(),
    )


# ===== Routes =====

# Health check routes (no auth required)
app.include_router(health_router)

# API routes (auth required)
api_prefix = settings.API_V1_PREFIX

app.include_router(
    crawl_router,
    prefix=api_prefix,
)

app.include_router(
    bugs_router,
    prefix=api_prefix,
)


# ===== Root Endpoint =====

@app.get(
    "/",
    include_in_schema=False,
    summary="API root",
)
async def root():
    """
    API root endpoint.

    Returns basic API information and available endpoints.
    """
    return {
        "name": "BugHive API",
        "version": "0.1.0",
        "description": "Autonomous QA agent system",
        "docs_url": f"{settings.API_V1_PREFIX}/docs" if settings.is_development else None,
        "health_url": "/health",
        "environment": settings.ENVIRONMENT.value,
    }


# ===== Startup Event =====

@app.on_event("startup")
async def startup_event():
    """Log startup completion."""
    logger.info(
        "fastapi_startup_complete",
        routes_count=len(app.routes),
        middleware_count=len(app.user_middleware),
    )


# ===== Shutdown Event =====

@app.on_event("shutdown")
async def shutdown_event():
    """Log shutdown."""
    logger.info("fastapi_shutdown_initiated")
