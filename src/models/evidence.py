"""Pydantic models for bug evidence."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Evidence supporting a bug report."""

    type: Literal[
        "screenshot",
        "console_log",
        "network_request",
        "dom_snapshot",
        "performance_metrics"
    ] = Field(
        ...,
        description="Type of evidence"
    )
    content: str = Field(
        ...,
        description="Evidence content (URL for screenshots, JSON for logs/requests)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When evidence was captured"
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional metadata about the evidence"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "screenshot",
                    "content": "https://storage.example.com/screenshots/abc123.png",
                    "timestamp": "2024-01-15T10:30:00Z",
                    "metadata": {"viewport": "1920x1080", "browser": "chromium"},
                },
                {
                    "type": "console_log",
                    "content": '{"level": "error", "message": "TypeError: Cannot read property..."}',
                    "timestamp": "2024-01-15T10:30:01Z",
                    "metadata": {"source": "app.js:42"},
                },
            ]
        }
    }


class ScreenshotEvidence(Evidence):
    """Screenshot evidence with image URL."""

    type: Literal["screenshot"] = "screenshot"
    content: str = Field(
        ...,
        description="URL to screenshot image"
    )

    @property
    def image_url(self) -> str:
        """Get screenshot URL."""
        return self.content


class ConsoleLogEvidence(Evidence):
    """Console log evidence."""

    type: Literal["console_log"] = "console_log"
    content: str = Field(
        ...,
        description="Console log entry as JSON string"
    )
    log_level: Literal["error", "warning", "info", "debug"] | None = Field(
        default=None,
        description="Log level"
    )


class NetworkRequestEvidence(Evidence):
    """Network request evidence."""

    type: Literal["network_request"] = "network_request"
    content: str = Field(
        ...,
        description="Network request/response as JSON string"
    )
    status_code: int | None = Field(
        default=None,
        description="HTTP status code"
    )
    request_url: str | None = Field(
        default=None,
        description="Request URL"
    )
    request_method: str | None = Field(
        default=None,
        description="HTTP method"
    )


class DOMSnapshotEvidence(Evidence):
    """DOM snapshot evidence."""

    type: Literal["dom_snapshot"] = "dom_snapshot"
    content: str = Field(
        ...,
        description="DOM snapshot as HTML string or JSON"
    )
    selector: str | None = Field(
        default=None,
        description="CSS selector for problematic element"
    )


class EvidenceCollection(BaseModel):
    """Collection of evidence items."""

    items: list[Evidence] = Field(
        default_factory=list,
        description="List of evidence items"
    )

    def add(self, evidence: Evidence) -> None:
        """Add evidence to collection."""
        self.items.append(evidence)

    def get_by_type(
        self,
        evidence_type: Literal[
            "screenshot",
            "console_log",
            "network_request",
            "dom_snapshot",
            "performance_metrics"
        ]
    ) -> list[Evidence]:
        """Get all evidence of a specific type."""
        return [e for e in self.items if e.type == evidence_type]

    @property
    def screenshots(self) -> list[Evidence]:
        """Get all screenshot evidence."""
        return self.get_by_type("screenshot")

    @property
    def console_logs(self) -> list[Evidence]:
        """Get all console log evidence."""
        return self.get_by_type("console_log")

    @property
    def network_requests(self) -> list[Evidence]:
        """Get all network request evidence."""
        return self.get_by_type("network_request")

    @property
    def dom_snapshots(self) -> list[Evidence]:
        """Get all DOM snapshot evidence."""
        return self.get_by_type("dom_snapshot")

    def __len__(self) -> int:
        """Get evidence count."""
        return len(self.items)

    def __iter__(self):
        """Iterate over evidence items."""
        return iter(self.items)
