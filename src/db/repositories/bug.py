"""Repository for bug operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import Evidence
from ..models import BugDB
from .base import BaseRepository


class BugRepository(BaseRepository[BugDB]):
    """Repository for bug database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize bug repository."""
        super().__init__(BugDB, session)

    async def create_bug(
        self,
        session_id: UUID,
        page_id: UUID,
        category: str,
        priority: str,
        title: str,
        description: str,
        steps_to_reproduce: list[str],
        evidence: list[Evidence],
        confidence: float,
        expected_behavior: str | None = None,
        actual_behavior: str | None = None,
        affected_users: str | None = None,
        browser_info: dict | None = None,
    ) -> BugDB:
        """
        Create a new bug record.

        Args:
            session_id: Parent session ID
            page_id: Page where bug was found
            category: Bug category
            priority: Bug priority
            title: Bug title
            description: Bug description
            steps_to_reproduce: Steps to reproduce
            evidence: List of evidence
            confidence: AI confidence score
            expected_behavior: Expected behavior
            actual_behavior: Actual behavior
            affected_users: Affected users
            browser_info: Browser information

        Returns:
            Created bug
        """
        return await self.create(
            session_id=session_id,
            page_id=page_id,
            category=category,
            priority=priority,
            title=title,
            description=description,
            steps_to_reproduce=steps_to_reproduce,
            evidence=[e.model_dump() for e in evidence],
            confidence=confidence,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            affected_users=affected_users,
            browser_info=browser_info,
            status="detected",
        )

    async def mark_validated(self, bug_id: UUID) -> BugDB | None:
        """
        Mark bug as validated.

        Args:
            bug_id: Bug ID

        Returns:
            Updated bug or None if not found
        """
        return await self.update(bug_id, status="validated")

    async def mark_reported(
        self,
        bug_id: UUID,
        linear_issue_id: str,
        linear_issue_url: str,
    ) -> BugDB | None:
        """
        Mark bug as reported to Linear.

        Args:
            bug_id: Bug ID
            linear_issue_id: Linear issue ID
            linear_issue_url: Linear issue URL

        Returns:
            Updated bug or None if not found
        """
        return await self.update(
            bug_id,
            status="reported",
            linear_issue_id=linear_issue_id,
            linear_issue_url=linear_issue_url,
            reported_at=datetime.utcnow(),
        )

    async def mark_dismissed(
        self,
        bug_id: UUID,
        reason: str,
    ) -> BugDB | None:
        """
        Mark bug as dismissed.

        Args:
            bug_id: Bug ID
            reason: Dismissal reason

        Returns:
            Updated bug or None if not found
        """
        return await self.update(
            bug_id,
            status="dismissed",
            dismissed_reason=reason,
            dismissed_at=datetime.utcnow(),
        )

    async def update_priority(
        self,
        bug_id: UUID,
        priority: str,
    ) -> BugDB | None:
        """
        Update bug priority.

        Args:
            bug_id: Bug ID
            priority: New priority

        Returns:
            Updated bug or None if not found
        """
        return await self.update(bug_id, priority=priority)

    async def get_session_bugs(
        self,
        session_id: UUID,
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BugDB]:
        """
        Get bugs for a session with filters.

        Args:
            session_id: Session ID
            status: Optional status filter
            priority: Optional priority filter
            category: Optional category filter
            skip: Number to skip
            limit: Maximum number to return

        Returns:
            List of bugs
        """
        query = select(BugDB).where(BugDB.session_id == session_id)

        if status:
            query = query.where(BugDB.status == status)
        if priority:
            query = query.where(BugDB.priority == priority)
        if category:
            query = query.where(BugDB.category == category)

        query = (
            query.order_by(
                BugDB.priority.desc(),
                BugDB.confidence.desc(),
                BugDB.created_at.desc()
            )
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_page_bugs(
        self,
        page_id: UUID,
        status: str | None = None,
    ) -> list[BugDB]:
        """
        Get bugs for a specific page.

        Args:
            page_id: Page ID
            status: Optional status filter

        Returns:
            List of bugs
        """
        query = select(BugDB).where(BugDB.page_id == page_id)

        if status:
            query = query.where(BugDB.status == status)

        query = query.order_by(
            BugDB.priority.desc(),
            BugDB.confidence.desc()
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_high_confidence_bugs(
        self,
        session_id: UUID,
        min_confidence: float = 0.8,
        status: str | None = None,
    ) -> list[BugDB]:
        """
        Get high-confidence bugs.

        Args:
            session_id: Session ID
            min_confidence: Minimum confidence threshold
            status: Optional status filter

        Returns:
            List of high-confidence bugs
        """
        query = (
            select(BugDB)
            .where(BugDB.session_id == session_id)
            .where(BugDB.confidence >= min_confidence)
        )

        if status:
            query = query.where(BugDB.status == status)

        query = query.order_by(BugDB.confidence.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_critical_bugs(
        self,
        session_id: UUID,
        status: str | None = None,
    ) -> list[BugDB]:
        """
        Get critical priority bugs.

        Args:
            session_id: Session ID
            status: Optional status filter

        Returns:
            List of critical bugs
        """
        query = (
            select(BugDB)
            .where(BugDB.session_id == session_id)
            .where(BugDB.priority == "critical")
        )

        if status:
            query = query.where(BugDB.status == status)

        query = query.order_by(BugDB.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_priority(
        self,
        session_id: UUID,
        status: str | None = None,
    ) -> dict[str, int]:
        """
        Count bugs by priority.

        Args:
            session_id: Session ID
            status: Optional status filter

        Returns:
            Dictionary of priority -> count
        """
        query = (
            select(BugDB.priority, func.count(BugDB.id))
            .where(BugDB.session_id == session_id)
        )

        if status:
            query = query.where(BugDB.status == status)

        query = query.group_by(BugDB.priority)

        result = await self.session.execute(query)
        return dict(result.all())

    async def count_by_category(
        self,
        session_id: UUID,
        status: str | None = None,
    ) -> dict[str, int]:
        """
        Count bugs by category.

        Args:
            session_id: Session ID
            status: Optional status filter

        Returns:
            Dictionary of category -> count
        """
        query = (
            select(BugDB.category, func.count(BugDB.id))
            .where(BugDB.session_id == session_id)
        )

        if status:
            query = query.where(BugDB.status == status)

        query = query.group_by(BugDB.category)

        result = await self.session.execute(query)
        return dict(result.all())

    async def count_by_status(
        self,
        session_id: UUID,
    ) -> dict[str, int]:
        """
        Count bugs by status.

        Args:
            session_id: Session ID

        Returns:
            Dictionary of status -> count
        """
        result = await self.session.execute(
            select(BugDB.status, func.count(BugDB.id))
            .where(BugDB.session_id == session_id)
            .group_by(BugDB.status)
        )

        return dict(result.all())

    async def get_average_confidence(
        self,
        session_id: UUID,
        status: str | None = None,
    ) -> float:
        """
        Get average confidence score.

        Args:
            session_id: Session ID
            status: Optional status filter

        Returns:
            Average confidence score (0-1)
        """
        query = (
            select(func.avg(BugDB.confidence))
            .where(BugDB.session_id == session_id)
        )

        if status:
            query = query.where(BugDB.status == status)

        result = await self.session.execute(query)
        avg = result.scalar_one_or_none()
        return float(avg) if avg is not None else 0.0

    async def get_bug_statistics(
        self,
        session_id: UUID,
    ) -> dict:
        """
        Get comprehensive bug statistics for a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with bug statistics
        """
        total_bugs = await self.count(session_id=session_id)
        bugs_by_priority = await self.count_by_priority(session_id)
        bugs_by_category = await self.count_by_category(session_id)
        bugs_by_status = await self.count_by_status(session_id)
        average_confidence = await self.get_average_confidence(session_id)

        return {
            "total_bugs": total_bugs,
            "bugs_by_priority": bugs_by_priority,
            "bugs_by_category": bugs_by_category,
            "bugs_by_status": bugs_by_status,
            "average_confidence": average_confidence,
            "bugs_reported": bugs_by_status.get("reported", 0),
            "bugs_dismissed": bugs_by_status.get("dismissed", 0),
        }

    async def search_bugs(
        self,
        session_id: UUID,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[BugDB]:
        """
        Search bugs by title or description.

        Args:
            session_id: Session ID
            search_term: Search term
            skip: Number to skip
            limit: Maximum number to return

        Returns:
            List of matching bugs
        """
        search_pattern = f"%{search_term}%"
        result = await self.session.execute(
            select(BugDB)
            .where(BugDB.session_id == session_id)
            .where(
                (BugDB.title.ilike(search_pattern)) |
                (BugDB.description.ilike(search_pattern))
            )
            .order_by(BugDB.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_unreported_bugs(
        self,
        session_id: UUID,
        min_priority: str | None = None,
        min_confidence: float | None = None,
    ) -> list[BugDB]:
        """
        Get bugs that haven't been reported yet.

        Args:
            session_id: Session ID
            min_priority: Minimum priority filter
            min_confidence: Minimum confidence filter

        Returns:
            List of unreported bugs
        """
        query = (
            select(BugDB)
            .where(BugDB.session_id == session_id)
            .where(BugDB.status.in_(["detected", "validated"]))
        )

        if min_priority:
            # Define priority order
            priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            min_value = priority_order.get(min_priority, 0)
            priorities = [p for p, v in priority_order.items() if v >= min_value]
            query = query.where(BugDB.priority.in_(priorities))

        if min_confidence is not None:
            query = query.where(BugDB.confidence >= min_confidence)

        query = query.order_by(
            BugDB.priority.desc(),
            BugDB.confidence.desc()
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())
