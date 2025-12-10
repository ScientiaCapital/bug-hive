# BugHive - Architecture Document

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BugHive System                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐     ┌───────────────────────────────────────┐    │
│  │   FastAPI    │────▶│         LangGraph Orchestration        │    │
│  │   Gateway    │     │                                        │    │
│  └──────────────┘     │  ┌─────────┐  ┌──────────┐  ┌───────┐ │    │
│                       │  │ Crawler │─▶│ Analyzer │─▶│Classify│ │    │
│                       │  └─────────┘  └──────────┘  └───────┘ │    │
│                       │       │            │            │      │    │
│                       │       ▼            ▼            ▼      │    │
│                       │  ┌─────────────────────────────────┐   │    │
│                       │  │         Orchestrator            │   │    │
│                       │  │        (Claude Opus 4.5)        │   │    │
│                       │  └─────────────────────────────────┘   │    │
│                       └───────────────────────────────────────┘    │
│                                        │                            │
│  ┌─────────────────────────────────────┴────────────────────────┐  │
│  │                    Infrastructure Layer                       │  │
│  │  ┌────────────┐ ┌───────┐ ┌──────────┐ ┌─────────────────┐  │  │
│  │  │Browserbase │ │ Redis │ │ Postgres │ │ S3/Screenshots  │  │  │
│  │  └────────────┘ └───────┘ └──────────┘ └─────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                        │                            │
│  ┌─────────────────────────────────────┴────────────────────────┐  │
│  │                   External Integrations                       │  │
│  │  ┌────────┐  ┌────────┐  ┌───────┐  ┌─────────────────────┐ │  │
│  │  │ Linear │  │ GitHub │  │ Slack │  │ OpenRouter/Anthropic│ │  │
│  │  └────────┘  └────────┘  └───────┘  └─────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
bug-hive/
├── docs/
│   ├── PRP.md
│   ├── PRD.md
│   └── ARCHITECTURE.md
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── routes/
│   │   │   ├── crawl.py         # Crawl endpoints
│   │   │   ├── bugs.py          # Bug management
│   │   │   └── health.py        # Health checks
│   │   └── middleware/
│   │       └── auth.py          # API key auth
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── crawler.py           # Crawler agent
│   │   ├── analyzer.py          # Page analyzer
│   │   ├── classifier.py        # Bug classifier
│   │   ├── edge_case.py         # Edge case generator
│   │   ├── reporter.py          # Report writer
│   │   ├── orchestrator.py      # Orchestrator (Opus)
│   │   └── fix_generator.py     # Fix generator (Phase 3)
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── state.py             # LangGraph state
│   │   ├── nodes.py             # Graph nodes
│   │   ├── edges.py             # Conditional edges
│   │   └── workflow.py          # Main workflow
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── client.py            # Browserbase client
│   │   ├── extractor.py         # Page data extraction
│   │   └── navigator.py         # Navigation logic
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── router.py            # LLM routing logic
│   │   ├── openrouter.py        # OpenRouter client
│   │   ├── anthropic.py         # Anthropic client
│   │   └── prompts/
│   │       ├── crawler.py
│   │       ├── analyzer.py
│   │       ├── classifier.py
│   │       └── reporter.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── linear.py            # Linear API client
│   │   ├── github.py            # GitHub client (Phase 3)
│   │   └── slack.py             # Slack notifications
│   ├── models/
│   │   ├── __init__.py
│   │   ├── crawl.py             # Crawl session models
│   │   ├── page.py              # Page models
│   │   ├── bug.py               # Bug models
│   │   └── evidence.py          # Evidence models
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py          # DB connection
│   │   ├── models.py            # SQLAlchemy models
│   │   └── repositories/
│   │       ├── session.py
│   │       ├── page.py
│   │       └── bug.py
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py        # Celery config
│   │   └── tasks.py             # Background tasks
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Settings
│   │   └── logging.py           # Logging config
│   └── cli/
│       ├── __init__.py
│       └── main.py              # CLI interface
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── scripts/
│   ├── setup.sh
│   └── run_local.sh
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── pyproject.toml
├── README.md
└── .env.example
```

---

## LangGraph Workflow

### State Schema

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class BugHiveState(TypedDict):
    # Session info
    session_id: str
    config: dict
    
    # Crawl state
    pages_discovered: list[dict]
    pages_crawled: list[dict]
    current_page: dict | None
    crawl_complete: bool
    
    # Bug state
    raw_issues: list[dict]
    classified_bugs: list[dict]
    validated_bugs: list[dict]
    reported_bugs: list[dict]
    
    # Orchestrator decisions
    should_continue: bool
    validation_needed: list[str]
    priority_override: dict
    
    # Outputs
    linear_tickets: list[dict]
    summary: dict
    
    # Messages for agent communication
    messages: Annotated[list, add_messages]
```

