"""Integration tests for crash recovery and checkpointing.

Tests the progress tracking and state persistence features
that enable recovery from crashes and interruptions.
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.utils.progress_tracker import ProgressTracker


class TestProgressTrackerRecovery:
    """Test progress tracker for crash recovery scenarios."""

    def test_progress_file_survives_restart(self, tmp_path):
        """Test that progress data persists across tracker instances."""
        session_id = "recovery-test-session"

        # First tracker instance - simulate work
        tracker1 = ProgressTracker(session_id=session_id, output_dir=tmp_path)
        tracker1.update(
            stage="crawl",
            pages_done=5,
            pages_total=20,
            bugs_found=3,
            cost=0.05,
        )
        tracker1.save_state({
            "session_id": session_id,
            "current_stage": "crawl",
            "pages_done": 5,
            "last_page_url": "https://example.com/page5",
        })

        # "Crash" - create new tracker instance
        tracker2 = ProgressTracker(session_id=session_id, output_dir=tmp_path)

        # Verify we can read the saved state
        state_file = tmp_path / f"{session_id}_state.json"
        assert state_file.exists()

        with open(state_file) as f:
            recovered_state = json.load(f)

        assert recovered_state["pages_done"] == 5
        assert recovered_state["last_page_url"] == "https://example.com/page5"

        # Continue from where we left off
        tracker2.update(
            stage="crawl",
            pages_done=10,
            pages_total=20,
            bugs_found=7,
            cost=0.10,
        )

        # Verify progress file has both entries
        progress_file = tmp_path / f"{session_id}_progress.txt"
        content = progress_file.read_text()
        assert "Pages: 5/20" in content
        assert "Pages: 10/20" in content

    def test_state_file_json_valid(self, tmp_path):
        """Test that state files are valid JSON."""
        tracker = ProgressTracker(session_id="json-test", output_dir=tmp_path)

        complex_state = {
            "session_id": "json-test",
            "bugs": [
                {"id": str(uuid4()), "title": "Bug 1", "priority": "high"},
                {"id": str(uuid4()), "title": "Bug 2", "priority": "medium"},
            ],
            "metadata": {
                "started_at": datetime.utcnow().isoformat(),
                "config": {"max_depth": 3, "focus_areas": ["ui_ux", "performance"]},
            },
        }

        tracker.save_state(complex_state)

        # Read and parse
        state_file = tmp_path / "json-test_state.json"
        with open(state_file) as f:
            parsed = json.load(f)

        assert parsed["session_id"] == "json-test"
        assert len(parsed["bugs"]) == 2
        assert parsed["metadata"]["config"]["max_depth"] == 3

    def test_progress_append_mode(self, tmp_path):
        """Test that progress updates append rather than overwrite."""
        tracker = ProgressTracker(session_id="append-test", output_dir=tmp_path)

        # Multiple updates
        for i in range(5):
            tracker.update(
                stage=f"stage_{i}",
                pages_done=i * 2,
                pages_total=10,
                bugs_found=i,
                cost=i * 0.01,
            )

        # Verify all updates present
        progress_file = tmp_path / "append-test_progress.txt"
        lines = progress_file.read_text().strip().split("\n")
        assert len(lines) == 5

        # Each stage should be in order
        for i, line in enumerate(lines):
            assert f"stage_{i}" in line

    def test_eta_calculation(self, tmp_path):
        """Test that ETA is properly recorded."""
        tracker = ProgressTracker(session_id="eta-test", output_dir=tmp_path)

        tracker.update(
            stage="analyze",
            pages_done=5,
            pages_total=20,
            bugs_found=3,
            cost=0.05,
            eta_seconds=180,  # 3 minutes
        )

        progress_file = tmp_path / "eta-test_progress.txt"
        content = progress_file.read_text()
        assert "ETA: 180s" in content

    def test_handles_special_characters(self, tmp_path):
        """Test that special characters in data don't break files."""
        tracker = ProgressTracker(session_id="special-chars", output_dir=tmp_path)

        state_with_special = {
            "session_id": "special-chars",
            "last_url": "https://example.com/path?query=value&other=test",
            "error_message": 'Error: Cannot read property "foo" of undefined',
            "unicode_test": "Bug with emoji",
        }

        tracker.save_state(state_with_special)

        # Read back
        state_file = tmp_path / "special-chars_state.json"
        with open(state_file) as f:
            parsed = json.load(f)

        assert parsed["last_url"] == state_with_special["last_url"]
        assert parsed["error_message"] == state_with_special["error_message"]


