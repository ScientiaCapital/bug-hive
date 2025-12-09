"""Health check endpoints."""

import time
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ..deps.database import get_db
from ..schemas import DetailedHealthResponse, HealthResponse, ServiceHealth

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic health check",
    description="Quick health check endpoint for load balancers and monitoring",
)
async def health_check() -> HealthResponse:
    """
    Basic health check.

    Returns 200 if service is running.
    This is a lightweight check suitable for frequent polling.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health check",
    description="Comprehensive health check including all service dependencies",
)
async def detailed_health(
    db: AsyncSession = Depends(get_db)
) -> DetailedHealthResponse:
    """
    Detailed health check with dependency verification.

    Checks:
    - Database connection and query performance
    - Redis connection (TODO: when Redis is integrated)
    - Browserbase API connectivity (TODO: when Browserbase is integrated)

    Returns overall health status and individual service health.
    """
    settings = get_settings()
    services: list[ServiceHealth] = []

    # Check database
    db_health = await _check_database(db)
    services.append(db_health)

    # TODO: Check Redis when integrated
    # redis_health = await _check_redis()
    # services.append(redis_health)

    # TODO: Check Browserbase API when integrated
    # browserbase_health = await _check_browserbase()
    # services.append(browserbase_health)

    # Determine overall status
    if all(s.status == "healthy" for s in services):
        overall_status = "healthy"
    elif any(s.status == "unhealthy" for s in services):
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        services=services,
    )


async def _check_database(db: AsyncSession) -> ServiceHealth:
    """
    Check database connectivity and performance.

    Args:
        db: Database session

    Returns:
        Database health status
    """
    try:
        start_time = time.time()

        # Simple query to test connection
        await db.execute("SELECT 1")

        latency_ms = (time.time() - start_time) * 1000

        logger.info(
            "database_health_check",
            status="healthy",
            latency_ms=round(latency_ms, 2),
        )

        return ServiceHealth(
            service="database",
            status="healthy",
            latency_ms=round(latency_ms, 2),
        )

    except Exception as exc:
        logger.error(
            "database_health_check_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )

        return ServiceHealth(
            service="database",
            status="unhealthy",
            error=str(exc),
        )


async def _check_redis() -> ServiceHealth:
    """
    Check Redis connectivity and performance.

    TODO: Implement when Redis is integrated.

    Returns:
        Redis health status
    """
    # Placeholder for Redis health check
    return ServiceHealth(
        service="redis",
        status="healthy",
        latency_ms=5.0,
    )


async def _check_browserbase() -> ServiceHealth:
    """
    Check Browserbase API connectivity.

    TODO: Implement when Browserbase is integrated.

    Returns:
        Browserbase health status
    """
    # Placeholder for Browserbase health check
    return ServiceHealth(
        service="browserbase",
        status="healthy",
        latency_ms=100.0,
    )
