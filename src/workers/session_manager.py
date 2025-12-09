"""Redis-based session state management for BugHive crawl sessions.

This module provides real-time state tracking for crawl sessions:
- Session status (pending, running, completed, failed)
- Progress tracking (pages crawled, bugs found)
- Error tracking and debugging
- 24-hour TTL for automatic cleanup

The SessionManager uses Redis for fast, distributed state management
that can be queried by the API for real-time progress updates.
"""

import json
from typing import Any

import redis
import structlog

from src.core.config import get_settings

logger = structlog.get_logger()


class SessionManager:
    """Manage crawl session state in Redis.

    Session State Schema:
    {
        "session_id": str,
        "status": "pending" | "running" | "completed" | "failed",
        "task_id": str,                    # Celery task ID
        "started_at": float,               # Unix timestamp
        "completed_at": float | null,
        "pages_crawled": int,
        "bugs_found": int,
        "current_url": str | null,         # Current page being crawled
        "error": str | null,               # Error message if failed
        "summary": dict | null             # Final summary on completion
    }
    """

    def __init__(self):
        """Initialize SessionManager with Redis connection."""
        settings = get_settings()

        # Parse Redis URL and create connection
        self.redis_client = redis.from_url(
            str(settings.REDIS_URL),
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,  # Auto-decode bytes to str
        )

        self.prefix = "bughive:session:"
        self.ttl = 86400  # 24 hours

        logger.info(
            "SessionManager initialized",
            redis_url=str(settings.REDIS_URL).split("@")[-1],  # Hide credentials
        )

    def _get_key(self, session_id: str) -> str:
        """Get Redis key for a session.

        Args:
            session_id: UUID of the session

        Returns:
            str: Redis key (e.g., "bughive:session:uuid")
        """
        return f"{self.prefix}{session_id}"

    def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """Get current session state from Redis.

        Args:
            session_id: UUID of the session

        Returns:
            Session state dict or None if not found
        """
        try:
            key = self._get_key(session_id)
            data = self.redis_client.get(key)

            if not data:
                return None

            return json.loads(data)

        except redis.RedisError as e:
            logger.error("Failed to get session state", session_id=session_id, error=str(e))
            return None

    def update_session_state(self, session_id: str, state: dict[str, Any]) -> None:
        """Update session state in Redis.

        Args:
            session_id: UUID of the session
            state: State dictionary to store
        """
        try:
            key = self._get_key(session_id)
            data = json.dumps(state)

            self.redis_client.setex(key, self.ttl, data)

            logger.debug("Session state updated", session_id=session_id, status=state.get("status"))

        except redis.RedisError as e:
            logger.error("Failed to update session state", session_id=session_id, error=str(e))

    def update_progress(
        self,
        session_id: str,
        pages_crawled: int,
        bugs_found: int,
        current_url: str | None = None,
    ) -> None:
        """Update crawl progress for a session.

        Args:
            session_id: UUID of the session
            pages_crawled: Total pages crawled so far
            bugs_found: Total bugs found so far
            current_url: URL currently being crawled (optional)
        """
        state = self.get_session_state(session_id) or {}

        state.update(
            {
                "pages_crawled": pages_crawled,
                "bugs_found": bugs_found,
                "status": "running",
            }
        )

        if current_url:
            state["current_url"] = current_url

        self.update_session_state(session_id, state)

        logger.info(
            "Progress updated",
            session_id=session_id,
            pages_crawled=pages_crawled,
            bugs_found=bugs_found,
        )

    def mark_complete(self, session_id: str, summary: dict[str, Any]) -> None:
        """Mark a session as successfully completed.

        Args:
            session_id: UUID of the session
            summary: Final summary from the crawl workflow
        """
        state = self.get_session_state(session_id) or {}

        import time

        state.update(
            {
                "status": "completed",
                "completed_at": time.time(),
                "summary": summary,
                "current_url": None,
            }
        )

        self.update_session_state(session_id, state)

        logger.info(
            "Session marked complete",
            session_id=session_id,
            pages_crawled=summary.get("pages_crawled", 0),
            bugs_found=summary.get("bugs_found", 0),
        )

    def mark_failed(self, session_id: str, error: str) -> None:
        """Mark a session as failed with an error message.

        Args:
            session_id: UUID of the session
            error: Error message or exception details
        """
        state = self.get_session_state(session_id) or {}

        import time

        state.update(
            {
                "status": "failed",
                "completed_at": time.time(),
                "error": error,
                "current_url": None,
            }
        )

        self.update_session_state(session_id, state)

        logger.error("Session marked failed", session_id=session_id, error=error)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session from Redis.

        Args:
            session_id: UUID of the session

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            key = self._get_key(session_id)
            deleted = self.redis_client.delete(key)

            if deleted:
                logger.info("Session deleted", session_id=session_id)
            else:
                logger.warning("Session not found for deletion", session_id=session_id)

            return bool(deleted)

        except redis.RedisError as e:
            logger.error("Failed to delete session", session_id=session_id, error=str(e))
            return False

    def get_all_sessions(self) -> list[dict[str, Any]]:
        """Get all active sessions from Redis.

        Returns:
            List of session state dictionaries
        """
        try:
            pattern = f"{self.prefix}*"
            keys = self.redis_client.keys(pattern)

            sessions = []
            for key in keys:
                data = self.redis_client.get(key)
                if data:
                    sessions.append(json.loads(data))

            return sessions

        except redis.RedisError as e:
            logger.error("Failed to get all sessions", error=str(e))
            return []

    def cleanup_completed_sessions(self, max_age_hours: int = 24) -> int:
        """Cleanup completed sessions older than max_age_hours.

        Args:
            max_age_hours: Delete completed sessions older than this

        Returns:
            int: Number of sessions deleted
        """
        import time

        cutoff_time = time.time() - (max_age_hours * 3600)

        sessions = self.get_all_sessions()
        deleted_count = 0

        for session in sessions:
            if session.get("status") == "completed":
                completed_at = session.get("completed_at")
                if completed_at and completed_at < cutoff_time:
                    session_id = session.get("session_id")
                    if session_id and self.delete_session(session_id):
                        deleted_count += 1

        logger.info(
            "Completed sessions cleaned up",
            max_age_hours=max_age_hours,
            deleted_count=deleted_count,
        )

        return deleted_count
