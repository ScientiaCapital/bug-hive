# Browser Module Integration Guide

## Overview
This guide shows how to integrate the browser automation layer into the BugHive crawler workflow.

## Quick Start

### 1. Install Dependencies
```bash
# Install project dependencies
pip install -e .

# Install Playwright browsers
playwright install chromium
```

### 2. Configure Environment
```bash
# .env file
BROWSERBASE_API_KEY=your-api-key-here
BROWSERBASE_PROJECT_ID=your-project-id-here
BROWSERBASE_TIMEOUT=300
```

### 3. Basic Usage

```python
from src.browser import BrowserbaseClient, PageExtractor, Navigator
from src.core.config import get_settings

async def crawl_page(url: str):
    """Simple page crawl example."""
    settings = get_settings()

    async with BrowserbaseClient(
        api_key=settings.BROWSERBASE_API_KEY,
        project_id=settings.BROWSERBASE_PROJECT_ID,
        timeout=settings.BROWSERBASE_TIMEOUT,
    ) as client:
        # Setup extractor
        extractor = PageExtractor(client.page, base_url=url)
        await extractor.setup_listeners()

        # Navigate
        await Navigator.navigate_with_human_behavior(client.page, url)
        await Navigator.dismiss_overlays(client.page)

        # Extract data
        data = await extractor.extract_all()
        screenshot = await client.screenshot(full_page=True)

        return data, screenshot
```

## Integration Patterns

### Pattern 1: Single Page Crawl with Evidence Collection

```python
from src.browser import BrowserbaseClient, PageExtractor, Navigator
from src.models.evidence import ConsoleLogEvidence, NetworkRequestEvidence, ScreenshotEvidence
from src.models.page import PageCreate, PageUpdate

async def crawl_and_collect_evidence(url: str, session_id: str):
    """Crawl page and collect evidence for bug detection."""
    settings = get_settings()

    async with BrowserbaseClient(
        api_key=settings.BROWSERBASE_API_KEY,
        project_id=settings.BROWSERBASE_PROJECT_ID,
    ) as client:
        # Setup
        extractor = PageExtractor(client.page, base_url=url)
        await extractor.setup_listeners()

        # Navigate
        result = await Navigator.navigate_with_human_behavior(client.page, url)
        await Navigator.dismiss_overlays(client.page, aggressive=True)

        # Extract data
        page_data = await extractor.extract_all()
        screenshot_bytes = await client.screenshot(full_page=True)

        # Create evidence objects
        evidence = []

        # Screenshot evidence
        screenshot_url = await upload_screenshot(screenshot_bytes)
        evidence.append(ScreenshotEvidence(
            type="screenshot",
            content=screenshot_url,
            metadata={"url": url, "full_page": True}
        ))

        # Console errors
        for error in extractor.get_console_errors():
            evidence.append(ConsoleLogEvidence(
                type="console_log",
                content=json.dumps(error),
                log_level="error",
                metadata={"source": error.get("location")}
            ))

        # Failed requests
        for req in extractor.get_failed_requests():
            evidence.append(NetworkRequestEvidence(
                type="network_request",
                content=json.dumps(req),
                status_code=req["status"],
                request_url=req["url"],
                request_method=req["method"]
            ))

        return {
            "page_data": page_data,
            "evidence": evidence,
            "has_issues": len(evidence) > 1,  # More than just screenshot
        }
```

### Pattern 2: Multi-Page Crawl with Session Rotation

```python
async def crawl_site(base_url: str, max_pages: int = 50):
    """Crawl multiple pages with session rotation."""
    settings = get_settings()

    client = BrowserbaseClient(
        api_key=settings.BROWSERBASE_API_KEY,
        project_id=settings.BROWSERBASE_PROJECT_ID,
    )

    pages_crawled = []
    urls_to_crawl = [base_url]
    urls_seen = set()

    try:
        await client.start_session()

        while urls_to_crawl and len(pages_crawled) < max_pages:
            # Check session rotation
            if await client.should_rotate_session():
                logger.info("rotating_session")
                await client.close()
                await client.start_session()

            # Get next URL
            url = urls_to_crawl.pop(0)
            if url in urls_seen:
                continue
            urls_seen.add(url)

            # Setup extractor
            extractor = PageExtractor(client.page, base_url=base_url)
            await extractor.setup_listeners()

            # Navigate and extract
            await Navigator.navigate_with_human_behavior(client.page, url)
            await Navigator.dismiss_overlays(client.page)

            page_data = await extractor.extract_all()

            # Find new links
            new_links = [
                link for link in page_data["links"]
                if link not in urls_seen
            ]
            urls_to_crawl.extend(new_links[:10])  # Limit breadth

            # Save page data
            pages_crawled.append({
                "url": url,
                "data": page_data,
                "links_found": len(new_links),
            })

            # Cleanup
            extractor.clear_data()

            logger.info(
                "page_crawled",
                url=url,
                total_crawled=len(pages_crawled),
                queue_size=len(urls_to_crawl),
            )

    finally:
        await client.close()

    return pages_crawled
```

