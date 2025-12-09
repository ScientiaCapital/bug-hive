"""Tests for Multi-Level Fallback Chain in LLM Router."""

import pytest
from unittest.mock import AsyncMock, Mock

from src.llm.router import (
    LLMRouter,
    ModelTier,
    AllModelsFailedError,
    FALLBACK_CHAIN,
)


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client."""
    client = Mock()
    client.create_message = AsyncMock()
    return client


@pytest.fixture
def mock_openrouter_client():
    """Create a mock OpenRouter client."""
    client = Mock()
    client.create_completion = AsyncMock()
    return client


@pytest.fixture
def mock_cost_tracker():
    """Create a mock cost tracker."""
    tracker = Mock()
    tracker.add = Mock(return_value=0.05)
    return tracker


@pytest.fixture
def router(mock_anthropic_client, mock_openrouter_client, mock_cost_tracker):
    """Create LLM router with mocked clients."""
    return LLMRouter(
        anthropic_client=mock_anthropic_client,
        openrouter_client=mock_openrouter_client,
        cost_tracker=mock_cost_tracker,
    )


@pytest.fixture
def sample_messages():
    """Sample messages for testing."""
    return [{"role": "user", "content": "Analyze this bug"}]


@pytest.fixture
def sample_response():
    """Sample successful response."""
    return {
        "content": "Analysis complete",
        "usage": {"input_tokens": 100, "output_tokens": 200},
    }


# Test 1: Primary model success (no fallback needed)
@pytest.mark.asyncio
async def test_primary_model_success(router, sample_messages, sample_response, mock_openrouter_client):
    """Test that primary model succeeds without fallback."""
    mock_openrouter_client.create_completion.return_value = sample_response

    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=sample_messages,
        max_retries_per_tier=2,
    )

    # Should succeed on primary model (REASONING)
    assert response["fallback_tier"] is None
    assert response["attempt"] == 1
    assert response["fallback_chain_used"] == ["REASONING"]
    assert response["original_task"] == "analyze_page"
    assert mock_openrouter_client.create_completion.call_count == 1


# Test 2: Fallback to second tier
@pytest.mark.asyncio
async def test_fallback_to_second_tier(router, sample_messages, sample_response, mock_openrouter_client):
    """Test fallback to second tier after primary fails."""
    # First tier fails, second succeeds
    mock_openrouter_client.create_completion.side_effect = [
        Exception("REASONING tier error"),
        Exception("REASONING tier error"),  # Both retries fail
        sample_response,  # GENERAL tier succeeds
    ]

    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=sample_messages,
        max_retries_per_tier=2,
    )

    # Should fallback to GENERAL tier
    assert response["fallback_tier"] == "GENERAL"
    assert response["attempt"] == 1
    assert response["fallback_chain_used"] == ["REASONING", "GENERAL"]
    assert mock_openrouter_client.create_completion.call_count == 3


# Test 3: Fallback to third tier
@pytest.mark.asyncio
async def test_fallback_to_third_tier(router, sample_messages, sample_response, mock_openrouter_client):
    """Test fallback to third tier after first two fail."""
    # ORCHESTRATOR → REASONING → GENERAL
    chain_for_orchestrator = [ModelTier.ORCHESTRATOR, ModelTier.REASONING, ModelTier.GENERAL]

    # Mock failures for first two tiers
    mock_openrouter_client.create_completion.side_effect = [
        Exception("REASONING tier error"),
        Exception("REASONING tier error"),  # Both REASONING attempts fail
        Exception("GENERAL tier error"),
        Exception("GENERAL tier error"),  # Both GENERAL attempts fail
    ]

    # Mock Anthropic client for ORCHESTRATOR tier
    router.anthropic_client.create_message.side_effect = [
        Exception("ORCHESTRATOR error"),
        Exception("ORCHESTRATOR error"),  # Both ORCHESTRATOR attempts fail
    ]

    # This should fail all the way down
    with pytest.raises(AllModelsFailedError) as exc_info:
        await router.route_with_fallback_chain(
            task="orchestrate_session",
            messages=sample_messages,
            max_retries_per_tier=2,
        )

    error = exc_info.value
    assert len(error.errors) == 6  # 3 tiers × 2 attempts
    assert error.errors[0]["tier"] == "ORCHESTRATOR"
    assert error.errors[2]["tier"] == "REASONING"
    assert error.errors[4]["tier"] == "GENERAL"


# Test 4: All models fail (AllModelsFailedError)
@pytest.mark.asyncio
async def test_all_models_fail(router, sample_messages, mock_openrouter_client):
    """Test that AllModelsFailedError is raised when all models fail."""
    mock_openrouter_client.create_completion.side_effect = Exception("Service unavailable")

    with pytest.raises(AllModelsFailedError) as exc_info:
        await router.route_with_fallback_chain(
            task="analyze_page",
            messages=sample_messages,
            max_retries_per_tier=2,
        )

    error = exc_info.value
    assert "All models in chain failed" in str(error)
    assert len(error.errors) == 6  # REASONING (2) + GENERAL (2) + FAST (2)

    # Verify error structure
    for err in error.errors:
        assert "tier" in err
        assert "attempt" in err
        assert "error" in err
        assert err["error"] == "Service unavailable"


# Test 5: Retry logic per tier
@pytest.mark.asyncio
async def test_retry_logic_per_tier(router, sample_messages, sample_response, mock_openrouter_client):
    """Test that each tier gets the correct number of retries."""
    # First attempt fails, second succeeds
    mock_openrouter_client.create_completion.side_effect = [
        Exception("Temporary error"),
        sample_response,
    ]

    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=sample_messages,
        max_retries_per_tier=2,
    )

    # Should succeed on second attempt of primary tier
    assert response["fallback_tier"] is None
    assert response["attempt"] == 2
    assert response["fallback_chain_used"] == ["REASONING"]
    assert mock_openrouter_client.create_completion.call_count == 2


# Test 6: Response includes fallback_tier and attempt
@pytest.mark.asyncio
async def test_response_metadata(router, sample_messages, sample_response, mock_openrouter_client):
    """Test that response includes correct metadata."""
    mock_openrouter_client.create_completion.return_value = sample_response

    response = await router.route_with_fallback_chain(
        task="format_ticket",
        messages=sample_messages,
        max_retries_per_tier=1,
    )

    # Check all metadata fields
    assert "fallback_tier" in response
    assert "attempt" in response
    assert "fallback_chain_used" in response
    assert "original_task" in response
    assert response["original_task"] == "format_ticket"
    assert isinstance(response["fallback_chain_used"], list)


# Test 7: Different fallback chains for different tasks
@pytest.mark.asyncio
async def test_different_fallback_chains(router, sample_messages):
    """Test that different tasks use different fallback chains."""
    # Test ORCHESTRATOR chain
    orchestrator_chain = [ModelTier.ORCHESTRATOR] + FALLBACK_CHAIN[ModelTier.ORCHESTRATOR]
    assert orchestrator_chain == [ModelTier.ORCHESTRATOR, ModelTier.REASONING, ModelTier.GENERAL]

    # Test CODING chain
    coding_chain = [ModelTier.CODING] + FALLBACK_CHAIN[ModelTier.CODING]
    assert coding_chain == [ModelTier.CODING, ModelTier.REASONING, ModelTier.GENERAL]

    # Test GENERAL chain
    general_chain = [ModelTier.GENERAL] + FALLBACK_CHAIN[ModelTier.GENERAL]
    assert general_chain == [ModelTier.GENERAL, ModelTier.FAST]

    # Test FAST chain (no fallback)
    fast_chain = [ModelTier.FAST] + FALLBACK_CHAIN[ModelTier.FAST]
    assert fast_chain == [ModelTier.FAST]


# Test 8: Backward compatibility with route_with_fallback
@pytest.mark.asyncio
async def test_route_with_fallback_backward_compatibility(
    router, sample_messages, sample_response, mock_openrouter_client
):
    """Test that route_with_fallback maintains backward compatibility."""
    # Test with explicit fallback_tier (old behavior)
    mock_openrouter_client.create_completion.side_effect = [
        Exception("Primary failed"),
        sample_response,
    ]

    response = await router.route_with_fallback(
        task="analyze_page",
        messages=sample_messages,
        fallback_tier=ModelTier.FAST,  # Explicit fallback
    )

    assert response["fallback_used"] is True
    assert response["original_task"] == "analyze_page"


# Test 9: route_with_fallback uses chain when no explicit tier
@pytest.mark.asyncio
async def test_route_with_fallback_uses_chain(
    router, sample_messages, sample_response, mock_openrouter_client
):
    """Test that route_with_fallback uses chain when no explicit tier."""
    mock_openrouter_client.create_completion.return_value = sample_response

    response = await router.route_with_fallback(
        task="analyze_page",
        messages=sample_messages,
        # No fallback_tier specified - should use chain
    )

    # Should have chain metadata
    assert "fallback_chain_used" in response
    assert response["fallback_chain_used"] == ["REASONING"]


# Test 10: Cost tracking works with fallback
@pytest.mark.asyncio
async def test_cost_tracking_with_fallback(
    router, sample_messages, sample_response, mock_openrouter_client, mock_cost_tracker
):
    """Test that cost tracking works correctly with fallback."""
    mock_openrouter_client.create_completion.return_value = sample_response

    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=sample_messages,
        session_id="test-session",
    )

    # Cost tracker should be called
    assert mock_cost_tracker.add.called
    assert "cost" in response


# Test 11: Max retries parameter works
@pytest.mark.asyncio
async def test_max_retries_parameter(router, sample_messages, sample_response, mock_openrouter_client):
    """Test that max_retries_per_tier parameter is respected."""
    # Fail 3 times, then succeed (should fail with max_retries=2)
    mock_openrouter_client.create_completion.side_effect = [
        Exception("Error 1"),
        Exception("Error 2"),
        Exception("Error 3"),
        sample_response,
    ]

    with pytest.raises(AllModelsFailedError):
        await router.route_with_fallback_chain(
            task="format_ticket",  # FAST tier (no fallback chain)
            messages=sample_messages,
            max_retries_per_tier=2,
        )

    # Should only call 2 times (max_retries_per_tier=2)
    assert mock_openrouter_client.create_completion.call_count == 2


# Test 12: FAST tier has no fallback
@pytest.mark.asyncio
async def test_fast_tier_no_fallback(router, sample_messages, mock_openrouter_client):
    """Test that FAST tier has no fallback options."""
    mock_openrouter_client.create_completion.side_effect = Exception("FAST tier failed")

    with pytest.raises(AllModelsFailedError) as exc_info:
        await router.route_with_fallback_chain(
            task="format_ticket",  # FAST tier task
            messages=sample_messages,
            max_retries_per_tier=2,
        )

    error = exc_info.value
    # Should only attempt FAST tier (2 retries)
    assert len(error.errors) == 2
    assert all(e["tier"] == "FAST" for e in error.errors)


# Test 13: Error structure validation
@pytest.mark.asyncio
async def test_error_structure(router, sample_messages, mock_openrouter_client):
    """Test that AllModelsFailedError has correct structure."""
    mock_openrouter_client.create_completion.side_effect = Exception("Test error")

    with pytest.raises(AllModelsFailedError) as exc_info:
        await router.route_with_fallback_chain(
            task="analyze_page",
            messages=sample_messages,
            max_retries_per_tier=1,
        )

    error = exc_info.value

    # Check error has errors attribute
    assert hasattr(error, "errors")
    assert isinstance(error.errors, list)

    # Check each error dict structure
    for err in error.errors:
        assert "tier" in err
        assert "attempt" in err
        assert "error" in err
        assert isinstance(err["tier"], str)
        assert isinstance(err["attempt"], int)
        assert isinstance(err["error"], str)


# Test 14: Successful fallback after multiple tier failures
@pytest.mark.asyncio
async def test_successful_deep_fallback(
    router, sample_messages, sample_response, mock_openrouter_client
):
    """Test successful fallback after multiple tiers fail."""
    # REASONING fails twice, GENERAL fails twice, FAST succeeds
    mock_openrouter_client.create_completion.side_effect = [
        Exception("REASONING error 1"),
        Exception("REASONING error 2"),
        Exception("GENERAL error 1"),
        Exception("GENERAL error 2"),
        sample_response,  # FAST succeeds
    ]

    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=sample_messages,
        max_retries_per_tier=2,
    )

    assert response["fallback_tier"] == "FAST"
    assert response["attempt"] == 1
    assert response["fallback_chain_used"] == ["REASONING", "GENERAL", "FAST"]
    assert len(response["fallback_chain_used"]) == 3
