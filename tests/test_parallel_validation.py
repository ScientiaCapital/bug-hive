"""Tests for parallel bug validation.

Tests the parallel validation system with semaphore-based rate limiting,
extended thinking integration, and error handling.
"""

import asyncio
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.graph.parallel import parallel_validate_batch, validate_single_bug
from src.models.bug import Bug
from src.llm.router import LLMRouter


@pytest.fixture
def mock_llm_router():
    """Create a mock LLM router."""
    router = MagicMock(spec=LLMRouter)
    router.route = AsyncMock()
    return router


@pytest.fixture
def sample_bugs():
    """Create sample bugs for testing."""
    session_id = uuid4()
    page_id = uuid4()

    bugs = [
        Bug(
            id=uuid4(),
            session_id=session_id,
            page_id=page_id,
            title="Critical login failure",
            description="Users cannot log in",
            category="data",
            priority="critical",
            steps_to_reproduce=["Navigate to /login", "Enter credentials", "Click submit"],
            confidence=0.95,
        ),
        Bug(
            id=uuid4(),
            session_id=session_id,
            page_id=page_id,
            title="High priority button bug",
            description="Submit button not working",
            category="ui_ux",
            priority="high",
            steps_to_reproduce=["Click submit button"],
            confidence=0.85,
        ),
        Bug(
            id=uuid4(),
            session_id=session_id,
            page_id=page_id,
            title="Medium priority styling issue",
            description="Button color incorrect",
            category="ui_ux",
            priority="medium",
            steps_to_reproduce=["View button"],
            confidence=0.75,
        ),
        Bug(
            id=uuid4(),
            session_id=session_id,
            page_id=page_id,
            title="Low priority typo",
            description="Typo in footer text",
            category="ui_ux",
            priority="low",
            steps_to_reproduce=["Scroll to footer"],
            confidence=0.65,
        ),
    ]
    return bugs


@pytest.mark.asyncio
async def test_validate_single_bug_success(mock_llm_router, sample_bugs):
    """Test successful validation of a single bug."""
    bug = sample_bugs[0]

    # Mock LLM response
    mock_llm_router.route.return_value = {
        "content": '{"is_valid": true, "validated_priority": "critical", "reasoning": "Legitimate critical bug", "recommended_action": "fix_immediately"}',
        "cost": 0.05,
    }

    result = await validate_single_bug(
        bug=bug,
        llm_router=mock_llm_router,
        session_id="test-session",
    )

    # Verify result
    assert result["is_valid"] is True
    assert result["validated_priority"] == "critical"
    assert result["reasoning"] == "Legitimate critical bug"
    assert result["recommended_action"] == "fix_immediately"
    assert result["cost"] == 0.05

    # Verify LLM was called correctly
    mock_llm_router.route.assert_called_once()
    call_args = mock_llm_router.route.call_args
    assert call_args.kwargs["task"] == "validate_critical_bug"
    assert call_args.kwargs["session_id"] == "test-session"
    assert call_args.kwargs["temperature"] == 0.3


@pytest.mark.asyncio
async def test_validate_single_bug_json_parse_error(mock_llm_router, sample_bugs):
    """Test handling of JSON parse errors in validation response."""
    bug = sample_bugs[0]

    # Mock LLM response with invalid JSON
    mock_llm_router.route.return_value = {
        "content": "This is not valid JSON",
        "cost": 0.05,
    }

    result = await validate_single_bug(
        bug=bug,
        llm_router=mock_llm_router,
        session_id="test-session",
    )

    # Should use default valid response
    assert result["is_valid"] is True
    assert result["reasoning"] == "This is not valid JSON"
    assert result["validated_priority"] == bug.priority
    assert result["recommended_action"] == "investigate"


@pytest.mark.asyncio
async def test_validate_single_bug_exception(mock_llm_router, sample_bugs):
    """Test handling of exceptions during validation."""
    bug = sample_bugs[0]

    # Mock LLM exception
    mock_llm_router.route.side_effect = Exception("API error")

    result = await validate_single_bug(
        bug=bug,
        llm_router=mock_llm_router,
        session_id="test-session",
    )

    # Should return error result
    assert result["is_valid"] is False
    assert result["error"] == "API error"
    assert result["recommended_action"] == "retry"
    assert result["cost"] == 0.0


