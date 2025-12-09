# Database Quick Start Guide

## Prerequisites

```bash
# Install PostgreSQL
brew install postgresql@14  # macOS
# or
sudo apt-get install postgresql-14  # Ubuntu

# Install Python dependencies
pip install sqlalchemy[asyncio] asyncpg pydantic
```

## Setup Database

### 1. Create Database
```bash
# Start PostgreSQL
brew services start postgresql@14

# Create database
createdb bughive

# Or with custom user
createdb -U postgres bughive
```

### 2. Configure Connection
```bash
# Create .env file
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bughive
EOF
```

### 3. Initialize Schema
```python
# init_db.py
import asyncio
from src.db import init_database

async def main():
    await init_database()
    print("Database initialized successfully!")

asyncio.run(main())
```

```bash
python init_db.py
```

## Basic Usage

### Complete Example
```python
import asyncio
from uuid import uuid4
from src.db import get_database, CrawlSessionRepository, PageRepository, BugRepository
from src.models import CrawlConfig, Evidence

async def main():
    # Get database instance
    db = get_database()

    # Use session context manager
    async with db.session() as session:
        # Initialize repositories
        session_repo = CrawlSessionRepository(session)
        page_repo = PageRepository(session)
        bug_repo = BugRepository(session)

        # 1. Create crawl session
        config = CrawlConfig(
            base_url="https://example.com",
            auth_method="none",
            max_pages=50,
            max_depth=3
        )

        crawl = await session_repo.create_session(
            base_url="https://example.com",
            config=config
        )
        print(f"Created session: {crawl.id}")

        # 2. Start crawling
        await session_repo.start_session(crawl.id)

        # 3. Create page
        page = await page_repo.create_page(
            session_id=crawl.id,
            url="https://example.com/products",
            depth=1,
            title="Products"
        )
        print(f"Created page: {page.url}")

        # 4. Create bug
        bug = await bug_repo.create_bug(
            session_id=crawl.id,
            page_id=page.id,
            category="ui_ux",
            priority="high",
            title="Button overlaps text",
            description="Submit button overlaps form label on mobile",
            steps_to_reproduce=[
                "Navigate to /products",
                "Resize to 375px",
                "Observe overlap"
            ],
            evidence=[
                Evidence(
                    type="screenshot",
                    content="https://storage.example.com/screenshot.png",
                    timestamp=datetime.utcnow()
                )
            ],
            confidence=0.92
        )
        print(f"Created bug: {bug.title}")

        # 5. Update metrics
        await session_repo.update_metrics(
            crawl.id,
            pages_discovered=1,
            pages_crawled=1,
            bugs_found=1,
            total_cost=0.05
        )

        # 6. Complete session
        await session_repo.complete_session(crawl.id, success=True)

        # 7. Get statistics
        stats = await session_repo.get_session_statistics(crawl.id)
        print(f"Stats: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Common Operations

### Create Session
```python
from src.db import CrawlSessionRepository
from src.models import CrawlConfig

config = CrawlConfig(
    base_url="https://example.com",
    max_pages=100,
    max_depth=5
)

session = await session_repo.create_session(
    base_url="https://example.com",
    config=config
)
```

### Track Progress
```python
# Increment counters
await session_repo.increment_pages_discovered(session_id)
await session_repo.increment_pages_crawled(session_id)
await session_repo.increment_bugs_found(session_id)

# Add costs
await session_repo.add_cost(session_id, cost=0.05)
```

### Query Bugs
```python
# High confidence bugs
bugs = await bug_repo.get_high_confidence_bugs(
    session_id,
    min_confidence=0.9
)

# Critical bugs
critical = await bug_repo.get_critical_bugs(session_id)

# Unreported bugs
unreported = await bug_repo.get_unreported_bugs(
    session_id,
    min_priority="high"
)
```

### Report to Linear
```python
await bug_repo.mark_reported(
    bug_id,
    linear_issue_id="BUG-123",
    linear_issue_url="https://linear.app/team/issue/BUG-123"
)
```

## FastAPI Integration

### Setup
```python
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_db, init_database, close_database

app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_database()

@app.on_event("shutdown")
async def shutdown():
    await close_database()
```

### Endpoints
```python
from src.db import CrawlSessionRepository
from src.models import CrawlConfig

@app.post("/sessions")
async def create_session(
    config: CrawlConfig,
    db: AsyncSession = Depends(get_db)
):
    repo = CrawlSessionRepository(db)
    session = await repo.create_session(
        base_url=config.base_url,
        config=config
    )
    return session

@app.get("/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    repo = CrawlSessionRepository(db)
    session = await repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404)
    return session

