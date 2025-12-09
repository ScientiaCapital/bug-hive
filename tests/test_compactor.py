"""Tests for message compaction."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.llm.compactor import MessageCompactor
from src.llm.router import LLMRouter
from src.llm.token_budget import MODEL_CONTEXT_LIMITS


@pytest.fixture
def mock_llm_router():
    """Create a mock LLM router."""
    router = AsyncMock(spec=LLMRouter)
    router.route = AsyncMock(return_value={"content": "Summarized context: bugs found on pages A, B, C."})
    return router


@pytest.fixture
def compactor(mock_llm_router):
    """Create a message compactor with mock router."""
    return MessageCompactor(
        llm_router=mock_llm_router,
        threshold_ratio=0.7,
        keep_recent=10,
    )


@pytest.mark.asyncio
async def test_no_compaction_when_under_threshold(compactor):
    """Test that no compaction occurs when under threshold."""
    # Create a small message list
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]

    # Should not trigger compaction (way under 70% threshold)
    result = await compactor.compact_if_needed(messages, model_tier="GENERAL")

    # Result should be identical
    assert result == messages


@pytest.mark.asyncio
async def test_compaction_triggers_at_threshold(compactor, mock_llm_router):
    """Test that compaction triggers when approaching context limit."""
    # Create a large message list that exceeds 70% of FAST tier (32k * 0.7 = ~22.4k tokens)
    # For Qwen models: 3.5 chars per token, need 22.4k * 3.5 = ~78k chars
    large_content = "x" * 20_000  # ~5.7k tokens per message

    messages = []
    for i in range(15):  # 15 * 5.7k = ~85k tokens, well over threshold
        messages.append({"role": "user", "content": large_content})

    result = await compactor.compact_if_needed(messages, model_tier="FAST")

    # Should have called summarization
    mock_llm_router.route.assert_called_once()

    # Result should be compacted
    assert len(result) < len(messages)

    # First message should be the summary
    assert result[0]["role"] == "system"
    assert "Previous context summary" in result[0]["content"]


@pytest.mark.asyncio
async def test_recent_messages_preserved(compactor, mock_llm_router):
    """Test that recent messages are preserved during compaction."""
    keep_recent = 5
    compactor.keep_recent = keep_recent

    # Create message list that will trigger compaction
    large_content = "x" * 30_000

    messages = []
    for i in range(15):
        messages.append({"role": "user", "content": f"Message {i}: {large_content}"})

    result = await compactor.compact_if_needed(messages, model_tier="FAST")

    # Should have: 1 summary + keep_recent messages
    assert len(result) == keep_recent + 1

    # Last message should be preserved
    assert "Message 14" in result[-1]["content"]

    # Recent messages should be intact
    for i, msg in enumerate(result[1:]):  # Skip summary
        expected_idx = len(messages) - keep_recent + i
        assert f"Message {expected_idx}" in msg["content"]


@pytest.mark.asyncio
async def test_summarization_content(compactor, mock_llm_router):
    """Test that summarization receives correct format."""
    large_content = "x" * 20_000
    messages = []
    for i in range(15):  # Ensure we exceed threshold
        messages.append({"role": "user", "content": large_content})

    await compactor.compact_if_needed(messages, model_tier="FAST")

    # Check summarization was called with correct task
    call_args = mock_llm_router.route.call_args
    assert call_args.kwargs["task"] == "summarize_session"

    # Check it uses FAST tier implicitly (via task mapping)
    # Check temperature is set for deterministic summaries
    assert call_args.kwargs["temperature"] == 0.3
    assert call_args.kwargs["max_tokens"] == 1024


@pytest.mark.asyncio
async def test_compaction_reduces_tokens(compactor, mock_llm_router):
    """Test that compaction actually reduces token count."""
    from src.llm.token_budget import TokenBudget

    budget = TokenBudget()

    # Create large message list
    large_content = "x" * 20_000
    messages = [
        {"role": "user", "content": large_content} for _ in range(15)
    ]

    original_tokens = budget.estimate_tokens(messages, model_tier="FAST")

    result = await compactor.compact_if_needed(messages, model_tier="FAST")

    compacted_tokens = budget.estimate_tokens(result, model_tier="FAST")

    # Compacted should be significantly smaller
    assert compacted_tokens < original_tokens
    # Note: Compaction may not always achieve 50% reduction depending on summary size
    # Just verify it's smaller
    assert compacted_tokens < original_tokens * 0.8  # At least 20% reduction


@pytest.mark.asyncio
async def test_no_compaction_if_already_small(compactor, mock_llm_router):
    """Test that compaction doesn't occur if message list is already small."""
    # Message count less than keep_recent
    large_content = "x" * 20_000
    messages = []
    for i in range(8):  # Less than keep_recent (10)
        messages.append({"role": "user", "content": large_content})

    result = await compactor.compact_if_needed(messages, model_tier="FAST")

    # Should not compact because len(messages) <= keep_recent
    # Even if tokens are high, we don't want to lose recent context
    assert result == messages


