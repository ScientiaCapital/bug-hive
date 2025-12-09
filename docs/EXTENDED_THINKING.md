# Extended Thinking & Reasoning Traces

## Overview

BugHive now supports **Extended Thinking** using Claude's advanced reasoning capabilities. This feature provides transparent reasoning traces for complex bug validation and analysis, dramatically improving debugging and decision-making quality.

## What is Extended Thinking?

Extended Thinking is Claude's ability to show its internal reasoning process before providing a final answer. Instead of just getting a result, you see:

- **Thinking Trace**: Step-by-step reasoning process
- **Final Answer**: The validated result with full context
- **Reasoning Field**: Structured explanation in the response

This is particularly valuable for:
- **Critical bug validation** - Ensure high-severity bugs are legitimate
- **Complex analysis** - Debug why a bug was classified a certain way
- **False positive detection** - Understand the AI's confidence level
- **Business impact assessment** - See the reasoning behind priority decisions

## Implementation

### 1. AnthropicClient Extended Thinking

**File**: `/src/llm/anthropic.py`

New method `create_message_with_thinking()` enables extended thinking:

```python
from src.llm.anthropic import AnthropicClient

async with AnthropicClient() as client:
    response = await client.create_message_with_thinking(
        messages=[{"role": "user", "content": "Analyze this bug..."}],
        max_tokens=8000,
        thinking_budget=5000,  # Tokens allocated for thinking
        temperature=0.7,
        model="claude-opus-4-5-20250514"
    )

    print("Thinking:", response["thinking"])  # Reasoning trace
    print("Answer:", response["content"])     # Final validated result
    print("Tokens:", response["usage"])        # Token usage stats
```

**Key Parameters**:
- `thinking_budget` - Token budget for reasoning (default: 10000)
- `max_tokens` - Maximum tokens for final answer (default: 16000)
- `model` - Uses Claude Opus 4.5 for best reasoning

**Response Structure**:
```python
{
    "content": "JSON result with validation...",
    "thinking": "Let me analyze this carefully. Step 1: ...",
    "usage": {
        "input_tokens": 500,
        "output_tokens": 300,
        "total_tokens": 800
    },
    "stop_reason": "end_turn"
}
```

### 2. Reasoning Fields in Prompts

All prompts now include explicit `reasoning` fields to capture step-by-step analysis.

#### Analyzer Prompts (`/src/agents/prompts/analyzer.py`)

**ANALYZE_PAGE_PROMPT**:
```json
{
  "type": "console_error|network_failure|...",
  "title": "Brief title",
  "description": "Detailed explanation",
  "confidence": 0.95,
  "severity": "critical|high|medium|low",
  "reasoning": "Step-by-step explanation of how you identified this issue, analyzed its severity, and determined confidence level"
}
```

**Reasoning Requirements**:
1. What evidence led to identifying this issue?
2. Why this severity level?
3. What influenced the confidence score?
4. What user impact considerations were made?

#### Classifier Prompts (`/src/agents/prompts/classifier.py`)

**CLASSIFY_BUG**:
```json
{
    "category": "ui_ux|data|edge_case|performance|security",
    "priority": "critical|high|medium|low",
    "confidence": 0.85,
    "reasoning": "Detailed step-by-step reasoning: (1) Evidence analysis, (2) Category selection rationale, (3) Priority determination, (4) Confidence justification, (5) Alternative classifications considered"
}
```

**DEDUPLICATE_BUGS**:
```json
{
    "is_duplicate": true/false,
    "similarity": 0.7,
    "reasoning": "Thorough reasoning: (1) Comparison of symptoms, (2) Root cause analysis, (3) Evidence overlap assessment, (4) Similarity score justification, (5) Final duplicate determination with supporting details"
}
```

### 3. Thinking Validator Module

**File**: `/src/graph/thinking_validator.py`

Dedicated module for validating bugs with extended thinking:

```python
from src.graph.thinking_validator import validate_bug_with_thinking

bug = {
    "id": "bug-123",
    "title": "Login button not working",
    "priority": "critical",
    "description": "Users cannot log in",
    # ... other fields
}

result = await validate_bug_with_thinking(bug)

print(result["is_valid"])           # True/False
print(result["validated_priority"]) # critical|high|medium|low
print(result["thinking_trace"])     # Full reasoning trace
print(result["reasoning"])          # Structured reasoning in JSON
print(result["cost"])               # Cost in USD
```

**Validation Output**:
```python
{
    "is_valid": True,
    "validated_priority": "critical",
    "business_impact": "Login is broken for all users, blocking access completely",
    "recommended_action": "fix_immediately|schedule|defer|dismiss",
    "validation_notes": "Clear evidence of broken core functionality",
    "confidence": 0.98,
    "reasoning": "Step 1: Evidence shows reproducible failure. Step 2: Login is critical path. Step 3: Affects all users. Step 4: No workaround exists.",
    "thinking_trace": "Let me analyze this carefully. The bug report indicates...",
    "usage": {"input_tokens": 500, "output_tokens": 300},
    "cost": 0.0165  # $0.0165 USD
}
```

