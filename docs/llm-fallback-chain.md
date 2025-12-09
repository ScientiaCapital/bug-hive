# Multi-Level Fallback Chain for LLM Router

## Overview

The BugHive LLM Router now supports multi-level fallback chains that automatically retry failed requests across progressively cheaper/faster model tiers. This ensures maximum reliability while optimizing costs.

## Architecture

### Fallback Chain Configuration

Each model tier has a predefined fallback chain:

```python
FALLBACK_CHAIN = {
    ModelTier.ORCHESTRATOR: [ModelTier.REASONING, ModelTier.GENERAL],
    ModelTier.REASONING: [ModelTier.GENERAL, ModelTier.FAST],
    ModelTier.CODING: [ModelTier.REASONING, ModelTier.GENERAL],
    ModelTier.GENERAL: [ModelTier.FAST],
    ModelTier.FAST: [],  # No fallback for fastest tier
}
```

**Example Flow:**
- ORCHESTRATOR fails → try REASONING → try GENERAL
- REASONING fails → try GENERAL → try FAST
- CODING fails → try REASONING → try GENERAL
- GENERAL fails → try FAST
- FAST fails → raise AllModelsFailedError

### Retry Logic

Each tier in the chain gets multiple retry attempts before falling back to the next tier:

- **Default:** 2 retries per tier
- **Configurable:** via `max_retries_per_tier` parameter
- **Total Attempts:** `len(chain) × max_retries_per_tier`

## Usage

### Basic Usage

```python
from src.llm import LLMRouter

router = LLMRouter(
    anthropic_client=anthropic,
    openrouter_client=openrouter,
    cost_tracker=tracker,
)

# Use the new fallback chain method
response = await router.route_with_fallback_chain(
    task="analyze_page",
    messages=[{"role": "user", "content": "Analyze this page..."}],
    max_retries_per_tier=2,  # 2 retries per tier
)

# Check which tier was used
if response["fallback_tier"]:
    print(f"Fell back to: {response['fallback_tier']}")
    print(f"Chain attempted: {response['fallback_chain_used']}")
else:
    print("Primary model succeeded")
```

### Response Metadata

Successful responses include additional metadata:

```python
{
    "content": "Analysis complete...",
    "usage": {"input_tokens": 100, "output_tokens": 200},
    "model": "deepseek/deepseek-chat",
    "model_tier": "REASONING",

    # Fallback metadata
    "fallback_tier": "GENERAL",  # None if primary succeeded
    "attempt": 1,  # Which attempt succeeded (1-indexed)
    "fallback_chain_used": ["REASONING", "GENERAL"],  # Tiers attempted
    "original_task": "analyze_page",
}
```

### Error Handling

When all models in the chain fail:

```python
from src.llm import AllModelsFailedError

try:
    response = await router.route_with_fallback_chain(
        task="analyze_page",
        messages=messages,
    )
except AllModelsFailedError as e:
    # Access detailed error information
    print(f"All models failed: {e}")

    for error in e.errors:
        print(f"  - {error['tier']} attempt {error['attempt']}: {error['error']}")

    # Example output:
    # All models failed: All models in chain failed for task 'analyze_page'
    #   - REASONING attempt 1: Connection timeout
    #   - REASONING attempt 2: Connection timeout
    #   - GENERAL attempt 1: Rate limit exceeded
    #   - GENERAL attempt 2: Rate limit exceeded
    #   - FAST attempt 1: Service unavailable
    #   - FAST attempt 2: Service unavailable
```

### Backward Compatibility

The existing `route_with_fallback()` method now uses the fallback chain internally:

```python
# New behavior: uses full fallback chain
response = await router.route_with_fallback(
    task="analyze_page",
    messages=messages,
)

# Old behavior still supported: explicit single fallback
response = await router.route_with_fallback(
    task="analyze_page",
    messages=messages,
    fallback_tier=ModelTier.FAST,  # Explicit single-level fallback
)
```

## Configuration

### Custom Retry Counts

```python
# More aggressive retries
response = await router.route_with_fallback_chain(
    task="analyze_page",
    messages=messages,
    max_retries_per_tier=5,  # 5 retries per tier
)

# Minimal retries (fail fast)
response = await router.route_with_fallback_chain(
    task="analyze_page",
    messages=messages,
    max_retries_per_tier=1,  # Single attempt per tier
)
```

### Task-Specific Behavior

Different tasks automatically use different fallback chains:

```python
# High-stakes task: ORCHESTRATOR → REASONING → GENERAL
await router.route_with_fallback_chain(
    task="validate_critical_bug",  # Uses ORCHESTRATOR tier
    messages=messages,
)

# Coding task: CODING → REASONING → GENERAL
await router.route_with_fallback_chain(
    task="generate_edge_cases",  # Uses CODING tier
    messages=messages,
)

# Fast task: FAST only (no fallback)
await router.route_with_fallback_chain(
    task="format_ticket",  # Uses FAST tier
    messages=messages,
)
```

## Performance Considerations

### Latency

- **Primary Success:** No additional latency
- **Fallback:** 0.5s delay between retries to avoid hammering failed services
- **Total Max Time:** `(len(chain) × max_retries_per_tier × avg_request_time) + delays`

### Cost Optimization

The fallback chain is designed to minimize costs:

