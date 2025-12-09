"""Mock Linear client for development and testing.

This client simulates the Linear API without requiring authentication.
All issues are stored in memory and will be lost when the process ends.
"""

import uuid
import logging
from datetime import datetime

from .linear import LinearClient, LinearIssue

logger = logging.getLogger(__name__)


class MockLinearClient(LinearClient):
    """Mock Linear client for development and testing.

    Features:
    - In-memory issue storage
    - Auto-incrementing issue identifiers (BUG-1, BUG-2, etc.)
    - Simulates all Linear API operations
    - No authentication required
    - Logs all operations for debugging

    Example:
        >>> client = MockLinearClient()
        >>> issue = await client.create_issue(
        ...     title="Button not responding",
        ...     description="Submit button does not work",
        ...     team_id="qa-team"
        ... )
        >>> print(issue.identifier)  # "BUG-1"
    """

    def __init__(self):
        """Initialize mock client with empty issue storage."""
        self.issues: dict[str, LinearIssue] = {}
        self._issue_counter = 0
        self.teams: dict[str, str] = {
            "engineering": "mock-team-engineering",
            "qa": "mock-team-qa",
            "design": "mock-team-design"
        }
        logger.info("[MockLinear] Initialized mock Linear client")

    async def create_issue(
        self,
        title: str,
        description: str,
        team_id: str,
        priority: int = 3,
        labels: list[str] | None = None,
        attachments: list[str] | None = None
    ) -> LinearIssue:
        """Create a mock issue.

        Args:
            title: Issue title
            description: Full description (markdown)
            team_id: Team ID (any string accepted in mock)
            priority: Priority level (default: 3=Medium)
            labels: List of label names (logged but not stored)
            attachments: List of URLs (logged but not stored)

        Returns:
            LinearIssue: Created mock issue

        Example:
            >>> issue = await client.create_issue(
            ...     title="Login page error",
            ...     description="## Steps\n1. Navigate to /login",
            ...     team_id="qa-team",
            ...     priority=2,
            ...     labels=["bug", "frontend"],
            ...     attachments=["https://example.com/screenshot.png"]
            ... )
        """
        self._issue_counter += 1
        issue_id = str(uuid.uuid4())
        identifier = f"BUG-{self._issue_counter}"

        issue = LinearIssue(
            id=issue_id,
            identifier=identifier,
            title=title,
            url=f"https://linear.app/mock/issue/{identifier}",
            priority=priority
        )

        self.issues[issue_id] = issue

        # Log for debugging
        logger.info(
            f"[MockLinear] Created issue {identifier}: {title}",
            extra={
                "issue_id": issue_id,
                "identifier": identifier,
                "team_id": team_id,
                "priority": priority,
                "labels": labels or [],
                "attachments": attachments or [],
                "description_length": len(description)
            }
        )

        return issue

    async def update_issue(
        self,
        issue_id: str,
        title: str | None = None,
        description: str | None = None,
        state_id: str | None = None,
        priority: int | None = None
    ) -> LinearIssue:
        """Update a mock issue.

        Args:
            issue_id: Issue ID (UUID)
            title: New title (optional)
            description: New description (optional)
            state_id: New state ID (optional, logged only)
            priority: New priority (optional)

        Returns:
            LinearIssue: Updated issue

        Raises:
            ValueError: If issue_id not found
        """
        if issue_id not in self.issues:
            logger.error(f"[MockLinear] Issue {issue_id} not found")
            raise ValueError(f"Issue {issue_id} not found")

        issue = self.issues[issue_id]

        # Update fields if provided
        updates = {}
        if title is not None:
            issue.title = title
            updates["title"] = title
        if priority is not None:
            issue.priority = priority
            updates["priority"] = priority

        logger.info(
            f"[MockLinear] Updated issue {issue.identifier}",
            extra={
                "issue_id": issue_id,
                "updates": updates,
                "state_id": state_id
            }
        )

        return issue

    async def get_issue(self, issue_id: str) -> LinearIssue | None:
        """Get a mock issue by ID.

        Args:
            issue_id: Issue ID (UUID)

        Returns:
            LinearIssue if found, None otherwise
        """
        issue = self.issues.get(issue_id)
        if issue:
            logger.debug(f"[MockLinear] Retrieved issue {issue.identifier}")
        else:
            logger.warning(f"[MockLinear] Issue {issue_id} not found")
        return issue

    async def get_team_id(self, team_name: str) -> str | None:
        """Get mock team ID by name.

        Args:
            team_name: Team name (case-insensitive)

        Returns:
            Mock team ID (always succeeds with format "mock-team-{name}")
        """
        team_name_lower = team_name.lower()
        if team_name_lower in self.teams:
            team_id = self.teams[team_name_lower]
        else:
            # Auto-create mock team
            team_id = f"mock-team-{team_name_lower}"
            self.teams[team_name_lower] = team_id
            logger.info(f"[MockLinear] Auto-created mock team: {team_name}")

        return team_id

    def get_all_issues(self) -> list[LinearIssue]:
        """Get all mock issues (for debugging/testing).

        Returns:
            List of all created issues
        """
        return list(self.issues.values())

    def clear_issues(self):
        """Clear all mock issues (for testing)."""
        count = len(self.issues)
        self.issues.clear()
        self._issue_counter = 0
        logger.info(f"[MockLinear] Cleared {count} mock issues")
