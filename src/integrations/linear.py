"""Linear integration abstract interface.

Defines the contract for Linear API clients (mock and real).
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel


class LinearIssue(BaseModel):
    """Represents a Linear issue.

    Attributes:
        id: Unique issue ID (UUID format)
        identifier: Human-readable identifier (e.g., "BUG-123")
        title: Issue title
        url: Direct URL to the issue in Linear
        priority: Priority level (0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low)
    """
    id: str
    identifier: str  # e.g., "BUG-123"
    title: str
    url: str
    priority: int  # 0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low


class LinearClient(ABC):
    """Abstract base class for Linear API clients.

    This interface ensures both MockLinearClient and RealLinearClient
    implement the same methods, allowing seamless switching between
    mock and production environments.
    """

    @abstractmethod
    async def create_issue(
        self,
        title: str,
        description: str,
        team_id: str,
        priority: int = 3,
        labels: list[str] | None = None,
        attachments: list[str] | None = None  # Screenshot URLs
    ) -> LinearIssue:
        """Create a new issue in Linear.

        Args:
            title: Issue title (summary)
            description: Full issue description (markdown supported)
            team_id: Linear team ID to create issue in
            priority: Priority level (default: 3=Medium)
            labels: List of label names to apply
            attachments: List of screenshot/file URLs to attach

        Returns:
            LinearIssue: Created issue with ID and URL

        Raises:
            ValueError: If team_id is invalid
            Exception: If API request fails
        """
        pass

    @abstractmethod
    async def update_issue(
        self,
        issue_id: str,
        title: str | None = None,
        description: str | None = None,
        state_id: str | None = None,
        priority: int | None = None
    ) -> LinearIssue:
        """Update an existing issue.

        Args:
            issue_id: Linear issue ID (UUID)
            title: New title (optional)
            description: New description (optional)
            state_id: New state ID (e.g., for moving to "In Progress")
            priority: New priority level (optional)

        Returns:
            LinearIssue: Updated issue

        Raises:
            ValueError: If issue_id not found
            Exception: If API request fails
        """
        pass

    @abstractmethod
    async def get_issue(self, issue_id: str) -> LinearIssue | None:
        """Get issue by ID.

        Args:
            issue_id: Linear issue ID (UUID)

        Returns:
            LinearIssue if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_team_id(self, team_name: str) -> str | None:
        """Get team ID by name.

        Args:
            team_name: Team name (e.g., "Engineering", "QA")

        Returns:
            Team ID if found, None otherwise
        """
        pass
