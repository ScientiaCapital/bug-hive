"""Background task processing with Celery.

This module provides Celery-based background task processing for BugHive:
- Asynchronous crawl session execution
- Linear ticket creation
- Screenshot uploads
- Periodic cleanup tasks

Usage:
    from src.workers import celery_app, run_crawl_session

    # Queue a crawl session
    task = run_crawl_session.delay(session_id, config_dict)
"""

from .celery_app import celery_app
from .session_manager import SessionManager
from .tasks import (
    cleanup_old_sessions,
    create_linear_ticket,
    run_crawl_session,
    upload_screenshot,
)

__all__ = [
    "celery_app",
    "run_crawl_session",
    "create_linear_ticket",
    "upload_screenshot",
    "cleanup_old_sessions",
    "SessionManager",
]