### Graph Definition

```python
from langgraph.graph import StateGraph, END

def create_workflow():
    workflow = StateGraph(BugHiveState)
    
    # Add nodes
    workflow.add_node("plan", plan_crawl)
    workflow.add_node("crawl", crawl_page)
    workflow.add_node("analyze", analyze_page)
    workflow.add_node("classify", classify_bugs)
    workflow.add_node("validate", validate_bugs)
    workflow.add_node("report", generate_reports)
    workflow.add_node("create_tickets", create_linear_tickets)
    workflow.add_node("summarize", generate_summary)
    
    # Define edges
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "crawl")
    workflow.add_edge("crawl", "analyze")
    workflow.add_edge("analyze", "classify")
    
    # Conditional: validate only high-confidence bugs
    workflow.add_conditional_edges(
        "classify",
        should_validate,
        {
            "validate": "validate",
            "report": "report"
        }
    )
    
    workflow.add_edge("validate", "report")
    workflow.add_edge("report", "create_tickets")
    
    # Conditional: continue crawling or summarize
    workflow.add_conditional_edges(
        "create_tickets",
        should_continue_crawling,
        {
            "continue": "crawl",
            "finish": "summarize"
        }
    )
    
    workflow.add_edge("summarize", END)
    
    return workflow.compile()
```

### Parallel Page Processing

```python
from langgraph.graph import Send

def crawl_and_analyze(state: BugHiveState):
    """Fan out to analyze multiple pages in parallel."""
    pages = state["pages_discovered"][:10]  # Batch of 10
    return [
        Send("analyze_single_page", {"page": page})
        for page in pages
        if page["status"] == "discovered"
    ]
```

---

## LLM Router

### Model Configuration

```python
from enum import Enum

class ModelTier(Enum):
    ORCHESTRATOR = "anthropic/claude-opus-4-5-20250514"
    REASONING = "deepseek/deepseek-chat"  # DeepSeek-V3
    CODING = "deepseek/deepseek-coder"
    GENERAL = "qwen/qwen-2.5-72b-instruct"
    FAST = "qwen/qwen-2.5-32b-instruct"

MODEL_COSTS = {
    ModelTier.ORCHESTRATOR: {"input": 15.0, "output": 75.0},
    ModelTier.REASONING: {"input": 0.27, "output": 1.10},
    ModelTier.CODING: {"input": 0.14, "output": 0.28},
    ModelTier.GENERAL: {"input": 0.15, "output": 0.60},
    ModelTier.FAST: {"input": 0.06, "output": 0.24},
}
```

### Task-to-Model Mapping

```python
TASK_MODEL_MAP = {
    # High-stakes decisions → Opus
    "plan_crawl_strategy": ModelTier.ORCHESTRATOR,
    "validate_critical_bug": ModelTier.ORCHESTRATOR,
    "quality_gate": ModelTier.ORCHESTRATOR,
    
    # Analysis and reasoning → DeepSeek-V3
    "analyze_page": ModelTier.REASONING,
    "classify_bug": ModelTier.REASONING,
    "deduplicate_bugs": ModelTier.REASONING,
    
    # Code-related → DeepSeek-Coder
    "generate_edge_cases": ModelTier.CODING,
    "propose_fix": ModelTier.CODING,
    "analyze_stack_trace": ModelTier.CODING,
    
    # General tasks → Qwen-72B
    "extract_navigation": ModelTier.GENERAL,
    "parse_console_logs": ModelTier.GENERAL,
    
    # Fast tasks → Qwen-32B
    "format_ticket": ModelTier.FAST,
    "summarize_session": ModelTier.FAST,
}
```

