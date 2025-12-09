"""LangGraph workflow nodes.

Each node represents a discrete step in the BugHive autonomous QA workflow.
"""

import logging
import time
from typing import Any

from src.agents.analyzer import PageAnalyzerAgent
from src.agents.classifier import BugClassifierAgent
from src.agents.crawler import CrawlerAgent
from src.graph.state import BugHiveState
from src.integrations.linear import LinearClient
from src.integrations.reporter import ReportWriterAgent
from src.llm.router import LLMRouter
from src.utils.error_aggregator import get_error_aggregator
from src.utils.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


async def plan_crawl(state: BugHiveState) -> dict[str, Any]:
    """Initial planning node - uses Orchestrator (Opus) to plan crawl strategy.

    The Orchestrator analyzes the config and determines:
    - Crawl depth and breadth strategy
    - Focus areas (authentication, forms, navigation, etc.)
    - Quality gates and success criteria
    - Initial pages to discover

    Args:
        state: Current workflow state

    Returns:
        State updates with planned strategy and initial pages
    """
    node_start = time.time()
    logger.info(f"[{state['session_id']}] Starting crawl planning...")

    config = state["config"]
    llm_router = LLMRouter()

    # Build planning prompt for Orchestrator
    planning_prompt = f"""You are planning a QA crawl for a web application.

**Application Details:**
- Base URL: {config.get('base_url')}
- Max Pages: {config.get('max_pages', 100)}
- Max Depth: {config.get('max_depth', 3)}
- Focus Areas: {config.get('focus_areas', ['all'])}
- Quality Mode: {config.get('quality_mode', 'balanced')}

**Your Task:**
Analyze this configuration and create a crawl strategy. Consider:
1. What pages should we prioritize?
2. What depth is appropriate for thorough testing?
3. What patterns should we look for (auth flows, forms, dynamic content)?
4. What quality gates should we apply?

Output a JSON strategy with:
{{
    "initial_pages": ["url1", "url2"],  // Starting points beyond base_url
    "focus_patterns": ["pattern1", "pattern2"],  // URL patterns to prioritize
    "quality_gates": {{
        "min_bugs_per_page": 1,
        "stop_on_critical_count": 3
    }},
    "crawl_approach": "breadth-first|depth-first",
    "reasoning": "Why this strategy is optimal"
}}
"""

    try:
        # Use Opus for strategic planning
        response = await llm_router.chat(
            messages=[{"role": "user", "content": planning_prompt}],
            task_type="orchestrator",
            model_override="claude-opus-4-5-20250929",
        )

        strategy = response.parsed_response
        logger.info(f"Crawl strategy: {strategy.get('reasoning')}")

        # Initialize pages_discovered with base_url and planned pages
        base_url = config.get("base_url")
        pages_discovered = [
            {
                "url": base_url,
                "depth": 0,
                "status": "discovered",
                "priority": 10,
            }
        ]

        # Add initial pages from strategy
        for url in strategy.get("initial_pages", []):
            pages_discovered.append(
                {
                    "url": url if url.startswith("http") else f"{base_url}{url}",
                    "depth": 1,
                    "status": "discovered",
                    "priority": 8,
                }
            )

        # Track LLM call
        llm_calls = state.get("llm_calls", [])
        llm_calls.append(
            {
                "node": "plan_crawl",
                "model": response.model,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cost": response.cost,
            }
        )

        # Add strategy to messages for other agents to reference
        messages = state.get("messages", [])
        messages.append(
            {
                "role": "assistant",
                "content": f"Crawl strategy planned: {strategy.get('reasoning')}",
                "metadata": {"strategy": strategy},
            }
        )

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["plan_crawl"] = node_duration

        logger.info(
            f"[{state['session_id']}] Planning complete. {len(pages_discovered)} initial pages. Cost: ${response.cost:.4f}"
        )

        return {
            "pages_discovered": pages_discovered,
            "total_cost": state.get("total_cost", 0.0) + response.cost,
            "llm_calls": llm_calls,
            "messages": messages,
            "node_durations": node_durations,
            "config": {
                **config,
                "strategy": strategy,  # Embed strategy in config
            },
        }

    except Exception as e:
        logger.error(f"Error in plan_crawl: {e}", exc_info=True)

        # Track error in aggregator
        error_agg = get_error_aggregator(state["session_id"])
        error_agg.add(e, context={"node": "plan_crawl"})

        errors = state.get("errors", [])
        errors.append(
            {"node": "plan_crawl", "error": str(e), "timestamp": time.time()}
        )
        return {"errors": errors}


