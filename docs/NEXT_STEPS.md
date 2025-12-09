# BugHive - Next Steps

## Wave 1: Infrastructure ✅ COMPLETE

- ✅ Project setup with modern Python tooling
- ✅ Pydantic models for all data structures
- ✅ Configuration management with environment variables
- ✅ LLM router infrastructure
- ✅ **Browser automation layer (Task 4)**

## Current State: Ready for Wave 2

### What's Complete

#### Core Infrastructure
- **Settings Management** (`src/core/config.py`)
  - Environment-based configuration
  - Pydantic validation
  - No hardcoded secrets

- **Data Models** (`src/models/`)
  - `Page` - Crawled page representation
  - `Bug` - Bug report structure
  - `Evidence` - Supporting evidence types
  - `Crawl` - Crawl session metadata

- **LLM Integration** (`src/llm/`)
  - Router for multiple providers
  - Anthropic Claude support
  - OpenRouter support
  - **NO OpenAI** (per project requirements)

- **Browser Automation** (`src/browser/`) ✅ NEW
  - `BrowserbaseClient` - Session management
  - `PageExtractor` - Data extraction
  - `Navigator` - Human-like interactions
  - Anti-detection features
  - Session rotation
  - Comprehensive testing (51 tests)

### What's Next: Wave 2 - Crawler Implementation

#### Task 5: Core Crawler Engine
**Priority: HIGH**

Create `src/crawler/engine.py`:
```python
class CrawlEngine:
    """Orchestrates page crawling workflow."""

    async def crawl_page(self, url: str) -> Page:
        """Crawl single page and extract data."""
        # 1. Create browser session
        # 2. Navigate and extract data
        # 3. Capture evidence
        # 4. Store to database

    async def crawl_site(self, base_url: str, max_depth: int = 3) -> list[Page]:
        """Crawl entire site breadth-first."""
        # 1. Queue management
        # 2. Duplicate detection
        # 3. Session rotation
        # 4. Parallel crawling
```

**Dependencies:**
- Browser module ✅ (complete)
- Database setup (pending)
- Redis for queue (pending)

**Files to create:**
- `src/crawler/__init__.py`
- `src/crawler/engine.py`
- `src/crawler/queue.py`
- `src/crawler/deduplicator.py`
- `tests/crawler/test_engine.py`

---

#### Task 6: Database Layer
**Priority: HIGH**

Setup PostgreSQL with async SQLAlchemy:

```python
# src/db/models.py
class PageModel(Base):
    """SQLAlchemy model for pages table."""
    __tablename__ = "pages"

    id = Column(UUID, primary_key=True)
    session_id = Column(UUID, ForeignKey("crawl_sessions.id"))
    url = Column(String, nullable=False)
    # ... rest of fields

# src/db/repositories/page.py
class PageRepository:
    """Repository for page CRUD operations."""

    async def create(self, page: PageCreate) -> Page:
        """Create new page record."""

    async def get_by_url(self, url: str) -> Page | None:
        """Get page by URL."""
```

**Files to create:**
- `src/db/__init__.py`
- `src/db/base.py` - Database connection
- `src/db/models.py` - SQLAlchemy models
- `src/db/repositories/page.py`
- `src/db/repositories/bug.py`
- `src/db/repositories/crawl.py`
- `alembic/` - Database migrations

**Dependencies:**
- PostgreSQL running locally or in Docker
- Alembic for migrations

---

#### Task 7: Evidence Storage
**Priority: MEDIUM**

Screenshot and artifact storage:

```python
# src/storage/screenshot.py
class ScreenshotStorage:
    """Manages screenshot uploads and retrieval."""

    async def upload(self, screenshot_bytes: bytes, page_id: str) -> str:
        """Upload screenshot and return URL."""
        # S3, Cloudflare R2, or local filesystem

    async def get(self, url: str) -> bytes:
        """Retrieve screenshot by URL."""
```

**Options:**
- Local filesystem (dev)
- AWS S3 (production)
- Cloudflare R2 (cost-effective)

**Files to create:**
- `src/storage/__init__.py`
- `src/storage/screenshot.py`
- `src/storage/artifact.py`

---

#### Task 8: Bug Detection Agent
**Priority: MEDIUM**

LangGraph agent for analyzing extracted data:

```python
# src/agents/bug_detector.py
class BugDetectorAgent:
    """LangGraph agent for detecting bugs from page data."""

    async def analyze_page(self, page_data: dict) -> list[Bug]:
        """Analyze page data and detect bugs."""
        # 1. Console error analysis
        # 2. Network failure detection
        # 3. Performance issues
        # 4. UI/UX problems
```

**LangGraph Workflow:**
1. **Console Analysis Node** - Parse console errors
2. **Network Analysis Node** - Detect failed requests
3. **Performance Node** - Check metrics
4. **Visual Analysis Node** - Screenshot comparison
5. **Synthesis Node** - Generate bug reports

