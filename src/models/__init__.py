"""Pydantic models for BugHive."""

from .bug import (
    Bug,
    BugCreate,
    BugFilter,
    BugReport,
    BugStatistics,
    BugUpdate,
)
from .crawl import (
    CrawlConfig,
    CrawlSession,
    CrawlSessionCreate,
    CrawlSessionResponse,
    CrawlSessionUpdate,
)
from .evidence import (
    ConsoleLogEvidence,
    DOMSnapshotEvidence,
    Evidence,
    EvidenceCollection,
    NetworkRequestEvidence,
    ScreenshotEvidence,
)
from .page import (
    Page,
    PageAnalytics,
    PageCreate,
    PageInventory,
    PageUpdate,
    PageWithBugs,
)
from .raw_issue import (
    PageAnalysisResult,
    RawIssue,
)

__all__ = [
    # Bug models
    "Bug",
    "BugCreate",
    "BugUpdate",
    "BugReport",
    "BugStatistics",
    "BugFilter",
    # Crawl models
    "CrawlSession",
    "CrawlSessionCreate",
    "CrawlSessionUpdate",
    "CrawlSessionResponse",
    "CrawlConfig",
    # Page models
    "Page",
    "PageCreate",
    "PageUpdate",
    "PageInventory",
    "PageWithBugs",
    "PageAnalytics",
    # Evidence models
    "Evidence",
    "EvidenceCollection",
    "ScreenshotEvidence",
    "ConsoleLogEvidence",
    "NetworkRequestEvidence",
    "DOMSnapshotEvidence",
    # Raw issue models
    "RawIssue",
    "PageAnalysisResult",
]
