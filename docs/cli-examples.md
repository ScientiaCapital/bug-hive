# BugHive CLI - Example Output

This document shows what the BugHive CLI looks like in action.

## Installation & Setup

### First Time Setup

```bash
$ bughive doctor

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

### Configuration Check

```bash
$ bughive config

╭──────────────────── 🐝 BugHive Configuration ─────────────────────╮
│ Setting               Value                           Status     │
├───────────────────────────────────────────────────────────────────┤
│ Environment           production                      ✓          │
│ Debug Mode            False                           ✓          │
│ Database URL          postgresql://***               ✓          │
│ Redis URL             redis://***                     ✓          │
│ Browserbase API       bb_a...ef12                     ✓          │
│ Anthropic API         sk-a...7890                     ✓          │
│ OpenRouter API        Not configured                  ✗          │
│ Linear API            lin_...xyz                      ✓          │
╰───────────────────────────────────────────────────────────────────╯
```

## Crawling

### Quick Synchronous Crawl

```bash
$ bughive crawl https://example.com --max-pages 10

╭───────────────── Crawl Session ──────────────────╮
│                                                   │
│  🐝 BugHive                                       │
│                                                   │
│  Starting autonomous QA session                  │
│  https://example.com                             │
│                                                   │
╰─── Max Pages: 10 | Max Depth: 5 ────────────────╯

⠋ Crawling... ━━━━━━━━━━━━━━━━━━━━━━━━ 00:00:42

╭────────────── ✓ Crawl Complete! ──────────────╮
╰────────────────────────────────────────────────╯

╭────────────────────────────────────────────────╮
│ Metric              Value                     │
├────────────────────────────────────────────────┤
│ Pages Crawled       10                        │
│ Bugs Found          3                         │
│ Tickets Created     2                         │
│ Total Cost          $0.0234                   │
│ Duration            42.3s                     │
╰────────────────────────────────────────────────╯

Bugs by Priority:
  🟡 high: 2
  🔵 medium: 1
```

### Async Background Crawl

```bash
$ bughive crawl https://app.example.com --max-pages 100 --async

╭───────────────── Crawl Session ──────────────────╮
│                                                   │
│  🐝 BugHive                                       │
│                                                   │
│  Starting autonomous QA session                  │
│  https://app.example.com                         │
│                                                   │
╰─── Max Pages: 100 | Max Depth: 5 ───────────────╯

✓ Crawl queued successfully

╭────────────────────────────────────────────────╮
│ Session ID    a1b2c3d4-567...                 │
│ Task ID       task-12345678                   │
│ Status        Queued                           │
╰────────────────────────────────────────────────╯

Use bughive status a1b2c3d4 to check progress
```

### Crawl with Authentication

```bash
$ bughive crawl https://app.example.com \
    --auth session \
    --username testuser \
    --password \
    --linear-team TEAM-123 \
    --async

Password: ********

╭───────────────── Crawl Session ──────────────────╮
│                                                   │
│  🐝 BugHive                                       │
│                                                   │
│  Starting autonomous QA session                  │
│  https://app.example.com                         │
│                                                   │
╰─── Max Pages: 50 | Max Depth: 5 ────────────────╯

✓ Crawl queued successfully

╭────────────────────────────────────────────────╮
│ Session ID    xyz789ab-cde...                 │
│ Task ID       task-87654321                   │
│ Status        Queued                           │
╰────────────────────────────────────────────────╯

Use bughive status xyz789ab to check progress
```

## Status Monitoring

### One-Time Status Check

```bash
$ bughive status a1b2c3d4

╭─────────────── Session a1b2c3d4... ───────────────╮
│ Metric              Value                         │
├───────────────────────────────────────────────────┤
│ Status              🔄 RUNNING                    │
│ Base URL            https://app.example.com       │
│ Pages Crawled       45 / 100                      │
│ Bugs Found          7                             │
│ Current Depth       3                             │
│ Started             2025-12-09 14:23:15           │
│ Total Cost          $0.1234                       │
╰───────────────────────────────────────────────────╯
```

### Watch Mode (Live Updates)

```bash
$ bughive status a1b2c3d4 --watch --interval 5

╭─────────────── Session a1b2c3d4... ───────────────╮
│ Metric              Value                         │
├───────────────────────────────────────────────────┤
│ Status              🔄 RUNNING                    │
│ Base URL            https://app.example.com       │
│ Pages Crawled       67 / 100                      │  ← Updates live
│ Bugs Found          12                            │  ← Updates live
│ Current Depth       4                             │
│ Started             2025-12-09 14:23:15           │
│ Total Cost          $0.1897                       │  ← Updates live
╰───────────────────────────────────────────────────╯

