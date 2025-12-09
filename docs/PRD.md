# BugHive - Product Requirements Document (PRD)

## Overview

BugHive is an autonomous QA agent system that crawls web applications, detects bugs through multiple analysis methods, and creates actionable tickets in project management tools.

---

## Agent Specifications

### 1. Crawler Agent
**Model:** Qwen2.5-72B (via OpenRouter)
**Purpose:** Navigate the application and build a complete page inventory

**Responsibilities:**
- Login with provided credentials
- Discover and catalog all accessible pages
- Track navigation paths
- Handle dynamic content loading
- Respect rate limits and avoid aggressive crawling
- Report inaccessible pages

**Input:**
```python
class CrawlConfig(BaseModel):
    base_url: str
    auth_method: Literal["session", "oauth", "api_key", "none"]
    credentials: Optional[dict]
    max_pages: int = 100
    max_depth: int = 5
    excluded_patterns: list[str] = []
```

**Output:**
```python
class PageInventory(BaseModel):
    pages: list[Page]
    navigation_graph: dict
    crawl_duration: float
    pages_discovered: int
    pages_crawled: int
```

---

### 2. Page Analyzer Agent
**Model:** DeepSeek-V3 (via OpenRouter)
**Purpose:** Analyze each page for errors and issues

**Detection Capabilities:**

| Category | Detection |
|----------|-----------|
| Console Errors | JS exceptions, React errors, unhandled promise rejections |
| Network Failures | 4xx/5xx responses, timeout errors, CORS issues |
| Visual Issues | Broken images, text overflow, z-index problems |
| Performance | Page load >3s, API calls >5s, large bundles |
| Accessibility | Missing alt text, low contrast, missing labels |
| Content Issues | Lorem ipsum, TODO comments, debug logs |

**Input:**
```python
class PageAnalysisInput(BaseModel):
    url: str
    screenshot_path: str
    console_logs: list[dict]
    network_requests: list[dict]
    dom_snapshot: str
    performance_metrics: dict
```

**Output:**
```python
class PageAnalysisResult(BaseModel):
    url: str
    issues_found: list[RawIssue]
    analysis_time: float
    confidence_scores: dict
```

---

### 3. Edge Case Generator Agent
**Model:** DeepSeek-Coder-V2 (via OpenRouter)
**Purpose:** Generate test scenarios for interactive elements

