# BugHive API

FastAPI gateway for the BugHive autonomous QA agent system.

## Features

- **Async-first architecture** - All endpoints use async/await for high concurrency
- **Type-safe with Pydantic** - Request/response validation with detailed error messages
- **Structured logging** - JSON logs with request tracing in production
- **API key authentication** - Simple X-API-Key header authentication
- **CORS support** - Configurable origins for frontend integration
- **Health checks** - Basic and detailed health endpoints
- **OpenAPI docs** - Auto-generated Swagger UI (development only)
- **Error handling** - Consistent error responses with request IDs

## Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn[standard] httpx structlog
```

### 2. Configure Environment

Create `.env` file:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bughive

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-here

# AI Providers (NO OPENAI)
ANTHROPIC_API_KEY=your-anthropic-key
OPENROUTER_API_KEY=your-openrouter-key

# Browserbase
BROWSERBASE_API_KEY=your-browserbase-key
BROWSERBASE_PROJECT_ID=your-project-id

# Optional: Linear Integration
LINEAR_API_KEY=your-linear-key
```

### 3. Run Server

```bash
# Development (with auto-reload)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Production (with workers)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access API

- API: http://localhost:8000
- Docs: http://localhost:8000/docs (development only)
- Health: http://localhost:8000/health

## API Endpoints

### Health Checks

#### `GET /health`
Basic health check for load balancers.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "0.1.0"
}
```

#### `GET /health/detailed`
Detailed health with service dependencies.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "0.1.0",
  "services": [
    {
      "service": "database",
      "status": "healthy",
      "latency_ms": 12.5
    }
  ]
}
```

### Crawl Sessions

#### `POST /api/v1/crawl/start`
Start a new crawl session.

**Headers:**
```
X-API-Key: your-api-key
Content-Type: application/json
```

**Request:**
```json
{
  "base_url": "https://example.com",
  "max_pages": 100,
  "max_depth": 5,
  "auth_method": "none",
  "excluded_patterns": ["/admin/*", "/api/*"]
}
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "base_url": "https://example.com",
  "status": "pending",
  "message": "Crawl session created and queued for processing",
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### `GET /api/v1/crawl/{session_id}/status`
Get crawl session status and progress.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "base_url": "https://example.com",
  "status": "running",
  "pages_discovered": 45,
  "pages_crawled": 42,
  "bugs_found": 7,
  "total_cost": 2.35,
  "started_at": "2024-01-15T10:30:00Z",
  "elapsed_time": 120.5,
  "success_rate": 93.3,
  "bugs_per_page": 0.17
}
```

#### `GET /api/v1/crawl/{session_id}/bugs`
Get all bugs found in a session.

**Query Parameters:**
- `priority` (optional): Filter by priority (critical, high, medium, low)
- `category` (optional): Filter by category (ui_ux, data, edge_case, performance, security)
- `status_filter` (optional): Filter by status (detected, validated, reported, dismissed)
- `skip` (optional): Number to skip (default: 0)
- `limit` (optional): Maximum to return (default: 100)

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "bugs": [...],
  "total": 7,
  "page": 1,
  "page_size": 100,
  "by_priority": {
    "critical": 2,
    "high": 3,
    "medium": 2
  },
  "by_category": {
    "ui_ux": 4,
    "performance": 2,
    "data": 1
  }
}
```

#### `POST /api/v1/crawl/{session_id}/stop`
Stop a running crawl session.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "previous_status": "running",
  "new_status": "completed",
  "message": "Crawl session stopped successfully",
  "pages_crawled": 42,
  "bugs_found": 7
}
```

### Bug Management

#### `GET /api/v1/bugs/{bug_id}`
Get bug details including evidence.

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "page_id": "550e8400-e29b-41d4-a716-446655440001",
  "category": "ui_ux",
  "priority": "high",
  "title": "Submit button overlaps text on mobile",
  "description": "On mobile viewports...",
  "steps_to_reproduce": [
    "Navigate to /products",
    "Resize to 375px width",
    "Observe overlap"
  ],
  "evidence": [...],
  "confidence": 0.92,
  "status": "detected",
  "page_url": "https://example.com/products"
}
```

