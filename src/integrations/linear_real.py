"""Real Linear API client implementation.

This client connects to the actual Linear GraphQL API.
Requires LINEAR_API_KEY environment variable.

Reference: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
"""

import httpx
import logging
from typing import Any

from .linear import LinearClient, LinearIssue

logger = logging.getLogger(__name__)


class RealLinearClient(LinearClient):
    """Real Linear API client using GraphQL.

    This client implements the actual Linear API integration.
    Currently a skeleton - will be implemented when Linear workspace is ready.

    Authentication:
        Uses API key authentication via Authorization header.

    GraphQL Endpoint:
        https://api.linear.app/graphql

    Example:
        >>> client = RealLinearClient(api_key="lin_api_xxxxx")
        >>> issue = await client.create_issue(
        ...     title="Bug found",
        ...     description="Description",
        ...     team_id="team-uuid"
        ... )
    """

    def __init__(self, api_key: str):
        """Initialize real Linear client.

        Args:
            api_key: Linear API key (format: lin_api_xxxxx)

        Raises:
            ValueError: If api_key is empty or invalid format
        """
        if not api_key or not api_key.startswith("lin_api_"):
            raise ValueError("Invalid Linear API key format (expected: lin_api_xxxxx)")

        self.api_key = api_key
        self.base_url = "https://api.linear.app/graphql"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
        logger.info("[RealLinear] Initialized real Linear client")

    async def _execute_query(self, query: str, variables: dict[str, Any]) -> dict:
        """Execute GraphQL query.

        Args:
            query: GraphQL query/mutation string
            variables: Query variables

        Returns:
            Response data

        Raises:
            Exception: If API request fails
        """
        response = await self.client.post(
            self.base_url,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            logger.error(f"[RealLinear] GraphQL errors: {data['errors']}")
            raise Exception(f"Linear API error: {data['errors']}")

        return data.get("data", {})

    async def create_issue(
        self,
        title: str,
        description: str,
        team_id: str,
        priority: int = 3,
        labels: list[str] | None = None,
        attachments: list[str] | None = None
    ) -> LinearIssue:
        """Create issue via GraphQL API.

        Args:
            title: Issue title
            description: Full description (markdown supported)
            team_id: Linear team ID (UUID)
            priority: Priority level (0-4)
            labels: List of label IDs (not names)
            attachments: List of attachment URLs

        Returns:
            LinearIssue: Created issue

        Raises:
            Exception: If API request fails

        TODO: Implement when Linear workspace is ready
        """
        mutation = """
        mutation CreateIssue(
            $title: String!,
            $description: String!,
            $teamId: String!,
            $priority: Int
        ) {
            issueCreate(input: {
                title: $title
                description: $description
                teamId: $teamId
                priority: $priority
            }) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                    priority
                }
            }
        }
        """

        variables = {
            "title": title,
            "description": description,
            "teamId": team_id,
            "priority": priority
        }

        logger.info(
            f"[RealLinear] Creating issue: {title}",
            extra={
                "team_id": team_id,
                "priority": priority,
                "labels": labels,
                "attachments": attachments
            }
        )

        data = await self._execute_query(mutation, variables)
        result = data.get("issueCreate", {})

        if not result.get("success"):
            raise Exception("Failed to create issue")

        issue_data = result.get("issue", {})
        issue = LinearIssue(
            id=issue_data["id"],
            identifier=issue_data["identifier"],
            title=issue_data["title"],
            url=issue_data["url"],
            priority=issue_data["priority"]
        )

        logger.info(f"[RealLinear] Created issue {issue.identifier}")
        return issue

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
            state_id: New state ID (optional)
            priority: New priority (optional)

        Returns:
            LinearIssue: Updated issue

        Raises:
            ValueError: If issue_id not found
            Exception: If API request fails

        TODO: Implement when Linear workspace is ready
        """
        mutation = """
        mutation UpdateIssue(
            $issueId: String!,
            $title: String,
            $description: String,
            $stateId: String,
            $priority: Int
        ) {
            issueUpdate(
                id: $issueId,
                input: {
                    title: $title
                    description: $description
                    stateId: $stateId
                    priority: $priority
                }
            ) {
                success
                issue {
                    id
                    identifier
                    title
                    url
                    priority
                }
            }
        }
        """

        variables = {
            "issueId": issue_id,
            "title": title,
            "description": description,
            "stateId": state_id,
            "priority": priority
        }

        logger.info(f"[RealLinear] Updating issue {issue_id}")

        data = await self._execute_query(mutation, variables)
        result = data.get("issueUpdate", {})

        if not result.get("success"):
            raise Exception(f"Failed to update issue {issue_id}")

        issue_data = result.get("issue", {})
        return LinearIssue(
            id=issue_data["id"],
            identifier=issue_data["identifier"],
            title=issue_data["title"],
            url=issue_data["url"],
            priority=issue_data["priority"]
        )

    async def get_issue(self, issue_id: str) -> LinearIssue | None:
        """Get issue by ID.

        Args:
            issue_id: Linear issue ID (UUID)

        Returns:
            LinearIssue if found, None otherwise

        TODO: Implement when Linear workspace is ready
        """
        query = """
        query GetIssue($issueId: String!) {
            issue(id: $issueId) {
                id
                identifier
                title
                url
                priority
            }
        }
        """

        try:
            data = await self._execute_query(query, {"issueId": issue_id})
            issue_data = data.get("issue")

            if not issue_data:
                return None

            return LinearIssue(
                id=issue_data["id"],
                identifier=issue_data["identifier"],
                title=issue_data["title"],
                url=issue_data["url"],
                priority=issue_data["priority"]
            )
        except Exception as e:
            logger.error(f"[RealLinear] Error getting issue {issue_id}: {e}")
            return None

    async def get_team_id(self, team_name: str) -> str | None:
        """Get team ID by name.

        Args:
            team_name: Team name (e.g., "Engineering")

        Returns:
            Team ID if found, None otherwise

        TODO: Implement when Linear workspace is ready
        """
        query = """
        query GetTeams {
            teams {
                nodes {
                    id
                    name
                    key
                }
            }
        }
        """

        try:
            data = await self._execute_query(query, {})
            teams = data.get("teams", {}).get("nodes", [])

            for team in teams:
                if team["name"].lower() == team_name.lower():
                    logger.info(f"[RealLinear] Found team '{team_name}': {team['id']}")
                    return team["id"]

            logger.warning(f"[RealLinear] Team '{team_name}' not found")
            return None
        except Exception as e:
            logger.error(f"[RealLinear] Error getting team: {e}")
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        logger.info("[RealLinear] Closed HTTP client")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