async def crawl_page(state: BugHiveState) -> dict[str, Any]:
    """Crawl a single page and extract data.

    Uses CrawlerAgent to:
    - Navigate to the page
    - Extract content and structure
    - Discover new links
    - Capture screenshots

    Args:
        state: Current workflow state

    Returns:
        State updates with crawled page data and newly discovered pages
    """
    node_start = time.time()
    logger.info(f"[{state['session_id']}] Crawling next page...")

    # Get next uncrawled page (highest priority)
    pages_discovered = state.get("pages_discovered", [])
    pages_crawled = state.get("pages_crawled", [])

    uncrawled = [
        p for p in pages_discovered if p.get("status") == "discovered"
    ]
    if not uncrawled:
        logger.warning("No uncrawled pages available")
        return {"crawl_complete": True}

    # Sort by priority (desc) then depth (asc)
    uncrawled.sort(key=lambda p: (-p.get("priority", 0), p.get("depth", 0)))
    next_page = uncrawled[0]

    logger.info(
        f"Crawling: {next_page['url']} (depth={next_page['depth']}, priority={next_page.get('priority')})"
    )

    try:
        crawler = CrawlerAgent()
        config = state.get("config", {})

        # Crawl the page
        crawl_result = await crawler.crawl_page(
            url=next_page["url"],
            session_id=state["session_id"],
            depth=next_page["depth"],
            max_depth=config.get("max_depth", 3),
        )

        # Update page status
        for page in pages_discovered:
            if page["url"] == next_page["url"]:
                page["status"] = "crawled"
                page["crawl_result"] = {
                    "page_id": crawl_result.page_id,
                    "text_length": len(crawl_result.extracted_text),
                    "links_found": len(crawl_result.discovered_links),
                }
                break

        # Add to crawled pages
        pages_crawled.append(
            {
                **next_page,
                "status": "crawled",
                "page_data": {
                    "page_id": crawl_result.page_id,
                    "url": crawl_result.url,
                    "extracted_text": crawl_result.extracted_text,
                    "html_structure": crawl_result.html_structure,
                    "screenshot_url": crawl_result.screenshot_url,
                    "discovered_links": crawl_result.discovered_links,
                    "metadata": crawl_result.metadata,
                },
            }
        )

        # Discover new pages from links
        max_depth = config.get("max_depth", 3)
        current_depth = next_page["depth"]
        new_pages = []

        if current_depth < max_depth:
            existing_urls = {p["url"] for p in pages_discovered}
            for link in crawl_result.discovered_links:
                if link not in existing_urls:
                    new_pages.append(
                        {
                            "url": link,
                            "depth": current_depth + 1,
                            "status": "discovered",
                            "priority": 5,  # Default priority
                        }
                    )
                    existing_urls.add(link)

        if new_pages:
            logger.info(f"Discovered {len(new_pages)} new pages")
            pages_discovered.extend(new_pages)

        # Track cost
        total_cost = state.get("total_cost", 0.0) + crawl_result.cost
        llm_calls = state.get("llm_calls", [])
        if crawl_result.cost > 0:
            llm_calls.append(
                {
                    "node": "crawl_page",
                    "model": "browserbase",
                    "cost": crawl_result.cost,
                }
            )

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["crawl_page"] = node_durations.get("crawl_page", 0) + node_duration

        logger.info(
            f"[{state['session_id']}] Crawled {next_page['url']}. "
            f"Found {len(crawl_result.discovered_links)} links. Cost: ${crawl_result.cost:.4f}"
        )

        # Track progress
        tracker = ProgressTracker(session_id=state["session_id"])
        tracker.update(
            stage="crawling",
            pages_done=len(pages_crawled),
            pages_total=len(pages_discovered),
            bugs_found=len(state.get("validated_bugs", [])),
            cost=total_cost,
        )
        tracker.save_state(state)

        return {
            "current_page": pages_crawled[-1],
            "pages_discovered": pages_discovered,
            "pages_crawled": pages_crawled,
            "total_cost": total_cost,
            "llm_calls": llm_calls,
            "node_durations": node_durations,
        }

    except Exception as e:
        logger.error(f"Error crawling {next_page['url']}: {e}", exc_info=True)

        # Track error in aggregator
        error_agg = get_error_aggregator(state["session_id"])
        error_agg.add(e, context={"node": "crawl_page", "url": next_page["url"]})

        # Mark page as failed
        for page in pages_discovered:
            if page["url"] == next_page["url"]:
                page["status"] = "failed"
                page["error"] = str(e)
                break

        errors = state.get("errors", [])
        errors.append(
            {
                "node": "crawl_page",
                "url": next_page["url"],
                "error": str(e),
                "timestamp": time.time(),
            }
        )

        return {
            "pages_discovered": pages_discovered,
            "errors": errors,
        }


