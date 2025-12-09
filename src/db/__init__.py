"""Database layer for BugHive."""

from .database import (
    Database,
    DatabaseConfig,
    check_database_health,
    close_database,
    get_database,
    get_db,
    init_database,
)
from .models import Base, BugDB, CrawlSessionDB, PageDB
from .repositories import (
    BaseRepository,
    BugRepository,
    CrawlSessionRepository,
    PageRepository,
)

__all__ = [
    # Database connection
    "Database",
    "DatabaseConfig",
    "get_database",
    "get_db",
    "init_database",
    "close_database",
    "check_database_health",
    # ORM Models
    "Base",
    "CrawlSessionDB",
    "PageDB",
    "BugDB",
    # Repositories
    "BaseRepository",
    "CrawlSessionRepository",
    "PageRepository",
    "BugRepository",
]
