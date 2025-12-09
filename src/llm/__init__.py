"""LLM routing and client infrastructure for BugHive.

This module provides multi-model LLM support with intelligent routing:
- Claude Opus 4.5 for high-stakes orchestration
- DeepSeek-V3 for reasoning and analysis
- DeepSeek-Coder-V2 for code-related tasks
- Qwen 2.5 models for general and fast tasks

Usage:
    from llm import LLMRouter, AnthropicClient, OpenRouterClient, CostTracker

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

    # Route a task
    response = await router.route(
        task="analyze_page",
        messages=[{"role": "user", "content": "Analyze this page..."}],
        session_id="session_123",
    )

    # Check costs
    print(tracker.get_cost_summary(session_id="session_123"))
"""

from .anthropic import AnthropicClient, create_message
from .compactor import MessageCompactor
from .cost_tracker import MODEL_COSTS, CostTracker, SessionStats, UsageRecord
from .openrouter import OpenRouterClient, create_completion
from .router import TASK_MODEL_MAP, LLMRouter, ModelTier
from .token_budget import TokenBudget

__all__ = [
    # Router
    "LLMRouter",
    "ModelTier",
    "TASK_MODEL_MAP",
    # Clients
    "AnthropicClient",
    "OpenRouterClient",
    # Convenience functions
    "create_message",
    "create_completion",
    # Cost tracking
    "CostTracker",
    "MODEL_COSTS",
    "UsageRecord",
    "SessionStats",
    # Token budget
    "TokenBudget",
    # Message compaction
    "MessageCompactor",
]

__version__ = "0.1.0"