async def analyze_page(state: BugHiveState) -> dict[str, Any]:
    """Analyze current page for issues.

    Uses PageAnalyzerAgent to:
    - Detect UI/UX issues
    - Identify accessibility problems
    - Find functional bugs
    - Check performance issues

    Args:
        state: Current workflow state

    Returns:
        State updates with discovered raw issues
    """
    node_start = time.time()
    logger.info(f"[{state['session_id']}] Analyzing current page...")

    current_page = state.get("current_page")
    if not current_page:
        logger.warning("No current page to analyze")
        return {}

    page_data = current_page.get("page_data", {})
    if not page_data:
        logger.warning("No page data available")
        return {}

    try:
        analyzer = PageAnalyzerAgent()
        config = state.get("config", {})

        # Analyze the page
        analysis_result = await analyzer.analyze_page(
            extracted_text=page_data.get("extracted_text", ""),
            html_structure=page_data.get("html_structure", {}),
            screenshot_url=page_data.get("screenshot_url"),
            url=page_data.get("url", ""),
            focus_areas=config.get("focus_areas", ["all"]),
        )

        # Add raw issues to state
        raw_issues = state.get("raw_issues", [])
        new_issues = []

        for issue in analysis_result.raw_issues:
            new_issues.append(
                {
                    "id": issue.id,
                    "page_url": page_data.get("url"),
                    "category": issue.category,
                    "severity": issue.severity,
                    "title": issue.title,
                    "description": issue.description,
                    "location": issue.location,
                    "suggested_fix": issue.suggested_fix,
                    "confidence": issue.confidence,
                    "screenshot_url": page_data.get("screenshot_url"),
                    "page_id": page_data.get("page_id"),
                }
            )

        raw_issues.extend(new_issues)

        # Track cost
        total_cost = state.get("total_cost", 0.0) + analysis_result.cost
        llm_calls = state.get("llm_calls", [])
        llm_calls.append(
            {
                "node": "analyze_page",
                "model": analysis_result.model_used,
                "input_tokens": analysis_result.input_tokens,
                "output_tokens": analysis_result.output_tokens,
                "cost": analysis_result.cost,
            }
        )

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["analyze_page"] = node_durations.get("analyze_page", 0) + node_duration

        logger.info(
            f"[{state['session_id']}] Found {len(new_issues)} issues on {page_data.get('url')}. "
            f"Cost: ${analysis_result.cost:.4f}"
        )

        # Track progress
        tracker = ProgressTracker(session_id=state["session_id"])
        tracker.update(
            stage="analyzing",
            pages_done=len(state.get("pages_crawled", [])),
            pages_total=len(state.get("pages_discovered", [])),
            bugs_found=len(raw_issues),
            cost=total_cost,
        )
        tracker.save_state(state)

        return {
            "raw_issues": raw_issues,
            "total_cost": total_cost,
            "llm_calls": llm_calls,
            "node_durations": node_durations,
        }

    except Exception as e:
        logger.error(f"Error analyzing page: {e}", exc_info=True)

        # Track error in aggregator
        error_agg = get_error_aggregator(state["session_id"])
        error_agg.add(e, context={"node": "analyze_page", "url": page_data.get("url")})

        errors = state.get("errors", [])
        errors.append(
            {
                "node": "analyze_page",
                "url": page_data.get("url"),
                "error": str(e),
                "timestamp": time.time(),
            }
        )
        return {"errors": errors}


