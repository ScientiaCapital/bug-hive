"""Tests for Celery tasks."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.workers.tasks import (
    cleanup_old_sessions,
    create_linear_ticket,
    health_check,
    run_crawl_session,
    upload_screenshot,
)


class TestRunCrawlSession:
    """Test suite for run_crawl_session task."""

    @patch("src.workers.tasks.asyncio.run")
    @patch("src.workers.tasks.session_manager")
    def test_run_crawl_session_success(self, mock_session_manager, mock_asyncio_run):
        """Test successful crawl session execution."""
        session_id = "test-session-123"
        config = {"base_url": "https://example.com", "max_pages": 5}

        # Mock the LangGraph workflow
        summary = {
            "pages_crawled": 5,
            "bugs_found": 3,
            "tests_passed": 10,
            "tests_failed": 2,
            "duration_seconds": 120.5,
            "status": "completed",
        }
        mock_asyncio_run.return_value = summary

        # Mock task binding
        task = run_crawl_session
        task.request = MagicMock()
        task.request.id = "task-123"
        task.request.retries = 0
        task.update_state = MagicMock()

        result = run_crawl_session(task, session_id, config)

        # Verify result
        assert result == summary
        assert result["pages_crawled"] == 5
        assert result["bugs_found"] == 3

        # Verify session manager was called
        mock_session_manager.update_session_state.assert_called()
        mock_session_manager.mark_complete.assert_called_once_with(session_id, summary)

    @patch("src.workers.tasks.asyncio.run")
    @patch("src.workers.tasks.session_manager")
    def test_run_crawl_session_failure(self, mock_session_manager, mock_asyncio_run):
        """Test crawl session failure handling."""
        session_id = "test-session-123"
        config = {"base_url": "https://example.com"}

        # Mock failure
        error = Exception("Browser crashed")
        mock_asyncio_run.side_effect = error

        # Mock task binding
        task = run_crawl_session
        task.request = MagicMock()
        task.request.id = "task-123"
        task.request.retries = 0
        task.max_retries = 3
        task.update_state = MagicMock()
        task.retry = MagicMock(side_effect=Exception("Retry called"))

        # Should retry
        with pytest.raises(Exception, match="Retry called"):
            run_crawl_session(task, session_id, config)

        # Verify session marked as failed
        mock_session_manager.mark_failed.assert_called()


class TestCreateLinearTicket:
    """Test suite for create_linear_ticket task."""

    @patch("src.workers.tasks.asyncio.run")
    @patch("src.workers.tasks.get_linear_client")
    def test_create_linear_ticket_success(self, mock_get_client, mock_asyncio_run):
        """Test successful Linear ticket creation."""
        bug_id = "bug-123"
        report = {
            "title": "Test Bug",
            "description": "This is a test bug",
            "priority": 3,
            "labels": ["test", "automated"],
        }
        team_id = "team-123"

        # Mock Linear issue response
        mock_issue = MagicMock()
        mock_issue.id = "issue-id-123"
        mock_issue.identifier = "BH-123"
        mock_issue.url = "https://linear.app/team/issue/BH-123"
        mock_asyncio_run.return_value = mock_issue

        # Mock task binding
        task = create_linear_ticket
        task.request = MagicMock()
        task.request.retries = 0
        task.max_retries = 5

        result = create_linear_ticket(task, bug_id, report, team_id)

        # Verify result
        assert result["linear_issue_id"] == "issue-id-123"
        assert result["linear_identifier"] == "BH-123"
        assert result["linear_url"] == "https://linear.app/team/issue/BH-123"

    @patch("src.workers.tasks.get_linear_client")
    def test_create_linear_ticket_retry(self, mock_get_client):
        """Test Linear ticket creation with retries."""
        bug_id = "bug-123"
        report = {"title": "Test", "description": "Test"}
        team_id = "team-123"

        # Mock API error
        mock_get_client.side_effect = Exception("API rate limit")

        # Mock task binding
        task = create_linear_ticket
        task.request = MagicMock()
        task.request.retries = 0
        task.max_retries = 5
        task.retry = MagicMock(side_effect=Exception("Retry called"))

        # Should retry
        with pytest.raises(Exception, match="Retry called"):
            create_linear_ticket(task, bug_id, report, team_id)


class TestUploadScreenshot:
    """Test suite for upload_screenshot task."""

    def test_upload_screenshot_placeholder(self):
        """Test screenshot upload placeholder."""
        session_id = "session-123"
        page_id = "page-456"
        screenshot_bytes = b"fake-png-data"

        # Mock task binding
        task = upload_screenshot
        task.request = MagicMock()
        task.request.retries = 0

        result = upload_screenshot(task, session_id, page_id, screenshot_bytes)

        # Should return placeholder URL
        assert "storage.bughive.dev" in result
        assert session_id in result
        assert page_id in result


class TestCleanupOldSessions:
    """Test suite for cleanup_old_sessions task."""

    def test_cleanup_old_sessions_placeholder(self):
        """Test cleanup task placeholder."""
        result = cleanup_old_sessions(days=30)

        # Placeholder returns 0
        assert result == 0


class TestHealthCheck:
    """Test suite for health_check task."""

    def test_health_check(self):
        """Test health check task."""
        result = health_check()

        assert result["status"] == "healthy"
        assert result["worker"] == "bughive"
        assert "version" in result