^C
Watch mode stopped
```

### Completed Session

```bash
$ bughive status a1b2c3d4

╭─────────────── Session a1b2c3d4... ───────────────╮
│ Metric              Value                         │
├───────────────────────────────────────────────────┤
│ Status              ✓ COMPLETED                   │
│ Base URL            https://app.example.com       │
│ Pages Crawled       100 / 100                     │
│ Bugs Found          23                            │
│ Current Depth       5                             │
│ Started             2025-12-09 14:23:15           │
│ Completed           2025-12-09 14:45:32           │
│ Total Cost          $0.3456                       │
╰───────────────────────────────────────────────────╯
```

## Bug Listing

### All Bugs

```bash
$ bughive bugs a1b2c3d4

Fetching bugs for session a1b2c3d4...

╭──────────────────── Bugs Found ────────────────────╮
│ ID       Priority  Type         Page                │
│                                                      │
│ BUG-001  critical  XSS          /login              │
│ BUG-002  high      SQL Inj      /api/users          │
│ BUG-003  high      CORS         /api/auth           │
│ BUG-004  medium    Broken Link  /dashboard          │
│ BUG-005  medium    404          /profile/edit       │
│ BUG-006  low       Missing Alt  /home               │
╰────────────────────────────────────────────────────╯
```

### Filter by Priority

```bash
$ bughive bugs a1b2c3d4 --priority critical

Fetching bugs for session a1b2c3d4...

╭────────────── Bugs Found (CRITICAL) ───────────────╮
│ ID       Priority   Type    Page        Description │
├─────────────────────────────────────────────────────┤
│ BUG-001  🔴critical XSS     /login      Unescaped   │
│                                         user input  │
│                                         in search   │
│                                         parameter   │
╰─────────────────────────────────────────────────────╯
```

### JSON Output

```bash
$ bughive bugs a1b2c3d4 --output json

{
  "bugs": [
    {
      "id": "BUG-001",
      "priority": "critical",
      "type": "XSS",
      "page": "/login",
      "description": "Unescaped user input in search parameter"
    },
    {
      "id": "BUG-002",
      "priority": "high",
      "type": "SQL Injection",
      "page": "/api/users",
      "description": "Raw SQL query with user input"
    }
  ],
  "total": 2
}
```

## Reports

### Markdown Report

```bash
$ bughive report a1b2c3d4

Generating MARKDOWN report for session a1b2c3d4...

# Bugs Report

## Summary
- **Total Bugs**: 23
- **Critical**: 1
- **High**: 5
- **Medium**: 12
- **Low**: 5

## Critical Issues

### BUG-001: XSS Vulnerability
- **Page**: /login
- **Type**: Cross-Site Scripting
- **Description**: Unescaped user input in search parameter

[... full report ...]
```

### HTML Report

```bash
$ bughive report a1b2c3d4 --format html --output qa-report.html

Generating HTML report for session a1b2c3d4...

✓ Report saved to: qa-report.html
```

## Sessions List

```bash
$ bughive sessions --limit 10

Fetching recent sessions...

╭──────────────── Recent Sessions ───────────────────╮
│ ID           Date         Status      Bugs  Pages  │
├─────────────────────────────────────────────────────┤
│ a1b2c3d4...  2025-12-09   ✓completed  23    100    │
│ xyz789ab...  2025-12-08   ✓completed  12    50     │
│ def456gh...  2025-12-08   🔄running    3     15/30 │
│ jkl012mn...  2025-12-07   ✓completed  8     25     │
╰─────────────────────────────────────────────────────╯
```

## Help Commands

### Main Help

```bash
$ bughive --help

Usage: bughive [OPTIONS] COMMAND [ARGS]...

  🐝 BugHive - Autonomous QA Agent System

  Automated web crawling, testing, and bug detection powered by AI.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  crawl     Start a new crawl session.
  status    Check status of a crawl session.
  bugs      List bugs found in a session.
  report    Generate a report for a session.
  sessions  List recent crawl sessions.
  config    Show current configuration.
  doctor    Run diagnostic checks on BugHive installation.
```

### Command-Specific Help

```bash
$ bughive crawl --help

