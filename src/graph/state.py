"""BugHive workflow state schema.

Defines the shared state that flows through the LangGraph workflow.
"""

from typing import TypedDict, Annotated, Any
from langgraph.graph import add_messages


class BugHiveState(TypedDict):
    """State schema for the BugHive autonomous QA workflow.

    This state is passed between nodes in the LangGraph workflow and tracks
    the entire crawl session, bug discovery, and reporting process.
    """

    # ===== Session Info =====
    session_id: str
    """Unique identifier for this crawl session."""

    config: dict[str, Any]
    """CrawlConfig dictionary containing all configuration parameters."""

    # ===== Crawl State =====
    pages_discovered: list[dict[str, Any]]
    """All pages discovered during crawl (URL, depth, status)."""

    pages_crawled: list[dict[str, Any]]
    """Pages that have been successfully crawled."""

    current_page: dict[str, Any] | None
    """The page currently being processed."""

    crawl_complete: bool
    """Flag indicating if crawling phase is finished."""

    # ===== Bug State =====
    raw_issues: list[dict[str, Any]]
    """RawIssue objects from PageAnalyzerAgent."""

    classified_bugs: list[dict[str, Any]]
    """Bug objects after classification and deduplication."""

    validated_bugs: list[dict[str, Any]]
    """Bugs that have been validated by Orchestrator (Opus)."""

    reported_bugs: list[dict[str, Any]]
    """Bugs with generated reports ready for ticketing."""

    # ===== Orchestrator Decisions =====
    should_continue: bool
    """Orchestrator decision to continue or stop crawling."""

    validation_needed: list[str]
    """List of bug IDs that need Orchestrator validation."""

    priority_override: dict[str, str]
    """Manual priority adjustments from Orchestrator {bug_id: new_priority}."""

    # ===== Outputs =====
    linear_tickets: list[dict[str, Any]]
    """Created Linear issues with IDs and URLs."""

    summary: dict[str, Any]
    """Final session summary with stats and results."""

    # ===== Cost Tracking =====
    total_cost: float
    """Total cost in USD for all LLM calls in this session."""

    llm_calls: list[dict[str, Any]]
    """Log of all LLM calls with model, tokens, and cost."""

    # ===== Error Tracking =====
    errors: list[dict[str, Any]]
    """List of errors encountered during workflow."""

    warnings: list[dict[str, Any]]
    """List of warnings (non-fatal issues)."""

    # ===== Agent Communication =====
    messages: Annotated[list, add_messages]
    """Messages for inter-agent communication and reasoning traces."""

    # ===== Performance Metrics =====
    start_time: float | None
    """Unix timestamp when workflow started."""

    end_time: float | None
    """Unix timestamp when workflow completed."""

    node_durations: dict[str, float]
    """Duration in seconds for each node execution."""


def create_initial_state(config: dict[str, Any]) -> BugHiveState:
    """Create initial state for a new BugHive session.

    Args:
        config: CrawlConfig dictionary

    Returns:
        Initial BugHiveState with empty collections and defaults
    """
    import uuid
    import time

    return {
        # Session info
        "session_id": str(uuid.uuid4()),
        "config": config,

        # Crawl state
        "pages_discovered": [],
        "pages_crawled": [],
        "current_page": None,
        "crawl_complete": False,

        # Bug state
        "raw_issues": [],
        "classified_bugs": [],
        "validated_bugs": [],
        "reported_bugs": [],

        # Orchestrator decisions
        "should_continue": True,
        "validation_needed": [],
        "priority_override": {},

        # Outputs
        "linear_tickets": [],
        "summary": {},

        # Cost tracking
        "total_cost": 0.0,
        "llm_calls": [],

        # Error tracking
        "errors": [],
        "warnings": [],

        # Messages
        "messages": [],

        # Performance metrics
        "start_time": time.time(),
        "end_time": None,
        "node_durations": {},
    }
