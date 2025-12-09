# Page Analyzer Agent

The Page Analyzer Agent is responsible for detecting bugs and issues from extracted page data. It combines fast rule-based detection with intelligent LLM-enhanced analysis for comprehensive bug detection.

## Overview

The analyzer processes data extracted by the `PageExtractor` and identifies various types of issues:

- **Console Errors**: JavaScript exceptions, React errors, unhandled promise rejections
- **Network Failures**: HTTP errors (4xx/5xx), CORS issues, timeouts
- **Performance Issues**: Slow page loads, slow API calls, large payloads
- **Content Issues**: Debug logs, TODO comments, placeholder text
- **Form Issues**: Missing attributes, validation problems
- **Accessibility Issues**: Missing alt text, low contrast (via LLM)
- **Visual Issues**: Layout problems, broken images (via LLM)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  PageAnalyzerAgent                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐  │
│  │         Rule-Based Detection (Fast)              │  │
│  │  • Console errors (JS exceptions, React errors)  │  │
│  │  • Network failures (4xx/5xx, CORS)              │  │
│  │  • Performance issues (slow loads, API calls)    │  │
│  │  • Content issues (debug logs, TODOs)            │  │
│  │  • Form issues (missing attributes)              │  │
│  └─────────────────────────────────────────────────┘  │
│                         ↓                               │
│                  RawIssue objects                       │
│                         ↓                               │
│  ┌─────────────────────────────────────────────────┐  │
│  │      LLM-Enhanced Detection (Intelligent)        │  │
│  │  • Uses DeepSeek-V3 (via LLMRouter)              │  │
│  │  • Accessibility issues                           │  │
│  │  • Visual problems                                │  │
│  │  • Complex content issues                         │  │
│  │  • Context-aware severity assessment             │  │
│  └─────────────────────────────────────────────────┘  │
│                         ↓                               │
│              PageAnalysisResult                         │
│  • All detected issues                                  │
│  • Confidence scores by type                            │
│  • Analysis metadata                                    │
└─────────────────────────────────────────────────────────┘
```

## Usage

### Basic Usage

```python
from src.agents.analyzer import PageAnalyzerAgent
from src.browser.extractor import PageExtractor
from src.llm.router import LLMRouter

# Initialize components
llm_router = LLMRouter(anthropic_client, openrouter_client, cost_tracker)
analyzer = PageAnalyzerAgent(llm_router=llm_router)

# Extract page data
async with async_playwright() as p:
    browser = await p.chromium.launch()
    page = await browser.new_page()

    extractor = PageExtractor(page)
    await extractor.setup_listeners()
    await page.goto("https://example.com/products")

    page_data = await extractor.extract_all()

    # Analyze for issues
    result = await analyzer.analyze(
        page_data=page_data,
        session_id="my-session-id"  # For cost tracking
    )

    # Process results
    print(f"Found {result.total_issues} issues")
    print(f"Severity: {result.issues_by_severity}")
    print(f"High confidence: {len(result.high_confidence_issues)}")

    for issue in result.critical_issues:
        print(f"CRITICAL: {issue.title}")
```

### Access Results

```python
# Get all issues
all_issues = result.issues_found

# Filter by severity
critical = result.critical_issues
high_conf = result.high_confidence_issues

# Get counts
severity_distribution = result.issues_by_severity
# {'critical': 2, 'high': 5, 'medium': 8, 'low': 3}

type_distribution = result.issues_by_type
# {'console_error': 4, 'network_failure': 3, 'performance': 2}

