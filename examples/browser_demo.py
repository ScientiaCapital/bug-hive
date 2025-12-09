"""Browser automation demo script.

This example demonstrates how to use the browser automation layer to crawl
a website and extract comprehensive data.

Requirements:
    - BROWSERBASE_API_KEY environment variable
    - BROWSERBASE_PROJECT_ID environment variable
"""

import asyncio
import json
import os
from pathlib import Path

import structlog

from src.browser import BrowserbaseClient, Navigator, PageExtractor

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging_level=20),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger(__name__)


async def crawl_single_page(url: str) -> dict:
    """Crawl a single page and extract all data.

    Args:
        url: Target URL to crawl

    Returns:
        dict: Extracted page data and metadata
    """
    # Get credentials from environment
    api_key = os.getenv("BROWSERBASE_API_KEY")
    project_id = os.getenv("BROWSERBASE_PROJECT_ID")

    if not api_key or not project_id:
        raise ValueError(
            "BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID must be set in environment"
        )

    logger.info("starting_crawl", url=url)

    # Create client
    client = BrowserbaseClient(
        api_key=api_key,
        project_id=project_id,
        timeout=300,
    )

    try:
        # Start browser session
        session_id = await client.start_session()
        logger.info("session_started", session_id=session_id)

        # Set up page extractor
        extractor = PageExtractor(client.page, base_url=url)
        await extractor.setup_listeners()

        # Navigate with human-like behavior
        await Navigator.navigate_with_human_behavior(
            client.page,
            url,
            wait_until="domcontentloaded",
        )

        # Dismiss overlays (cookie consents, modals, etc.)
        overlays_dismissed = await Navigator.dismiss_overlays(
            client.page,
            aggressive=True,
        )
        logger.info("overlays_dismissed", dismissed=overlays_dismissed)

        # Wait a moment for page to stabilize
        await asyncio.sleep(2)

        # Extract all data
        page_data = await extractor.extract_all()

        # Capture screenshot
        screenshot_bytes = await client.screenshot(full_page=True)

        # Get specific issues
        console_errors = extractor.get_console_errors()
        console_warnings = extractor.get_console_warnings()
        failed_requests = extractor.get_failed_requests()
        slow_requests = extractor.get_slow_requests(threshold_ms=1000)

        logger.info(
            "crawl_complete",
            url=url,
            console_errors=len(console_errors),
            console_warnings=len(console_warnings),
            failed_requests=len(failed_requests),
            slow_requests=len(slow_requests),
            forms_found=len(page_data["forms"]),
            links_found=len(page_data["links"]),
        )

        return {
            "session_id": session_id,
            "page_data": page_data,
            "screenshot_size": len(screenshot_bytes),
            "issues": {
                "console_errors": console_errors,
                "console_warnings": console_warnings,
                "failed_requests": failed_requests,
                "slow_requests": slow_requests,
            },
        }

    finally:
        # Always clean up
        await client.close()
        logger.info("session_closed")


async def crawl_multiple_pages(urls: list[str]) -> list[dict]:
    """Crawl multiple pages with session rotation.

    Args:
        urls: List of URLs to crawl

    Returns:
        list: Extracted data for each page
    """
    # Get credentials
    api_key = os.getenv("BROWSERBASE_API_KEY")
    project_id = os.getenv("BROWSERBASE_PROJECT_ID")

    if not api_key or not project_id:
        raise ValueError(
            "BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID must be set in environment"
        )

    logger.info("starting_multi_page_crawl", page_count=len(urls))

    # Create client
    client = BrowserbaseClient(
        api_key=api_key,
        project_id=project_id,
        timeout=300,
    )

    results = []

    try:
        # Start initial session
        await client.start_session()

        for idx, url in enumerate(urls):
            logger.info("crawling_page", index=idx + 1, total=len(urls), url=url)

            # Check if we should rotate session
            if await client.should_rotate_session():
                logger.info("rotating_session")
                await client.close()
                await client.start_session()

            # Set up extractor
            extractor = PageExtractor(client.page, base_url=url)
            await extractor.setup_listeners()

            # Navigate
            await Navigator.navigate_with_human_behavior(
                client.page,
                url,
                wait_until="domcontentloaded",
            )

            # Dismiss overlays
            await Navigator.dismiss_overlays(client.page, aggressive=True)

            # Extract data
            page_data = await extractor.extract_all()

            # Take screenshot
            screenshot = await client.screenshot(full_page=True)

            results.append({
                "url": url,
                "page_data": page_data,
                "screenshot_size": len(screenshot),
                "issues": {
                    "console_errors": extractor.get_console_errors(),
                    "failed_requests": extractor.get_failed_requests(),
                },
            })

            # Clear extractor for next page
            extractor.clear_data()

            logger.info("page_complete", index=idx + 1, total=len(urls))

    finally:
        await client.close()
        logger.info("multi_page_crawl_complete", pages_crawled=len(results))

    return results


async def main():
    """Main demo function."""
    # Example 1: Single page crawl
    logger.info("=== Example 1: Single Page Crawl ===")
    result = await crawl_single_page("https://example.com")

    # Save results
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / "page_data.json", "w") as f:
        json.dump(result["page_data"], f, indent=2, default=str)

    logger.info("results_saved", file="output/page_data.json")

    # Print summary
    print("\n=== Crawl Summary ===")
    print(f"URL: {result['page_data']['url']}")
    print(f"Title: {result['page_data']['title']}")
    print(f"Console Errors: {len(result['issues']['console_errors'])}")
    print(f"Console Warnings: {len(result['issues']['console_warnings'])}")
    print(f"Failed Requests: {len(result['issues']['failed_requests'])}")
    print(f"Slow Requests: {len(result['issues']['slow_requests'])}")
    print(f"Forms Found: {len(result['page_data']['forms'])}")
    print(f"Links Found: {len(result['page_data']['links'])}")
    print(f"Screenshot Size: {result['screenshot_size']:,} bytes")

    # Example 2: Multiple pages (commented out by default)
    # logger.info("=== Example 2: Multiple Pages ===")
    # urls = [
    #     "https://example.com",
    #     "https://example.com/about",
    #     "https://example.com/contact",
    # ]
    # results = await crawl_multiple_pages(urls)
    # logger.info("multi_crawl_complete", pages=len(results))


if __name__ == "__main__":
    asyncio.run(main())
