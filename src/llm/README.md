# BugHive LLM Router

Multi-model LLM infrastructure with intelligent routing and cost optimization for BugHive's autonomous QA agent system.

## Overview

BugHive uses different LLM models for different tasks to optimize for both quality and cost:

| Model | Use Case | Cost/1M tokens | Provider |
|-------|----------|----------------|----------|
| **Claude Opus 4.5** | Orchestration, critical decisions | $15/$75 | Anthropic |
| **DeepSeek-V3** | Reasoning, analysis | $0.27/$1.10 | OpenRouter |
| **DeepSeek-Coder-V2** | Code analysis, bug fixing | $0.14/$0.28 | OpenRouter |
| **Qwen 2.5-72B** | General tasks | $0.15/$0.60 | OpenRouter |
| **Qwen 2.5-32B** | Fast, simple tasks | $0.06/$0.24 | OpenRouter |

## Architecture

```
┌─────────────────┐
│   LLMRouter     │  ← Task-based routing logic
└────────┬────────┘
         │
    ┌────┴─────┐
    ▼          ▼
┌────────┐  ┌──────────┐
│Anthropic│  │OpenRouter│  ← API clients
└────────┘  └──────────┘
         │
         ▼
  ┌─────────────┐
  │CostTracker  │  ← Usage & cost tracking
  └─────────────┘
```

## Installation

```bash
cd src/llm
pip install -r requirements.txt
```

## Setup

Set your API keys as environment variables:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENROUTER_API_KEY="sk-or-..."
```

Or use a `.env` file (recommended for development):

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...
```

## Usage

### Basic Routing

```python
from llm import LLMRouter, AnthropicClient, OpenRouterClient, CostTracker

# Initialize clients
anthropic = AnthropicClient()
openrouter = OpenRouterClient()
tracker = CostTracker()

# Create router
router = LLMRouter(
    anthropic_client=anthropic,
    openrouter_client=openrouter,
    cost_tracker=tracker,
)

# Route a task - automatically selects optimal model
response = await router.route(
    task="analyze_page",  # Task determines model selection
    messages=[
        {"role": "user", "content": "Analyze this page structure..."}
    ],
    session_id="crawl_session_123",
    max_tokens=2000,
)

print(f"Model used: {response['model_tier']}")
print(f"Response: {response['content']}")
print(f"Cost: ${response['cost']:.6f}")
```

### Task-to-Model Mapping

The router automatically selects models based on task type:

```python
from llm import TASK_MODEL_MAP, ModelTier

# High-stakes decisions → Claude Opus
TASK_MODEL_MAP["plan_crawl_strategy"] = ModelTier.ORCHESTRATOR
TASK_MODEL_MAP["quality_gate"] = ModelTier.ORCHESTRATOR

# Analysis → DeepSeek-V3
TASK_MODEL_MAP["classify_bug"] = ModelTier.REASONING
TASK_MODEL_MAP["analyze_page"] = ModelTier.REASONING

# Code tasks → DeepSeek-Coder
TASK_MODEL_MAP["propose_fix"] = ModelTier.CODING
TASK_MODEL_MAP["analyze_stack_trace"] = ModelTier.CODING

# Fast tasks → Qwen-32B
TASK_MODEL_MAP["format_ticket"] = ModelTier.FAST
```

### Direct Client Usage

#### Anthropic Client

```python
from llm import AnthropicClient

async with AnthropicClient() as client:
    response = await client.create_message(
        model="anthropic/claude-opus-4-5-20250514",
        messages=[
            {"role": "user", "content": "Plan a crawl strategy"}
        ],
        max_tokens=2000,
    )
    print(response['content'])
```

#### OpenRouter Client

```python
from llm import OpenRouterClient

async with OpenRouterClient() as client:
    response = await client.create_completion(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "user", "content": "Analyze this bug"}
        ],
        max_tokens=1000,
    )
    print(response['content'])
```

### Tool Use (Function Calling)

Claude Opus supports tool use for agentic workflows:

```python
# Define tools
tools = [
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot of the page",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {"type": "string"}
            }
        }
    }
]

# Call with tools
response = await router.route(
    task="plan_crawl_strategy",
    messages=[{"role": "user", "content": "Inspect the login form"}],
    tools=tools,
)

# Check for tool calls
if response.get('tool_calls'):
    for tool_call in response['tool_calls']:
        print(f"Tool: {tool_call['name']}")
        print(f"Input: {tool_call['input']}")
```

### Cost Tracking

Track usage and costs per session:

