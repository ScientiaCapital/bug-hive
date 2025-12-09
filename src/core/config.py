"""Configuration management using Pydantic Settings.

All configuration values are loaded from environment variables.
Never hardcode sensitive values like API keys or connection strings.
"""

from enum import Enum
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings are loaded from environment variables or .env file.
    Use .env.example as a template for creating your local .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application Settings
    APP_NAME: str = Field(default="BugHive", description="Application name")
    ENVIRONMENT: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Application environment (development/staging/production)",
    )
    DEBUG: bool = Field(default=False, description="Enable debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Database Settings
    DATABASE_URL: PostgresDsn = Field(
        description="PostgreSQL database URL (postgresql+asyncpg://user:pass@host:port/db)"
    )
    DB_POOL_SIZE: int = Field(default=5, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Database connection pool max overflow")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries (for debugging)")

    # Redis Settings
    REDIS_URL: RedisDsn = Field(
        description="Redis URL for caching and task queue (redis://host:port/db)"
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, description="Maximum Redis connection pool size")

    # Browser Automation Settings
    BROWSERBASE_API_KEY: str = Field(description="Browserbase API key for browser automation")
    BROWSERBASE_PROJECT_ID: str = Field(description="Browserbase project ID")
    BROWSERBASE_TIMEOUT: int = Field(default=300, description="Browser session timeout in seconds")

    # AI/LLM Settings - NO OPENAI ALLOWED
    ANTHROPIC_API_KEY: str = Field(description="Anthropic API key for Claude models")
    OPENROUTER_API_KEY: str = Field(
        description="OpenRouter API key for accessing multiple LLM providers"
    )
    DEFAULT_LLM_PROVIDER: Literal["anthropic", "openrouter"] = Field(
        default="anthropic", description="Default LLM provider to use"
    )
    DEFAULT_MODEL: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default AI model to use",
    )
    LLM_TEMPERATURE: float = Field(default=0.7, description="LLM temperature for randomness")
    LLM_MAX_TOKENS: int = Field(default=4096, description="Maximum tokens for LLM responses")

    # Task Queue Settings (Celery)
    CELERY_BROKER_URL: str | None = Field(
        default=None,
        description="Celery broker URL (defaults to REDIS_URL if not set)",
    )
    CELERY_RESULT_BACKEND: str | None = Field(
        default=None,
        description="Celery result backend URL (defaults to REDIS_URL if not set)",
    )

    # External Integrations
    LINEAR_API_KEY: str | None = Field(
        default=None,
        description="Linear API key for bug ticket creation (optional)",
    )

    # API Settings
    API_V1_PREFIX: str = Field(default="/api/v1", description="API version prefix")
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="CORS allowed origins",
    )
    API_RATE_LIMIT: str = Field(default="100/minute", description="API rate limit")

    # Security Settings
    SECRET_KEY: str = Field(description="Secret key for signing tokens and encryption")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, description="Access token expiration time in minutes"
    )

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def set_celery_broker_url(cls, v: str | None, info: Any) -> str:
        """Set Celery broker URL to Redis URL if not explicitly provided."""
        if v is None and "REDIS_URL" in info.data:
            return str(info.data["REDIS_URL"])
        return v or ""

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def set_celery_result_backend(cls, v: str | None, info: Any) -> str:
        """Set Celery result backend to Redis URL if not explicitly provided."""
        if v is None and "REDIS_URL" in info.data:
            return str(info.data["REDIS_URL"])
        return v or ""

    @field_validator("DEBUG", mode="before")
    @classmethod
    def set_debug_from_environment(cls, v: bool | None, info: Any) -> bool:
        """Automatically enable debug mode in development environment."""
        if v is None and "ENVIRONMENT" in info.data:
            return bool(info.data["ENVIRONMENT"] == Environment.DEVELOPMENT)
        return bool(v) if v is not None else False

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENVIRONMENT == Environment.STAGING


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    This function uses lru_cache to ensure we only create one Settings
    instance throughout the application lifecycle.

    Returns:
        Settings: Application settings instance
    """
    return Settings()  # type: ignore[call-arg]
