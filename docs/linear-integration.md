# Linear Integration Documentation

## Overview

The Linear integration layer provides seamless bug reporting to Linear issue tracking with both mock (for development) and real (for production) implementations.

## Architecture

```
src/integrations/
├── linear.py           # Abstract LinearClient interface
├── linear_mock.py      # Mock implementation (no API key needed)
├── linear_real.py      # Real GraphQL API client (skeleton)
├── reporter.py         # ReportWriterAgent (formats bugs with LLM)
└── __init__.py         # Factory functions
```

## Components

### 1. LinearClient (Abstract Interface)

Defines the contract for all Linear API operations:

```python
from src.integrations import LinearClient, LinearIssue

class LinearClient(ABC):
    async def create_issue(...) -> LinearIssue
    async def update_issue(...) -> LinearIssue
    async def get_issue(...) -> LinearIssue | None
    async def get_team_id(...) -> str | None
```

### 2. MockLinearClient

In-memory mock for development and testing. No API key required.

**Features:**
- In-memory issue storage
- Auto-incrementing identifiers (BUG-1, BUG-2, etc.)
- Simulates all Linear API operations
- Comprehensive logging

**Usage:**
```python
from src.integrations import MockLinearClient

client = MockLinearClient()

# Create issue
issue = await client.create_issue(
    title="Button not working",
    description="Submit button does not respond",
    team_id="qa-team",
    priority=2,  # High
    labels=["bug", "frontend"]
)

print(f"Created: {issue.identifier}")  # BUG-1
print(f"URL: {issue.url}")  # https://linear.app/mock/issue/BUG-1
```

### 3. RealLinearClient

GraphQL API client for production (currently skeleton).

**Usage:**
```python
from src.integrations import RealLinearClient

client = RealLinearClient(api_key="lin_api_xxxxx")

issue = await client.create_issue(
    title="Bug title",
    description="Bug description",
    team_id="actual-team-uuid",
    priority=2
)
```

**Status:** Skeleton implementation. GraphQL mutations and queries are defined but need testing with actual Linear workspace.

### 4. ReportWriterAgent

Formats Bug objects into professional Linear tickets using LLM.

**Features:**
- Uses Qwen 32B (ModelTier.FAST) for formatting
- Generates markdown reports with proper structure
- Maps bug priorities to Linear priorities
- Handles evidence formatting (screenshots, logs, etc.)

**Usage:**
```python
from src.integrations import get_reporter_agent
from src.llm import LLMRouter

# Initialize
router = LLMRouter(...)
reporter = get_reporter_agent(router)

# Create ticket from bug
issue = await reporter.create_ticket(
    bug=bug,
    team_id="qa-team"
)

print(f"Created: {issue.url}")
```

## Factory Functions

### get_linear_client()

Automatically selects between mock and real clients:

```python
from src.integrations import get_linear_client

# Development (no API key) → MockLinearClient
client = get_linear_client()

# Production (with API key) → RealLinearClient
client = get_linear_client(api_key="lin_api_xxxxx")

# From environment variable
import os
os.environ["LINEAR_API_KEY"] = "lin_api_xxxxx"
client = get_linear_client()  # Uses environment variable
```

### get_reporter_agent()

Creates ReportWriterAgent with appropriate Linear client:

```python
from src.integrations import get_reporter_agent
from src.llm import LLMRouter

router = LLMRouter(...)

# With mock client
reporter = get_reporter_agent(router)

# With real client
reporter = get_reporter_agent(router, api_key="lin_api_xxxxx")
```

## Data Models

### LinearIssue

```python
class LinearIssue(BaseModel):
    id: str              # UUID
    identifier: str      # BUG-123
    title: str           # Issue title
    url: str             # Direct URL
    priority: int        # 0-4 (0=None, 1=Urgent, 2=High, 3=Medium, 4=Low)
```

## Priority Mapping

Bug priorities are mapped to Linear priorities:

| Bug Priority | Linear Priority | Linear Name |
|--------------|----------------|-------------|
| critical     | 1              | Urgent      |
| high         | 2              | High        |
| medium       | 3              | Medium      |
| low          | 4              | Low         |

