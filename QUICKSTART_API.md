# BugHive API - Quick Start Guide

## Prerequisites

```bash
# Install dependencies
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg httpx structlog python-dotenv pydantic pydantic-settings
```

## Setup

### 1. Configure Environment

Create `.env` file:

```bash
# Required
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bughive
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-change-in-production

# AI Providers (NO OPENAI)
ANTHROPIC_API_KEY=your-key-here
OPENROUTER_API_KEY=your-key-here

# Browserbase
BROWSERBASE_API_KEY=your-key-here
BROWSERBASE_PROJECT_ID=your-project-id

# Optional
LINEAR_API_KEY=your-linear-key
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### 2. Initialize Database

```bash
# Start PostgreSQL
docker run -d \
  --name bughive-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=bughive \
  -p 5432:5432 \
  postgres:15

# Tables will be created automatically on first run (development mode)
```

### 3. Start API Server

```bash
# Development (auto-reload)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production (4 workers)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Test API

```bash
# Health check
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed

# View docs
open http://localhost:8000/docs
```

## Quick Test

```bash
# Run test script
python test_api.py
```

Expected output:
```
Testing BugHive API...
--------------------------------------------------

1. Testing root endpoint...
   Status: 200
   Response: {'name': 'BugHive API', 'version': '0.1.0', ...}

2. Testing health check...
   Status: 200
   Response: {'status': 'healthy', 'timestamp': '...', ...}

3. Testing detailed health...
   Status: 200
   Overall Status: healthy
   Services:
     - database: healthy (12.50ms)

4. Testing API without authentication...
   Status: 401
   Response: {'error': 'http_error', 'detail': 'Missing API key...'}

5. Testing OpenAPI docs...
   Status: 200
   Docs available: True

--------------------------------------------------
Test complete!
```

## Example Usage

### Start a Crawl

```bash
curl -X POST http://localhost:8000/api/v1/crawl/start \
  -H "X-API-Key: your-secret-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{
    "base_url": "https://example.com",
    "max_pages": 50,
    "max_depth": 3
  }'
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "base_url": "https://example.com",
  "status": "pending",
  "message": "Crawl session created. Processing will begin shortly.",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Check Status

```bash
curl http://localhost:8000/api/v1/crawl/550e8400-e29b-41d4-a716-446655440000/status \
  -H "X-API-Key: your-secret-key-change-in-production"
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "pages_discovered": 45,
  "pages_crawled": 42,
  "bugs_found": 7,
  "total_cost": 2.35,
  "elapsed_time": 120.5
}
```

### Get Bugs

```bash
curl "http://localhost:8000/api/v1/crawl/550e8400-e29b-41d4-a716-446655440000/bugs?priority=critical" \
  -H "X-API-Key: your-secret-key-change-in-production"
```

## Python Client

```python
import asyncio
from src.api.example_usage import BugHiveClient

async def main():
    # Initialize client
    client = BugHiveClient(
        base_url="http://localhost:8000",
        api_key="your-secret-key-change-in-production",
    )

    # Health check
    health = await client.health_check()
    print(f"API Status: {health['status']}")

    # Start crawl
    crawl = await client.start_crawl(
        base_url="https://example.com",
        max_pages=50,
    )
    session_id = crawl["session_id"]
    print(f"Crawl started: {session_id}")

    # Wait for completion
    status = await client.wait_for_crawl(session_id)
    print(f"Crawl completed: {status['bugs_found']} bugs found")

    # Get bugs
    bugs = await client.get_session_bugs(session_id)
    print(f"Total bugs: {bugs['total']}")

    # Validate first bug
    if bugs["bugs"]:
        bug_id = bugs["bugs"][0]["id"]
        await client.validate_bug(bug_id, is_valid=True)
        print(f"Bug {bug_id} validated")

asyncio.run(main())
```

## Troubleshooting

### Database Connection Error

```
Error: could not translate host name "localhost" to address
```

Solution: Check DATABASE_URL in .env, ensure PostgreSQL is running.

### Authentication Error

```
Status: 401
Detail: Missing API key
```

Solution: Include `X-API-Key` header with SECRET_KEY from .env.

### Import Error

```
ModuleNotFoundError: No module named 'fastapi'
```

Solution: Install dependencies: `pip install -r requirements.txt`

### Port Already in Use

```
Error: [Errno 48] Address already in use
```

Solution: Change port or kill existing process:
```bash
lsof -ti:8000 | xargs kill -9
```

## Directory Structure

```
bug-hive/
├── src/
│   ├── api/               # FastAPI application
│   │   ├── main.py       # App entry point
│   │   ├── schemas.py    # Request/response models
│   │   ├── deps/         # Dependencies
│   │   ├── middleware/   # Middleware
│   │   └── routes/       # API routes
│   ├── core/             # Config, logging
│   ├── db/               # Database, repositories
│   └── models/           # Pydantic models
├── test_api.py           # Quick test script
└── .env                  # Environment variables
```

## Next Steps

1. **Integrate Celery** - Background task processing
2. **Add Linear Integration** - Real bug reporting
3. **Implement Redis** - Caching and rate limiting
4. **Add WebSocket** - Real-time updates
5. **Deploy to Production** - Docker + Kubernetes

## Documentation

- API Docs: http://localhost:8000/docs
- Full README: src/api/README.md
- Implementation Details: src/api/IMPLEMENTATION.md

## Support

For issues or questions:
1. Check logs: Look for errors in console output
2. Enable debug: Set `DEBUG=true` in .env
3. Check health: `curl http://localhost:8000/health/detailed`

## Production Checklist

Before deploying to production:

- [ ] Change SECRET_KEY to strong random value
- [ ] Set ENVIRONMENT=production
- [ ] Configure DATABASE_URL with production credentials
- [ ] Set DEBUG=false
- [ ] Configure CORS_ORIGINS with allowed domains
- [ ] Enable HTTPS/TLS
- [ ] Setup monitoring (Sentry, Datadog)
- [ ] Configure rate limiting
- [ ] Setup log aggregation
- [ ] Configure backups
- [ ] Load test the API

## License

Proprietary - BugHive System
