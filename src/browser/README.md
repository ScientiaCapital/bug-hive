# Browser Automation Layer

This module provides comprehensive browser automation capabilities for BugHive using Browserbase and Playwright.

## Components

### 1. BrowserbaseClient (`client.py`)

Manages remote browser sessions through Browserbase's API.

**Features:**
- WebSocket connection to Browserbase browsers via Chrome DevTools Protocol (CDP)
- Automatic session creation and management
- Smart navigation with configurable wait strategies
- Screenshot capture (full page or viewport)
- Session rotation after 20 pages for fresh fingerprints
- Comprehensive error handling and logging

**Usage:**
```python
from browser import BrowserbaseClient

async def example():
    client = BrowserbaseClient(
        api_key="your-api-key",
        project_id="your-project-id",
        timeout=300
    )

    try:
        # Start session
        session_id = await client.start_session()

        # Navigate
        result = await client.navigate(
            "https://example.com",
            wait_until="domcontentloaded"
        )

        # Take screenshot
        screenshot_bytes = await client.screenshot(full_page=True)

        # Check if rotation needed
        if await client.should_rotate_session():
            await client.close()
            await client.start_session()

    finally:
        await client.close()

# Or use as context manager
async with BrowserbaseClient(api_key, project_id) as client:
    await client.navigate("https://example.com")
```

### 2. PageExtractor (`extractor.py`)

Extracts comprehensive data from web pages including console logs, network requests, forms, links, and performance metrics.

**Features:**
- Console log capture (errors, warnings, info, debug)
- Network request/response monitoring
- Form extraction with input details
- Internal link discovery
- Performance metrics (Navigation Timing API)
- Meta tag extraction
- Automatic data aggregation

**Usage:**
```python
from browser import PageExtractor

async def extract_page_data(page):
    # Create extractor
    extractor = PageExtractor(page, base_url="https://example.com")

    # Setup listeners BEFORE navigation
    await extractor.setup_listeners()

    # Navigate to page
    await page.goto("https://example.com/page")

    # Extract all data
    data = await extractor.extract_all()

    # Access specific data
    console_errors = extractor.get_console_errors()
    failed_requests = extractor.get_failed_requests()
    slow_requests = extractor.get_slow_requests(threshold_ms=1000)

    return data
```

**Extracted Data Structure:**
```python
{
    "url": "https://example.com/page",
    "title": "Page Title",
    "console_logs": [
        {
            "level": "error",
            "text": "TypeError: ...",
            "timestamp": "2024-01-15T10:30:00Z",
            "location": "app.js:42"
        }
    ],
    "network_requests": [
        {
            "url": "https://api.example.com/data",
            "status": 200,
            "method": "GET",
            "resource_type": "fetch",
            "timing": {...}
        }
    ],
    "forms": [
        {
            "id": "login-form",
            "action": "/login",
            "method": "post",
            "inputs": [...]
        }
    ],
    "links": ["https://example.com/about", ...],
    "performance_metrics": {
        "loadTime": 1234,
        "domReady": 890,
        "firstPaint": 456
    },
    "meta_tags": {...}
}
```

### 3. Navigator (`navigator.py`)

Provides human-like navigation patterns and anti-detection behaviors.

**Features:**
- Random delays between actions (1-2.5s)
- Human-like scrolling patterns
- Character-by-character typing with random delays (80-200ms)
- Aggressive overlay/modal dismissal
- Cookie consent auto-acceptance
- Element interaction with natural timing

**Usage:**
```python
from browser import Navigator

async def navigate_like_human(page):
    # Navigate with human behavior
    await Navigator.navigate_with_human_behavior(
        page,
        "https://example.com",
        wait_until="domcontentloaded"
    )

    # Dismiss overlays
    await Navigator.dismiss_overlays(page, aggressive=True)

    # Fill form with typing simulation
    await Navigator.fill_form(
        page,
        selector="#email",
        value="test@example.com",
        delay_between_chars=True
    )

    # Click element
    await Navigator.click_element(
        page,
        selector="button[type='submit']",
        wait_for_navigation=True
    )

    # Random scrolling
    await Navigator.random_scroll(page, num_scrolls=3)
```

