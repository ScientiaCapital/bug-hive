# BugHive Database Architecture

## Overview

BugHive uses a PostgreSQL database with SQLAlchemy 2.0 async ORM and asyncpg driver. The architecture follows the Repository pattern for clean separation of concerns.

## Technology Stack

- **Database**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0 (async)
- **Driver**: asyncpg
- **Validation**: Pydantic v2
- **Pattern**: Repository pattern

## Database Schema

### Tables

#### `crawl_sessions`
Stores crawl session metadata and metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| base_url | VARCHAR(2048) | URL being crawled |
| status | VARCHAR(20) | pending, running, completed, failed |
| config | JSONB | Crawl configuration |
| started_at | TIMESTAMP | When crawl started |
| completed_at | TIMESTAMP | When crawl completed |
| pages_discovered | INTEGER | Total pages found |
| pages_crawled | INTEGER | Total pages analyzed |
| bugs_found | INTEGER | Total bugs detected |
| total_cost | DECIMAL(10,4) | Total AI cost (USD) |
| error_message | TEXT | Error if failed |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

**Indexes:**
- `id` (primary key, B-tree)
- `base_url` (B-tree)
- `status` (B-tree)
- `(status, created_at)` (composite)
- `(base_url, status)` (composite)

#### `pages`
Stores individual page crawl results.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_id | UUID | Foreign key to sessions |
| parent_page_id | UUID | Parent page (nullable) |
| url | VARCHAR(2048) | Page URL |
| title | VARCHAR(500) | Page title |
| status | VARCHAR(20) | discovered, crawling, analyzed, error |
| depth | INTEGER | Depth from base URL |
| screenshot_url | VARCHAR(2048) | Screenshot storage URL |
| analysis_result | JSONB | AI analysis output |
| response_time_ms | INTEGER | Page load time |
| status_code | INTEGER | HTTP status code |
| content_type | VARCHAR(255) | Content-Type header |
| content_length | INTEGER | Response size (bytes) |
| error_message | TEXT | Error if failed |
| discovered_at | TIMESTAMP | When page was found |
| crawled_at | TIMESTAMP | When page was analyzed |
| created_at | TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | Last update time |

**Indexes:**
- `id` (primary key, B-tree)
- `session_id` (B-tree)
- `parent_page_id` (B-tree)
- `url` (B-tree)
- `status` (B-tree)
- `depth` (B-tree)
- `status_code` (B-tree)
- `crawled_at` (B-tree)
- `(session_id, status)` (composite)
- `(session_id, depth)` (composite)
- `(url, session_id)` (unique composite)

#### `bugs`
Stores detected bugs and their metadata.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_id | UUID | Foreign key to sessions |
| page_id | UUID | Foreign key to pages |
| category | VARCHAR(50) | ui_ux, data, edge_case, performance, security |
| priority | VARCHAR(20) | critical, high, medium, low |
| title | VARCHAR(255) | Bug title |
| description | TEXT | Detailed description |
| steps_to_reproduce | JSONB | Array of steps |
| evidence | JSONB | Array of evidence objects |
| confidence | FLOAT | AI confidence (0-1) |
| status | VARCHAR(20) | detected, validated, reported, dismissed |
| linear_issue_id | VARCHAR(100) | Linear issue ID |
| linear_issue_url | VARCHAR(500) | Linear issue URL |
| expected_behavior | TEXT | What should happen |
| actual_behavior | TEXT | What actually happens |
| affected_users | VARCHAR(255) | Who is affected |
| browser_info | JSONB | Browser/device info |
| dismissed_reason | TEXT | Why dismissed |
| dismissed_at | TIMESTAMP | When dismissed |
| reported_at | TIMESTAMP | When reported |
| created_at | TIMESTAMP | Bug detection time |
| updated_at | TIMESTAMP | Last update time |

