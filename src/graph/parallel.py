"""Parallel processing capabilities for BugHive workflow.

Enables fan-out/fan-in patterns for analyzing multiple pages concurrently.
"""

import logging
import asyncio
from typing import Any

from langgraph.graph import Send
from src.graph.state import BugHiveState
from src.agents.crawler import CrawlerAgent
from src.agents.analyzer import PageAnalyzerAgent

logger = logging.getLogger(__name__)


async def analyze_single_page(state: dict[str, Any]) -> dict[str, Any]:
    """Analyze a single page in parallel.

    This is a sub-node that can be invoked in parallel via Send().

    Args:
        state: Partial state with page data

    Returns:
        State updates with raw issues from this page
    """
    page = state.get("page")
    if not page:
        return {"raw_issues": []}

    logger.info(f"Analyzing page in parallel: {page.get('url')}")

    try:
        analyzer = PageAnalyzerAgent()
        config = state.get("config", {})

        analysis_result = await analyzer.analyze_page(
            extracted_text=page.get("extracted_text", ""),
            html_structure=page.get("html_structure", {}),
            screenshot_url=page.get("screenshot_url"),
            url=page.get("url", ""),
            focus_areas=config.get("focus_areas", ["all"]),
        )

        # Convert raw issues to dicts
        raw_issues = []
        for issue in analysis_result.raw_issues:
            raw_issues.append(
                {
                    "id": issue.id,
                    "page_url": page.get("url"),
                    "category": issue.category,
                    "severity": issue.severity,
                    "title": issue.title,
                    "description": issue.description,
                    "location": issue.location,
                    "suggested_fix": issue.suggested_fix,
                    "confidence": issue.confidence,
                    "screenshot_url": page.get("screenshot_url"),
                }
            )

        return {
            "raw_issues": raw_issues,
            "cost": analysis_result.cost,
            "page_url": page.get("url"),
        }

    except Exception as e:
        logger.error(f"Error analyzing page {page.get('url')}: {e}", exc_info=True)
        return {
            "raw_issues": [],
            "error": str(e),
            "page_url": page.get("url"),
        }


def crawl_and_analyze_parallel(state: BugHiveState) -> list[Send]:
    """Fan out to analyze multiple pages in parallel.

    This creates multiple parallel sub-tasks for concurrent page analysis.

    Args:
        state: Current workflow state

    Returns:
        List of Send objects for parallel execution
    """
    # Get batch of uncrawled pages (limit to avoid overwhelming the system)
    pages_discovered = state.get("pages_discovered", [])
    uncrawled = [
        p for p in pages_discovered
        if p.get("status") == "discovered"
    ]

    # Limit parallel processing to 5 pages at a time
    batch_size = min(5, len(uncrawled))
    batch = uncrawled[:batch_size]

    logger.info(f"Fan-out: Analyzing {len(batch)} pages in parallel")

    # Create Send objects for each page
    return [
        Send("analyze_single_page", {"page": page, **state})
        for page in batch
    ]