@app.get("/sessions/{session_id}/bugs")
async def get_session_bugs(
    session_id: UUID,
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    repo = BugRepository(db)
    bugs = await repo.get_session_bugs(
        session_id,
        priority=priority
    )
    return bugs
```

## Testing

### Test Database Setup
```python
import pytest
from src.db import Database, DatabaseConfig

@pytest.fixture
async def test_db():
    """Provide clean test database."""
    config = DatabaseConfig(
        database_url="postgresql+asyncpg://postgres:postgres@localhost/bughive_test"
    )
    db = Database(config)
    await db.init_db()
    yield db
    await db.drop_db()
    await db.close()

@pytest.fixture
async def db_session(test_db):
    """Provide database session for tests."""
    async with test_db.session() as session:
        yield session
```

### Test Example
```python
async def test_create_session(db_session):
    repo = CrawlSessionRepository(db_session)

    config = CrawlConfig(base_url="https://example.com")
    session = await repo.create_session(
        base_url="https://example.com",
        config=config
    )

    assert session.status == "pending"
    assert session.bugs_found == 0
    assert session.pages_crawled == 0
```

## Troubleshooting

### Connection Refused
```bash
# Check if PostgreSQL is running
pg_isready

# Start PostgreSQL
brew services start postgresql@14
```

### Database Doesn't Exist
```bash
# Create database
createdb bughive

# Or with specific user
createdb -U postgres bughive
```

### Wrong Driver
```python
# ❌ Wrong
DATABASE_URL=postgresql://localhost/bughive

# ✅ Correct
DATABASE_URL=postgresql+asyncpg://localhost/bughive
```

### Permission Denied
```bash
# Grant permissions
psql -d bughive -c "GRANT ALL PRIVILEGES ON DATABASE bughive TO your_user;"
```

### Reset Database (Development)
```python
import asyncio
from src.db import init_database

async def reset():
    await init_database(drop_existing=True)
    print("Database reset complete!")

asyncio.run(reset())
```

## Performance Tips

### Connection Pooling
```python
from src.db import DatabaseConfig, get_database

config = DatabaseConfig(
    pool_size=10,          # Connections to maintain
    max_overflow=20,       # Extra connections allowed
    pool_timeout=30,       # Wait 30s for connection
    pool_recycle=3600,     # Recycle after 1 hour
    pool_pre_ping=True     # Test connections before use
)

db = get_database(config)
```

### Query Optimization
```python
# ❌ Bad: N+1 queries
session = await session_repo.get_by_id(session_id)
for page in session.pages:
    bugs = await bug_repo.get_page_bugs(page.id)

# ✅ Good: Single query with joins
from sqlalchemy import select
from sqlalchemy.orm import selectinload

result = await session.execute(
    select(CrawlSessionDB)
    .options(selectinload(CrawlSessionDB.pages).selectinload(PageDB.bugs))
    .where(CrawlSessionDB.id == session_id)
)
session = result.scalars().first()
```

### Batch Operations
```python
# ❌ Bad: One-by-one
for url in urls:
    await page_repo.create_page(session_id=session_id, url=url)

# ✅ Good: Bulk insert
pages = [{"session_id": session_id, "url": url} for url in urls]
await page_repo.bulk_create(pages)
```

## Monitoring

### Check Database Health
```python
from src.db import check_database_health

is_healthy = await check_database_health()
print(f"Database healthy: {is_healthy}")
```

### Enable Query Logging
```python
from src.db import DatabaseConfig

config = DatabaseConfig(echo=True)  # Log all SQL queries
```

### Monitor Connection Pool
```python
engine = db.engine
print(f"Pool size: {engine.pool.size()}")
print(f"Checked out: {engine.pool.checkedout()}")
```

## Next Steps

1. **Read the full docs**: `src/db/README.md`
2. **Run the example**: `python src/db/example_usage.py`
3. **Review the schema**: `docs/database-schema.md`
4. **Understand the architecture**: `docs/database-architecture.md`
5. **Write tests**: See testing section above

## Quick Reference

### Import Statements
```python
from src.db import (
    get_database,
    get_db,
    init_database,
    close_database,
    CrawlSessionRepository,
    PageRepository,
    BugRepository,
)

from src.models import (
    CrawlConfig,
    CrawlSession,
    Page,
    Bug,
    Evidence,
)
```

### Common Patterns
```python
# Session context manager
async with db.session() as session:
    repo = CrawlSessionRepository(session)
    result = await repo.create(...)
    # Auto-commits on exit, rolls back on exception

# FastAPI dependency
@app.get("/items")
async def get_items(db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    return await repo.list()

# Transaction management
async with db.session() as session:
    try:
        await repo.create(...)
        await repo.update(...)
        await session.commit()  # Explicit commit
    except Exception:
        await session.rollback()  # Explicit rollback
        raise
```

## Environment Variables

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/dbname

# Optional
TESTING=1  # Use NullPool for tests
```

## Help & Support

- **Documentation**: `src/db/README.md`
- **Examples**: `src/db/example_usage.py`
- **Schema**: `docs/database-schema.md`
- **Architecture**: `docs/database-architecture.md`
