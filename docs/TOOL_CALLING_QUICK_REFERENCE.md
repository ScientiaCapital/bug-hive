# BugHive Tool Calling - Quick Reference

## Available Tools

### Analyzer Agent Tools

| Tool Name | Required Params | Description |
|-----------|----------------|-------------|
| `take_screenshot` | None | Capture page state screenshot |
| `get_element_details` | `selector` (string) | Get DOM element attributes |
| `check_accessibility` | None | Run WCAG accessibility audit |
| `get_console_errors` | None | Get JavaScript errors/warnings |
| `get_network_logs` | `filter_status` (optional) | Get network request logs |
| `measure_performance` | None | Get Core Web Vitals metrics |

### Crawler Agent Tools

| Tool Name | Required Params | Description |
|-----------|----------------|-------------|
| `navigate_to` | `url` (string) | Navigate to URL |
| `click_element` | `selector` (string) | Click element by selector |
| `fill_form` | `selector`, `value` (strings) | Fill form field |
| `scroll_page` | None | Scroll page (lazy load) |
| `wait_for_element` | `selector` (string) | Wait for element to appear |
| `hover_element` | `selector` (string) | Hover over element |
| `select_dropdown` | `selector`, `value` (strings) | Select dropdown option |

## Usage

### Getting Tools
```python
from src.agents.tools import get_analyzer_tools, get_crawler_tools

analyzer_tools = get_analyzer_tools()  # Returns list of 6 tools
crawler_tools = get_crawler_tools()    # Returns list of 7 tools
```

### Passing Tools to LLM
```python
# In analyzer agent
response = await self.llm.route(
    task="analyze_page",
    messages=[{"role": "user", "content": prompt}],
    tools=get_analyzer_tools(),
    session_id=session_id,
)

# In crawler agent
response = await self.llm.route(
    task="extract_navigation",
    messages=[{"role": "user", "content": prompt}],
    tools=get_crawler_tools(),
)
```

## Tool Schema Format

All tools follow Anthropic's format:
```python
{
    "name": "tool_name",
    "description": "What it does and when to use it",
    "input_schema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "What this param does"}
        },
        "required": ["param"]
    }
}
```

## Example Tool Definitions

### Simple Tool (No Parameters)
```python
{
    "name": "take_screenshot",
    "description": "Capture screenshot of current page state",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}
```

### Tool with Required Parameter
```python
{
    "name": "navigate_to",
    "description": "Navigate to a specific URL",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "Full URL to navigate to"
            }
        },
        "required": ["url"]
    }
}
```

### Tool with Multiple Parameters
```python
{
    "name": "fill_form",
    "description": "Fill a form field with a value",
    "input_schema": {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector for the form field"
            },
            "value": {
                "type": "string",
                "description": "Value to fill into the field"
            }
        },
        "required": ["selector", "value"]
    }
}
```

## Adding New Tools

1. **Define the tool** in `src/agents/tools.py`:
```python
ANALYZER_TOOLS.append({
    "name": "your_new_tool",
    "description": "Clear description of what it does and when to use it",
    "input_schema": {
        "type": "object",
        "properties": {
            "your_param": {
                "type": "string",  # or "number", "boolean"
                "description": "What this parameter is for"
            }
        },
        "required": ["your_param"]  # List required params
    }
})
```

2. **Test it** in `tests/test_agent_tools.py`:
```python
def test_your_new_tool(self):
    """Test your_new_tool definition."""
    tool = next(
        (t for t in ANALYZER_TOOLS if t["name"] == "your_new_tool"),
        None
    )
    assert tool is not None
    assert "your_param" in tool["input_schema"]["properties"]
    assert "your_param" in tool["input_schema"]["required"]
```

3. **Implement the handler** (future work):
```python
# src/agents/tool_handlers.py
async def handle_your_new_tool(param: str, browser_client, session_id):
    """Execute your new tool."""
    result = await do_something(param)
    return {"success": True, "data": result}
```

## Common Patterns

### Optional Parameters
```python
"properties": {
    "required_param": {"type": "string"},
    "optional_param": {"type": "number", "description": "Optional (default: 100)"}
},
"required": ["required_param"]  # optional_param not listed
```

### Enum Values
```python
"filter_status": {
    "type": "string",
    "description": "Filter type: 'all', 'errors', or 'slow'",
    "enum": ["all", "errors", "slow"]
}
```

### Boolean Parameters
```python
"wait_for_navigation": {
    "type": "boolean",
    "description": "Whether to wait for navigation (default: false)"
}
```

## Files to Know

- **Tool Definitions:** `/Users/tmkipper/Desktop/tk_projects/bug-hive/src/agents/tools.py`
- **Analyzer Agent:** `/Users/tmkipper/Desktop/tk_projects/bug-hive/src/agents/analyzer.py`
- **Crawler Agent:** `/Users/tmkipper/Desktop/tk_projects/bug-hive/src/agents/crawler.py`
- **Tests:** `/Users/tmkipper/Desktop/tk_projects/bug-hive/tests/test_agent_tools.py`
- **LLM Router:** `/Users/tmkipper/Desktop/tk_projects/bug-hive/src/llm/router.py`

## Validation

Run these commands to validate tools:
```bash
# Direct validation (no dependencies)
python3 -c "exec(open('src/agents/tools.py').read()); print(f'✅ {len(ANALYZER_TOOLS)} analyzer tools, {len(CRAWLER_TOOLS)} crawler tools')"

# Run tests (requires dependencies)
pytest tests/test_agent_tools.py -v
```

## Troubleshooting

### Import Error
```python
# ❌ Wrong
from src.agents import tools

# ✅ Correct
from src.agents.tools import get_analyzer_tools, get_crawler_tools
```

### Tool Not Recognized by LLM
- Check tool name doesn't have typos
- Ensure description is clear and actionable
- Verify required parameters are listed correctly
- Confirm input_schema follows Anthropic format exactly

### Response Parsing Error
```python
# ❌ Wrong (old route_task format)
response.strip()

# ✅ Correct (route format)
response.get("content", "").strip()
```

## Next Steps

1. **Implement tool handlers** - Create actual execution logic
2. **Add tool response processing** - Handle tool calls in agent loops
3. **Enable multi-turn conversations** - Allow sequential tool usage
4. **Add usage tracking** - Monitor which tools are called when
5. **Optimize tool selection** - Guide LLM to use optimal tools first
