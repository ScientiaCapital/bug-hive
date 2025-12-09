"""Tests for token budget management."""

import pytest

from src.llm.token_budget import TokenBudget, MODEL_CONTEXT_LIMITS


def test_estimate_tokens_simple():
    """Test basic token estimation."""
    budget = TokenBudget()
    messages = [{"role": "user", "content": "Hello, how are you?"}]
    tokens = budget.estimate_tokens(messages, model_tier="GENERAL")
    assert tokens > 0
    assert tokens < 100  # Should be small


def test_estimate_tokens_with_tools():
    """Test token estimation with tools."""
    budget = TokenBudget()
    messages = [{"role": "user", "content": "Use a tool"}]
    tools = [{"name": "test_tool", "description": "A test tool"}]

    tokens_without = budget.estimate_tokens(messages, model_tier="GENERAL")
    tokens_with = budget.estimate_tokens(messages, tools=tools, model_tier="GENERAL")

    assert tokens_with > tokens_without


def test_validate_request_ok():
    """Test validation passes for small request."""
    budget = TokenBudget()
    messages = [{"role": "user", "content": "Short message"}]

    valid, reason = budget.validate_request(
        model_tier="ORCHESTRATOR",
        messages=messages,
        max_tokens=4096,
    )
    assert valid is True
    assert reason == "OK"


def test_validate_request_too_large():
    """Test validation fails for oversized request."""
    budget = TokenBudget()
    # Create a very long message
    long_content = "x" * 500_000  # ~125k tokens
    messages = [{"role": "user", "content": long_content}]

    valid, reason = budget.validate_request(
        model_tier="FAST",  # Only 32k limit
        messages=messages,
        max_tokens=4096,
    )
    assert valid is False
    assert "exceeds" in reason.lower()


def test_get_remaining_budget():
    """Test remaining budget calculation."""
    budget = TokenBudget()
    messages = [{"role": "user", "content": "Hello"}]

    remaining = budget.get_remaining_budget("ORCHESTRATOR", messages)
    limit = MODEL_CONTEXT_LIMITS["ORCHESTRATOR"]

    # Should have most of the budget remaining
    assert remaining > limit * 0.8


def test_suggest_max_tokens_normal():
    """Test max_tokens suggestion with plenty of budget."""
    budget = TokenBudget()
    messages = [{"role": "user", "content": "Short message"}]

    suggested = budget.suggest_max_tokens(
        model_tier="ORCHESTRATOR",
        messages=messages,
        desired_output=4096,
    )
    # Should get full desired amount
    assert suggested == 4096


def test_suggest_max_tokens_limited():
    """Test max_tokens suggestion when budget is tight."""
    budget = TokenBudget()
    # Create a message that uses most of the context
    long_content = "x" * 100_000  # ~25k tokens
    messages = [{"role": "user", "content": long_content}]

    suggested = budget.suggest_max_tokens(
        model_tier="FAST",  # Only 32k limit
        messages=messages,
        desired_output=10_000,
    )
    # Should be reduced from desired
    assert suggested < 10_000
    assert suggested >= 256  # Minimum


def test_estimate_tokens_multiblock_content():
    """Test token estimation with multi-block content."""
    budget = TokenBudget()
    messages = [
        {
            "role": "user",
            "content": [
                {"text": "First block"},
                {"text": "Second block"},
            ],
        }
    ]

    tokens = budget.estimate_tokens(messages, model_tier="GENERAL")
    assert tokens > 0


def test_estimate_tokens_different_families():
    """Test that different model families use different char/token ratios."""
    budget = TokenBudget()
    messages = [{"role": "user", "content": "x" * 1000}]

    tokens_anthropic = budget.estimate_tokens(messages, model_tier="ORCHESTRATOR")
    tokens_deepseek = budget.estimate_tokens(messages, model_tier="REASONING")
    tokens_qwen = budget.estimate_tokens(messages, model_tier="GENERAL")

    # Different families should give slightly different estimates
    # DeepSeek should estimate fewer tokens (higher chars/token)
    assert tokens_deepseek < tokens_anthropic


def test_get_context_limit():
    """Test getting context limits for different tiers."""
    budget = TokenBudget()

    assert budget.get_context_limit("ORCHESTRATOR") == 200_000
    assert budget.get_context_limit("REASONING") == 64_000
    assert budget.get_context_limit("CODING") == 128_000
    assert budget.get_context_limit("GENERAL") == 32_000
    assert budget.get_context_limit("FAST") == 32_000
    assert budget.get_context_limit("UNKNOWN") == 32_000  # Default


def test_safety_margin():
    """Test that safety margin affects validation."""
    budget_strict = TokenBudget(safety_margin=0.5)  # Only use 50%
    budget_relaxed = TokenBudget(safety_margin=0.95)  # Use 95%

    long_content = "x" * 50_000  # ~12.5k tokens
    messages = [{"role": "user", "content": long_content}]

    # Both should pass for ORCHESTRATOR (200k limit)
    valid_strict, _ = budget_strict.validate_request(
        model_tier="ORCHESTRATOR",
        messages=messages,
        max_tokens=4096,
    )
    valid_relaxed, _ = budget_relaxed.validate_request(
        model_tier="ORCHESTRATOR",
        messages=messages,
        max_tokens=4096,
    )

    assert valid_strict is True
    assert valid_relaxed is True

    # For FAST tier (32k limit), strict should fail with large output
    valid_strict, _ = budget_strict.validate_request(
        model_tier="FAST",
        messages=messages,
        max_tokens=10_000,
    )
    assert valid_strict is False
