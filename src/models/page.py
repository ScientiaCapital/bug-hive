"""Pydantic models for crawled pages."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class Page(BaseModel):
    """Represents a single crawled page."""

    id: UUID = Field(..., description="Unique page identifier")
    session_id: UUID = Field(..., description="Parent crawl session ID")
    url: str = Field(..., description="Page URL")
    title: str | None = Field(
        default=None,
        description="Page title from <title> tag"
    )
    status: Literal["discovered", "crawling", "analyzed", "error"] = Field(
        default="discovered",
        description="Current page status"
    )
    depth: int = Field(
        ...,
        ge=0,
        description="Depth from base URL (0 = base URL)"
    )
    screenshot_url: str | None = Field(
        default=None,
        description="URL to page screenshot"
    )
    crawled_at: datetime | None = Field(
        default=None,
        description="When page was crawled"
    )
    analysis_result: dict | None = Field(
        default=None,
        description="AI analysis results"
    )
    response_time_ms: int | None = Field(
        default=None,
        description="Page load time in milliseconds"
    )
    status_code: int | None = Field(
        default=None,
        description="HTTP status code"
    )
    content_type: str | None = Field(
        default=None,
        description="Content-Type header value"
    )
    content_length: int | None = Field(
        default=None,
        description="Response size in bytes"
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if status is 'error'"
    )
    parent_page_id: UUID | None = Field(
        default=None,
        description="ID of page that linked to this page"
    )
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When page was discovered"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Database record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "url": "https://example.com/products",
                    "title": "Products - Example Site",
                    "status": "analyzed",
                    "depth": 1,
                    "screenshot_url": "https://storage.example.com/screenshots/abc123.png",
                    "response_time_ms": 234,
                    "status_code": 200,
                }
            ]
        }
    }


class PageCreate(BaseModel):
    """Schema for creating a new page record."""

    session_id: UUID
    url: str
    depth: int = 0
    parent_page_id: UUID | None = None
    title: str | None = None
    status: Literal["discovered", "crawling", "analyzed", "error"] = "discovered"


class PageUpdate(BaseModel):
    """Schema for updating a page record."""

    status: Literal["discovered", "crawling", "analyzed", "error"] | None = None
    title: str | None = None
    screenshot_url: str | None = None
    crawled_at: datetime | None = None
    analysis_result: dict | None = None
    response_time_ms: int | None = None
    status_code: int | None = None
    content_type: str | None = None
    content_length: int | None = None
    error_message: str | None = None


class PageInventory(BaseModel):
    """Inventory of all pages in a crawl session."""

    pages: list[Page] = Field(
        default_factory=list,
        description="List of all pages"
    )
    navigation_graph: dict = Field(
        default_factory=dict,
        description="Graph of page relationships (parent -> children)"
    )
    crawl_duration: float = Field(
        default=0.0,
        ge=0.0,
        description="Total crawl duration in seconds"
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
    pages_by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Count of pages by status"
    )
    pages_by_depth: dict[int, int] = Field(
        default_factory=dict,
        description="Count of pages by depth level"
    )
    average_response_time_ms: float | None = Field(
        default=None,
        description="Average page load time"
    )
    total_content_size_bytes: int | None = Field(
        default=None,
        description="Total size of all crawled content"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "pages": [],
                    "navigation_graph": {
                        "https://example.com": [
                            "https://example.com/about",
                            "https://example.com/products"
                        ]
                    },
                    "crawl_duration": 45.2,
                    "pages_discovered": 50,
                    "pages_crawled": 48,
                    "pages_by_status": {
                        "analyzed": 46,
                        "error": 2,
                        "discovered": 2
                    },
                    "pages_by_depth": {
                        "0": 1,
                        "1": 15,
                        "2": 34
                    },
                }
            ]
        }
    }


class PageWithBugs(Page):
    """Page with bug count."""

    bug_count: int = Field(
        default=0,
        ge=0,
        description="Number of bugs found on this page"
    )


class PageAnalytics(BaseModel):
    """Analytics for a specific page."""

    page_id: UUID
    url: str
    bugs_found: int
    bug_severity_distribution: dict[str, int] = Field(
        description="Count of bugs by severity (critical, high, medium, low)"
    )
    bug_category_distribution: dict[str, int] = Field(
        description="Count of bugs by category"
    )
    response_time_ms: int | None = None
    status_code: int | None = None
    crawled_at: datetime | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "page_id": "550e8400-e29b-41d4-a716-446655440001",
                    "url": "https://example.com/products",
                    "bugs_found": 3,
                    "bug_severity_distribution": {
                        "high": 1,
                        "medium": 2
                    },
                    "bug_category_distribution": {
                        "ui_ux": 2,
                        "performance": 1
                    },
                }
            ]
        }
    }
