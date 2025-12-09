# LLM Router Integration Guide

Quick guide for integrating the LLM router into BugHive components.

## For Other Agents Building BugHive

This module is ready to use! Here's how to integrate it into your components.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r src/llm/requirements.txt
```

### 2. Set Environment Variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENROUTER_API_KEY="sk-or-..."
```

### 3. Initialize in Your Module

```python
from src.llm import LLMRouter, AnthropicClient, OpenRouterClient, CostTracker

class YourAgent:
    def __init__(self):
        # Initialize LLM infrastructure
        self.anthropic = AnthropicClient()
        self.openrouter = OpenRouterClient()
        self.cost_tracker = CostTracker()

        self.llm_router = LLMRouter(
            anthropic_client=self.anthropic,
            openrouter_client=self.openrouter,
            cost_tracker=self.cost_tracker,
        )

    async def your_method(self, session_id: str):
        # Use router for LLM calls
        response = await self.llm_router.route(
            task="analyze_page",  # Choose appropriate task type
            messages=[
                {"role": "user", "content": "Your prompt here"}
            ],
            session_id=session_id,
            max_tokens=2000,
        )

        return response['content']

    async def cleanup(self):
        # Clean up clients when done
        await self.anthropic.close()
        await self.openrouter.close()
```

## Available Task Types by Component

### Crawler/Navigator Components
Use these task types:
- `extract_navigation` - Parse page navigation
- `identify_elements` - Find interactable elements
- `extract_forms` - Parse form structures

```python
response = await router.route(
    task="extract_navigation",
    messages=[
        {"role": "user", "content": f"Extract navigation from: {page_html}"}
    ],
)
```

### Bug Detection Components
Use these task types:
- `classify_bug` - Categorize bugs
- `evaluate_severity` - Assess impact
- `deduplicate_bugs` - Find duplicates

```python
response = await router.route(
    task="classify_bug",
    messages=[
        {"role": "user", "content": f"Classify this bug: {bug_description}"}
    ],
)
```

### Code Analysis Components
Use these task types:
- `analyze_stack_trace` - Parse errors
- `propose_fix` - Suggest fixes
- `generate_edge_cases` - Create test cases

```python
response = await router.route(
    task="analyze_stack_trace",
    messages=[
        {"role": "user", "content": f"Analyze: {stack_trace}"}
    ],
)
```

### Orchestrator Components
Use these task types:
- `plan_crawl_strategy` - Plan approach
- `orchestrate_session` - Coordinate tasks
- `quality_gate` - Final validation

```python
response = await router.route(
    task="plan_crawl_strategy",
    messages=[
        {"role": "user", "content": f"Plan crawl for: {site_url}"}
    ],
    tools=available_tools,  # Optional tool definitions
)
```

### Reporting Components
Use these task types:
- `format_ticket` - Format bug reports
- `summarize_session` - Create summaries
- `generate_title` - Create titles

```python
response = await router.route(
    task="format_ticket",
    messages=[
        {"role": "user", "content": f"Format ticket: {bug_data}"}
    ],
)
```

## Database Integration

If you're storing LLM usage in the database:

```python
from src.database.models import LLMUsage  # Hypothetical model

class YourAgent:
    async def track_usage(self, session_id: str, response: dict):
        # Get usage stats
        usage = response['usage']

        # Store in database
        await LLMUsage.create(
            session_id=session_id,
            model=response['model'],
            model_tier=response['model_tier'],
            input_tokens=usage['input_tokens'],
            output_tokens=usage['output_tokens'],
            cost=response['cost'],
            task=response.get('task'),
        )
```

## Adding Custom Tasks

If you need a task type that doesn't exist:

```python
from src.llm import TASK_MODEL_MAP, ModelTier

# Add your custom task
TASK_MODEL_MAP["my_custom_task"] = ModelTier.REASONING

# Use it
response = await router.route(
    task="my_custom_task",
    messages=[...],
)
```

Then submit a PR to add it to the main task mapping!

## Error Handling

Wrap LLM calls in try-except:

