"""SQLAlchemy 2.0 async ORM models for BugHive."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DECIMAL,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class CrawlSessionDB(Base):
    """Database model for crawl sessions."""

    __tablename__ = "crawl_sessions"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Core fields
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
    )
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Metrics
    pages_discovered: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    pages_crawled: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    bugs_found: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_cost: Mapped[float] = mapped_column(
        DECIMAL(10, 4),
        nullable=False,
        default=0.0,
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    pages: Mapped[list["PageDB"]] = relationship(
        "PageDB",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    bugs: Mapped[list["BugDB"]] = relationship(
        "BugDB",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="valid_status"),
        CheckConstraint("pages_discovered >= 0", name="non_negative_pages_discovered"),
        CheckConstraint("pages_crawled >= 0", name="non_negative_pages_crawled"),
        CheckConstraint("bugs_found >= 0", name="non_negative_bugs_found"),
        CheckConstraint("total_cost >= 0", name="non_negative_total_cost"),
        Index("idx_session_status_created", "status", "created_at"),
        Index("idx_session_base_url_status", "base_url", "status"),
    )

    def __repr__(self) -> str:
        return f"<CrawlSession(id={self.id}, base_url={self.base_url}, status={self.status})>"


class PageDB(Base):
    """Database model for crawled pages."""

    __tablename__ = "pages"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign keys
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    parent_page_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        index=True,
    )

    # Core fields
    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="discovered",
        index=True,
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)

    # Content fields
    screenshot_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
    )
    analysis_result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Performance metrics
    response_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )
    content_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    content_length: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Error handling
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    crawled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    session: Mapped["CrawlSessionDB"] = relationship(
        "CrawlSessionDB",
        back_populates="pages",
        foreign_keys=[session_id],
    )
    bugs: Mapped[list["BugDB"]] = relationship(
        "BugDB",
        back_populates="page",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('discovered', 'crawling', 'analyzed', 'error')", name="valid_page_status"),
        CheckConstraint("depth >= 0", name="non_negative_depth"),
        CheckConstraint("response_time_ms >= 0", name="non_negative_response_time"),
        CheckConstraint("content_length >= 0", name="non_negative_content_length"),
        Index("idx_page_session_status", "session_id", "status"),
        Index("idx_page_session_depth", "session_id", "depth"),
        Index("idx_page_url_session", "url", "session_id", unique=True),
        Index("idx_page_crawled_at", "crawled_at"),
    )

    def __repr__(self) -> str:
        return f"<Page(id={self.id}, url={self.url}, status={self.status})>"


class BugDB(Base):
    """Database model for bugs."""

    __tablename__ = "bugs"

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True,
    )

    # Foreign keys
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    page_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    # Core fields
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    steps_to_reproduce: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
    )
    evidence: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="detected",
        index=True,
    )

    # Linear integration
    linear_issue_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    linear_issue_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    # Additional context
    expected_behavior: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    actual_behavior: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    affected_users: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    browser_info: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Dismissal tracking
    dismissed_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    session: Mapped["CrawlSessionDB"] = relationship(
        "CrawlSessionDB",
        back_populates="bugs",
        foreign_keys=[session_id],
    )
    page: Mapped["PageDB"] = relationship(
        "PageDB",
        back_populates="bugs",
        foreign_keys=[page_id],
    )

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "category IN ('ui_ux', 'data', 'edge_case', 'performance', 'security')",
            name="valid_category"
        ),
        CheckConstraint(
            "priority IN ('critical', 'high', 'medium', 'low')",
            name="valid_priority"
        ),
        CheckConstraint(
            "status IN ('detected', 'validated', 'reported', 'dismissed')",
            name="valid_bug_status"
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="valid_confidence"),
        Index("idx_bug_session_priority", "session_id", "priority"),
        Index("idx_bug_session_category", "session_id", "category"),
        Index("idx_bug_session_status", "session_id", "status"),
        Index("idx_bug_page_priority", "page_id", "priority"),
        Index("idx_bug_confidence", "confidence"),
        Index("idx_bug_created_at", "created_at"),
        Index("idx_bug_linear_issue", "linear_issue_id"),
    )

    def __repr__(self) -> str:
        return f"<Bug(id={self.id}, title={self.title}, priority={self.priority}, status={self.status})>"