## Evidence Handling

The ReportWriterAgent formats different evidence types:

| Evidence Type      | Formatted As          |
|--------------------|-----------------------|
| screenshot         | Link to image URL     |
| console_log        | Code block            |
| network_request    | HTTP details          |
| dom_snapshot       | HTML code block       |
| performance_metrics| Performance data      |

## Report Format

Generated Linear tickets follow this structure:

```markdown
## Summary
[One-line description]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Expected vs actual result]

## Evidence
- Screenshot: [URL]
- Console Log:
```
[error details]
```

## Environment
- Bug ID: [UUID]
- Browser: Chrome (via Browserbase)
- Timestamp: [ISO timestamp]

## Suggested Priority
**[priority]** - [Justification]
```

## Testing

### Mock Client Test

```bash
python3 examples/test_linear_mock_only.py
```

This test suite demonstrates:
- Creating issues
- Retrieving issues
- Updating issues
- Getting team IDs
- Error handling

### Full Integration Test

```bash
# Requires LLM dependencies
PYTHONPATH=/path/to/bug-hive python3 examples/test_linear_integration.py
```

## Configuration

### Environment Variables

```bash
# Optional: Enables RealLinearClient
LINEAR_API_KEY=lin_api_xxxxx

# Required for ReportWriterAgent
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENROUTER_API_KEY=sk-or-xxxxx
```

## Development Workflow

1. **Development Phase**: Use MockLinearClient (no API key needed)
2. **Testing Phase**: Test with mock client to validate logic
3. **Staging Phase**: Connect RealLinearClient to Linear workspace
4. **Production Phase**: Use RealLinearClient with actual team IDs

## Logging

All operations are logged with structured metadata:

```python
import logging
logging.basicConfig(level=logging.INFO)

# MockLinearClient logs
[MockLinear] Created issue BUG-1: Button not working
[MockLinear] Updated issue BUG-1
[MockLinear] Retrieved issue BUG-1

# RealLinearClient logs
[RealLinear] Creating issue: Bug title
[RealLinear] Created issue BUG-123

# ReportWriterAgent logs
[ReportWriter] Generating report for bug: [title]
[ReportWriter] Created Linear issue BUG-123
```

## Error Handling

### MockLinearClient

```python
try:
    issue = await client.update_issue("invalid-id", title="Test")
except ValueError as e:
    print(f"Issue not found: {e}")
```

### RealLinearClient

```python
try:
    issue = await client.create_issue(...)
except Exception as e:
    print(f"API error: {e}")
```

### ReportWriterAgent

```python
try:
    issue = await reporter.create_ticket(bug, team_id="qa")
except Exception as e:
    print(f"Failed to create ticket: {e}")
    # Bug remains in database with status="detected"
```

## Future Enhancements

### Planned Features

1. **RealLinearClient**:
   - Complete GraphQL implementation
   - Test with actual Linear workspace
   - Add attachments support
   - Implement label management

2. **ReportWriterAgent**:
   - Support for custom report templates
   - Configurable priority mapping
   - Automatic duplicate detection via Linear search
   - Rich evidence embedding (inline images)

3. **Integration**:
   - Webhook support for Linear updates
   - Bidirectional sync (Linear → BugHive)
   - Comment management
   - State transition tracking

### Contributing

To implement RealLinearClient:

1. Create Linear workspace and get API key
2. Update `linear_real.py` GraphQL mutations
3. Test with real data
4. Add integration tests

## References

- [Linear API Documentation](https://developers.linear.app/docs/graphql/working-with-the-graphql-api)
- [Linear GraphQL Schema](https://studio.apollographql.com/public/Linear-API/variant/current/home)
- [BugHive LLM Router](./llm-routing.md)
- [BugHive Bug Model](./models.md)

## Support

For issues or questions:
1. Check logs for detailed error messages
2. Verify API key format (lin_api_xxxxx)
3. Test with MockLinearClient first
4. Review Linear API quotas and rate limits