**Batch Validation**:
```python
from src.graph.thinking_validator import batch_validate_bugs_with_thinking

bugs = [bug1, bug2, bug3]
results = await batch_validate_bugs_with_thinking(bugs)

for result in results:
    print(f"Bug {result['bug_id']}: {result['recommended_action']}")
```

### 4. Integration in Workflow

**File**: `/src/graph/nodes.py` (future integration)

Extended thinking is used for critical/high priority bug validation:

```python
# In validate_bugs node
if bug["priority"] in ("critical", "high"):
    # Use extended thinking for deep validation
    result = await validate_bug_with_thinking(bug)

    if result["thinking_trace"]:
        logger.info(f"Thinking trace: {result['thinking_trace'][:200]}...")
```

## Benefits

### 1. Improved Accuracy

Extended thinking reduces false positives by encouraging thorough analysis:

```
Without Extended Thinking:
"API returns 404" → Classified as Critical Bug

With Extended Thinking:
Thinking: "Wait, they're requesting '/users/nonexistent'. A 404 is the
*correct* response for a resource that doesn't exist. This is standard
REST behavior, not a bug."
Result: Dismissed as False Positive
```

### 2. Transparent Decision Making

See exactly why the AI made a decision:

```
Bug: SQL Injection in Login Form

Thinking Trace:
"This is a serious security issue. The payload 'admin' OR '1'='1' is a
classic SQL injection attack. Let me assess severity:

1. OWASP Top 10 #1 (Injection)
2. Allows authentication bypass
3. Can lead to data breach
4. Trivially exploitable

Evidence is strong - reproducible steps, clear attack vector. Priority:
Critical is correct. Recommendation: Fix immediately."

Reasoning (Structured):
"Step 1: Bug legitimacy - SQL injection confirmed by successful auth bypass
 Step 2: Priority - Critical due to OWASP Top 10, complete auth bypass
 Step 3: Business impact - Data breach risk, compliance violations
 Step 4: Action - Immediate fix required, disable endpoint if needed"
```

### 3. Better Debugging

When bugs are mis-classified, the reasoning helps identify issues:

```
Expected: Critical
Actual: Medium

Reasoning:
"Evidence shows error only on specific edge case (mobile Safari < v12).
Affects <1% of users based on browser stats. Workaround exists (use desktop).
Severity is high but impact is low. Downgrading to medium priority."

→ Developer can see the AI considered browser stats and made a data-driven decision
```

### 4. Cost Tracking

Extended thinking costs are tracked transparently:

```python
{
    "usage": {
        "input_tokens": 500,
        "output_tokens": 300,
        "total_tokens": 800
    },
    "cost": 0.0165  # Claude Opus: $15/MTok input, $75/MTok output
}
```

## Cost Analysis

**Claude Opus 4.5 Pricing**:
- Input: $15 per million tokens
- Output: $75 per million tokens

**Typical Extended Thinking Validation**:
- Input: ~500 tokens (bug context)
- Thinking: ~2000 tokens (reasoning process)
- Output: ~300 tokens (final validation)
- **Total Cost**: ~$0.015-0.025 per validation

**When to Use Extended Thinking**:
- ✅ Critical/High priority bugs (worth the cost for accuracy)
- ✅ Ambiguous cases needing deep analysis
- ✅ Security vulnerabilities (need thorough validation)
- ❌ Low priority bugs (use standard validation)
- ❌ Obvious duplicates (simple classification is fine)

## Usage Recommendations

### 1. Use for Critical Bugs Only

```python
if bug["priority"] in ("critical", "high"):
    result = await validate_bug_with_thinking(bug)
else:
    result = await standard_validation(bug)
```

### 2. Log Thinking Traces

```python
if result["thinking_trace"]:
    logger.info(f"Extended thinking for bug {bug_id}:")
    logger.info(result["thinking_trace"])
```

### 3. Store Reasoning in Database

```sql
CREATE TABLE bug_validations (
    bug_id UUID PRIMARY KEY,
    is_valid BOOLEAN,
    validated_priority VARCHAR(20),
    reasoning TEXT,
    thinking_trace TEXT,
    confidence FLOAT,
    validated_at TIMESTAMP
);
```

### 4. Review Thinking Traces for Model Improvement

Periodically review thinking traces to:
- Identify patterns in false positives
- Improve prompt templates
- Adjust confidence thresholds
- Train team on AI reasoning

## Testing

**Test File**: `/tests/test_extended_thinking.py`

Comprehensive test suite covering:

1. **AnthropicClient Tests**
   - `test_create_message_with_thinking_success`
   - `test_create_message_with_thinking_no_thinking_block`
   - `test_create_message_with_thinking_custom_parameters`

2. **Thinking Validator Tests**
   - `test_validate_bug_with_thinking_success`
   - `test_validate_bug_with_thinking_invalid_json`
   - `test_batch_validate_bugs_with_thinking`

3. **Integration Tests**
   - `test_extended_thinking_reduces_false_positives`
   - `test_extended_thinking_validates_critical_bug`