**Files to create:**
- `src/agents/__init__.py`
- `src/agents/bug_detector.py`
- `src/agents/nodes/console_analyzer.py`
- `src/agents/nodes/network_analyzer.py`
- `src/agents/workflows/detection.py`

---

### Wave 3: API & UI (Future)

#### Task 9: FastAPI Backend
- REST API for crawl management
- WebSocket for real-time updates
- API endpoints for bug reports

#### Task 10: Frontend Dashboard
- React/Next.js dashboard
- Crawl session management
- Bug report viewing
- Screenshot gallery

---

## Immediate Next Actions

### 1. Database Setup (Do This First)

```bash
# Install PostgreSQL
brew install postgresql@16  # macOS
# or
sudo apt install postgresql  # Ubuntu

# Start PostgreSQL
brew services start postgresql

# Create database
createdb bughive_dev

# Run migrations (after Task 6)
alembic upgrade head
```

### 2. Redis Setup

```bash
# Install Redis
brew install redis  # macOS

# Start Redis
brew services start redis

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

### 3. Environment Variables

Update `.env`:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bughive_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# Browser (already configured)
BROWSERBASE_API_KEY=your-key
BROWSERBASE_PROJECT_ID=your-project

# LLM (already configured)
ANTHROPIC_API_KEY=your-key
OPENROUTER_API_KEY=your-key
```

### 4. Test Browser Module

```bash
# Install dependencies
pip install -e .
playwright install chromium

# Run tests
pytest tests/browser/ -v

# Try demo (requires Browserbase credentials)
export BROWSERBASE_API_KEY=your-key
export BROWSERBASE_PROJECT_ID=your-project
python examples/browser_demo.py
```

---

## Development Workflow

### For Each New Task:

1. **Read Requirements**
   - Review task description
   - Check dependencies
   - Verify prerequisites

2. **Create Files**
   - Follow existing patterns
   - Use type hints
   - Add docstrings
   - Include examples

3. **Write Tests**
   - Unit tests with mocks
   - Integration tests (optional)
   - Aim for >90% coverage

4. **Update Docs**
   - README for each module
   - Integration guides
   - API documentation

5. **Run Checks**
   ```bash
   # Type checking
   mypy src/

   # Linting
   ruff check src/

   # Formatting
   ruff format src/

   # Tests
   pytest tests/ -v --cov=src
   ```

---

## Project Conventions

### File Organization
```
src/
├── module_name/
│   ├── __init__.py       # Public API exports
│   ├── main_class.py     # Main implementation
│   ├── helpers.py        # Utility functions
│   └── README.md         # Module documentation
```

### Testing
```
tests/
├── module_name/
│   ├── __init__.py
│   ├── test_main_class.py
│   └── test_helpers.py
```

### Documentation
```
docs/
├── MODULE_NAME.md        # Module overview
├── integration_guide.md  # How to use
└── TASK_XX_COMPLETE.md   # Completion report
```

---

## Code Quality Standards

### Type Hints
```python
def process_page(url: str, depth: int = 0) -> Page:
    """Process page at URL with specified depth."""
    ...
```

### Docstrings
```python
def method_name(arg: str) -> dict:
    """Short description.

    Longer description if needed.

    Args:
        arg: Description of argument

    Returns:
        dict: Description of return value

    Raises:
        ValueError: When and why
    """
```

### Error Handling
```python
try:
    result = await risky_operation()
except SpecificError as e:
    logger.error("operation_failed", error=str(e))
    raise CustomError(f"Failed to process: {e}") from e
```

### Logging
```python
logger.info(
    "event_name",
    url=url,
    status="success",
    duration_ms=123,
)
```

---

## Resources

### Documentation
- [Playwright Docs](https://playwright.dev/python/)
- [Browserbase Docs](https://docs.browserbase.com/)
- [Pydantic Docs](https://docs.pydantic.dev/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)

### Examples
- `examples/browser_demo.py` - Browser automation
- `docs/browser_integration_guide.md` - Integration patterns
- `tests/browser/` - Testing examples

---

## Support

### Getting Help
1. Check module README files
2. Review integration guides
3. Look at test files for examples
4. Check existing implementations

### Common Issues

**Browser not connecting:**
- Check Browserbase API key
- Verify project ID
- Check network connectivity

**Database errors:**
- Ensure PostgreSQL is running
- Check connection string
- Run migrations

**Import errors:**
- Install with `pip install -e .`
- Check Python version (3.12+)

---

## Summary

✅ **Wave 1 Complete** - Infrastructure ready
🚀 **Next: Wave 2** - Crawler implementation
📋 **Priority Order:**
1. Task 6: Database Layer
2. Task 5: Crawler Engine
3. Task 7: Evidence Storage
4. Task 8: Bug Detection Agent

The foundation is solid. Time to build the crawler! 🐝
