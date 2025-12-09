"""Structured logging configuration using structlog.

Provides consistent, structured logging across the application with:
- JSON output for production environments
- Pretty console output for development
- Request ID tracking for distributed tracing
- Timestamp formatting
- Log level filtering
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from .config import Environment, get_settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries.

    Args:
        logger: The logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary to modify

    Returns:
        Modified event dictionary with app context
    """
    settings = get_settings()
    event_dict["app"] = settings.APP_NAME
    event_dict["environment"] = settings.ENVIRONMENT.value
    return event_dict


def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Censor sensitive data from logs.

    Removes or masks sensitive information like API keys, passwords, tokens, etc.

    Args:
        logger: The logger instance
        method_name: The name of the method being called
        event_dict: The event dictionary to modify

    Returns:
        Modified event dictionary with censored data
    """
    sensitive_keys = {
        "password",
        "api_key",
        "token",
        "secret",
        "apikey",
        "authorization",
        "auth",
        "bearer",
    }

    def _censor_dict(data: dict[str, Any]) -> dict[str, Any]:
        """Recursively censor sensitive keys in dictionary."""
        censored: dict[str, Any] = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                censored[key] = "***CENSORED***"
            elif isinstance(value, dict):
                censored[key] = _censor_dict(value)
            elif isinstance(value, list):
                censored[key] = [
                    _censor_dict(item) if isinstance(item, dict) else item for item in value
                ]
            else:
                censored[key] = value
        return censored

    # Cast to dict to satisfy mypy since event_dict is MutableMapping
    return _censor_dict(dict(event_dict))


def get_log_processors(environment: Environment) -> list[Processor]:
    """Get log processors based on environment.

    Args:
        environment: The application environment

    Returns:
        List of structlog processors
    """
    # Common processors for all environments
    common_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
        censor_sensitive_data,
    ]

    # Environment-specific processors
    if environment == Environment.PRODUCTION:
        # Production: JSON output for log aggregation systems
        return [
            *common_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development/Staging: Pretty console output
        return [
            *common_processors,
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ]


def setup_logging() -> None:
    """Configure structured logging for the application.

    Sets up structlog with appropriate processors and formatters based on
    the application environment. Call this once at application startup.
    """
    settings = get_settings()

    # Configure standard library logging
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Configure structlog
    structlog.configure(
        processors=get_log_processors(settings.ENVIRONMENT),
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Any:
    """Get a logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured structlog logger (BoundLogger or BoundLoggerLazyProxy)
    """
    return structlog.get_logger(name)


# Example usage context manager for request tracking
class LogContext:
    """Context manager for adding context to logs within a scope.

    Example:
        with LogContext(request_id="abc-123", user_id="user-456"):
            logger.info("processing_request")
            # Logs will include request_id and user_id
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize log context.

        Args:
            **kwargs: Key-value pairs to add to log context
        """
        self.context = kwargs

    def __enter__(self) -> None:
        """Enter the context and bind variables."""
        structlog.contextvars.bind_contextvars(**self.context)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and clear variables."""
        structlog.contextvars.clear_contextvars()
