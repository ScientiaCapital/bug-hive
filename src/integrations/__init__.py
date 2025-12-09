"""Linear integration layer for BugHive.

This module provides Linear issue tracking integration with both
mock (for development) and real (for production) implementations.

Components:
- LinearClient: Abstract interface for Linear API operations
- MockLinearClient: In-memory mock for development/testing
- RealLinearClient: GraphQL API client for production
- ReportWriterAgent: Formats bugs into Linear tickets using LLM

Usage:
    >>> # Development (no API key needed)
    >>> client = get_linear_client()
    >>> issue = await client.create_issue(...)

    >>> # Production (requires LINEAR_API_KEY)
    >>> client = get_linear_client(api_key="lin_api_xxxxx")
    >>> issue = await client.create_issue(...)

    >>> # With Report Writer
    >>> reporter = ReportWriterAgent(llm_router, client)
    >>> issue = await reporter.create_ticket(bug, team_id="qa")
"""

import os
import logging

# Import core types without dependencies
from .linear import LinearClient, LinearIssue
from .linear_mock import MockLinearClient
from .linear_real import RealLinearClient

# Lazy import for ReportWriterAgent to avoid loading LLM dependencies
# when just using the Linear clients
def _get_reporter_agent_class():
    """Lazy import ReportWriterAgent."""
    from .reporter import ReportWriterAgent
    return ReportWriterAgent

logger = logging.getLogger(__name__)

__all__ = [
    "LinearClient",
    "LinearIssue",
    "MockLinearClient",
    "RealLinearClient",
    "get_linear_client",
    "get_reporter_agent",
]


def get_linear_client(api_key: str | None = None) -> LinearClient:
    """Factory function to get appropriate Linear client.

    Automatically selects between mock and real clients based on
    whether an API key is provided.

    Args:
        api_key: Linear API key (format: lin_api_xxxxx)
                 If None, uses environment variable LINEAR_API_KEY
                 If still None, returns MockLinearClient

    Returns:
        LinearClient: Mock or real client instance

    Examples:
        >>> # Explicit mock
        >>> client = get_linear_client()  # MockLinearClient

        >>> # Explicit real
        >>> client = get_linear_client(api_key="lin_api_xxxxx")  # RealLinearClient

        >>> # From environment
        >>> os.environ["LINEAR_API_KEY"] = "lin_api_xxxxx"
        >>> client = get_linear_client()  # RealLinearClient
    """
    # Try to get API key from parameter or environment
    if api_key is None:
        api_key = os.getenv("LINEAR_API_KEY")

    # Return appropriate client
    if api_key:
        logger.info("[LinearFactory] Using RealLinearClient")
        return RealLinearClient(api_key)
    else:
        logger.info("[LinearFactory] Using MockLinearClient (no API key provided)")
        return MockLinearClient()


def get_reporter_agent(
    llm_router,
    api_key: str | None = None
):
    """Factory function to get ReportWriterAgent with appropriate Linear client.

    Args:
        llm_router: LLMRouter instance for formatting tasks
        api_key: Linear API key (optional, will use environment if not provided)

    Returns:
        ReportWriterAgent: Ready-to-use report writer

    Example:
        >>> from src.llm import LLMRouter
        >>> router = LLMRouter(...)
        >>> reporter = get_reporter_agent(router)
        >>> issue = await reporter.create_ticket(bug, team_id="qa")
    """
    ReportWriterAgent = _get_reporter_agent_class()
    linear_client = get_linear_client(api_key)
    return ReportWriterAgent(llm_router, linear_client)
