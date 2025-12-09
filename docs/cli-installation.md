# BugHive CLI - Installation & Setup Guide

Complete guide to installing and configuring the BugHive CLI.

## Prerequisites

- Python 3.12 or higher
- pip or uv package manager
- Redis (for async crawls)
- PostgreSQL (for data storage)

## Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/your-org/bug-hive.git
cd bug-hive
```

### Step 2: Install Dependencies

Using pip:
```bash
pip install -e .
```

Using uv (faster):
```bash
uv pip install -e .
```

This will:
- Install all dependencies (Click, Rich, FastAPI, etc.)
- Register the `bughive` command globally
- Install in development mode (editable)

### Step 3: Install Playwright Browsers

```bash
playwright install chromium
```

### Step 4: Verify Installation

```bash
bughive --version
```

You should see:
```
bughive, version 0.1.0
```

Test the CLI:
```bash
bughive --help
```

## Configuration

### Step 1: Create `.env` File

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

### Step 2: Add Required Credentials

Edit `.env` and add your API keys:

```env
# Required - Browserbase for web crawling
BROWSERBASE_API_KEY=your_browserbase_api_key_here
BROWSERBASE_PROJECT_ID=your_project_id_here

# Required - AI Provider (choose one or both)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Required - Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bughive

# Required - Redis
REDIS_URL=redis://localhost:6379/0

# Optional - Linear for ticket creation
LINEAR_API_KEY=your_linear_api_key_here
LINEAR_TEAM_ID=your_default_team_id

# Optional - Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

### Step 3: Get API Keys

#### Browserbase API Key

