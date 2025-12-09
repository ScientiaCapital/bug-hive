"""Database repositories for BugHive."""

from .base import BaseRepository
from .bug import BugRepository
from .page import PageRepository
from .session import CrawlSessionRepository

__all__ = [
    "BaseRepository",
    "CrawlSessionRepository",
    "PageRepository",
    "BugRepository",
]