async def classify_bugs(state: BugHiveState) -> dict[str, Any]:
    """Classify and deduplicate bugs.

    Uses BugClassifierAgent to:
    - Deduplicate similar issues
    - Prioritize bugs (critical/high/medium/low)
    - Filter out noise (low confidence issues)
    - Group related bugs

    Args:
        state: Current workflow state

    Returns:
        State updates with classified and deduplicated bugs
    """
    node_start = time.time()
    logger.info(f"[{state['session_id']}] Classifying bugs...")

    raw_issues = state.get("raw_issues", [])
    if not raw_issues:
        logger.info("No raw issues to classify")
        return {"classified_bugs": []}

    try:
        classifier = BugClassifierAgent()
        config = state.get("config", {})

        # Classify all raw issues
        classification_result = await classifier.classify_and_deduplicate(
            raw_issues=raw_issues,
            existing_bugs=state.get("classified_bugs", []),
            quality_threshold=config.get("quality_threshold", 0.7),
        )

        # Convert Bug objects to dicts
        classified_bugs = []
        for bug in classification_result.bugs:
            classified_bugs.append(
                {
                    "id": bug.id,
                    "title": bug.title,
                    "description": bug.description,
                    "category": bug.category,
                    "priority": bug.priority,
                    "severity": bug.severity,
                    "affected_pages": bug.affected_pages,
                    "steps_to_reproduce": bug.steps_to_reproduce,
                    "expected_behavior": bug.expected_behavior,
                    "actual_behavior": bug.actual_behavior,
                    "environment": bug.environment,
                    "screenshots": bug.screenshots,
                    "related_issue_ids": bug.related_issue_ids,
                    "confidence_score": bug.confidence_score,
                    "is_duplicate": bug.is_duplicate,
                    "duplicate_of": bug.duplicate_of,
                }
            )

        # Track duplicates filtered
        duplicates_count = len([b for b in classified_bugs if b.get("is_duplicate")])
        logger.info(f"Filtered {duplicates_count} duplicate bugs")

        # Identify bugs needing validation (critical/high priority)
        validation_needed = [
            b["id"]
            for b in classified_bugs
            if b.get("priority") in ("critical", "high")
            and not b.get("is_duplicate")
        ]

        # Track cost
        total_cost = state.get("total_cost", 0.0) + classification_result.cost
        llm_calls = state.get("llm_calls", [])
        llm_calls.append(
            {
                "node": "classify_bugs",
                "model": classification_result.model_used,
                "input_tokens": classification_result.input_tokens,
                "output_tokens": classification_result.output_tokens,
                "cost": classification_result.cost,
            }
        )

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["classify_bugs"] = node_duration

        logger.info(
            f"[{state['session_id']}] Classified {len(classified_bugs)} bugs "
            f"({len(validation_needed)} need validation). Cost: ${classification_result.cost:.4f}"
        )

        # Track progress
        tracker = ProgressTracker(session_id=state["session_id"])
        non_duplicate_bugs = len([b for b in classified_bugs if not b.get("is_duplicate")])
        tracker.update(
            stage="classifying",
            pages_done=len(state.get("pages_crawled", [])),
            pages_total=len(state.get("pages_discovered", [])),
            bugs_found=non_duplicate_bugs,
            cost=total_cost,
        )
        tracker.save_state(state)

        return {
            "classified_bugs": classified_bugs,
            "validation_needed": validation_needed,
            "total_cost": total_cost,
            "llm_calls": llm_calls,
            "node_durations": node_durations,
        }

    except Exception as e:
        logger.error(f"Error classifying bugs: {e}", exc_info=True)

        # Track error in aggregator
        error_agg = get_error_aggregator(state["session_id"])
        error_agg.add(e, context={"node": "classify_bugs"})

        errors = state.get("errors", [])
        errors.append(
            {"node": "classify_bugs", "error": str(e), "timestamp": time.time()}
        )
        return {"errors": errors}


