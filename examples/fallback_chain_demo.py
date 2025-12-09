#!/usr/bin/env python3
"""
Demo script for Multi-Level Fallback Chain in LLM Router.

This script demonstrates how to use the fallback chain feature for robust
LLM request handling with automatic retry and tier fallback.

Run with:
    python examples/fallback_chain_demo.py
"""

import asyncio
from unittest.mock import AsyncMock, Mock

from src.llm import AllModelsFailedError, LLMRouter, ModelTier


def create_mock_router():
    """Create a mock router for demonstration."""
    mock_anthropic = Mock()
    mock_anthropic.create_message = AsyncMock()

    mock_openrouter = Mock()
    mock_openrouter.create_completion = AsyncMock()

    mock_tracker = Mock()
    mock_tracker.add = Mock(return_value=0.05)

    return LLMRouter(
        anthropic_client=mock_anthropic,
        openrouter_client=mock_openrouter,
        cost_tracker=mock_tracker,
    )


async def demo_primary_success():
    """Demo 1: Primary model succeeds (no fallback needed)."""
    print("\n" + "=" * 80)
    print("DEMO 1: Primary Model Success (No Fallback)")
    print("=" * 80)

    router = create_mock_router()

    # Mock successful response
    router.openrouter_client.create_completion.return_value = {
        "content": "Analysis complete",
        "usage": {"input_tokens": 100, "output_tokens": 200},
    }

    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=[{"role": "user", "content": "Analyze this page"}],
    )

    print(f"\n✅ Primary model succeeded!")
    print(f"   Model tier: {response['model_tier']}")
    print(f"   Fallback tier: {response['fallback_tier']}")
    print(f"   Attempt: {response['attempt']}")
    print(f"   Chain used: {response['fallback_chain_used']}")


async def demo_fallback_to_second_tier():
    """Demo 2: Primary fails, fallback to second tier."""
    print("\n" + "=" * 80)
    print("DEMO 2: Fallback to Second Tier")
    print("=" * 80)

    router = create_mock_router()

    # Primary tier fails twice, second tier succeeds
    router.openrouter_client.create_completion.side_effect = [
        Exception("REASONING tier timeout"),
        Exception("REASONING tier timeout"),
        {
            "content": "Analysis from GENERAL tier",
            "usage": {"input_tokens": 100, "output_tokens": 200},
        },
    ]

    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=[{"role": "user", "content": "Analyze this page"}],
        max_retries_per_tier=2,
    )

    print(f"\n⚠️  Primary model failed, fell back to: {response['fallback_tier']}")
    print(f"   Original task tier: REASONING")
    print(f"   Successful tier: {response['fallback_tier']}")
    print(f"   Attempt: {response['attempt']}")
    print(f"   Full chain attempted: {response['fallback_chain_used']}")


async def demo_all_models_fail():
    """Demo 3: All models in chain fail."""
    print("\n" + "=" * 80)
    print("DEMO 3: All Models Fail (Error Handling)")
    print("=" * 80)

    router = create_mock_router()

    # All tiers fail
    router.openrouter_client.create_completion.side_effect = Exception(
        "Service unavailable"
    )

    try:
        await router.route_with_fallback_chain(
            task="analyze_page",
            messages=[{"role": "user", "content": "Analyze this page"}],
            max_retries_per_tier=2,
        )
    except AllModelsFailedError as e:
        print(f"\n❌ All models failed!")
        print(f"\nError summary:")
        print(f"{str(e)}\n")
        print(f"Detailed errors:")
        for error in e.errors:
            print(f"  - {error['tier']} attempt {error['attempt']}: {error['error']}")


async def demo_custom_retry_counts():
    """Demo 4: Custom retry counts per tier."""
    print("\n" + "=" * 80)
    print("DEMO 4: Custom Retry Counts")
    print("=" * 80)

    router = create_mock_router()

    # Fail on first 4 attempts, succeed on 5th
    responses = [Exception("Error")] * 4 + [
        {
            "content": "Success on 5th attempt",
            "usage": {"input_tokens": 100, "output_tokens": 200},
        }
    ]
    router.openrouter_client.create_completion.side_effect = responses

    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=[{"role": "user", "content": "Analyze this page"}],
        max_retries_per_tier=5,  # More aggressive retries
    )

    print(f"\n✅ Succeeded after {response['attempt']} attempts")
    print(f"   Tier: {response['model_tier']}")
    print(f"   Chain: {response['fallback_chain_used']}")