Usage: bughive crawl [OPTIONS] URL

  Start a new crawl session.

  URL: The base URL to start crawling from

  Examples:

      # Quick crawl with defaults
      bughive crawl https://example.com

      # Crawl with authentication
      bughive crawl https://app.example.com --auth session -u user -p

      # Background crawl with Linear integration
      bughive crawl https://example.com --async --linear-team TEAM-123

Options:
  --max-pages, -m INTEGER         Maximum pages to crawl
  --max-depth, -d INTEGER         Maximum crawl depth
  --auth [none|session|oauth|api_key]
                                  Authentication method
  --username, -u TEXT             Username for session auth
  --password, -p TEXT             Password for session auth
  --linear-team TEXT              Linear team ID for ticket creation
  --async                         Run in background via Celery
  --output, -o [json|table|markdown]
                                  Output format
  --help                          Show this message and exit.
```

## Error Handling

### Missing Configuration

```bash
$ bughive crawl https://example.com

╭────────────────────────────────────────────────────╮
│ ⚠️  Configuration Error                           │
│                                                    │
│ Missing required environment variable:            │
│   BROWSERBASE_API_KEY                             │
│                                                    │
│ Please set in .env file or export in shell.       │
╰────────────────────────────────────────────────────╯
```

### Invalid Session ID

```bash
$ bughive status invalid123

Session not found

Try:
  • Check the session ID is correct
  • List recent sessions: bughive sessions
  • Session might still be initializing (async)
```

### Crawl Failure

```bash
$ bughive crawl https://invalid-url-xyz.com

╭───────────────── Crawl Session ──────────────────╮
│                                                   │
│  🐝 BugHive                                       │
│                                                   │
│  Starting autonomous QA session                  │
│  https://invalid-url-xyz.com                     │
│                                                   │
╰─── Max Pages: 50 | Max Depth: 5 ────────────────╯

✗ Crawl failed: DNS lookup failed for invalid-url-xyz.com

Traceback (most recent call last):
  [... stack trace ...]
```

## Advanced Usage

### Multiple Output Formats

```bash
# Table format (default)
$ bughive crawl https://example.com
[... colorful table output ...]

# JSON format (for scripts)
$ bughive crawl https://example.com --output json
{"session_id": "...", "pages_crawled": 10, ...}

# Markdown format (for docs)
$ bughive crawl https://example.com --output markdown
# Crawl Summary
...
```

### Piping and Processing

```bash
# Get session ID from async crawl
$ SESSION=$(bughive crawl https://example.com --async --output json | jq -r '.session_id')
$ echo $SESSION
a1b2c3d4-5678-90ab-cdef-1234567890ab

# Count critical bugs
$ bughive bugs $SESSION --priority critical --output json | jq '.total'
3

# Export bugs to file
$ bughive bugs $SESSION --output json > bugs.json
```

### CI/CD Integration

```bash
#!/bin/bash
# In GitHub Actions or GitLab CI

set -e

# Start crawl
echo "Starting QA crawl..."
SESSION=$(bughive crawl https://staging.example.com \
  --max-pages 30 \
  --output json | jq -r '.session_id')

echo "Session: $SESSION"

# Wait for completion
while true; do
  STATUS=$(bughive status $SESSION --output json | jq -r '.status')
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 10
done

# Check for critical bugs
CRITICAL=$(bughive bugs $SESSION --priority critical --output json | jq '.total')

if [ "$CRITICAL" -gt 0 ]; then
  echo "❌ Found $CRITICAL critical bugs - blocking deployment"
  bughive bugs $SESSION --priority critical
  exit 1
fi

echo "✅ QA passed - no critical bugs found"
```

## Color Reference

The CLI uses semantic colors consistently:

- **Cyan** (🔵): Headers, labels, primary UI elements
- **Green** (🟢): Success states, checkmarks, completed items
- **Yellow** (🟡): Warnings, pending states, high priority
- **Red** (🔴): Errors, failures, critical bugs
- **Blue** (💙): Medium priority, info messages
- **Dim** (⚪): Secondary text, timestamps, hints

## Emojis & Icons

- 🐝 BugHive branding
- ✓ Success / Completed
- ✗ Failure / Error
- ⏳ Pending
- 🔄 Running / In Progress
- ⊘ Cancelled
- 🔴 Critical priority
- 🟡 High priority
- 🔵 Medium priority
- ⚪ Low priority
- ⚠️ Warning
- ❌ Critical error
- ✅ All good

---

All examples shown here are representative of the actual CLI output when using a properly configured BugHive installation.
