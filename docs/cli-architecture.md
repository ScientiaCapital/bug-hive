# BugHive CLI Architecture

## Overview

The BugHive CLI provides a beautiful, user-friendly interface to the autonomous QA system, built with Click for command handling and Rich for terminal output.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        BugHive CLI                          │
│                    (src/cli/main.py)                        │
└───────────────┬─────────────────────────────────────────────┘
                │
                ├──────────────┬──────────────┬──────────────┐
                │              │              │              │
        ┌───────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐ ┌─────▼─────┐
        │   Commands   │ │  Output  │ │   Config    │ │  Session  │
        │              │ │ Formatter│ │   Manager   │ │  Manager  │
        └───────┬──────┘ └────┬─────┘ └──────┬──────┘ └─────┬─────┘
                │              │              │              │
        ┌───────▼──────────────▼──────────────▼──────────────▼─────┐
        │                    Core Components                        │
        ├───────────────────────────────────────────────────────────┤
        │  • Click Framework (CLI routing)                          │
        │  • Rich Library (Beautiful output)                        │
        │  • Async/Sync execution modes                             │
        └───────────────────────────┬───────────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
        ┌───────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
        │   Workflow   │    │   Celery    │    │  Database   │
        │   (Sync)     │    │   (Async)   │    │   (Status)  │
        │              │    │             │    │             │
        │ run_bughive()│    │run_crawl_   │    │  Sessions   │
        │              │    │session()    │    │  Bugs       │
        └──────────────┘    └─────────────┘    └─────────────┘
```

## Component Details

### 1. CLI Entry Point (`src/cli/main.py`)

The main Click application with command groups:

- **`cli()`**: Root command group
- **Command decorators**: Define each subcommand
- **Rich Console**: Terminal output manager

### 2. Commands

Each command is a Click-decorated function:

| Command | Purpose | Sync/Async |
|---------|---------|------------|
| `crawl` | Start crawl session | Both |
| `status` | Check session status | Read-only |
| `bugs` | List bugs found | Read-only |
| `report` | Generate reports | Read-only |
| `sessions` | List sessions | Read-only |
| `config` | Show configuration | Read-only |
| `doctor` | Run diagnostics | Read-only |

### 3. Output Formatting

Rich provides multiple output types:

```python
# Tables
table = Table(title="Results", box=box.ROUNDED)
table.add_column("Name", style="cyan")
table.add_column("Value", style="green")

# Panels
Panel.fit("Message", border_style="cyan")

# Progress bars
with Progress() as progress:
    task = progress.add_task("Working...", total=100)

# Live updates
with Live(get_status(), refresh_per_second=1) as live:
    # Updates automatically
```

### 4. Execution Modes

#### Synchronous Mode (Default)
```
User → CLI → run_bughive() → LangGraph → Results → Display
                ↓
            Progress bars & live updates
```

#### Asynchronous Mode (--async)
```
User → CLI → Celery.delay() → Task ID → Display
                ↓
            Background worker executes
                ↓
        User checks status with 'bughive status'
```

## Data Flow

### Crawl Command Flow

```
1. User Input
   ├── Parse arguments (Click)
   ├── Validate options
   └── Build config dict

2. Execution
   ├── Sync: run_bughive(config)
   │   ├── Initialize LangGraph workflow
   │   ├── Execute crawl with progress bars
   │   └── Return summary
   │
   └── Async: run_crawl_session.delay(config)
       ├── Queue task in Celery
       ├── Return task ID
       └── Background worker executes

3. Output
   ├── Format results (Rich)
   ├── Display tables/panels
   └── Show next steps
```

### Status Command Flow

```
1. User Input
   └── Session ID

2. Fetch Data
   ├── Query SessionManager
   └── Get current state

3. Display
   ├── One-time: Show table
   └── Watch mode: Live updates every N seconds
```

## Rich Output Components

### 1. Tables

```python
table = Table(
    title="Session Status",
    box=box.ROUNDED,
    border_style="cyan",
    show_header=True,
    header_style="bold cyan"
)
```

**Used for:**
- Configuration display
- Session status
- Bug listings
- Crawl summaries

### 2. Panels

```python
Panel.fit(
    "[bold green]Success![/bold green]",
    border_style="green",
    title="Crawl Complete"
)
```

**Used for:**
- Success/error messages
- Important notifications
- Command headers

### 3. Progress Bars

```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TimeElapsedColumn()
) as progress:
    task = progress.add_task("Crawling...", total=100)
