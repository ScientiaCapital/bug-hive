# Error Pattern Detection for BugHive

## Overview

BugHive now includes a sophisticated error aggregation and pattern detection system that automatically identifies systemic issues during web application crawling and analysis.

## Architecture

### ErrorAggregator Class

The `ErrorAggregator` class (`src/utils/error_aggregator.py`) is the core component that:

- **Collects errors** from all workflow nodes
- **Groups similar errors** by type and message prefix
- **Detects patterns** when errors repeat 2+ times
- **Tracks context** (URLs, nodes, timestamps) for each error
- **Thread-safe** for parallel crawling operations

### Key Features

#### 1. Error Collection
```python
error_agg.add(
    ValueError("Invalid selector"),
    context={"node": "analyze_page", "url": "http://example.com"}
)
```

#### 2. Pattern Detection
Errors are grouped by:
- **Error type** (e.g., `ValueError`, `TimeoutError`)
- **Message prefix** (first 100 characters)

Example: Three `TimeoutError("Connection timeout")` errors from different pages are grouped as one pattern with count=3.

#### 3. Context Tracking
Each error captures:
- Exception type and message
- Session ID
- Node name
- URL (if available)
- Timestamp
- Custom context fields

#### 4. Summary Generation
```python
summary = error_agg.get_summary()
# Returns:
# {
#     "total_errors": 15,
#     "unique_types": 3,
#     "pattern_count": 2,
#     "top_patterns": [...]
# }
```

## Integration with BugHive Workflow

### 1. Import and Initialization

In `src/graph/nodes.py`:
```python
from src.utils.error_aggregator import get_error_aggregator
```

### 2. Error Tracking in Exception Handlers

Every node exception handler now tracks errors:
```python
try:
    # Node logic
except Exception as e:
    logger.error(f"Error in node: {e}", exc_info=True)

    # Track error in aggregator
    error_agg = get_error_aggregator(state["session_id"])
    error_agg.add(e, context={"node": "crawl_page", "url": next_page["url"]})

    # Continue with existing error handling
```

### 3. Integrated Nodes

Error tracking is integrated in all major workflow nodes:
- `plan_crawl` - Planning strategy
- `crawl_page` - Page navigation and extraction
- `analyze_page` - Issue analysis
- `classify_bugs` - Bug classification
- `validate_bugs` - Bug validation
- `generate_reports` - Report generation
- `create_linear_tickets` - Ticket creation
- `generate_summary` - Final summary
- `report_error_patterns` - ERROR PATTERN REPORTING (NEW)

### 4. Error Pattern Reporting Node

A new `report_error_patterns()` node analyzes all collected errors:

```python
async def report_error_patterns(state: BugHiveState) -> dict[str, Any]:
    """Reports aggregated error patterns from the session."""
    error_agg = get_error_aggregator(state["session_id"])
    error_summary = error_agg.get_summary()
    error_patterns = error_agg.get_patterns(min_occurrences=2)

    # Add to final summary
    summary["error_analysis"] = {
        "total_errors": error_summary["total_errors"],
        "unique_error_types": error_summary["unique_types"],
        "pattern_count": error_summary["pattern_count"],
        "detected_patterns": error_patterns,
    }
```

This node should be added to the workflow after `generate_summary`.

## Usage Examples

### Basic Error Tracking
```python
from src.utils import get_error_aggregator

# Create aggregator for a session
agg = get_error_aggregator("my-session-123")

# Add errors
agg.add(ConnectionError("timeout"), context={"url": "http://example.com"})
agg.add(ConnectionError("timeout"), context={"url": "http://example.com/page2"})

# Get patterns (only 2+ occurrences)
patterns = agg.get_patterns(min_occurrences=2)
# [{
#     "error_type": "ConnectionError",
#     "count": 2,
#     "message_prefix": "timeout",
#     "urls": ["http://example.com", "http://example.com/page2"],
#     ...
# }]
```

### Filtering Errors by Type
```python
agg = get_error_aggregator("session-123")

# Get all TimeoutErrors
timeout_errors = agg.get_errors_by_type("TimeoutError")

# Get all errors of any type
all_errors = agg.get_all_errors()
```

### Summary Statistics
```python
summary = agg.get_summary()
print(f"Total errors: {summary['total_errors']}")
print(f"Unique error types: {summary['unique_types']}")
print(f"Patterns detected: {summary['pattern_count']}")
```

## Thread Safety

