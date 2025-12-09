"""Prompt templates for agents."""

# Shared system prompt for all BugHive agents
# This prompt is prepended to all agent prompts to ensure consistent behavior
BUGHIVE_SYSTEM_PROMPT = """
You are DeepQA, an expert autonomous QA engineer within the BugHive system.
Your role is to identify bugs that real users will encounter.

You have access to:
- Page DOM analysis and network monitoring
- Performance profiling and accessibility checking
- Screenshot evidence collection

You must:
1. Reason through evidence systematically before concluding
2. Flag uncertainty when confidence is below 0.8
3. Prioritize user impact over technical correctness
4. Provide reasoning traces with your decisions

When unsure, escalate to human review rather than guess.
"""

__all__ = [
    # System prompt
    "BUGHIVE_SYSTEM_PROMPT",
    # Analyzer prompts (imported lazily to avoid circular imports)
    "ANALYZE_PAGE_PROMPT",
    "CLASSIFY_ISSUE_PROMPT",
    "DEDUPLICATE_ISSUES_PROMPT",
    "GENERATE_BUG_STEPS_PROMPT",
    # Crawler prompts
    "PLAN_CRAWL_STRATEGY",
    "SHOULD_CRAWL",
    "EXTRACT_NAVIGATION_CONTEXT",
]


# Import prompt templates after defining BUGHIVE_SYSTEM_PROMPT to avoid circular imports
def __getattr__(name: str):
    """Lazy import to avoid circular imports."""
    if name in __all__:
        if name == "BUGHIVE_SYSTEM_PROMPT":
            return BUGHIVE_SYSTEM_PROMPT
        elif name in [
            "ANALYZE_PAGE_PROMPT",
            "CLASSIFY_ISSUE_PROMPT",
            "DEDUPLICATE_ISSUES_PROMPT",
            "GENERATE_BUG_STEPS_PROMPT",
        ]:
            from src.agents.prompts.analyzer import (
                ANALYZE_PAGE_PROMPT,
                CLASSIFY_ISSUE_PROMPT,
                DEDUPLICATE_ISSUES_PROMPT,
                GENERATE_BUG_STEPS_PROMPT,
            )

            return {
                "ANALYZE_PAGE_PROMPT": ANALYZE_PAGE_PROMPT,
                "CLASSIFY_ISSUE_PROMPT": CLASSIFY_ISSUE_PROMPT,
                "DEDUPLICATE_ISSUES_PROMPT": DEDUPLICATE_ISSUES_PROMPT,
                "GENERATE_BUG_STEPS_PROMPT": GENERATE_BUG_STEPS_PROMPT,
            }[name]
        elif name in ["PLAN_CRAWL_STRATEGY", "SHOULD_CRAWL", "EXTRACT_NAVIGATION_CONTEXT"]:
            from src.agents.prompts.crawler import (
                EXTRACT_NAVIGATION_CONTEXT,
                PLAN_CRAWL_STRATEGY,
                SHOULD_CRAWL,
            )

            return {
                "PLAN_CRAWL_STRATEGY": PLAN_CRAWL_STRATEGY,
                "SHOULD_CRAWL": SHOULD_CRAWL,
                "EXTRACT_NAVIGATION_CONTEXT": EXTRACT_NAVIGATION_CONTEXT,
            }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
