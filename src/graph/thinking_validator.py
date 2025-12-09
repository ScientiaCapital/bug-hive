"""Extended thinking validation for critical bugs."""

import json
import logging
from typing import Any

from src.llm.anthropic import AnthropicClient

logger = logging.getLogger(__name__)


async def validate_bug_with_thinking(
    bug: dict[str, Any],
    anthropic_client: AnthropicClient | None = None,
) -> dict[str, Any]:
    """
    Validate a bug using extended thinking for deep analysis.

    Uses Claude's extended thinking capability to provide transparent
    reasoning traces for complex bug validation decisions.

    Args:
        bug: Bug dictionary with fields: id, title, priority, severity,
             category, description, steps_to_reproduce, expected_behavior,
             actual_behavior, confidence_score
        anthropic_client: Optional pre-initialized AnthropicClient.
                         If None, creates a new client.

    Returns:
        Dict with validation results including:
            - is_valid: bool
            - validated_priority: str
            - business_impact: str
            - recommended_action: str
            - validation_notes: str
            - confidence: float
            - reasoning: str (detailed step-by-step reasoning)
            - thinking_trace: str | None (extended thinking output)
            - usage: dict (token usage statistics)
            - cost: float (estimated cost in USD)

    Example:
        >>> bug = {
        ...     "id": "bug-123",
        ...     "title": "Login button not working",
        ...     "priority": "critical",
        ...     "severity": "high",
        ...     "category": "ui_ux",
        ...     "description": "Users cannot log in",
        ...     "steps_to_reproduce": ["Navigate to /login", "Click login button"],
        ...     "expected_behavior": "User should be logged in",
        ...     "actual_behavior": "Nothing happens",
        ...     "confidence_score": 0.95
        ... }
        >>> result = await validate_bug_with_thinking(bug)
        >>> print(result["is_valid"])
        True
        >>> print(result["thinking_trace"][:100])
        "Let me carefully analyze this bug report..."
    """
    # Create client if not provided
    should_close_client = False
    if anthropic_client is None:
        anthropic_client = AnthropicClient()
        should_close_client = True

    try:
        validation_prompt = f"""You are validating a potential bug from an autonomous QA system.

**Bug Report:**
- ID: {bug.get('id', 'unknown')}
- Title: {bug.get('title', 'N/A')}
- Priority: {bug.get('priority', 'unknown')}
- Severity: {bug.get('severity', 'unknown')}
- Category: {bug.get('category', 'unknown')}
- Confidence: {bug.get('confidence_score', 0.0)}

**Description:**
{bug.get('description', 'No description provided')}

**Steps to Reproduce:**
{chr(10).join(bug.get('steps_to_reproduce', ['No steps provided']))}

**Expected vs Actual:**
- Expected: {bug.get('expected_behavior', 'N/A')}
- Actual: {bug.get('actual_behavior', 'N/A')}

**Your Task:**
Think deeply and systematically about this bug report. Validate it thoroughly and provide:

1. **Bug Legitimacy**: Is this a real bug or a false positive?
   - Analyze the evidence quality
   - Consider alternative explanations
   - Evaluate confidence level justification

2. **Priority Assessment**: Is the assigned priority correct?
   - Evaluate user impact
   - Consider business criticality
   - Compare to severity

3. **Business Impact**: What are the consequences?
   - User experience impact
   - Revenue/conversion impact
   - Brand/reputation impact
   - Security implications

4. **Recommended Action**: What should be done?
   - Fix immediately (blocks users)
   - Schedule (important but not blocking)
   - Defer (low impact, backlog)
   - Dismiss (false positive or won't fix)

**Output JSON:**
{{
    "is_valid": true/false,
    "validated_priority": "critical|high|medium|low",
    "business_impact": "Comprehensive description of business impact",
    "recommended_action": "fix_immediately|schedule|defer|dismiss",
    "validation_notes": "Additional context, concerns, or recommendations",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed step-by-step reasoning covering all four analysis areas above"
}}

**IMPORTANT**:
- Think step-by-step through each validation aspect
- Consider edge cases and alternative interpretations
- Base conclusions on evidence, not assumptions
- Be conservative with "critical" priority validation
- Provide actionable, specific reasoning
"""

        # Use extended thinking for deep analysis
        logger.info(f"Starting extended thinking validation for bug {bug.get('id')}")

        response_data = await anthropic_client.create_message_with_thinking(
            messages=[{"role": "user", "content": validation_prompt}],
            max_tokens=8000,
            thinking_budget=5000,
            temperature=0.7,
            model="claude-opus-4-5-20250514",
        )

        # Parse validation from content
        try:
            validation = json.loads(response_data["content"])
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse validation JSON: {e}\nContent: {response_data['content']}"
            )
            # Return conservative validation on parse error
            validation = {
                "is_valid": False,
                "validated_priority": bug.get("priority", "medium"),
                "business_impact": "Unable to validate - JSON parse error",
                "recommended_action": "defer",
                "validation_notes": f"Validation parsing failed: {str(e)}",
                "confidence": 0.0,
                "reasoning": "Failed to parse validation response",
            }

        # Add extended thinking trace
        validation["thinking_trace"] = response_data.get("thinking")
        if validation["thinking_trace"]:
            logger.info(
                f"Extended thinking trace captured: {len(validation['thinking_trace'])} chars"
            )
        else:
            logger.warning("No thinking trace returned from extended thinking API")

        # Add token usage statistics
        validation["usage"] = response_data["usage"]

        # Calculate cost (Claude Opus 4.5 pricing: $15/MTok input, $75/MTok output)
        input_tokens = response_data["usage"]["input_tokens"]
        output_tokens = response_data["usage"]["output_tokens"]
        validation["cost"] = (input_tokens / 1_000_000 * 15) + (
            output_tokens / 1_000_000 * 75
        )

        logger.info(
            f"Validation complete for bug {bug.get('id')}: "
            f"is_valid={validation.get('is_valid')}, "
            f"priority={validation.get('validated_priority')}, "
            f"action={validation.get('recommended_action')}, "
            f"cost=${validation['cost']:.4f}"
        )

        return validation

    finally:
        # Close client if we created it
        if should_close_client:
            await anthropic_client.close()


async def batch_validate_bugs_with_thinking(
    bugs: list[dict[str, Any]],
    anthropic_client: AnthropicClient | None = None,
) -> list[dict[str, Any]]:
    """
    Validate multiple bugs using extended thinking.

    Reuses the same AnthropicClient for efficiency.

    Args:
        bugs: List of bug dictionaries to validate
        anthropic_client: Optional pre-initialized client

    Returns:
        List of validation results (one per bug)
    """
    # Create client if not provided
    should_close_client = False
    if anthropic_client is None:
        anthropic_client = AnthropicClient()
        should_close_client = True

    try:
        validations = []
        for bug in bugs:
            validation = await validate_bug_with_thinking(bug, anthropic_client)
            validations.append(validation)

        return validations

    finally:
        if should_close_client:
            await anthropic_client.close()
