"""Tests for logging configuration."""

import pytest
import structlog

from src.core.config import get_settings
from src.core.logging import LogContext, get_logger, setup_logging


@pytest.fixture
def mock_env(monkeypatch):
    """Set up minimal required environment variables for tests."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("BROWSERBASE_API_KEY", "test_key")
    monkeypatch.setenv("BROWSERBASE_PROJECT_ID", "test_project")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test_openrouter")
    monkeypatch.setenv("SECRET_KEY", "test_secret")

    # Clear the lru_cache to force reload of settings
    get_settings.cache_clear()


def test_setup_logging(mock_env) -> None:
    """Test that logging setup runs without errors."""
    # This should not raise any exceptions
    setup_logging()

    # Verify structlog is configured
    assert structlog.is_configured()


def test_get_logger(mock_env) -> None:
    """Test getting a logger instance."""
    setup_logging()

    logger = get_logger(__name__)
    assert logger is not None
    # Logger can be either BoundLogger or BoundLoggerLazyProxy
    # Just verify it has the expected methods
    assert hasattr(logger, "info")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "error")


def test_log_context(mock_env) -> None:
    """Test LogContext context manager."""
    setup_logging()
    logger = get_logger(__name__)

    # Test that context is added and removed
    with LogContext(request_id="test-123", user_id="user-456"):
        # Context should be available here
        # We can't directly test the output, but we can verify no exceptions
        logger.info("test_message")

    # After exiting context, it should be cleared
    logger.info("test_message_after_context")


def test_logger_methods(mock_env) -> None:
    """Test that logger has expected methods."""
    setup_logging()
    logger = get_logger(__name__)

    # Test all common log levels exist and are callable
    assert hasattr(logger, "debug")
    assert hasattr(logger, "info")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")
    assert hasattr(logger, "critical")

    # Test they don't raise exceptions when called
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")


def test_structured_logging(mock_env) -> None:
    """Test that structured logging accepts key-value pairs."""
    setup_logging()
    logger = get_logger(__name__)

    # Should not raise exception with structured data
    logger.info("user_action", user_id="123", action="login", success=True)
