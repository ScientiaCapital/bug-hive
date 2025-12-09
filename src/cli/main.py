"""BugHive CLI - Main entry point for command-line interface."""

import asyncio
import uuid
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich import box

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="BugHive")
def cli():
    """
    🐝 BugHive - Autonomous QA Agent System

    Automated web crawling, testing, and bug detection powered by AI.
    """
    pass


@cli.command()
@click.argument("url")
@click.option("--max-pages", "-m", default=50, help="Maximum pages to crawl")
@click.option("--max-depth", "-d", default=5, help="Maximum crawl depth")
@click.option("--auth", type=click.Choice(["none", "session", "oauth", "api_key"]), default="none", help="Authentication method")
@click.option("--username", "-u", help="Username for session auth")
@click.option("--password", "-p", help="Password for session auth", hide_input=True)
@click.option("--linear-team", help="Linear team ID for ticket creation")
@click.option("--async", "run_async", is_flag=True, help="Run in background via Celery")
@click.option("--output", "-o", type=click.Choice(["json", "table", "markdown"]), default="table", help="Output format")
def crawl(url: str, max_pages: int, max_depth: int, auth: str, username: Optional[str],
          password: Optional[str], linear_team: Optional[str], run_async: bool, output: str):
    """
    Start a new crawl session.

    URL: The base URL to start crawling from

    Examples:

        # Quick crawl with defaults
        bughive crawl https://example.com

        # Crawl with authentication
        bughive crawl https://app.example.com --auth session -u user -p

        # Background crawl with Linear integration
        bughive crawl https://example.com --async --linear-team TEAM-123
    """

    console.print(Panel.fit(
        f"[bold cyan]🐝 BugHive[/bold cyan]\n\n"
        f"[dim]Starting autonomous QA session[/dim]\n"
        f"[bold]{url}[/bold]",
        border_style="cyan",
        title="[bold]Crawl Session[/bold]",
        subtitle=f"Max Pages: {max_pages} | Max Depth: {max_depth}"
    ))

    # Validate auth requirements
    if auth == "session" and (not username or not password):
        console.print("[red]✗[/red] Session auth requires --username and --password")
        raise click.Abort()

    # Build config
    session_id = str(uuid.uuid4())
    config = {
        "base_url": url,
        "max_pages": max_pages,
        "max_depth": max_depth,
        "auth_method": auth,
        "credentials": {"username": username, "password": password} if auth == "session" else None,
        "linear_team_id": linear_team,
        "session_id": session_id,
    }

    if run_async:
        # Queue via Celery
        try:
            from src.workers.tasks import run_crawl_session
            task = run_crawl_session.delay(session_id, config)

            console.print()
            console.print(f"[green]✓[/green] Crawl queued successfully")
            console.print()

            table = Table(show_header=False, box=box.ROUNDED, border_style="green")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Session ID", session_id[:12] + "...")
            table.add_row("Task ID", task.id)
            table.add_row("Status", "Queued")

            console.print(table)
            console.print()
            console.print(f"[dim]Use [bold]bughive status {session_id}[/bold] to check progress[/dim]")

        except Exception as e:
            console.print(f"[red]✗ Failed to queue crawl:[/red] {str(e)}")
            raise click.Abort()
    else:
        # Run synchronously with progress
        try:
            from src.graph.workflow import run_bughive

            console.print()
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                crawl_task = progress.add_task("[cyan]Initializing crawl...", total=max_pages)

                # Run the workflow
                summary = asyncio.run(run_bughive(config))
                progress.update(crawl_task, completed=max_pages, description="[green]Crawl complete!")

            console.print()
            _display_summary(summary, output_format=output)

        except Exception as e:
            console.print(f"\n[red]✗ Crawl failed:[/red] {str(e)}")
            if console.is_terminal:
                console.print_exception()
            raise click.Abort()


