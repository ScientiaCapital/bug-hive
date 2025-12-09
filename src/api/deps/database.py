"""Database dependency providers."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_db as get_db_session
from ...db.repositories.bug import BugRepository
from ...db.repositories.page import PageRepository
from ...db.repositories.session import CrawlSessionRepository


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session dependency.

    Usage:
        @router.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
    """
    async for session in get_db_session():
        yield session


async def get_session_repo(
    db: AsyncSession = Depends(get_db)
) -> CrawlSessionRepository:
    """
    Get crawl session repository dependency.

    Usage:
        @router.get("/sessions")
        async def endpoint(repo: CrawlSessionRepository = Depends(get_session_repo)):
            ...
    """
    return CrawlSessionRepository(db)


async def get_bug_repo(
    db: AsyncSession = Depends(get_db)
) -> BugRepository:
    """
    Get bug repository dependency.

    Usage:
        @router.get("/bugs")
        async def endpoint(repo: BugRepository = Depends(get_bug_repo)):
            ...
    """
    return BugRepository(db)


async def get_page_repo(
    db: AsyncSession = Depends(get_db)
) -> PageRepository:
    """
    Get page repository dependency.

    Usage:
        @router.get("/pages")
        async def endpoint(repo: PageRepository = Depends(get_page_repo)):
            ...
    """
    return PageRepository(db)


# Type aliases for cleaner dependency injection
SessionRepoDep = Annotated[CrawlSessionRepository, Depends(get_session_repo)]
BugRepoDep = Annotated[BugRepository, Depends(get_bug_repo)]
PageRepoDep = Annotated[PageRepository, Depends(get_page_repo)]
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
