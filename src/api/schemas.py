"""Additional API request/response schemas.

These complement the Pydantic models in src/models/.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from ..models.bug import Bug
from ..models.crawl import CrawlConfig

# ===== Crawl Endpoints =====

class CrawlStartRequest(BaseModel):
    """Request to start a new crawl session."""

    base_url: str = Field(..., description="Base URL to start crawling from")
    auth_method: Literal["session", "oauth", "api_key", "none"] = Field(
        default="none",
        description="Authentication method to use"
    )
    credentials: dict | None = Field(
        default=None,
        description="Authentication credentials (will be encrypted)"
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

    def to_crawl_config(self) -> CrawlConfig:
        """Convert to CrawlConfig model."""
        return CrawlConfig(
            base_url=self.base_url,
            auth_method=self.auth_method,
            credentials=self.credentials,
            max_pages=self.max_pages,
            max_depth=self.max_depth,
            excluded_patterns=self.excluded_patterns,
            follow_external_links=self.follow_external_links,
        )


class CrawlStartResponse(BaseModel):
    """Response when starting a new crawl."""

    session_id: UUID = Field(..., description="Created session ID")
    base_url: str = Field(..., description="Base URL being crawled")
    status: str = Field(..., description="Initial status (pending)")
    message: str = Field(
        default="Crawl session created and queued for processing",
        description="Status message"
    )
    created_at: datetime = Field(..., description="Session creation time")


class CrawlStatusResponse(BaseModel):
    """Response for crawl session status."""

    session_id: UUID
    base_url: str
    status: Literal["pending", "running", "completed", "failed"]
    pages_discovered: int = Field(ge=0)
    pages_crawled: int = Field(ge=0)
    bugs_found: int = Field(ge=0)
    total_cost: float = Field(ge=0.0, description="Total AI analysis cost in USD")
    started_at: datetime | None = None
    completed_at: datetime | None = None
    elapsed_time: float | None = Field(
        None,
        description="Elapsed time in seconds (if completed)"
    )
    error_message: str | None = None

    # Computed metrics
    success_rate: float | None = Field(
        None,
        description="Percentage of successfully crawled pages"
    )
    bugs_per_page: float | None = Field(
        None,
        description="Average bugs found per page"
    )


class CrawlStopResponse(BaseModel):
    """Response when stopping a crawl."""

    session_id: UUID
    previous_status: str
    new_status: str
    message: str = Field(default="Crawl session stopped")
    pages_crawled: int
    bugs_found: int


class SessionBugsResponse(BaseModel):
    """Response for bugs in a session."""

    session_id: UUID
    bugs: list[Bug]
    total: int = Field(description="Total number of bugs")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of bugs per page")
    by_priority: dict[str, int] = Field(
        description="Count of bugs by priority level"
    )
    by_category: dict[str, int] = Field(
        description="Count of bugs by category"
    )


# ===== Bug Endpoints =====

class BugResponse(Bug):
    """Enhanced bug response with page information."""

    page_url: str | None = Field(None, description="URL of page where bug was found")


class BugValidateRequest(BaseModel):
    """Request to validate or dismiss a bug."""

    is_valid: bool = Field(..., description="Whether bug is valid")
    notes: str | None = Field(
        None,
        description="Optional notes about validation decision"
    )


class BugValidateResponse(BaseModel):
    """Response after bug validation."""

    bug_id: UUID
    previous_status: str
    new_status: str
    message: str


class BugReportResponse(BaseModel):
    """Response after reporting bug to Linear."""

    bug_id: UUID
    linear_issue_id: str = Field(..., description="Linear issue ID")
    linear_issue_url: str = Field(..., description="URL to Linear issue")
    reported_at: datetime = Field(..., description="When bug was reported")
    message: str = Field(default="Bug successfully reported to Linear")


# ===== Health Check =====

class HealthResponse(BaseModel):
    """Basic health check response."""

    status: Literal["healthy", "unhealthy"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="0.1.0")


class ServiceHealth(BaseModel):
    """Health status of a single service."""

    service: str
    status: Literal["healthy", "unhealthy", "degraded"]
    latency_ms: float | None = None
    error: str | None = None


class DetailedHealthResponse(BaseModel):
    """Detailed health check with dependency status."""

    status: Literal["healthy", "unhealthy", "degraded"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="0.1.0")
    services: list[ServiceHealth] = Field(
        description="Health status of each service"
    )

    @property
    def is_healthy(self) -> bool:
        """Check if all services are healthy."""
        return all(s.status == "healthy" for s in self.services)


# ===== Error Responses =====

class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type or code")
    detail: str = Field(..., description="Detailed error message")
    request_id: str | None = Field(
        None,
        description="Request ID for tracing"
    )


class ValidationErrorDetail(BaseModel):
    """Validation error detail."""

    loc: list[str | int] = Field(..., description="Location of error in request")
    msg: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")


class ValidationErrorResponse(BaseModel):
    """Validation error response."""

    error: str = Field(default="validation_error")
    detail: str = Field(..., description="Error summary")
    validation_errors: list[ValidationErrorDetail] = Field(
        ...,
        description="List of validation errors"
    )


# ===== Pagination =====

class PaginationParams(BaseModel):
    """Common pagination parameters."""

    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of items to return"
    )


class PaginatedResponse[T](BaseModel):
    """Generic paginated response."""

    items: list[T]
    total: int = Field(ge=0, description="Total number of items")
    skip: int = Field(ge=0, description="Number of items skipped")
    limit: int = Field(ge=1, description="Maximum items per page")

    @property
    def has_more(self) -> bool:
        """Check if there are more items available."""
        return self.skip + len(self.items) < self.total
