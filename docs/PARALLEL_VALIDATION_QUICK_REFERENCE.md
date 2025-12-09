# Parallel Validation Quick Reference

## Quick Start

### Basic Usage

```python
from src.graph.parallel import parallel_validate_batch
from src.models.bug import Bug
from src.llm.router import LLMRouter

# Validate bugs in parallel
results = await parallel_validate_batch(
    bugs=[bug1, bug2, bug3],
    llm_router=router,
    session_id="session-id",
    batch_size=5,
    use_extended_thinking=False,
)
```

---

## API Reference

### `parallel_validate_batch()`

Validate multiple bugs in parallel with semaphore-controlled concurrency.

**Parameters:**
- `bugs: list[Bug]` - List of Bug objects to validate
- `llm_router: LLMRouter` - LLM router for API calls
- `session_id: str` - Session ID for cost tracking
- `batch_size: int = 5` - Max concurrent validations
- `use_extended_thinking: bool = False` - Use extended thinking for critical/high bugs

**Returns:**
```python
[
    {
        "bug_id": "abc-123",
        "is_valid": true,
        "validated_priority": "critical",
        "reasoning": "Explanation...",
        "recommended_action": "fix_immediately",
        "cost": 0.05
    },
    # ... more results
]
```

---

### `validate_single_bug()`

Validate a single bug (used internally by `parallel_validate_batch`).

**Parameters:**
- `bug: Bug` - Bug object to validate
- `llm_router: LLMRouter` - LLM router
- `session_id: str` - Session ID

**Returns:**
```python
{
    "is_valid": true,
    "validated_priority": "high",
    "reasoning": "...",
    "recommended_action": "investigate",
    "cost": 0.05
}
```

---

## Configuration

### Workflow Config

```python
config = {
    "validation_batch_size": 5,        # Max concurrent validations
    "use_extended_thinking": True,     # Extended thinking for critical/high
}
```

### Recommended Settings

| Use Case | batch_size | use_extended_thinking |
|----------|------------|-----------------------|
| Fast & Cheap | 10 | False |
| Balanced | 5 | False |
| High Quality | 3 | True |

---

## Return Values

### Success Result
```python
{
    "bug_id": "123",
    "is_valid": True,
    "validated_priority": "critical",
    "reasoning": "Blocks user login",
    "recommended_action": "fix_immediately",
    "cost": 0.05
}
```

### Invalid Bug Result
```python
{
    "bug_id": "123",
    "is_valid": False,
    "reasoning": "Not reproducible",
    "recommended_action": "dismiss",
    "cost": 0.05
}
```

### Error Result
```python
{
    "bug_id": "123",
    "is_valid": False,
    "error": "API timeout",
    "recommended_action": "retry",
    "cost": 0.0
}
```

---

## Recommended Actions

| Action | Meaning |
|--------|---------|
| `fix_immediately` | Critical bug blocking users |
| `investigate` | Needs further investigation |
| `defer` | Low priority, backlog |
| `dismiss` | False positive or won't fix |
| `retry` | Validation failed, retry later |

---

## Error Handling

### JSON Parse Errors
Automatically falls back to default valid response:
```python
{
    "is_valid": True,
    "reasoning": "<raw response>",
    "validated_priority": "<original priority>",
    "recommended_action": "investigate"
}
```

### API Exceptions
Returns error result:
```python
{
    "is_valid": False,
    "error": "<exception message>",
    "recommended_action": "retry",
    "cost": 0.0
}
```

---

## Performance

### Sequential (Before)
```
10 bugs × 2s each = 20 seconds
```

### Parallel (After)
```
10 bugs ÷ 5 batch_size × 2s = 4 seconds
Speedup: 5x
```

---

## Cost Tracking

```python
# Individual costs
result["cost"]  # 0.05 for standard, 0.15 for extended thinking

# Batch total
total_cost = sum(r["cost"] for r in results)

# Session total (in state)
state["total_cost"] += total_cost
```

---

## Extended Thinking

When `use_extended_thinking=True`:

| Priority | Validation Method |
|----------|-------------------|
| Critical | Extended Thinking (Opus 4.5) |
| High | Extended Thinking (Opus 4.5) |
| Medium | Standard (Opus via router) |
| Low | Standard (Opus via router) |

---

## Testing

```bash
# Run tests
pytest tests/test_parallel_validation.py -v

# Check syntax
python3 -m py_compile src/graph/parallel.py
```

---

## Logging

```python
logger.info(f"Starting parallel validation of {len(bugs)} bugs with batch_size={batch_size}")
logger.info(f"Using extended thinking for {bug.priority} priority bug {bug.id}")
logger.info(f"Bug {bug_id} validated: {validation['recommended_action']}")
logger.info(f"Parallel validation complete: {valid_count}/{len(bugs)} valid, total cost: ${total_cost:.4f}")
```

---

## Common Patterns

### Validate All Bugs
```python
results = await parallel_validate_batch(bugs, router, session_id)
```

### Validate Only Critical/High
```python
high_priority = [b for b in bugs if b.priority in ["critical", "high"]]
results = await parallel_validate_batch(high_priority, router, session_id)
```

### Filter Valid Bugs
```python
results = await parallel_validate_batch(bugs, router, session_id)
valid_bugs = [bugs[i] for i, r in enumerate(results) if r["is_valid"]]
```

### Calculate Total Cost
```python
results = await parallel_validate_batch(bugs, router, session_id)
total_cost = sum(r.get("cost", 0.0) for r in results)
```

---

## Troubleshooting

### Issue: Semaphore not limiting concurrency
**Solution:** Check that `batch_size` is being passed correctly

### Issue: Extended thinking not activating
**Solution:** Verify `use_extended_thinking=True` and bug priority is "critical" or "high"

### Issue: All validations failing
**Solution:** Check LLM router configuration and API credentials

### Issue: High costs
**Solution:** Reduce `batch_size` or disable `use_extended_thinking`

---

## Files Modified

| File | Purpose |
|------|---------|
| `src/agents/prompts/classifier.py` | Added `VALIDATE_BUG_PROMPT` |
| `src/graph/parallel.py` | Added parallel validation functions |
| `src/graph/nodes.py` | Refactored `validate_bugs()` node |
| `tests/test_parallel_validation.py` | Comprehensive test suite |

---

## See Also

- [Full Implementation Guide](PARALLEL_VALIDATION_IMPLEMENTATION.md)
- [Extended Thinking Integration](EXTENDED_THINKING_IMPLEMENTATION.md)
- [Workflow Architecture](WORKFLOW.md)
