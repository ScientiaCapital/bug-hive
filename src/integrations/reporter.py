"""Report Writer Agent for generating Linear tickets.

This agent takes Bug objects and generates well-formatted Linear tickets
using LLM to format the content professionally.
"""

import logging
from datetime import datetime

from src.models.bug import Bug, Evidence
from src.llm import LLMRouter
from .linear import LinearClient, LinearIssue

logger = logging.getLogger(__name__)


class ReportWriterAgent:
    """Generates well-formatted Linear tickets from bugs.

    This agent:
    1. Takes a Bug object with evidence
    2. Uses LLM to format a professional markdown report
    3. Creates a Linear ticket via the LinearClient
    4. Maps bug priority to Linear priority levels

    Example:
        >>> router = LLMRouter(anthropic_key="...", openrouter_key="...")
        >>> linear = MockLinearClient()
        >>> reporter = ReportWriterAgent(router, linear)
        >>> issue = await reporter.create_ticket(bug, team_id="qa-team")
        >>> print(issue.url)
    """

    def __init__(self, llm_router: LLMRouter, linear_client: LinearClient):
        """Initialize the Report Writer Agent.

        Args:
            llm_router: LLM router for formatting tasks
            linear_client: Linear client (mock or real)
        """
        self.llm = llm_router
        self.linear = linear_client
        logger.info("[ReportWriter] Initialized Report Writer Agent")

    def _format_evidence(self, evidence_list: list[Evidence]) -> str:
        """Format evidence list as markdown.

        Args:
            evidence_list: List of Evidence objects

        Returns:
            Formatted markdown string
        """
        if not evidence_list:
            return "No evidence collected"

        formatted = []
        for idx, evidence in enumerate(evidence_list, 1):
            if evidence.type == "screenshot":
                formatted.append(f"{idx}. **Screenshot**: {evidence.content}")
            elif evidence.type == "console_log":
                formatted.append(f"{idx}. **Console Log**:\n```\n{evidence.content}\n```")
            elif evidence.type == "network_request":
                formatted.append(f"{idx}. **Network Request**: {evidence.content}")
            elif evidence.type == "dom_snapshot":
                # Truncate long DOM snapshots
                content = evidence.content
                if len(content) > 500:
                    content = content[:500] + "... (truncated)"
                formatted.append(f"{idx}. **DOM Snapshot**:\n```html\n{content}\n```")
            elif evidence.type == "performance_metrics":
                formatted.append(f"{idx}. **Performance Metrics**: {evidence.content}")
            else:
                formatted.append(f"{idx}. **{evidence.type}**: {evidence.content}")

        return "\n".join(formatted)

    def _format_evidence_for_prompt(self, evidence_list: list[Evidence]) -> str:
        """Format evidence for inclusion in LLM prompt.

        Args:
            evidence_list: List of Evidence objects

        Returns:
            Formatted string for prompt
        """
        if not evidence_list:
            return "No evidence available"

        evidence_strs = []
        for evidence in evidence_list:
            evidence_strs.append(f"- {evidence.type}: {evidence.content[:200]}")

        return "\n".join(evidence_strs)

    async def generate_report(self, bug: Bug) -> str:
        """Generate markdown report for a bug.

        Uses LLM task "format_ticket" with Qwen 32B (ModelTier.FAST).

        Args:
            bug: Bug object to format

        Returns:
            Formatted markdown report

        Example:
            >>> report = await reporter.generate_report(bug)
            >>> print(report)
            ## Summary
            Fix submit button not responding on checkout page
            ...
        """
        from src.agents.prompts.reporter import FORMAT_TICKET

        # Format evidence for display in the ticket
        evidence_formatted = self._format_evidence(bug.evidence)

        # Format evidence for LLM prompt
        evidence_prompt = self._format_evidence_for_prompt(bug.evidence)

        # Format timestamp - Bug model uses created_at, not timestamp
        timestamp = bug.created_at.isoformat()

        # Get URL from bug - we'll need to reconstruct or store it
        # For now, use a placeholder since Bug model doesn't have url field
        url = f"Bug ID: {bug.id}"

        # Fill in the prompt template
        prompt = FORMAT_TICKET.format(
            title=bug.title,
            category=bug.category,
            priority=bug.priority,
            description=bug.description,
            evidence=evidence_prompt,
            evidence_formatted=evidence_formatted,
            url=url,
            timestamp=timestamp
        )

        logger.info(
            f"[ReportWriter] Generating report for bug: {bug.title}",
            extra={"bug_id": str(bug.id), "category": bug.category}
        )

        # Use LLM router to format the ticket
        # Task: format_ticket → Qwen 32B (ModelTier.FAST)
        response = await self.llm.route(
            task="format_ticket",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.5  # Lower temperature for more consistent formatting
        )

        report = response.get("content", "")

        logger.debug(
            f"[ReportWriter] Generated report ({len(report)} chars)",
            extra={"bug_id": str(bug.id)}
        )

        return report

    def _map_priority(self, bug_priority: str) -> int:
        """Map bug priority to Linear priority level.

        Args:
            bug_priority: Bug priority string (critical/high/medium/low)

        Returns:
            Linear priority (0-4)
        """
        priority_map = {
            "critical": 1,  # Urgent
            "high": 2,      # High
            "medium": 3,    # Medium (default)
            "low": 4        # Low
        }
        return priority_map.get(bug_priority.lower(), 3)

    def _extract_screenshot_urls(self, evidence_list: list[Evidence]) -> list[str]:
        """Extract screenshot URLs from evidence.

        Args:
            evidence_list: List of Evidence objects

        Returns:
            List of screenshot URLs
        """
        screenshots = []
        for evidence in evidence_list:
            if evidence.type == "screenshot":
                # Evidence.content should be a URL for screenshots
                screenshots.append(evidence.content)
        return screenshots

    async def create_ticket(
        self,
        bug: Bug,
        team_id: str,
        auto_format: bool = True
    ) -> LinearIssue:
        """Create Linear ticket for bug.

        Args:
            bug: Bug object to report
            team_id: Linear team ID to create ticket in
            auto_format: Whether to use LLM to format the report (default: True)

        Returns:
            LinearIssue: Created Linear issue

        Raises:
            Exception: If ticket creation fails

        Example:
            >>> issue = await reporter.create_ticket(bug, team_id="qa-team")
            >>> print(f"Created: {issue.url}")
        """
        logger.info(
            f"[ReportWriter] Creating ticket for bug: {bug.title}",
            extra={
                "bug_id": str(bug.id),
                "team_id": team_id,
                "priority": bug.priority,
                "category": bug.category
            }
        )

        # Generate formatted report using LLM
        if auto_format:
            report = await self.generate_report(bug)
        else:
            # Fallback: Use bug description directly
            report = f"## Description\n{bug.description}\n\n## URL\n{bug.url}"

        # Map priority
        linear_priority = self._map_priority(bug.priority)

        # Extract screenshot URLs
        attachments = self._extract_screenshot_urls(bug.evidence)

        # Create the Linear issue
        try:
            issue = await self.linear.create_issue(
                title=bug.title,
                description=report,
                team_id=team_id,
                priority=linear_priority,
                labels=[bug.category],
                attachments=attachments
            )

            logger.info(
                f"[ReportWriter] Created Linear issue {issue.identifier}",
                extra={
                    "bug_id": str(bug.id),
                    "issue_id": issue.id,
                    "issue_url": issue.url
                }
            )

            return issue

        except Exception as e:
            logger.error(
                f"[ReportWriter] Failed to create ticket for bug {bug.title}: {e}",
                extra={"bug_id": str(bug.id), "error": str(e)},
                exc_info=True
            )
            raise

    async def update_ticket(
        self,
        issue_id: str,
        bug: Bug,
        regenerate: bool = False
    ) -> LinearIssue:
        """Update existing Linear ticket.

        Args:
            issue_id: Linear issue ID to update
            bug: Updated bug object
            regenerate: Whether to regenerate the full report (default: False)

        Returns:
            LinearIssue: Updated issue

        Example:
            >>> updated = await reporter.update_ticket(
            ...     issue_id="abc-123",
            ...     bug=updated_bug,
            ...     regenerate=True
            ... )
        """
        logger.info(
            f"[ReportWriter] Updating ticket {issue_id}",
            extra={"bug_id": str(bug.id), "regenerate": regenerate}
        )

        if regenerate:
            # Regenerate full report
            report = await self.generate_report(bug)
            linear_priority = self._map_priority(bug.priority)

            issue = await self.linear.update_issue(
                issue_id=issue_id,
                title=bug.title,
                description=report,
                priority=linear_priority
            )
        else:
            # Just update priority
            linear_priority = self._map_priority(bug.priority)
            issue = await self.linear.update_issue(
                issue_id=issue_id,
                priority=linear_priority
            )

        logger.info(f"[ReportWriter] Updated issue {issue.identifier}")
        return issue
