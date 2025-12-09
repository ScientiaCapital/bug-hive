"""Anthropic client for Claude Opus models."""

import logging
import os

from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam, ToolParam

logger = logging.getLogger(__name__)


class AnthropicClient:
    """Async client for Anthropic Claude models with tool use support."""

    def __init__(
        self,
        api_key: str | None = None,
        max_retries: int = 3,
        timeout: float = 120.0,
    ):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var "
                "or pass api_key parameter."
            )

        self.client = AsyncAnthropic(
            api_key=self.api_key,
            max_retries=max_retries,
            timeout=timeout,
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the client."""
        await self.client.close()

    async def create_message(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float | None = None,
        top_k: int | None = None,
        system: str | None = None,
        tools: list[dict] | None = None,
        stop_sequences: list[str] | None = None,
        metadata: dict | None = None,
        **kwargs,
    ) -> dict:
        """
        Create a message with Claude.

        Args:
            model: Model identifier (e.g., 'claude-opus-4-5-20250514')
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            system: System prompt (separate from messages)
            tools: Tool definitions for function calling
            stop_sequences: List of sequences to stop generation
            metadata: Request metadata for tracking
            **kwargs: Additional parameters

        Returns:
            Dict with:
                - content: Generated text or tool calls
                - usage: Token usage dict
                - stop_reason: Completion reason
                - tool_calls: List of tool calls (if any)
                - raw_response: Full API response

        Raises:
            ValueError: If messages format is invalid
            Exception: If API call fails
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        # Convert to MessageParam format expected by SDK
        formatted_messages = self._format_messages(messages)

        # Build request parameters
        request_params = {
            "model": model,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system:
            request_params["system"] = system

        if top_p is not None:
            request_params["top_p"] = top_p

        if top_k is not None:
            request_params["top_k"] = top_k

        if tools:
            request_params["tools"] = self._format_tools(tools)

        if stop_sequences:
            request_params["stop_sequences"] = stop_sequences

        if metadata:
            request_params["metadata"] = metadata

        # Add any extra parameters
        request_params.update(kwargs)

        logger.info(
            f"Creating message with {model} "
            f"({len(messages)} messages, max_tokens={max_tokens})"
        )

        # Make API call
        response: Message = await self.client.messages.create(**request_params)

        # Extract content
        content_text = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })

        result = {
            "content": content_text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            "stop_reason": response.stop_reason,
            "tool_calls": tool_calls if tool_calls else None,
            "raw_response": response,
        }

        logger.info(
            f"Message completed: {result['usage']['total_tokens']} total tokens, "
            f"stop_reason: {result['stop_reason']}"
        )

        if tool_calls:
            logger.info(f"Tool calls requested: {[tc['name'] for tc in tool_calls]}")

        return result

    def _format_messages(self, messages: list[dict]) -> list[MessageParam]:
        """
        Format messages for Anthropic API.

        Args:
            messages: List of message dicts

        Returns:
            List of properly formatted MessageParam objects
        """
        formatted = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role not in ("user", "assistant"):
                raise ValueError(
                    f"Invalid role '{role}'. Must be 'user' or 'assistant'"
                )

            formatted.append({
                "role": role,
                "content": content,
            })

        return formatted

    def _format_tools(self, tools: list[dict]) -> list[ToolParam]:
        """
        Format tool definitions for Anthropic API.

        Args:
            tools: List of tool definition dicts

        Returns:
            List of properly formatted ToolParam objects

        Example tool format:
            {
                "name": "get_weather",
                "description": "Get current weather for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "City name"}
                    },
                    "required": ["location"]
                }
            }
        """
        formatted_tools = []
        for tool in tools:
            if "name" not in tool or "input_schema" not in tool:
                raise ValueError(
                    "Tool must have 'name' and 'input_schema' fields"
                )

            formatted_tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool["input_schema"],
            })

        return formatted_tools

    async def create_message_with_tool_loop(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict],
        tool_executor,
        max_iterations: int = 5,
        **kwargs,
    ) -> dict:
        """
        Create message with automatic tool execution loop.

        This handles the full agentic loop:
        1. Send message with tools
        2. If tool calls are returned, execute them
        3. Add tool results to conversation
        4. Repeat until no more tool calls or max iterations

        Args:
            model: Model identifier
            messages: Initial message list
            tools: Tool definitions
            tool_executor: Async callable that executes tools
                          Should accept (tool_name, tool_input) and return result
            max_iterations: Maximum tool execution iterations
            **kwargs: Additional parameters for create_message()

        Returns:
            Final response dict after tool loop completes
        """
        conversation = messages.copy()
        iteration = 0

        while iteration < max_iterations:
            response = await self.create_message(
                model=model,
                messages=conversation,
                tools=tools,
                **kwargs,
            )

            # If no tool calls, we're done
            if not response.get("tool_calls"):
                return response

            # Add assistant's response to conversation
            conversation.append({
                "role": "assistant",
                "content": response["raw_response"].content,
            })

            # Execute all tool calls
            tool_results = []
            for tool_call in response["tool_calls"]:
                logger.info(f"Executing tool: {tool_call['name']}")

                try:
                    result = await tool_executor(
                        tool_call["name"],
                        tool_call["input"]
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": str(result),
                    })
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_call["id"],
                        "content": f"Error: {str(e)}",
                        "is_error": True,
                    })

            # Add tool results to conversation
            conversation.append({
                "role": "user",
                "content": tool_results,
            })

            iteration += 1
            logger.info(f"Tool loop iteration {iteration}/{max_iterations}")

        logger.warning(f"Reached max tool iterations ({max_iterations})")
        return response


# Convenience function for one-off requests
async def create_message(
    model: str,
    messages: list[dict],
    **kwargs,
) -> dict:
    """
    Create a message without managing client lifecycle.

    Args:
        model: Model identifier
        messages: Message list
        **kwargs: Additional parameters

    Returns:
        Message result dict
    """
    async with AnthropicClient() as client:
        return await client.create_message(
            model=model,
            messages=messages,
            **kwargs,
        )
