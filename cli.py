#!/usr/bin/env python3
"""BugHive CLI - Autonomous QA Agent System.

Command-line interface for running autonomous QA crawls.
"""

import asyncio
import logging
from pathlib import Path
import json
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.graph import run_bughive, resume_bughive, quick_crawl, deep_crawl

console = Console()


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="BugHive")
def cli():
    """BugHive - Autonomous QA Agent System powered by LangGraph and Claude."""
    pass


@cli.command()
@click.argument("url")
@click.option("--max-pages", default=10, help="Maximum pages to crawl")
@click.option("--max-depth", default=2, help="Maximum link depth")
@click.option("--focus-areas", multiple=True, help="Focus areas (forms, navigation, etc.)")
@click.option("--create-tickets/--no-tickets", default=False, help="Create Linear tickets")
@click.option("--linear-team-id", help="Linear team ID for ticket creation")
@click.option("--quality-threshold", default=0.7, type=float, help="Confidence threshold")
@click.option("--output", "-o", help="Output file for summary JSON")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def crawl(
    url: str,
    max_pages: int,
    max_depth: int,
    focus_areas: tuple,
    create_tickets: bool,
    linear_team_id: Optional[str],
    quality_threshold: float,
    output: Optional[str],
    verbose: bool,
):
    """Run a QA crawl on the specified URL.

    Example:

        bughive crawl https://example.com --max-pages 50 --focus-areas forms --focus-areas navigation
    """
    setup_logging(verbose)

    config = {
        "base_url": url,
        "max_pages": max_pages,
        "max_depth": max_depth,
        "focus_areas": list(focus_areas) if focus_areas else ["all"],
        "quality_threshold": quality_threshold,
        "create_linear_tickets": create_tickets,
    }

    if linear_team_id:
        config["linear_team_id"] = linear_team_id

    console.print(f"\n[bold blue]Starting BugHive crawl...[/bold blue]")
    console.print(f"URL: {url}")
    console.print(f"Max Pages: {max_pages}")
    console.print(f"Max Depth: {max_depth}")
    console.print(f"Focus Areas: {config['focus_areas']}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Crawling and analyzing...", total=None)

        try:
            summary = asyncio.run(run_bughive(config))

            progress.update(task, completed=True, description="[green]Crawl complete!")

            # Display summary
            display_summary(summary)

            # Save to file if requested
            if output:
                output_path = Path(output)
                output_path.write_text(json.dumps(summary, indent=2))
                console.print(f"\n[green]Summary saved to: {output}[/green]")

        except Exception as e:
            progress.update(task, description=f"[red]Error: {e}[/red]")
            console.print(f"\n[red]Crawl failed: {e}[/red]")
            raise click.Abort()


