"""Main BugHive LangGraph workflow.

Orchestrates the autonomous QA agent system using LangGraph's state machine.
"""

import logging
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    # SqliteSaver not available, will use MemorySaver as fallback
    SqliteSaver = None

from src.graph.edges import (
    should_continue_crawling,
    should_create_tickets,
    should_validate,
)
from src.graph.nodes import (
    analyze_page,
    classify_bugs,
    crawl_page,
    create_linear_tickets,
    generate_reports,
    generate_summary,
    plan_crawl,
    validate_bugs,
)
from src.graph.state import BugHiveState, create_initial_state

logger = logging.getLogger(__name__)


def create_workflow(checkpointer=None) -> StateGraph:
    """Create the BugHive workflow graph.

    The workflow follows this pattern:
    1. Plan crawl strategy (Orchestrator/Opus)
    2. Loop: Crawl page -> Analyze -> Classify -> Continue?
    3. Validate high-priority bugs (Orchestrator/Opus)
    4. Generate reports
    5. Create Linear tickets (optional)
    6. Summarize results

    Args:
        checkpointer: Optional checkpoint saver for workflow persistence.
                     Defaults to MemorySaver() for in-memory checkpointing.

    Returns:
        Compiled StateGraph ready for execution
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    workflow = StateGraph(BugHiveState)

    # ===== Add Nodes =====
    workflow.add_node("plan", plan_crawl)
    workflow.add_node("crawl", crawl_page)
    workflow.add_node("analyze", analyze_page)
    workflow.add_node("classify", classify_bugs)
    workflow.add_node("validate", validate_bugs)
    workflow.add_node("report", generate_reports)
    workflow.add_node("create_tickets", create_linear_tickets)
    workflow.add_node("summarize", generate_summary)

    # ===== Define Edges =====

    # Start with planning
    workflow.set_entry_point("plan")

    # Plan -> Crawl first page
    workflow.add_edge("plan", "crawl")

    # Crawl -> Analyze (always analyze after crawl)
    workflow.add_edge("crawl", "analyze")

    # Analyze -> Classify (accumulate issues)
    workflow.add_edge("analyze", "classify")

    # Classify -> Validate or Report (based on priority)
    workflow.add_conditional_edges(
        "classify",
        should_validate,
        {
            "validate": "validate",
            "report": "report",
        },
    )

    # Validate -> Report (after validation, always report)
    workflow.add_edge("validate", "report")

    # Report -> Create Tickets or Continue Crawling
    # We create tickets after each batch for incremental progress
    workflow.add_conditional_edges(
        "report",
        should_create_tickets,
        {
            "create_tickets": "create_tickets",
            "skip_tickets": "continue_or_finish",
        },
    )

    # Create Tickets -> Continue or Finish
    workflow.add_edge("create_tickets", "continue_or_finish")

    # Decision point: Continue crawling or finish
    workflow.add_node("continue_or_finish", lambda state: state)  # Pass-through node
    workflow.add_conditional_edges(
        "continue_or_finish",
        should_continue_crawling,
        {
            "continue": "crawl",  # Loop back to crawl next page
            "finish": "summarize",
        },
    )

    # Summarize -> END
    workflow.add_edge("summarize", END)

    # Compile with checkpointing for state persistence
    return workflow.compile(checkpointer=checkpointer)


async def run_bughive(config: dict[str, Any], checkpointer=None) -> dict[str, Any]:
    """Run the BugHive workflow with the given configuration.

    This is the main entry point for running autonomous QA crawls.

    Args:
        config: Configuration dictionary with:
            - base_url: Starting URL for crawl
            - max_pages: Maximum pages to crawl (default: 100)
            - max_depth: Maximum link depth (default: 3)
            - focus_areas: Areas to focus on (default: ["all"])
            - quality_threshold: Confidence threshold for bugs (default: 0.7)
            - create_linear_tickets: Whether to create Linear tickets (default: False)
            - linear_team_id: Linear team ID if creating tickets
        checkpointer: Optional checkpoint saver for workflow persistence

    Returns:
        Summary dictionary with:
            - session_id: Unique session identifier
            - pages: Crawl statistics
            - bugs: Bug discovery statistics
            - linear_tickets: Created tickets
            - cost: Total cost breakdown
            - performance: Timing metrics
            - errors: Error summary
            - recommendations: Suggested next steps

    Example:
        >>> config = {
        ...     "base_url": "https://example.com",
        ...     "max_pages": 50,
        ...     "max_depth": 2,
        ...     "focus_areas": ["forms", "navigation"],
        ...     "create_linear_tickets": True,
        ...     "linear_team_id": "TEAM123",
        ... }
        >>> summary = await run_bughive(config)
        >>> print(f"Found {summary['bugs']['validated_bugs']} bugs")
    """
    logger.info("Starting BugHive workflow...")
    logger.info(f"Config: {config}")

    # Create workflow
    workflow = create_workflow(checkpointer=checkpointer)

    # Create initial state
    initial_state = create_initial_state(config)

    # Run workflow
    try:
        # If using checkpointing, provide a thread_id for state persistence
        thread_config = {
            "configurable": {
                "thread_id": initial_state["session_id"]
            }
        }

        result = await workflow.ainvoke(
            initial_state,
            config=thread_config if checkpointer else None
        )

        logger.info("BugHive workflow completed successfully")
        logger.info(f"Session ID: {result['session_id']}")
        logger.info(f"Pages crawled: {len(result.get('pages_crawled', []))}")
        logger.info(f"Bugs found: {len(result.get('validated_bugs', []))}")
        logger.info(f"Total cost: ${result.get('total_cost', 0.0):.2f}")

        return result.get("summary", {})

    except Exception as e:
        logger.error(f"BugHive workflow failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "session_id": initial_state["session_id"],
            "status": "failed",
        }


async def resume_bughive(
    session_id: str,
    checkpointer,
    updates: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Resume a checkpointed BugHive workflow from a previous session.

    Useful for:
    - Recovering from crashes
    - Continuing interrupted crawls
    - Adjusting strategy mid-crawl

    Args:
        session_id: Session ID to resume
        checkpointer: Checkpoint saver with persisted state
        updates: Optional state updates to apply before resuming

    Returns:
        Summary dictionary from completed workflow

    Example:
        >>> from langgraph.checkpoint.sqlite import SqliteSaver
        >>> checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
        >>> # Later, resume from checkpoint
        >>> summary = await resume_bughive(
        ...     session_id="abc-123",
        ...     checkpointer=checkpointer,
        ...     updates={"max_pages": 200}  # Increase limit
        ... )
    """
    logger.info(f"Resuming BugHive workflow for session: {session_id}")

    workflow = create_workflow(checkpointer=checkpointer)

    try:
        thread_config = {
            "configurable": {
                "thread_id": session_id
            }
        }

        # Get current state
        state = await workflow.aget_state(config=thread_config)

        if not state:
            raise ValueError(f"No checkpoint found for session: {session_id}")

        # Apply updates if provided
        if updates:
            logger.info(f"Applying state updates: {updates}")
            state.values.update(updates)

        # Resume workflow
        result = await workflow.ainvoke(
            state.values,
            config=thread_config
        )

        logger.info(f"Resumed workflow completed for session: {session_id}")
        return result.get("summary", {})

    except Exception as e:
        logger.error(f"Failed to resume workflow: {e}", exc_info=True)
        return {
            "error": str(e),
            "session_id": session_id,
            "status": "resume_failed",
        }


