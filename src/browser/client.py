"""Browserbase client for managing browser automation sessions.

This module provides a client for interacting with Browserbase's browser automation
service. It uses Playwright's Chrome DevTools Protocol (CDP) to connect to remote
browser instances hosted by Browserbase.

Key Features:
- WebSocket connection to Browserbase browsers
- Session management with automatic cleanup
- Smart navigation with configurable wait strategies
- Screenshot capture
- Session rotation for fresh fingerprints
"""

import time
from typing import Any, Literal

import httpx
import structlog
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = structlog.get_logger(__name__)


class BrowserbaseSessionError(Exception):
    """Raised when Browserbase session operations fail."""

    pass


class BrowserbaseClient:
    """Manages Browserbase browser sessions with Playwright.

    This client handles the creation and management of remote browser sessions
    through Browserbase's API. It uses Playwright to connect to browsers via
    Chrome DevTools Protocol (CDP).

    Attributes:
        api_key: Browserbase API key for authentication
        project_id: Browserbase project ID (optional)
        session_id: Current active session ID
        browser: Playwright browser instance
        context: Browser context (auto-created by Browserbase)
        page: Current page instance
    """

    # Browserbase API constants
    API_BASE_URL = "https://www.browserbase.com/v1"
    WS_BASE_URL = "wss://connect.browserbase.com"

    # Session management
    MAX_PAGES_PER_SESSION = 20  # Rotate session after this many pages for fresh fingerprints

    def __init__(
        self,
        api_key: str,
        project_id: str | None = None,
        timeout: int = 300,
    ) -> None:
        """Initialize Browserbase client.

        Args:
            api_key: Browserbase API key
            project_id: Optional project ID for session creation
            timeout: Session timeout in seconds (default: 300)
        """
        self.api_key = api_key
        self.project_id = project_id
        self.timeout = timeout

        # Session state
        self.session_id: str | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self._playwright: Any = None
        self._pages_count = 0

        logger.info(
            "browserbase_client_initialized",
            project_id=project_id,
            timeout=timeout,
        )

    async def start_session(self) -> str:
        """Create new browser session and connect via CDP.

        This method creates a new Browserbase session via API, then connects to it
        using Playwright's Chrome DevTools Protocol support.

        Returns:
            str: Session ID of the created session

        Raises:
            BrowserbaseSessionError: If session creation or connection fails
        """
        try:
            # Create session via Browserbase API
            session_data = await self._create_session_via_api()
            self.session_id = session_data["id"]

            logger.info(
                "browserbase_session_created",
                session_id=self.session_id,
                debug_url=session_data.get("debuggerUrl"),
            )

            # Connect to browser via WebSocket
            await self._connect_to_browser()

            # Get the auto-created page
            if self.context and self.context.pages:
                self.page = self.context.pages[0]
            else:
                # Create new page if none exists
                if self.context:
                    self.page = await self.context.new_page()

            logger.info(
                "browserbase_session_ready",
                session_id=self.session_id,
                page_count=len(self.context.pages) if self.context else 0,
            )

            return self.session_id

        except Exception as e:
            logger.error(
                "browserbase_session_start_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise BrowserbaseSessionError(f"Failed to start Browserbase session: {e}") from e

    async def _create_session_via_api(self) -> dict[str, Any]:
        """Create session via Browserbase REST API.

        Returns:
            dict: Session data including id, debuggerUrl, etc.

        Raises:
            BrowserbaseSessionError: If API request fails
        """
        url = f"{self.API_BASE_URL}/sessions"
        headers = {
            "x-bb-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "timeout": self.timeout,
        }

        if self.project_id:
            payload["projectId"] = self.project_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_detail = e.response.text if hasattr(e.response, "text") else str(e)
                logger.error(
                    "browserbase_api_error",
                    status_code=e.response.status_code,
                    error=error_detail,
                )
                raise BrowserbaseSessionError(
                    f"Browserbase API error ({e.response.status_code}): {error_detail}"
                ) from e
            except Exception as e:
                logger.error("browserbase_api_request_failed", error=str(e))
                raise BrowserbaseSessionError(f"Failed to create session: {e}") from e

    async def _connect_to_browser(self) -> None:
        """Connect to browser via Chrome DevTools Protocol.

        Raises:
            BrowserbaseSessionError: If connection fails
        """
        if not self.session_id:
            raise BrowserbaseSessionError("No session ID available for connection")

        # Build WebSocket endpoint URL
        ws_endpoint = f"{self.WS_BASE_URL}?apiKey={self.api_key}&sessionId={self.session_id}&enableProxy=true"

        try:
            # Initialize Playwright
            self._playwright = await async_playwright().start()

            # Connect to remote browser via CDP
            self.browser = await self._playwright.chromium.connect_over_cdp(ws_endpoint)

            # Get the default context (auto-created by Browserbase)
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
            else:
                raise BrowserbaseSessionError("No browser context available")

            logger.info(
                "browserbase_browser_connected",
                session_id=self.session_id,
                context_count=len(self.browser.contexts),
            )

        except Exception as e:
            logger.error(
                "browserbase_connection_failed",
                session_id=self.session_id,
                error=str(e),
            )
            raise BrowserbaseSessionError(f"Failed to connect to browser: {e}") from e

    async def navigate(
        self,
        url: str,
        wait_until: Literal["domcontentloaded", "networkidle", "load", "commit"] = "domcontentloaded",
    ) -> dict[str, Any]:
        """Navigate to URL with smart waiting.

        Args:
            url: Target URL to navigate to
            wait_until: Wait strategy (default: domcontentloaded)
                - domcontentloaded: Fast, waits for DOM
                - networkidle: Waits for network to be idle
                - load: Waits for load event
                - commit: Fastest, doesn't wait

        Returns:
            dict: Navigation result with status, url, title

        Raises:
            BrowserbaseSessionError: If navigation fails
        """
        if not self.page:
            raise BrowserbaseSessionError("No active page. Call start_session() first.")

        start_time = time.time()

        try:
            # Navigate to URL
            response = await self.page.goto(url, wait_until=wait_until, timeout=30000)

            # Increment page counter
            self._pages_count += 1

            navigation_time = time.time() - start_time

            result = {
                "status": response.status if response else None,
                "url": self.page.url,
                "title": await self.page.title(),
                "navigation_time_ms": int(navigation_time * 1000),
            }

            logger.info(
                "browserbase_navigation_complete",
                url=url,
                final_url=result["url"],
                status=result["status"],
                time_ms=result["navigation_time_ms"],
                pages_count=self._pages_count,
            )

            return result

        except Exception as e:
            logger.error(
                "browserbase_navigation_failed",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise BrowserbaseSessionError(f"Navigation to {url} failed: {e}") from e

    async def screenshot(
        self,
        full_page: bool = True,
        image_type: Literal["png", "jpeg"] = "png",
    ) -> bytes:
        """Capture screenshot of current page.

        Args:
            full_page: Capture full scrollable page (default: True)
            image_type: Image format - png or jpeg (default: png)

        Returns:
            bytes: Screenshot image data

        Raises:
            BrowserbaseSessionError: If screenshot capture fails
        """
        if not self.page:
            raise BrowserbaseSessionError("No active page. Call start_session() first.")

        try:
            screenshot_bytes = await self.page.screenshot(
                full_page=full_page,
                type=image_type,
            )

            logger.info(
                "browserbase_screenshot_captured",
                url=self.page.url,
                full_page=full_page,
                size_bytes=len(screenshot_bytes),
            )

            return screenshot_bytes

        except Exception as e:
            logger.error(
                "browserbase_screenshot_failed",
                url=self.page.url if self.page else None,
                error=str(e),
            )
            raise BrowserbaseSessionError(f"Screenshot capture failed: {e}") from e

    async def should_rotate_session(self) -> bool:
        """Check if session should be rotated for fresh fingerprints.

        Browserbase sessions should be rotated periodically to maintain
        anti-detection effectiveness.

        Returns:
            bool: True if session should be rotated
        """
        return self._pages_count >= self.MAX_PAGES_PER_SESSION

    async def close(self) -> None:
        """Clean up session and close browser connection.

        This method properly closes the browser connection and cleans up
        Playwright resources. Always call this when done with a session.
        """
        try:
            if self.browser:
                await self.browser.close()
                logger.info(
                    "browserbase_browser_closed",
                    session_id=self.session_id,
                    pages_processed=self._pages_count,
                )

            if self._playwright:
                await self._playwright.stop()

        except Exception as e:
            logger.warning(
                "browserbase_cleanup_warning",
                session_id=self.session_id,
                error=str(e),
            )
        finally:
            # Reset state
            self.session_id = None
            self.browser = None
            self.context = None
            self.page = None
            self._playwright = None
            self._pages_count = 0

    async def __aenter__(self) -> "BrowserbaseClient":
        """Async context manager entry."""
        await self.start_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
