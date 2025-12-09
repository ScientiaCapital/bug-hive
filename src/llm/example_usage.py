"""Example usage of BugHive LLM routing system.

This demonstrates how to use the multi-model LLM infrastructure with
intelligent routing and cost tracking.

Before running:
    1. Set environment variables:
       export ANTHROPIC_API_KEY="your-key"
       export OPENROUTER_API_KEY="your-key"

    2. Install dependencies:
       pip install -r src/llm/requirements.txt
"""

import asyncio
import logging
from datetime import datetime

from anthropic import AnthropicClient
from cost_tracker import CostTracker
from openrouter import OpenRouterClient
from router import LLMRouter, ModelTier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_basic_routing():
    """Example: Basic task routing to different models."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Task Routing")
    print("=" * 60)

    # Initialize clients
    anthropic = AnthropicClient()
    openrouter = OpenRouterClient()
    tracker = CostTracker()

    # Create router
    router = LLMRouter(
        anthropic_client=anthropic,
        openrouter_client=openrouter,
        cost_tracker=tracker,
    )

    session_id = f"example_{datetime.now().timestamp()}"

    try:
        # Example 1: Fast task - Qwen-32B
        print("\n1. Fast task (format_ticket) -> Qwen-32B")
        response = await router.route(
            task="format_ticket",
            messages=[
                {
                    "role": "user",
                    "content": "Format this as a bug ticket: The login button doesn't work on mobile"
                }
            ],
            session_id=session_id,
            max_tokens=500,
        )
        print(f"Model used: {response['model_tier']}")
        print(f"Response: {response['content'][:100]}...")
        print(f"Cost: ${response.get('cost', 0):.6f}")

        # Example 2: Code analysis - DeepSeek-Coder
        print("\n2. Code task (analyze_stack_trace) -> DeepSeek-Coder")
        response = await router.route(
            task="analyze_stack_trace",
            messages=[
                {
                    "role": "user",
                    "content": "Analyze this error: TypeError: Cannot read property 'value' of null at line 42"
                }
            ],
            session_id=session_id,
            max_tokens=1000,
        )
        print(f"Model used: {response['model_tier']}")
        print(f"Response: {response['content'][:100]}...")
        print(f"Cost: ${response.get('cost', 0):.6f}")

        # Example 3: Reasoning - DeepSeek-V3
        print("\n3. Analysis task (classify_bug) -> DeepSeek-V3")
        response = await router.route(
            task="classify_bug",
            messages=[
                {
                    "role": "user",
                    "content": "Classify this bug: Users can't checkout when cart has >10 items"
                }
            ],
            session_id=session_id,
            max_tokens=1000,
        )
        print(f"Model used: {response['model_tier']}")
        print(f"Response: {response['content'][:100]}...")
        print(f"Cost: ${response.get('cost', 0):.6f}")

        # Example 4: Orchestration - Claude Opus
        print("\n4. High-stakes task (plan_crawl_strategy) -> Claude Opus")
        response = await router.route(
            task="plan_crawl_strategy",
            messages=[
                {
                    "role": "user",
                    "content": "Plan a crawl strategy for an e-commerce site with authentication"
                }
            ],
            session_id=session_id,
            max_tokens=2000,
        )
        print(f"Model used: {response['model_tier']}")
        print(f"Response: {response['content'][:100]}...")
        print(f"Cost: ${response.get('cost', 0):.6f}")

        # Print session summary
        print("\n" + "-" * 60)
        print(tracker.get_cost_summary(session_id=session_id))

    finally:
        await anthropic.close()
        await openrouter.close()


async def example_tool_use():
    """Example: Using Claude with tool calling."""
    print("\n" + "=" * 60)
    print("Example 2: Tool Use with Claude Opus")
    print("=" * 60)

    anthropic = AnthropicClient()

    # Define a simple tool
    tools = [
        {
            "name": "take_screenshot",
            "description": "Take a screenshot of the current page",
            "input_schema": {
                "type": "object",
                "properties": {
                    "selector": {
                        "type": "string",
                        "description": "CSS selector to screenshot (optional)"
                    }
                },
                "required": []
            }
        }
    ]

    try:
        response = await anthropic.create_message(
            model="anthropic/claude-opus-4-5-20250514",
            messages=[
                {
                    "role": "user",
                    "content": "Take a screenshot of the login form"
                }
            ],
            tools=tools,
            max_tokens=500,
        )

        print(f"Response: {response['content']}")
        if response.get('tool_calls'):
            print(f"Tool calls: {response['tool_calls']}")

    finally:
        await anthropic.close()


async def example_fallback():
    """Example: Using fallback routing."""
    print("\n" + "=" * 60)
    print("Example 3: Fallback Routing")
    print("=" * 60)

    anthropic = AnthropicClient()
    openrouter = OpenRouterClient()
    tracker = CostTracker()

    router = LLMRouter(
        anthropic_client=anthropic,
        openrouter_client=openrouter,
        cost_tracker=tracker,
    )

    try:
        # This will try the primary model and fall back to GENERAL if it fails
        response = await router.route_with_fallback(
            task="analyze_page",
            messages=[
                {
                    "role": "user",
                    "content": "Analyze this page structure"
                }
            ],
            fallback_tier=ModelTier.FAST,  # Fall back to fast tier
            max_tokens=500,
        )

        print(f"Model used: {response.get('model_tier')}")
        if response.get('fallback_used'):
            print("⚠️  Fallback was used!")

    finally:
        await anthropic.close()
        await openrouter.close()


async def example_cost_tracking():
    """Example: Cost tracking and analysis."""
    print("\n" + "=" * 60)
    print("Example 4: Cost Tracking")
    print("=" * 60)

    tracker = CostTracker()

    # Simulate some API calls
    tracker.add(
        model=ModelTier.ORCHESTRATOR,
        input_tokens=1000,
        output_tokens=500,
        session_id="session_1",
        task="plan_crawl_strategy",
    )

    tracker.add(
        model=ModelTier.REASONING,
        input_tokens=2000,
        output_tokens=1000,
        session_id="session_1",
        task="analyze_page",
    )

    tracker.add(
        model=ModelTier.FAST,
        input_tokens=500,
        output_tokens=200,
        session_id="session_1",
        task="format_ticket",
    )

    # Get session stats
    print("\nSession Statistics:")
    stats = tracker.get_session_stats("session_1")
    if stats:
        print(f"  Total Cost: ${stats.total_cost:.4f}")
        print(f"  Total Requests: {stats.total_requests}")
        print(f"  Input Tokens: {stats.total_input_tokens:,}")
        print(f"  Output Tokens: {stats.total_output_tokens:,}")

    # Get breakdown
    print("\nCost Breakdown by Model:")
    breakdown = tracker.get_breakdown("session_1")
    for model, data in breakdown.items():
        print(f"  {model}: ${data['cost']:.4f} ({data['requests']} requests)")

    # Get full summary
    print("\n" + tracker.get_cost_summary(session_id="session_1"))


async def main():
    """Run all examples."""
    print("\n🧿 BugHive LLM Routing Examples")
    print("=" * 60)

    # Run examples
    await example_basic_routing()
    # await example_tool_use()  # Uncomment if you want to test tool use
    # await example_fallback()  # Uncomment if you want to test fallback
    await example_cost_tracking()

    print("\n✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
