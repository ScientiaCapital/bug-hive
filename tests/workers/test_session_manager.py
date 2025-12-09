"""Tests for SessionManager Redis state management."""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.workers.session_manager import SessionManager


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("src.workers.session_manager.redis.from_url") as mock:
        redis_client = MagicMock()
        mock.return_value = redis_client
        yield redis_client


@pytest.fixture
def session_manager(mock_redis):
    """SessionManager with mocked Redis."""
    return SessionManager()


class TestSessionManager:
    """Test suite for SessionManager."""

    def test_get_session_state_found(self, session_manager, mock_redis):
        """Test getting existing session state."""
        session_id = "test-session-123"
        state = {
            "session_id": session_id,
            "status": "running",
            "pages_crawled": 5,
            "bugs_found": 2,
        }

        mock_redis.get.return_value = json.dumps(state)

        result = session_manager.get_session_state(session_id)

        assert result == state
        mock_redis.get.assert_called_once_with(f"bughive:session:{session_id}")

    def test_get_session_state_not_found(self, session_manager, mock_redis):
        """Test getting non-existent session state."""
        session_id = "nonexistent"
        mock_redis.get.return_value = None

        result = session_manager.get_session_state(session_id)

        assert result is None

    def test_update_session_state(self, session_manager, mock_redis):
        """Test updating session state."""
        session_id = "test-session-123"
        state = {"status": "running", "pages_crawled": 10}

        session_manager.update_session_state(session_id, state)

        mock_redis.setex.assert_called_once_with(
            f"bughive:session:{session_id}", 86400, json.dumps(state)
        )

    def test_update_progress(self, session_manager, mock_redis):
        """Test updating crawl progress."""
        session_id = "test-session-123"
        existing_state = {"status": "pending", "task_id": "task-123"}

        mock_redis.get.return_value = json.dumps(existing_state)

        session_manager.update_progress(
            session_id=session_id,
            pages_crawled=5,
            bugs_found=2,
            current_url="https://example.com/page5",
        )

        # Verify state was updated with progress
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"bughive:session:{session_id}"
        assert call_args[0][1] == 86400

        updated_state = json.loads(call_args[0][2])
        assert updated_state["status"] == "running"
        assert updated_state["pages_crawled"] == 5
        assert updated_state["bugs_found"] == 2
        assert updated_state["current_url"] == "https://example.com/page5"

    def test_mark_complete(self, session_manager, mock_redis):
        """Test marking session as complete."""
        session_id = "test-session-123"
        existing_state = {"status": "running", "pages_crawled": 10}
        summary = {"pages_crawled": 10, "bugs_found": 5, "duration_seconds": 120.5}

        mock_redis.get.return_value = json.dumps(existing_state)

        session_manager.mark_complete(session_id, summary)

        # Verify final state
        call_args = mock_redis.setex.call_args
        updated_state = json.loads(call_args[0][2])

        assert updated_state["status"] == "completed"
        assert updated_state["summary"] == summary
        assert "completed_at" in updated_state

    def test_mark_failed(self, session_manager, mock_redis):
        """Test marking session as failed."""
        session_id = "test-session-123"
        error_message = "Browser crashed"
        existing_state = {"status": "running"}

        mock_redis.get.return_value = json.dumps(existing_state)

        session_manager.mark_failed(session_id, error_message)

        # Verify error state
        call_args = mock_redis.setex.call_args
        updated_state = json.loads(call_args[0][2])

        assert updated_state["status"] == "failed"
        assert updated_state["error"] == error_message
        assert "completed_at" in updated_state

    def test_delete_session(self, session_manager, mock_redis):
        """Test deleting session."""
        session_id = "test-session-123"
        mock_redis.delete.return_value = 1

        result = session_manager.delete_session(session_id)

        assert result is True
        mock_redis.delete.assert_called_once_with(f"bughive:session:{session_id}")

    def test_delete_session_not_found(self, session_manager, mock_redis):
        """Test deleting non-existent session."""
        session_id = "nonexistent"
        mock_redis.delete.return_value = 0

        result = session_manager.delete_session(session_id)

        assert result is False

    def test_get_all_sessions(self, session_manager, mock_redis):
        """Test getting all active sessions."""
        sessions = [
            {"session_id": "session-1", "status": "running"},
            {"session_id": "session-2", "status": "completed"},
        ]

        mock_redis.keys.return_value = [
            "bughive:session:session-1",
            "bughive:session:session-2",
        ]
        mock_redis.get.side_effect = [json.dumps(s) for s in sessions]

        result = session_manager.get_all_sessions()

        assert len(result) == 2
        assert result[0]["session_id"] == "session-1"
        assert result[1]["session_id"] == "session-2"

    def test_cleanup_completed_sessions(self, session_manager, mock_redis):
        """Test cleanup of old completed sessions."""
        import time

        old_time = time.time() - (25 * 3600)  # 25 hours ago
        recent_time = time.time() - (1 * 3600)  # 1 hour ago

        sessions = [
            {
                "session_id": "old-completed",
                "status": "completed",
                "completed_at": old_time,
            },
            {
                "session_id": "recent-completed",
                "status": "completed",
                "completed_at": recent_time,
            },
            {"session_id": "running", "status": "running"},
        ]

        mock_redis.keys.return_value = [
            f"bughive:session:{s['session_id']}" for s in sessions
        ]
        mock_redis.get.side_effect = [json.dumps(s) for s in sessions]
        mock_redis.delete.return_value = 1

        deleted_count = session_manager.cleanup_completed_sessions(max_age_hours=24)

        # Should only delete old completed session
        assert deleted_count == 1
        mock_redis.delete.assert_called_once_with("bughive:session:old-completed")
