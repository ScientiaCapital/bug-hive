"""Pydantic models for crawl sessions and configuration."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AuthMethod(str, Enum):
    """Authentication methods for crawling."""

    SESSION = "session"
    OAUTH = "oauth"
    API_KEY = "api_key"
    NONE = "none"


class PageInventory(BaseModel):
    """Inventory of discovered pages during a crawl."""

    discovered_urls: list[str] = Field(default_factory=list)
    crawled_urls: list[str] = Field(default_factory=list)
    failed_urls: list[str] = Field(default_factory=list)
    skipped_urls: list[str] = Field(default_factory=list)

    @property
    def total_discovered(self) -> int:
        """Total discovered pages."""
        return len(self.discovered_urls)

    @property
    def total_crawled(self) -> int:
        """Total crawled pages."""
        return len(self.crawled_urls)

    @property
    def pending_count(self) -> int:
        """Pages remaining to crawl."""
        crawled_set = set(self.crawled_urls)
        failed_set = set(self.failed_urls)
        skipped_set = set(self.skipped_urls)
        return len([
            url for url in self.discovered_urls
            if url not in crawled_set and url not in failed_set and url not in skipped_set
        ])


class CrawlConfig(BaseModel):
    """Configuration for a crawl session."""

    base_url: str = Field(..., description="Base URL to start crawling from")
    auth_method: Literal["session", "oauth", "api_key", "none"] = Field(
        default="none",
        description="Authentication method to use"
    )
    credentials: dict | None = Field(
        default=None,
        description="Authentication credentials (encrypted in DB)"
    )
    max_pages: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of pages to crawl"
    )
    max_depth: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum crawl depth from base URL"
    )
    excluded_patterns: list[str] = Field(
        default_factory=list,
        description="URL patterns to exclude from crawling"
    )
    follow_external_links: bool = Field(
        default=False,
        description="Whether to follow links outside base domain"
    )
    respect_robots_txt: bool = Field(
        default=True,
        description="Whether to respect robots.txt"
    )
    crawl_delay_ms: int = Field(
        default=1000,
        ge=0,
        description="Delay between page requests in milliseconds"
    )
    user_agent: str | None = Field(
        default=None,
        description="Custom user agent string"
    )
    viewport_width: int = Field(default=1920, description="Browser viewport width")
    viewport_height: int = Field(default=1080, description="Browser viewport height")

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Ensure base_url is a valid URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.rstrip("/")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "base_url": "https://example.com",
                    "auth_method": "session",
                    "credentials": {"username": "test", "password": "***"},
                    "max_pages": 50,
                    "max_depth": 3,
                    "excluded_patterns": ["/api/*", "/admin/*"],
                }
            ]
        }
    }


class CrawlSession(BaseModel):
    """Represents a complete crawl session."""

    id: UUID = Field(..., description="Unique session identifier")
    base_url: str = Field(..., description="Base URL being crawled")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        default="pending",
        description="Current session status"
    )
    config: CrawlConfig = Field(..., description="Crawl configuration")
    started_at: datetime | None = Field(
        default=None,
        description="When crawling started"
    )
    completed_at: datetime | None = Field(
        default=None,
        description="When crawling completed"
    )
    pages_discovered: int = Field(
        default=0,
        ge=0,
        description="Total pages discovered"
    )
    pages_crawled: int = Field(
        default=0,
        ge=0,
        description="Total pages successfully crawled"
    )
    bugs_found: int = Field(
        default=0,
        ge=0,
        description="Total bugs detected"
    )
    total_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Total AI analysis cost in USD"
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if status is 'failed'"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Session creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "base_url": "https://example.com",
                    "status": "completed",
                    "config": {
                        "base_url": "https://example.com",
                        "auth_method": "none",
                        "max_pages": 50,
                        "max_depth": 3,
                    },
                    "pages_discovered": 45,
                    "pages_crawled": 42,
                    "bugs_found": 7,
                    "total_cost": 2.35,
                }
            ]
        }
    }


class CrawlSessionCreate(BaseModel):
    """Schema for creating a new crawl session."""

    base_url: str
    config: CrawlConfig


class CrawlSessionUpdate(BaseModel):
    """Schema for updating a crawl session."""

    status: Literal["pending", "running", "completed", "failed"] | None = None
    pages_discovered: int | None = None
    pages_crawled: int | None = None
    bugs_found: int | None = None
    total_cost: float | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CrawlSessionResponse(CrawlSession):
    """Response schema with additional computed fields."""

    @property
    def duration_seconds(self) -> float | None:
        """Calculate crawl duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def success_rate(self) -> float | None:
        """Calculate percentage of successfully crawled pages."""
        if self.pages_discovered > 0:
            return (self.pages_crawled / self.pages_discovered) * 100
        return None

    @property
    def bugs_per_page(self) -> float | None:
        """Calculate average bugs found per page."""
        if self.pages_crawled > 0:
            return self.bugs_found / self.pages_crawled
        return None