The `ErrorAggregator` is fully thread-safe for parallel crawling:
- Uses `threading.RLock()` for all operations
- Safe for concurrent error additions from multiple threads
- Safe for pattern detection while errors are being added

```python
# Safe to call from multiple threads
agg.add(error, context={...})
patterns = agg.get_patterns()
```

## Pattern Detection Logic

### Grouping Algorithm

Errors are grouped by a tuple key: `(error_type, message_prefix)`

1. **Error Type**: The exception class name (e.g., `ValueError`)
2. **Message Prefix**: First 100 characters of the error message

Example:
- `ValueError("Invalid selector for [data-test-id='btn']")` and
- `ValueError("Invalid selector for [data-test-id='form']")`

Both share the same prefix "Invalid selector for" and are grouped together.

### Pattern Detection Threshold

Patterns are detected when:
- Same error type + message prefix combination
- Occurs >= `min_occurrences` times (default: 2)

Only patterns meeting this threshold are returned, filtering out isolated errors.

### Context Limiting

To keep memory usage reasonable:
- Only first 5 contexts are kept per pattern
- URLs are deduplicated (stored as set)
- Timestamp ranges are tracked (first_seen, last_seen)

## Output Format

### Error Pattern Structure
```python
{
    "error_type": "TimeoutError",
    "message_prefix": "Connection timeout after 30s",
    "count": 5,
    "first_seen": datetime(2025, 12, 9, 17:00:00),
    "last_seen": datetime(2025, 12, 9, 17:15:00),
    "urls": [
        "http://example.com/page1",
        "http://example.com/page2",
        "http://example.com/page3"
    ],
    "contexts": [
        {"node": "crawl_page", "url": "http://example.com/page1"},
        {"node": "crawl_page", "url": "http://example.com/page2"},
        ...
    ]
}
```

## Logging

Error patterns are logged at WARN level:
```
Detected 2 error patterns during session:
  1. TimeoutError: 5 occurrences - Connection timeout after 30s
  2. ValueError: 3 occurrences - Invalid selector for [data-test-id='btn']
```

Isolated errors (not patterns) are logged at DEBUG level only.

## Testing

Comprehensive test suite in `tests/test_error_aggregator.py`:

```bash
# Run tests (requires pytest and dev dependencies)
python3 -m pytest tests/test_error_aggregator.py -v
```

Test coverage includes:
- Single error addition
- Pattern detection with minimum occurrences
- Message prefix grouping
- URL extraction from context
- Context limiting
- Timestamp recording
- Thread-safe concurrent operations
- Error filtering by type
- Summary generation
- Session isolation

## Performance Considerations

### Memory Usage
- Errors stored in list: O(n) where n = total errors
- Patterns cached after first call
- Context limited to 5 per pattern
- URLs deduplicated

### CPU Usage
- Pattern detection: O(n) on first call, cached thereafter
- Threading operations: Minimal overhead from RLock
- No network calls or external dependencies

### Scalability
- Tested with 200+ concurrent errors from multiple threads
- Suitable for large crawl sessions (100+ pages)
- Cache invalidated only on new errors

## Integration Checklist

To fully integrate error pattern detection:

- [x] Create ErrorAggregator class
- [x] Add to all exception handlers in nodes.py
- [x] Create report_error_patterns() node
- [x] Add error_analysis to final summary
- [ ] Wire report_error_patterns into workflow graph
- [ ] Update workflow to call report_error_patterns after generate_summary

## Future Enhancements

Potential improvements for future versions:

1. **Error Clustering**: Use similarity metrics to group related errors
2. **Root Cause Analysis**: Correlate errors with specific crawl conditions
3. **Alerts**: Send notifications when critical patterns are detected
4. **Metrics**: Track error patterns over multiple sessions
5. **Suggestions**: Auto-generate remediation suggestions for common patterns
6. **Webhooks**: POST pattern summaries to external services
7. **Error Causality**: Track error chains (e.g., auth error causes parse error)

## References

- **Module**: `/Users/tmkipper/Desktop/tk_projects/bug-hive/src/utils/error_aggregator.py`
- **Tests**: `/Users/tmkipper/Desktop/tk_projects/bug-hive/tests/test_error_aggregator.py`
- **Integration**: `/Users/tmkipper/Desktop/tk_projects/bug-hive/src/graph/nodes.py`
- **Exports**: `/Users/tmkipper/Desktop/tk_projects/bug-hive/src/utils/__init__.py`
