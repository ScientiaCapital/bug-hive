"""LangGraph conditional edge functions.

These functions determine routing between nodes based on state conditions.
"""

import logging
from typing import Literal

from src.graph.state import BugHiveState

logger = logging.getLogger(__name__)


def should_validate(
    state: BugHiveState,
) -> Literal["validate", "report"]:
    """Determine if bugs need validation before reporting.

    Routes to:
    - "validate": If there are critical/high priority bugs not yet validated
    - "report": If all high-priority bugs are validated or no high-priority bugs exist

    Args:
        state: Current workflow state

    Returns:
        Next node: "validate" or "report"
    """
    validation_needed = state.get("validation_needed", [])
    validated_bugs = state.get("validated_bugs", [])

    # Get IDs of already validated bugs
    validated_ids = {b["id"] for b in validated_bugs}

    # Check if there are bugs needing validation that haven't been validated
    unvalidated = [bug_id for bug_id in validation_needed if bug_id not in validated_ids]

    if unvalidated:
        logger.info(f"{len(unvalidated)} bugs need validation")
        return "validate"

    logger.info("No bugs need validation, proceeding to report")
    return "report"


def should_continue_crawling(
    state: BugHiveState,
) -> Literal["continue", "finish"]:
    """Determine if we should continue crawling or finish the workflow.

    Stop conditions:
    1. Reached max_pages limit
    2. No more uncrawled pages available
    3. Too many critical bugs found (early stop for urgent issues)
    4. Too many errors (system instability)
    5. Orchestrator decision to stop

    Args:
        state: Current workflow state

    Returns:
        Next action: "continue" (crawl more pages) or "finish" (summarize)
    """
    config = state.get("config", {})
    pages_crawled = state.get("pages_crawled", [])
    pages_discovered = state.get("pages_discovered", [])
    classified_bugs = state.get("classified_bugs", [])
    errors = state.get("errors", [])

    # 1. Check max_pages limit
    max_pages = config.get("max_pages", 100)
    if len(pages_crawled) >= max_pages:
        logger.info(f"Reached max_pages limit ({max_pages}). Finishing crawl.")
        return "finish"

    # 2. Check for uncrawled pages
    uncrawled = [p for p in pages_discovered if p.get("status") == "discovered"]
    if not uncrawled:
        logger.info("No uncrawled pages remaining. Finishing crawl.")
        return "finish"

    # 3. Early stop on too many critical bugs
    critical_bugs = [
        b for b in classified_bugs
        if b.get("priority") == "critical" and not b.get("is_duplicate")
    ]

    strategy = config.get("strategy", {})
    quality_gates = strategy.get("quality_gates", {})
    critical_threshold = quality_gates.get("stop_on_critical_count", 5)

    if len(critical_bugs) >= critical_threshold:
        logger.warning(
            f"Found {len(critical_bugs)} critical bugs (threshold: {critical_threshold}). "
            "Stopping crawl to prioritize bug fixes."
        )
        return "finish"

    # 4. Stop if too many errors
    if len(errors) > 20:
        logger.error(
            f"Too many errors ({len(errors)}). Stopping crawl due to system instability."
        )
        return "finish"

    # 5. Check orchestrator decision
    if not state.get("should_continue", True):
        logger.info("Orchestrator decided to stop crawling.")
        return "finish"

    # Continue crawling
    logger.info(
        f"Continuing crawl. Progress: {len(pages_crawled)}/{max_pages} pages, "
        f"{len(uncrawled)} pages remaining, {len(critical_bugs)} critical bugs found."
    )
    return "continue"


def all_validated(bugs: list[dict], state: BugHiveState) -> bool:
    """Check if all high-priority bugs have been validated.

    Args:
        bugs: List of bugs to check
        state: Current workflow state

    Returns:
        True if all bugs are validated, False otherwise
    """
    validated_bugs = state.get("validated_bugs", [])
    validated_ids = {b["id"] for b in validated_bugs}

    return all(b["id"] in validated_ids for b in bugs)


def get_uncrawled_pages(state: BugHiveState) -> list[dict]:
    """Get list of uncrawled pages.

    Args:
        state: Current workflow state

    Returns:
        List of page dicts with status="discovered"
    """
    pages_discovered = state.get("pages_discovered", [])
    return [p for p in pages_discovered if p.get("status") == "discovered"]


def should_create_tickets(state: BugHiveState) -> Literal["create_tickets", "skip_tickets"]:
    """Determine if we should create Linear tickets.

    Routes to:
    - "create_tickets": If config enables ticket creation and there are reported bugs
    - "skip_tickets": If ticket creation is disabled or no bugs to report

    Args:
        state: Current workflow state

    Returns:
        Next node: "create_tickets" or "skip_tickets"
    """
    config = state.get("config", {})
    reported_bugs = state.get("reported_bugs", [])

    # Check if ticket creation is enabled
    if not config.get("create_linear_tickets", False):
        logger.info("Linear ticket creation disabled in config")
        return "skip_tickets"

    # Check if there are bugs to report
    if not reported_bugs:
        logger.info("No reported bugs to create tickets for")
        return "skip_tickets"

    logger.info(f"Creating tickets for {len(reported_bugs)} bugs")
    return "create_tickets"


def should_analyze_page(state: BugHiveState) -> Literal["analyze", "skip"]:
    """Determine if we should analyze the current page.

    Skip analysis if:
    - Current page is None (crawl failed)
    - Page data is missing
    - Page is a known static resource (CSS, JS, images)

    Args:
        state: Current workflow state

    Returns:
        Next action: "analyze" or "skip"
    """
    current_page = state.get("current_page")

    if not current_page:
        logger.warning("No current page to analyze, skipping")
        return "skip"

    page_data = current_page.get("page_data")
    if not page_data:
        logger.warning("No page data available, skipping analysis")
        return "skip"

    # Check if page is a static resource
    url = page_data.get("url", "")
    static_extensions = [".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".woff", ".woff2"]

    if any(url.lower().endswith(ext) for ext in static_extensions):
        logger.info(f"Skipping analysis for static resource: {url}")
        return "skip"

    return "analyze"
