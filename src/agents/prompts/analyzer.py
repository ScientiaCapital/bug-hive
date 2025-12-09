"""Prompt templates for Page Analyzer Agent.

Note: These prompts are used in conjunction with BUGHIVE_SYSTEM_PROMPT from __init__.py
to ensure consistent agent behavior and persona across the BugHive system.
"""

# Import system prompt for reference (actual use is in agent implementation)
from src.agents.prompts import BUGHIVE_SYSTEM_PROMPT  # noqa: F401

ANALYZE_PAGE_PROMPT = """You are an expert QA engineer analyzing a web page for bugs and issues.

## Page Information
URL: {url}
Title: {title}

## Console Logs
{console_logs}

## Network Requests
{network_requests}

## Forms
{forms}

## Performance Metrics
{performance_metrics}

## Your Task
Analyze this page data and identify potential bugs and issues. Look for:

### 1. JavaScript Errors
- Uncaught exceptions and runtime errors
- React/Vue/Angular framework errors
- Unhandled promise rejections
- Type errors and undefined references

### 2. Network Failures
- 4xx client errors (404, 403, etc.)
- 5xx server errors (500, 503, etc.)
- Timeout errors
- CORS (Cross-Origin Resource Sharing) issues
- Failed API calls

### 3. Performance Issues
- Page load time > 3 seconds
- API calls taking > 5 seconds
- Large bundle sizes (> 1MB)
- Excessive network requests

### 4. Content Issues
- "Lorem ipsum" placeholder text visible to users
- TODO/FIXME comments exposed in production
- Debug console.log statements in production
- Hardcoded test data visible

### 5. Form Issues
- Missing required field validation
- Forms without submit handlers
- Input fields without labels
- Broken form submissions

### 6. Accessibility Issues
- Missing alt text on images
- Low color contrast
- Missing ARIA labels
- Keyboard navigation problems

## Response Format
Return a JSON array of issues. Each issue must have:

{{
  "type": "console_error|network_failure|performance|content|form|accessibility",
  "title": "Brief descriptive title (max 100 chars)",
  "description": "Detailed explanation of the issue and its impact",
  "confidence": 0.0-1.0,  // How confident are you this is a real issue?
  "severity": "critical|high|medium|low",
  "reasoning": "Step-by-step explanation of how you reached this conclusion",
  "metadata": {{
    // Optional: Any additional context (line numbers, affected elements, etc.)
  }}
}}

## Severity Guidelines
- **critical**: Breaks core functionality, security vulnerabilities, data loss
- **high**: Significant user impact, broken features, major performance issues
- **medium**: Degraded UX, minor bugs, performance slowdowns
- **low**: Cosmetic issues, minor inconsistencies

## Confidence Guidelines
- **0.9-1.0**: Definite bug with clear evidence
- **0.7-0.9**: Likely bug, strong indicators
- **0.5-0.7**: Possible issue, needs investigation
- **0.3-0.5**: Uncertain, may be false positive
- **0.0-0.3**: Low confidence, questionable

## Important Notes
- Only report actual issues, not potential improvements
- Focus on user-facing bugs, not code style
- Be specific in descriptions
- Provide actionable information
- Consider the user impact

Return ONLY the JSON array, no additional text.
"""


CLASSIFY_ISSUE_PROMPT = """You are a QA engineer classifying a detected issue.

## Issue Details
Title: {title}
Description: {description}
Type: {issue_type}

## Evidence
{evidence}

## Your Task
Analyze this issue and provide:
1. Refined severity level (critical, high, medium, low)
2. Updated confidence score (0.0-1.0)
3. Bug category (ui_ux, data, edge_case, performance, security)
4. Priority level for fixing
5. Estimated user impact

Return as JSON:
{{
  "severity": "critical|high|medium|low",
  "confidence": 0.0-1.0,
  "category": "ui_ux|data|edge_case|performance|security",
  "priority": "critical|high|medium|low",
  "user_impact": "Brief description of how this affects users",
  "affected_users": "all_users|mobile_users|specific_feature|edge_case",
  "reproducibility": "always|sometimes|rarely",
  "reasoning": "Step-by-step explanation of your classification decision"
}}

Be objective and base your assessment on the evidence provided.
Return ONLY the JSON object, no additional text.
"""


DEDUPLICATE_ISSUES_PROMPT = """You are a QA engineer deduplicating bug reports.

## Issues to Analyze
{issues}

## Your Task
Identify duplicate or similar issues that should be merged.

Two issues are duplicates if they:
- Describe the same underlying bug
- Have the same root cause
- Affect the same functionality
- Have overlapping evidence

Return as JSON array of duplicate groups:
[
  {{
    "primary_issue_index": 0,  // Index of the issue to keep
    "duplicate_indices": [2, 5],  // Indices of duplicates to merge
    "reason": "Brief explanation why these are duplicates"
  }}
]

If no duplicates found, return empty array: []

Return ONLY the JSON array, no additional text.
"""


GENERATE_BUG_STEPS_PROMPT = """You are a QA engineer writing reproduction steps for a bug.

## Bug Information
Title: {title}
Description: {description}
URL: {url}
Evidence: {evidence}

## Your Task
Generate clear, numbered steps to reproduce this bug.

Good reproduction steps:
1. Start from a known state
2. Be specific and actionable
3. Include exact UI elements to interact with
4. Specify input values if needed
5. Describe expected vs actual behavior

Return as JSON:
{{
  "steps_to_reproduce": [
    "Step 1: Navigate to...",
    "Step 2: Click on...",
    "Step 3: Enter...",
    "Step 4: Observe..."
  ],
  "expected_behavior": "What should happen",
  "actual_behavior": "What actually happens",
  "preconditions": ["Any setup needed before steps"],
  "reasoning": "Explanation of how you derived these steps from the evidence"
}}

Return ONLY the JSON object, no additional text.
"""