async def demo_different_task_chains():
    """Demo 5: Different tasks use different fallback chains."""
    print("\n" + "=" * 80)
    print("DEMO 5: Different Fallback Chains for Different Tasks")
    print("=" * 80)

    from src.llm.router import FALLBACK_CHAIN

    print("\nFallback chains by task type:\n")

    # Orchestration task
    orchestrator_chain = [ModelTier.ORCHESTRATOR] + FALLBACK_CHAIN[
        ModelTier.ORCHESTRATOR
    ]
    print(f"📋 Orchestration tasks (validate_critical_bug):")
    print(f"   Chain: {[t.name for t in orchestrator_chain]}")

    # Coding task
    coding_chain = [ModelTier.CODING] + FALLBACK_CHAIN[ModelTier.CODING]
    print(f"\n💻 Coding tasks (generate_edge_cases):")
    print(f"   Chain: {[t.name for t in coding_chain]}")

    # Analysis task
    reasoning_chain = [ModelTier.REASONING] + FALLBACK_CHAIN[ModelTier.REASONING]
    print(f"\n🔍 Analysis tasks (analyze_page):")
    print(f"   Chain: {[t.name for t in reasoning_chain]}")

    # General task
    general_chain = [ModelTier.GENERAL] + FALLBACK_CHAIN[ModelTier.GENERAL]
    print(f"\n📝 General tasks (extract_navigation):")
    print(f"   Chain: {[t.name for t in general_chain]}")

    # Fast task
    fast_chain = [ModelTier.FAST] + FALLBACK_CHAIN[ModelTier.FAST]
    print(f"\n⚡ Fast tasks (format_ticket):")
    print(f"   Chain: {[t.name for t in fast_chain]}")
    print(f"   Note: No fallback - fastest tier already")


async def demo_backward_compatibility():
    """Demo 6: Backward compatibility with old route_with_fallback()."""
    print("\n" + "=" * 80)
    print("DEMO 6: Backward Compatibility")
    print("=" * 80)

    router = create_mock_router()

    # Mock response
    router.openrouter_client.create_completion.return_value = {
        "content": "Response",
        "usage": {"input_tokens": 100, "output_tokens": 200},
    }

    # Old style: with explicit fallback tier (single-level fallback)
    print("\n🔄 Old style (explicit fallback tier):")
    response_old = await router.route_with_fallback(
        task="analyze_page",
        messages=[{"role": "user", "content": "Test"}],
        fallback_tier=ModelTier.FAST,  # Explicit single fallback
    )
    print(f"   Uses single-level fallback: {response_old.get('fallback_used', False)}")

    # New style: without fallback tier (multi-level chain)
    print("\n✨ New style (automatic chain):")
    response_new = await router.route_with_fallback(
        task="analyze_page",
        messages=[{"role": "user", "content": "Test"}],
        # No fallback_tier - uses chain automatically
    )
    print(f"   Uses fallback chain: {'fallback_chain_used' in response_new}")
    print(f"   Chain: {response_new.get('fallback_chain_used', [])}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("MULTI-LEVEL FALLBACK CHAIN - DEMONSTRATION")
    print("=" * 80)
    print("\nThis demo shows the new multi-level fallback chain feature.")
    print("All examples use mocked LLM clients for demonstration purposes.")

    await demo_primary_success()
    await demo_fallback_to_second_tier()
    await demo_all_models_fail()
    await demo_custom_retry_counts()
    await demo_different_task_chains()
    await demo_backward_compatibility()

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\n📚 For more information, see:")
    print("   - Documentation: docs/llm-fallback-chain.md")
    print("   - Tests: tests/test_fallback_chain.py")
    print("   - Implementation: src/llm/router.py")
    print()


if __name__ == "__main__":
    asyncio.run(main())