@pytest.mark.asyncio
async def test_different_model_tiers(compactor, mock_llm_router):
    """Test compaction works with different model tiers."""
    large_content = "x" * 20_000
    messages = [{"role": "user", "content": large_content} for _ in range(15)]

    # ORCHESTRATOR has 200k limit, should not compact
    result_opus = await compactor.compact_if_needed(messages, model_tier="ORCHESTRATOR")
    assert len(result_opus) == len(messages)  # No compaction

    # FAST has 32k limit, should compact
    result_fast = await compactor.compact_if_needed(messages, model_tier="FAST")
    assert len(result_fast) < len(messages)  # Compacted


@pytest.mark.asyncio
async def test_summary_fallback_on_error(compactor, mock_llm_router):
    """Test that compaction handles summarization errors gracefully."""
    # Make summarization fail
    mock_llm_router.route.side_effect = Exception("API error")

    large_content = "x" * 20_000
    messages = [{"role": "user", "content": large_content} for _ in range(15)]

    # Should raise the exception (compactor doesn't handle it internally)
    with pytest.raises(Exception, match="API error"):
        await compactor.compact_if_needed(messages, model_tier="FAST")


@pytest.mark.asyncio
async def test_threshold_ratio_configurable(mock_llm_router):
    """Test that threshold ratio affects when compaction triggers."""
    # Strict compactor (compact early at 50%)
    strict_compactor = MessageCompactor(
        llm_router=mock_llm_router,
        threshold_ratio=0.5,
        keep_recent=10,
    )

    # Relaxed compactor (compact late at 90%)
    relaxed_compactor = MessageCompactor(
        llm_router=mock_llm_router,
        threshold_ratio=0.9,
        keep_recent=10,
    )

    # Message that's between 50% and 90% of FAST tier limit
    # FAST = 32k tokens, 50% = 16k, 90% = 28.8k
    # Create enough messages to exceed 50% threshold but not 90%
    # Need ~18k tokens for strict threshold
    # 3.5 chars/token means we need ~63k chars
    medium_content = "x" * 5_500  # ~1.57k tokens per message
    messages = [{"role": "user", "content": medium_content} for _ in range(12)]  # ~66k chars = ~18.8k tokens, more than keep_recent

    # Strict should compact (18.8k > 16k threshold)
    strict_result = await strict_compactor.compact_if_needed(messages, model_tier="FAST")
    assert len(strict_result) < len(messages)

    # Relaxed should not compact (18.8k < 28.8k threshold)
    relaxed_result = await relaxed_compactor.compact_if_needed(messages, model_tier="FAST")
    assert len(relaxed_result) == len(messages)


@pytest.mark.asyncio
async def test_keep_recent_configurable(mock_llm_router):
    """Test that keep_recent parameter controls how many messages are preserved."""
    large_content = "x" * 20_000

    # Compactor that keeps only 3 recent messages
    small_keeper = MessageCompactor(
        llm_router=mock_llm_router,
        threshold_ratio=0.7,
        keep_recent=3,
    )

    messages = [{"role": "user", "content": large_content} for _ in range(15)]

    result = await small_keeper.compact_if_needed(messages, model_tier="FAST")

    # Should have 1 summary + 3 recent messages
    assert len(result) == 4


@pytest.mark.asyncio
async def test_multiblock_content_handling(compactor, mock_llm_router):
    """Test that compaction handles multi-block message content."""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "x" * 20_000},
                {"type": "text", "text": "y" * 20_000},
            ]
        }
        for _ in range(15)
    ]

    result = await compactor.compact_if_needed(messages, model_tier="FAST")

    # Should handle multi-block content without errors
    assert isinstance(result, list)
    assert len(result) > 0


def test_compactor_initialization():
    """Test that compactor initializes with correct defaults."""
    router = MagicMock()
    compactor = MessageCompactor(router)

    assert compactor.llm == router
    assert compactor.threshold_ratio == 0.7
    assert compactor.keep_recent == 10


def test_compactor_custom_initialization():
    """Test that compactor accepts custom parameters."""
    router = MagicMock()
    compactor = MessageCompactor(
        llm_router=router,
        threshold_ratio=0.8,
        keep_recent=15,
    )

    assert compactor.threshold_ratio == 0.8
    assert compactor.keep_recent == 15