@pytest.mark.asyncio
async def test_parallel_validate_batch_basic(mock_llm_router, sample_bugs):
    """Test basic parallel validation of multiple bugs."""
    # Mock LLM responses
    mock_llm_router.route.return_value = {
        "content": '{"is_valid": true, "validated_priority": "high", "reasoning": "Valid bug", "recommended_action": "investigate"}',
        "cost": 0.05,
    }

    results = await parallel_validate_batch(
        bugs=sample_bugs[:3],  # Validate 3 bugs
        llm_router=mock_llm_router,
        session_id="test-session",
        batch_size=5,
        use_extended_thinking=False,
    )

    # Verify results
    assert len(results) == 3
    assert all(r["is_valid"] for r in results)
    assert all("bug_id" in r for r in results)
    assert all("cost" in r for r in results)

    # Verify all bugs were validated
    bug_ids = {str(bug.id) for bug in sample_bugs[:3]}
    result_ids = {r["bug_id"] for r in results}
    assert bug_ids == result_ids


@pytest.mark.asyncio
async def test_parallel_validate_batch_semaphore_limit(mock_llm_router, sample_bugs):
    """Test that semaphore limits concurrent validations."""
    # Track concurrent calls
    concurrent_calls = 0
    max_concurrent = 0

    async def mock_route_with_tracking(*args, **kwargs):
        nonlocal concurrent_calls, max_concurrent
        concurrent_calls += 1
        max_concurrent = max(max_concurrent, concurrent_calls)

        # Simulate some processing time
        await asyncio.sleep(0.1)

        concurrent_calls -= 1
        return {
            "content": '{"is_valid": true, "validated_priority": "high", "reasoning": "Valid", "recommended_action": "investigate"}',
            "cost": 0.05,
        }

    mock_llm_router.route = mock_route_with_tracking

    # Validate with batch_size=2
    results = await parallel_validate_batch(
        bugs=sample_bugs,  # 4 bugs
        llm_router=mock_llm_router,
        session_id="test-session",
        batch_size=2,  # Only 2 at a time
        use_extended_thinking=False,
    )

    # Verify semaphore worked (max 2 concurrent)
    assert max_concurrent <= 2
    assert len(results) == 4


@pytest.mark.asyncio
async def test_parallel_validate_batch_extended_thinking(mock_llm_router, sample_bugs):
    """Test that extended thinking is used for critical/high priority bugs."""
    with patch("src.graph.thinking_validator.validate_bug_with_thinking") as mock_thinking:
        # Mock extended thinking response
        mock_thinking.return_value = {
            "is_valid": True,
            "validated_priority": "critical",
            "reasoning": "Extended thinking analysis",
            "recommended_action": "fix_immediately",
            "thinking_trace": "Deep analysis...",
            "cost": 0.15,
        }

        # Mock standard validation for medium/low bugs
        mock_llm_router.route.return_value = {
            "content": '{"is_valid": true, "validated_priority": "medium", "reasoning": "Standard validation", "recommended_action": "defer"}',
            "cost": 0.05,
        }

        results = await parallel_validate_batch(
            bugs=sample_bugs,  # Critical, high, medium, low
            llm_router=mock_llm_router,
            session_id="test-session",
            batch_size=5,
            use_extended_thinking=True,  # Enable extended thinking
        )

        # Verify extended thinking was used for critical/high priority
        assert len(results) == 4

        # Extended thinking should be called for critical and high priority bugs
        assert mock_thinking.call_count == 2  # Critical + high

        # Standard validation should be called for medium and low
        assert mock_llm_router.route.call_count == 2  # Medium + low


