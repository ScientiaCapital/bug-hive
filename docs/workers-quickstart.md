# Workers Quickstart Guide

Quick reference for working with BugHive Celery workers.

## Quick Start

### 1. Install Dependencies
```bash
pip install celery[redis] redis flower
```

### 2. Start Redis
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using Homebrew (macOS)
brew services start redis
```

### 3. Start Worker
```bash
./scripts/run_worker.sh
```

### 4. Start Beat (Optional - for periodic tasks)
```bash
./scripts/run_beat.sh
```

### 5. Start Flower (Optional - monitoring UI)
```bash
./scripts/run_flower.sh
# Access at http://localhost:5555
```

## Common Commands

### Check Worker Status
```bash
celery -A src.workers.celery_app inspect active
```

### Check Queue Length
```bash
celery -A src.workers.celery_app inspect active_queues
```

### Purge All Tasks (Careful!)
```bash
celery -A src.workers.celery_app purge
```

### Cancel a Task
```python
from src.workers.celery_app import celery_app

celery_app.control.revoke(
    "task-id-here",
    terminate=True
)
```

## Testing Tasks

### Run a Test Crawl
```python
from src.workers.tasks import run_crawl_session

task = run_crawl_session.delay(
    session_id="test-session-123",
    config={
        "base_url": "https://example.com",
        "max_pages": 5,
        "max_depth": 2
    }
)

print(f"Task ID: {task.id}")
print(f"Status: {task.status}")

# Wait for result (blocking)
result = task.get(timeout=300)
print(result)
```

### Check Session State
```python
from src.workers.session_manager import SessionManager

manager = SessionManager()
state = manager.get_session_state("test-session-123")
print(state)
```

### Create Linear Ticket
```python
from src.workers.tasks import create_linear_ticket

task = create_linear_ticket.delay(
    bug_id="bug-123",
    report={
        "title": "Test Bug",
        "description": "This is a test bug",
        "priority": 3,
        "labels": ["test", "automated"]
    },
    team_id="your-team-id"
)

result = task.get()
print(f"Linear URL: {result['linear_url']}")
```

## Development Mode

### Auto-reload Worker
```bash
celery -A src.workers.celery_app worker \
    --loglevel=debug \
    --concurrency=1 \
    --autoreload
```

### Run Task Synchronously (for debugging)
```python
# Instead of .delay()
result = run_crawl_session.apply(
    args=[session_id, config],
    throw=True  # Raise exceptions immediately
)
```

## Troubleshooting

### Worker Can't Connect to Redis
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG

# Check environment variable
echo $REDIS_URL
```

### Task Stuck in "PENDING"
- Worker not running or crashed
- Task routed to wrong queue
- Connection to broker lost

```bash
# Check worker status
celery -A src.workers.celery_app inspect ping
```

### Memory Issues
- Enable worker recycling: `--max-tasks-per-child=50`
- Reduce concurrency: `--concurrency=1`
- Monitor with Flower

### Task Timeout
- Increase time limits in `celery_app.py`
- Or use `task.apply_async(time_limit=7200)`

## Environment Variables

Required in `.env`:
```bash
# Redis (required)
REDIS_URL=redis://localhost:6379/0

# Database (for crawl tasks)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/bughive

# Browser automation (for crawl tasks)
BROWSERBASE_API_KEY=your-key
BROWSERBASE_PROJECT_ID=your-project

# AI (for crawl tasks)
ANTHROPIC_API_KEY=your-key

# Linear (for ticket tasks)
LINEAR_API_KEY=your-key
```

## Production Checklist

- [ ] Redis persistence enabled
- [ ] Worker auto-restart configured (systemd/supervisor)
- [ ] Beat scheduler running (for periodic tasks)
- [ ] Monitoring setup (Flower or other APM)
- [ ] Logging configured (JSON to stdout)
- [ ] Error alerting configured
- [ ] Resource limits set (memory, CPU)
- [ ] Task result expiration configured

## Useful Resources

- Flower UI: http://localhost:5555
- Celery Docs: https://docs.celeryq.dev/
- Workers README: /src/workers/README.md