### Pattern 3: Interactive Testing (Forms, Buttons)

```python
async def test_form_submission(url: str, form_data: dict):
    """Test form submission with validation."""
    settings = get_settings()

    async with BrowserbaseClient(
        api_key=settings.BROWSERBASE_API_KEY,
        project_id=settings.BROWSERBASE_PROJECT_ID,
    ) as client:
        extractor = PageExtractor(client.page)
        await extractor.setup_listeners()

        # Navigate
        await Navigator.navigate_with_human_behavior(client.page, url)
        await Navigator.dismiss_overlays(client.page)

        # Extract forms to validate structure
        forms = await extractor.extract_forms()
        target_form = next(
            (f for f in forms if f["id"] == form_data["form_id"]),
            None
        )

        if not target_form:
            raise ValueError(f"Form {form_data['form_id']} not found")

        # Fill form fields
        for field_name, field_value in form_data["fields"].items():
            selector = f"#{form_data['form_id']} [name='{field_name}']"
            await Navigator.fill_form(
                client.page,
                selector=selector,
                value=field_value,
                delay_between_chars=True,
            )

        # Take before screenshot
        before_screenshot = await client.screenshot(full_page=True)

        # Submit form
        submit_selector = f"#{form_data['form_id']} [type='submit']"
        await Navigator.click_element(
            client.page,
            selector=submit_selector,
            wait_for_navigation=True,
        )

        # Wait for response
        await asyncio.sleep(2)

        # Take after screenshot
        after_screenshot = await client.screenshot(full_page=True)

        # Check for errors
        page_data = await extractor.extract_all()
        console_errors = extractor.get_console_errors()
        failed_requests = extractor.get_failed_requests()

        return {
            "form": target_form,
            "submission_successful": len(console_errors) == 0,
            "console_errors": console_errors,
            "failed_requests": failed_requests,
            "before_screenshot": before_screenshot,
            "after_screenshot": after_screenshot,
            "final_url": client.page.url,
        }
```

### Pattern 4: Performance Testing

```python
async def test_page_performance(url: str, runs: int = 3):
    """Test page performance over multiple runs."""
    settings = get_settings()
    results = []

    for run in range(runs):
        async with BrowserbaseClient(
            api_key=settings.BROWSERBASE_API_KEY,
            project_id=settings.BROWSERBASE_PROJECT_ID,
        ) as client:
            extractor = PageExtractor(client.page)
            await extractor.setup_listeners()

            # Navigate without human delays for accurate timing
            start_time = time.time()
            await client.navigate(url, wait_until="load")
            navigation_time = time.time() - start_time

            # Extract performance metrics
            perf = await extractor.extract_performance_metrics()
            slow_requests = extractor.get_slow_requests(threshold_ms=500)

            results.append({
                "run": run + 1,
                "navigation_time": navigation_time,
                "load_time": perf.get("loadTime", 0),
                "dom_ready": perf.get("domReady", 0),
                "first_paint": perf.get("firstPaint", 0),
                "slow_requests": len(slow_requests),
                "total_requests": len(extractor._network_responses),
            })

            # Clear for next run
            extractor.clear_data()

    # Calculate averages
    avg_load_time = sum(r["load_time"] for r in results) / len(results)
    avg_dom_ready = sum(r["dom_ready"] for r in results) / len(results)

    return {
        "runs": results,
        "averages": {
            "load_time": avg_load_time,
            "dom_ready": avg_dom_ready,
        },
        "performance_grade": "good" if avg_load_time < 2000 else "slow",
    }
```

