"""Database connection and session management."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from .models import Base


class DatabaseConfig:
    """Database configuration."""

    def __init__(
        self,
        database_url: str | None = None,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
    ):
        """
        Initialize database configuration.

        Args:
            database_url: PostgreSQL connection URL (defaults to env var)
            echo: Whether to log SQL queries
            pool_size: Number of connections to maintain in pool
            max_overflow: Max connections beyond pool_size
            pool_timeout: Timeout for getting connection from pool
            pool_recycle: Recycle connections after this many seconds
            pool_pre_ping: Test connections before using
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Set it with: export DATABASE_URL='postgresql+asyncpg://user:pass@host/db'"
            )
        # Ensure asyncpg driver is used
        if self.database_url.startswith("postgresql://"):
            self.database_url = self.database_url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1
            )
        elif not self.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("Database URL must use postgresql+asyncpg:// driver")

        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping


class Database:
    """Database connection manager."""

    def __init__(self, config: DatabaseConfig | None = None):
        """
        Initialize database connection manager.

        Args:
            config: Database configuration (creates default if None)
        """
        self.config = config or DatabaseConfig()
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def _create_engine(self) -> AsyncEngine:
        """Create async SQLAlchemy engine."""
        # Determine pooling strategy
        if os.getenv("TESTING") == "1":
            # Use NullPool for testing to avoid connection issues
            poolclass = NullPool
            pool_kwargs = {}
        else:
            # Use QueuePool for production with connection pooling
            poolclass = QueuePool
            pool_kwargs = {
                "pool_size": self.config.pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
                "pool_pre_ping": self.config.pool_pre_ping,
            }

        engine = create_async_engine(
            self.config.database_url,
            echo=self.config.echo,
            poolclass=poolclass,
            **pool_kwargs,
            # Performance optimizations
            future=True,
            # Connection arguments for asyncpg
            connect_args={
                "server_settings": {
                    "application_name": "bughive",
                    "jit": "off",  # Disable JIT for faster queries on small datasets
                },
                "command_timeout": 60,  # Query timeout in seconds
                "timeout": 10,  # Connection timeout in seconds
            },
        )

        # Setup connection event listeners
        @event.listens_for(engine.sync_engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Set up connection on connect."""
            # Set statement timeout at connection level
            # dbapi_conn is an asyncpg connection
            pass

        return engine

    @property
    def engine(self) -> AsyncEngine:
        """Get SQLAlchemy engine (lazy initialization)."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get session factory (lazy initialization)."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    async def init_db(self) -> None:
        """Initialize database (create tables)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_db(self) -> None:
        """Drop all database tables (dangerous!)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def close(self) -> None:
        """Close database connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager for database sessions.

        Usage:
            async with db.session() as session:
                result = await session.execute(query)
                await session.commit()
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def get_session(self) -> AsyncSession:
        """
        Get a new database session.

        Note: Caller is responsible for closing the session.
        Prefer using the session() context manager instead.
        """
        return self.session_factory()


# Global database instance
_database: Database | None = None


def get_database(config: DatabaseConfig | None = None) -> Database:
    """
    Get global database instance (singleton).

    Args:
        config: Database configuration (only used on first call)

    Returns:
        Database instance
    """
    global _database
    if _database is None:
        _database = Database(config)
    return _database


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    db = get_database()
    async with db.session() as session:
        yield session


async def init_database(drop_existing: bool = False) -> None:
    """
    Initialize database (create tables).

    Args:
        drop_existing: Whether to drop existing tables first
    """
    db = get_database()
    if drop_existing:
        await db.drop_db()
    await db.init_db()


async def close_database() -> None:
    """Close database connections."""
    global _database
    if _database is not None:
        await _database.close()
        _database = None


# Health check
async def check_database_health() -> bool:
    """
    Check if database is accessible.

    Returns:
        True if database is healthy, False otherwise
    """
    try:
        db = get_database()
        async with db.session() as session:
            await session.execute("SELECT 1")
        return True
    except Exception:
        return False
