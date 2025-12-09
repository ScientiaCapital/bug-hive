"""Browser automation layer for BugHive.

This package provides browser automation capabilities using Browserbase and Playwright.
It includes tools for session management, page data extraction, and human-like navigation
with anti-detection features.

Main Components:
- BrowserbaseClient: Manages remote browser sessions via Browserbase
- PageExtractor: Extracts comprehensive data from web pages
- Navigator: Provides human-like navigation and interaction patterns

Example Usage:
    ```python
    from browser import BrowserbaseClient, PageExtractor, Navigator

    async def crawl_page(url: str):
        # Create client
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

            # Dismiss overlays
            await Navigator.dismiss_overlays(client.page)

            # Extract data
            data = await extractor.extract_all()

            # Capture screenshot
            screenshot = await client.screenshot(full_page=True)

            return data, screenshot

        finally:
            await client.close()
    ```
"""

from src.browser.client import BrowserbaseClient, BrowserbaseSessionError
from src.browser.extractor import PageExtractor
from src.browser.navigator import NavigationError, Navigator

__all__ = [
    # Client
    "BrowserbaseClient",
    "BrowserbaseSessionError",
    # Extractor
    "PageExtractor",
    # Navigator
    "Navigator",
    "NavigationError",
]
