"""OpenRouter client for DeepSeek and Qwen models."""

import asyncio
import logging
import os

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class OpenRouterError(Exception):
    """Base exception for OpenRouter API errors."""
    pass


class OpenRouterClient:
    """Async client for OpenRouter API supporting DeepSeek and Qwen models."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        """
        Initialize OpenRouter client.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY env var "
                "or pass api_key parameter."
            )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://bughive.dev",  # Optional site URL
                "X-Title": "BugHive",  # Optional app name
            },
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((httpx.HTTPError, RateLimitError)),
        reraise=True,
    )
    async def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        json_data: dict | None = None,
    ) -> dict:
        """
        Make HTTP request with retry logic.

        Args:
            endpoint: API endpoint (e.g., '/chat/completions')
            method: HTTP method
            json_data: JSON payload

        Returns:
            Response JSON dict

        Raises:
            RateLimitError: If rate limit is exceeded
            OpenRouterError: For other API errors
            httpx.HTTPError: For network errors
        """
        url = f"{self.base_url}{endpoint}"

        logger.debug(f"Making {method} request to {url}")

        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=json_data,
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 30))
                logger.warning(
                    f"Rate limit exceeded. Retrying after {retry_after}s"
                )
                await asyncio.sleep(retry_after)
                raise RateLimitError("Rate limit exceeded")

            # Raise for other HTTP errors
            response.raise_for_status()

            return response.json()

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"OpenRouter API error: {e.response.status_code} - {error_detail}")
            raise OpenRouterError(
                f"API request failed: {e.response.status_code} - {error_detail}"
            ) from e

    async def create_completion(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.7,
        top_p: float = 1.0,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        stop: list[str] | None = None,
        stream: bool = False,
        **kwargs,
    ) -> dict:
        """
        Create a chat completion.

        Args:
            model: Model identifier (e.g., 'deepseek/deepseek-chat')
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter
            frequency_penalty: Frequency penalty (-2.0 to 2.0)
            presence_penalty: Presence penalty (-2.0 to 2.0)
            stop: List of stop sequences
            stream: Whether to stream the response (not implemented)
            **kwargs: Additional model-specific parameters

        Returns:
            Dict with:
                - content: Generated text
                - usage: Token usage dict
                - finish_reason: Completion reason
                - raw_response: Full API response

        Raises:
            ValueError: If messages format is invalid
            OpenRouterError: If API call fails
        """
        if not messages:
            raise ValueError("messages cannot be empty")

        if stream:
            raise NotImplementedError("Streaming not yet implemented")

        # Build request payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
        }

        if stop:
            payload["stop"] = stop

        # Add any extra parameters
        payload.update(kwargs)

        logger.info(
            f"Creating completion with {model} "
            f"({len(messages)} messages, max_tokens={max_tokens})"
        )

        response = await self._make_request(
            endpoint="/chat/completions",
            method="POST",
            json_data=payload,
        )

        # Extract relevant information
        choice = response["choices"][0]
        message = choice["message"]

        result = {
            "content": message.get("content", ""),
            "usage": {
                "input_tokens": response["usage"]["prompt_tokens"],
                "output_tokens": response["usage"]["completion_tokens"],
                "total_tokens": response["usage"]["total_tokens"],
            },
            "finish_reason": choice.get("finish_reason"),
            "raw_response": response,
        }

        logger.info(
            f"Completion finished: {result['usage']['total_tokens']} total tokens, "
            f"reason: {result['finish_reason']}"
        )

        return result

    async def create_completion_stream(
        self,
        model: str,
        messages: list[dict],
        **kwargs,
    ):
        """
        Create a streaming chat completion.

        Args:
            model: Model identifier
            messages: List of message dicts
            **kwargs: Additional parameters

        Yields:
            Chunks of generated text

        Note:
            This is a placeholder for future streaming implementation.
        """
        # TODO: Implement streaming with Server-Sent Events (SSE)
        raise NotImplementedError(
            "Streaming support will be added in a future update"
        )

    async def get_models(self) -> list[dict]:
        """
        Get list of available models from OpenRouter.

        Returns:
            List of model dicts with metadata

        Note:
            Useful for checking model availability and pricing.
        """
        response = await self._make_request(
            endpoint="/models",
            method="GET",
        )
        return response.get("data", [])

    async def get_generation_stats(self, generation_id: str) -> dict:
        """
        Get stats for a specific generation (if supported by OpenRouter).

        Args:
            generation_id: ID from a previous completion

        Returns:
            Stats dict with timing and cost information
        """
        response = await self._make_request(
            endpoint=f"/generation?id={generation_id}",
            method="GET",
        )
        return response


# Convenience function for one-off requests
async def create_completion(
    model: str,
    messages: list[dict],
    **kwargs,
) -> dict:
    """
    Create a completion without managing client lifecycle.

    Args:
        model: Model identifier
        messages: Message list
        **kwargs: Additional parameters

    Returns:
        Completion result dict
    """
    async with OpenRouterClient() as client:
        return await client.create_completion(
            model=model,
            messages=messages,
            **kwargs,
        )
