"""FastAPI dependencies."""

from .auth import verify_api_key
from .database import get_bug_repo, get_db, get_page_repo, get_session_repo

__all__ = [
    "verify_api_key",
    "get_db",
    "get_bug_repo",
    "get_page_repo",
    "get_session_repo",
]
