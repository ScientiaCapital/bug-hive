"""Tests for error aggregation and pattern detection."""

import pytest
import time
from datetime import datetime
from threading import Thread

from src.utils.error_aggregator import (
    ErrorAggregator,
    get_error_aggregator,
    reset_error_aggregator,
)


class TestErrorAggregator:
    """Test cases for ErrorAggregator class."""

    def setup_method(self):
        """Reset global aggregator before each test."""
        reset_error_aggregator()

    def test_single_error_addition(self):
        """Test adding a single error to the aggregator."""
        aggregator = ErrorAggregator("test-session")

        aggregator.add(ValueError("Invalid value"), context={"url": "http://example.com"})

        errors = aggregator.get_all_errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "ValueError"
        assert errors[0]["message"] == "Invalid value"
        assert errors[0]["context"]["url"] == "http://example.com"

    def test_error_with_string_message(self):
        """Test adding error as string instead of exception."""
        aggregator = ErrorAggregator()

        aggregator.add("Connection timeout", error_type="NetworkError")

        errors = aggregator.get_all_errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "NetworkError"
        assert errors[0]["message"] == "Connection timeout"

    def test_exception_vs_string_error_type(self):
        """Test error type detection from exception vs string."""
        aggregator = ErrorAggregator()

        aggregator.add(RuntimeError("Something broke"))

        errors = aggregator.get_all_errors()
        assert errors[0]["type"] == "RuntimeError"

    def test_context_preservation(self):
        """Test that context data is preserved in errors."""
        aggregator = ErrorAggregator()

        context = {
            "url": "http://example.com/page",
            "page_id": "123",
            "node": "crawl_page",
            "depth": 2,
        }
        aggregator.add(Exception("Test error"), context=context)

        errors = aggregator.get_all_errors()
        assert errors[0]["context"] == context

    def test_pattern_detection_min_occurrences(self):
        """Test pattern detection with minimum occurrences threshold."""
        aggregator = ErrorAggregator()

        # Add three similar errors
        for i in range(3):
            aggregator.add(
                TimeoutError("Connection timeout"),
                context={"url": f"http://example.com/page{i}"}
            )

        patterns = aggregator.get_patterns(min_occurrences=2)
        assert len(patterns) == 1
        assert patterns[0]["count"] == 3
        assert patterns[0]["error_type"] == "TimeoutError"
        assert patterns[0]["message_prefix"] == "Connection timeout"

    def test_pattern_not_returned_below_threshold(self):
        """Test that errors below threshold are not returned as patterns."""
        aggregator = ErrorAggregator()

        # Add single error
        aggregator.add(ValueError("Single error"))

        patterns = aggregator.get_patterns(min_occurrences=2)
        assert len(patterns) == 0

    def test_multiple_different_errors(self):
        """Test aggregation with multiple different error types."""
        aggregator = ErrorAggregator()

        aggregator.add(ValueError("Invalid input"))
        aggregator.add(TimeoutError("Connection timeout"))
        aggregator.add(ValueError("Invalid input"))
        aggregator.add(RuntimeError("Internal error"))

        patterns = aggregator.get_patterns(min_occurrences=2)
        assert len(patterns) == 1
        assert patterns[0]["error_type"] == "ValueError"
        assert patterns[0]["count"] == 2

    def test_message_prefix_grouping(self):
        """Test that errors are grouped by message prefix (first 100 chars)."""
        aggregator = ErrorAggregator()

        long_msg = "This is a very long error message " * 10  # > 100 chars
        short_msg = long_msg[:100]

        aggregator.add(ValueError(long_msg))
        aggregator.add(ValueError(long_msg))

        patterns = aggregator.get_patterns(min_occurrences=1)
        assert len(patterns) == 1
        assert patterns[0]["message_prefix"] == short_msg

    def test_url_extraction_from_context(self):
        """Test that URLs are extracted from context."""
        aggregator = ErrorAggregator()

        urls = [
            "http://example.com/page1",
            "http://example.com/page2",
            "http://example.com/page1",
        ]

        for url in urls:
            aggregator.add(
                TimeoutError("Timeout"),
                context={"url": url}
            )

        patterns = aggregator.get_patterns(min_occurrences=2)
        assert len(patterns[0]["urls"]) == 2  # Two unique URLs
        assert set(patterns[0]["urls"]) == {
            "http://example.com/page1",
            "http://example.com/page2",
        }

    def test_context_limiting(self):
        """Test that only first 5 contexts are kept in patterns."""
        aggregator = ErrorAggregator()

        # Add 10 errors
        for i in range(10):
            aggregator.add(
                ValueError("Same error"),
                context={"url": f"http://example.com/{i}"}
            )

        patterns = aggregator.get_patterns(min_occurrences=2)
        assert len(patterns[0]["contexts"]) == 5

    def test_patterns_sorted_by_count(self):
        """Test that patterns are sorted by count descending."""
        aggregator = ErrorAggregator()

        # Add errors with different counts
        for _ in range(5):
            aggregator.add(ValueError("Error A"))
        for _ in range(3):
            aggregator.add(TimeoutError("Error B"))
        for _ in range(2):
            aggregator.add(RuntimeError("Error C"))

        patterns = aggregator.get_patterns(min_occurrences=1)
        counts = [p["count"] for p in patterns]
        assert counts == sorted(counts, reverse=True)
        assert patterns[0]["count"] == 5
        assert patterns[1]["count"] == 3

    def test_get_summary(self):
        """Test summary generation."""
        aggregator = ErrorAggregator("test-session-123")

        # Add various errors
        aggregator.add(ValueError("Error 1"))
        aggregator.add(ValueError("Error 1"))
        aggregator.add(TimeoutError("Error 2"))
        aggregator.add(TimeoutError("Error 2"))
        aggregator.add(TimeoutError("Error 2"))
        aggregator.add(RuntimeError("Error 3"))

        summary = aggregator.get_summary()

        assert summary["total_errors"] == 6
        assert summary["unique_types"] == 3
        assert summary["pattern_count"] == 2  # Only 2 have >= 2 occurrences (ValueError, TimeoutError)
        assert summary["session_id"] == "test-session-123"
        assert len(summary["top_patterns"]) == 3
        assert summary["top_patterns"][0]["count"] == 3

    def test_get_errors_by_type(self):
        """Test filtering errors by type."""
        aggregator = ErrorAggregator()

        aggregator.add(ValueError("Error 1"))
        aggregator.add(ValueError("Error 2"))
        aggregator.add(TimeoutError("Error 3"))

        value_errors = aggregator.get_errors_by_type("ValueError")
        assert len(value_errors) == 2
        assert all(e["type"] == "ValueError" for e in value_errors)

        timeout_errors = aggregator.get_errors_by_type("TimeoutError")
        assert len(timeout_errors) == 1

    def test_clear_errors(self):
        """Test clearing all errors."""
        aggregator = ErrorAggregator()

        aggregator.add(ValueError("Error 1"))
        aggregator.add(ValueError("Error 2"))

        assert len(aggregator.get_all_errors()) == 2

        aggregator.clear()

        assert len(aggregator.get_all_errors()) == 0
        assert len(aggregator.get_patterns()) == 0

    def test_session_id_tracking(self):
        """Test that session ID is tracked in errors."""
        aggregator = ErrorAggregator("session-456")

        aggregator.add(ValueError("Test error"))

        errors = aggregator.get_all_errors()
        assert errors[0]["session_id"] == "session-456"

    def test_timestamp_recording(self):
        """Test that timestamps are recorded for errors."""
        aggregator = ErrorAggregator()
        before = datetime.now()

        aggregator.add(ValueError("Test error"))

        after = datetime.now()
        errors = aggregator.get_all_errors()
        timestamp = errors[0]["timestamp"]

        assert before <= timestamp <= after

    def test_global_aggregator(self):
        """Test global aggregator instance."""
        reset_error_aggregator()

        agg1 = get_error_aggregator("session-1")
        agg1.add(ValueError("Error in session 1"))

        agg2 = get_error_aggregator("session-1")
        assert agg1 is agg2

        agg3 = get_error_aggregator("session-2")
        assert agg3 is not agg1
        assert agg3.session_id == "session-2"

    def test_global_aggregator_without_session_id(self):
        """Test global aggregator without explicit session ID."""
        reset_error_aggregator()

        agg1 = get_error_aggregator()
        agg1.add(ValueError("Error 1"))

        agg2 = get_error_aggregator()
        assert agg1 is agg2
        assert len(agg2.get_all_errors()) == 1

    def test_thread_safe_error_addition(self):
        """Test thread-safe error addition."""
        aggregator = ErrorAggregator()
        num_threads = 10
        errors_per_thread = 100

        def add_errors():
            for i in range(errors_per_thread):
                aggregator.add(
                    ValueError(f"Error {i}"),
                    context={"thread": True}
                )

        threads = [Thread(target=add_errors) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(aggregator.get_all_errors()) == num_threads * errors_per_thread

    def test_thread_safe_pattern_detection(self):
        """Test thread-safe pattern detection during concurrent additions."""
        aggregator = ErrorAggregator()

        def add_same_error(count):
            for _ in range(count):
                aggregator.add(ValueError("Same error"))

        threads = [
            Thread(target=add_same_error, args=(10,)),
            Thread(target=add_same_error, args=(10,)),
            Thread(target=add_same_error, args=(10,)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        patterns = aggregator.get_patterns(min_occurrences=2)
        assert len(patterns) == 1
        assert patterns[0]["count"] == 30

    def test_empty_context_handling(self):
        """Test that errors work with empty context."""
        aggregator = ErrorAggregator()

        aggregator.add(ValueError("Error with no context"))

        errors = aggregator.get_all_errors()
        assert errors[0]["context"] == {}

    def test_none_context_handling(self):
        """Test that None context is converted to empty dict."""
        aggregator = ErrorAggregator()

        aggregator.add(ValueError("Error"), context=None)

        errors = aggregator.get_all_errors()
        assert errors[0]["context"] == {}

    def test_complex_error_message(self):
        """Test error with complex/long message."""
        aggregator = ErrorAggregator()

        long_message = """This is a complex error that spans multiple lines
        and contains special characters like @#$%^&*()
        and Unicode emoji like 🔥💥🚀"""

        aggregator.add(ValueError(long_message))

        errors = aggregator.get_all_errors()
        assert errors[0]["message"] == long_message
        assert len(errors[0]["message_prefix"]) <= 100

    def test_error_type_override(self):
        """Test overriding error type with custom classification."""
        aggregator = ErrorAggregator()

        aggregator.add(
            ValueError("Custom error"),
            error_type="CustomNetworkError"
        )

        errors = aggregator.get_all_errors()
        assert errors[0]["type"] == "CustomNetworkError"

    def test_pattern_first_and_last_seen(self):
        """Test that patterns track first and last seen timestamps."""
        aggregator = ErrorAggregator()

        aggregator.add(ValueError("Error"))
        time.sleep(0.01)
        aggregator.add(ValueError("Error"))

        patterns = aggregator.get_patterns(min_occurrences=1)
        assert patterns[0]["first_seen"] < patterns[0]["last_seen"]


class TestGlobalAggregator:
    """Test cases for global aggregator functions."""

    def setup_method(self):
        """Reset global aggregator before each test."""
        reset_error_aggregator()

    def test_reset_aggregator(self):
        """Test resetting global aggregator."""
        agg1 = get_error_aggregator()
        agg1.add(ValueError("Error"))

        reset_error_aggregator()

        agg2 = get_error_aggregator()
        assert agg2 is not agg1
        assert len(agg2.get_all_errors()) == 0

    def test_session_isolation(self):
        """Test that different sessions have different aggregators."""
        agg1 = get_error_aggregator("session-1")
        agg2 = get_error_aggregator("session-2")

        agg1.add(ValueError("Error in 1"))
        agg2.add(ValueError("Error in 2"))

        assert len(agg1.get_all_errors()) == 1
        assert len(agg2.get_all_errors()) == 1
        assert agg1.session_id != agg2.session_id


class TestErrorPatternDetection:
    """Integration tests for error pattern detection."""

    def setup_method(self):
        """Reset global aggregator before each test."""
        reset_error_aggregator()

    def test_real_world_scenario(self):
        """Test realistic crawl scenario with multiple error types."""
        aggregator = ErrorAggregator("crawl-session-1")

        # Simulate crawl errors from multiple pages
        urls = ["http://example.com/page1", "http://example.com/page2", "http://example.com/page3"]

        # Connection timeouts on all pages
        for url in urls:
            aggregator.add(
                TimeoutError("Connection timeout"),
                context={"url": url, "node": "crawl_page"}
            )

        # Auth errors on some pages
        for url in urls[:2]:
            aggregator.add(
                PermissionError("Authentication required"),
                context={"url": url, "node": "parse_content"}
            )

        # One random error
        aggregator.add(
            ValueError("Invalid selector"),
            context={"url": urls[0], "node": "extract_data"}
        )

        # Analyze patterns
        patterns = aggregator.get_patterns(min_occurrences=2)
        assert len(patterns) == 2

        # Timeout should be most common
        assert patterns[0]["error_type"] == "TimeoutError"
        assert patterns[0]["count"] == 3

        # Auth error second
        assert patterns[1]["error_type"] == "PermissionError"
        assert patterns[1]["count"] == 2

        # Summary should show all info
        summary = aggregator.get_summary()
        assert summary["total_errors"] == 6
        assert summary["unique_types"] == 3
        assert summary["pattern_count"] == 2