#### `POST /api/v1/bugs/{bug_id}/validate`
Mark bug as validated or dismissed.

**Request:**
```json
{
  "is_valid": true,
  "notes": "Confirmed as real issue"
}
```

**Response:**
```json
{
  "bug_id": "550e8400-e29b-41d4-a716-446655440002",
  "previous_status": "detected",
  "new_status": "validated",
  "message": "Bug marked as validated"
}
```

#### `POST /api/v1/bugs/{bug_id}/report`
Create Linear ticket for bug.

**Response:**
```json
{
  "bug_id": "550e8400-e29b-41d4-a716-446655440002",
  "linear_issue_id": "BUG-123",
  "linear_issue_url": "https://linear.app/bughive/issue/BUG-123",
  "reported_at": "2024-01-15T10:35:00Z",
  "message": "Bug successfully reported to Linear"
}
```

## Authentication

All API endpoints (except health checks) require authentication via API key.

**Header:**
```
X-API-Key: your-api-key-here
```

**Error Response (401):**
```json
{
  "error": "http_error",
  "detail": "Missing API key. Include X-API-Key header.",
  "request_id": "abc-123-def"
}
```

## Error Handling

All errors return consistent JSON format:

### Validation Error (422)
```json
{
  "error": "validation_error",
  "detail": "Request validation failed",
  "validation_errors": [
    {
      "loc": ["body", "base_url"],
      "msg": "base_url must start with http:// or https://",
      "type": "value_error"
    }
  ]
}
```

### Not Found (404)
```json
{
  "error": "http_error",
  "detail": "Crawl session 550e8400-e29b-41d4-a716-446655440000 not found",
  "request_id": "abc-123-def"
}
```

### Internal Error (500)
```json
{
  "error": "internal_error",
  "detail": "An unexpected error occurred",
  "request_id": "abc-123-def"
}
```

## Request Tracing

Every request receives a unique `request_id` for distributed tracing:

**Response Header:**
```
X-Request-ID: abc-123-def-456
```

Use this ID to correlate logs and track requests across services.

## Example Usage

See `src/api/example_usage.py` for a complete Python client example.

```python
from src.api.example_usage import BugHiveClient

client = BugHiveClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
)

# Start crawl
crawl = await client.start_crawl(
    base_url="https://example.com",
    max_pages=50,
)

# Wait for completion
status = await client.wait_for_crawl(crawl["session_id"])

# Get bugs
bugs = await client.get_session_bugs(crawl["session_id"])

# Validate and report
await client.validate_bug(bugs["bugs"][0]["id"], is_valid=True)
await client.report_bug(bugs["bugs"][0]["id"])
```

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Environment Variables

```bash
# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/bughive
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Security
SECRET_KEY=<generate-strong-key>
CORS_ORIGINS=["https://yourdomain.com"]

# Rate limiting
API_RATE_LIMIT=1000/minute
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name api.bughive.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Architecture

```
src/api/
├── main.py                 # FastAPI app with middleware and routes
├── schemas.py              # Request/response models
├── example_usage.py        # Client usage examples
├── deps/
│   ├── auth.py            # API key authentication
│   └── database.py        # Database session dependencies
├── middleware/
│   └── logging.py         # Request logging middleware
└── routes/
    ├── health.py          # Health check endpoints
    ├── crawl.py           # Crawl session management
    └── bugs.py            # Bug management
```

## Next Steps

1. **Integrate Celery** - Background task queue for crawl processing
2. **Add rate limiting** - Per-key rate limits with Redis
3. **Implement Linear API** - Real Linear ticket creation
4. **Add WebSocket** - Real-time crawl progress updates
5. **Metrics export** - Prometheus metrics endpoint
6. **API versioning** - Support for multiple API versions

## License

Proprietary - BugHive System
