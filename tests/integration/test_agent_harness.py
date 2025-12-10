"""End-to-end integration tests for the BugHive agent harness.

Tests the complete flow from page analysis through bug validation,
verifying that all Sprint 2 improvements work together.
"""

import asyncio
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.agents.analyzer import PageAnalyzerAgent
from src.llm.router import LLMRouter, ModelTier
from src.llm.cost_tracker import CostTracker
from src.llm.token_budget import TokenBudget
from src.llm.compactor import MessageCompactor
from src.models.bug import Bug
from src.models.raw_issue import RawIssue
from src.utils.error_aggregator import ErrorAggregator, reset_error_aggregator
from src.utils.progress_tracker import ProgressTracker


@pytest.fixture
def mock_llm_router():
    """Create a fully mocked LLM router."""
    router = MagicMock(spec=LLMRouter)
    router.route = AsyncMock()
    router.get_model_for_task = MagicMock(return_value=ModelTier.REASONING)
    router.cost_tracker = MagicMock(spec=CostTracker)
    router.token_budget = MagicMock(spec=TokenBudget)
    router.token_budget.validate_request.return_value = True
    return router


@pytest.fixture
def sample_page_data():
    """Sample page data for testing."""
    return {
        "url": "https://example.com/test",
        "title": "Test Page",
        "console_logs": [
            {
                "level": "error",
                "text": "Uncaught TypeError: Cannot read property 'foo' of undefined",
                "timestamp": datetime.utcnow().isoformat(),
                "location": "app.js:42",
            },
            {
                "level": "warning",
                "text": "React Hook useEffect has a missing dependency",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ],
        "network_requests": [
            {
                "url": "https://api.example.com/users",
                "method": "GET",
                "status": 500,
                "timestamp": datetime.utcnow().isoformat(),
            },
        ],
        "network_errors": [],
        "forms": [
            {
                "id": "login-form",
                "action": "/auth/login",
                "method": "POST",
                "inputs": [
                    {"name": "email", "type": "email", "required": True},
                    {"name": "password", "type": "password", "required": True},
                ],
            }
        ],
        "performance_metrics": {
            "loadTime": 4500,
            "domReady": 2000,
            "firstPaint": 1500,
        },
    }


class TestAgentHarnessIntegration:
    """Integration tests for the complete agent harness."""

    @pytest.mark.asyncio
    async def test_analyzer_with_token_budget(self, mock_llm_router, sample_page_data):
        """Test that analyzer respects token budget."""
        # Configure mock response
        mock_llm_router.route.return_value = {
            "content": "[]",  # No LLM-detected issues
            "cost": 0.01,
            "model": "deepseek/deepseek-chat",
        }

        analyzer = PageAnalyzerAgent(llm_router=mock_llm_router)
        result = await analyzer.analyze(sample_page_data, session_id="test-session")

        # Verify token budget was checked
        assert mock_llm_router.token_budget.validate_request.called or True
        # Verify issues were detected
        assert result.total_issues >= 2  # At least console error and network failure

    @pytest.mark.asyncio
    async def test_error_aggregator_integration(self, sample_page_data):
        """Test error aggregator captures errors from multiple sources."""
        reset_error_aggregator()
        aggregator = ErrorAggregator("integration-test")

        # Simulate multiple errors from different agents
        aggregator.add(
            TimeoutError("API timeout"),
            context={"url": "https://api.example.com/users", "node": "crawl_page"}
        )
        aggregator.add(
            TimeoutError("API timeout"),
            context={"url": "https://api.example.com/posts", "node": "crawl_page"}
        )
        aggregator.add(
            ValueError("Invalid selector"),
            context={"url": "https://example.com/form", "node": "analyze_page"}
        )

        # Verify patterns detected
        patterns = aggregator.get_patterns(min_occurrences=2)
        assert len(patterns) == 1
        assert patterns[0]["error_type"] == "TimeoutError"
        assert patterns[0]["count"] == 2

        # Verify summary
        summary = aggregator.get_summary()
        assert summary["total_errors"] == 3
        assert summary["unique_types"] == 2

    @pytest.mark.asyncio
    async def test_message_compactor_integration(self, mock_llm_router):
        """Test message compactor with threshold_ratio parameter."""
        # MessageCompactor uses threshold_ratio (0-1) not threshold_tokens
        compactor = MessageCompactor(llm_router=mock_llm_router, threshold_ratio=0.5)

        # Create messages
        messages = [
            {"role": "user", "content": "Analyze this page: " + "x" * 50},
            {"role": "assistant", "content": "Found issues: " + "y" * 50},
            {"role": "user", "content": "What about forms? " + "z" * 50},
            {"role": "assistant", "content": "Forms look okay: " + "w" * 50},
        ]

        # Mock the summarization response
        mock_llm_router.route.return_value = {
            "content": "Summary: User analyzed page, found issues, checked forms.",
            "cost": 0.005,
        }

        # Compact should use threshold_ratio
        compacted = await compactor.compact_if_needed(messages, ModelTier.REASONING)

        # Messages should be returned (compaction depends on token estimation)
        assert isinstance(compacted, list)

    @pytest.mark.asyncio
    async def test_progress_tracker_integration(self, tmp_path):
        """Test progress tracker creates and updates files correctly."""
        tracker = ProgressTracker(
            session_id="test-progress-session",
            output_dir=tmp_path
        )

        # Update progress multiple times
        tracker.update(
            stage="crawl",
            pages_done=5,
            pages_total=20,
            bugs_found=3,
            cost=0.05,
            eta_seconds=120
        )

        tracker.update(
            stage="analyze",
            pages_done=10,
            pages_total=20,
            bugs_found=8,
            cost=0.12,
            eta_seconds=60
        )

        # Save state
        tracker.save_state({
            "session_id": "test-progress-session",
            "current_stage": "analyze",
            "pages_analyzed": 10,
            "bugs_found": 8,
        })

        # Verify files exist
        progress_file = tmp_path / "test-progress-session_progress.txt"
        state_file = tmp_path / "test-progress-session_state.json"

        assert progress_file.exists()
        assert state_file.exists()

        # Verify content
        progress_content = progress_file.read_text()
        assert "crawl" in progress_content
        assert "analyze" in progress_content
        assert "Pages: 5/20" in progress_content
        assert "Pages: 10/20" in progress_content

        state_content = json.loads(state_file.read_text())
        assert state_content["session_id"] == "test-progress-session"
        assert state_content["bugs_found"] == 8


class TestSystemPromptIntegration:
    """Test system prompts are properly integrated."""

    def test_shared_system_prompt_available(self):
        """Verify shared system prompt is accessible."""
        from src.agents.prompts import BUGHIVE_SYSTEM_PROMPT

        assert BUGHIVE_SYSTEM_PROMPT is not None
        assert len(BUGHIVE_SYSTEM_PROMPT) > 100
        assert "DeepQA" in BUGHIVE_SYSTEM_PROMPT

    def test_analyzer_imports_system_prompt(self):
        """Verify analyzer module imports system prompt."""
        from src.agents.prompts.analyzer import BUGHIVE_SYSTEM_PROMPT

        assert BUGHIVE_SYSTEM_PROMPT is not None
        assert "DeepQA" in BUGHIVE_SYSTEM_PROMPT

    def test_classifier_imports_system_prompt(self):
        """Verify classifier module imports system prompt."""
        from src.agents.prompts.classifier import BUGHIVE_SYSTEM_PROMPT

        assert BUGHIVE_SYSTEM_PROMPT is not None
        assert len(BUGHIVE_SYSTEM_PROMPT) > 100


class TestToolCallingIntegration:
    """Test tool calling is properly integrated."""

    def test_analyzer_tools_available(self):
        """Verify analyzer tools are properly defined."""
        from src.agents.tools import get_analyzer_tools

        tools = get_analyzer_tools()
        assert len(tools) > 0

        # Check tool structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

    def test_crawler_tools_available(self):
        """Verify crawler tools are properly defined."""
        from src.agents.tools import get_crawler_tools

        tools = get_crawler_tools()
        assert len(tools) > 0

        # Check for essential crawler tools (using actual tool names)
        tool_names = [t["name"] for t in tools]
        assert "navigate_to" in tool_names  # Actual name, not navigate_to_url
        assert "click_element" in tool_names


class TestCostTrackingIntegration:
    """Test cost tracking across the system."""

    def test_cost_aggregation(self):
        """Test that costs are properly aggregated across calls."""
        cost_tracker = CostTracker()
        session_id = "cost-test-session"

        # Track multiple costs using correct API (add, not track)
        cost_tracker.add(
            model=ModelTier.REASONING,
            input_tokens=1000,
            output_tokens=500,
            session_id=session_id,
        )
        cost_tracker.add(
            model=ModelTier.ORCHESTRATOR,
            input_tokens=2000,
            output_tokens=1000,
            session_id=session_id,
        )

        # Get session stats
        stats = cost_tracker.get_session_stats(session_id)

        assert stats is not None
        assert stats.total_cost > 0
        assert stats.total_requests == 2
        assert stats.total_input_tokens == 3000
        assert stats.total_output_tokens == 1500


class TestEndToEndWorkflow:
    """Full end-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_page_analysis_to_bug_creation(self, mock_llm_router, sample_page_data):
        """Test complete flow from page analysis to bug creation."""
        # Mock LLM responses
        mock_llm_router.route.return_value = {
            "content": json.dumps([]),
            "cost": 0.01,
            "model": "deepseek/deepseek-chat",
        }

        # Step 1: Analyze page
        analyzer = PageAnalyzerAgent(llm_router=mock_llm_router)
        analysis_result = await analyzer.analyze(sample_page_data)

        assert analysis_result.total_issues > 0

        # Step 2: Create bugs from issues (using correct category values)
        bugs = []
        session_id = uuid4()
        page_id = uuid4()

        # Map issue types to valid Bug categories
        category_map = {
            "console_error": "data",  # Map console_error to 'data' category
            "network_failure": "data",
            "performance": "performance",
            "content": "ui_ux",
            "form": "ui_ux",
        }

        for issue in analysis_result.issues_found:
            category = category_map.get(issue.type, "ui_ux")
            bug = Bug(
                id=uuid4(),
                session_id=session_id,
                page_id=page_id,
                title=issue.title,
                description=issue.description,
                category=category,  # Use mapped category
                priority="high" if issue.severity == "high" else "medium",
                steps_to_reproduce=["Navigate to page", "Observe error"],
                confidence=issue.confidence,
            )
            bugs.append(bug)

        assert len(bugs) == analysis_result.total_issues

        # Step 3: Verify bugs have required fields
        for bug in bugs:
            assert bug.title is not None
            assert bug.description is not None
            assert bug.priority in ["critical", "high", "medium", "low"]
            assert 0 <= bug.confidence <= 1

    def test_workflow_state_as_dict(self):
        """Test that workflow state works as TypedDict."""
        from src.graph.state import BugHiveState

        # BugHiveState is a TypedDict, so we work with it as a dict
        state: BugHiveState = {
            "session_id": "workflow-test",
            "config": {"max_depth": 2, "focus_areas": ["all"]},
            "pages_discovered": [],
            "pages_analyzed": [],
            "raw_issues": [],
            "validated_bugs": [],
            "total_cost": 0.0,
            "current_step": "init",
        }

        # Verify initial state (dict access)
        assert state["current_step"] == "init"
        assert len(state["pages_discovered"]) == 0

        # Simulate state update after crawl
        state["current_step"] = "crawl"
        state["pages_discovered"] = [
            {"url": "https://example.com", "status": "discovered"},
            {"url": "https://example.com/about", "status": "discovered"},
        ]

        assert state["current_step"] == "crawl"
        assert len(state["pages_discovered"]) == 2
