"""Repository for page operations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import BugDB, PageDB
from .base import BaseRepository


class PageRepository(BaseRepository[PageDB]):
    """Repository for page database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize page repository."""
        super().__init__(PageDB, session)

    async def create_page(
        self,
        session_id: UUID,
        url: str,
        depth: int = 0,
        parent_page_id: UUID | None = None,
        title: str | None = None,
        status: str = "discovered",
    ) -> PageDB:
        """
        Create a new page record.

        Args:
            session_id: Parent session ID
            url: Page URL
            depth: Crawl depth
            parent_page_id: Parent page ID
            title: Page title
            status: Initial status

        Returns:
            Created page
        """
        return await self.create(
            session_id=session_id,
            url=url,
            depth=depth,
            parent_page_id=parent_page_id,
            title=title,
            status=status,
        )

    async def get_by_url(
        self,
        session_id: UUID,
        url: str,
    ) -> PageDB | None:
        """
        Get page by URL within a session.

        Args:
            session_id: Session ID
            url: Page URL

        Returns:
            Page or None if not found
        """
        result = await self.session.execute(
            select(PageDB)
            .where(PageDB.session_id == session_id)
            .where(PageDB.url == url)
        )
        return result.scalars().first()

    async def mark_crawling(self, page_id: UUID) -> PageDB | None:
        """
        Mark page as currently being crawled.

        Args:
            page_id: Page ID

        Returns:
            Updated page or None if not found
        """
        return await self.update(page_id, status="crawling")

    async def mark_analyzed(
        self,
        page_id: UUID,
        title: str | None = None,
        screenshot_url: str | None = None,
        analysis_result: dict | None = None,
        response_time_ms: int | None = None,
        status_code: int | None = None,
        content_type: str | None = None,
        content_length: int | None = None,
    ) -> PageDB | None:
        """
        Mark page as analyzed with results.

        Args:
            page_id: Page ID
            title: Page title
            screenshot_url: Screenshot URL
            analysis_result: AI analysis results
            response_time_ms: Response time
            status_code: HTTP status code
            content_type: Content type
            content_length: Content length

        Returns:
            Updated page or None if not found
        """
        kwargs = {
            "status": "analyzed",
            "crawled_at": datetime.utcnow(),
        }
        if title is not None:
            kwargs["title"] = title
        if screenshot_url is not None:
            kwargs["screenshot_url"] = screenshot_url
        if analysis_result is not None:
            kwargs["analysis_result"] = analysis_result
        if response_time_ms is not None:
            kwargs["response_time_ms"] = response_time_ms
        if status_code is not None:
            kwargs["status_code"] = status_code
        if content_type is not None:
            kwargs["content_type"] = content_type
        if content_length is not None:
            kwargs["content_length"] = content_length

        return await self.update(page_id, **kwargs)

    async def mark_error(
        self,
        page_id: UUID,
        error_message: str,
    ) -> PageDB | None:
        """
        Mark page as error.

        Args:
            page_id: Page ID
            error_message: Error message

        Returns:
            Updated page or None if not found
        """
        return await self.update(
            page_id,
            status="error",
            error_message=error_message,
        )

    async def get_session_pages(
        self,
        session_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[PageDB]:
        """
        Get pages for a session.

        Args:
            session_id: Session ID
            status: Optional status filter
            skip: Number to skip
            limit: Maximum number to return

        Returns:
            List of pages
        """
        query = select(PageDB).where(PageDB.session_id == session_id)

        if status:
            query = query.where(PageDB.status == status)

        query = (
            query.order_by(PageDB.depth, PageDB.discovered_at)
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pages_by_depth(
        self,
        session_id: UUID,
        depth: int,
    ) -> list[PageDB]:
        """
        Get pages at a specific depth.

        Args:
            session_id: Session ID
            depth: Crawl depth

        Returns:
            List of pages at that depth
        """
        result = await self.session.execute(
            select(PageDB)
            .where(PageDB.session_id == session_id)
            .where(PageDB.depth == depth)
            .order_by(PageDB.discovered_at)
        )
        return list(result.scalars().all())

    async def get_pages_to_crawl(
        self,
        session_id: UUID,
        limit: int = 10,
    ) -> list[PageDB]:
        """
        Get pages that need to be crawled.

        Args:
            session_id: Session ID
            limit: Maximum number to return

        Returns:
            List of pages with status 'discovered'
        """
        result = await self.session.execute(
            select(PageDB)
            .where(PageDB.session_id == session_id)
            .where(PageDB.status == "discovered")
            .order_by(PageDB.depth, PageDB.discovered_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_status(
        self,
        session_id: UUID,
    ) -> dict[str, int]:
        """
        Count pages by status.

        Args:
            session_id: Session ID

        Returns:
            Dictionary of status -> count
        """
        result = await self.session.execute(
            select(PageDB.status, func.count(PageDB.id))
            .where(PageDB.session_id == session_id)
            .group_by(PageDB.status)
        )

        return dict(result.all())

    async def count_by_depth(
        self,
        session_id: UUID,
    ) -> dict[int, int]:
        """
        Count pages by depth.

        Args:
            session_id: Session ID

        Returns:
            Dictionary of depth -> count
        """
        result = await self.session.execute(
            select(PageDB.depth, func.count(PageDB.id))
            .where(PageDB.session_id == session_id)
            .group_by(PageDB.depth)
            .order_by(PageDB.depth)
        )

        return dict(result.all())

    async def get_page_analytics(
        self,
        page_id: UUID,
    ) -> dict | None:
        """
        Get analytics for a specific page.

        Args:
            page_id: Page ID

        Returns:
            Dictionary with page analytics or None if not found
        """
        page = await self.get_by_id(page_id)
        if page is None:
            return None

        # Count bugs by priority
        bug_priority_query = await self.session.execute(
            select(BugDB.priority, func.count(BugDB.id))
            .where(BugDB.page_id == page_id)
            .group_by(BugDB.priority)
        )
        bug_severity_distribution = dict(bug_priority_query.all())

        # Count bugs by category
        bug_category_query = await self.session.execute(
            select(BugDB.category, func.count(BugDB.id))
            .where(BugDB.page_id == page_id)
            .group_by(BugDB.category)
        )
        bug_category_distribution = dict(bug_category_query.all())

        # Total bugs
        total_bugs_result = await self.session.execute(
            select(func.count(BugDB.id)).where(BugDB.page_id == page_id)
        )
        total_bugs = total_bugs_result.scalar_one()

        return {
            "page_id": str(page.id),
            "url": page.url,
            "bugs_found": total_bugs,
            "bug_severity_distribution": bug_severity_distribution,
            "bug_category_distribution": bug_category_distribution,
            "response_time_ms": page.response_time_ms,
            "status_code": page.status_code,
            "crawled_at": page.crawled_at,
        }

    async def get_navigation_graph(
        self,
        session_id: UUID,
    ) -> dict[str, list[str]]:
        """
        Build navigation graph of parent -> children relationships.

        Args:
            session_id: Session ID

        Returns:
            Dictionary mapping parent URL to list of child URLs
        """
        pages = await self.get_session_pages(session_id, limit=10000)

        # Build URL lookup
        url_by_id = {str(page.id): page.url for page in pages}

        # Build graph
        graph: dict[str, list[str]] = {}
        for page in pages:
            if page.parent_page_id:
                parent_url = url_by_id.get(str(page.parent_page_id))
                if parent_url:
                    if parent_url not in graph:
                        graph[parent_url] = []
                    graph[parent_url].append(page.url)

        return graph

    async def get_average_response_time(
        self,
        session_id: UUID,
    ) -> float | None:
        """
        Get average response time for session pages.

        Args:
            session_id: Session ID

        Returns:
            Average response time in milliseconds or None
        """
        result = await self.session.execute(
            select(func.avg(PageDB.response_time_ms))
            .where(PageDB.session_id == session_id)
            .where(PageDB.response_time_ms.isnot(None))
        )
        avg_time = result.scalar_one_or_none()
        return float(avg_time) if avg_time is not None else None

    async def get_total_content_size(
        self,
        session_id: UUID,
    ) -> int | None:
        """
        Get total content size for session pages.

        Args:
            session_id: Session ID

        Returns:
            Total content size in bytes or None
        """
        result = await self.session.execute(
            select(func.sum(PageDB.content_length))
            .where(PageDB.session_id == session_id)
            .where(PageDB.content_length.isnot(None))
        )
        total = result.scalar_one_or_none()
        return int(total) if total is not None else None
