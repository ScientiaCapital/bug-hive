"""Repository for crawl session operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import CrawlConfig
from ..models import CrawlSessionDB
from .base import BaseRepository


class CrawlSessionRepository(BaseRepository[CrawlSessionDB]):
    """Repository for crawl session database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize crawl session repository."""
        super().__init__(CrawlSessionDB, session)

    async def create_session(
        self,
        base_url: str,
        config: CrawlConfig,
    ) -> CrawlSessionDB:
        """
        Create a new crawl session.

        Args:
            base_url: Base URL to crawl
            config: Crawl configuration

        Returns:
            Created session
        """
        return await self.create(
            base_url=base_url,
            config=config.model_dump(),
            status="pending",
        )

    async def start_session(self, session_id: UUID) -> CrawlSessionDB | None:
        """
        Mark session as started.

        Args:
            session_id: Session ID

        Returns:
            Updated session or None if not found
        """
        return await self.update(
            session_id,
            status="running",
            started_at=datetime.utcnow(),
        )

    async def complete_session(
        self,
        session_id: UUID,
        success: bool = True,
        error_message: str | None = None,
    ) -> CrawlSessionDB | None:
        """
        Mark session as completed or failed.

        Args:
            session_id: Session ID
            success: Whether session completed successfully
            error_message: Error message if failed

        Returns:
            Updated session or None if not found
        """
        return await self.update(
            session_id,
            status="completed" if success else "failed",
            completed_at=datetime.utcnow(),
            error_message=error_message,
        )

    async def update_metrics(
        self,
        session_id: UUID,
        pages_discovered: int | None = None,
        pages_crawled: int | None = None,
        bugs_found: int | None = None,
        total_cost: float | None = None,
    ) -> CrawlSessionDB | None:
        """
        Update session metrics.

        Args:
            session_id: Session ID
            pages_discovered: Total pages discovered
            pages_crawled: Total pages crawled
            bugs_found: Total bugs found
            total_cost: Total AI cost

        Returns:
            Updated session or None if not found
        """
        kwargs = {}
        if pages_discovered is not None:
            kwargs["pages_discovered"] = pages_discovered
        if pages_crawled is not None:
            kwargs["pages_crawled"] = pages_crawled
        if bugs_found is not None:
            kwargs["bugs_found"] = bugs_found
        if total_cost is not None:
            kwargs["total_cost"] = total_cost

        if not kwargs:
            return await self.get_by_id(session_id)

        return await self.update(session_id, **kwargs)

    async def increment_pages_discovered(
        self,
        session_id: UUID,
        count: int = 1,
    ) -> CrawlSessionDB | None:
        """
        Increment pages_discovered counter.

        Args:
            session_id: Session ID
            count: Number to increment by

        Returns:
            Updated session or None if not found
        """
        session = await self.get_by_id(session_id)
        if session is None:
            return None

        return await self.update(
            session_id,
            pages_discovered=session.pages_discovered + count,
        )

    async def increment_pages_crawled(
        self,
        session_id: UUID,
        count: int = 1,
    ) -> CrawlSessionDB | None:
        """
        Increment pages_crawled counter.

        Args:
            session_id: Session ID
            count: Number to increment by

        Returns:
            Updated session or None if not found
        """
        session = await self.get_by_id(session_id)
        if session is None:
            return None

        return await self.update(
            session_id,
            pages_crawled=session.pages_crawled + count,
        )

    async def increment_bugs_found(
        self,
        session_id: UUID,
        count: int = 1,
    ) -> CrawlSessionDB | None:
        """
        Increment bugs_found counter.

        Args:
            session_id: Session ID
            count: Number to increment by

        Returns:
            Updated session or None if not found
        """
        session = await self.get_by_id(session_id)
        if session is None:
            return None

        return await self.update(
            session_id,
            bugs_found=session.bugs_found + count,
        )

    async def add_cost(
        self,
        session_id: UUID,
        cost: float,
    ) -> CrawlSessionDB | None:
        """
        Add to total cost.

        Args:
            session_id: Session ID
            cost: Cost to add

        Returns:
            Updated session or None if not found
        """
        session = await self.get_by_id(session_id)
        if session is None:
            return None

        return await self.update(
            session_id,
            total_cost=float(session.total_cost) + cost,
        )

    async def get_by_base_url(
        self,
        base_url: str,
        status: str | None = None,
    ) -> list[CrawlSessionDB]:
        """
        Get sessions by base URL.

        Args:
            base_url: Base URL to filter by
            status: Optional status filter

        Returns:
            List of matching sessions
        """
        query = select(CrawlSessionDB).where(CrawlSessionDB.base_url == base_url)

        if status:
            query = query.where(CrawlSessionDB.status == status)

        query = query.order_by(CrawlSessionDB.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_active_sessions(self) -> list[CrawlSessionDB]:
        """
        Get all active (running) sessions.

        Returns:
            List of active sessions
        """
        result = await self.session.execute(
            select(CrawlSessionDB)
            .where(CrawlSessionDB.status == "running")
            .order_by(CrawlSessionDB.started_at)
        )
        return list(result.scalars().all())

    async def get_recent_sessions(
        self,
        limit: int = 10,
        status: str | None = None,
    ) -> list[CrawlSessionDB]:
        """
        Get recent sessions.

        Args:
            limit: Maximum number of sessions
            status: Optional status filter

        Returns:
            List of recent sessions
        """
        query = select(CrawlSessionDB)

        if status:
            query = query.where(CrawlSessionDB.status == status)

        query = query.order_by(CrawlSessionDB.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_session_statistics(self, session_id: UUID) -> dict | None:
        """
        Get detailed statistics for a session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with statistics or None if session not found
        """
        session = await self.get_by_id(session_id)
        if session is None:
            return None

        duration_seconds = None
        if session.started_at and session.completed_at:
            duration_seconds = (
                session.completed_at - session.started_at
            ).total_seconds()

        success_rate = None
        if session.pages_discovered > 0:
            success_rate = (session.pages_crawled / session.pages_discovered) * 100

        bugs_per_page = None
        if session.pages_crawled > 0:
            bugs_per_page = session.bugs_found / session.pages_crawled

        return {
            "session_id": str(session.id),
            "base_url": session.base_url,
            "status": session.status,
            "pages_discovered": session.pages_discovered,
            "pages_crawled": session.pages_crawled,
            "bugs_found": session.bugs_found,
            "total_cost": float(session.total_cost),
            "duration_seconds": duration_seconds,
            "success_rate": success_rate,
            "bugs_per_page": bugs_per_page,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
        }
