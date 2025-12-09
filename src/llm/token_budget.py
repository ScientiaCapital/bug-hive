"""Token budget management for BugHive LLM requests.

NO OpenAI/tiktoken dependencies - uses character-based estimation.
"""

import logging

logger = logging.getLogger(__name__)


# Import ModelTier from router to avoid circular imports
# We'll reference it by string initially
MODEL_CONTEXT_LIMITS = {
    "ORCHESTRATOR": 200_000,  # Claude Opus
    "REASONING": 64_000,      # DeepSeek-V3
    "CODING": 128_000,        # DeepSeek-Coder
    "GENERAL": 32_000,        # Qwen-72B
    "FAST": 32_000,           # Qwen-32B
}

# Approximate characters per token by model family
CHARS_PER_TOKEN = {
    "anthropic": 3.5,    # Claude models
    "deepseek": 3.8,     # DeepSeek models
    "qwen": 3.5,         # Qwen models
    "cerebras": 4.0,     # Cerebras models
    "default": 4.0,      # Conservative default
}

# Map model tier to family
MODEL_TIER_TO_FAMILY = {
    "ORCHESTRATOR": "anthropic",
    "REASONING": "deepseek",
    "CODING": "deepseek",
    "GENERAL": "qwen",
    "FAST": "qwen",
}


class TokenBudget:
    """Manages token budgets for LLM requests without OpenAI dependencies."""

    def __init__(self, safety_margin: float = 0.9):
        """
        Initialize token budget manager.

        Args:
            safety_margin: Fraction of context limit to use (0.9 = 90%)
        """
        self.safety_margin = safety_margin

    def estimate_tokens(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model_tier: str = "GENERAL",
    ) -> int:
        """
        Estimate token count using character-based heuristic.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional tool definitions
            model_tier: Model tier name for family detection

        Returns:
            Estimated token count
        """
        family = MODEL_TIER_TO_FAMILY.get(model_tier, "default")
        chars_per_token = CHARS_PER_TOKEN.get(family, 4.0)

        # Count message content
        total_chars = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str):
                total_chars += len(content)
            elif isinstance(content, list):
                # Handle content blocks
                for block in content:
                    if isinstance(block, dict):
                        total_chars += len(str(block.get("text", "")))
                    else:
                        total_chars += len(str(block))

            # Add overhead for role, etc.
            total_chars += 20  # Approximate overhead per message

        # Add tool definitions if present
        if tools:
            total_chars += len(str(tools))

        estimated = int(total_chars / chars_per_token)
        logger.debug(
            f"Estimated {estimated} tokens for {len(messages)} messages "
            f"(family={family}, chars={total_chars})"
        )
        return estimated

    def get_context_limit(self, model_tier: str) -> int:
        """Get context window limit for model tier."""
        return MODEL_CONTEXT_LIMITS.get(model_tier, 32_000)

    def validate_request(
        self,
        model_tier: str,
        messages: list[dict],
        max_tokens: int,
        tools: list[dict] | None = None,
    ) -> tuple[bool, str]:
        """
        Validate that request fits in context window.

        Args:
            model_tier: Model tier name
            messages: Messages to send
            max_tokens: Requested max output tokens
            tools: Optional tool definitions

        Returns:
            Tuple of (is_valid, reason)
        """
        context_limit = self.get_context_limit(model_tier)
        safe_limit = int(context_limit * self.safety_margin)

        estimated_input = self.estimate_tokens(messages, tools, model_tier)
        total_needed = estimated_input + max_tokens

        if total_needed > safe_limit:
            return (
                False,
                f"Request too large: {estimated_input} input + {max_tokens} output = "
                f"{total_needed} tokens exceeds safe limit of {safe_limit} "
                f"(context: {context_limit})"
            )

        return (True, "OK")

    def get_remaining_budget(
        self,
        model_tier: str,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> int:
        """
        Get tokens available for response.

        Args:
            model_tier: Model tier name
            messages: Current messages
            tools: Optional tool definitions

        Returns:
            Available tokens for response
        """
        context_limit = self.get_context_limit(model_tier)
        safe_limit = int(context_limit * self.safety_margin)
        estimated_input = self.estimate_tokens(messages, tools, model_tier)

        remaining = max(0, safe_limit - estimated_input)
        logger.debug(
            f"Remaining budget: {remaining} tokens "
            f"(limit={safe_limit}, used={estimated_input})"
        )
        return remaining

    def suggest_max_tokens(
        self,
        model_tier: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        desired_output: int = 4096,
    ) -> int:
        """
        Suggest appropriate max_tokens based on remaining budget.

        Args:
            model_tier: Model tier name
            messages: Current messages
            tools: Optional tool definitions
            desired_output: Preferred output tokens

        Returns:
            Suggested max_tokens value
        """
        remaining = self.get_remaining_budget(model_tier, messages, tools)
        suggested = min(desired_output, remaining)

        if suggested < desired_output:
            logger.warning(
                f"Reduced max_tokens from {desired_output} to {suggested} "
                f"due to context budget"
            )

        return max(256, suggested)  # Minimum 256 tokens for response