```python
from src.llm.openrouter import OpenRouterError
from src.llm.anthropic import anthropic  # For Anthropic exceptions

async def safe_llm_call(self, task: str, messages: list):
    try:
        response = await self.llm_router.route(
            task=task,
            messages=messages,
        )
        return response

    except OpenRouterError as e:
        logger.error(f"OpenRouter API failed: {e}")
        # Handle gracefully - maybe use fallback
        return await self.llm_router.route_with_fallback(
            task=task,
            messages=messages,
            fallback_tier=ModelTier.FAST,
        )

    except Exception as e:
        logger.error(f"Unexpected LLM error: {e}")
        raise
```

## Cost Monitoring

Monitor costs during development:

```python
class YourAgent:
    async def run_session(self, session_id: str):
        # Your logic here...

        # Check costs periodically
        cost = self.cost_tracker.get_session_cost(session_id)
        if cost > 1.0:  # $1 threshold
            logger.warning(f"Session {session_id} has cost ${cost:.2f}")

        # Get final summary
        summary = self.cost_tracker.get_cost_summary(session_id)
        logger.info(summary)
```

## Testing

For testing, you can mock the LLM router:

```python
from unittest.mock import AsyncMock

class TestYourAgent:
    async def test_with_mocked_llm(self):
        agent = YourAgent()

        # Mock the router
        agent.llm_router.route = AsyncMock(return_value={
            'content': 'Mocked response',
            'usage': {'input_tokens': 10, 'output_tokens': 20},
            'cost': 0.001,
            'model': 'test-model',
            'model_tier': 'FAST',
        })

        result = await agent.your_method(session_id="test")
        assert result == 'Mocked response'
```

## Best Practices

1. **Always pass session_id** for cost tracking
2. **Set appropriate max_tokens** to control costs
3. **Use specific task types** for optimal routing
4. **Handle errors gracefully** with fallbacks
5. **Clean up clients** in finally blocks or context managers
6. **Monitor costs** in long-running sessions
7. **Use tools** for agentic workflows with Opus

## Example: Complete Integration

```python
from contextlib import asynccontextmanager
from src.llm import LLMRouter, AnthropicClient, OpenRouterClient, CostTracker

class BugDetector:
    def __init__(self):
        self.anthropic = AnthropicClient()
        self.openrouter = OpenRouterClient()
        self.cost_tracker = CostTracker()
        self.router = LLMRouter(
            anthropic_client=self.anthropic,
            openrouter_client=self.openrouter,
            cost_tracker=self.cost_tracker,
        )

    async def analyze_screenshot(
        self,
        screenshot_base64: str,
        session_id: str
    ) -> dict:
        """Analyze screenshot for potential bugs."""
        try:
            response = await self.router.route(
                task="analyze_page",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": screenshot_base64,
                                }
                            },
                            {
                                "type": "text",
                                "text": "Analyze this screenshot for UI bugs"
                            }
                        ]
                    }
                ],
                session_id=session_id,
                max_tokens=2000,
            )

            return {
                'analysis': response['content'],
                'cost': response['cost'],
            }

        except Exception as e:
            logger.error(f"Screenshot analysis failed: {e}")
            raise

    async def cleanup(self):
        """Clean up resources."""
        await self.anthropic.close()
        await self.openrouter.close()

# Context manager usage
@asynccontextmanager
async def bug_detector():
    detector = BugDetector()
    try:
        yield detector
    finally:
        await detector.cleanup()

# Usage
async def main():
    async with bug_detector() as detector:
        result = await detector.analyze_screenshot(
            screenshot_base64="...",
            session_id="session_123"
        )
        print(result['analysis'])
```

## Questions?

- Check the main README: `src/llm/README.md`
- See examples: `src/llm/example_usage.py`
- Review code: Each module has comprehensive docstrings

## Adding to Main Requirements

Add to project root `requirements.txt`:

```txt
# LLM routing infrastructure
anthropic>=0.39.0
httpx>=0.27.0
tenacity>=9.0.0
```

Or reference the module's requirements:

```bash
pip install -r src/llm/requirements.txt
```