# Check analysis metrics
print(f"Analysis took {result.analysis_time:.2f}s")
print(f"Confidence scores: {result.confidence_scores}")
```

## Detection Capabilities

### 1. Console Error Detection

Detects JavaScript errors and warnings from console logs:

- **Uncaught exceptions**: High severity (0.95 confidence)
- **React errors**: High severity (0.92 confidence)
- **Warnings**: Low severity (0.75 confidence)
- **Unhandled promise rejections**: High severity

Example:
```python
RawIssue(
    type="console_error",
    title="Console error: Uncaught TypeError: Cannot read property 'map' of undefined",
    description="Uncaught TypeError: Cannot read property 'map' of undefined at app.js:42",
    severity="high",
    confidence=0.95,
    evidence=[Evidence(type="console_log", content="{...}")]
)
```

### 2. Network Failure Detection

Identifies failed HTTP requests and network issues:

- **5xx errors**: High severity (0.95 confidence)
- **4xx errors**: Medium severity (0.90 confidence)
- **CORS errors**: High severity (0.98 confidence)
- **Timeouts**: High severity

Example:
```python
RawIssue(
    type="network_failure",
    title="HTTP 500 on POST /api/users",
    description="Request to /api/users returned 500 Internal Server Error",
    severity="high",
    confidence=0.95,
    evidence=[Evidence(type="network_request", content="{...}")]
)
```

### 3. Performance Issue Detection

Detects slow page loads and API calls:

- **Page load > 3s**: Medium/High severity (0.85 confidence)
- **Page load > 5s**: High severity
- **API call > 5s**: Medium/High severity (0.80 confidence)
- **API call > 10s**: High severity

Example:
```python
RawIssue(
    type="performance",
    title="Slow page load: 4523ms",
    description="Page took 4523ms to load (threshold: 3000ms). This impacts user experience and SEO.",
    severity="medium",
    confidence=0.85,
    evidence=[Evidence(type="performance_metrics", content="{...}")]
)
```

### 4. Content Issue Detection

Finds debug code and placeholder content:

- **Debug console logs**: Low severity (0.70 confidence)
- **TODO/FIXME comments**: Low severity (detected by LLM)
- **Lorem ipsum text**: Medium severity (detected by LLM)

### 5. Form Issue Detection

Identifies form problems:

- **Missing action attribute**: Low severity (0.65 confidence)
- **Required field without name**: Medium severity (0.75 confidence)
- **Inputs without labels**: Medium severity (detected by LLM)

### 6. LLM-Enhanced Detection

Uses DeepSeek-V3 for complex analysis:

- **Accessibility issues**: Missing alt text, low contrast, ARIA labels
- **Visual problems**: Layout issues, z-index problems
- **Complex content issues**: Context-aware detection
- **Smart severity assessment**: Based on user impact

## Models

### RawIssue

Represents a detected issue before validation/deduplication:

```python
class RawIssue(BaseModel):
    type: Literal[
        "console_error",
        "network_failure",
        "performance",
        "visual",
        "content",
        "form",
        "accessibility",
        "security"
    ]
    title: str  # Brief description (max 255 chars)
    description: str  # Detailed explanation
    evidence: list[Evidence]  # Supporting evidence
    confidence: float  # 0.0-1.0
    severity: Literal["critical", "high", "medium", "low"]
    url: str | None  # Page URL
    detected_at: datetime
    metadata: dict | None  # Additional context
```

### PageAnalysisResult

Complete analysis results:

```python
class PageAnalysisResult(BaseModel):
    url: str
    issues_found: list[RawIssue]
    analysis_time: float  # Seconds
    confidence_scores: dict[str, float]  # By issue type
    page_title: str | None
    analyzed_at: datetime
    metadata: dict | None

    # Computed properties
    @property
    def total_issues(self) -> int

    @property
    def issues_by_severity(self) -> dict[str, int]

    @property
    def issues_by_type(self) -> dict[str, int]

    @property
    def high_confidence_issues(self) -> list[RawIssue]

    @property
    def critical_issues(self) -> list[RawIssue]
```

## Detection Strategy

### Rule-Based Detection (Fast, Free)

1. **Console Errors**: Pattern matching on log level and text
2. **Network Failures**: HTTP status code checks
3. **Performance**: Threshold-based (3s for pages, 5s for APIs)
4. **Content**: Keyword matching for debug patterns
5. **Forms**: DOM structure validation

**Advantages**:
- No LLM cost
- Instant results
- Deterministic
- High precision for known patterns

### LLM-Enhanced Detection (Intelligent, Cost-Effective)

1. **Context-Aware Analysis**: Understands page purpose
2. **Accessibility**: Detects WCAG violations
3. **Visual Issues**: Layout and styling problems
4. **Smart Severity**: Based on user impact
5. **False Positive Reduction**: Filters noise

**Advantages**:
- Catches complex issues
- Context-aware
- Better severity assessment
- Learns from patterns

## Configuration

### Thresholds

Adjust detection thresholds:

```python
# Performance thresholds (in milliseconds)
PAGE_LOAD_THRESHOLD = 3000  # 3 seconds
API_CALL_THRESHOLD = 5000   # 5 seconds

