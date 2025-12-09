"""Pydantic model for raw issues detected during page analysis."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .evidence import Evidence


class RawIssue(BaseModel):
    """Represents a raw issue detected during page analysis.

    RawIssues are intermediate detections that may be refined into Bug objects
    after validation and deduplication.
    """

    type: Literal[
        "console_error",
        "network_failure",
        "performance",
        "visual",
        "content",
        "form",
        "accessibility",
        "security"
    ] = Field(
        ...,
        description="Issue type category"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Brief issue title"
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Detailed issue description"
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Evidence supporting this issue"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Detection confidence score (0.0-1.0)"
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(
        default="medium",
        description="Issue severity level"
    )
    url: str | None = Field(
        default=None,
        description="Page URL where issue was found"
    )
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When issue was detected"
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional metadata about the issue"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "type": "console_error",
                    "title": "Uncaught TypeError in app.js",
                    "description": "Cannot read property 'map' of undefined at line 42",
                    "evidence": [
                        {
                            "type": "console_log",
                            "content": '{"level": "error", "message": "TypeError: Cannot read property..."}',
                            "timestamp": "2024-01-15T10:30:00Z"
                        }
                    ],
                    "confidence": 0.95,
                    "severity": "high",
                    "url": "https://example.com/products",
                },
                {
                    "type": "network_failure",
                    "title": "HTTP 500 on POST /api/users",
                    "description": "Server error when creating user",
                    "evidence": [
                        {
                            "type": "network_request",
                            "content": '{"url": "/api/users", "status": 500, "method": "POST"}',
                            "timestamp": "2024-01-15T10:31:00Z"
                        }
                    ],
                    "confidence": 0.98,
                    "severity": "critical",
                    "url": "https://example.com/signup",
                },
                {
                    "type": "performance",
                    "title": "Slow page load: 4523ms",
                    "description": "Page took 4523ms to load (threshold: 3000ms)",
                    "evidence": [
                        {
                            "type": "performance_metrics",
                            "content": '{"loadTime": 4523, "domReady": 3200}',
                            "timestamp": "2024-01-15T10:32:00Z"
                        }
                    ],
                    "confidence": 0.85,
                    "severity": "medium",
                    "url": "https://example.com/products",
                }
            ]
        }
    }


class PageAnalysisResult(BaseModel):
    """Result of page analysis containing all detected issues."""

    url: str = Field(
        ...,
        description="URL of analyzed page"
    )
    issues_found: list[RawIssue] = Field(
        default_factory=list,
        description="List of detected issues"
    )
    analysis_time: float = Field(
        ...,
        ge=0.0,
        description="Analysis duration in seconds"
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores by issue type"
    )
    page_title: str | None = Field(
        default=None,
        description="Page title from extraction"
    )
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When analysis was performed"
    )
    metadata: dict | None = Field(
        default=None,
        description="Additional analysis metadata"
    )

    @property
    def total_issues(self) -> int:
        """Get total count of detected issues."""
        return len(self.issues_found)

    @property
    def issues_by_severity(self) -> dict[str, int]:
        """Get count of issues by severity level."""
        counts: dict[str, int] = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0
        }
        for issue in self.issues_found:
            counts[issue.severity] += 1
        return counts

    @property
    def issues_by_type(self) -> dict[str, int]:
        """Get count of issues by type."""
        counts: dict[str, int] = {}
        for issue in self.issues_found:
            counts[issue.type] = counts.get(issue.type, 0) + 1
        return counts

    @property
    def high_confidence_issues(self) -> list[RawIssue]:
        """Get issues with confidence >= 0.8."""
        return [issue for issue in self.issues_found if issue.confidence >= 0.8]

    @property
    def critical_issues(self) -> list[RawIssue]:
        """Get critical severity issues."""
        return [issue for issue in self.issues_found if issue.severity == "critical"]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://example.com/products",
                    "issues_found": [],
                    "analysis_time": 2.34,
                    "confidence_scores": {
                        "console_error": 0.92,
                        "network_failure": 0.88,
                        "performance": 0.85
                    },
                    "page_title": "Products - Example Site",
                }
            ]
        }
    }
