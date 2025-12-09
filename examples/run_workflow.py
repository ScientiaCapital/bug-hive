"""Example script demonstrating the BugHive LangGraph workflow.

This shows how to run autonomous QA crawls with different configurations.
"""

import asyncio
import logging
from pathlib import Path

from src.graph import run_bughive, quick_crawl, deep_crawl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def example_quick_crawl():
    """Example: Quick crawl for testing or small sites."""
    logger.info("=== Example 1: Quick Crawl ===")

    summary = await quick_crawl(
        url="https://example.com",
        max_pages=10,
        create_tickets=False,
    )

    print("\n--- Quick Crawl Summary ---")
    print(f"Session ID: {summary.get('session_id')}")
    print(f"Pages crawled: {summary['pages']['total_crawled']}")
    print(f"Bugs found: {summary['bugs']['validated_bugs']}")
    print(f"Total cost: ${summary['cost']['total_usd']:.2f}")
    print(f"Duration: {summary['duration_seconds']:.1f}s")
    print(f"\nBugs by priority: {summary['bugs']['by_priority']}")
    print(f"Bugs by category: {summary['bugs']['by_category']}")


async def example_deep_crawl():
    """Example: Comprehensive deep crawl with full analysis."""
    logger.info("=== Example 2: Deep Crawl ===")

    summary = await deep_crawl(
        url="https://example.com",
        max_pages=100,
        focus_areas=["forms", "navigation", "accessibility"],
        linear_team_id="TEAM123",  # Replace with your Linear team ID
    )

    print("\n--- Deep Crawl Summary ---")
    print(f"Session ID: {summary.get('session_id')}")
    print(f"Pages crawled: {summary['pages']['total_crawled']}")
    print(f"Bugs found: {summary['bugs']['validated_bugs']}")
    print(f"Linear tickets created: {summary['linear_tickets']['total_created']}")
    print(f"Total cost: ${summary['cost']['total_usd']:.2f}")
    print(f"Duration: {summary['duration_seconds']:.1f}s")

    if summary.get("recommendations"):
        print("\n--- Recommendations ---")
        for rec in summary["recommendations"]:
            print(f"- {rec}")


async def example_custom_config():
    """Example: Custom configuration with specific requirements."""
    logger.info("=== Example 3: Custom Configuration ===")

    config = {
        # Base settings
        "base_url": "https://example.com",
        "max_pages": 50,
        "max_depth": 3,

        # Focus areas (what to test)
        "focus_areas": [
            "forms",           # Form validation, inputs
            "authentication",  # Login, signup, password reset
            "navigation",      # Links, menus, routing
            "accessibility",   # WCAG compliance, screen readers
            "performance",     # Load times, resource sizes
        ],

        # Quality settings
        "quality_mode": "comprehensive",  # "balanced" | "comprehensive" | "fast"
        "quality_threshold": 0.8,         # Confidence threshold for bugs

        # Integration
        "create_linear_tickets": True,
        "linear_team_id": "TEAM123",

        # Advanced options
        "strategy": {
            "initial_pages": [
                "/login",
                "/signup",
                "/dashboard",
            ],
            "focus_patterns": [
                r"\/app\/.*",      # Prioritize app routes
                r"\/admin\/.*",    # Prioritize admin routes
            ],
            "quality_gates": {
                "min_bugs_per_page": 1,
                "stop_on_critical_count": 5,
            },
            "crawl_approach": "breadth-first",
        },
    }

    summary = await run_bughive(config)

    print("\n--- Custom Crawl Summary ---")
    print(f"Session ID: {summary.get('session_id')}")
    print(f"Pages crawled: {summary['pages']['total_crawled']}")
    print(f"Pages failed: {summary['pages']['failed']}")
    print(f"Bugs found: {summary['bugs']['validated_bugs']}")
    print(f"Duplicates filtered: {summary['bugs']['duplicates_filtered']}")
    print(f"Linear tickets created: {summary['linear_tickets']['total_created']}")
    print(f"Total cost: ${summary['cost']['total_usd']:.2f}")

    print("\n--- Cost Breakdown ---")
    for node, cost in summary['cost']['by_node'].items():
        print(f"{node}: ${cost:.4f}")

    print("\n--- Performance Metrics ---")
    for node, duration in summary['performance']['node_durations'].items():
        print(f"{node}: {duration:.2f}s")