@pytest.mark.asyncio
async def test_parallel_validate_batch_error_handling(mock_llm_router, sample_bugs):
    """Test that individual bug failures don't crash the batch."""
    call_count = 0

    async def mock_route_with_errors(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # Fail every other bug
        if call_count % 2 == 0:
            raise Exception(f"Validation error {call_count}")

        return {
            "content": '{"is_valid": true, "validated_priority": "high", "reasoning": "Valid", "recommended_action": "investigate"}',
            "cost": 0.05,
        }

    mock_llm_router.route = mock_route_with_errors

    results = await parallel_validate_batch(
        bugs=sample_bugs,
        llm_router=mock_llm_router,
        session_id="test-session",
        batch_size=5,
        use_extended_thinking=False,
    )

    # All bugs should have results
    assert len(results) == 4

    # Half should be valid, half should have errors
    valid_count = sum(1 for r in results if r["is_valid"])
    error_count = sum(1 for r in results if "error" in r)

    assert valid_count == 2  # Bugs 1 and 3
    assert error_count == 2  # Bugs 2 and 4


@pytest.mark.asyncio
async def test_parallel_validate_batch_mixed_results(mock_llm_router, sample_bugs):
    """Test handling of mixed validation results (valid/invalid)."""
    call_count = 0

    async def mock_route_with_mixed_results(*args, **kwargs):
        nonlocal call_count
        call_count += 1

        # Alternate between valid and invalid
        is_valid = call_count % 2 == 1

        return {
            "content": f'{{"is_valid": {str(is_valid).lower()}, "validated_priority": "medium", "reasoning": "Validation result", "recommended_action": "investigate"}}',
            "cost": 0.05,
        }

    mock_llm_router.route = mock_route_with_mixed_results

    results = await parallel_validate_batch(
        bugs=sample_bugs,
        llm_router=mock_llm_router,
        session_id="test-session",
        batch_size=5,
        use_extended_thinking=False,
    )

    # Verify mixed results
    assert len(results) == 4
    valid_count = sum(1 for r in results if r.get("is_valid"))
    invalid_count = sum(1 for r in results if not r.get("is_valid"))

    assert valid_count == 2
    assert invalid_count == 2


@pytest.mark.asyncio
async def test_parallel_validate_batch_priority_override(mock_llm_router, sample_bugs):
    """Test that priority can be overridden during validation."""
    async def mock_route_with_priority_override(*args, **kwargs):
        # Downgrade all priorities to "low"
        return {
            "content": '{"is_valid": true, "validated_priority": "low", "reasoning": "Not as severe as reported", "recommended_action": "defer"}',
            "cost": 0.05,
        }

    mock_llm_router.route = mock_route_with_priority_override

    results = await parallel_validate_batch(
        bugs=sample_bugs,
        llm_router=mock_llm_router,
        session_id="test-session",
        batch_size=5,
        use_extended_thinking=False,
    )

    # All results should have priority downgraded to "low"
    assert all(r.get("validated_priority") == "low" for r in results)


@pytest.mark.asyncio
async def test_parallel_validate_batch_cost_tracking(mock_llm_router, sample_bugs):
    """Test that costs are properly tracked and aggregated."""
    # Mock varying costs
    costs = [0.05, 0.10, 0.15, 0.20]
    cost_index = 0

    async def mock_route_with_costs(*args, **kwargs):
        nonlocal cost_index
        cost = costs[cost_index]
        cost_index += 1

        return {
            "content": '{"is_valid": true, "validated_priority": "medium", "reasoning": "Valid", "recommended_action": "investigate"}',
            "cost": cost,
        }

    mock_llm_router.route = mock_route_with_costs

    results = await parallel_validate_batch(
        bugs=sample_bugs,
        llm_router=mock_llm_router,
        session_id="test-session",
        batch_size=5,
        use_extended_thinking=False,
    )

    # Verify individual costs
    assert results[0]["cost"] == 0.05
    assert results[1]["cost"] == 0.10
    assert results[2]["cost"] == 0.15
    assert results[3]["cost"] == 0.20

    # Verify total cost
    total_cost = sum(r["cost"] for r in results)
    assert total_cost == 0.50


@pytest.mark.asyncio
async def test_parallel_validate_batch_empty_list(mock_llm_router):
    """Test handling of empty bug list."""
    results = await parallel_validate_batch(
        bugs=[],
        llm_router=mock_llm_router,
        session_id="test-session",
        batch_size=5,
        use_extended_thinking=False,
    )

    assert results == []


@pytest.mark.asyncio
async def test_validate_single_bug_prompt_format(mock_llm_router, sample_bugs):
    """Test that validation prompt is properly formatted."""
    bug = sample_bugs[0]

    mock_llm_router.route.return_value = {
        "content": '{"is_valid": true, "validated_priority": "critical", "reasoning": "Valid", "recommended_action": "fix_immediately"}',
        "cost": 0.05,
    }

    await validate_single_bug(
        bug=bug,
        llm_router=mock_llm_router,
        session_id="test-session",
    )

    # Verify prompt contains all required fields
    call_args = mock_llm_router.route.call_args
    prompt = call_args.kwargs["messages"][0]["content"]

    assert bug.title in prompt
    assert bug.description in prompt
    assert bug.category in prompt
    assert bug.priority in prompt
    assert str(bug.confidence) in prompt
    assert all(step in prompt for step in bug.steps_to_reproduce)