async def validate_bugs(state: BugHiveState) -> dict[str, Any]:
    """Validate high-priority bugs in parallel using semaphore-controlled concurrency.

    Uses parallel validation to:
    - Verify critical/high priority bugs are legitimate
    - Adjust priorities based on business impact
    - Add strategic context and recommendations
    - Filter false positives
    - Use extended thinking for critical/high priority bugs (optional)

    Args:
        state: Current workflow state

    Returns:
        State updates with validated bugs and priority overrides
    """
    from src.graph.parallel import parallel_validate_batch
    from src.models.bug import Bug

    node_start = time.time()
    logger.info(f"[{state['session_id']}] Validating high-priority bugs in parallel...")

    validation_needed = state.get("validation_needed", [])
    if not validation_needed:
        logger.info("No bugs need validation")
        # Move all classified bugs to validated
        return {
            "validated_bugs": state.get("classified_bugs", []),
            "node_durations": {
                **state.get("node_durations", {}),
                "validate_bugs": 0.0,
            },
        }

    classified_bugs = state.get("classified_bugs", [])
    bugs_to_validate = [b for b in classified_bugs if b["id"] in validation_needed]

    logger.info(f"Validating {len(bugs_to_validate)} high-priority bugs in parallel")

    try:
        llm_router = LLMRouter()
        config = state.get("config", {})

        # Convert bug dicts to Bug objects for validation
        bug_objects = []
        for bug_dict in bugs_to_validate:
            # Create a minimal Bug object for validation
            # Note: Some fields may not be present in classified_bugs dict
            try:
                bug_obj = Bug(
                    id=bug_dict["id"],
                    session_id=state["session_id"],
                    page_id=bug_dict.get("page_id", bug_dict.get("affected_pages", [None])[0]),
                    title=bug_dict["title"],
                    description=bug_dict["description"],
                    category=bug_dict["category"],
                    priority=bug_dict["priority"],
                    steps_to_reproduce=bug_dict.get("steps_to_reproduce", []),
                    confidence=bug_dict.get("confidence_score", 0.0),
                )
                bug_objects.append(bug_obj)
            except Exception as e:
                logger.warning(
                    f"Failed to convert bug {bug_dict['id']} to Bug object: {e}. Skipping."
                )

        # Use parallel validation with semaphore
        use_extended_thinking = config.get("use_extended_thinking", False)
        batch_size = config.get("validation_batch_size", 5)

        validation_results = await parallel_validate_batch(
            bugs=bug_objects,
            llm_router=llm_router,
            session_id=state["session_id"],
            batch_size=batch_size,
            use_extended_thinking=use_extended_thinking,
        )

        # Process validation results
        validated_bugs = state.get("validated_bugs", [])
        priority_override = state.get("priority_override", {})
        total_validation_cost = sum(r.get("cost", 0.0) for r in validation_results)
        llm_calls = state.get("llm_calls", [])

        # Map results back to bugs
        results_by_id = {r["bug_id"]: r for r in validation_results}

        for bug in bugs_to_validate:
            bug_id = str(bug["id"])
            validation = results_by_id.get(bug_id)

            if not validation:
                logger.warning(f"No validation result for bug {bug_id}")
                continue

            # Track LLM call
            llm_calls.append(
                {
                    "node": "validate_bugs",
                    "bug_id": bug_id,
                    "model": "parallel_validation",
                    "cost": validation.get("cost", 0.0),
                }
            )

            # Only add to validated if bug is legitimate
            if validation.get("is_valid", False):
                validated_bug = {
                    **bug,
                    "validation": validation,
                    "validated_at": time.time(),
                }

                # Update priority if changed
                new_priority = validation.get("validated_priority")
                if new_priority and new_priority != bug["priority"]:
                    validated_bug["priority"] = new_priority
                    priority_override[bug_id] = new_priority
                    logger.info(
                        f"Priority override for {bug_id}: {bug['priority']} -> {new_priority}"
                    )

                validated_bugs.append(validated_bug)
                logger.info(
                    f"Bug {bug_id} validated: {validation.get('recommended_action')}"
                )
            else:
                logger.info(f"Bug {bug_id} rejected as invalid")

        # Add remaining non-validated bugs (medium/low priority)
        non_validated_bugs = [
            b for b in classified_bugs if b["id"] not in validation_needed
        ]
        validated_bugs.extend(non_validated_bugs)

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["validate_bugs"] = node_duration

        logger.info(
            f"[{state['session_id']}] Parallel validation complete: "
            f"{len(bugs_to_validate)} bugs validated in {node_duration:.2f}s. "
            f"{len(validated_bugs)} total validated. Cost: ${total_validation_cost:.4f}"
        )

        return {
            "validated_bugs": validated_bugs,
            "priority_override": priority_override,
            "total_cost": state.get("total_cost", 0.0) + total_validation_cost,
            "llm_calls": llm_calls,
            "node_durations": node_durations,
        }

    except Exception as e:
        logger.error(f"Error validating bugs: {e}", exc_info=True)

        # Track error in aggregator
        error_agg = get_error_aggregator(state["session_id"])
        error_agg.add(e, context={"node": "validate_bugs"})

        errors = state.get("errors", [])
        errors.append(
            {"node": "validate_bugs", "error": str(e), "timestamp": time.time()}
        )
        # On error, pass through all classified bugs as validated
        return {
            "validated_bugs": state.get("classified_bugs", []),
            "errors": errors,
        }


