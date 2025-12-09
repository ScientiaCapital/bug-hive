#!/usr/bin/env python3
"""Validation script to check LLM router setup.

Run this script to verify:
1. Dependencies are installed
2. API keys are configured
3. Clients can connect successfully
4. All components work together

Usage:
    python src/llm/validate_setup.py
"""

import asyncio
import os
import sys


def check_imports() -> tuple[bool, str]:
    """Check if all required packages are installed."""
    print("Checking dependencies...")

    try:
        import anthropic
        print(f"  ✓ anthropic (v{anthropic.__version__})")
    except ImportError:
        return False, "anthropic package not installed. Run: pip install anthropic"

    try:
        import httpx
        print(f"  ✓ httpx (v{httpx.__version__})")
    except ImportError:
        return False, "httpx package not installed. Run: pip install httpx"

    try:
        import tenacity
        print(f"  ✓ tenacity (v{tenacity.__version__})")
    except ImportError:
        return False, "tenacity package not installed. Run: pip install tenacity"

    return True, "All dependencies installed"


def check_api_keys() -> tuple[bool, str]:
    """Check if API keys are configured."""
    print("\nChecking API keys...")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return False, "ANTHROPIC_API_KEY not set. Set it with: export ANTHROPIC_API_KEY='sk-ant-...'"

    if not anthropic_key.startswith("sk-ant-"):
        return False, "ANTHROPIC_API_KEY doesn't look valid (should start with 'sk-ant-')"

    print(f"  ✓ ANTHROPIC_API_KEY ({anthropic_key[:10]}...)")

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        return False, "OPENROUTER_API_KEY not set. Set it with: export OPENROUTER_API_KEY='sk-or-...'"

    if not openrouter_key.startswith("sk-or-"):
        return False, "OPENROUTER_API_KEY doesn't look valid (should start with 'sk-or-')"

    print(f"  ✓ OPENROUTER_API_KEY ({openrouter_key[:10]}...)")

    return True, "API keys configured"


def check_module_imports() -> tuple[bool, str]:
    """Check if LLM module components can be imported."""
    print("\nChecking LLM module imports...")

    try:
        from router import TASK_MODEL_MAP, LLMRouter, ModelTier
        print("  ✓ router (LLMRouter, ModelTier, TASK_MODEL_MAP)")
    except ImportError as e:
        return False, f"Failed to import router: {e}"

    try:
        from anthropic import AnthropicClient
        print("  ✓ anthropic (AnthropicClient)")
    except ImportError as e:
        return False, f"Failed to import AnthropicClient: {e}"

    try:
        from openrouter import OpenRouterClient
        print("  ✓ openrouter (OpenRouterClient)")
    except ImportError as e:
        return False, f"Failed to import OpenRouterClient: {e}"

    try:
        from cost_tracker import CostTracker
        print("  ✓ cost_tracker (CostTracker)")
    except ImportError as e:
        return False, f"Failed to import CostTracker: {e}"

    return True, "All modules import successfully"


async def check_anthropic_connection() -> tuple[bool, str]:
    """Check if Anthropic API is accessible."""
    print("\nChecking Anthropic API connection...")

    try:
        from anthropic import AnthropicClient

        async with AnthropicClient() as client:
            # Try a minimal API call
            response = await client.create_message(
                model="anthropic/claude-opus-4-5-20250514",
                messages=[
                    {"role": "user", "content": "Hi"}
                ],
                max_tokens=10,
            )

            print("  ✓ Connection successful")
            print(f"  ✓ Response: {response['content'][:50]}...")
            print(f"  ✓ Usage: {response['usage']['total_tokens']} tokens")

            return True, "Anthropic API accessible"

    except Exception as e:
        return False, f"Anthropic API connection failed: {e}"


async def check_openrouter_connection() -> tuple[bool, str]:
    """Check if OpenRouter API is accessible."""
    print("\nChecking OpenRouter API connection...")

    try:
        from openrouter import OpenRouterClient

        async with OpenRouterClient() as client:
            # Try a minimal API call
            response = await client.create_completion(
                model="qwen/qwen-2.5-32b-instruct",  # Fast, cheap model
                messages=[
                    {"role": "user", "content": "Hi"}
                ],
                max_tokens=10,
            )

            print("  ✓ Connection successful")
            print(f"  ✓ Response: {response['content'][:50]}...")
            print(f"  ✓ Usage: {response['usage']['total_tokens']} tokens")

            return True, "OpenRouter API accessible"

    except Exception as e:
        return False, f"OpenRouter API connection failed: {e}"


async def check_router() -> tuple[bool, str]:
    """Check if LLMRouter works end-to-end."""
    print("\nChecking LLMRouter integration...")

    try:
        from anthropic import AnthropicClient
        from cost_tracker import CostTracker
        from openrouter import OpenRouterClient
        from router import LLMRouter

        # Initialize components
        anthropic = AnthropicClient()
        openrouter = OpenRouterClient()
        tracker = CostTracker()

        router = LLMRouter(
            anthropic_client=anthropic,
            openrouter_client=openrouter,
            cost_tracker=tracker,
        )

        try:
            # Test routing to fast model
            response = await router.route(
                task="format_ticket",
                messages=[
                    {"role": "user", "content": "Test"}
                ],
                session_id="validation_test",
                max_tokens=10,
            )

            print("  ✓ Router works")
            print(f"  ✓ Task routed to: {response['model_tier']}")
            print(f"  ✓ Cost tracked: ${response['cost']:.6f}")

            # Check cost tracking
            session_cost = tracker.get_session_cost("validation_test")
            print(f"  ✓ Session cost: ${session_cost:.6f}")

            return True, "LLMRouter fully functional"

        finally:
            await anthropic.close()
            await openrouter.close()

    except Exception as e:
        return False, f"LLMRouter test failed: {e}"


async def main():
    """Run all validation checks."""
    print("=" * 60)
    print("BugHive LLM Router Setup Validation")
    print("=" * 60)

    checks = [
        ("Dependencies", check_imports, False),
        ("API Keys", check_api_keys, False),
        ("Module Imports", check_module_imports, False),
        ("Anthropic Connection", check_anthropic_connection, True),
        ("OpenRouter Connection", check_openrouter_connection, True),
        ("Router Integration", check_router, True),
    ]

    results = []
    all_passed = True

    for name, check_func, is_async in checks:
        try:
            if is_async:
                success, message = await check_func()
            else:
                success, message = check_func()

            results.append((name, success, message))

            if not success:
                all_passed = False
                print(f"\n❌ {name} FAILED: {message}")

        except Exception as e:
            results.append((name, False, str(e)))
            all_passed = False
            print(f"\n❌ {name} ERROR: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)

    for name, success, message in results:
        status = "✓" if success else "✗"
        print(f"{status} {name}: {message}")

    print("=" * 60)

    if all_passed:
        print("✅ All checks passed! LLM router is ready to use.")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
