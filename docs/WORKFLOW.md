# BugHive LangGraph Workflow

This document describes the LangGraph workflow architecture that orchestrates the autonomous QA agent system.

## Architecture Overview

```
┌─────────────┐
│    Plan     │  ← Orchestrator (Opus) plans crawl strategy
└─────┬───────┘
      │
      ▼
┌─────────────┐
│    Crawl    │  ← Navigate and extract page data
└─────┬───────┘
      │
      ▼
┌─────────────┐
│   Analyze   │  ← Find bugs with PageAnalyzerAgent
└─────┬───────┘
      │
      ▼
┌─────────────┐
│  Classify   │  ← Deduplicate and prioritize bugs
└─────┬───────┘
      │
      ├─────────────┐
      │             │
      ▼             ▼
┌──────────┐  ┌──────────┐
│ Validate │  │  Report  │  ← Validate critical bugs with Opus
└────┬─────┘  └────┬─────┘
     │             │
     └──────┬──────┘
            │
            ▼
     ┌──────────────┐
     │Create Tickets│  ← Create Linear issues
     └──────┬───────┘
            │
            ├───────────┐
            │           │
            ▼           ▼
     ┌──────────┐  ┌──────────┐
     │ Continue │  │Summarize │  ← Loop or finish
     └──────────┘  └──────────┘
```

## State Schema

The workflow state (`BugHiveState`) tracks:

### Session Info
- `session_id`: Unique session identifier
- `config`: Crawl configuration (max_pages, depth, focus areas, etc.)

### Crawl State
- `pages_discovered`: All discovered pages with status
- `pages_crawled`: Successfully crawled pages with data
- `current_page`: Currently processing page
- `crawl_complete`: Completion flag

### Bug State
- `raw_issues`: Initial issues from PageAnalyzerAgent
- `classified_bugs`: Deduplicated and classified bugs
- `validated_bugs`: Opus-validated high-priority bugs
- `reported_bugs`: Bugs with formatted reports

### Orchestrator Decisions
- `should_continue`: Continue crawling flag
- `validation_needed`: Bug IDs requiring Opus validation
- `priority_override`: Manual priority adjustments

### Outputs
- `linear_tickets`: Created Linear issues
- `summary`: Final session summary

### Metrics
- `total_cost`: Total USD spent on LLM calls
- `llm_calls`: Detailed log of all LLM invocations
- `errors`: Error tracking
- `node_durations`: Performance metrics per node

## Workflow Nodes

### 1. `plan_crawl`
**Purpose**: Strategic planning with Orchestrator (Opus)

**What it does**:
- Analyzes configuration
- Plans crawl strategy (breadth-first vs depth-first)
- Identifies focus areas and quality gates
- Seeds initial pages to discover

**Model**: Claude Opus 4.5 (high-stakes strategic planning)

**Outputs**:
- `pages_discovered`: Initial pages to crawl
- `config.strategy`: Embedded strategy for other nodes

### 2. `crawl_page`
**Purpose**: Navigate and extract page data

**What it does**:
- Selects next uncrawled page (by priority)
- Uses CrawlerAgent to navigate with Browserbase
- Extracts text, HTML structure, screenshots
- Discovers new links
- Updates page status

**Cost**: Browserbase session cost

**Outputs**:
- `current_page`: Page data for analysis
- `pages_crawled`: Updated crawl history
- `pages_discovered`: New pages found

### 3. `analyze_page`
**Purpose**: Find bugs on current page

**What it does**:
- Uses PageAnalyzerAgent with focus areas
- Detects UI/UX, accessibility, functional issues
- Assigns confidence scores
- Provides suggested fixes

**Model**: Claude Sonnet 4.5 (balanced quality/cost)

**Outputs**:
- `raw_issues`: List of discovered issues

### 4. `classify_bugs`
**Purpose**: Deduplicate and prioritize

**What it does**:
- Uses BugClassifierAgent for deduplication
- Groups related issues
- Assigns priority (critical/high/medium/low)
- Filters low-confidence noise

**Model**: Claude Sonnet 4.5

**Outputs**:
- `classified_bugs`: Deduplicated bugs with priorities
- `validation_needed`: IDs needing Opus validation

### 5. `validate_bugs`
**Purpose**: Validate high-priority bugs

**What it does**:
- Validates critical/high priority bugs with Opus
- Assesses business impact
- Adjusts priorities based on strategic context
- Filters false positives

**Model**: Claude Opus 4.5 (high-stakes validation)

**Outputs**:
- `validated_bugs`: Confirmed bugs
- `priority_override`: Priority adjustments

### 6. `generate_reports`
**Purpose**: Create formatted bug reports

**What it does**:
- Uses ReportWriterAgent
- Formats for Linear/Jira
- Adds reproduction steps
- Suggests effort estimates

**Model**: Claude Sonnet 4.5

**Outputs**:
- `reported_bugs`: Bugs with formatted reports

### 7. `create_linear_tickets`
**Purpose**: Create Linear issues

**What it does**:
- Creates issues via Linear API
- Applies labels and priorities
- Links related bugs
- Attaches screenshots

**Cost**: Linear API calls (no LLM cost)

**Outputs**:
- `linear_tickets`: Created issue IDs and URLs

### 8. `generate_summary`
**Purpose**: Final session summary

**What it does**:
- Aggregates statistics
- Calculates costs
- Generates recommendations
- Creates performance report

**Outputs**:
- `summary`: Complete session summary

## Conditional Edges

### `should_validate`
**Decision**: Validate bugs or proceed to reporting?

