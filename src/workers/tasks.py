"""Celery task definitions for BugHive.

This module defines all background tasks:
- run_crawl_session: Execute LangGraph workflow for crawling
- create_linear_ticket: Create bug tickets in Linear
- upload_screenshot: Upload screenshots to storage
- cleanup_old_sessions: Periodic cleanup of old data

All tasks use structlog for consistent logging and include retry logic
for transient failures.
"""

import asyncio
from typing import Any

import structlog

from src.workers.celery_app import celery_app
from src.workers.session_manager import SessionManager

logger = structlog.get_logger()
session_manager = SessionManager()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_crawl_session(self, session_id: str, config: dict[str, Any]) -> dict[str, Any]:
    """Execute a BugHive crawl session using the LangGraph workflow.

    This is the main task that orchestrates the entire crawling process:
    1. Updates session state to "running"
    2. Executes the LangGraph workflow
    3. Tracks progress and updates Redis state
    4. Returns a summary of results

    Args:
        session_id: UUID of the crawl session
        config: CrawlConfig as dictionary (must be JSON-serializable)

    Returns:
        Dictionary with crawl summary:
        {
            "pages_crawled": int,
            "bugs_found": int,
            "tests_passed": int,
            "tests_failed": int,
            "duration_seconds": float,
            "status": "completed" | "failed"
        }

    Raises:
        SoftTimeLimitExceeded: If task exceeds soft time limit (50 minutes)
        Exception: Any error during crawl execution (will retry up to 3 times)
    """
    try:
        logger.info(
            "Starting crawl session",
            session_id=session_id,
            task_id=self.request.id,
            config_url=config.get("base_url"),
        )

        # Update task state in Celery
        self.update_state(
            state="CRAWLING",
            meta={
                "session_id": session_id,
                "status": "starting",
                "pages_crawled": 0,
                "bugs_found": 0,
            },
        )

        # Update session state in Redis
        session_manager.update_session_state(
            session_id,
            {
                "status": "running",
                "task_id": self.request.id,
                "started_at": asyncio.get_event_loop().time(),
            },
        )

        # Import the LangGraph workflow
        from src.graph import run_bughive

        # Run the workflow (async)
        summary = asyncio.run(run_bughive(config))

        # Mark session as complete
        session_manager.mark_complete(session_id, summary)

        logger.info(
            "Crawl session completed successfully",
            session_id=session_id,
            pages_crawled=summary.get("pages_crawled", 0),
            bugs_found=summary.get("bugs_found", 0),
            duration_seconds=summary.get("duration_seconds", 0),
        )

        return summary

    except asyncio.CancelledError:
        # Task was cancelled (likely soft time limit)
        logger.warning("Crawl session cancelled", session_id=session_id)
        session_manager.mark_failed(session_id, "Task cancelled (timeout)")
        raise

    except Exception as e:
        logger.error(
            "Crawl session failed",
            session_id=session_id,
            error=str(e),
            error_type=type(e).__name__,
            retry_count=self.request.retries,
        )

        # Update session state
        session_manager.mark_failed(session_id, str(e))

        # Retry on transient errors (network issues, browser crashes, etc.)
        if self.request.retries < self.max_retries:
            logger.info(
                "Retrying crawl session",
                session_id=session_id,
                retry_count=self.request.retries + 1,
                max_retries=self.max_retries,
            )
            raise self.retry(exc=e)

        # Max retries exceeded
        raise


