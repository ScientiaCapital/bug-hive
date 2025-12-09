# Linear Integration Layer

Professional bug reporting to Linear with mock and real implementations.

## Quick Start

### Development (No API Key)

```python
from src.integrations import get_linear_client

# Automatically uses MockLinearClient
client = get_linear_client()

issue = await client.create_issue(
    title="Button not working",
    description="Submit button does not respond",
    team_id="qa-team",
    priority=2  # High
)

print(f"Created: {issue.identifier}")  # BUG-1
print(f"URL: {issue.url}")
```

### Production (With API Key)

```python
import os
from src.integrations import get_linear_client

# Set environment variable
os.environ["LINEAR_API_KEY"] = "lin_api_xxxxx"

# Automatically uses RealLinearClient
client = get_linear_client()

issue = await client.create_issue(
    title="Bug title",
    description="Bug description",
    team_id="actual-team-uuid",
    priority=2
)
```

### With Report Writer Agent

```python
from src.integrations import get_reporter_agent
from src.llm import LLMRouter
from src.models.bug import Bug

# Initialize
router = LLMRouter(...)
reporter = get_reporter_agent(router)

# Create formatted ticket from bug
issue = await reporter.create_ticket(
    bug=bug,
    team_id="qa-team"
)

print(f"Created: {issue.url}")
```

## Files

| File | Purpose |
|------|---------|
| `linear.py` | Abstract interface (LinearClient, LinearIssue) |
| `linear_mock.py` | Mock implementation for development |
| `linear_real.py` | Real GraphQL API client (skeleton) |
| `reporter.py` | Report Writer Agent (LLM-powered formatting) |
| `__init__.py` | Factory functions and exports |

## Testing

```bash
# Test mock client (no dependencies)
python3 examples/test_linear_mock_only.py

# Test full integration (requires LLM)
PYTHONPATH=/path/to/bug-hive python3 examples/test_linear_integration.py
```

## Priority Mapping

| Bug | Linear |
|-----|--------|
| critical | 1 (Urgent) |
| high | 2 (High) |
| medium | 3 (Medium) |
| low | 4 (Low) |

## Documentation

See [docs/linear-integration.md](../../docs/linear-integration.md) for complete documentation.

## Status

- ✅ MockLinearClient: Complete and tested
- ✅ LinearClient interface: Complete
- ✅ ReportWriterAgent: Complete with LLM integration
- 🚧 RealLinearClient: Skeleton (ready for implementation)

## Dependencies

### Core (no external deps):
- `linear.py` - Pydantic only
- `linear_mock.py` - Python stdlib + Pydantic

### Real Client:
- `linear_real.py` - httpx

### Report Writer:
- `reporter.py` - src.llm (LLMRouter), src.models.bug

## Architecture

```
┌─────────────────────────────────────────────┐
│           Factory Functions                 │
│  get_linear_client() / get_reporter_agent() │
└────────────────┬────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼────────┐  ┌────▼──────────┐
│ MockLinearClient│  │RealLinearClient│
│  (Development)  │  │  (Production) │
└────────┬────────┘  └────┬──────────┘
         │                │
         └────────┬───────┘
                  │
         ┌────────▼────────┐
         │  LinearClient   │
         │   (Interface)   │
         └─────────────────┘

┌─────────────────────────────────────────────┐
│         ReportWriterAgent                   │
│  (Formats bugs → Linear tickets with LLM)   │
└─────────────────────────────────────────────┘
```

## Next Steps

1. ✅ Test MockLinearClient
2. ✅ Create documentation
3. 🔲 Connect RealLinearClient to Linear workspace
4. 🔲 Test ReportWriterAgent with real bugs
5. 🔲 Integration with main crawler workflow