def visualize_workflow(output_path: str = "workflow.png"):
    """Generate a visual diagram of the BugHive workflow.

    Requires graphviz to be installed.

    Args:
        output_path: Path to save the diagram image

    Example:
        >>> visualize_workflow("docs/bughive_workflow.png")
    """
    try:
        from pathlib import Path

        from IPython.display import Image

        workflow = create_workflow()
        graph_image = workflow.get_graph().draw_mermaid_png()

        output = Path(output_path)
        with output.open("wb") as f:
            f.write(graph_image)

        logger.info(f"Workflow diagram saved to: {output_path}")
        return Image(graph_image)

    except ImportError:
        logger.warning("IPython not available. Install with: pip install ipython")
    except Exception as e:
        logger.error(f"Failed to visualize workflow: {e}", exc_info=True)


# Convenience functions for common operations

async def quick_crawl(
    url: str,
    max_pages: int = 10,
    create_tickets: bool = False
) -> dict[str, Any]:
    """Quick crawl for testing or small sites.

    Args:
        url: Starting URL
        max_pages: Maximum pages to crawl (default: 10)
        create_tickets: Whether to create Linear tickets (default: False)

    Returns:
        Summary dictionary
    """
    config = {
        "base_url": url,
        "max_pages": max_pages,
        "max_depth": 2,
        "focus_areas": ["all"],
        "quality_mode": "balanced",
        "create_linear_tickets": create_tickets,
    }

    return await run_bughive(config)


async def deep_crawl(
    url: str,
    max_pages: int = 100,
    focus_areas: list[str] = None,
    linear_team_id: str = None
) -> dict[str, Any]:
    """Comprehensive deep crawl with full analysis.

    Args:
        url: Starting URL
        max_pages: Maximum pages to crawl (default: 100)
        focus_areas: Specific areas to focus on (default: ["all"])
        linear_team_id: Linear team ID for ticket creation

    Returns:
        Summary dictionary
    """
    config = {
        "base_url": url,
        "max_pages": max_pages,
        "max_depth": 4,
        "focus_areas": focus_areas or ["all"],
        "quality_mode": "comprehensive",
        "quality_threshold": 0.8,
        "create_linear_tickets": bool(linear_team_id),
        "linear_team_id": linear_team_id,
    }

    return await run_bughive(config)