**Indexes:**
- `id` (primary key, B-tree)
- `session_id` (B-tree)
- `page_id` (B-tree)
- `category` (B-tree)
- `priority` (B-tree)
- `title` (B-tree)
- `status` (B-tree)
- `confidence` (B-tree)
- `linear_issue_id` (B-tree)
- `created_at` (B-tree)
- `reported_at` (B-tree)
- `(session_id, priority)` (composite)
- `(session_id, category)` (composite)
- `(session_id, status)` (composite)
- `(page_id, priority)` (composite)

## Architecture Patterns

### Repository Pattern

Each entity has a dedicated repository providing:
- CRUD operations
- Complex queries
- Business logic encapsulation
- Clean separation from ORM details

```python
from src.db import get_database, CrawlSessionRepository

async def example():
    db = get_database()
    async with db.session() as session:
        repo = CrawlSessionRepository(session)
        crawl_session = await repo.create_session(
            base_url="https://example.com",
            config=config
        )
```

### Async/Await Pattern

All database operations are asynchronous using asyncpg:

```python
# Good - async
async with db.session() as session:
    result = await session.execute(query)

# Bad - sync (will not work)
result = session.execute(query)  # ❌
```

### FastAPI Dependency Injection

Use `get_db()` dependency for API endpoints:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_db

@app.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    repo = CrawlSessionRepository(db)
    return await repo.list()
```

## Connection Pooling

### Production Configuration
```python
DatabaseConfig(
    pool_size=5,           # Maintain 5 connections
    max_overflow=10,       # Allow 10 extra on demand
    pool_timeout=30,       # Wait 30s for connection
    pool_recycle=3600,     # Recycle after 1 hour
    pool_pre_ping=True,    # Test connections before use
)
```

### Testing Configuration
```python
# Set TESTING=1 to use NullPool
os.environ["TESTING"] = "1"
```

## Database Initialization

### Create Tables
```python
from src.db import init_database

# Create all tables
await init_database()

# Drop and recreate (dangerous!)
await init_database(drop_existing=True)
```

### Connection Management
```python
from src.db import get_database, close_database

# Get database instance
db = get_database()

# Initialize tables
await db.init_db()

# Close connections on shutdown
await close_database()
```

## Repository Usage Examples

### CrawlSessionRepository

```python
from src.db import CrawlSessionRepository
from src.models import CrawlConfig

repo = CrawlSessionRepository(session)

# Create session
session = await repo.create_session(
    base_url="https://example.com",
    config=CrawlConfig(...)
)

# Start crawling
await repo.start_session(session.id)

# Update metrics
await repo.increment_pages_discovered(session.id, count=5)
await repo.increment_bugs_found(session.id)
await repo.add_cost(session.id, cost=0.05)

# Complete session
await repo.complete_session(session.id, success=True)

# Get statistics
stats = await repo.get_session_statistics(session.id)
```

### PageRepository

```python
from src.db import PageRepository

repo = PageRepository(session)

# Create page
page = await repo.create_page(
    session_id=session_id,
    url="https://example.com/about",
    depth=1,
    parent_page_id=parent_id
)

# Update status
await repo.mark_crawling(page.id)
await repo.mark_analyzed(
    page.id,
    title="About Us",
    screenshot_url="https://...",
    analysis_result={"findings": [...]},
    response_time_ms=234
)

# Get pages to crawl
pages = await repo.get_pages_to_crawl(session_id, limit=10)

# Get analytics
analytics = await repo.get_page_analytics(page.id)
graph = await repo.get_navigation_graph(session_id)
```

### BugRepository

```python
from src.db import BugRepository
from src.models import Evidence

repo = BugRepository(session)

# Create bug
bug = await repo.create_bug(
    session_id=session_id,
    page_id=page_id,
    category="ui_ux",
    priority="high",
    title="Button overlaps text",
    description="On mobile viewports...",
    steps_to_reproduce=["Navigate to /products", "..."],
    evidence=[Evidence(...)],
    confidence=0.92
)

