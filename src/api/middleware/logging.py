"""Request logging middleware."""

import time
import uuid
from collections.abc import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests with timing and status.

    Adds request_id to context for distributed tracing.
    Logs request start, end, and timing information.
    """

    def __init__(self, app: ASGIApp):
        """
        Initialize logging middleware.

        Args:
            app: ASGI application
        """
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response]
    ) -> Response:
        """
        Process request with logging.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response from application
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())

        # Add request ID to request state for use in handlers
        request.state.request_id = request_id

        # Bind request context for structured logging
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        # Log request start
        logger.info(
            "request_started",
            query_params=dict(request.query_params) if request.query_params else None,
        )

        # Time the request
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful response
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Add request ID to response headers for client tracking
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )

            # Re-raise exception to be handled by exception handlers
            raise

        finally:
            # Clear context variables
            structlog.contextvars.clear_contextvars()
