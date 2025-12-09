"""Tests for progress tracker."""

import tempfile
from pathlib import Path

import pytest

from src.utils.progress_tracker import ProgressTracker


def test_progress_tracker_update():
    """Test progress update writes to file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ProgressTracker("test-session", output_dir=tmpdir)
        tracker.update(
            stage="crawling",
            pages_done=5,
            pages_total=10,
            bugs_found=3,
            cost=0.05,
        )
        assert tracker.progress_file.exists()
        content = tracker.progress_file.read_text()
        assert "crawling" in content
        assert "5/10" in content


def test_progress_tracker_save_load_state():
    """Test state save and load."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ProgressTracker("test-session", output_dir=tmpdir)
        state = {"pages": ["url1", "url2"], "bugs": 5}
        tracker.save_state(state)
        loaded = tracker.load_state()
        assert loaded == state


def test_progress_tracker_with_eta():
    """Test progress update with ETA."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ProgressTracker("test-session", output_dir=tmpdir)
        tracker.update(
            stage="analyzing",
            pages_done=2,
            pages_total=10,
            bugs_found=1,
            cost=0.02,
            eta_seconds=120,
        )
        content = tracker.progress_file.read_text()
        assert "ETA: 120s" in content


def test_progress_tracker_get_summary():
    """Test getting progress summary."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ProgressTracker("test-session", output_dir=tmpdir)

        # No summary yet
        assert tracker.get_progress_summary() is None

        # Add progress
        tracker.update(
            stage="crawling",
            pages_done=5,
            pages_total=10,
            bugs_found=3,
            cost=0.05,
        )

        summary = tracker.get_progress_summary()
        assert summary is not None
        assert "crawling" in summary
        assert "5/10" in summary


def test_progress_tracker_multiple_updates():
    """Test multiple progress updates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ProgressTracker("test-session", output_dir=tmpdir)

        # Multiple updates
        tracker.update(stage="crawling", pages_done=1, pages_total=10, bugs_found=0, cost=0.01)
        tracker.update(stage="analyzing", pages_done=1, pages_total=10, bugs_found=2, cost=0.03)
        tracker.update(stage="classifying", pages_done=1, pages_total=10, bugs_found=2, cost=0.05)

        content = tracker.progress_file.read_text()
        lines = content.strip().split("\n")
        assert len(lines) == 3
        assert "crawling" in lines[0]
        assert "analyzing" in lines[1]
        assert "classifying" in lines[2]


def test_progress_tracker_complex_state():
    """Test saving complex state with nested structures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ProgressTracker("test-session", output_dir=tmpdir)

        complex_state = {
            "session_id": "test-123",
            "pages_crawled": [
                {"url": "https://example.com", "depth": 0},
                {"url": "https://example.com/page1", "depth": 1},
            ],
            "bugs": [
                {"id": "bug-1", "priority": "high", "title": "Test bug"},
            ],
            "config": {
                "max_pages": 100,
                "focus_areas": ["forms", "navigation"],
            },
        }

        tracker.save_state(complex_state)
        loaded = tracker.load_state()

        assert loaded["session_id"] == "test-123"
        assert len(loaded["pages_crawled"]) == 2
        assert len(loaded["bugs"]) == 1
        assert loaded["config"]["max_pages"] == 100


def test_progress_tracker_no_state_file():
    """Test loading state when file doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracker = ProgressTracker("test-session", output_dir=tmpdir)
        loaded = tracker.load_state()
        assert loaded is None


def test_progress_tracker_creates_directory():
    """Test that tracker creates output directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        nested_dir = Path(tmpdir) / "nested" / "progress"
        tracker = ProgressTracker("test-session", output_dir=nested_dir)

        tracker.update(
            stage="crawling",
            pages_done=1,
            pages_total=5,
            bugs_found=0,
            cost=0.01,
        )

        assert nested_dir.exists()
        assert tracker.progress_file.exists()
