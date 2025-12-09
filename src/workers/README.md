# BugHive Workers

Background task processing using Celery for BugHive autonomous QA agent system.

## Overview

The workers module handles asynchronous, resource-intensive tasks:
- **Crawl execution**: Run LangGraph workflows in the background
- **Ticket creation**: Create Linear issues without blocking API
- **Screenshot uploads**: Handle media uploads asynchronously
- **Periodic cleanup**: Daily maintenance tasks

## Architecture

```
┌─────────────────┐
│   FastAPI API   │ ───► Queue tasks
└─────────────────┘
         │
         ▼
┌─────────────────┐
│      Redis      │ ◄──► Task queue & state
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  Celery Worker  │ ───► Process tasks
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  LangGraph      │ ───► Execute crawls
└─────────────────┘
```

## Components

### 1. celery_app.py
Celery application configuration:
- Task serialization (JSON)
- Worker concurrency (max 2)
- Task routing to queues
- Periodic task schedule (Beat)

### 2. tasks.py
Task definitions:
- `run_crawl_session`: Execute full crawl workflow
- `create_linear_ticket`: Create bug tickets
- `upload_screenshot`: Upload media to storage
- `cleanup_old_sessions`: Periodic cleanup

### 3. session_manager.py
Redis-based session state management:
- Real-time progress tracking
- Session status updates
- Error tracking
- 24-hour TTL for auto-cleanup

## Task Queues

| Queue    | Purpose              | Concurrency | Priority |
|----------|---------------------|-------------|----------|
| crawl    | Heavy crawl tasks   | 2           | High     |
| tickets  | Linear integration  | 4           | Medium   |
| media    | Screenshot uploads  | 8           | Low      |
| default  | Misc/cleanup tasks  | 2           | Low      |

## Usage

### Starting Workers

```bash
# Start the main worker
./scripts/run_worker.sh

# Start Beat scheduler (in separate terminal)
./scripts/run_beat.sh

# Start Flower monitoring UI (optional)
./scripts/run_flower.sh
```

### Queuing Tasks

```python
from src.workers.tasks import run_crawl_session

# Queue a crawl
task = run_crawl_session.delay(
    session_id="uuid-here",
    config={
        "base_url": "https://example.com",
        "max_pages": 10,
        "max_depth": 3
    }
)

print(f"Task queued: {task.id}")
```

### Monitoring Progress

```python
from src.workers.session_manager import SessionManager

manager = SessionManager()
state = manager.get_session_state(session_id)

print(f"Status: {state['status']}")
print(f"Pages crawled: {state['pages_crawled']}")
print(f"Bugs found: {state['bugs_found']}")
```

## Task Lifecycle

1. **Queued**: Task added to Redis queue
2. **Starting**: Worker picks up task
3. **Running**: Task executing (status updates in Redis)
4. **Completed**: Task finished successfully
5. **Failed**: Task failed (with error message)

## Configuration

Environment variables (in `.env`):

```bash
# Required
REDIS_URL=redis://localhost:6379/0

# Optional (defaults to REDIS_URL if not set)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## Task Retry Logic

### run_crawl_session
- Max retries: 3
- Retry delay: 60 seconds
- Exponential backoff with jitter
- Hard timeout: 1 hour
- Soft timeout: 50 minutes

### create_linear_ticket
- Max retries: 5
- Retry delay: 30 seconds
- Exponential backoff

### upload_screenshot
- Max retries: 3
- Default retry delay

## Monitoring

### Flower Web UI

Access at `http://localhost:5555`:
- Real-time task monitoring
- Worker status and health
- Task history and results
- Queue statistics

```bash
./scripts/run_flower.sh
```

### Logs

Workers use structlog for JSON logging:

```json
{
  "event": "Starting crawl session",
  "session_id": "abc-123",
  "task_id": "xyz-789",
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info"
}
```

### Redis Keys

Session state is stored in Redis:

```
bughive:session:{session_id} → JSON state (24h TTL)
```

## Error Handling

### Transient Errors
Automatically retried with exponential backoff:
- Network errors
- Browser crashes
- API rate limits

### Permanent Errors
Not retried:
- Invalid configuration
- Authentication failures
- Resource not found

### Task Cancellation
Stop a running task:

```python
from src.workers.celery_app import celery_app

celery_app.control.revoke(
    task_id,
    terminate=True,
    signal="SIGTERM"
)
```

## Periodic Tasks

Configured in `celery_app.py`:

| Task                    | Schedule        | Purpose                |
|------------------------|-----------------|------------------------|
| cleanup_old_sessions   | Daily at 3 AM   | Delete old Redis data  |

## Best Practices

### Task Design
- Keep tasks **idempotent** (safe to retry)
- Use **JSON-serializable** arguments only
- **Update state** frequently for progress tracking
- **Log errors** with context for debugging

### Worker Scaling
- Run **1 worker per server** for heavy crawls
- Increase concurrency for light tasks (tickets, uploads)
- Use **separate workers** for different queues
- Monitor **memory usage** (restart workers if needed)

### Development
```bash
# Run worker with auto-reload (development only)
celery -A src.workers.celery_app worker \
    --loglevel=debug \
    --concurrency=1 \
    --autoreload
```

## Production Deployment

### Docker Compose

```yaml
version: '3.8'

services:
  worker:
    build: .
    command: ./scripts/run_worker.sh
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://...
    depends_on:
      - redis
      - postgres

  beat:
    build: .
    command: ./scripts/run_beat.sh
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

### Systemd Service

```ini
[Unit]
Description=BugHive Celery Worker
After=redis.service

[Service]
Type=simple
User=bughive
WorkingDirectory=/opt/bughive
ExecStart=/opt/bughive/scripts/run_worker.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Worker won't start
```bash
# Check Redis connection
redis-cli ping

# Check environment variables
env | grep REDIS_URL

# Check worker logs
celery -A src.workers.celery_app inspect active
```

### Tasks stuck in queue
```bash
# Check worker status
celery -A src.workers.celery_app inspect stats

# Purge queue (careful!)
celery -A src.workers.celery_app purge
```

### Memory leaks
```bash
# Enable worker process recycling
celery -A src.workers.celery_app worker \
    --max-tasks-per-child=50
```

## Dependencies

Required packages:
- `celery[redis]>=5.3.0` - Task queue
- `redis>=5.0.0` - State management
- `flower>=2.0.0` - Monitoring UI (optional)

Install:
```bash
pip install -r requirements.txt
```

## API Integration

The workers are integrated into the FastAPI app:

```python
# src/api/routes/crawl.py
from src.workers.tasks import run_crawl_session

@router.post("/start")
async def start_crawl(...):
    # Create session in DB
    session = await session_repo.create(...)

    # Queue task
    task = run_crawl_session.delay(
        str(session.id),
        config.model_dump()
    )

    return {"session_id": session.id, "task_id": task.id}
```

## Further Reading

- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Best Practices](https://redis.io/docs/manual/patterns/)
- [Flower Monitoring](https://flower.readthedocs.io/)
