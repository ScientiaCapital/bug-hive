"""Prompt templates for Bug Classifier Agent.

Note: These prompts are used in conjunction with BUGHIVE_SYSTEM_PROMPT from __init__.py
to ensure consistent agent behavior and persona across the BugHive system.
"""

# Import system prompt for reference (actual use is in agent implementation)
from src.agents.prompts import BUGHIVE_SYSTEM_PROMPT  # noqa: F401

CLASSIFY_BUG = """Classify this bug into a category and priority.

Bug Details:
Title: {title}
Type: {type}
Description: {description}
Evidence Count: {evidence_count}
URL: {url}

Categories:
- ui_ux: Visual defects, layout issues, styling problems, responsive design issues
- data: Incorrect data display, missing data, stale data, data validation failures
- edge_case: Input handling failures, boundary issues, unexpected state transitions
- performance: Slow loads, memory leaks, large payloads, rendering bottlenecks
- security: XSS, injection, auth bypass, data exposure, CORS issues

Priority Levels:
- critical: App crash, data loss, security vulnerability, complete feature failure
- high: Core feature broken, significant UX impact, affects many users
- medium: Feature partially broken, workaround exists, cosmetic but noticeable
- low: Minor visual issue, cosmetic defect, rare edge case

Context:
- Console errors often indicate ui_ux or edge_case issues
- Network failures with 5xx codes are typically critical data issues
- Performance issues with load times > 3s are high priority
- Security issues are always critical or high priority
- Visual issues are usually low priority unless they block core functionality

Return JSON:
{{
    "category": "...",
    "priority": "...",
    "confidence": 0.X,
    "reasoning": "Brief explanation of classification"
}}"""

DEDUPLICATE_BUGS = """Are these two bugs duplicates or variants of the same issue?

Bug 1:
Title: {title1}
Description: {description1}
Category: {category1}
URL: {url1}

Bug 2:
Title: {title2}
Description: {description2}
Category: {category2}
URL: {url2}

Consider duplicates if:
- Same error message with same root cause
- Same visual issue across different pages
- Related console errors from same code path
- Same network failure endpoint and error

NOT duplicates if:
- Different categories (e.g., ui_ux vs performance)
- Different root causes (e.g., different API endpoints)
- Different symptoms (e.g., button position vs button color)
- Unrelated evidence (e.g., different stack traces)

Return JSON:
{{
    "is_duplicate": true/false,
    "similarity": 0.X,
    "reasoning": "Step-by-step explanation of duplicate assessment"
}}"""

COMPUTE_SIMILARITY = """Compute the semantic similarity between these two bug descriptions.

Description 1:
{description1}

Description 2:
{description2}

Consider similar if they describe:
- The same error or failure mode
- The same visual defect
- The same user-facing symptom
- The same root cause

Return JSON:
{{
    "similarity": 0.X,
    "reasoning": "Step-by-step explanation of similarity score"
}}"""
