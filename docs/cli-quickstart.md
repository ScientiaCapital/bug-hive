# BugHive CLI - Quick Start Guide

Get started with BugHive CLI in 5 minutes.

## Installation

```bash
# Clone and install
git clone https://github.com/your-org/bug-hive.git
cd bug-hive
pip install -e .
```

## Setup

1. **Create `.env` file:**

```bash
cp .env.example .env
```

2. **Add required credentials to `.env`:**

```env
# Required
BROWSERBASE_API_KEY=your_browserbase_key
ANTHROPIC_API_KEY=your_anthropic_key
DATABASE_URL=postgresql+asyncpg://localhost/bughive
REDIS_URL=redis://localhost:6379/0

# Optional
LINEAR_API_KEY=your_linear_key
OPENROUTER_API_KEY=your_openrouter_key
```

3. **Verify configuration:**

```bash
bughive config
bughive doctor
```

## Basic Usage

### 1. Quick Crawl (Synchronous)

Perfect for testing and small sites:

```bash
bughive crawl https://example.com --max-pages 10
```

### 2. Background Crawl (Asynchronous)

For larger sites - requires Celery worker:

```bash
# Terminal 1: Start Celery worker
celery -A src.workers.celery_app worker --loglevel=info

# Terminal 2: Start crawl
bughive crawl https://example.com --max-pages 50 --async
```

### 3. Check Status

```bash
bughive status <session_id>

# Watch in real-time
bughive status <session_id> --watch
```

### 4. View Bugs

```bash
# All bugs
bughive bugs <session_id>

# Only critical
bughive bugs <session_id> --priority critical
```

### 5. Generate Report

```bash
bughive report <session_id> --format html --output report.html
```

## Common Workflows

### Workflow 1: Test a New Feature

```bash
# Quick synchronous crawl
bughive crawl https://app.example.com/new-feature \
  --max-pages 10 \
  --max-depth 2
```

### Workflow 2: Full Site Scan

```bash
# Start background crawl
bughive crawl https://app.example.com \
  --max-pages 200 \
  --max-depth 5 \
  --async

# Watch progress
bughive status <session_id> --watch

# View results
bughive bugs <session_id> --priority high
```

### Workflow 3: Authenticated App Testing

```bash
bughive crawl https://app.example.com \
  --auth session \
  --username testuser \
  --password \
  --max-pages 50 \
  --async
```

### Workflow 4: CI/CD Integration

```bash
#!/bin/bash
# In your CI pipeline

# Start crawl
SESSION=$(bughive crawl https://staging.example.com \
  --max-pages 30 \
  --output json | jq -r '.session_id')

# Wait for completion (with timeout)
TIMEOUT=600
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  STATUS=$(bughive status $SESSION | grep Status | awk '{print $2}')
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 10
  ELAPSED=$((ELAPSED + 10))
done

# Check for critical bugs
CRITICAL=$(bughive bugs $SESSION --priority critical | grep -c "critical")
if [ $CRITICAL -gt 0 ]; then
  echo "❌ Found critical bugs - blocking deployment"
  exit 1
fi

echo "✅ No critical bugs found - deployment approved"
```

## Command Cheat Sheet

| Command | Description | Example |
|---------|-------------|---------|
| `crawl` | Start crawl | `bughive crawl https://example.com` |
| `status` | Check progress | `bughive status abc123 --watch` |
| `bugs` | List bugs | `bughive bugs abc123 --priority critical` |
| `report` | Generate report | `bughive report abc123 --format html` |
| `sessions` | List sessions | `bughive sessions --limit 20` |
| `config` | Show config | `bughive config` |
| `doctor` | Run diagnostics | `bughive doctor` |

## Keyboard Shortcuts

- `Ctrl+C`: Stop current operation or exit watch mode
- `Enter`: Continue in interactive prompts
- `Tab`: Autocomplete (if shell completion configured)

## Output Formats

### Table (Default) - Human Friendly
```bash
bughive crawl https://example.com
```
✅ Colorful, easy to read

### JSON - Machine Readable
```bash
bughive crawl https://example.com --output json | jq
```
✅ Perfect for scripts and automation

### Markdown - Documentation
```bash
bughive report abc123 --format markdown > docs/qa-report.md
```
✅ Great for documentation and sharing

## Tips & Tricks

### 1. Shorten Session IDs
Instead of full UUID, use first 8-12 characters:
```bash
bughive status abc12345  # Instead of abc12345-6789-...
```

### 2. Background + Watch
Start async crawl and immediately watch:
```bash
SESSION=$(bughive crawl https://example.com --async | grep "Session ID" | awk '{print $NF}')
bughive status $SESSION --watch
```

### 3. Priority Filtering
Focus on what matters:
```bash
# Critical only
bughive bugs $SESSION --priority critical

# High and Critical
bughive bugs $SESSION --priority high
```

### 4. Export Results
```bash
# JSON for processing
bughive bugs $SESSION --output json > bugs.json

# Markdown for docs
bughive report $SESSION --format markdown > QA-Report.md

# HTML for sharing
bughive report $SESSION --format html --output report.html
```

### 5. Config Security
Hide secrets in production:
```bash
# Safe - secrets masked
bughive config

# Dangerous - shows full keys
bughive config --show-secrets
```

## Troubleshooting

### "Command not found"
```bash
# Reinstall
pip install -e .

# Check installation
which bughive
```

### "Session not found"
- Session might not be created yet (async delay)
- Check session ID is correct
- List recent sessions: `bughive sessions`

### "Celery not running"
```bash
# Start worker
celery -A src.workers.celery_app worker --loglevel=info

# Check Redis
redis-cli ping
```

### "Database connection failed"
```bash
# Check config
bughive config

# Run diagnostics
bughive doctor

# Verify DATABASE_URL in .env
```

## Next Steps

1. ✅ Run `bughive doctor` to verify setup
2. ✅ Try a quick crawl: `bughive crawl https://example.com --max-pages 5`
3. ✅ Set up Celery for async crawls
4. ✅ Configure Linear integration for ticket creation
5. ✅ Add to CI/CD pipeline

## Getting Help

- `bughive --help` - Main help
- `bughive crawl --help` - Command help
- `bughive doctor` - Diagnostic tool
- Full docs: [CLI README](../src/cli/README.md)

---

Happy bug hunting! 🐝