1. Sign up at [browserbase.com](https://www.browserbase.com)
2. Create a new project
3. Copy your API key and Project ID
4. Add to `.env`

#### Anthropic API Key

1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Go to API Keys section
3. Create a new API key
4. Add to `.env`

#### OpenRouter API Key (Alternative)

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Go to Keys section
3. Create a new API key
4. Add to `.env`

#### Linear API Key (Optional)

1. Go to [linear.app](https://linear.app) settings
2. Create a personal API key
3. Add to `.env`

### Step 4: Setup Database

#### Using Docker (Recommended)

```bash
# Start PostgreSQL
docker run -d \
  --name bughive-postgres \
  -e POSTGRES_USER=bughive \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=bughive \
  -p 5432:5432 \
  postgres:16-alpine

# Start Redis
docker run -d \
  --name bughive-redis \
  -p 6379:6379 \
  redis:7-alpine
```

#### Using Local Installation

**PostgreSQL:**
```bash
# macOS
brew install postgresql@16
brew services start postgresql@16

# Ubuntu/Debian
sudo apt install postgresql-16
sudo systemctl start postgresql

# Create database
createdb bughive
```

**Redis:**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis
```

### Step 5: Run Database Migrations

```bash
# Initialize database schema
alembic upgrade head
```

### Step 6: Verify Configuration

```bash
bughive config
```

You should see:
```
╭──────────────────── 🐝 BugHive Configuration ─────────────────────╮
│ Setting               Value                           Status     │
├───────────────────────────────────────────────────────────────────┤
│ Environment           development                      ✓          │
│ Debug Mode            True                             ✓          │
│ Database URL          postgresql://***               ✓          │
│ Redis URL             redis://***                     ✓          │
│ Browserbase API       bb_a...ef12                     ✓          │
│ Anthropic API         sk-a...7890                     ✓          │
│ OpenRouter API        Not configured                  ✗          │
│ Linear API            lin_...xyz                      ✓          │
╰───────────────────────────────────────────────────────────────────╯
```

All items should show ✓ (except optional ones).

### Step 7: Run Diagnostics

```bash
bughive doctor
```

You should see:
```
╭──────────────────── 🐝 BugHive Doctor ────────────────────╮
│                                                            │
│  Running diagnostic checks...                             │
│                                                            │
╰────────────────────────────────────────────────────────────╯

╭────────────────────────────────────────────────────────────╮
│ Check            Status  Details                          │
├────────────────────────────────────────────────────────────┤
│ Python 3.11+     ✓       Python 3.12                      │
│ Playwright       ✓       Installed                        │
│ Configuration    ✓       Valid                            │
│ Database         ✓       Configured                       │
│ Redis            ✓       Configured                       │
│ Browserbase      ✓       Configured                       │
╰────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────╮
│ All checks passed! BugHive is ready to use.            │
╰─────────────────────────────────────────────────────────╯
```

## Setting Up Workers (Optional - For Async Crawls)

If you want to use async crawls (`--async` flag), you need to start a Celery worker.

### Terminal 1: Start Celery Worker

```bash
celery -A src.workers.celery_app worker --loglevel=info
```

### Terminal 2: Start Flower (Optional - Web UI)

```bash
celery -A src.workers.celery_app flower --port=5555
```

Access Flower at: http://localhost:5555

## Quick Test

Test the installation with a quick crawl:

```bash
bughive crawl https://example.com --max-pages 5
```

You should see a beautiful progress bar and summary:

```
╭───────────────── Crawl Session ──────────────────╮
│                                                   │
│  🐝 BugHive                                       │
│                                                   │
│  Starting autonomous QA session                  │
│  https://example.com                             │
│                                                   │
╰─── Max Pages: 5 | Max Depth: 5 ────────────────╯

⠋ Crawling... ━━━━━━━━━━━━━━━━━━━━━━━━ 00:00:15

╭────────────── ✓ Crawl Complete! ──────────────╮
╰────────────────────────────────────────────────╯

╭────────────────────────────────────────────────╮
│ Metric              Value                     │
├────────────────────────────────────────────────┤
│ Pages Crawled       5                         │
│ Bugs Found          1                         │
│ Tickets Created     0                         │
│ Total Cost          $0.0123                   │
│ Duration            15.4s                     │
╰────────────────────────────────────────────────╯
```

## Troubleshooting

### "bughive: command not found"

**Solution 1**: Reinstall in editable mode
```bash
pip install -e .
```

**Solution 2**: Check Python scripts directory is in PATH
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

**Solution 3**: Use full path
```bash
python -m src.cli.main --help
```

### "Module 'click' not found"

Dependencies not installed:
```bash
pip install -e .
# or
pip install click rich
```

### "Module 'src' not found"

Not running from project directory:
```bash
cd /path/to/bug-hive
pip install -e .
```

### Database Connection Failed

Check PostgreSQL is running:
```bash
# Using Docker
docker ps | grep postgres

# Using system service
sudo systemctl status postgresql
```

Verify DATABASE_URL in `.env`:
```bash
cat .env | grep DATABASE_URL
```

### Redis Connection Failed

Check Redis is running:
```bash
# Using Docker
docker ps | grep redis

# Using system service
sudo systemctl status redis

# Test connection
redis-cli ping
# Should return: PONG
```

### Browserbase API Error

Check API key is valid:
```bash
curl -H "x-bb-api-key: YOUR_KEY" https://api.browserbase.com/v1/sessions
```

Verify in `.env`:
```bash
cat .env | grep BROWSERBASE
```

### Permission Denied on cli_demo.sh

Make it executable:
```bash
chmod +x examples/cli_demo.sh
```

## Updating

To update BugHive to the latest version:

```bash
cd bug-hive
git pull origin main
pip install -e . --upgrade
alembic upgrade head
```

## Uninstalling

To completely remove BugHive:

```bash
# Uninstall package
pip uninstall bug-hive

# Remove Docker containers (if used)
docker rm -f bughive-postgres bughive-redis

# Remove data directories (optional)
rm -rf ~/.bughive
```

## Next Steps

1. ✅ Read the [Quick Start Guide](cli-quickstart.md)
2. ✅ Try the [Demo Script](../examples/cli_demo.sh)
3. ✅ Review [Example Outputs](cli-examples.md)
4. ✅ Check [Architecture Docs](cli-architecture.md)
5. ✅ Read [Full CLI Reference](../src/cli/README.md)

## Getting Help

- Run `bughive --help` for command overview
- Run `bughive <command> --help` for specific command help
- Run `bughive doctor` to diagnose issues
- Check the [documentation](../README.md) for more details

## Environment Variables Reference

Complete list of environment variables:

```env
# Browserbase
BROWSERBASE_API_KEY=          # Required
BROWSERBASE_PROJECT_ID=       # Required

# AI Providers (at least one required)
ANTHROPIC_API_KEY=           # Claude models
OPENROUTER_API_KEY=          # Multiple model access

# Database
DATABASE_URL=                # Required (PostgreSQL)

# Redis
REDIS_URL=                   # Required

# Linear Integration
LINEAR_API_KEY=              # Optional
LINEAR_TEAM_ID=              # Optional

# Application
ENVIRONMENT=                 # development|production|staging
DEBUG=                       # true|false
LOG_LEVEL=                   # DEBUG|INFO|WARNING|ERROR

# Server (for API mode)
API_HOST=                    # Default: 0.0.0.0
API_PORT=                    # Default: 8000
```

## Production Deployment

For production deployment:

1. Set `ENVIRONMENT=production`
2. Set `DEBUG=false`
3. Use strong database credentials
4. Use managed Redis (e.g., Redis Cloud)
5. Use managed PostgreSQL (e.g., RDS, Supabase)
6. Set up SSL/TLS for API
7. Use process manager (systemd, supervisor)
8. Set up monitoring and alerting
9. Configure log aggregation
10. Use secrets manager (not `.env` file)

See full deployment guide in main documentation.

---

Happy bug hunting! 🐝
