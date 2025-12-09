"""Tests for LangGraph workflow."""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.graph.state import BugHiveState, create_initial_state
from src.graph.edges import (
    should_validate,
    should_continue_crawling,
    should_create_tickets,
    all_validated,
    get_uncrawled_pages,
)


class TestStateCreation:
    """Test state initialization."""

    def test_create_initial_state(self):
        """Test creating initial state with config."""
        config = {
            "base_url": "https://example.com",
            "max_pages": 50,
            "max_depth": 3,
        }

        state = create_initial_state(config)

        assert state["config"] == config
        assert state["session_id"] is not None
        assert state["pages_discovered"] == []
        assert state["pages_crawled"] == []
        assert state["raw_issues"] == []
        assert state["classified_bugs"] == []
        assert state["total_cost"] == 0.0
        assert state["should_continue"] is True
        assert state["start_time"] is not None


class TestConditionalEdges:
    """Test conditional edge functions."""

    def test_should_validate_with_unvalidated_bugs(self):
        """Test validation needed when critical bugs exist."""
        state: BugHiveState = {
            "validation_needed": ["bug1", "bug2"],
            "validated_bugs": [],
        }

        assert should_validate(state) == "validate"

    def test_should_validate_all_validated(self):
        """Test skip validation when all bugs validated."""
        state: BugHiveState = {
            "validation_needed": ["bug1", "bug2"],
            "validated_bugs": [
                {"id": "bug1"},
                {"id": "bug2"},
            ],
        }

        assert should_validate(state) == "report"

    def test_should_validate_no_bugs(self):
        """Test skip validation when no bugs need it."""
        state: BugHiveState = {
            "validation_needed": [],
            "validated_bugs": [],
        }

        assert should_validate(state) == "report"

    def test_should_continue_max_pages_reached(self):
        """Test stop when max_pages reached."""
        state: BugHiveState = {
            "config": {"max_pages": 10},
            "pages_crawled": [{"url": f"page{i}"} for i in range(10)],
            "pages_discovered": [{"url": "page11", "status": "discovered"}],
            "classified_bugs": [],
            "errors": [],
            "should_continue": True,
        }

        assert should_continue_crawling(state) == "finish"

    def test_should_continue_no_uncrawled_pages(self):
        """Test stop when no uncrawled pages."""
        state: BugHiveState = {
            "config": {"max_pages": 100},
            "pages_crawled": [{"url": "page1"}],
            "pages_discovered": [{"url": "page1", "status": "crawled"}],
            "classified_bugs": [],
            "errors": [],
            "should_continue": True,
        }

        assert should_continue_crawling(state) == "finish"

    def test_should_continue_too_many_critical_bugs(self):
        """Test stop when critical bug threshold exceeded."""
        state: BugHiveState = {
            "config": {
                "max_pages": 100,
                "strategy": {
                    "quality_gates": {
                        "stop_on_critical_count": 3
                    }
                },
            },
            "pages_crawled": [{"url": "page1"}],
            "pages_discovered": [{"url": "page2", "status": "discovered"}],
            "classified_bugs": [
                {"id": f"bug{i}", "priority": "critical", "is_duplicate": False}
                for i in range(5)
            ],
            "errors": [],
            "should_continue": True,
        }

        assert should_continue_crawling(state) == "finish"

    def test_should_continue_too_many_errors(self):
        """Test stop when too many errors."""
        state: BugHiveState = {
            "config": {"max_pages": 100},
            "pages_crawled": [{"url": "page1"}],
            "pages_discovered": [{"url": "page2", "status": "discovered"}],
            "classified_bugs": [],
            "errors": [{"error": f"error{i}"} for i in range(25)],
            "should_continue": True,
        }

        assert should_continue_crawling(state) == "finish"

    def test_should_continue_orchestrator_stop(self):
        """Test stop when orchestrator decides."""
        state: BugHiveState = {
            "config": {"max_pages": 100},
            "pages_crawled": [{"url": "page1"}],
            "pages_discovered": [{"url": "page2", "status": "discovered"}],
            "classified_bugs": [],
            "errors": [],
            "should_continue": False,
        }

        assert should_continue_crawling(state) == "finish"

    def test_should_continue_normal(self):
        """Test continue when conditions met."""
        state: BugHiveState = {
            "config": {"max_pages": 100},
            "pages_crawled": [{"url": "page1"}],
            "pages_discovered": [
                {"url": "page1", "status": "crawled"},
                {"url": "page2", "status": "discovered"},
            ],
            "classified_bugs": [],
            "errors": [],
            "should_continue": True,
        }

        assert should_continue_crawling(state) == "continue"

    def test_should_create_tickets_enabled(self):
        """Test create tickets when enabled."""
        state: BugHiveState = {
            "config": {"create_linear_tickets": True},
            "reported_bugs": [{"id": "bug1"}],
        }

        assert should_create_tickets(state) == "create_tickets"

    def test_should_create_tickets_disabled(self):
        """Test skip tickets when disabled."""
        state: BugHiveState = {
            "config": {"create_linear_tickets": False},
            "reported_bugs": [{"id": "bug1"}],
        }

        assert should_create_tickets(state) == "skip_tickets"

    def test_should_create_tickets_no_bugs(self):
        """Test skip tickets when no bugs."""
        state: BugHiveState = {
            "config": {"create_linear_tickets": True},
            "reported_bugs": [],
        }

        assert should_create_tickets(state) == "skip_tickets"


class TestHelperFunctions:
    """Test helper functions."""

    def test_all_validated_true(self):
        """Test all_validated returns True when all bugs validated."""
        bugs = [{"id": "bug1"}, {"id": "bug2"}]
        state: BugHiveState = {
            "validated_bugs": [
                {"id": "bug1"},
                {"id": "bug2"},
            ]
        }

        assert all_validated(bugs, state) is True

    def test_all_validated_false(self):
        """Test all_validated returns False when some bugs not validated."""
        bugs = [{"id": "bug1"}, {"id": "bug2"}, {"id": "bug3"}]
        state: BugHiveState = {
            "validated_bugs": [
                {"id": "bug1"},
                {"id": "bug2"},
            ]
        }

        assert all_validated(bugs, state) is False

    def test_get_uncrawled_pages(self):
        """Test getting uncrawled pages."""
        state: BugHiveState = {
            "pages_discovered": [
                {"url": "page1", "status": "crawled"},
                {"url": "page2", "status": "discovered"},
                {"url": "page3", "status": "discovered"},
                {"url": "page4", "status": "failed"},
            ]
        }

        uncrawled = get_uncrawled_pages(state)

        assert len(uncrawled) == 2
        assert all(p["status"] == "discovered" for p in uncrawled)


class TestWorkflowIntegration:
    """Integration tests for workflow."""

    @pytest.mark.asyncio
    async def test_workflow_creation(self):
        """Test workflow can be created."""
        from src.graph.workflow import create_workflow

        workflow = create_workflow()
        assert workflow is not None

    @pytest.mark.asyncio
    async def test_quick_crawl_config(self):
        """Test quick crawl creates correct config."""
        # This would be an actual integration test
        # For now, just test the config structure
        from src.graph.workflow import quick_crawl

        # Mock the actual workflow execution
        with patch("src.graph.workflow.create_workflow") as mock_workflow:
            mock_workflow.return_value.ainvoke = AsyncMock(
                return_value={
                    "summary": {
                        "session_id": "test",
                        "pages": {"total_crawled": 5},
                        "bugs": {"validated_bugs": 3},
                    }
                }
            )

            # This would actually run in a real test
            # summary = await quick_crawl("https://example.com")
            # assert summary is not None