```

**Used for:**
- Synchronous crawls
- Long-running operations
- Live feedback

### 4. Live Updates

```python
with Live(get_status_table(), refresh_per_second=1) as live:
    while True:
        time.sleep(interval)
        live.update(get_status_table())
```

**Used for:**
- Watch mode in status command
- Real-time monitoring

## Configuration Management

### Settings Loading

```python
from src.core.config import get_settings

settings = get_settings()  # Loads from .env
```

### Secrets Masking

```python
def _mask_url(url: str) -> str:
    """Mask credentials in URLs"""
    # postgresql://user:pass@host/db
    # → postgresql://***:***@host/db

def _mask_secret(secret: str, show: bool) -> str:
    """Mask API keys"""
    # sk-ant-1234567890abcdef
    # → sk-a...cdef
```

## Error Handling

### Strategy

1. **Input Validation**: Click validates arguments/options
2. **Try/Catch**: Wrap API calls in try/except
3. **Rich Display**: Show errors in red with proper formatting
4. **Exit Codes**: Use `raise click.Abort()` for clean exits

### Example

```python
try:
    result = await run_bughive(config)
except Exception as e:
    console.print(f"[red]✗ Error:[/red] {str(e)}")
    if console.is_terminal:
        console.print_exception()
    raise click.Abort()
```

## Styling Guidelines

### Colors

- **Cyan**: Primary brand color, headers, labels
- **Green**: Success, completed status, checkmarks
- **Yellow**: Warnings, pending status, caution
- **Red**: Errors, failed status, critical bugs
- **Dim**: Secondary info, hints, timestamps

### Icons

- ✓ Success
- ✗ Failure
- ⏳ Pending
- 🔄 Running
- ⊘ Cancelled
- 🐝 BugHive branding
- 🔴 Critical priority
- 🟡 High priority
- 🔵 Medium priority
- ⚪ Low priority

### Typography

- **Bold**: Important info, titles
- **Dim**: Secondary info, hints
- **Italic**: Not supported in all terminals, use sparingly
- **Underline**: Links, emphasis

## Testing

### Manual Testing

```bash
# Test all commands
./examples/cli_demo.sh
```

### Unit Testing

```python
from click.testing import CliRunner
from src.cli.main import cli

def test_config_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['config'])
    assert result.exit_code == 0
```

## Extension Points

### Adding New Commands

```python
@cli.command()
@click.argument("arg_name")
@click.option("--option", "-o", help="Description")
def new_command(arg_name, option):
    """Command description."""
    # Implementation
    console.print("[cyan]Working...[/cyan]")
```

### Custom Output Formats

```python
def _display_custom(data: dict, format: str):
    if format == "table":
        # Rich table
    elif format == "json":
        console.print_json(data=data)
    elif format == "markdown":
        console.print(Markdown(text))
```

## Best Practices

1. **Always mask secrets** in output
2. **Provide helpful error messages** with suggestions
3. **Use progress indicators** for long operations
4. **Support both sync and async** when applicable
5. **Include examples** in command help text
6. **Validate early** to fail fast
7. **Use semantic colors** consistently
8. **Add --help to all commands**
9. **Support shortened UUIDs** for convenience
10. **Test in different terminals** for compatibility

## Performance Considerations

### Async Benefits

- **Non-blocking**: CLI returns immediately
- **Scalable**: Multiple crawls in parallel
- **Monitorable**: Check status anytime

### Sync Benefits

- **Immediate results**: See output right away
- **Simpler workflow**: No worker setup needed
- **Better for small tasks**: Quick tests, demos

## Dependencies

- **Click 8.1+**: CLI framework
- **Rich 13.0+**: Terminal output
- **Python 3.12+**: Modern Python features

## Future Enhancements

- [ ] Shell completion (bash, zsh, fish)
- [ ] Interactive mode with prompts
- [ ] TUI (Text User Interface) for advanced monitoring
- [ ] Export to CSV/Excel
- [ ] Integration with Jira/GitHub Issues
- [ ] Scheduled crawls (cron-like)
- [ ] Diff mode (compare two sessions)
- [ ] Screenshot capture in reports