@celery_app.task(bind=True, max_retries=5, default_retry_delay=30)
def create_linear_ticket(
    self, bug_id: str, report: dict[str, Any], team_id: str
) -> dict[str, str]:
    """Create a bug ticket in Linear.

    Args:
        bug_id: UUID of the bug in BugHive database
        report: Formatted bug report with title, description, priority, labels
        team_id: Linear team ID to assign the ticket to

    Returns:
        Dictionary with Linear ticket details:
        {
            "linear_issue_id": str,      # Linear's internal ID
            "linear_identifier": str,     # Human-readable ID (e.g., "BH-123")
            "linear_url": str             # Direct URL to ticket
        }

    Raises:
        Exception: Linear API errors (will retry up to 5 times)
    """
    try:
        logger.info(
            "Creating Linear ticket",
            bug_id=bug_id,
            team_id=team_id,
            title=report.get("title"),
        )

        # Import Linear client
        from src.integrations.linear import get_linear_client

        client = get_linear_client()

        # Create the issue (async)
        issue = asyncio.run(
            client.create_issue(
                title=report["title"],
                description=report["description"],
                team_id=team_id,
                priority=report.get("priority", 3),  # Default: Medium
                labels=report.get("labels", []),
                project_id=report.get("project_id"),
            )
        )

        result = {
            "linear_issue_id": issue.id,
            "linear_identifier": issue.identifier,
            "linear_url": issue.url,
        }

        logger.info(
            "Created Linear ticket successfully",
            bug_id=bug_id,
            linear_id=issue.identifier,
            linear_url=issue.url,
        )

        return result

    except Exception as e:
        logger.error(
            "Failed to create Linear ticket",
            bug_id=bug_id,
            error=str(e),
            error_type=type(e).__name__,
            retry_count=self.request.retries,
        )

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        # Max retries exceeded
        raise


@celery_app.task(bind=True, max_retries=3)
def upload_screenshot(
    self, session_id: str, page_id: str, screenshot_bytes: bytes
) -> str:
    """Upload a screenshot to cloud storage (S3/R2/etc.).

    This is a placeholder for future implementation. Currently returns a mock URL.

    Args:
        session_id: UUID of the crawl session
        page_id: UUID of the page that was screenshotted
        screenshot_bytes: Raw PNG screenshot bytes

    Returns:
        str: Public URL of the uploaded screenshot

    TODO:
        - Implement S3/Cloudflare R2 upload
        - Add image compression
        - Generate thumbnails
        - Set appropriate cache headers
    """
    try:
        logger.info(
            "Uploading screenshot",
            session_id=session_id,
            page_id=page_id,
            size_bytes=len(screenshot_bytes),
        )

        # TODO: Implement actual upload when storage is configured
        # from src.integrations.storage import upload_to_s3
        # url = await upload_to_s3(
        #     bucket="bughive-screenshots",
        #     key=f"{session_id}/{page_id}.png",
        #     data=screenshot_bytes,
        #     content_type="image/png"
        # )

        # Placeholder URL
        url = f"https://storage.bughive.dev/{session_id}/{page_id}.png"

        logger.info(
            "Screenshot uploaded (placeholder)",
            session_id=session_id,
            page_id=page_id,
            url=url,
        )

        return url

    except Exception as e:
        logger.error(
            "Failed to upload screenshot",
            session_id=session_id,
            page_id=page_id,
            error=str(e),
        )

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        raise


@celery_app.task
def cleanup_old_sessions(days: int = 30) -> int:
    """Cleanup crawl sessions and related data older than specified days.

    This is a periodic task that runs daily via Celery Beat.
    It removes old sessions from Redis and optionally from the database.

    Args:
        days: Delete sessions older than this many days (default: 30)

    Returns:
        int: Number of sessions cleaned up

    TODO:
        - Implement database cleanup
        - Archive important sessions before deletion
        - Cleanup associated screenshots from storage
    """
    try:
        logger.info("Starting cleanup task", days=days)

        # TODO: Implement actual cleanup when needed
        # from src.db import get_session_repository
        # repo = get_session_repository()
        # deleted = await repo.delete_older_than(days=days)

        # Placeholder
        deleted_count = 0

        logger.info(
            "Cleanup task completed", days=days, sessions_deleted=deleted_count
        )

        return deleted_count

    except Exception as e:
        logger.error("Cleanup task failed", days=days, error=str(e))
        raise


# Health check task (useful for monitoring)
@celery_app.task
def health_check() -> dict[str, str]:
    """Simple health check task for monitoring worker status.

    Returns:
        dict: Status information
    """
    return {
        "status": "healthy",
        "worker": "bughive",
        "version": "1.0.0",
    }