async def example_with_checkpointing():
    """Example: Using checkpointing for resumable workflows."""
    logger.info("=== Example 4: Checkpointing ===")

    from langgraph.checkpoint.sqlite import SqliteSaver

    # Create SQLite checkpoint saver
    checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

    config = {
        "base_url": "https://example.com",
        "max_pages": 100,
        "max_depth": 3,
        "focus_areas": ["all"],
    }

    try:
        summary = await run_bughive(config, checkpointer=checkpointer)
        print(f"\nWorkflow completed: {summary.get('session_id')}")

    except Exception as e:
        logger.error(f"Workflow interrupted: {e}")
        print("\nWorkflow can be resumed later with resume_bughive()")


async def example_resume_workflow():
    """Example: Resuming a checkpointed workflow."""
    logger.info("=== Example 5: Resume Workflow ===")

    from langgraph.checkpoint.sqlite import SqliteSaver
    from src.graph import resume_bughive

    checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

    # Resume with original session ID
    session_id = "abc-123-def-456"  # Replace with actual session ID

    try:
        summary = await resume_bughive(
            session_id=session_id,
            checkpointer=checkpointer,
            updates={
                "max_pages": 200,  # Optionally update config
            },
        )

        print(f"\nResumed workflow completed: {summary.get('session_id')}")
        print(f"Total bugs found: {summary['bugs']['validated_bugs']}")

    except ValueError as e:
        logger.error(f"No checkpoint found: {e}")


async def example_parallel_processing():
    """Example: Using parallel processing for faster crawls."""
    logger.info("=== Example 6: Parallel Processing ===")

    from src.graph.parallel import parallel_crawl_batch, parallel_analyze_batch

    config = {
        "base_url": "https://example.com",
        "max_depth": 3,
        "focus_areas": ["all"],
    }

    # Batch crawl multiple pages in parallel
    urls = [
        "https://example.com",
        "https://example.com/about",
        "https://example.com/contact",
        "https://example.com/products",
        "https://example.com/services",
    ]

    crawl_results = await parallel_crawl_batch(
        urls=urls,
        session_id="parallel-test",
        config=config,
    )

    print(f"\nCrawled {len(crawl_results)} pages in parallel")

    # Extract successful pages
    pages = [r["page_data"] for r in crawl_results if r["status"] == "success"]

    # Batch analyze pages in parallel
    analysis_results = await parallel_analyze_batch(
        pages=pages,
        config=config,
    )

    total_issues = sum(len(r["raw_issues"]) for r in analysis_results)
    print(f"Found {total_issues} issues across all pages")


async def example_visualize_workflow():
    """Example: Visualizing the workflow graph."""
    logger.info("=== Example 7: Visualize Workflow ===")

    from src.graph import visualize_workflow

    output_path = "docs/bughive_workflow.png"

    try:
        visualize_workflow(output_path)
        print(f"\nWorkflow diagram saved to: {output_path}")

    except Exception as e:
        logger.warning(f"Could not visualize workflow: {e}")
        logger.info("Install graphviz to enable visualization: brew install graphviz")


async def main():
    """Run all examples."""
    print("=" * 60)
    print("BugHive LangGraph Workflow Examples")
    print("=" * 60)

    # Choose which examples to run
    examples = [
        # example_quick_crawl,
        # example_deep_crawl,
        example_custom_config,
        # example_with_checkpointing,
        # example_resume_workflow,
        # example_parallel_processing,
        # example_visualize_workflow,
    ]

    for example in examples:
        try:
            await example()
            print("\n" + "=" * 60 + "\n")

        except Exception as e:
            logger.error(f"Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
