"""Prompts for the Report Writer Agent.

These prompts are used to generate well-formatted Linear tickets
from Bug objects using the LLM.

Note: These prompts are used in conjunction with BUGHIVE_SYSTEM_PROMPT from __init__.py
to ensure consistent agent behavior and persona across the BugHive system.
"""

# Import system prompt for reference (actual use is in agent implementation)
from src.agents.prompts import BUGHIVE_SYSTEM_PROMPT  # noqa: F401

FORMAT_TICKET = """
Generate a well-formatted bug report for Linear issue tracking.

Bug Details:
- Title: {title}
- Category: {category}
- Priority: {priority}
- Description: {description}

Evidence:
{evidence}

URL: {url}
Timestamp: {timestamp}

Format the report as clean, professional markdown with these sections:

## Summary
[One-line description of the issue - clear and actionable]

## Steps to Reproduce
1. Navigate to [specific page/URL]
2. [Specific action taken - be precise]
3. [Another action if needed]
4. [Expected vs actual result]

## Evidence
{evidence_formatted}

## Environment
- URL: {url}
- Browser: Chrome (via Browserbase)
- User Agent: [If available from evidence]
- Timestamp: {timestamp}

## Suggested Priority
**{priority}** - [Brief justification based on impact and severity]

## Additional Context
[Any other relevant information from the description or evidence]

Guidelines:
- Be concise but complete
- Use markdown formatting (bold, lists, code blocks)
- Include exact error messages in code blocks
- Link to screenshots if available
- Make steps reproducible by a developer who has never seen the issue
- Justify the priority level
- If console errors exist, include them in a code block
- If network requests failed, include the URL and status code

Output ONLY the formatted markdown report. Do not include any preamble or explanations.
"""

PRIORITIZE_BUG = """
Analyze this bug and suggest an appropriate priority level.

Bug Details:
- Title: {title}
- Category: {category}
- Description: {description}
- Evidence: {evidence}

Priority Levels:
- **critical**: System down, data loss, security breach, major functionality broken
- **high**: Important feature broken, significant UX degradation, affects many users
- **medium**: Feature partially broken, workaround exists, affects some users
- **low**: Minor issue, cosmetic bug, edge case, low user impact

Consider:
1. Impact: How many users are affected?
2. Severity: How badly does it affect the user experience?
3. Workaround: Can users still accomplish their goal another way?
4. Frequency: How often does this occur?
5. Security: Does this expose any vulnerabilities?

Respond with ONLY one word: critical, high, medium, or low
"""

SUMMARIZE_BUG = """
Create a concise one-line summary for this bug suitable as a Linear issue title.

Bug Details:
- Category: {category}
- Description: {description}
- URL: {url}

Requirements:
- Maximum 80 characters
- Start with action verb (e.g., "Fix", "Resolve", "Correct")
- Be specific (include component/page name)
- Be actionable
- No jargon or unclear abbreviations

Examples:
- "Fix submit button not responding on checkout page"
- "Resolve 500 error when loading user profile with missing avatar"
- "Correct misaligned header on mobile devices"

Respond with ONLY the title text, no quotes or explanation.
"""