```python
from llm import CostTracker

tracker = CostTracker()

# Costs are automatically tracked when using router with session_id
response = await router.route(
    task="analyze_page",
    messages=[...],
    session_id="session_123",
)

# Get session cost
total_cost = tracker.get_session_cost("session_123")
print(f"Session cost: ${total_cost:.4f}")

# Get detailed breakdown
breakdown = tracker.get_breakdown("session_123")
for model, stats in breakdown.items():
    print(f"{model}: ${stats['cost']:.4f}")

# Get formatted summary
print(tracker.get_cost_summary(session_id="session_123"))
```

Output:
```
Session session_123 Cost Summary:
  Total Cost: $0.0123
  Total Requests: 5
  Input Tokens: 3,421
  Output Tokens: 1,234

Model Breakdown:
  ORCHESTRATOR: $0.0100 (1 requests, 1000 in, 500 out)
  REASONING: $0.0020 (3 requests, 2000 in, 600 out)
  FAST: $0.0003 (1 requests, 421 in, 134 out)
```

### Fallback Routing

Automatically fall back to cheaper models on failure:

```python
response = await router.route_with_fallback(
    task="analyze_page",
    messages=[...],
    fallback_tier=ModelTier.FAST,  # Fall back to Qwen-32B
)

if response.get('fallback_used'):
    print("⚠️ Primary model failed, fallback was used")
```

## Task Types

### Orchestrator Tasks (Claude Opus)
- `plan_crawl_strategy` - Plan autonomous crawl approach
- `validate_critical_bug` - Verify high-severity bugs
- `quality_gate` - Final quality check before reporting
- `orchestrate_session` - Coordinate multi-step workflows

### Reasoning Tasks (DeepSeek-V3)
- `analyze_page` - Understand page structure and interactions
- `classify_bug` - Categorize bug type and severity
- `deduplicate_bugs` - Identify duplicate issues
- `evaluate_severity` - Assess bug impact

### Coding Tasks (DeepSeek-Coder)
- `generate_edge_cases` - Create test scenarios
- `propose_fix` - Suggest code fixes
- `analyze_stack_trace` - Parse error traces
- `review_code` - Code quality analysis

### General Tasks (Qwen-72B)
- `extract_navigation` - Parse navigation structure
- `parse_console_logs` - Interpret browser logs
- `identify_elements` - Find UI elements
- `extract_forms` - Parse form structures

### Fast Tasks (Qwen-32B)
- `format_ticket` - Format bug reports
- `summarize_session` - Create session summaries
- `generate_title` - Create bug titles
- `categorize_simple` - Simple categorization

## Error Handling

All clients include automatic retry logic with exponential backoff:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
)
async def _make_request(...):
    # Automatic retries on network errors
    pass
```

Rate limiting is handled automatically:
- 429 responses trigger wait based on `Retry-After` header
- Configurable timeout per request (default: 120s)

## Configuration

### Client Configuration

```python
# Anthropic with custom settings
anthropic = AnthropicClient(
    api_key="sk-ant-...",  # Or from env
    max_retries=5,
    timeout=180.0,
)

# OpenRouter with custom settings
openrouter = OpenRouterClient(
    api_key="sk-or-...",  # Or from env
    timeout=120.0,
    max_retries=3,
)
```

### Adding New Tasks

To add a new task type:

```python
from llm import TASK_MODEL_MAP, ModelTier

# Add to task mapping
TASK_MODEL_MAP["my_new_task"] = ModelTier.REASONING

# Use in routing
response = await router.route(
    task="my_new_task",
    messages=[...],
)
```

## Cost Optimization Tips

1. **Use appropriate tiers**: Don't use Opus for simple formatting
2. **Batch operations**: Group similar tasks to reuse context
3. **Control token limits**: Set `max_tokens` appropriately
4. **Monitor per-session**: Track costs by `session_id`
5. **Use fallbacks**: Have cheaper fallback options

## Examples

See `example_usage.py` for comprehensive examples:

```bash
python src/llm/example_usage.py
```

## Development

### Running Tests

```bash
# TODO: Add pytest tests
pytest src/llm/tests/
```

### Type Checking

All code includes type hints for mypy:

```bash
mypy src/llm/
```

## Roadmap

- [ ] Streaming support for long-running tasks
- [ ] Prompt template library in `prompts/`
- [ ] Cost budget enforcement per session
- [ ] Model performance analytics
- [ ] A/B testing framework for prompts
- [ ] Semantic caching for repeated queries
- [ ] Multi-turn conversation management

## License

Part of BugHive - Autonomous QA Agent System
