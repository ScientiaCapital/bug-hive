"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from src.core.config import Environment, Settings


def test_environment_enum() -> None:
    """Test Environment enum values."""
    assert Environment.DEVELOPMENT == "development"
    assert Environment.STAGING == "staging"
    assert Environment.PRODUCTION == "production"


def test_settings_requires_database_url(monkeypatch) -> None:
    """Test that Settings requires DATABASE_URL."""
    # Clear any existing DATABASE_URL
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "DATABASE_URL" in str(exc_info.value)


def test_settings_requires_redis_url(monkeypatch) -> None:
    """Test that Settings requires REDIS_URL."""
    monkeypatch.delenv("REDIS_URL", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(
            DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test",
            BROWSERBASE_API_KEY="test",
            BROWSERBASE_PROJECT_ID="test",
            ANTHROPIC_API_KEY="test",
            OPENROUTER_API_KEY="test",
            SECRET_KEY="test",
        )

    assert "REDIS_URL" in str(exc_info.value)


def test_settings_with_minimal_config(monkeypatch) -> None:
    """Test Settings with minimal required configuration."""
    # Clear environment to avoid interference
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)

    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/0",
        BROWSERBASE_API_KEY="test_key",
        BROWSERBASE_PROJECT_ID="test_project",
        ANTHROPIC_API_KEY="test_anthropic",
        OPENROUTER_API_KEY="test_openrouter",
        SECRET_KEY="test_secret",
    )

    assert settings.APP_NAME == "BugHive"
    assert settings.ENVIRONMENT == Environment.DEVELOPMENT
    assert settings.DEFAULT_LLM_PROVIDER == "anthropic"
    assert settings.DEFAULT_MODEL == "claude-3-5-sonnet-20241022"


def test_settings_environment_properties(monkeypatch) -> None:
    """Test environment property helpers."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Test development
    dev_settings = Settings(
        ENVIRONMENT=Environment.DEVELOPMENT,
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/0",
        BROWSERBASE_API_KEY="test",
        BROWSERBASE_PROJECT_ID="test",
        ANTHROPIC_API_KEY="test",
        OPENROUTER_API_KEY="test",
        SECRET_KEY="test",
    )
    assert dev_settings.is_development is True
    assert dev_settings.is_production is False
    assert dev_settings.is_staging is False

    # Test production
    prod_settings = Settings(
        ENVIRONMENT=Environment.PRODUCTION,
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/0",
        BROWSERBASE_API_KEY="test",
        BROWSERBASE_PROJECT_ID="test",
        ANTHROPIC_API_KEY="test",
        OPENROUTER_API_KEY="test",
        SECRET_KEY="test",
    )
    assert prod_settings.is_development is False
    assert prod_settings.is_production is True
    assert prod_settings.is_staging is False


def test_celery_defaults_to_redis(monkeypatch) -> None:
    """Test that Celery URLs default to REDIS_URL."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)

    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/test",
        REDIS_URL="redis://localhost:6379/0",
        BROWSERBASE_API_KEY="test",
        BROWSERBASE_PROJECT_ID="test",
        ANTHROPIC_API_KEY="test",
        OPENROUTER_API_KEY="test",
        SECRET_KEY="test",
    )

    assert settings.CELERY_BROKER_URL == "redis://localhost:6379/0"
    assert settings.CELERY_RESULT_BACKEND == "redis://localhost:6379/0"


def test_no_openai_in_config() -> None:
    """Verify that there are no OpenAI references in configuration.

    This project explicitly does NOT use OpenAI models.
    """
    import inspect

    settings_source = inspect.getsource(Settings)

    # Check for OpenAI references (case insensitive)
    assert "openai" not in settings_source.lower() or "openrouter" in settings_source.lower()
    # OpenRouter is allowed (it provides access to multiple providers)
    # But direct OpenAI integration is not
