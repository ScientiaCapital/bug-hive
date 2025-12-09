"""LLM Router for BugHive - Routes tasks to optimal models for cost efficiency."""

import logging
from enum import Enum

from .token_budget import TokenBudget

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tiers with their OpenRouter/Anthropic identifiers."""
    ORCHESTRATOR = "anthropic/claude-opus-4-5-20250514"
    REASONING = "deepseek/deepseek-chat"
    CODING = "deepseek/deepseek-coder"
    GENERAL = "qwen/qwen-2.5-72b-instruct"
    FAST = "qwen/qwen-2.5-32b-instruct"


# Task-to-model mapping for intelligent routing
TASK_MODEL_MAP = {
    # High-stakes decisions → Opus
    "plan_crawl_strategy": ModelTier.ORCHESTRATOR,
    "validate_critical_bug": ModelTier.ORCHESTRATOR,
    "quality_gate": ModelTier.ORCHESTRATOR,
    "orchestrate_session": ModelTier.ORCHESTRATOR,

    # Analysis and reasoning → DeepSeek-V3
    "analyze_page": ModelTier.REASONING,
    "classify_bug": ModelTier.REASONING,
    "deduplicate_bugs": ModelTier.REASONING,
    "evaluate_severity": ModelTier.REASONING,
    "analyze_interaction": ModelTier.REASONING,

    # Code-related → DeepSeek-Coder
    "generate_edge_cases": ModelTier.CODING,
    "propose_fix": ModelTier.CODING,
    "analyze_stack_trace": ModelTier.CODING,
    "review_code": ModelTier.CODING,
    "generate_test": ModelTier.CODING,

    # General tasks → Qwen-72B
    "extract_navigation": ModelTier.GENERAL,
    "parse_console_logs": ModelTier.GENERAL,
    "identify_elements": ModelTier.GENERAL,
    "extract_forms": ModelTier.GENERAL,

    # Fast tasks → Qwen-32B
    "format_ticket": ModelTier.FAST,
    "summarize_session": ModelTier.FAST,
    "generate_title": ModelTier.FAST,
    "categorize_simple": ModelTier.FAST,
}


class LLMRouter:
    """Routes LLM requests to optimal model based on task type."""

    def __init__(
        self,
        anthropic_client,
        openrouter_client,
        cost_tracker,
        safety_margin: float = 0.9,
    ):
        """
        Initialize router with LLM clients.

        Args:
            anthropic_client: AnthropicClient instance for Claude models
            openrouter_client: OpenRouterClient instance for DeepSeek/Qwen models
            cost_tracker: CostTracker instance for usage tracking
            safety_margin: Token budget safety margin (default 0.9 = 90%)
        """
        self.anthropic_client = anthropic_client
        self.openrouter_client = openrouter_client
        self.cost_tracker = cost_tracker
        self.token_budget = TokenBudget(safety_margin=safety_margin)

    def get_model_for_task(self, task: str) -> ModelTier:
        """
        Determine the optimal model tier for a given task.

        Args:
            task: Task identifier (e.g., 'analyze_page', 'format_ticket')

        Returns:
            ModelTier enum value for the task
        """
        model = TASK_MODEL_MAP.get(task)
        if model is None:
            logger.warning(
                f"Unknown task '{task}', defaulting to GENERAL tier. "
                f"Consider adding to TASK_MODEL_MAP."
            )
            return ModelTier.GENERAL
        return model

    async def route(
        self,
        task: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        session_id: str | None = None,
        tools: list[dict] | None = None,
        **kwargs,
    ) -> dict:
        """
        Route request to appropriate model based on task type.

        Args:
            task: Task identifier to determine model selection
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            session_id: Optional session ID for cost tracking
            tools: Optional tool definitions for function calling
            **kwargs: Additional model-specific parameters

        Returns:
            Response dict with 'content', 'model', 'usage', and 'cost'

        Raises:
            ValueError: If messages format is invalid
            Exception: If API call fails after retries
        """
        if not messages or not isinstance(messages, list):
            raise ValueError("messages must be a non-empty list")

        # Determine which model to use
        model_tier = self.get_model_for_task(task)

        # Validate token budget before routing
        is_valid, reason = self.token_budget.validate_request(
            model_tier=model_tier.name,
            messages=messages,
            max_tokens=max_tokens,
            tools=tools,
        )

        if not is_valid:
            # Try to suggest a better max_tokens value
            suggested = self.token_budget.suggest_max_tokens(
                model_tier=model_tier.name,
                messages=messages,
                tools=tools,
                desired_output=max_tokens,
            )
            logger.warning(
                f"Token budget validation failed: {reason}. "
                f"Suggested max_tokens: {suggested}"
            )
            # Adjust max_tokens automatically
            max_tokens = suggested

        # Log usage estimate
        estimated_input = self.token_budget.estimate_tokens(
            messages=messages,
            tools=tools,
            model_tier=model_tier.name,
        )
        logger.info(
            f"Routing task '{task}' to {model_tier.name} "
            f"(model: {model_tier.value}, est. input: {estimated_input} tokens, "
            f"max_output: {max_tokens} tokens)"
        )

        # Route to appropriate client
        if model_tier == ModelTier.ORCHESTRATOR:
            response = await self.anthropic_client.create_message(
                model=model_tier.value,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
                **kwargs,
            )
        else:
            response = await self.openrouter_client.create_completion(
                model=model_tier.value,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

        # Track costs
        if session_id and "usage" in response:
            cost = self.cost_tracker.add(
                model=model_tier,
                input_tokens=response["usage"].get("input_tokens", 0),
                output_tokens=response["usage"].get("output_tokens", 0),
                session_id=session_id,
            )
            response["cost"] = cost

        response["model"] = model_tier.value
        response["model_tier"] = model_tier.name

        return response

    async def route_with_fallback(
        self,
        task: str,
        messages: list[dict],
        fallback_tier: ModelTier | None = None,
        **kwargs,
    ) -> dict:
        """
        Route with automatic fallback on failure.

        Useful for production scenarios where you want to guarantee a response.
        Falls back to GENERAL tier by default if primary model fails.

        Args:
            task: Task identifier
            messages: Message list
            fallback_tier: ModelTier to use on failure (defaults to GENERAL)
            **kwargs: Additional parameters for route()

        Returns:
            Response dict from successful call
        """
        try:
            return await self.route(task, messages, **kwargs)
        except Exception as e:
            logger.error(f"Primary model failed for task '{task}': {e}")

            if fallback_tier is None:
                fallback_tier = ModelTier.GENERAL

            logger.info(f"Falling back to {fallback_tier.name}")

            # Use direct model call instead of mutating global TASK_MODEL_MAP (thread-safe)
            response = await self._route_with_model(
                fallback_tier, messages, **kwargs
            )
            response["fallback_used"] = True
            response["original_task"] = task
            return response

    async def _route_with_model(
        self,
        model_tier: ModelTier,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        session_id: str | None = None,
        **kwargs,
    ) -> dict:
        """
        Route directly to a specific model tier (bypasses task mapping).

        Args:
            model_tier: ModelTier to use
            messages: Message list
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            session_id: Optional session ID for cost tracking
            **kwargs: Additional parameters

        Returns:
            Response dict
        """
        logger.info(f"Direct routing to {model_tier.name} (model: {model_tier.value})")

        if model_tier == ModelTier.ORCHESTRATOR:
            response = await self.anthropic_client.create_message(
                model=model_tier.value,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )
        else:
            response = await self.openrouter_client.create_completion(
                model=model_tier.value,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs,
            )

        # Track costs
        if session_id and "usage" in response:
            cost = self.cost_tracker.add(
                model=model_tier,
                input_tokens=response["usage"].get("input_tokens", 0),
                output_tokens=response["usage"].get("output_tokens", 0),
                session_id=session_id,
            )
            response["cost"] = cost

        response["model"] = model_tier.value
        response["model_tier"] = model_tier.name

        return response
