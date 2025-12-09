# Message Compaction Usage Guide

## Overview

BugHive's `MessageCompactor` automatically summarizes older messages in long-running agent sessions to stay within token limits. This ensures continuous operation without context overflow.

## How It Works

1. **Monitors Token Usage**: Tracks estimated token count of message history
2. **Triggers at Threshold**: Compacts when reaching configurable % of context limit (default 70%)
3. **Preserves Recent Context**: Keeps N recent messages intact (default 10)
4. **Summarizes Old Messages**: Uses FAST tier (Qwen-32B) to create concise summary
5. **Returns Compacted History**: `[summary_message, ...recent_messages]`

## Basic Usage

```python
from src.llm import LLMRouter, MessageCompactor

# Initialize router
router = LLMRouter(
    anthropic_client=anthropic,
    openrouter_client=openrouter,
    cost_tracker=tracker,
)

# Create compactor
compactor = MessageCompactor(
    llm_router=router,
    threshold_ratio=0.7,  # Compact at 70% of context limit
    keep_recent=10,       # Keep last 10 messages
)

# In your agent loop
messages = []
for page in pages:
    # Add new messages
    messages.append({"role": "user", "content": f"Analyze {page}"})

    # Compact if needed (before making request)
    messages = await compactor.compact_if_needed(
        messages=messages,
        model_tier="GENERAL",  # Target tier for token limit lookup
    )

    # Make LLM request with compacted messages
    response = await router.route(
        task="analyze_page",
        messages=messages,
        session_id=session_id,
    )

    messages.append({"role": "assistant", "content": response["content"]})
```

## Configuration Options

### Threshold Ratio

Controls when compaction triggers as % of context limit:

```python
# Conservative (compact early)
compactor = MessageCompactor(router, threshold_ratio=0.5)  # 50%

# Balanced (default)
compactor = MessageCompactor(router, threshold_ratio=0.7)  # 70%

# Aggressive (compact late)
compactor = MessageCompactor(router, threshold_ratio=0.9)  # 90%
```

### Keep Recent

Number of recent messages to preserve uncompacted:

```python
# Minimal context (faster, cheaper summaries)
compactor = MessageCompactor(router, keep_recent=5)

# Balanced (default)
compactor = MessageCompactor(router, keep_recent=10)

# Maximum context (better continuity)
compactor = MessageCompactor(router, keep_recent=20)
```

## Integration with BugHive State

The `BugHiveState` now tracks compaction metrics:

```python
from src.graph.state import BugHiveState, create_initial_state

state = create_initial_state(config)

# Check if compaction needed
state["needs_compaction"] = True  # Set by workflow

# Track compaction events
state["last_compaction_at"] = time.time()
state["compaction_count"] += 1

# Access compaction history in summary
print(f"Compacted {state['compaction_count']} times")
```

## Example: Long Crawl Session

```python
async def crawl_with_compaction(config):
    """Example crawl with automatic message compaction."""
    state = create_initial_state(config)

    # Initialize compactor
    compactor = MessageCompactor(
        llm_router=state["llm_router"],
        threshold_ratio=0.7,
        keep_recent=10,
    )

    messages = state["messages"]

    for page in state["pages_discovered"]:
        # Check token budget before analysis
        messages = await compactor.compact_if_needed(
            messages=messages,
            model_tier="REASONING",  # Using DeepSeek-V3 for analysis
        )

        # Track if compaction occurred
        if len(messages) < len(state["messages"]):
            state["compaction_count"] += 1
            state["last_compaction_at"] = time.time()
            logger.info(f"Compacted messages to {len(messages)}")

        # Analyze page
        response = await router.route(
            task="analyze_page",
            messages=messages + [
                {"role": "user", "content": f"Analyze {page['url']}"}
            ],
            session_id=state["session_id"],
        )

        # Update state
        state["messages"] = messages + [
            {"role": "user", "content": f"Analyze {page['url']}"},
            {"role": "assistant", "content": response["content"]},
        ]

    return state
```

## Token Budget Reference

| Model Tier     | Context Limit | 70% Threshold | 90% Threshold |
|----------------|---------------|---------------|---------------|
| ORCHESTRATOR   | 200k tokens   | 140k tokens   | 180k tokens   |
| CODING         | 128k tokens   | 89.6k tokens  | 115.2k tokens |
| REASONING      | 64k tokens    | 44.8k tokens  | 57.6k tokens  |
| GENERAL        | 32k tokens    | 22.4k tokens  | 28.8k tokens  |
| FAST           | 32k tokens    | 22.4k tokens  | 28.8k tokens  |

## Best Practices

1. **Compact Before Requests**: Always check `compact_if_needed()` before making LLM calls
2. **Match Model Tier**: Pass same `model_tier` to compactor as router will use
3. **Log Compactions**: Track when compaction occurs for debugging
4. **Adjust Thresholds**: Lower threshold for long sessions, higher for short bursts
5. **Monitor Summary Quality**: Review summaries to ensure key info preserved

## Summary Quality

The compactor uses `summarize_session` task (FAST tier) with:
- **Max Tokens**: 1024 (concise summaries)
- **Temperature**: 0.3 (deterministic, factual)
- **Focus**: URLs visited, bugs found, decisions made
- **Omits**: Redundant details, verbose reasoning

## Cost Impact

Compaction adds minimal cost:
- **Qwen-32B**: $0.30/M input, $0.60/M output (FAST tier)
- **Typical Summary**: ~500 input + ~200 output tokens = ~$0.00027 per compaction
- **Savings**: Prevents hitting expensive rate limits or context errors

## Troubleshooting

### Compaction Happens Too Early

```python
# Increase threshold
compactor = MessageCompactor(router, threshold_ratio=0.85)
```

### Lost Important Context

```python
# Increase keep_recent
compactor = MessageCompactor(router, keep_recent=15)
```

### Summaries Too Long

The compactor uses fixed `max_tokens=1024`. This is intentional to prevent summary bloat. If you need longer summaries, modify the compactor source.

### No Compaction Happening

Check:
1. Message count > `keep_recent`
2. Token estimate > threshold
3. Correct `model_tier` passed

```python
from src.llm.token_budget import TokenBudget

budget = TokenBudget()
tokens = budget.estimate_tokens(messages, model_tier="FAST")
print(f"Estimated tokens: {tokens} (threshold: {32000 * 0.7})")
```

## Future Enhancements

Potential improvements:
- **Hierarchical Summaries**: Summarize summaries for extremely long sessions
- **Selective Compaction**: Keep critical messages (e.g., bug reports) uncompacted
- **Custom Summarization Prompts**: Per-task summary templates
- **Compression Metrics**: Track compression ratio, summary quality scores