class TestStateRecovery:
    """Test workflow state recovery scenarios."""

    def test_state_dict_serialization_roundtrip(self, tmp_path):
        """Test that state dict can be serialized and deserialized."""
        # BugHiveState is a TypedDict, so we work with plain dicts
        original_state = {
            "session_id": "roundtrip-test",
            "config": {"max_depth": 3, "focus_areas": ["all"]},
            "pages_discovered": [
                {"url": "https://example.com", "status": "analyzed"},
                {"url": "https://example.com/about", "status": "discovered"},
            ],
            "pages_analyzed": ["https://example.com"],
            "raw_issues": [
                {"id": str(uuid4()), "type": "console_error", "title": "Error 1"},
            ],
            "validated_bugs": [],
            "total_cost": 0.15,
            "current_step": "analyze",
        }

        # Serialize
        state_json = json.dumps(original_state, default=str)

        # Save to file
        state_file = tmp_path / "state_backup.json"
        with open(state_file, "w") as f:
            f.write(state_json)

        # Recover
        with open(state_file) as f:
            recovered_state = json.load(f)

        # Verify
        assert recovered_state["session_id"] == original_state["session_id"]
        assert len(recovered_state["pages_discovered"]) == 2
        assert recovered_state["total_cost"] == pytest.approx(0.15)

    def test_partial_state_recovery(self):
        """Test recovering from partial state."""
        # Minimal state that might exist after a crash
        partial_state = {
            "session_id": "partial-test",
            "config": {},
            "pages_discovered": [],
            "pages_analyzed": [],
            "raw_issues": [],
            "validated_bugs": [],
            "total_cost": 0.0,
            "current_step": "init",
        }

        # Should be valid dict with required fields
        assert partial_state["session_id"] == "partial-test"
        assert len(partial_state["pages_discovered"]) == 0


class TestCrashScenarios:
    """Test specific crash scenario recovery."""

    def test_recovery_mid_crawl(self, tmp_path):
        """Test recovery when crash occurs during crawl."""
        session_id = "mid-crawl-crash"
        tracker = ProgressTracker(session_id=session_id, output_dir=tmp_path)

        # Simulate crawl progress
        discovered_pages = [
            {"url": f"https://example.com/page{i}", "status": "analyzed" if i < 5 else "discovered"}
            for i in range(10)
        ]

        # Save state before "crash"
        tracker.save_state({
            "session_id": session_id,
            "current_step": "crawl",
            "pages_discovered": discovered_pages,
            "last_processed_index": 4,
        })

        # "Crash" and recover
        state_file = tmp_path / f"{session_id}_state.json"
        with open(state_file) as f:
            recovered = json.load(f)

        # Should be able to continue from page 5
        assert recovered["last_processed_index"] == 4
        remaining = [p for p in recovered["pages_discovered"] if p["status"] == "discovered"]
        assert len(remaining) == 5

    def test_recovery_mid_validation(self, tmp_path):
        """Test recovery when crash occurs during bug validation."""
        session_id = "mid-validation-crash"
        tracker = ProgressTracker(session_id=session_id, output_dir=tmp_path)

        # Simulate validation progress
        bugs = [
            {"id": str(uuid4()), "title": f"Bug {i}", "validated": i < 3}
            for i in range(10)
        ]

        tracker.save_state({
            "session_id": session_id,
            "current_step": "validate",
            "bugs": bugs,
            "validated_count": 3,
        })

        # Recover
        state_file = tmp_path / f"{session_id}_state.json"
        with open(state_file) as f:
            recovered = json.load(f)

        # Should know we validated 3 bugs
        assert recovered["validated_count"] == 3
        unvalidated = [b for b in recovered["bugs"] if not b["validated"]]
        assert len(unvalidated) == 7

    def test_output_directory_creation(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        nested_path = tmp_path / "deep" / "nested" / "progress"

        tracker = ProgressTracker(session_id="nested-test", output_dir=nested_path)
        tracker.update(
            stage="test",
            pages_done=1,
            pages_total=1,
            bugs_found=0,
            cost=0.0,
        )

        assert nested_path.exists()
        assert (nested_path / "nested-test_progress.txt").exists()


class TestConcurrentAccess:
    """Test behavior under concurrent access scenarios."""

    def test_multiple_trackers_same_session(self, tmp_path):
        """Test that multiple trackers don't corrupt data."""
        session_id = "concurrent-test"

        tracker1 = ProgressTracker(session_id=session_id, output_dir=tmp_path)
        tracker2 = ProgressTracker(session_id=session_id, output_dir=tmp_path)

        # Both write updates
        tracker1.update("stage1", 1, 10, 0, 0.01)
        tracker2.update("stage2", 2, 10, 1, 0.02)

        # Both should be in the file
        progress_file = tmp_path / f"{session_id}_progress.txt"
        content = progress_file.read_text()

        assert "stage1" in content
        assert "stage2" in content

    def test_state_overwrite_with_later_data(self, tmp_path):
        """Test that state overwrites preserve latest data."""
        session_id = "overwrite-test"

        tracker1 = ProgressTracker(session_id=session_id, output_dir=tmp_path)
        tracker2 = ProgressTracker(session_id=session_id, output_dir=tmp_path)

        # First tracker saves state
        tracker1.save_state({"version": 1, "data": "first"})

        # Second tracker saves newer state
        tracker2.save_state({"version": 2, "data": "second"})

        # Latest should win
        state_file = tmp_path / f"{session_id}_state.json"
        with open(state_file) as f:
            final = json.load(f)

        assert final["version"] == 2
        assert final["data"] == "second"