@cli.command()
@click.argument("session_id")
@click.option("--watch", "-w", is_flag=True, help="Watch status in real-time")
@click.option("--interval", "-i", default=5, help="Refresh interval for watch mode (seconds)")
def status(session_id: str, watch: bool, interval: int):
    """
    Check status of a crawl session.

    SESSION_ID: The UUID of the crawl session (can be shortened to first 8 chars)

    Examples:

        # Check status once
        bughive status abc12345

        # Watch status in real-time
        bughive status abc12345 --watch
    """

    from src.workers.session_manager import SessionManager

    manager = SessionManager()

    def get_status_table():
        state = manager.get_session_state(session_id)

        if not state:
            return Panel("[red]Session not found[/red]", border_style="red")

        status_emoji = {
            "pending": "⏳",
            "running": "🔄",
            "completed": "✓",
            "failed": "✗",
            "cancelled": "⊘"
        }.get(state.get("status", "unknown"), "❓")

        status_color = {
            "pending": "yellow",
            "running": "cyan",
            "completed": "green",
            "failed": "red",
            "cancelled": "dim"
        }.get(state.get("status", "unknown"), "white")

        table = Table(
            title=f"Session {session_id[:12]}...",
            box=box.ROUNDED,
            border_style=status_color,
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="green")

        table.add_row("Status", f"{status_emoji} [{status_color}]{state.get('status', 'unknown').upper()}[/{status_color}]")
        table.add_row("Base URL", state.get("base_url", "N/A"))
        table.add_row("Pages Crawled", f"{state.get('pages_crawled', 0)} / {state.get('max_pages', '?')}")
        table.add_row("Bugs Found", str(state.get("bugs_found", 0)))
        table.add_row("Current Depth", str(state.get("current_depth", 0)))

        if state.get("started_at"):
            table.add_row("Started", _format_timestamp(state["started_at"]))

        if state.get("completed_at"):
            table.add_row("Completed", _format_timestamp(state["completed_at"]))

        if state.get("total_cost"):
            table.add_row("Total Cost", f"${state['total_cost']:.4f}")

        return table

    if watch:
        try:
            with Live(get_status_table(), refresh_per_second=1/interval, console=console) as live:
                while True:
                    import time
                    time.sleep(interval)
                    live.update(get_status_table())
        except KeyboardInterrupt:
            console.print("\n[yellow]Watch mode stopped[/yellow]")
    else:
        console.print(get_status_table())