async def generate_reports(state: BugHiveState) -> dict[str, Any]:
    """Generate reports for validated bugs.

    Uses ReportWriterAgent to:
    - Create detailed bug reports
    - Format for Linear/Jira
    - Add reproduction steps
    - Include screenshots and evidence

    Args:
        state: Current workflow state

    Returns:
        State updates with generated reports
    """
    node_start = time.time()
    logger.info(f"[{state['session_id']}] Generating bug reports...")

    validated_bugs = state.get("validated_bugs", [])
    if not validated_bugs:
        logger.info("No validated bugs to report")
        return {"reported_bugs": []}

    try:
        reporter = ReportWriterAgent()
        reported_bugs = []
        total_report_cost = 0.0
        llm_calls = state.get("llm_calls", [])

        for bug in validated_bugs:
            # Skip duplicates
            if bug.get("is_duplicate"):
                continue

            report_result = await reporter.generate_report(
                bug_id=bug["id"],
                title=bug["title"],
                description=bug["description"],
                category=bug["category"],
                priority=bug["priority"],
                severity=bug["severity"],
                steps_to_reproduce=bug.get("steps_to_reproduce", []),
                expected_behavior=bug.get("expected_behavior", ""),
                actual_behavior=bug.get("actual_behavior", ""),
                environment=bug.get("environment", {}),
                screenshots=bug.get("screenshots", []),
            )

            reported_bugs.append(
                {
                    **bug,
                    "report": {
                        "formatted_report": report_result.formatted_report,
                        "linear_description": report_result.linear_description,
                        "jira_description": report_result.jira_description,
                        "suggested_labels": report_result.suggested_labels,
                        "estimated_effort": report_result.estimated_effort,
                    },
                    "reported_at": time.time(),
                }
            )

            total_report_cost += report_result.cost
            llm_calls.append(
                {
                    "node": "generate_reports",
                    "bug_id": bug["id"],
                    "model": report_result.model_used,
                    "input_tokens": report_result.input_tokens,
                    "output_tokens": report_result.output_tokens,
                    "cost": report_result.cost,
                }
            )

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["generate_reports"] = node_duration

        logger.info(
            f"[{state['session_id']}] Generated {len(reported_bugs)} reports. "
            f"Cost: ${total_report_cost:.4f}"
        )

        return {
            "reported_bugs": reported_bugs,
            "total_cost": state.get("total_cost", 0.0) + total_report_cost,
            "llm_calls": llm_calls,
            "node_durations": node_durations,
        }

    except Exception as e:
        logger.error(f"Error generating reports: {e}", exc_info=True)

        # Track error in aggregator
        error_agg = get_error_aggregator(state["session_id"])
        error_agg.add(e, context={"node": "generate_reports"})

        errors = state.get("errors", [])
        errors.append(
            {"node": "generate_reports", "error": str(e), "timestamp": time.time()}
        )
        return {"errors": errors}