### Router Implementation

```python
class LLMRouter:
    def __init__(self, openrouter_client, anthropic_client):
        self.openrouter = openrouter_client
        self.anthropic = anthropic_client
        self.cost_tracker = CostTracker()
    
    async def route(
        self,
        task: str,
        messages: list[dict],
        max_tokens: int = 4096
    ) -> dict:
        model_tier = TASK_MODEL_MAP.get(task, ModelTier.GENERAL)
        
        # Use Anthropic directly for Opus
        if model_tier == ModelTier.ORCHESTRATOR:
            response = await self.anthropic.messages.create(
                model=model_tier.value.split("/")[1],
                messages=messages,
                max_tokens=max_tokens
            )
        else:
            # Use OpenRouter for all other models
            response = await self.openrouter.chat.completions.create(
                model=model_tier.value,
                messages=messages,
                max_tokens=max_tokens
            )
        
        # Track costs
        self.cost_tracker.add(
            model=model_tier,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens
        )
        
        return response
```

---

## Browser Automation

### Browserbase Client

```python
from browserbase import Browserbase
from playwright.async_api import async_playwright

class BrowserClient:
    def __init__(self, api_key: str, project_id: str):
        self.bb = Browserbase(api_key=api_key)
        self.project_id = project_id
        self.session = None
        self.browser = None
        self.page = None
    
    async def start_session(self):
        """Create a new browser session."""
        self.session = self.bb.sessions.create(
            project_id=self.project_id,
            browser_settings={
                "viewport": {"width": 1920, "height": 1080}
            }
        )
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.connect_over_cdp(
            self.session.connect_url
        )
        self.page = await self.browser.new_page()
        return self.session.id
    
    async def navigate(self, url: str) -> dict:
        """Navigate to URL and wait for load."""
        response = await self.page.goto(url, wait_until="networkidle")
        return {
            "status": response.status,
            "url": self.page.url,
            "title": await self.page.title()
        }
    
    async def screenshot(self, path: str):
        """Take full-page screenshot."""
        await self.page.screenshot(path=path, full_page=True)
    
    async def close(self):
        """Clean up session."""
        if self.browser:
            await self.browser.close()
        if self.session:
            self.bb.sessions.stop(self.session.id)
```

### Page Extractor

```python
class PageExtractor:
    def __init__(self, page):
        self.page = page
    
    async def extract_all(self) -> dict:
        """Extract all relevant data from current page."""
        return {
            "url": self.page.url,
            "title": await self.page.title(),
            "screenshot": await self._take_screenshot(),
            "console_logs": await self._get_console_logs(),
            "network_requests": await self._get_network_requests(),
            "dom_snapshot": await self._get_dom_snapshot(),
            "forms": await self._get_forms(),
            "links": await self._get_links(),
            "performance": await self._get_performance_metrics()
        }
    
    async def _get_console_logs(self) -> list[dict]:
        """Get console logs captured during navigation."""
        # Logs collected via page.on("console", ...)
        return self._console_logs
    
    async def _get_network_requests(self) -> list[dict]:
        """Get network requests with status codes."""
        # Requests collected via page.on("response", ...)
        return [
            {
                "url": r.url,
                "status": r.status,
                "method": r.request.method,
                "duration": r.duration
            }
            for r in self._network_responses
        ]
    
    async def _get_forms(self) -> list[dict]:
        """Extract form elements for edge case testing."""
        return await self.page.evaluate("""
            () => Array.from(document.forms).map(form => ({
                id: form.id,
                action: form.action,
                method: form.method,
                inputs: Array.from(form.elements).map(el => ({
                    name: el.name,
                    type: el.type,
                    required: el.required,
                    pattern: el.pattern
                }))
            }))
        """)
    
    async def _get_links(self) -> list[str]:
        """Extract all links for crawl queue."""
        return await self.page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(href => href.startsWith(window.location.origin))
        """)
```

---

## Database Schema

### SQLAlchemy Models