## Complete Example

```python
from browser import BrowserbaseClient, PageExtractor, Navigator

async def crawl_and_analyze(url: str):
    """Complete crawl and analysis workflow."""

    client = BrowserbaseClient(
        api_key="your-api-key",
        project_id="your-project-id"
    )

    try:
        # Start session
        await client.start_session()

        # Set up extractor
        extractor = PageExtractor(client.page, base_url=url)
        await extractor.setup_listeners()

        # Navigate with human behavior
        await Navigator.navigate_with_human_behavior(
            client.page,
            url,
            wait_until="domcontentloaded"
        )

        # Clean up overlays
        await Navigator.dismiss_overlays(client.page, aggressive=True)

        # Extract comprehensive data
        page_data = await extractor.extract_all()

        # Capture screenshot
        screenshot = await client.screenshot(full_page=True)

        # Check for issues
        console_errors = extractor.get_console_errors()
        failed_requests = extractor.get_failed_requests()

        return {
            "page_data": page_data,
            "screenshot": screenshot,
            "issues": {
                "console_errors": console_errors,
                "failed_requests": failed_requests
            }
        }

    finally:
        await client.close()
```

## Anti-Detection Features

### Session Rotation
- Sessions rotate every 20 pages for fresh browser fingerprints
- Prevents tracking and detection by target sites

### Human-like Behavior
- Random delays (1-2.5s) between actions
- Natural scrolling patterns with pauses
- Character-by-character typing with variable speed
- Mouse movement simulation via hover

### Overlay Handling
- Automatic cookie consent acceptance
- Aggressive modal/popup removal
- CSS injection to disable pointer events
- DOM element removal for persistent overlays

## Configuration

Environment variables (via `src/core/config.py`):
- `BROWSERBASE_API_KEY`: Browserbase API key (required)
- `BROWSERBASE_PROJECT_ID`: Browserbase project ID (required)
- `BROWSERBASE_TIMEOUT`: Session timeout in seconds (default: 300)

## Error Handling

All modules use custom exceptions for clear error handling:

```python
from browser import BrowserbaseSessionError, NavigationError

try:
    await client.start_session()
    await Navigator.navigate_with_human_behavior(page, url)
except BrowserbaseSessionError as e:
    # Handle session errors
    logger.error("Session failed", error=str(e))
except NavigationError as e:
    # Handle navigation errors
    logger.error("Navigation failed", error=str(e))
```

## Logging

All components use `structlog` for structured logging:

```python
import structlog

logger = structlog.get_logger(__name__)

# Logs include context
logger.info(
    "navigation_complete",
    url=url,
    status=response.status,
    final_url=page.url
)
```

## Best Practices

1. **Always use context managers or try/finally**
   ```python
   async with BrowserbaseClient(api_key, project_id) as client:
       # Your code here
       pass
   # Automatic cleanup
   ```

2. **Set up listeners before navigation**
   ```python
   extractor = PageExtractor(page)
   await extractor.setup_listeners()  # BEFORE goto
   await page.goto(url)
   ```

3. **Rotate sessions for long crawls**
   ```python
   if await client.should_rotate_session():
       await client.close()
       await client.start_session()
   ```

4. **Handle timeouts gracefully**
   ```python
   try:
       await Navigator.wait_for_element(page, selector, timeout_ms=5000)
   except NavigationError:
       logger.warning("Element not found", selector=selector)
       # Continue with alternative flow
   ```

5. **Clear extractor data between pages**
   ```python
   extractor.clear_data()  # Reset for next page
   ```

## Testing

Run tests with pytest:
```bash
pytest tests/browser/ -v
```

For integration tests with real Browserbase:
```bash
pytest tests/browser/integration/ -v --browserbase
```

## Dependencies

- `playwright>=1.40.0` - Browser automation
- `httpx>=0.26.0` - HTTP client for Browserbase API
- `structlog>=24.1.0` - Structured logging
- `pydantic>=2.5.0` - Data validation

## Installation

Playwright requires browser installation:
```bash
# Install dependencies
pip install -e .

# Install Playwright browsers
playwright install chromium
```