4. **Prompt Tests**
   - `test_analyzer_prompt_has_reasoning`
   - `test_classifier_prompt_has_reasoning`

**Run Tests**:
```bash
python -m pytest tests/test_extended_thinking.py -v
```

## Examples

### Example 1: Critical Bug Validation

```python
critical_bug = {
    "id": "bug-001",
    "title": "SQL Injection in search endpoint",
    "priority": "critical",
    "severity": "critical",
    "category": "security",
    "description": "User input directly interpolated into SQL query",
    "steps_to_reproduce": [
        "Navigate to /search",
        "Enter: '; DROP TABLE users; --",
        "Submit form",
        "Observe SQL error exposing injection"
    ],
    "expected_behavior": "Safe search results",
    "actual_behavior": "SQL injection executed",
    "confidence_score": 0.99
}

result = await validate_bug_with_thinking(critical_bug)

# Output:
{
    "is_valid": True,
    "validated_priority": "critical",
    "business_impact": "Critical SQL injection allows database manipulation, data exfiltration, and potential complete system compromise",
    "recommended_action": "fix_immediately",
    "thinking_trace": "This is a textbook SQL injection vulnerability. The evidence is definitive - SQL error messages confirm the injection works. OWASP Top 10 #1, affects all users, no auth required. Severity: Critical is absolutely correct. Action: Immediate remediation, disable endpoint if needed, implement parameterized queries.",
    "confidence": 0.99
}
```

### Example 2: False Positive Detection

```python
false_positive = {
    "id": "bug-002",
    "title": "404 error on user endpoint",
    "priority": "high",
    "description": "API returns 404 Not Found",
    "steps_to_reproduce": [
        "Call GET /api/users/invalid-user-id",
        "Observe 404 response"
    ],
    "expected_behavior": "Return user data",
    "actual_behavior": "Returns 404",
    "confidence_score": 0.75
}

result = await validate_bug_with_thinking(false_positive)

# Output:
{
    "is_valid": False,
    "validated_priority": "low",
    "business_impact": "None - this is expected REST API behavior",
    "recommended_action": "dismiss",
    "thinking_trace": "Analyzing the request: /api/users/invalid-user-id. The endpoint is being queried for a non-existent user. HTTP 404 (Not Found) is the *correct* response per RFC 7231. This is not a bug but proper error handling. The expected behavior should be 404, not user data, since the user doesn't exist. This is a false positive.",
    "confidence": 0.95
}
```

## Configuration

**Environment Variables**:
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
THINKING_BUDGET_TOKENS=5000        # Default thinking token budget
EXTENDED_THINKING_MIN_PRIORITY=high  # Minimum priority for extended thinking
```

**In Code**:
```python
from src.llm.anthropic import AnthropicClient

client = AnthropicClient(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_retries=3,
    timeout=120.0
)

response = await client.create_message_with_thinking(
    messages=[{"role": "user", "content": prompt}],
    thinking_budget=int(os.getenv("THINKING_BUDGET_TOKENS", 5000)),
    max_tokens=8000
)
```

## Monitoring & Metrics

Track extended thinking effectiveness:

```python
metrics = {
    "total_validations": 100,
    "extended_thinking_used": 25,  # Only for critical/high
    "false_positives_detected": 8,
    "priority_adjustments": 12,
    "average_cost_per_validation": 0.018,
    "average_thinking_tokens": 2100,
    "validation_accuracy": 0.96
}
```

## Future Enhancements

1. **Adaptive Thinking Budget**
   - Adjust budget based on bug complexity
   - Increase budget for ambiguous cases

2. **Thinking Trace Analysis**
   - ML model to identify reasoning patterns
   - Auto-improve prompts based on traces

3. **Multi-Agent Collaboration**
   - Multiple agents with extended thinking debate classifications
   - Consensus-based validation

4. **Human-in-the-Loop**
   - Review thinking traces for critical bugs
   - Override AI decisions with reasoning

## Troubleshooting

### Issue: No thinking trace returned

**Cause**: Model didn't use thinking capability

**Solution**: Check model version and parameters
```python
# Ensure using correct model
model="claude-opus-4-5-20250514"  # Not older versions

# Check thinking parameter is set
thinking={
    "type": "enabled",
    "budget_tokens": 5000
}
```

### Issue: JSON parsing errors

**Cause**: Model returned invalid JSON

**Solution**: Error handling catches this and returns conservative validation
```python
try:
    validation = json.loads(response["content"])
except JSONDecodeError:
    # Returns safe fallback validation
    validation = {
        "is_valid": False,
        "recommended_action": "defer",
        "confidence": 0.0
    }
```

### Issue: High costs

**Cause**: Using extended thinking for all bugs

**Solution**: Only use for critical/high priority
```python
if bug["priority"] not in ("critical", "high"):
    use_standard_validation()
else:
    use_extended_thinking()
```

## References

- [Claude Extended Thinking API Documentation](https://docs.anthropic.com/en/docs/extended-thinking)
- [BugHive Architecture](./ARCHITECTURE.md)
- [Agent Prompts](../src/agents/prompts/)
- [Test Suite](../tests/test_extended_thinking.py)