**Routes**:
- `"validate"`: If critical/high priority bugs need validation
- `"report"`: If all high-priority bugs validated or none exist

### `should_continue_crawling`
**Decision**: Continue crawling or finish?

**Stop Conditions**:
1. Reached `max_pages` limit
2. No uncrawled pages remaining
3. Too many critical bugs (early stop for urgent issues)
4. Too many errors (system instability)
5. Orchestrator decision to stop

**Routes**:
- `"continue"`: Loop back to crawl next page
- `"finish"`: Proceed to summary

### `should_create_tickets`
**Decision**: Create Linear tickets or skip?

**Routes**:
- `"create_tickets"`: If enabled in config and bugs exist
- `"skip_tickets"`: If disabled or no bugs

## Usage Examples

### Quick Crawl
```python
from src.graph import quick_crawl

summary = await quick_crawl(
    url="https://example.com",
    max_pages=10,
    create_tickets=False
)
```

### Deep Crawl
```python
from src.graph import deep_crawl

summary = await deep_crawl(
    url="https://example.com",
    max_pages=100,
    focus_areas=["forms", "navigation", "accessibility"],
    linear_team_id="TEAM123"
)
```

### Custom Configuration
```python
from src.graph import run_bughive

config = {
    "base_url": "https://example.com",
    "max_pages": 50,
    "max_depth": 3,
    "focus_areas": ["forms", "authentication"],
    "quality_mode": "comprehensive",
    "quality_threshold": 0.8,
    "create_linear_tickets": True,
    "linear_team_id": "TEAM123",
}

summary = await run_bughive(config)
```

### With Checkpointing
```python
from langgraph.checkpoint.sqlite import SqliteSaver
from src.graph import run_bughive

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

summary = await run_bughive(config, checkpointer=checkpointer)
```

### Resume Interrupted Crawl
```python
from src.graph import resume_bughive
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

summary = await resume_bughive(
    session_id="abc-123-def-456",
    checkpointer=checkpointer,
    updates={"max_pages": 200}  # Optional updates
)
```

## CLI Commands

### Basic Crawl
```bash
python cli.py crawl https://example.com --max-pages 50
```

### With Focus Areas
```bash
python cli.py crawl https://example.com \
  --max-pages 100 \
  --focus-areas forms \
  --focus-areas navigation \
  --create-tickets \
  --linear-team-id TEAM123
```

### Quick Test
```bash
python cli.py quick https://example.com
```

### Deep Analysis
```bash
python cli.py deep https://example.com \
  --max-pages 200 \
  --linear-team-id TEAM123
```

### Resume Session
```bash
python cli.py resume abc-123-def-456
```

### Visualize Workflow
```bash
python cli.py visualize -o docs/workflow.png
```

## Cost Optimization

### Model Selection by Task
- **Planning**: Opus (strategic, infrequent)
- **Analysis**: Sonnet (balanced, frequent)
- **Classification**: Sonnet (fast, frequent)
- **Validation**: Opus (high-stakes, selective)
- **Reporting**: Sonnet (formatting, frequent)

### Cost Tracking
Every node tracks LLM costs in state:
```python
{
    "node": "analyze_page",
    "model": "claude-sonnet-4-5-20250929",
    "input_tokens": 2000,
    "output_tokens": 500,
    "cost": 0.0125
}
```

Final summary includes cost breakdown by node.

### Optimization Strategies
1. **Selective Validation**: Only validate critical/high bugs with Opus
2. **Batch Processing**: Analyze multiple pages before classification
3. **Early Stopping**: Stop on critical bug threshold
4. **Smart Prioritization**: Crawl high-value pages first

## Parallel Processing

For faster crawls, use parallel batch processing:

```python
from src.graph.parallel import parallel_crawl_batch, parallel_analyze_batch

# Crawl 5 pages in parallel
crawl_results = await parallel_crawl_batch(
    urls=["url1", "url2", "url3", "url4", "url5"],
    session_id="parallel-test",
    config=config
)

# Analyze all pages in parallel
analysis_results = await parallel_analyze_batch(
    pages=crawl_results,
    config=config
)
```

## State Persistence

The workflow supports checkpointing for:
- **Crash Recovery**: Resume after failures
- **Long-Running Crawls**: Pause and resume
- **Configuration Adjustments**: Update limits mid-crawl

### Checkpoint Backends
- **MemorySaver**: In-memory (default, ephemeral)
- **SqliteSaver**: SQLite database (persistent)
- **PostgresSaver**: PostgreSQL (production)

## Error Handling

Each node implements error handling:

1. **Try-Catch**: All nodes catch exceptions
2. **Error Logging**: Errors tracked in state
3. **Graceful Degradation**: Page failures don't stop workflow
4. **Error Summary**: Final summary includes error count

## Performance Metrics

The workflow tracks performance for each node:

```python
{
    "plan_crawl": 2.3,      # seconds
    "crawl_page": 45.7,     # total for all pages
    "analyze_page": 23.4,
    "classify_bugs": 5.1,
    "validate_bugs": 12.8,
    "generate_reports": 8.3,
    "create_linear_tickets": 1.2,
    "generate_summary": 0.4
}
```

## Next Steps

1. **Add Human-in-the-Loop**: Interrupt for manual review
2. **Streaming Updates**: Real-time progress via WebSocket
3. **Multi-Site Crawls**: Parallel workflows for multiple sites
4. **ML Bug Prediction**: Learn from historical data
5. **Visual Regression Testing**: Screenshot comparison