```python
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

class CrawlSessionDB(Base):
    __tablename__ = "crawl_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    base_url = Column(String, nullable=False)
    status = Column(String, default="pending")
    config = Column(JSON)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    pages_discovered = Column(Integer, default=0)
    pages_crawled = Column(Integer, default=0)
    bugs_found = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    
    pages = relationship("PageDB", back_populates="session")
    bugs = relationship("BugDB", back_populates="session")

class PageDB(Base):
    __tablename__ = "pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("crawl_sessions.id"))
    url = Column(String, nullable=False)
    title = Column(String)
    status = Column(String, default="discovered")
    depth = Column(Integer, default=0)
    screenshot_url = Column(String)
    crawled_at = Column(DateTime)
    analysis_result = Column(JSON)
    
    session = relationship("CrawlSessionDB", back_populates="pages")
    bugs = relationship("BugDB", back_populates="page")

class BugDB(Base):
    __tablename__ = "bugs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("crawl_sessions.id"))
    page_id = Column(UUID(as_uuid=True), ForeignKey("pages.id"))
    category = Column(String)
    priority = Column(String)
    title = Column(String, nullable=False)
    description = Column(String)
    steps_to_reproduce = Column(JSON)
    evidence = Column(JSON)
    confidence = Column(Float)
    status = Column(String, default="detected")
    linear_issue_id = Column(String)
    created_at = Column(DateTime)
    
    session = relationship("CrawlSessionDB", back_populates="bugs")
    page = relationship("PageDB", back_populates="bugs")
```

---

## Background Tasks (Celery)

```python
from celery import Celery

celery_app = Celery(
    "bughive",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1"
)

@celery_app.task
def run_crawl_session(session_id: str, config: dict):
    """Main crawl task - runs the LangGraph workflow."""
    from src.graph.workflow import create_workflow
    
    workflow = create_workflow()
    initial_state = {
        "session_id": session_id,
        "config": config,
        "pages_discovered": [],
        "pages_crawled": [],
        # ... initialize all state fields
    }
    
    result = workflow.invoke(initial_state)
    return result["summary"]

@celery_app.task
def create_linear_ticket(bug_id: str, report: dict):
    """Create ticket in Linear."""
    from src.integrations.linear import LinearClient
    
    client = LinearClient()
    issue = client.create_issue(
        title=report["title"],
        description=report["description"],
        labels=report["labels"],
        priority=report["priority"]
    )
    
    # Update bug record with Linear issue ID
    # ...
    return issue.id

@celery_app.task
def upload_screenshot(session_id: str, page_id: str, screenshot_bytes: bytes):
    """Upload screenshot to S3."""
    # ... S3 upload logic
    pass
```

---

## Docker Configuration

### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://bughive:bughive@postgres:5432/bughive
      - REDIS_URL=redis://redis:6379/0
      - BROWSERBASE_API_KEY=${BROWSERBASE_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LINEAR_API_KEY=${LINEAR_API_KEY}
    depends_on:
      - postgres
      - redis
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile
    environment:
      - DATABASE_URL=postgresql://bughive:bughive@postgres:5432/bughive
      - REDIS_URL=redis://redis:6379/0
      - BROWSERBASE_API_KEY=${BROWSERBASE_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - postgres
      - redis
    command: celery -A src.workers.celery_app worker --loglevel=info

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=bughive
      - POSTGRES_PASSWORD=bughive
      - POSTGRES_DB=bughive
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## Security Considerations

### Credential Storage
- Encrypt credentials at rest using Fernet
- Never log credentials or auth tokens
- Session tokens expire after crawl completion

### Bug Handling
- Security bugs marked private by default
- Critical security issues trigger immediate Slack alert
- No screenshot capture for pages with sensitive data patterns

### Rate Limiting
- Max 10 requests/second to target app
- Respect robots.txt (configurable)
- Honor rate limit headers

### Data Retention
- Screenshots deleted after 30 days
- Session data deleted after 90 days
- Configurable per-customer retention

---

## Monitoring & Metrics

### Key Metrics
- Pages crawled per session
- Bugs detected per session
- Bugs reported (after validation)
- LLM cost per session
- False positive rate
- Time to complete session

### Logging
- Structured JSON logs
- Request ID tracking
- LLM call traces
- Error categorization

### Alerts
- Session failure
- Cost threshold exceeded
- High false positive rate
- Integration failures (Linear, Browserbase)

---

## Agent Harness Patterns (Sprint 2)

### System Prompts & Agent Personas

All agents share a consistent identity through a unified system prompt:

```python
# src/agents/prompts/__init__.py
BUGHIVE_SYSTEM_PROMPT = """
You are DeepQA, an expert autonomous QA engineer within the BugHive system.
Your role is to identify bugs that real users will encounter.

You have access to:
- Page DOM analysis and network monitoring
- Performance profiling and accessibility checking
- Screenshot evidence collection

You must:
1. Reason through evidence systematically before concluding
2. Flag uncertainty when confidence is below 0.8
3. Prioritize user impact over technical correctness
4. Provide reasoning traces with your decisions

When unsure, escalate to human review rather than guess.
"""
```

### Progress Tracking & Checkpointing

Human-readable progress files enable crash recovery:

```python
# src/utils/progress_tracker.py
class ProgressTracker:
    def __init__(self, session_id: str, output_dir: Path):
        self.progress_file = output_dir / f"{session_id}_progress.txt"
        self.state_file = output_dir / f"{session_id}_state.json"

    def update(self, stage: str, pages_done: int, pages_total: int,
               bugs_found: int, cost: float, eta_seconds: int | None = None):
        """Write human-readable progress: [timestamp] stage | Pages: X/Y | Bugs: Z"""

    def save_state(self, state: dict):
        """Save structured JSON state snapshot for crash recovery."""
```

Example progress output:
```
[2025-01-15T10:30:00] crawl | Pages: 5/20 | Bugs: 3 | Cost: $0.05 ETA: 180s
[2025-01-15T10:35:00] analyze | Pages: 10/20 | Bugs: 8 | Cost: $0.12 ETA: 60s
```

### Token Budget Management

Prevents context overflow with character-based token estimation (no OpenAI dependencies):

```python
# src/llm/token_budget.py
MODEL_CONTEXT_LIMITS = {
    ModelTier.ORCHESTRATOR: 200_000,  # Claude Opus
    ModelTier.REASONING: 64_000,      # DeepSeek-V3
    ModelTier.CODING: 128_000,        # DeepSeek-Coder
    ModelTier.GENERAL: 32_000,        # Qwen-72B
    ModelTier.FAST: 32_000,           # Qwen-32B
}

class TokenBudget:
    def estimate_tokens(self, messages: list[dict], model_family: str = "default") -> int:
        """Estimate tokens using character-based heuristic (~4 chars/token)."""

    def validate_request(self, model: ModelTier, messages: list[dict], max_tokens: int) -> bool:
        """Return True if request fits in context window."""

    def get_remaining_budget(self, model: ModelTier, messages: list[dict]) -> int:
        """Return tokens available for response."""
```

### Tool Calling in Agents

Agents have access to structured tools for browser automation:

```python
# src/agents/tools.py
ANALYZER_TOOLS = [
    {
        "name": "record_issue",
        "description": "Record a detected bug with evidence",
        "input_schema": {...}
    },
    {
        "name": "request_screenshot",
        "description": "Request screenshot of current page state",
        "input_schema": {...}
    }
]

CRAWLER_TOOLS = [
    {
        "name": "navigate_to",
        "description": "Navigate to a URL",
        "input_schema": {...}
    },
    {
        "name": "click_element",
        "description": "Click on a DOM element",
        "input_schema": {...}
    },
    {
        "name": "fill_form",
        "description": "Fill and submit a form",
        "input_schema": {...}
    }
]
```

### Extended Thinking for Critical Decisions

Claude Opus uses extended thinking for high-stakes validation:

```python
# src/llm/anthropic.py
async def create_message_with_thinking(
    self,
    messages: list[dict],
    max_tokens: int = 16000,
    thinking_budget: int = 10000,
) -> dict:
    """Use extended thinking for complex reasoning tasks."""
    response = await self.client.messages.create(
        model="claude-opus-4-5-20250514",
        max_tokens=max_tokens,
        thinking={
            "type": "enabled",
            "budget_tokens": thinking_budget
        },
        messages=messages,
    )
    return {
        "content": response.content[-1].text,
        "thinking": response.content[0].thinking,  # Internal reasoning trace
    }
```

### Message Compaction

Summarizes old messages when context grows too large:

```python
# src/llm/compactor.py
class MessageCompactor:
    def __init__(self, llm_router, threshold_ratio: float = 0.7):
        self.llm = llm_router
        self.threshold_ratio = threshold_ratio

    async def compact_if_needed(self, messages: list[dict], model: ModelTier) -> list[dict]:
        """Keep recent messages, summarize older ones when approaching limit."""
        if self._should_compact(messages, model):
            summary = await self._summarize(messages[:-10])
            return [{"role": "system", "content": f"Context: {summary}"}] + messages[-10:]
        return messages
```

### Multi-Level Fallback Chain

Automatic failover through model tiers:

```python
# src/llm/router.py
FALLBACK_CHAIN = {
    ModelTier.ORCHESTRATOR: [ModelTier.REASONING, ModelTier.GENERAL],
    ModelTier.REASONING: [ModelTier.GENERAL, ModelTier.FAST],
    ModelTier.CODING: [ModelTier.REASONING, ModelTier.GENERAL],
    ModelTier.GENERAL: [ModelTier.FAST],
    ModelTier.FAST: [],  # No fallback - last resort
}

FALLBACK_RETRY_DELAY_SECONDS = 0.5

async def route_with_fallback_chain(self, task: str, messages: list[dict], **kwargs):
    """Try primary model, then each fallback in chain."""
    model_tier = self.get_model_for_task(task)
    chain = [model_tier] + FALLBACK_CHAIN.get(model_tier, [])

    errors = []
    for tier in chain:
        for attempt in range(max_retries_per_tier):
            try:
                return await self._route_with_model(tier, messages, **kwargs)
            except Exception as e:
                errors.append({"tier": tier.name, "error": str(e)})
                await asyncio.sleep(FALLBACK_RETRY_DELAY_SECONDS)

    raise AllModelsFailedError(f"All models failed for {task}", errors)
```

### Error Pattern Detection

Aggregates similar errors for debugging:

```python
# src/utils/error_aggregator.py
class ErrorAggregator:
    def add(self, error: Exception, context: dict):
        """Record error with context."""

    def get_patterns(self, min_occurrences: int = 2) -> list[dict]:
        """Return errors that occurred multiple times (systemic issues)."""
        # Groups by (error_type, message_prefix)
        # Returns: [{"error_type": "TimeoutError", "count": 5, "contexts": [...]}]

    def get_summary(self) -> dict:
        """Return summary: total_errors, unique_types, patterns."""
```

### Parallel Bug Validation

Validates multiple bugs concurrently with semaphore-based rate limiting:

```python
# src/graph/parallel.py
async def parallel_validate_batch(
    bugs: list[Bug],
    llm_router: LLMRouter,
    session_id: str,
    batch_size: int = 5,
    use_extended_thinking: bool = False,
) -> list[dict]:
    """Validate bugs in parallel with semaphore control."""
    semaphore = asyncio.Semaphore(batch_size)

    async def validate_one(bug: Bug) -> dict:
        async with semaphore:
            if use_extended_thinking and bug.priority in ["critical", "high"]:
                return await validate_bug_with_thinking(bug.model_dump())
            return await validate_single_bug(bug, llm_router, session_id)

    return await asyncio.gather(*[validate_one(bug) for bug in bugs])
```

---

## Integration Tests

Integration tests verify all Sprint 2 components work together:

```
tests/integration/
├── test_agent_harness.py    # End-to-end agent workflow tests
├── test_checkpointing.py    # Crash recovery scenarios
└── test_fallback_chain.py   # Model failover tests
```

Key test coverage:
- Progress tracker persistence across restarts
- Token budget enforcement
- Message compaction triggering
- Fallback chain exhaustion
- Parallel validation concurrency
- Error pattern aggregation
