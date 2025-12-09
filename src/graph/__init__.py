"""BugHive LangGraph workflow.

This module orchestrates the autonomous QA agent system using LangGraph's
state machine for robust, checkpointable workflows.

Main components:
- State: Shared state schema (BugHiveState)
- Nodes: Discrete workflow steps (plan, crawl, analyze, classify, etc.)
- Edges: Conditional routing logic
- Workflow: Main workflow graph and execution functions

Example:
    >>> from src.graph import run_bughive
    >>>
    >>> config = {
    ...     "base_url": "https://example.com",
    ...     "max_pages": 50,
    ...     "max_depth": 3,
    ...     "create_linear_tickets": True,
    ... }
    >>>
    >>> summary = await run_bughive(config)
    >>> print(f"Found {summary['bugs']['validated_bugs']} bugs")
"""

from src.graph.state import BugHiveState, create_initial_state
from src.graph.workflow import (
    create_workflow,
    run_bughive,
    resume_bughive,
    visualize_workflow,
    quick_crawl,
    deep_crawl,
)
from src.graph.nodes import (
    plan_crawl,
    crawl_page,
    analyze_page,
    classify_bugs,
    validate_bugs,
    generate_reports,
    create_linear_tickets,
    generate_summary,
)
from src.graph.edges import (
    should_validate,
    should_continue_crawling,
    should_create_tickets,
    should_analyze_page,
)
from src.graph.parallel import (
    parallel_crawl_batch,
    parallel_analyze_batch,
    create_parallel_workflow,
)

__all__ = [
    # State
    "BugHiveState",
    "create_initial_state",
    # Workflow
    "create_workflow",
    "run_bughive",
    "resume_bughive",
    "visualize_workflow",
    "quick_crawl",
    "deep_crawl",
    # Nodes
    "plan_crawl",
    "crawl_page",
    "analyze_page",
    "classify_bugs",
    "validate_bugs",
    "generate_reports",
    "create_linear_tickets",
    "generate_summary",
    # Edges
    "should_validate",
    "should_continue_crawling",
    "should_create_tickets",
    "should_analyze_page",
    # Parallel
    "parallel_crawl_batch",
    "parallel_analyze_batch",
    "create_parallel_workflow",
]
