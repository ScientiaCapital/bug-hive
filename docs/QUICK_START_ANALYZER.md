# Quick Start: Page Analyzer Agent

## 5-Minute Quick Start

### 1. Import the Agent

```python
from src.agents.analyzer import PageAnalyzerAgent
from src.llm.router import LLMRouter
```

### 2. Initialize with LLMRouter

```python
# Initialize LLM components (see src/llm/ for setup)
from src.llm.anthropic_client import AnthropicClient
from src.llm.openrouter import OpenRouterClient
from src.llm.cost_tracker import CostTracker

anthropic_client = AnthropicClient(api_key="your-key")
openrouter_client = OpenRouterClient(api_key="your-key")
cost_tracker = CostTracker()

llm_router = LLMRouter(
    anthropic_client=anthropic_client,
    openrouter_client=openrouter_client,
    cost_tracker=cost_tracker,
)

# Create analyzer
analyzer = PageAnalyzerAgent(llm_router=llm_router)
```

### 3. Get Page Data

```python
from src.browser.extractor import PageExtractor
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()

    # Extract page data
    extractor = PageExtractor(page)
    await extractor.setup_listeners()
    await page.goto("https://example.com/products")

    page_data = await extractor.extract_all()
```

### 4. Analyze for Issues

```python
result = await analyzer.analyze(
    page_data=page_data,
    session_id="my-session-123"  # For cost tracking
)
```

### 5. Access Results

```python
# Basic stats
print(f"Total issues: {result.total_issues}")
print(f"Severity: {result.issues_by_severity}")
print(f"By type: {result.issues_by_type}")

# Filter issues
critical_issues = result.critical_issues
high_conf_issues = result.high_confidence_issues

# Iterate through issues
for issue in result.issues_found:
    print(f"\n{issue.title}")
    print(f"  Type: {issue.type}")
    print(f"  Severity: {issue.severity}")
    print(f"  Confidence: {issue.confidence:.2f}")
    print(f"  Evidence: {len(issue.evidence)} items")
```

## What Gets Detected?

| Category | Examples | Severity |
|----------|----------|----------|
| **Console Errors** | Uncaught TypeError, React errors, Promise rejections | High |
| **Network Failures** | HTTP 500, CORS errors, timeouts | High |
| **Performance** | Page load > 3s, API calls > 5s | Medium |
| **Content** | Debug logs, TODO comments | Low |
| **Forms** | Missing action, no validation | Medium |
| **Accessibility** | Missing alt text, low contrast | Medium |
| **Visual** | Layout issues, broken images | Medium |

## Result Structure

```python
PageAnalysisResult(
    url="https://example.com/products",
    issues_found=[
        RawIssue(
            type="console_error",
            title="Console error: Uncaught TypeError...",
            description="Uncaught TypeError: Cannot read property 'map'...",
            severity="high",
            confidence=0.95,
            evidence=[...],
            url="https://example.com/products",
        ),
        # ... more issues
    ],
    analysis_time=2.34,
    confidence_scores={
        "console_error": 0.92,
        "network_failure": 0.88,
    },
    page_title="Products - Example Site",
)
```

## Common Patterns

### Filter by Severity

```python
critical = [i for i in result.issues_found if i.severity == "critical"]
high = [i for i in result.issues_found if i.severity == "high"]
```

### Filter by Type

```python
console_errors = [i for i in result.issues_found if i.type == "console_error"]
perf_issues = [i for i in result.issues_found if i.type == "performance"]
```

### Filter by Confidence

```python
high_confidence = [i for i in result.issues_found if i.confidence >= 0.8]
medium_confidence = [i for i in result.issues_found if 0.5 <= i.confidence < 0.8]
```

### Access Evidence

```python
for issue in result.issues_found:
    for evidence in issue.evidence:
        if evidence.type == "console_log":
            log_data = json.loads(evidence.content)
            print(f"Console log: {log_data['text']}")
        elif evidence.type == "network_request":
            req_data = json.loads(evidence.content)
            print(f"Request: {req_data['method']} {req_data['url']}")
```

## Performance

- **Speed**: 1-3 seconds per page
- **Cost**: $0.0001-0.0003 per page (with LLM)
- **Accuracy**: 90%+ precision

## Next Steps

After analysis, issues flow to:

1. **Bug Validator Agent**: Validates and enriches issues
2. **Deduplication**: Merges similar issues
3. **Report Generator**: Creates Linear tickets

## Need Help?

- **Full docs**: [page-analyzer-agent.md](./page-analyzer-agent.md)
- **Examples**: [../examples/analyzer_demo.py](../examples/analyzer_demo.py)
- **Tests**: [../tests/test_analyzer.py](../tests/test_analyzer.py)

## Demo

Run the interactive demo:

```bash
python examples/analyzer_demo.py
```

This shows all detection types with mock data (no API keys required).