**Test Scenarios:**
- Empty form submissions
- Boundary values (min/max lengths)
- Special characters (& % < > " ')
- SQL injection patterns
- XSS attempts
- Rapid repeated submissions
- Invalid data formats

**Input:**
```python
class FormContext(BaseModel):
    url: str
    form_html: str
    input_fields: list[dict]
    submit_button: str
    validation_rules: Optional[dict]
```

**Output:**
```python
class TestScenarios(BaseModel):
    form_id: str
    scenarios: list[TestCase]
    priority_order: list[str]
```

---

### 4. Bug Classifier Agent
**Model:** DeepSeek-V3 (via OpenRouter)
**Purpose:** Categorize, prioritize, and deduplicate bugs

**Bug Categories:**
- **UI/UX:** Visual defects, layout issues, styling problems
- **Data:** Incorrect data display, missing data, stale data
- **Edge Case:** Input handling failures, boundary issues
- **Performance:** Slow loads, memory leaks, large payloads
- **Security:** XSS, injection, auth bypass, data exposure

**Priority Levels:**
- **Critical:** App crash, data loss, security vulnerability
- **High:** Core feature broken, significant UX impact
- **Medium:** Feature partially broken, workaround exists
- **Low:** Minor visual issue, cosmetic defect

**Deduplication:**
- Same error message on different pages → single bug
- Same visual issue across components → single bug
- Related console errors → grouped bug

---

### 5. Report Writer Agent
**Model:** Qwen2.5-32B (via OpenRouter)
**Purpose:** Generate well-formatted Linear tickets

**Output Format:**
```markdown
## Summary
[One-line description of the bug]

## Steps to Reproduce
1. Navigate to [page]
2. [Action taken]
3. [Expected vs actual result]

## Evidence
- Screenshot: [attached]
- Console Error: `[error message]`
- Network Request: `[failed request]`

## Environment
- URL: [full URL]
- Browser: Chrome (via Browserbase)
- Timestamp: [ISO timestamp]

## Suggested Priority
[Priority level with justification]
```

---

### 6. Orchestrator Agent
**Model:** Claude Opus 4.5 (via Anthropic API)
**Purpose:** High-level planning, validation, and quality control

**Responsibilities:**
- Create crawl strategy based on app type
- Validate bug reports before submission
- Escalate uncertain findings for review
- Maintain quality gate (reject low-confidence bugs)
- Handle edge cases and unexpected situations
- Summarize session results

**Decision Points:**
- Should this page be crawled? (authentication, relevance)
- Is this a real bug or false positive? (confidence threshold)
- What priority should this bug have? (impact assessment)
- Should we stop early? (critical issue found)

---

### 7. Fix Generator Agent (Phase 3)
**Model:** DeepSeek-Coder-V2 (via OpenRouter)
**Purpose:** Propose code fixes for simple bugs

**Scope:**
- Typos and copy errors
- Missing null checks
- Simple styling fixes
- Missing error handling
- Basic accessibility fixes

**Output:**
```python
class FixProposal(BaseModel):
    bug_id: str
    file_path: str
    original_code: str
    fixed_code: str
    explanation: str
    confidence: float
    test_suggestions: list[str]
```

---

## Data Models

### CrawlSession
```python
class CrawlSession(BaseModel):
    id: UUID
    base_url: str
    status: Literal["pending", "running", "completed", "failed"]
    config: CrawlConfig
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    pages_discovered: int = 0
    pages_crawled: int = 0
    bugs_found: int = 0
    total_cost: float = 0.0
```

### Page
```python
class Page(BaseModel):
    id: UUID
    session_id: UUID
    url: str
    title: Optional[str]
    status: Literal["discovered", "crawling", "analyzed", "error"]
    depth: int
    screenshot_url: Optional[str]
    crawled_at: Optional[datetime]
    analysis_result: Optional[dict]
```

### Bug
```python
class Bug(BaseModel):
    id: UUID
    session_id: UUID
    page_id: UUID
    category: Literal["ui_ux", "data", "edge_case", "performance", "security"]
    priority: Literal["critical", "high", "medium", "low"]
    title: str
    description: str
    steps_to_reproduce: list[str]
    evidence: list[Evidence]
    confidence: float
    status: Literal["detected", "validated", "reported", "dismissed"]
    linear_issue_id: Optional[str]
    created_at: datetime
```

### Evidence
```python
class Evidence(BaseModel):
    type: Literal["screenshot", "console_log", "network_request", "dom_snapshot"]
    content: str  # URL for screenshots, raw content for others
    timestamp: datetime
```

---

## API Endpoints

### Crawl Management

```
POST /crawl/start
Request:
{
    "base_url": "https://app.example.com",
    "auth_method": "session",
    "credentials": {"email": "...", "password": "..."},
    "max_pages": 100
}
Response:
{
    "session_id": "uuid",
    "status": "pending"
}
```

```
GET /crawl/{session_id}/status
Response:
{
    "session_id": "uuid",
    "status": "running",
    "pages_discovered": 45,
    "pages_crawled": 23,
    "bugs_found": 7,
    "elapsed_time": 342.5
}
```

```
GET /crawl/{session_id}/bugs
Response:
{
    "bugs": [...],
    "total": 12,
    "by_priority": {"critical": 1, "high": 3, "medium": 5, "low": 3}
}
```

### Bug Management

```
POST /bugs/{bug_id}/validate
Request:
{
    "is_valid": true,
    "notes": "Confirmed on my machine"
}
```

```
POST /bugs/{bug_id}/report
Response:
{
    "linear_issue_id": "BUG-123",
    "linear_url": "https://linear.app/..."
}
```

```
POST /bugs/{bug_id}/fix (Phase 3)
Response:
{
    "fix_proposal": {...},
    "pr_url": "https://github.com/..."
}
```

---

## Integrations

### Browserbase
- Cloud browser sessions
- Screenshot capture
- Console log extraction
- Network request monitoring

### Linear
- Create issues with labels
- Attach screenshots
- Link related issues
- Update status on validation

### OpenRouter
- Route requests to optimal LLM
- Cost tracking per request
- Fallback handling

### GitHub (Phase 3)
- Read repository structure
- Create branches
- Submit pull requests
- Add review comments

---

## Non-Functional Requirements

### Performance
- Crawl 100+ pages per hour
- Analyze page in <10 seconds
- Generate ticket in <5 seconds

### Reliability
- Resume interrupted crawls
- Retry failed page loads
- Handle rate limiting gracefully

### Cost
- Track LLM usage per session
- Enforce budget limits
- Report cost breakdown

### Security
- Encrypt stored credentials
- Don't log sensitive data
- Private bug handling for security issues
