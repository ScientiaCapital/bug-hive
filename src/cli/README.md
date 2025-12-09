# BugHive CLI

Beautiful command-line interface for BugHive - the autonomous QA agent system.

## Installation

After installing BugHive, the `bughive` command will be available globally:

```bash
pip install -e .
```

## Commands

### `bughive crawl`

Start a new crawl session.

```bash
# Basic crawl
bughive crawl https://example.com

# Crawl with custom limits
bughive crawl https://example.com --max-pages 100 --max-depth 10

# Crawl with authentication
bughive crawl https://app.example.com --auth session -u username -p

# Background crawl via Celery
bughive crawl https://example.com --async

# Crawl with Linear integration
bughive crawl https://example.com --linear-team TEAM-123 --async

# Custom output format
bughive crawl https://example.com --output json
bughive crawl https://example.com --output markdown
```

**Options:**
- `--max-pages, -m`: Maximum pages to crawl (default: 50)
- `--max-depth, -d`: Maximum crawl depth (default: 5)
- `--auth`: Authentication method (none|session|oauth|api_key)
- `--username, -u`: Username for session auth
- `--password, -p`: Password for session auth (hidden input)
- `--linear-team`: Linear team ID for ticket creation
- `--async`: Run in background via Celery
- `--output, -o`: Output format (table|json|markdown)

---

### `bughive status`

Check status of a crawl session.

```bash
# Check status once
bughive status abc12345

# Watch status in real-time (refreshes every 5 seconds)
bughive status abc12345 --watch

# Custom refresh interval
bughive status abc12345 --watch --interval 10
```

**Options:**
- `--watch, -w`: Watch status in real-time
- `--interval, -i`: Refresh interval in seconds (default: 5)

---

### `bughive bugs`

List bugs found in a session.

```bash
# Show all bugs
bughive bugs abc12345

# Filter by priority
bughive bugs abc12345 --priority critical
bughive bugs abc12345 --priority high

# Limit results
bughive bugs abc12345 --limit 20

# Export as JSON
bughive bugs abc12345 --output json

# Export as Markdown
bughive bugs abc12345 --output markdown
```

**Options:**
- `--priority, -p`: Filter by priority (critical|high|medium|low)
- `--limit, -l`: Maximum number of bugs to show (default: 50)
- `--output, -o`: Output format (table|json|markdown)

---

### `bughive report`

Generate a detailed report for a session.

```bash
# Generate markdown report
bughive report abc12345

# Generate HTML report
bughive report abc12345 --format html --output report.html

# Generate PDF report
bughive report abc12345 --format pdf --output report.pdf

# Generate JSON report
bughive report abc12345 --format json --output report.json
```

**Options:**
- `--format, -f`: Report format (html|pdf|markdown|json)
- `--output, -o`: Output file path

---

### `bughive sessions`

List recent crawl sessions.

```bash
# Show last 20 sessions
bughive sessions

# Show last 50 sessions
bughive sessions --limit 50
```

**Options:**
- `--limit, -l`: Number of sessions to show (default: 20)

---

### `bughive config`

Show current BugHive configuration.

```bash
# Show config (secrets masked)
bughive config

# Show full config with secrets (use with caution!)
bughive config --show-secrets
```

**Options:**
- `--show-secrets`: Show full API keys (use with caution)

---

### `bughive doctor`

Run diagnostic checks on BugHive installation.

```bash
bughive doctor
```

Verifies:
- Python version (3.11+)
- Required dependencies
- Configuration validity
- Database connection
- Redis connection
- Browserbase API key
- AI provider API keys

---

## Output Formats

BugHive CLI supports multiple output formats:

### Table (Default)
Beautiful, colorized tables with Rich formatting.

```bash
bughive crawl https://example.com
```

### JSON
Machine-readable JSON output for scripting.

```bash
bughive crawl https://example.com --output json
```

### Markdown
Human-readable Markdown for documentation.

```bash
bughive crawl https://example.com --output markdown
```

---

## Environment Variables

BugHive CLI respects the same environment variables as the main application:

```bash
# Required
BROWSERBASE_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
REDIS_URL=redis://localhost:6379/0

# Optional
LINEAR_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
```

Set these in `.env` file or export them in your shell.

---

## Examples

### Quick Start

1. Check configuration:
```bash
bughive config
```

2. Run diagnostics:
```bash
bughive doctor
```

3. Start a quick crawl:
```bash
bughive crawl https://example.com --max-pages 10
```

### Production Workflow

1. Start background crawl with Linear integration:
```bash
bughive crawl https://app.example.com \
  --auth session \
  --username testuser \
  --password \
  --linear-team TEAM-123 \
  --max-pages 100 \
  --async
```

2. Watch progress:
```bash
bughive status <session_id> --watch
```

3. View critical bugs:
```bash
bughive bugs <session_id> --priority critical
```

4. Generate report:
```bash
bughive report <session_id> --format html --output qa-report.html
```

### Automation & Scripting

```bash
#!/bin/bash
# Daily QA check

SESSION=$(bughive crawl https://app.example.com \
  --max-pages 50 \
  --async \
  --output json | jq -r '.session_id')

echo "Started session: $SESSION"

# Wait for completion
while true; do
  STATUS=$(bughive status $SESSION --output json | jq -r '.status')
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 30
done

# Generate report
bughive report $SESSION --format html --output "reports/qa-$(date +%Y%m%d).html"

# Check for critical bugs
CRITICAL=$(bughive bugs $SESSION --priority critical --output json | jq '.total')
if [ "$CRITICAL" -gt 0 ]; then
  echo "⚠️  Found $CRITICAL critical bugs!"
  exit 1
fi
```

---

## Colors & Styling

The CLI uses Rich for beautiful terminal output with:

- 🎨 **Colors**: Semantic colors (green for success, red for errors, etc.)
- 📊 **Tables**: Clean, bordered tables with headers
- 🔄 **Progress Bars**: Real-time progress indicators
- ⏱️ **Live Updates**: Watch mode with auto-refresh
- 🎭 **Panels**: Highlighted sections for important info
- ✨ **Icons**: Emoji and symbols for visual clarity

---

## Tips

1. **Session IDs**: You can use shortened session IDs (first 8 chars) in most commands
2. **Watch Mode**: Press Ctrl+C to exit watch mode
3. **Hidden Input**: Use `-p` without a value to prompt for password securely
4. **Config Check**: Run `bughive config` after setup to verify all services
5. **Doctor First**: Run `bughive doctor` to diagnose issues before crawling
6. **Output Formats**: Use `--output json` for scripts, `--output table` for humans

---

## Troubleshooting

### Command not found

If `bughive` command is not found, reinstall:

```bash
pip install -e .
```

### Configuration errors

Check your `.env` file and run:

```bash
bughive config
bughive doctor
```

### Async crawls not working

Ensure Celery worker is running:

```bash
celery -A src.workers.celery_app worker --loglevel=info
```

### Import errors

Make sure all dependencies are installed:

```bash
pip install -e ".[dev]"
```

---

## Getting Help

- `bughive --help`: Show main help
- `bughive <command> --help`: Show command-specific help
- `bughive doctor`: Run diagnostics

For more information, see the main [BugHive documentation](../../README.md).