@cli.command()
@click.argument("session_id")
@click.option("--priority", "-p", type=click.Choice(["critical", "high", "medium", "low"]), help="Filter by priority")
@click.option("--limit", "-l", default=50, help="Maximum number of bugs to show")
@click.option("--output", "-o", type=click.Choice(["table", "json", "markdown"]), default="table", help="Output format")
def bugs(session_id: str, priority: Optional[str], limit: int, output: str):
    """
    List bugs found in a session.

    SESSION_ID: The UUID of the crawl session

    Examples:

        # Show all bugs
        bughive bugs abc12345

        # Show only critical bugs
        bughive bugs abc12345 --priority critical

        # Export as JSON
        bughive bugs abc12345 --output json
    """

    console.print(f"[cyan]Fetching bugs for session {session_id[:12]}...[/cyan]")

    # TODO: Implement database query
    # For now, show a mock example

    if output == "table":
        table = Table(
            title=f"Bugs Found{' (' + priority.upper() + ')' if priority else ''}",
            box=box.ROUNDED,
            border_style="yellow",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("ID", style="dim", width=8)
        table.add_column("Priority", width=10)
        table.add_column("Type", width=15)
        table.add_column("Page", width=30)
        table.add_column("Description", width=40)

        # Mock data - replace with actual DB query
        console.print(table)
        console.print("[dim]Database integration pending[/dim]")

    elif output == "json":
        console.print_json('{"bugs": [], "total": 0}')

    elif output == "markdown":
        md = "# Bugs Report\n\nNo bugs found yet."
        console.print(Markdown(md))


@cli.command()
@click.argument("session_id")
@click.option("--format", "-f", type=click.Choice(["html", "pdf", "markdown", "json"]), default="markdown", help="Report format")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def report(session_id: str, format: str, output: Optional[str]):
    """
    Generate a detailed report for a session.

    SESSION_ID: The UUID of the crawl session

    Examples:

        # Generate markdown report
        bughive report abc12345

        # Generate HTML report to file
        bughive report abc12345 --format html --output report.html
    """

    console.print(f"[cyan]Generating {format.upper()} report for session {session_id[:12]}...[/cyan]")

    # TODO: Implement report generation
    console.print("[yellow]Report generation coming soon[/yellow]")


@cli.command()
@click.option("--show-secrets", is_flag=True, help="Show full API keys (use with caution)")
def config(show_secrets: bool):
    """
    Show current BugHive configuration.

    Displays environment settings, API key status, and service connections.

    Examples:

        # Show config (masked)
        bughive config

        # Show full config with secrets
        bughive config --show-secrets
    """

    try:
        from src.core.config import get_settings

        settings = get_settings()

        table = Table(
            title="🐝 BugHive Configuration",
            box=box.DOUBLE,
            border_style="cyan",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Value", style="green")
        table.add_column("Status", width=10)

        # Environment
        table.add_row("Environment", settings.environment, _status_icon(True))
        table.add_row("Debug Mode", str(settings.debug), _status_icon(settings.debug))

        # Database
        db_configured = bool(settings.database_url)
        table.add_row(
            "Database URL",
            settings.database_url if show_secrets else _mask_url(settings.database_url),
            _status_icon(db_configured)
        )

        # Redis
        redis_configured = bool(settings.redis_url)
        table.add_row(
            "Redis URL",
            settings.redis_url if show_secrets else _mask_url(settings.redis_url),
            _status_icon(redis_configured)
        )

        # API Keys
        browserbase_configured = bool(getattr(settings, 'browserbase_api_key', None))
        table.add_row(
            "Browserbase API",
            _mask_secret(settings.browserbase_api_key if hasattr(settings, 'browserbase_api_key') else None, show_secrets),
            _status_icon(browserbase_configured)
        )

        anthropic_configured = bool(getattr(settings, 'anthropic_api_key', None))
        table.add_row(
            "Anthropic API",
            _mask_secret(settings.anthropic_api_key if hasattr(settings, 'anthropic_api_key') else None, show_secrets),
            _status_icon(anthropic_configured)
        )

        openrouter_configured = bool(getattr(settings, 'openrouter_api_key', None))
        table.add_row(
            "OpenRouter API",
            _mask_secret(settings.openrouter_api_key if hasattr(settings, 'openrouter_api_key') else None, show_secrets),
            _status_icon(openrouter_configured)
        )

        # Linear
        linear_configured = bool(getattr(settings, 'linear_api_key', None))
        table.add_row(
            "Linear API",
            _mask_secret(settings.linear_api_key if hasattr(settings, 'linear_api_key') else None, show_secrets),
            _status_icon(linear_configured)
        )

        console.print(table)

        # Warnings
        if not all([browserbase_configured, anthropic_configured or openrouter_configured]):
            console.print()
            console.print(Panel(
                "[yellow]⚠️  Some services are not configured.[/yellow]\n\n"
                "BugHive requires:\n"
                "• Browserbase API key for web crawling\n"
                "• Anthropic or OpenRouter API key for AI analysis\n\n"
                "Set these in your .env file.",
                border_style="yellow",
                title="[bold]Configuration Warning[/bold]"
            ))

    except Exception as e:
        console.print(f"[red]✗ Failed to load configuration:[/red] {str(e)}")
        raise click.Abort()


@cli.command()
@click.option("--limit", "-l", default=20, help="Number of sessions to show")
def sessions(limit: int):
    """
    List recent crawl sessions.

    Shows a table of recent sessions with their status and basic metrics.

    Examples:

        # Show last 20 sessions
        bughive sessions

        # Show last 50 sessions
        bughive sessions --limit 50
    """

    console.print("[cyan]Fetching recent sessions...[/cyan]")

    # TODO: Query database for sessions
    console.print("[yellow]Session history coming soon[/yellow]")


@cli.command()
def doctor():
    """
    Run diagnostic checks on BugHive installation.

    Verifies that all dependencies and services are properly configured.
    """

    console.print(Panel.fit(
        "[bold cyan]🐝 BugHive Doctor[/bold cyan]\n\n"
        "[dim]Running diagnostic checks...[/dim]",
        border_style="cyan"
    ))

    checks = []

    # Check Python version
    import sys
    python_ok = sys.version_info >= (3, 11)
    checks.append(("Python 3.11+", python_ok, f"Python {sys.version_info.major}.{sys.version_info.minor}"))

    # Check dependencies
    try:
        import playwright
        playwright_ok = True
    except ImportError:
        playwright_ok = False
    checks.append(("Playwright", playwright_ok, "Installed" if playwright_ok else "Not found"))

    try:
        from src.core.config import get_settings
        config_ok = True
    except Exception:
        config_ok = False
    checks.append(("Configuration", config_ok, "Valid" if config_ok else "Invalid"))

    # Check services
    try:
        from src.core.config import get_settings
        settings = get_settings()
        db_ok = bool(settings.database_url)
        redis_ok = bool(settings.redis_url)
        browserbase_ok = bool(getattr(settings, 'browserbase_api_key', None))
    except Exception:
        db_ok = redis_ok = browserbase_ok = False

    checks.append(("Database", db_ok, "Configured" if db_ok else "Not configured"))
    checks.append(("Redis", redis_ok, "Configured" if redis_ok else "Not configured"))
    checks.append(("Browserbase", browserbase_ok, "Configured" if browserbase_ok else "Not configured"))

    # Display results
    console.print()
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Check", style="cyan")
    table.add_column("Status", width=10)
    table.add_column("Details", style="dim")

    all_ok = True
    for name, ok, details in checks:
        status = "[green]✓[/green]" if ok else "[red]✗[/red]"
        table.add_row(name, status, details)
        if not ok:
            all_ok = False

    console.print(table)
    console.print()

    if all_ok:
        console.print(Panel(
            "[bold green]All checks passed! BugHive is ready to use.[/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[bold yellow]Some checks failed. Please review the configuration.[/bold yellow]\n\n"
            "Run [bold]bughive config[/bold] for more details.",
            border_style="yellow"
        ))


def _display_summary(summary: dict, output_format: str = "table"):
    """Display crawl summary in a nice format."""

    if output_format == "json":
        console.print_json(data=summary)
        return

    if output_format == "markdown":
        md = f"""
# Crawl Summary

## Results
- **Pages Crawled**: {summary.get('pages_crawled', 0)}
- **Bugs Found**: {summary.get('bugs_found', 0)}
- **Tickets Created**: {summary.get('tickets_created', 0)}
- **Total Cost**: ${summary.get('total_cost', 0):.4f}
- **Duration**: {summary.get('duration', 0):.1f}s

## Bugs by Priority
"""
        if summary.get("bugs_by_priority"):
            for priority, count in summary["bugs_by_priority"].items():
                md += f"- **{priority.capitalize()}**: {count}\n"

        console.print(Markdown(md))
        return

    # Table format (default)
    console.print()
    console.print(Panel.fit(
        "[bold green]✓ Crawl Complete![/bold green]",
        border_style="green"
    ))

    table = Table(box=box.ROUNDED, border_style="green", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="green")

    table.add_row("Pages Crawled", str(summary.get("pages_crawled", 0)))
    table.add_row("Bugs Found", str(summary.get("bugs_found", 0)))
    table.add_row("Tickets Created", str(summary.get("tickets_created", 0)))
    table.add_row("Total Cost", f"${summary.get('total_cost', 0):.4f}")
    table.add_row("Duration", f"{summary.get('duration', 0):.1f}s")

    console.print(table)

    # Show bugs by priority
    if summary.get("bugs_by_priority"):
        console.print()
        console.print("[bold]Bugs by Priority:[/bold]")
        for priority, count in summary["bugs_by_priority"].items():
            color = {
                "critical": "red",
                "high": "yellow",
                "medium": "blue",
                "low": "dim"
            }.get(priority, "white")
            emoji = {
                "critical": "🔴",
                "high": "🟡",
                "medium": "🔵",
                "low": "⚪"
            }.get(priority, "•")
            console.print(f"  {emoji} [{color}]{priority.capitalize()}[/{color}]: {count}")


def _mask_url(url: str) -> str:
    """Mask sensitive parts of URLs."""
    if not url:
        return "[dim]Not configured[/dim]"

    if "://" in url:
        parts = url.split("://")
        protocol = parts[0]
        rest = parts[1]

        if "@" in rest:
            # Mask credentials
            creds, host = rest.split("@", 1)
            return f"{protocol}://***:***@{host}"

        # Mask host details but keep protocol
        return f"{protocol}://***"

    return url


def _mask_secret(secret: Optional[str], show: bool = False) -> str:
    """Mask API keys and secrets."""
    if not secret:
        return "[dim]Not configured[/dim]"

    if show:
        return secret

    if len(secret) > 8:
        return f"{secret[:4]}...{secret[-4:]}"

    return "***"


def _status_icon(configured: bool) -> str:
    """Return a status icon."""
    return "[green]✓[/green]" if configured else "[red]✗[/red]"


def _format_timestamp(ts) -> str:
    """Format timestamp for display."""
    if isinstance(ts, str):
        return ts
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return str(ts)


if __name__ == "__main__":
    cli()