1. **Start with task-appropriate tier:** Not always the most expensive
2. **Fall back to cheaper models:** ORCHESTRATOR → REASONING → GENERAL → FAST
3. **Track actual costs:** All attempts are tracked in cost_tracker

```python
# Check total costs including failed attempts
summary = tracker.get_cost_summary(session_id="session_123")
print(f"Total cost: ${summary['total_cost']:.4f}")
print(f"Failed attempts: {summary['failed_attempts']}")
```

### Reliability Metrics

```python
# Track fallback usage
if response["fallback_tier"]:
    metric_tracker.increment("llm_fallback", {
        "task": response["original_task"],
        "primary_tier": "REASONING",
        "fallback_tier": response["fallback_tier"],
        "attempts": len(response["fallback_chain_used"]),
    })
```

## Best Practices

### When to Use Fallback Chain

✅ **USE for:**
- Production workloads requiring high reliability
- Non-critical tasks where cheaper fallbacks are acceptable
- API calls that may experience intermittent failures
- Situations where response quality can degrade gracefully

❌ **DON'T USE for:**
- Tasks requiring specific model capabilities
- When fallback to cheaper model would produce incorrect results
- Time-critical operations (use single retry instead)

### Example: Production Session Analysis

```python
async def analyze_session_robust(session_data: dict) -> dict:
    """Analyze session with automatic fallback to ensure success."""
    router = get_llm_router()

    try:
        response = await router.route_with_fallback_chain(
            task="analyze_page",
            messages=[
                {"role": "user", "content": f"Analyze: {session_data}"}
            ],
            max_retries_per_tier=3,
            session_id=session_data["session_id"],
        )

        # Log fallback usage for monitoring
        if response["fallback_tier"]:
            logger.warning(
                f"Session analysis fell back to {response['fallback_tier']}",
                extra={
                    "session_id": session_data["session_id"],
                    "chain": response["fallback_chain_used"],
                    "attempts": response["attempt"],
                }
            )

        return response

    except AllModelsFailedError as e:
        # All models failed - escalate to manual review
        logger.error(
            f"Critical: All models failed for session {session_data['session_id']}",
            extra={"errors": e.errors}
        )
        await notify_on_call_engineer(e)
        raise
```

## Testing

Comprehensive test coverage is available in `/Users/tmkipper/Desktop/tk_projects/bug-hive/tests/test_fallback_chain.py`:

```bash
# Run fallback chain tests
pytest tests/test_fallback_chain.py -v

# All 14 tests cover:
# - Primary model success (no fallback)
# - Fallback to second tier
# - Fallback to third tier
# - All models fail (error handling)
# - Retry logic per tier
# - Response metadata validation
# - Different chains for different tasks
# - Backward compatibility
# - Cost tracking integration
# - Custom retry parameters
```

## Monitoring & Observability

### Recommended Metrics

```python
# Track fallback rates by task
metrics.gauge("llm_fallback_rate", {
    "task": task_name,
    "tier": response["fallback_tier"] or "primary",
})

# Track attempts before success
metrics.histogram("llm_attempts", response["attempt"], {
    "task": task_name,
})

# Track which tiers are failing
for error in failed_errors:
    metrics.increment("llm_tier_failure", {
        "tier": error["tier"],
        "error_type": type(error["error"]).__name__,
    })
```

### Alerting Thresholds

```yaml
alerts:
  - name: HighFallbackRate
    condition: fallback_rate > 0.3  # >30% of requests falling back
    severity: warning

  - name: AllModelFailures
    condition: all_models_failed_count > 5  # per hour
    severity: critical

  - name: PrimaryTierUnhealthy
    condition: primary_success_rate < 0.7  # <70% success
    severity: warning
```

## Migration Guide

### From Single Fallback

```python
# OLD: Single fallback
try:
    response = await router.route(task, messages)
except Exception:
    response = await router._route_with_model(ModelTier.GENERAL, messages)

# NEW: Automatic multi-level fallback
response = await router.route_with_fallback_chain(task, messages)
```

### From Manual Retry Logic

```python
# OLD: Manual retry with backoff
for attempt in range(3):
    try:
        response = await router.route(task, messages)
        break
    except Exception as e:
        if attempt == 2:
            raise
        await asyncio.sleep(2 ** attempt)

# NEW: Built-in retry with fallback
response = await router.route_with_fallback_chain(
    task=task,
    messages=messages,
    max_retries_per_tier=3,
)
```

## Future Enhancements

Potential improvements under consideration:

1. **Dynamic Chain Configuration:** Adjust fallback chains based on observed failure patterns
2. **Cost-Aware Fallback:** Skip expensive fallbacks based on session budget
3. **Parallel Attempts:** Try multiple tiers simultaneously for critical tasks
4. **Circuit Breaker:** Temporarily skip tiers with high failure rates
5. **Custom Chains:** Per-task or per-session fallback chain overrides

## Related Documentation

- [LLM Router Documentation](/Users/tmkipper/Desktop/tk_projects/bug-hive/src/llm/router.py)
- [Model Tier Configuration](/Users/tmkipper/Desktop/tk_projects/bug-hive/src/llm/router.py#L11-L17)
- [Cost Tracking](/Users/tmkipper/Desktop/tk_projects/bug-hive/src/llm/cost_tracker.py)
- [Token Budget Management](/Users/tmkipper/Desktop/tk_projects/bug-hive/src/llm/token_budget.py)