async def parallel_crawl_batch(
    urls: list[str],
    session_id: str,
    config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Crawl multiple pages in parallel.

    Utility function for batch crawling outside the main workflow.

    Args:
        urls: List of URLs to crawl
        session_id: Session identifier
        config: Crawl configuration

    Returns:
        List of crawl results (one per URL)
    """
    logger.info(f"Parallel crawling {len(urls)} pages")

    crawler = CrawlerAgent()

    async def crawl_single(url: str, depth: int = 1) -> dict[str, Any]:
        """Crawl a single URL."""
        try:
            result = await crawler.crawl_page(
                url=url,
                session_id=session_id,
                depth=depth,
                max_depth=config.get("max_depth", 3),
            )

            return {
                "url": url,
                "status": "success",
                "page_data": {
                    "page_id": result.page_id,
                    "url": result.url,
                    "extracted_text": result.extracted_text,
                    "html_structure": result.html_structure,
                    "screenshot_url": result.screenshot_url,
                    "discovered_links": result.discovered_links,
                    "metadata": result.metadata,
                },
                "cost": result.cost,
            }

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}", exc_info=True)
            return {
                "url": url,
                "status": "failed",
                "error": str(e),
            }

    # Execute crawls in parallel
    results = await asyncio.gather(
        *[crawl_single(url) for url in urls],
        return_exceptions=True
    )

    # Filter out exceptions and return results
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Crawl task failed: {result}")
        else:
            valid_results.append(result)

    logger.info(
        f"Parallel crawl completed: {len(valid_results)} successful, "
        f"{len(results) - len(valid_results)} failed"
    )

    return valid_results


async def parallel_analyze_batch(
    pages: list[dict[str, Any]],
    config: dict[str, Any]
) -> list[dict[str, Any]]:
    """Analyze multiple pages in parallel.

    Utility function for batch analysis outside the main workflow.

    Args:
        pages: List of page data dictionaries
        config: Analysis configuration

    Returns:
        List of analysis results (raw issues per page)
    """
    logger.info(f"Parallel analyzing {len(pages)} pages")

    analyzer = PageAnalyzerAgent()

    async def analyze_single(page: dict[str, Any]) -> dict[str, Any]:
        """Analyze a single page."""
        try:
            result = await analyzer.analyze_page(
                extracted_text=page.get("extracted_text", ""),
                html_structure=page.get("html_structure", {}),
                screenshot_url=page.get("screenshot_url"),
                url=page.get("url", ""),
                focus_areas=config.get("focus_areas", ["all"]),
            )

            # Convert to dicts
            raw_issues = []
            for issue in result.raw_issues:
                raw_issues.append(
                    {
                        "id": issue.id,
                        "page_url": page.get("url"),
                        "category": issue.category,
                        "severity": issue.severity,
                        "title": issue.title,
                        "description": issue.description,
                        "location": issue.location,
                        "suggested_fix": issue.suggested_fix,
                        "confidence": issue.confidence,
                        "screenshot_url": page.get("screenshot_url"),
                    }
                )

            return {
                "page_url": page.get("url"),
                "status": "success",
                "raw_issues": raw_issues,
                "cost": result.cost,
            }

        except Exception as e:
            logger.error(f"Error analyzing page {page.get('url')}: {e}", exc_info=True)
            return {
                "page_url": page.get("url"),
                "status": "failed",
                "error": str(e),
                "raw_issues": [],
            }

    # Execute analyses in parallel
    results = await asyncio.gather(
        *[analyze_single(page) for page in pages],
        return_exceptions=True
    )

    # Filter out exceptions
    valid_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Analysis task failed: {result}")
        else:
            valid_results.append(result)

    total_issues = sum(len(r.get("raw_issues", [])) for r in valid_results)
    logger.info(
        f"Parallel analysis completed: {len(valid_results)} pages analyzed, "
        f"{total_issues} issues found"
    )

    return valid_results


# Advanced parallel workflow (optional)

def create_parallel_workflow():
    """Create an advanced workflow with parallel page processing.

    This is an alternative workflow design that processes multiple pages
    concurrently instead of sequentially.

    Note: This requires more resources but is faster for large crawls.
    """
    from langgraph.graph import StateGraph, END

    workflow = StateGraph(BugHiveState)

    # Define nodes (reuse from main workflow)
    from src.graph.nodes import (
        plan_crawl,
        classify_bugs,
        validate_bugs,
        generate_reports,
        create_linear_tickets,
        generate_summary,
    )

    workflow.add_node("plan", plan_crawl)
    workflow.add_node("analyze_single_page", analyze_single_page)
    workflow.add_node("classify", classify_bugs)
    workflow.add_node("validate", validate_bugs)
    workflow.add_node("report", generate_reports)
    workflow.add_node("create_tickets", create_linear_tickets)
    workflow.add_node("summarize", generate_summary)

    # Set entry point
    workflow.set_entry_point("plan")

    # Plan -> Fan out to parallel analysis
    workflow.add_conditional_edges(
        "plan",
        crawl_and_analyze_parallel,
        ["analyze_single_page"],
    )

    # Collect results from parallel analysis -> Classify
    workflow.add_edge("analyze_single_page", "classify")

    # Rest of workflow is sequential (validation, reporting)
    from src.graph.edges import should_validate, should_create_tickets, should_continue_crawling

    workflow.add_conditional_edges(
        "classify",
        should_validate,
        {
            "validate": "validate",
            "report": "report",
        },
    )

    workflow.add_edge("validate", "report")

    workflow.add_conditional_edges(
        "report",
        should_create_tickets,
        {
            "create_tickets": "create_tickets",
            "skip_tickets": "continue_or_finish",
        },
    )

    workflow.add_node("continue_or_finish", lambda state: state)
    workflow.add_edge("create_tickets", "continue_or_finish")

    workflow.add_conditional_edges(
        "continue_or_finish",
        should_continue_crawling,
        {
            "continue": "plan",  # Loop back to plan next batch
            "finish": "summarize",
        },
    )

    workflow.add_edge("summarize", END)

    return workflow.compile()