async def create_linear_tickets(state: BugHiveState) -> dict[str, Any]:
    """Create Linear tickets for reported bugs.

    Creates tickets in Linear with:
    - Proper priority and labels
    - Formatted descriptions
    - Screenshot attachments
    - Links between related bugs

    Args:
        state: Current workflow state

    Returns:
        State updates with created Linear issue IDs and URLs
    """
    node_start = time.time()
    logger.info(f"[{state['session_id']}] Creating Linear tickets...")

    reported_bugs = state.get("reported_bugs", [])
    if not reported_bugs:
        logger.info("No reported bugs to create tickets for")
        return {"linear_tickets": []}

    config = state.get("config", {})
    if not config.get("create_linear_tickets", False):
        logger.info("Linear ticket creation disabled in config")
        return {"linear_tickets": []}

    try:
        linear_client = LinearClient()
        linear_tickets = state.get("linear_tickets", [])

        for bug in reported_bugs:
            # Skip if already has a ticket
            if any(t["bug_id"] == bug["id"] for t in linear_tickets):
                continue

            report = bug.get("report", {})

            # Create Linear issue
            issue = await linear_client.create_issue(
                title=bug["title"],
                description=report.get("linear_description", bug["description"]),
                priority=bug["priority"],
                labels=report.get("suggested_labels", [bug["category"]]),
                team_id=config.get("linear_team_id"),
            )

            linear_tickets.append(
                {
                    "bug_id": bug["id"],
                    "linear_id": issue["id"],
                    "linear_url": issue.get("url"),
                    "created_at": time.time(),
                }
            )

            logger.info(f"Created Linear ticket for bug {bug['id']}: {issue.get('url')}")

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["create_linear_tickets"] = node_duration

        logger.info(
            f"[{state['session_id']}] Created {len(linear_tickets)} Linear tickets"
        )

        return {
            "linear_tickets": linear_tickets,
            "node_durations": node_durations,
        }

    except Exception as e:
        logger.error(f"Error creating Linear tickets: {e}", exc_info=True)

        # Track error in aggregator
        error_agg = get_error_aggregator(state["session_id"])
        error_agg.add(e, context={"node": "create_linear_tickets"})

        errors = state.get("errors", [])
        errors.append(
            {
                "node": "create_linear_tickets",
                "error": str(e),
                "timestamp": time.time(),
            }
        )
        return {"errors": errors}


async def generate_summary(state: BugHiveState) -> dict[str, Any]:
    """Generate final session summary.

    Creates comprehensive summary with:
    - Pages crawled and analyzed
    - Bugs found by category and priority
    - Linear tickets created
    - Total cost and performance metrics
    - Recommendations for next steps

    Args:
        state: Current workflow state

    Returns:
        State updates with final summary
    """
    node_start = time.time()
    logger.info(f"[{state['session_id']}] Generating session summary...")

    try:
        pages_crawled = state.get("pages_crawled", [])
        raw_issues = state.get("raw_issues", [])
        classified_bugs = state.get("classified_bugs", [])
        validated_bugs = state.get("validated_bugs", [])
        linear_tickets = state.get("linear_tickets", [])
        errors = state.get("errors", [])

        # Calculate statistics
        bugs_by_priority = {}
        bugs_by_category = {}

        for bug in validated_bugs:
            if not bug.get("is_duplicate"):
                priority = bug.get("priority", "unknown")
                bugs_by_priority[priority] = bugs_by_priority.get(priority, 0) + 1

                category = bug.get("category", "unknown")
                bugs_by_category[category] = bugs_by_category.get(category, 0) + 1

        # Calculate duration
        start_time = state.get("start_time")
        end_time = time.time()
        duration = end_time - start_time if start_time else 0

        summary = {
            "session_id": state["session_id"],
            "duration_seconds": duration,
            "pages": {
                "total_discovered": len(state.get("pages_discovered", [])),
                "total_crawled": len(pages_crawled),
                "failed": len([p for p in state.get("pages_discovered", []) if p.get("status") == "failed"]),
            },
            "bugs": {
                "raw_issues_found": len(raw_issues),
                "classified_bugs": len(classified_bugs),
                "validated_bugs": len([b for b in validated_bugs if not b.get("is_duplicate")]),
                "duplicates_filtered": len([b for b in classified_bugs if b.get("is_duplicate")]),
                "by_priority": bugs_by_priority,
                "by_category": bugs_by_category,
            },
            "linear_tickets": {
                "total_created": len(linear_tickets),
                "ticket_urls": [t.get("linear_url") for t in linear_tickets if t.get("linear_url")],
            },
            "cost": {
                "total_usd": state.get("total_cost", 0.0),
                "by_node": {},
            },
            "performance": {
                "node_durations": state.get("node_durations", {}),
            },
            "errors": {
                "total_errors": len(errors),
                "by_node": {},
            },
            "recommendations": [],
        }

        # Cost by node
        for call in state.get("llm_calls", []):
            node = call.get("node", "unknown")
            cost = call.get("cost", 0.0)
            summary["cost"]["by_node"][node] = summary["cost"]["by_node"].get(node, 0.0) + cost

        # Errors by node
        for error in errors:
            node = error.get("node", "unknown")
            summary["errors"]["by_node"][node] = summary["errors"]["by_node"].get(node, 0) + 1

        # Generate recommendations
        if bugs_by_priority.get("critical", 0) > 0:
            summary["recommendations"].append(
                f"Immediate attention needed: {bugs_by_priority['critical']} critical bugs found"
            )

        if summary["pages"]["failed"] > 5:
            summary["recommendations"].append(
                f"High page failure rate: {summary['pages']['failed']} pages failed to crawl"
            )

        if summary["cost"]["total_usd"] > 10:
            summary["recommendations"].append(
                f"High cost detected: ${summary['cost']['total_usd']:.2f}. Consider optimizing crawl strategy."
            )

        if len(errors) > 10:
            summary["recommendations"].append(
                f"Multiple errors detected ({len(errors)}). Review error logs for patterns."
            )

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["generate_summary"] = node_duration

        logger.info(
            f"[{state['session_id']}] Summary generated. "
            f"Crawled {len(pages_crawled)} pages, found {len(validated_bugs)} bugs, "
            f"created {len(linear_tickets)} tickets. Total cost: ${summary['cost']['total_usd']:.2f}"
        )

        return {
            "summary": summary,
            "end_time": end_time,
            "node_durations": node_durations,
        }

    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)

        # Track error in aggregator
        error_agg = get_error_aggregator(state["session_id"])
        error_agg.add(e, context={"node": "generate_summary"})

        errors = state.get("errors", [])
        errors.append(
            {"node": "generate_summary", "error": str(e), "timestamp": time.time()}
        )
        return {
            "summary": {"error": str(e)},
            "errors": errors,
        }