@cli.command()
@click.argument("url")
@click.option("--max-pages", default=10, help="Maximum pages to crawl")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def quick(url: str, max_pages: int, verbose: bool):
    """Quick crawl for testing or small sites.

    Example:

        bughive quick https://example.com
    """
    setup_logging(verbose)

    console.print(f"\n[bold blue]Quick crawl: {url}[/bold blue]")

    try:
        summary = asyncio.run(quick_crawl(url, max_pages=max_pages))
        display_summary(summary)

    except Exception as e:
        console.print(f"\n[red]Quick crawl failed: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument("url")
@click.option("--max-pages", default=100, help="Maximum pages to crawl")
@click.option("--focus-areas", multiple=True, help="Focus areas")
@click.option("--linear-team-id", help="Linear team ID for ticket creation")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def deep(
    url: str,
    max_pages: int,
    focus_areas: tuple,
    linear_team_id: Optional[str],
    verbose: bool,
):
    """Comprehensive deep crawl with full analysis.

    Example:

        bughive deep https://example.com --focus-areas forms --linear-team-id TEAM123
    """
    setup_logging(verbose)

    console.print(f"\n[bold blue]Deep crawl: {url}[/bold blue]")

    try:
        summary = asyncio.run(
            deep_crawl(
                url,
                max_pages=max_pages,
                focus_areas=list(focus_areas) if focus_areas else None,
                linear_team_id=linear_team_id,
            )
        )
        display_summary(summary)

    except Exception as e:
        console.print(f"\n[red]Deep crawl failed: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument("session_id")
@click.option("--checkpoint-db", default="checkpoints.db", help="Checkpoint database path")
@click.option("--max-pages", type=int, help="Update max pages limit")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def resume(
    session_id: str,
    checkpoint_db: str,
    max_pages: Optional[int],
    verbose: bool,
):
    """Resume a checkpointed crawl session.

    Example:

        bughive resume abc-123-def-456
    """
    setup_logging(verbose)

    from langgraph.checkpoint.sqlite import SqliteSaver

    console.print(f"\n[bold blue]Resuming session: {session_id}[/bold blue]")

    try:
        checkpointer = SqliteSaver.from_conn_string(checkpoint_db)

        updates = {}
        if max_pages is not None:
            updates["max_pages"] = max_pages

        summary = asyncio.run(
            resume_bughive(
                session_id=session_id,
                checkpointer=checkpointer,
                updates=updates if updates else None,
            )
        )

        display_summary(summary)

    except ValueError as e:
        console.print(f"\n[red]No checkpoint found for session: {session_id}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"\n[red]Resume failed: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.option("--output", "-o", default="workflow.png", help="Output diagram path")
def visualize(output: str):
    """Generate a visual diagram of the BugHive workflow.

    Example:

        bughive visualize -o docs/workflow.png
    """
    from src.graph import visualize_workflow

    console.print(f"\n[bold blue]Generating workflow diagram...[/bold blue]")

    try:
        visualize_workflow(output)
        console.print(f"[green]Diagram saved to: {output}[/green]")

    except Exception as e:
        console.print(f"\n[red]Visualization failed: {e}[/red]")
        console.print("Install graphviz: brew install graphviz")
        raise click.Abort()


def display_summary(summary: dict):
    """Display crawl summary in a formatted table."""
    console.print("\n[bold green]Crawl Summary[/bold green]")

    # Basic info
    info_table = Table(show_header=False)
    info_table.add_column("Field", style="cyan")
    info_table.add_column("Value", style="white")

    info_table.add_row("Session ID", summary.get("session_id", "N/A"))
    info_table.add_row("Duration", f"{summary.get('duration_seconds', 0):.1f}s")
    info_table.add_row("Total Cost", f"${summary.get('cost', {}).get('total_usd', 0):.2f}")

    console.print(info_table)

    # Pages
    console.print("\n[bold]Pages[/bold]")
    pages_table = Table(show_header=False)
    pages_table.add_column("Metric", style="cyan")
    pages_table.add_column("Count", style="white")

    pages = summary.get("pages", {})
    pages_table.add_row("Discovered", str(pages.get("total_discovered", 0)))
    pages_table.add_row("Crawled", str(pages.get("total_crawled", 0)))
    pages_table.add_row("Failed", str(pages.get("failed", 0)))

    console.print(pages_table)

    # Bugs
    console.print("\n[bold]Bugs[/bold]")
    bugs_table = Table(show_header=False)
    bugs_table.add_column("Metric", style="cyan")
    bugs_table.add_column("Count", style="white")

    bugs = summary.get("bugs", {})
    bugs_table.add_row("Raw Issues", str(bugs.get("raw_issues_found", 0)))
    bugs_table.add_row("Validated Bugs", str(bugs.get("validated_bugs", 0)))
    bugs_table.add_row("Duplicates Filtered", str(bugs.get("duplicates_filtered", 0)))

    console.print(bugs_table)

    # Bugs by priority
    by_priority = bugs.get("by_priority", {})
    if by_priority:
        console.print("\n[bold]By Priority[/bold]")
        priority_table = Table(show_header=False)
        priority_table.add_column("Priority", style="cyan")
        priority_table.add_column("Count", style="white")

        for priority in ["critical", "high", "medium", "low"]:
            if priority in by_priority:
                style = "red" if priority == "critical" else "yellow" if priority == "high" else "white"
                priority_table.add_row(priority.capitalize(), str(by_priority[priority]), style=style)

        console.print(priority_table)

    # Bugs by category
    by_category = bugs.get("by_category", {})
    if by_category:
        console.print("\n[bold]By Category[/bold]")
        category_table = Table(show_header=False)
        category_table.add_column("Category", style="cyan")
        category_table.add_column("Count", style="white")

        for category, count in sorted(by_category.items(), key=lambda x: -x[1])[:5]:
            category_table.add_row(category, str(count))

        console.print(category_table)

    # Linear tickets
    linear = summary.get("linear_tickets", {})
    if linear.get("total_created", 0) > 0:
        console.print("\n[bold]Linear Tickets[/bold]")
        console.print(f"Created: {linear['total_created']}")

        if linear.get("ticket_urls"):
            console.print("\nTicket URLs:")
            for url in linear["ticket_urls"][:5]:
                console.print(f"  - {url}")

    # Recommendations
    recommendations = summary.get("recommendations", [])
    if recommendations:
        console.print("\n[bold yellow]Recommendations[/bold yellow]")
        for rec in recommendations:
            console.print(f"  - {rec}")

    # Cost breakdown
    cost_by_node = summary.get("cost", {}).get("by_node", {})
    if cost_by_node:
        console.print("\n[bold]Cost Breakdown[/bold]")
        cost_table = Table(show_header=False)
        cost_table.add_column("Node", style="cyan")
        cost_table.add_column("Cost", style="white")

        for node, cost in sorted(cost_by_node.items(), key=lambda x: -x[1])[:5]:
            cost_table.add_row(node, f"${cost:.4f}")

        console.print(cost_table)


if __name__ == "__main__":
    cli()