## Database Integration

### Storing Page Data

```python
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.page import Page, PageCreate, PageUpdate

async def save_crawl_results(
    db: AsyncSession,
    session_id: str,
    url: str,
    page_data: dict,
    screenshot_url: str,
):
    """Save crawl results to database."""
    # Create page record
    page_create = PageCreate(
        session_id=session_id,
        url=url,
        title=page_data["title"],
        status="crawling",
    )

    page = Page(**page_create.model_dump())
    db.add(page)
    await db.flush()

    # Update with crawl results
    page_update = PageUpdate(
        status="analyzed",
        screenshot_url=screenshot_url,
        crawled_at=datetime.utcnow(),
        response_time_ms=int(page_data["performance_metrics"].get("loadTime", 0)),
        status_code=200,
        analysis_result={
            "console_errors": len(page_data["console_logs"]),
            "failed_requests": len([
                r for r in page_data["network_requests"]
                if r["status"] >= 400
            ]),
            "forms_found": len(page_data["forms"]),
            "links_found": len(page_data["links"]),
        },
    )

    for key, value in page_update.model_dump(exclude_none=True).items():
        setattr(page, key, value)

    await db.commit()
    return page
```

## Error Handling

### Graceful Degradation

```python
from src.browser import BrowserbaseSessionError, NavigationError

async def crawl_with_retry(url: str, max_retries: int = 3):
    """Crawl with retry logic."""
    settings = get_settings()

    for attempt in range(max_retries):
        try:
            async with BrowserbaseClient(
                api_key=settings.BROWSERBASE_API_KEY,
                project_id=settings.BROWSERBASE_PROJECT_ID,
            ) as client:
                extractor = PageExtractor(client.page)
                await extractor.setup_listeners()

                await Navigator.navigate_with_human_behavior(client.page, url)
                await Navigator.dismiss_overlays(client.page)

                return await extractor.extract_all()

        except BrowserbaseSessionError as e:
            logger.error(
                "session_error",
                url=url,
                attempt=attempt + 1,
                error=str(e),
            )
            if attempt == max_retries - 1:
                raise

            # Wait before retry
            await asyncio.sleep(2 ** attempt)

        except NavigationError as e:
            logger.error(
                "navigation_error",
                url=url,
                attempt=attempt + 1,
                error=str(e),
            )
            if attempt == max_retries - 1:
                # Return partial data
                return {
                    "url": url,
                    "error": str(e),
                    "status": "error",
                }

            await asyncio.sleep(2 ** attempt)
```

## Testing

### Unit Tests
```bash
# Run all browser tests
pytest tests/browser/ -v

# Run with coverage
pytest tests/browser/ --cov=src/browser --cov-report=html
```

### Integration Tests
```bash
# Set environment variables
export BROWSERBASE_API_KEY=your-key
export BROWSERBASE_PROJECT_ID=your-project

# Run demo
python examples/browser_demo.py
```

## Best Practices

1. **Always use context managers**
   ```python
   async with BrowserbaseClient(...) as client:
       # Your code
       pass
   # Automatic cleanup
   ```

2. **Setup listeners before navigation**
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

4. **Clear extractor data between pages**
   ```python
   extractor.clear_data()  # Reset for next page
   ```

5. **Use structured logging**
   ```python
   logger.info("crawl_complete", url=url, errors=len(errors))
   ```

## Performance Tips

1. **Use appropriate wait strategies**
   - `domcontentloaded`: Fast, good for most cases
   - `networkidle`: Thorough, for dynamic content
   - `load`: Complete page load

2. **Limit concurrent sessions**
   - Browserbase has rate limits
   - Recommended: 2-5 concurrent sessions

3. **Batch operations**
   - Extract all data in one `extract_all()` call
   - Take screenshots after all interactions

4. **Session rotation**
   - Rotate every 20 pages
   - Prevents fingerprint staleness

## Next Steps

1. **Integrate with Crawler** - Use in main crawl workflow
2. **Add to LangGraph** - Browser node in agent graph
3. **Screenshot Storage** - Upload to S3/storage service
4. **Evidence Pipeline** - Process extracted evidence
5. **Bug Detection** - Analyze console errors and network failures