async def report_error_patterns(state: BugHiveState) -> dict[str, Any]:
    """Report aggregated error patterns detected during the session.

    Analyzes all errors from the session using ErrorAggregator to:
    - Group similar errors by type and message prefix
    - Identify systemic issues and patterns
    - Report top error patterns with occurrence counts
    - Add pattern analysis to the final summary

    Args:
        state: Current workflow state

    Returns:
        State updates with error pattern analysis
    """
    node_start = time.time()
    logger.info(f"[{state['session_id']}] Analyzing error patterns...")

    try:
        error_agg = get_error_aggregator(state["session_id"])

        # Get error patterns
        error_summary = error_agg.get_summary()
        error_patterns = error_agg.get_patterns(min_occurrences=2)

        # Add to state summary
        summary = state.get("summary", {})
        summary["error_analysis"] = {
            "total_errors": error_summary["total_errors"],
            "unique_error_types": error_summary["unique_types"],
            "pattern_count": error_summary["pattern_count"],
            "detected_patterns": error_patterns,
        }

        # Log pattern findings
        if error_patterns:
            logger.warning(
                f"Detected {len(error_patterns)} error patterns during session:"
            )
            for i, pattern in enumerate(error_patterns[:5], 1):  # Top 5 patterns
                logger.warning(
                    f"  {i}. {pattern['error_type']}: "
                    f"{pattern['count']} occurrences - {pattern['message_prefix']}"
                )
            if len(error_patterns) > 5:
                logger.warning(
                    f"  ... and {len(error_patterns) - 5} more patterns"
                )
        else:
            logger.info("No error patterns detected (errors are isolated)")

        node_duration = time.time() - node_start
        node_durations = state.get("node_durations", {})
        node_durations["report_error_patterns"] = node_duration

        return {
            "summary": summary,
            "error_analysis": error_summary,
            "node_durations": node_durations,
        }

    except Exception as e:
        logger.error(f"Error analyzing patterns: {e}", exc_info=True)
        # Don't fail the entire workflow on pattern analysis error
        return {"summary": state.get("summary", {})}
