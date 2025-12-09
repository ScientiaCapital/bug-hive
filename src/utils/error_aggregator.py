"""Error pattern detection and aggregation for BugHive."""

import logging
from datetime import datetime
from collections import defaultdict
from typing import Any
import threading

logger = logging.getLogger(__name__)


class ErrorAggregator:
    """Aggregates similar errors to detect patterns.

    Thread-safe error aggregation for parallel crawling operations.
    Groups errors by type and message prefix to identify systemic issues.
    """

    def __init__(self, session_id: str | None = None):
        """Initialize error aggregator.

        Args:
            session_id: Optional session ID for scoping errors
        """
        self.session_id = session_id
        self.errors: list[dict] = []
        self._patterns: dict[tuple, dict] = {}  # Cached patterns
        self._lock = threading.RLock()  # Thread-safe access

    def add(
        self,
        error: Exception | str,
        context: dict[str, Any] | None = None,
        error_type: str | None = None,
    ) -> None:
        """Add an error to the aggregator.

        Args:
            error: Exception instance or error message string
            context: Additional context (url, page_id, node, etc.)
            error_type: Optional override for error type classification
        """
        with self._lock:
            if isinstance(error, Exception):
                err_type = error_type or type(error).__name__
                err_msg = str(error)
            else:
                err_type = error_type or "Error"
                err_msg = error

            self.errors.append({
                "type": err_type,
                "message": err_msg,
                "message_prefix": err_msg[:100],  # First 100 chars for grouping
                "context": context or {},
                "timestamp": datetime.now(),
                "session_id": self.session_id,
            })

            # Invalidate pattern cache
            self._patterns = {}

            logger.debug(f"Added error: {err_type} - {err_msg[:50]}...")

    def get_patterns(self, min_occurrences: int = 2) -> list[dict]:
        """Aggregate similar errors and return patterns.

        Args:
            min_occurrences: Minimum count to be considered a pattern

        Returns:
            List of error patterns with counts and contexts
        """
        with self._lock:
            patterns: dict[tuple, dict] = {}

            for e in self.errors:
                # Group by (type, message_prefix)
                key = (e["type"], e["message_prefix"])

                if key not in patterns:
                    patterns[key] = {
                        "error_type": e["type"],
                        "message_prefix": e["message_prefix"],
                        "count": 0,
                        "first_seen": e["timestamp"],
                        "last_seen": e["timestamp"],
                        "contexts": [],
                        "urls": set(),
                    }

                patterns[key]["count"] += 1
                patterns[key]["last_seen"] = e["timestamp"]
                patterns[key]["contexts"].append(e["context"])

                # Track unique URLs
                if url := e["context"].get("url"):
                    patterns[key]["urls"].add(url)

            # Filter to patterns with min occurrences
            result = [
                {
                    **p,
                    "urls": list(p["urls"]),  # Convert set to list
                    "contexts": p["contexts"][:5],  # Keep first 5 contexts
                }
                for p in patterns.values()
                if p["count"] >= min_occurrences
            ]

            # Sort by count descending
            result.sort(key=lambda x: x["count"], reverse=True)

            logger.info(f"Found {len(result)} error patterns from {len(self.errors)} errors")
            return result

    def get_summary(self) -> dict:
        """Get summary statistics.

        Returns:
            Dictionary with error counts and top patterns
        """
        with self._lock:
            patterns = self.get_patterns(min_occurrences=1)

            return {
                "total_errors": len(self.errors),
                "unique_types": len(set(e["type"] for e in self.errors)),
                "pattern_count": len([p for p in patterns if p["count"] >= 2]),
                "top_patterns": patterns[:3],
                "session_id": self.session_id,
            }

    def get_all_errors(self) -> list[dict]:
        """Get all collected errors.

        Returns:
            List of all error records
        """
        with self._lock:
            return list(self.errors)

    def get_errors_by_type(self, error_type: str) -> list[dict]:
        """Get errors filtered by type.

        Args:
            error_type: Type of error to filter by

        Returns:
            List of errors matching the type
        """
        with self._lock:
            return [e for e in self.errors if e["type"] == error_type]

    def clear(self) -> None:
        """Clear all errors."""
        with self._lock:
            self.errors = []
            self._patterns = {}


# Global aggregator for session-wide error tracking
_global_aggregator: ErrorAggregator | None = None
_global_lock = threading.RLock()


def get_error_aggregator(session_id: str | None = None) -> ErrorAggregator:
    """Get or create global error aggregator.

    Args:
        session_id: Optional session ID for creating new aggregator

    Returns:
        Global ErrorAggregator instance
    """
    global _global_aggregator

    with _global_lock:
        if _global_aggregator is None or (
            session_id and _global_aggregator.session_id != session_id
        ):
            _global_aggregator = ErrorAggregator(session_id)
        return _global_aggregator


def reset_error_aggregator() -> None:
    """Reset the global error aggregator (useful for testing)."""
    global _global_aggregator

    with _global_lock:
        _global_aggregator = None
