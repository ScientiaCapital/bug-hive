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
    "reasoning": "Detailed step-by-step reasoning: (1) Evidence analysis, (2) Category selection rationale, (3) Priority determination, (4) Confidence justification, (5) Alternative classifications considered"
}}

**IMPORTANT**: Provide comprehensive reasoning that demonstrates:
- Analysis of all available evidence
- Clear logical steps from evidence to conclusion
- Consideration of edge cases and alternative interpretations
- Justification for confidence level based on evidence quality"""

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
    "reasoning": "Thorough reasoning: (1) Comparison of symptoms, (2) Root cause analysis, (3) Evidence overlap assessment, (4) Similarity score justification, (5) Final duplicate determination with supporting details"
}}

**IMPORTANT**: Reasoning should include:
- Point-by-point comparison of bug characteristics
- Analysis of whether symptoms indicate same root cause
- Evaluation of evidence overlap
- Clear explanation of similarity score calculation"""

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
    "reasoning": "Detailed reasoning process: (1) Semantic analysis of both descriptions, (2) Identification of shared concepts, (3) Evaluation of symptom overlap, (4) Assessment of root cause similarity, (5) Final similarity score calculation with justification"
}}

**IMPORTANT**: Provide transparent reasoning:
- Break down the semantic comparison methodically
- Identify specific shared terminology and concepts
- Explain how overlap in symptoms affects the score
- Justify the final similarity value with concrete examples"""
