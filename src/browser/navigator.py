"""Browser navigation with human-like behavior and anti-detection.

This module provides utilities for navigating web pages with human-like
behaviors including random delays, scrolling patterns, and overlay dismissal.
"""

import asyncio
import random
from typing import Literal

import structlog
from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

logger = structlog.get_logger(__name__)


class NavigationError(Exception):
    """Raised when navigation operations fail."""

    pass


class Navigator:
    """Handles page navigation with anti-detection and human behavior simulation.

    This class provides methods for navigating pages, filling forms, and
    interacting with elements in ways that mimic human behavior patterns
    to avoid detection.
    """

    # Timing constants for human-like behavior (in seconds)
    MIN_DELAY = 1.0
    MAX_DELAY = 2.5
    MIN_CHAR_DELAY_MS = 80
    MAX_CHAR_DELAY_MS = 200
    SCROLL_PAUSE_MIN = 0.5
    SCROLL_PAUSE_MAX = 1.5

    @staticmethod
    def _random_delay(min_seconds: float = MIN_DELAY, max_seconds: float = MAX_DELAY) -> float:
        """Generate random delay in seconds.

        Args:
            min_seconds: Minimum delay
            max_seconds: Maximum delay

        Returns:
            float: Random delay value
        """
        return random.uniform(min_seconds, max_seconds)

    @staticmethod
    async def _human_delay(min_seconds: float = MIN_DELAY, max_seconds: float = MAX_DELAY) -> None:
        """Sleep for random human-like duration.

        Args:
            min_seconds: Minimum delay in seconds
            max_seconds: Maximum delay in seconds
        """
        delay = Navigator._random_delay(min_seconds, max_seconds)
        logger.debug("human_delay", delay_seconds=delay)
        await asyncio.sleep(delay)

    @staticmethod
    async def navigate_with_human_behavior(
        page: Page,
        url: str,
        wait_until: Literal["domcontentloaded", "networkidle", "load"] = "domcontentloaded",
    ) -> bool:
        """Navigate to URL with human-like delays and scrolling.

        Args:
            page: Playwright Page instance
            url: Target URL
            wait_until: Wait strategy for navigation

        Returns:
            bool: True if navigation successful

        Raises:
            NavigationError: If navigation fails
        """
        try:
            # Random delay before navigation (simulate thinking time)
            await Navigator._human_delay(1.0, 2.5)

            logger.info("navigating_with_human_behavior", url=url, wait_until=wait_until)

            # Navigate to URL
            response = await page.goto(url, wait_until=wait_until, timeout=30000)

            if not response:
                raise NavigationError(f"No response received for {url}")

            # Wait for network to settle
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeoutError:
                logger.debug("networkidle_timeout", url=url)

            # Random scrolling to simulate reading
            await Navigator.random_scroll(page)

            logger.info(
                "navigation_complete",
                url=url,
                status=response.status,
                final_url=page.url,
            )

            return True

        except PlaywrightTimeoutError as e:
            logger.error("navigation_timeout", url=url, error=str(e))
            raise NavigationError(f"Navigation timeout for {url}: {e}") from e
        except Exception as e:
            logger.error("navigation_failed", url=url, error=str(e), error_type=type(e).__name__)
            raise NavigationError(f"Navigation to {url} failed: {e}") from e

    @staticmethod
    async def random_scroll(page: Page, num_scrolls: int = 3) -> None:
        """Perform random scrolling to simulate human reading behavior.

        Args:
            page: Playwright Page instance
            num_scrolls: Number of scroll actions to perform
        """
        try:
            for i in range(num_scrolls):
                # Random scroll amount (100-500 pixels)
                scroll_amount = random.randint(100, 500)

                # Scroll down
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")

                # Pause like human reading
                await Navigator._human_delay(
                    Navigator.SCROLL_PAUSE_MIN,
                    Navigator.SCROLL_PAUSE_MAX,
                )

            logger.debug("random_scroll_complete", scrolls=num_scrolls)

        except Exception as e:
            logger.warning("random_scroll_failed", error=str(e))

    @staticmethod
    async def fill_form(
        page: Page,
        selector: str,
        value: str,
        delay_between_chars: bool = True,
    ) -> bool:
        """Type into form field with character delays to simulate human typing.

        Args:
            page: Playwright Page instance
            selector: CSS selector for input field
            value: Value to type
            delay_between_chars: Add random delay between characters

        Returns:
            bool: True if successful

        Raises:
            NavigationError: If form filling fails
        """
        try:
            # Wait for element to be visible
            await page.wait_for_selector(selector, state="visible", timeout=5000)

            # Click to focus
            await page.click(selector)

            # Small delay after clicking
            await Navigator._human_delay(0.2, 0.5)

            if delay_between_chars:
                # Type with character delays
                for char in value:
                    await page.type(selector, char, delay=random.randint(
                        Navigator.MIN_CHAR_DELAY_MS,
                        Navigator.MAX_CHAR_DELAY_MS,
                    ))
            else:
                # Type all at once
                await page.fill(selector, value)

            logger.info("form_field_filled", selector=selector, length=len(value))
            return True

        except PlaywrightTimeoutError as e:
            logger.error("form_field_timeout", selector=selector, error=str(e))
            raise NavigationError(f"Form field not found: {selector}") from e
        except Exception as e:
            logger.error("form_fill_failed", selector=selector, error=str(e))
            raise NavigationError(f"Failed to fill form field {selector}: {e}") from e

    @staticmethod
    async def click_element(
        page: Page,
        selector: str,
        wait_for_navigation: bool = False,
    ) -> bool:
        """Click element with human-like behavior.

        Args:
            page: Playwright Page instance
            selector: CSS selector for element
            wait_for_navigation: Wait for navigation after click

        Returns:
            bool: True if successful

        Raises:
            NavigationError: If click fails
        """
        try:
            # Wait for element
            await page.wait_for_selector(selector, state="visible", timeout=5000)

            # Random delay before clicking
            await Navigator._human_delay(0.3, 0.8)

            if wait_for_navigation:
                # Click and wait for navigation
                async with page.expect_navigation(timeout=10000):
                    await page.click(selector)
            else:
                await page.click(selector)

            logger.info("element_clicked", selector=selector)
            return True

        except PlaywrightTimeoutError as e:
            logger.error("click_timeout", selector=selector, error=str(e))
            raise NavigationError(f"Element not found: {selector}") from e
        except Exception as e:
            logger.error("click_failed", selector=selector, error=str(e))
            raise NavigationError(f"Failed to click {selector}: {e}") from e

    @staticmethod
    async def dismiss_overlays(page: Page, aggressive: bool = True) -> bool:
        """Nuclear cookie/modal removal to clean up page.

        This method aggressively removes common overlays, modals, and popups
        that might interfere with testing.

        Args:
            page: Playwright Page instance
            aggressive: Use aggressive removal tactics

        Returns:
            bool: True if any overlays were dismissed
        """
        dismissed = False

        try:
            logger.info("dismissing_overlays", aggressive=aggressive)

            # Common cookie consent selectors
            cookie_selectors = [
                "button:has-text('Accept')",
                "button:has-text('Accept all')",
                "button:has-text('I accept')",
                "button:has-text('I agree')",
                "button:has-text('OK')",
                "button:has-text('Got it')",
                "[class*='cookie'] button",
                "[class*='consent'] button",
                "[id*='cookie'] button",
                "[id*='consent'] button",
            ]

            # Try clicking cookie consent buttons
            for selector in cookie_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements[:1]:  # Only click first match
                        if await element.is_visible():
                            await element.click(timeout=1000)
                            dismissed = True
                            logger.info("cookie_button_clicked", selector=selector)
                            await asyncio.sleep(0.5)
                            break
                except Exception:
                    pass

            if aggressive:
                # Nuclear option: Remove common overlay elements via CSS injection
                await page.add_style_tag(content="""
                    [class*='modal'],
                    [class*='popup'],
                    [class*='overlay'],
                    [class*='cookie'],
                    [class*='consent'],
                    [id*='modal'],
                    [id*='popup'],
                    [id*='overlay'],
                    [id*='cookie'],
                    [id*='consent'] {
                        display: none !important;
                        pointer-events: none !important;
                    }
                    body {
                        overflow: auto !important;
                    }
                """)

                # Remove elements directly from DOM
                removed_count = await page.evaluate("""
                    () => {
                        const selectors = [
                            '[class*="modal"]',
                            '[class*="popup"]',
                            '[class*="overlay"]',
                            '[class*="cookie"]',
                            '[class*="consent"]',
                            '[id*="modal"]',
                            '[id*="popup"]',
                            '[id*="overlay"]'
                        ];

                        let count = 0;
                        for (const selector of selectors) {
                            const elements = document.querySelectorAll(selector);
                            elements.forEach(el => {
                                // Only remove if it's taking up significant screen space
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 200 || rect.height > 200) {
                                    el.remove();
                                    count++;
                                }
                            });
                        }

                        // Re-enable body scrolling
                        document.body.style.overflow = 'auto';

                        return count;
                    }
                """)

                if removed_count > 0:
                    dismissed = True
                    logger.info("overlays_removed", count=removed_count)

            # Wait a moment for page to stabilize
            await asyncio.sleep(0.5)

            logger.info("overlay_dismissal_complete", dismissed=dismissed)
            return dismissed

        except Exception as e:
            logger.warning("overlay_dismissal_failed", error=str(e))
            return dismissed

    @staticmethod
    async def wait_for_element(
        page: Page,
        selector: str,
        timeout_ms: int = 5000,
        state: Literal["attached", "detached", "visible", "hidden"] = "visible",
    ) -> bool:
        """Wait for element to reach specified state.

        Args:
            page: Playwright Page instance
            selector: CSS selector
            timeout_ms: Timeout in milliseconds
            state: Element state to wait for

        Returns:
            bool: True if element reached desired state

        Raises:
            NavigationError: If timeout occurs
        """
        try:
            await page.wait_for_selector(selector, state=state, timeout=timeout_ms)
            logger.debug("element_ready", selector=selector, state=state)
            return True

        except PlaywrightTimeoutError as e:
            logger.error(
                "wait_for_element_timeout",
                selector=selector,
                state=state,
                timeout_ms=timeout_ms,
            )
            raise NavigationError(
                f"Element {selector} did not reach {state} state within {timeout_ms}ms"
            ) from e

    @staticmethod
    async def hover_element(page: Page, selector: str) -> bool:
        """Hover over element with human-like behavior.

        Args:
            page: Playwright Page instance
            selector: CSS selector for element

        Returns:
            bool: True if successful

        Raises:
            NavigationError: If hover fails
        """
        try:
            # Wait for element
            await page.wait_for_selector(selector, state="visible", timeout=5000)

            # Random delay before hovering
            await Navigator._human_delay(0.2, 0.6)

            # Hover
            await page.hover(selector)

            logger.debug("element_hovered", selector=selector)
            return True

        except PlaywrightTimeoutError as e:
            logger.error("hover_timeout", selector=selector, error=str(e))
            raise NavigationError(f"Element not found: {selector}") from e
        except Exception as e:
            logger.error("hover_failed", selector=selector, error=str(e))
            raise NavigationError(f"Failed to hover {selector}: {e}") from e

    @staticmethod
    async def select_option(
        page: Page,
        selector: str,
        value: str | None = None,
        label: str | None = None,
    ) -> bool:
        """Select option from dropdown.

        Args:
            page: Playwright Page instance
            selector: CSS selector for select element
            value: Option value to select
            label: Option label text to select

        Returns:
            bool: True if successful

        Raises:
            NavigationError: If selection fails
        """
        try:
            # Wait for select element
            await page.wait_for_selector(selector, state="visible", timeout=5000)

            # Random delay before selecting
            await Navigator._human_delay(0.3, 0.7)

            # Select option
            if value is not None:
                await page.select_option(selector, value=value)
            elif label is not None:
                await page.select_option(selector, label=label)
            else:
                raise ValueError("Either value or label must be provided")

            logger.info("option_selected", selector=selector, value=value, label=label)
            return True

        except PlaywrightTimeoutError as e:
            logger.error("select_timeout", selector=selector, error=str(e))
            raise NavigationError(f"Select element not found: {selector}") from e
        except Exception as e:
            logger.error("select_failed", selector=selector, error=str(e))
            raise NavigationError(f"Failed to select option in {selector}: {e}") from e