# Confidence thresholds
HIGH_CONFIDENCE = 0.8
MEDIUM_CONFIDENCE = 0.5
```

### LLM Settings

Configure LLM analysis:

```python
analyzer = PageAnalyzerAgent(llm_router=llm_router)

# LLM uses:
# - Task: "analyze_page" → DeepSeek-V3 (via LLMRouter)
# - Temperature: 0.3 (deterministic)
# - Max tokens: 2048
```

## Performance

### Analysis Speed

- **Rule-based detection**: ~50-100ms
- **LLM analysis**: ~1-3s (DeepSeek-V3)
- **Total**: ~1-3s per page

### Cost

- **Rule-based**: $0 (free)
- **LLM analysis**: ~$0.0001-0.0003 per page (DeepSeek-V3 pricing)
- **Total**: ~$0.10-0.30 per 1000 pages

### Optimization Tips

1. **Skip LLM for clean pages**: If no rule-based issues, consider skipping LLM
2. **Batch analysis**: Process multiple pages before LLM calls
3. **Cache results**: For repeated page visits
4. **Adjust thresholds**: Based on your app's performance targets

## Error Handling

The analyzer handles errors gracefully:

```python
# LLM failures don't break analysis
try:
    llm_issues = await self._analyze_with_llm(page_data)
except Exception as e:
    logger.error("llm_analysis_failed", error=str(e))
    llm_issues = []  # Continue with rule-based only

# Invalid LLM responses are logged and skipped
try:
    issues_data = json.loads(llm_response)
except JSONDecodeError:
    logger.error("invalid_llm_response")
    return []
```

## Testing

Run tests:

```bash
# Run analyzer tests
pytest tests/test_analyzer.py -v

# Test with coverage
pytest tests/test_analyzer.py --cov=src/agents/analyzer

# Test specific detection
pytest tests/test_analyzer.py::test_detect_console_errors -v
```

## Integration

### With Crawler Agent

```python
from src.agents.crawler import CrawlerAgent
from src.agents.analyzer import PageAnalyzerAgent

# Crawl and analyze together
crawler = CrawlerAgent(...)
analyzer = PageAnalyzerAgent(...)

async for page in crawler.crawl(base_url):
    page_data = await extractor.extract_all()
    analysis = await analyzer.analyze(page_data)

    # Store results
    await store_analysis(page.id, analysis)
```

### With Bug Validator

```python
# Analyze → Validate → Report
analysis = await analyzer.analyze(page_data)

for raw_issue in analysis.high_confidence_issues:
    # Validate issue
    bug = await validator.validate(raw_issue)

    if bug.status == "validated":
        # Report to Linear
        await reporter.report(bug)
```

## Prompt Templates

Located in `src/agents/prompts/analyzer.py`:

1. **ANALYZE_PAGE_PROMPT**: Main analysis prompt
2. **CLASSIFY_ISSUE_PROMPT**: Issue classification
3. **DEDUPLICATE_ISSUES_PROMPT**: Deduplication
4. **GENERATE_BUG_STEPS_PROMPT**: Reproduction steps

Customize prompts for your use case:

```python
from src.agents.prompts.analyzer import ANALYZE_PAGE_PROMPT

# Modify prompt template
custom_prompt = ANALYZE_PAGE_PROMPT + """
Additional instructions:
- Focus on e-commerce specific issues
- Prioritize checkout flow bugs
"""
```

## Best Practices

1. **Always provide session_id**: For cost tracking
2. **Review confidence thresholds**: Adjust based on false positive rate
3. **Monitor LLM costs**: Track usage with CostTracker
4. **Validate critical issues**: Don't auto-report without validation
5. **Log all detections**: For continuous improvement
6. **Adjust severity**: Based on your app's criticality
7. **Test on real pages**: Validate detection accuracy

## Next Steps

After analysis, issues flow to:

1. **Bug Validator Agent**: Validates and enriches issues
2. **Deduplication**: Merges similar issues
3. **Bug Report Generator**: Creates Linear tickets
4. **Quality Gate**: Final review before reporting

See [Bug Validator Agent](./bug-validator-agent.md) for the next step.