# Report to Linear
await repo.mark_reported(
    bug.id,
    linear_issue_id="BUG-123",
    linear_issue_url="https://linear.app/..."
)

# Query bugs
high_confidence = await repo.get_high_confidence_bugs(
    session_id,
    min_confidence=0.8
)
critical = await repo.get_critical_bugs(session_id)

# Get statistics
stats = await repo.get_bug_statistics(session_id)
```

## Performance Optimizations

### Indexes
- All foreign keys are indexed
- Composite indexes on frequently queried combinations
- Unique index on (url, session_id) for duplicate prevention

### JSONB Columns
- Used for flexible semi-structured data (config, evidence, analysis)
- PostgreSQL provides efficient JSONB querying and indexing
- Consider GIN indexes for large JSONB columns if needed

### Query Optimization
- Use `selectin` loading for relationships to avoid N+1
- Pagination on all list queries
- Connection pooling for high-traffic scenarios

### Monitoring
```python
from src.db import check_database_health

# Health check
is_healthy = await check_database_health()
```

## Migration Strategy

### Initial Setup (Greenfield)
```bash
# Set database URL
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/bughive"

# Run initialization script
python -c "
import asyncio
from src.db import init_database
asyncio.run(init_database())
"
```

### Future Migrations
Use Alembic for schema migrations:

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add new field"

# Apply migration
alembic upgrade head
```

## Security Considerations

### Credentials
- Store credentials in environment variables
- Use `.env` file for local development
- Encrypt sensitive data in `config.credentials` field

### SQL Injection Prevention
- SQLAlchemy ORM prevents SQL injection
- Use parameterized queries for raw SQL
- Validate all user inputs with Pydantic

### Row-Level Security
- Consider PostgreSQL RLS for multi-tenant scenarios
- Currently using application-level filtering by `session_id`

## Testing

### Test Database Setup
```python
import pytest
from src.db import Database, DatabaseConfig

@pytest.fixture
async def db():
    config = DatabaseConfig(
        database_url="postgresql+asyncpg://postgres:postgres@localhost/bughive_test"
    )
    db = Database(config)
    await db.init_db()
    yield db
    await db.drop_db()
    await db.close()

@pytest.fixture
async def session(db):
    async with db.session() as session:
        yield session
```

### Test Example
```python
async def test_create_session(session):
    repo = CrawlSessionRepository(session)
    crawl = await repo.create_session(
        base_url="https://example.com",
        config=CrawlConfig(base_url="https://example.com")
    )
    assert crawl.status == "pending"
    assert crawl.bugs_found == 0
```

## Environment Variables

```bash
# Database connection
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bughive

# Testing mode (uses NullPool)
TESTING=0
```

## Common Patterns

### Transactional Operations
```python
async with db.session() as session:
    repo = BugRepository(session)
    bug = await repo.create_bug(...)
    await repo.mark_validated(bug.id)
    # Commits automatically on context exit
    # Rolls back on exception
```

### Bulk Operations
```python
pages = await repo.bulk_create([
    {"url": "https://example.com/1", "session_id": session_id},
    {"url": "https://example.com/2", "session_id": session_id},
])
```

### Filtering and Pagination
```python
bugs = await repo.get_session_bugs(
    session_id=session_id,
    status="detected",
    priority="critical",
    skip=0,
    limit=20
)
```

## Troubleshooting

### Connection Issues
```python
# Check database health
is_healthy = await check_database_health()

# Verify asyncpg driver
assert "asyncpg" in db.config.database_url
```

### Migration Errors
```bash
# Reset database (development only!)
python -c "
import asyncio
from src.db import init_database
asyncio.run(init_database(drop_existing=True))
"
```

### Performance Issues
- Enable query logging: `DatabaseConfig(echo=True)`
- Monitor connection pool: Check for exhaustion warnings
- Add indexes: Use `EXPLAIN ANALYZE` to identify slow queries
