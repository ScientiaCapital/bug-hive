"""Message compaction for BugHive LLM context management."""

import logging
from .router import LLMRouter

logger = logging.getLogger(__name__)


class MessageCompactor:
    """Compacts message history when approaching context limits."""

    def __init__(
        self,
        llm_router: LLMRouter,
        threshold_ratio: float = 0.7,
        keep_recent: int = 10,
    ):
        """
        Initialize message compactor.

        Args:
            llm_router: LLMRouter for summarization
            threshold_ratio: Trigger compaction at this % of context limit (0.7 = 70%)
            keep_recent: Number of recent messages to keep uncompacted
        """
        self.llm = llm_router
        self.threshold_ratio = threshold_ratio
        self.keep_recent = keep_recent

    async def compact_if_needed(
        self,
        messages: list[dict],
        model_tier: str = "GENERAL",
    ) -> list[dict]:
        """
        Compact messages if approaching context limit.

        Args:
            messages: Current message list
            model_tier: Target model tier for context limit lookup

        Returns:
            Compacted message list (or original if no compaction needed)
        """
        # Check if compaction needed using token budget
        from .token_budget import TokenBudget, MODEL_CONTEXT_LIMITS

        budget = TokenBudget()
        estimated_tokens = budget.estimate_tokens(messages, model_tier=model_tier)
        context_limit = MODEL_CONTEXT_LIMITS.get(model_tier, 32_000)
        threshold = int(context_limit * self.threshold_ratio)

        if estimated_tokens < threshold:
            logger.debug(
                f"No compaction needed: {estimated_tokens} < {threshold} tokens"
            )
            return messages

        logger.info(
            f"Compacting messages: {estimated_tokens} tokens exceeds {threshold} threshold"
        )

        # Keep recent messages, summarize the rest
        if len(messages) <= self.keep_recent:
            return messages

        old_messages = messages[:-self.keep_recent]
        recent_messages = messages[-self.keep_recent:]

        # Summarize old messages
        summary = await self._summarize(old_messages)

        # Return summary + recent messages
        compacted = [
            {"role": "system", "content": f"Previous context summary:\n{summary}"}
        ] + recent_messages

        new_tokens = budget.estimate_tokens(compacted, model_tier=model_tier)
        logger.info(
            f"Compacted {len(messages)} messages to {len(compacted)}: "
            f"{estimated_tokens} → {new_tokens} tokens"
        )

        return compacted

    async def _summarize(self, messages: list[dict]) -> str:
        """Summarize a list of messages."""
        # Format messages for summarization
        text = "\n".join([
            f"{m.get('role', 'unknown')}: {m.get('content', '')[:500]}"
            for m in messages
        ])

        summary_prompt = f"""Summarize the following conversation context concisely.
Keep key information: URLs visited, bugs found, decisions made.
Omit redundant details.

Conversation:
{text}

Summary (be concise):"""

        response = await self.llm.route(
            task="summarize_session",  # Uses FAST tier (Qwen-32B)
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=1024,
            temperature=0.3,
        )

        return response.get("content", "Context summary unavailable.")
