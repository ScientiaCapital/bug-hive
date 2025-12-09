"""Page data extraction from browser pages.

This module provides utilities for extracting various types of data from
browser pages including console logs, network requests, forms, links, and
performance metrics.
"""

import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import structlog
from playwright.async_api import Page, Response

logger = structlog.get_logger(__name__)


class PageExtractor:
    """Extracts comprehensive data from browser pages.

    This class sets up listeners and extracts various types of data from
    web pages including console logs, network requests, DOM elements,
    and performance metrics.

    Attributes:
        page: Playwright Page instance
        base_url: Base URL for filtering internal links
    """

    def __init__(self, page: Page, base_url: str | None = None) -> None:
        """Initialize page extractor.

        Args:
            page: Playwright Page instance
            base_url: Base URL for internal link filtering (uses page.url if None)
        """
        self.page = page
        self.base_url = base_url

        # Storage for captured data
        self._console_logs: list[dict[str, Any]] = []
        self._network_responses: list[dict[str, Any]] = []
        self._network_errors: list[dict[str, Any]] = []
        self._start_time = time.time()

    async def setup_listeners(self) -> None:
        """Set up console and network listeners before navigation.

        This must be called before navigating to capture all events.
        """
        # Console listener
        self.page.on("console", self._handle_console)

        # Network response listener
        self.page.on("response", self._handle_response)

        # Network request failure listener
        self.page.on("requestfailed", self._handle_request_failed)

        logger.debug("page_listeners_setup", url=self.page.url)

    def _handle_console(self, msg: Any) -> None:
        """Handle console messages."""
        try:
            log_entry = {
                "level": msg.type,
                "text": msg.text,
                "timestamp": datetime.utcnow().isoformat(),
                "location": msg.location if hasattr(msg, "location") else None,
            }
            self._console_logs.append(log_entry)

            # Log errors and warnings
            if msg.type in ("error", "warning"):
                logger.info(
                    "console_message",
                    level=msg.type,
                    text=msg.text[:200],  # Truncate long messages
                )
        except Exception as e:
            logger.warning("console_handler_error", error=str(e))

    def _handle_response(self, response: Response) -> None:
        """Handle network responses."""
        try:
            # Calculate timing if possible
            timing = None
            try:
                timing_info = response.request.timing
                if timing_info:
                    timing = {
                        "dns": timing_info.get("domainLookupEnd", 0) - timing_info.get("domainLookupStart", 0),
                        "connect": timing_info.get("connectEnd", 0) - timing_info.get("connectStart", 0),
                        "request": timing_info.get("requestStart", 0),
                        "response": timing_info.get("responseStart", 0),
                        "total": timing_info.get("responseEnd", 0),
                    }
            except Exception:
                pass

            response_entry = {
                "url": response.url,
                "status": response.status,
                "method": response.request.method,
                "resource_type": response.request.resource_type,
                "timestamp": datetime.utcnow().isoformat(),
                "timing": timing,
                "headers": dict(response.headers) if hasattr(response, "headers") else {},
            }
            self._network_responses.append(response_entry)

            # Log non-200 responses
            if response.status >= 400:
                logger.info(
                    "network_error_response",
                    url=response.url[:100],
                    status=response.status,
                    method=response.request.method,
                )
        except Exception as e:
            logger.warning("response_handler_error", error=str(e))

    def _handle_request_failed(self, request: Any) -> None:
        """Handle failed network requests."""
        try:
            error_entry = {
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "failure": request.failure,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self._network_errors.append(error_entry)

            logger.info(
                "network_request_failed",
                url=request.url[:100],
                failure=request.failure,
            )
        except Exception as e:
            logger.warning("request_failed_handler_error", error=str(e))

    async def extract_forms(self) -> list[dict[str, Any]]:
        """Extract all forms from the page.

        Returns:
            list: Form data including inputs, actions, methods
        """
        try:
            forms_data = await self.page.evaluate("""
                () => {
                    return Array.from(document.forms).map(form => {
                        const inputs = Array.from(form.elements).map(el => {
                            const input = {
                                name: el.name || '',
                                type: el.type || '',
                                id: el.id || '',
                                required: el.required || false,
                                tagName: el.tagName.toLowerCase(),
                            };

                            // Add placeholder if exists
                            if (el.placeholder) {
                                input.placeholder = el.placeholder;
                            }

                            // Add options for select elements
                            if (el.tagName.toLowerCase() === 'select') {
                                input.options = Array.from(el.options).map(opt => ({
                                    value: opt.value,
                                    text: opt.text,
                                }));
                            }

                            return input;
                        });

                        return {
                            id: form.id || '',
                            name: form.name || '',
                            action: form.action || '',
                            method: form.method || 'get',
                            target: form.target || '',
                            inputCount: inputs.length,
                            inputs: inputs,
                        };
                    });
                }
            """)

            logger.debug("forms_extracted", count=len(forms_data))
            return forms_data

        except Exception as e:
            logger.error("form_extraction_failed", error=str(e))
            return []

    async def extract_links(self, internal_only: bool = True) -> list[str]:
        """Extract links from the page.

        Args:
            internal_only: Only return internal links (same origin)

        Returns:
            list: List of URLs
        """
        try:
            # Get base URL for filtering
            base_url = self.base_url or self.page.url
            parsed_base = urlparse(base_url)
            origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

            # Extract all links
            all_links = await self.page.evaluate("""
                () => {
                    return Array.from(document.querySelectorAll('a[href]'))
                        .map(a => a.href)
                        .filter(href => href && !href.startsWith('javascript:') && !href.startsWith('#'));
                }
            """)

            # Filter internal links if requested
            if internal_only:
                links = [link for link in all_links if link.startswith(origin)]
            else:
                links = all_links

            # Deduplicate
            unique_links = list(set(links))

            logger.debug(
                "links_extracted",
                total=len(all_links),
                internal=len(unique_links),
                internal_only=internal_only,
            )

            return unique_links

        except Exception as e:
            logger.error("link_extraction_failed", error=str(e))
            return []

    async def extract_performance_metrics(self) -> dict[str, Any]:
        """Extract performance metrics using Navigation Timing API.

        Returns:
            dict: Performance metrics including load times
        """
        try:
            metrics = await self.page.evaluate("""
                () => {
                    const perfData = performance.getEntriesByType('navigation')[0];
                    const paintData = performance.getEntriesByType('paint');

                    const result = {
                        loadTime: perfData ? perfData.loadEventEnd - perfData.fetchStart : 0,
                        domReady: perfData ? perfData.domContentLoadedEventEnd - perfData.fetchStart : 0,
                        firstPaint: 0,
                        largestPaint: 0,
                        dns: perfData ? perfData.domainLookupEnd - perfData.domainLookupStart : 0,
                        tcp: perfData ? perfData.connectEnd - perfData.connectStart : 0,
                        request: perfData ? perfData.responseStart - perfData.requestStart : 0,
                        response: perfData ? perfData.responseEnd - perfData.responseStart : 0,
                        domProcessing: perfData ? perfData.domComplete - perfData.domLoading : 0,
                    };

                    // Get paint timings
                    for (const entry of paintData) {
                        if (entry.name === 'first-paint') {
                            result.firstPaint = entry.startTime;
                        } else if (entry.name === 'first-contentful-paint') {
                            result.largestPaint = entry.startTime;
                        }
                    }

                    return result;
                }
            """)

            logger.debug("performance_metrics_extracted", load_time=metrics.get("loadTime"))
            return metrics

        except Exception as e:
            logger.error("performance_extraction_failed", error=str(e))
            return {}

    async def extract_meta_tags(self) -> dict[str, str]:
        """Extract meta tags from page head.

        Returns:
            dict: Meta tag key-value pairs
        """
        try:
            meta_tags = await self.page.evaluate("""
                () => {
                    const metas = {};
                    document.querySelectorAll('meta').forEach(meta => {
                        const name = meta.getAttribute('name') || meta.getAttribute('property') || meta.getAttribute('http-equiv');
                        const content = meta.getAttribute('content');
                        if (name && content) {
                            metas[name] = content;
                        }
                    });
                    return metas;
                }
            """)

            logger.debug("meta_tags_extracted", count=len(meta_tags))
            return meta_tags

        except Exception as e:
            logger.error("meta_tag_extraction_failed", error=str(e))
            return {}

    async def extract_all(self) -> dict[str, Any]:
        """Extract all relevant data from current page.

        Returns:
            dict: Comprehensive page data including all extracted information
        """
        logger.info("extracting_page_data", url=self.page.url)

        # Extract all data in parallel
        forms = await self.extract_forms()
        links = await self.extract_links(internal_only=True)
        performance = await self.extract_performance_metrics()
        meta_tags = await self.extract_meta_tags()

        # Build result
        result = {
            "url": self.page.url,
            "title": await self.page.title(),
            "console_logs": self._console_logs.copy(),
            "network_requests": self._network_responses.copy(),
            "network_errors": self._network_errors.copy(),
            "forms": forms,
            "links": links,
            "performance_metrics": performance,
            "meta_tags": meta_tags,
            "extraction_time": time.time() - self._start_time,
        }

        logger.info(
            "page_data_extracted",
            url=self.page.url,
            console_logs=len(result["console_logs"]),
            network_requests=len(result["network_requests"]),
            network_errors=len(result["network_errors"]),
            forms=len(result["forms"]),
            links=len(result["links"]),
        )

        return result

    def get_console_errors(self) -> list[dict[str, Any]]:
        """Get all console error messages.

        Returns:
            list: Console errors
        """
        return [log for log in self._console_logs if log["level"] == "error"]

    def get_console_warnings(self) -> list[dict[str, Any]]:
        """Get all console warning messages.

        Returns:
            list: Console warnings
        """
        return [log for log in self._console_logs if log["level"] == "warning"]

    def get_failed_requests(self) -> list[dict[str, Any]]:
        """Get all failed network requests (4xx, 5xx).

        Returns:
            list: Failed requests
        """
        return [
            req for req in self._network_responses
            if req["status"] >= 400
        ]

    def get_slow_requests(self, threshold_ms: int = 1000) -> list[dict[str, Any]]:
        """Get network requests slower than threshold.

        Args:
            threshold_ms: Threshold in milliseconds (default: 1000)

        Returns:
            list: Slow requests
        """
        slow = []
        for req in self._network_responses:
            if req.get("timing") and req["timing"].get("total", 0) > threshold_ms:
                slow.append(req)
        return slow

    def clear_data(self) -> None:
        """Clear all captured data."""
        self._console_logs.clear()
        self._network_responses.clear()
        self._network_errors.clear()
        self._start_time = time.time()
        logger.debug("extractor_data_cleared")
