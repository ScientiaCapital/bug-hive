"""Pydantic models for bugs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from .evidence import Evidence


class Bug(BaseModel):
    """Represents a detected bug."""

    id: UUID = Field(..., description="Unique bug identifier")
    session_id: UUID = Field(..., description="Parent crawl session ID")
    page_id: UUID = Field(..., description="Page where bug was found")
    category: Literal["ui_ux", "data", "edge_case", "performance", "security"] = Field(
        ...,
        description="Bug category"
    )
    priority: Literal["critical", "high", "medium", "low"] = Field(
        ...,
        description="Bug priority/severity"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Brief bug title"
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Detailed bug description"
    )
    steps_to_reproduce: list[str] = Field(
        ...,
        min_length=1,
        description="Steps to reproduce the bug"
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="Evidence supporting the bug"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="AI confidence score (0-1)"
    )
    status: Literal["detected", "validated", "reported", "dismissed"] = Field(
        default="detected",
        description="Bug lifecycle status"
    )
    linear_issue_id: str | None = Field(
        default=None,
        description="Linear issue ID if reported"
    )
    linear_issue_url: str | None = Field(
        default=None,
        description="Linear issue URL if reported"
    )
    expected_behavior: str | None = Field(
        default=None,
        description="What should happen instead"
    )
    actual_behavior: str | None = Field(
        default=None,
        description="What actually happens"
    )
    affected_users: str | None = Field(
        default=None,
        description="Which users are affected (e.g., 'all users', 'mobile users')"
    )
    browser_info: dict | None = Field(
        default=None,
        description="Browser/device information"
    )
    dismissed_reason: str | None = Field(
        default=None,
        description="Reason if bug was dismissed"
    )
    dismissed_at: datetime | None = Field(
        default=None,
        description="When bug was dismissed"
    )
    reported_at: datetime | None = Field(
        default=None,
        description="When bug was reported to Linear"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Bug detection timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )

    @field_validator("steps_to_reproduce")
    @classmethod
    def validate_steps(cls, v: list[str]) -> list[str]:
        """Ensure steps are not empty strings."""
        if not v:
            raise ValueError("At least one reproduction step is required")
        if any(not step.strip() for step in v):
            raise ValueError("Reproduction steps cannot be empty")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440002",
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "page_id": "550e8400-e29b-41d4-a716-446655440001",
                    "category": "ui_ux",
                    "priority": "high",
                    "title": "Submit button overlaps text on mobile viewport",
                    "description": "On mobile viewports (< 768px), the submit button...",
                    "steps_to_reproduce": [
                        "Navigate to /products",
                        "Resize browser to 375px width",
                        "Observe button overlapping text"
                    ],
                    "evidence": [
                        {
                            "type": "screenshot",
                            "content": "https://storage.example.com/screenshots/abc123.png",
                            "timestamp": "2024-01-15T10:30:00Z"
                        }
                    ],
                    "confidence": 0.92,
                    "status": "detected",
                }
            ]
        }
    }


class BugCreate(BaseModel):
    """Schema for creating a new bug."""

    session_id: UUID
    page_id: UUID
    category: Literal["ui_ux", "data", "edge_case", "performance", "security"]
    priority: Literal["critical", "high", "medium", "low"]
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    steps_to_reproduce: list[str] = Field(..., min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    affected_users: str | None = None
    browser_info: dict | None = None


class BugUpdate(BaseModel):
    """Schema for updating a bug."""

    status: Literal["detected", "validated", "reported", "dismissed"] | None = None
    priority: Literal["critical", "high", "medium", "low"] | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    steps_to_reproduce: list[str] | None = None
    evidence: list[Evidence] | None = None
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    linear_issue_id: str | None = None
    linear_issue_url: str | None = None
    dismissed_reason: str | None = None
    dismissed_at: datetime | None = None
    reported_at: datetime | None = None


class BugReport(BaseModel):
    """Bug report for Linear integration."""

    title: str
    description: str
    priority: Literal["critical", "high", "medium", "low"]
    category: Literal["ui_ux", "data", "edge_case", "performance", "security"]
    steps_to_reproduce: list[str]
    evidence_urls: list[str] = Field(
        default_factory=list,
        description="URLs to screenshots and other evidence"
    )
    page_url: str
    confidence: float

    @property
    def formatted_description(self) -> str:
        """Format bug description for Linear."""
        parts = [
            "**Description**",
            self.description,
            "",
            "**Steps to Reproduce**",
        ]
        for i, step in enumerate(self.steps_to_reproduce, 1):
            parts.append(f"{i}. {step}")

        if self.evidence_urls:
            parts.extend([
                "",
                "**Evidence**",
            ])
            for url in self.evidence_urls:
                parts.append(f"- {url}")

        parts.extend([
            "",
            f"**Page URL**: {self.page_url}",
            f"**AI Confidence**: {self.confidence:.2%}",
            "",
            "*Generated by BugHive autonomous QA agent*",
        ])

        return "\n".join(parts)


class BugStatistics(BaseModel):
    """Statistics about bugs in a session."""

    total_bugs: int = Field(default=0, description="Total bugs found")
    bugs_by_priority: dict[str, int] = Field(
        default_factory=dict,
        description="Count of bugs by priority"
    )
    bugs_by_category: dict[str, int] = Field(
        default_factory=dict,
        description="Count of bugs by category"
    )
    bugs_by_status: dict[str, int] = Field(
        default_factory=dict,
        description="Count of bugs by status"
    )
    average_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average AI confidence score"
    )
    bugs_reported: int = Field(
        default=0,
        description="Number of bugs reported to Linear"
    )
    bugs_dismissed: int = Field(
        default=0,
        description="Number of bugs dismissed"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total_bugs": 15,
                    "bugs_by_priority": {
                        "critical": 2,
                        "high": 5,
                        "medium": 6,
                        "low": 2
                    },
                    "bugs_by_category": {
                        "ui_ux": 8,
                        "performance": 4,
                        "data": 2,
                        "security": 1
                    },
                    "bugs_by_status": {
                        "detected": 10,
                        "validated": 3,
                        "reported": 2
                    },
                    "average_confidence": 0.87,
                    "bugs_reported": 2,
                    "bugs_dismissed": 0,
                }
            ]
        }
    }


class BugFilter(BaseModel):
    """Filters for querying bugs."""

    session_id: UUID | None = None
    page_id: UUID | None = None
    category: Literal["ui_ux", "data", "edge_case", "performance", "security"] | None = None
    priority: Literal["critical", "high", "medium", "low"] | None = None
    status: Literal["detected", "validated", "reported", "dismissed"] | None = None
    min_confidence: float | None = Field(None, ge=0.0, le=1.0)
    max_confidence: float | None = Field(None, ge=0.0, le=1.0)
