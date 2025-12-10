# BugHive 🐝

An autonomous QA agent system for intelligent web application testing using AI-powered test generation and execution.

## Features

- **Autonomous Testing**: AI-powered test case generation and execution
- **Browser Automation**: Headless browser testing via Browserbase
- **Multi-Agent System**: Built with LangGraph for complex workflows
- **Modern Python Stack**: Python 3.12+ with async/await throughout
- **Production Ready**: PostgreSQL, Redis, Celery for scalable architecture
- **Crash Recovery**: Progress tracking with checkpointing for session recovery
- **Multi-Level Fallback**: Automatic failover through model tiers
- **Parallel Validation**: Concurrent bug validation with rate limiting
- **Extended Thinking**: Claude Opus deep reasoning for critical decisions

## Tech Stack

- **Python 3.12+** with modern async patterns
- **FastAPI** for high-performance API
- **SQLAlchemy 2.0+** with async support
- **PostgreSQL** for persistent storage
- **Redis** for caching and task queue
- **Celery** for background job processing
- **LangGraph** for multi-agent orchestration
- **Anthropic Claude** for AI capabilities (NO OpenAI)
- **Browserbase** for browser automation

## Quick Start

### Prerequisites

- Python 3.12 or higher
- PostgreSQL 15+
- Redis 7+
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bug-hive
   ```

2. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Create and activate virtual environment**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   uv sync
   ```

5. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

6. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb bughive

   # Run migrations (when available)
   # alembic upgrade head
   ```

7. **Start Redis**
   ```bash
   redis-server
   ```

## Development

### Running Tests

```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_config.py

# Run with verbose output
uv run pytest -v
```

### Code Quality

```bash
# Format code with ruff
uv run ruff format .

# Lint code
uv run ruff check .

# Type check with mypy
uv run mypy src/
```

### Running the Application

```bash
# Start the FastAPI development server
uv run uvicorn src.main:app --reload

# Start Celery worker
uv run celery -A src.tasks worker --loglevel=info
```

## Project Structure

```
bug-hive/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Pydantic settings
│   │   └── logging.py         # Structured logging
│   ├── agents/                # AI agents (to be implemented)
│   ├── browser/               # Browser automation (to be implemented)
│   ├── database/              # Database models and queries (to be implemented)
│   └── api/                   # FastAPI routes (to be implemented)
├── tests/
│   └── __init__.py
├── docs/                      # Documentation
├── pyproject.toml            # Project dependencies and config
├── .env.example              # Environment template
├── .gitignore
└── README.md
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

### Key Configuration Areas

- **Database**: PostgreSQL connection settings
- **Redis**: Cache and task queue configuration
- **Browserbase**: Browser automation credentials
- **AI/LLM**: Anthropic API key (NO OpenAI models)
- **Security**: Secret keys and token expiration
- **API**: CORS, rate limiting, versioning

## Environment Variables

Required environment variables (see `.env.example` for full list):

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bughive
REDIS_URL=redis://localhost:6379/0
BROWSERBASE_API_KEY=your_key_here
BROWSERBASE_PROJECT_ID=your_project_id
ANTHROPIC_API_KEY=your_anthropic_key
SECRET_KEY=your_secret_key
```

## Architecture

BugHive uses a modern async Python architecture:

- **FastAPI**: REST API for external interactions
- **LangGraph**: Multi-agent orchestration for test workflows
- **Celery**: Background task processing for long-running tests
- **PostgreSQL**: Persistent storage for test results and configurations
- **Redis**: Caching and message broker
- **Browserbase**: Cloud browser automation

### Agent Harness Features

BugHive implements best practices from [Anthropic's agent harness guidelines](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents):

- **Progress Tracking**: Human-readable progress files (`{session_id}_progress.txt`) and JSON state snapshots for crash recovery
- **Token Budget**: Character-based token estimation to prevent context overflow (no OpenAI dependencies)
- **Message Compaction**: Automatic summarization when context grows too large
- **Multi-Level Fallback**: `ORCHESTRATOR → REASONING → GENERAL → FAST` chain for reliability
- **Error Aggregation**: Pattern detection for debugging systemic issues
- **Extended Thinking**: Claude Opus deep reasoning for critical/high priority bug validation

### Progress Tracking

Each session generates progress files for monitoring and recovery:

```
progress/
├── session-123_progress.txt  # Human-readable progress log
└── session-123_state.json    # Structured state for crash recovery
```

Example progress output:
```
[2025-01-15T10:30:00] crawl | Pages: 5/20 | Bugs: 3 | Cost: $0.05 ETA: 180s
[2025-01-15T10:35:00] analyze | Pages: 10/20 | Bugs: 8 | Cost: $0.12 ETA: 60s
```

### Multi-Model Strategy

Cost-optimized model routing (NO OpenAI models):

| Role | Model | Cost/1M tokens |
|------|-------|----------------|
| Orchestrator | Claude Opus 4.5 | $15 |
| Reasoning | DeepSeek-V3 | $0.27 |
| Coding | DeepSeek-Coder-V2 | $0.14 |
| General | Qwen2.5-72B | $0.15 |
| Fast | Qwen2.5-32B | $0.06 |

## Development Guidelines

### Code Style

- Follow PEP 8 and modern Python idioms
- Use type hints throughout (`mypy --strict` compatible)
- Write comprehensive docstrings for all public APIs
- Keep functions small and focused (< 50 lines)
- Use async/await for I/O-bound operations

### Testing

- Write tests for all new features
- Maintain >90% code coverage
- Use pytest fixtures for test setup
- Mock external services (APIs, databases)
- Test both success and failure cases

### Security

- Never commit API keys or secrets
- Always use environment variables for sensitive data
- Validate and sanitize all user inputs
- Use parameterized queries to prevent SQL injection
- Keep dependencies up to date

## Contributing

1. Create a feature branch (`git checkout -b feature/amazing-feature`)
2. Make your changes with tests
3. Run code quality checks (`ruff format . && ruff check . && mypy src/`)
4. Ensure all tests pass (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Note**: This project does NOT use OpenAI models. We use Anthropic Claude and OpenRouter for AI capabilities.
