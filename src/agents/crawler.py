"""Crawler Agent for autonomous web application discovery."""

import asyncio
import json
import random
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog

from src.browser import BrowserbaseClient, Navigator, PageExtractor
from src.llm import LLMRouter
from src.models.crawl import AuthMethod, CrawlConfig, PageInventory
from src.models.page import Page
from src.agents.prompts.crawler import (
    ANALYZE_AUTH_PAGE,
    EXTRACT_NAVIGATION_CONTEXT,
    PLAN_CRAWL_STRATEGY,
    SHOULD_CRAWL,
)

logger = structlog.get_logger(__name__)


class CrawlerAgent:
    """Agent for crawling web applications and discovering pages."""

    def __init__(
        self,
        browser_client: BrowserbaseClient,
        llm_router: LLMRouter,
        config: CrawlConfig,
    ):
        """Initialize the Crawler Agent.

        Args:
            browser_client: Browser automation client
            llm_router: LLM routing service
            config: Crawl configuration
        """
        self.browser = browser_client
        self.llm = llm_router
        self.config = config
        self.extractor: PageExtractor | None = None
        self.navigator: Navigator | None = None

        # Crawl state
        self.discovered_urls: set[str] = set()
        self.crawled_urls: set[str] = set()
        self.navigation_graph: dict[str, list[str]] = {}
        self.pages: list[Page] = []
        self.url_to_page: dict[str, Page] = {}

        # Parse base domain for filtering
        parsed = urlparse(config.base_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"

        logger.info(
            "crawler_initialized",
            base_url=config.base_url,
            base_domain=self.base_domain,
            max_pages=config.max_pages,
            max_depth=config.max_depth,
        )

    async def start(self) -> PageInventory:
        """Start the crawl and return page inventory.

        Returns:
            PageInventory containing all discovered pages and navigation graph

        Raises:
            Exception: If crawl fails to start or critical error occurs
        """
        logger.info("crawl_starting", base_url=self.config.base_url)

        try:
            # Create browser session
            session = await self.browser.create_session(
                project_id=self.config.project_id or "default"
            )
            session_id = session["id"]

            # Initialize components
            self.extractor = PageExtractor(self.browser, session_id)
            self.navigator = Navigator(self.browser, session_id)

            logger.info("session_created", session_id=session_id)

            # Handle authentication if required
            if self.config.auth_method != AuthMethod.NONE:
                logger.info("authentication_required", method=self.config.auth_method)
                auth_success = await self._authenticate()
                if not auth_success:
                    logger.error("authentication_failed")
                    raise Exception("Authentication failed")
                logger.info("authentication_successful")

            # Start crawling from base URL
            await self._crawl_recursive(self.config.base_url, depth=0)

            # Build page inventory
            inventory = PageInventory(
                pages=self.pages,
                navigation_graph=self.navigation_graph,
                total_pages=len(self.pages),
            )

            logger.info(
                "crawl_completed",
                total_pages=len(self.pages),
                total_urls_discovered=len(self.discovered_urls),
                graph_nodes=len(self.navigation_graph),
            )

            return inventory

        except Exception as e:
            logger.error("crawl_failed", error=str(e), exc_info=True)
            raise

        finally:
            # Cleanup session
            if hasattr(self, "extractor") and self.extractor:
                try:
                    await self.browser.end_session(self.extractor.session_id)
                    logger.info("session_ended")
                except Exception as e:
                    logger.warning("session_cleanup_failed", error=str(e))

    async def _authenticate(self) -> bool:
        """Handle authentication based on config.auth_method.

        Returns:
            True if authentication successful, False otherwise
        """
        if not self.navigator:
            return False

        try:
            if self.config.auth_method == AuthMethod.SESSION:
                return await self._authenticate_session()
            elif self.config.auth_method == AuthMethod.OAUTH:
                return await self._authenticate_oauth()
            elif self.config.auth_method == AuthMethod.API_KEY:
                return await self._authenticate_api_key()
            else:
                return True

        except Exception as e:
            logger.error(
                "authentication_error",
                method=self.config.auth_method,
                error=str(e),
                exc_info=True,
            )
            return False

    async def _authenticate_session(self) -> bool:
        """Handle session-based authentication (login form)."""
        if not self.navigator or not self.extractor:
            return False

        logger.info("authenticating_session", login_url=self.config.login_url)

        # Navigate to login page
        login_url = self.config.login_url or self.config.base_url
        await self.navigator.navigate(login_url)
        await asyncio.sleep(2)  # Wait for page load

        # Extract page data to analyze auth form
        page_data = await self.extractor.extract_page(login_url)

        # Use LLM to analyze the auth page
        prompt = ANALYZE_AUTH_PAGE.format(
            url=login_url,
            title=page_data.get("title", ""),
            forms_count=len(page_data.get("forms", [])),
            form_details=json.dumps(page_data.get("forms", []), indent=2),
        )

        response = await self.llm.route_task(
            task="extract_navigation", prompt=prompt, page_content=page_data
        )

        try:
            auth_info = json.loads(response.strip())
        except json.JSONDecodeError:
            logger.error("failed_to_parse_auth_analysis", response=response)
            return False

        logger.info("auth_form_analyzed", auth_info=auth_info)

        # Fill login form
        credentials = self.config.credentials or {}
        for field in auth_info.get("fields", []):
            field_name = field.get("name", "")
            field_type = field.get("type", "")

            # Map field to credential
            value = None
            if field_type in ["email", "username"] or "user" in field_name.lower():
                value = credentials.get("username") or credentials.get("email")
            elif field_type == "password" or "pass" in field_name.lower():
                value = credentials.get("password")

            if value:
                # Use Navigator to fill field with human-like behavior
                await self.navigator.type_text(f"[name='{field_name}']", value)
                await asyncio.sleep(random.uniform(0.5, 1.5))

        # Submit form
        submit_selector = auth_info.get("submit_button", "button[type='submit']")
        await self.navigator.click(submit_selector)
        await asyncio.sleep(3)  # Wait for redirect/response

        # Verify authentication (check if we're redirected or see logged-in state)
        current_url = await self.browser.get_current_url(self.extractor.session_id)
        if current_url != login_url:
            logger.info("auth_redirect_detected", new_url=current_url)
            return True

        # Alternative: check for logout button or user menu
        current_page = await self.extractor.extract_page(current_url)
        page_html = current_page.get("html", "").lower()
        if any(
            term in page_html for term in ["logout", "sign out", "dashboard", "profile"]
        ):
            logger.info("auth_verified_by_content")
            return True

        logger.warning("auth_verification_uncertain")
        return True  # Optimistic - proceed with crawl

    async def _authenticate_oauth(self) -> bool:
        """Handle OAuth authentication flow."""
        logger.warning("oauth_not_fully_implemented")
        # OAuth requires handling redirect flows, which is complex
        # For MVP, log warning and proceed
        return True

    async def _authenticate_api_key(self) -> bool:
        """Handle API key authentication."""
        logger.info("api_key_auth", note="Headers will be set for each request")
        # API key is set in headers for each request
        # This is handled at the browser client level
        return True

    async def _crawl_recursive(self, url: str, depth: int, parent_url: str | None = None):
        """Recursively crawl pages starting from URL.

        Args:
            url: URL to crawl
            depth: Current depth in crawl tree
            parent_url: Parent URL for navigation graph
        """
        # Check limits
        if len(self.crawled_urls) >= self.config.max_pages:
            logger.debug("max_pages_reached", max_pages=self.config.max_pages)
            return

        if depth > self.config.max_depth:
            logger.debug("max_depth_reached", url=url, depth=depth)
            return

        # Check if should crawl
        if not await self._should_crawl(url, depth):
            return

        # Crawl the page
        page = await self._crawl_page(url, depth)
        if not page:
            return

        # Add to navigation graph
        if parent_url:
            if parent_url not in self.navigation_graph:
                self.navigation_graph[parent_url] = []
            self.navigation_graph[parent_url].append(url)

        # Extract and normalize links
        links = self._extract_links(page.links)
        self.discovered_urls.update(links)

        logger.info(
            "page_crawled",
            url=url,
            depth=depth,
            links_found=len(links),
            total_crawled=len(self.crawled_urls),
        )

        # Rate limiting
        delay = random.uniform(5.0, 10.0)
        await asyncio.sleep(delay)

        # Plan crawl strategy for discovered links
        if links and len(self.crawled_urls) < self.config.max_pages:
            prioritized_links = await self._plan_crawl_strategy(links, depth)

            # Crawl prioritized links
            for link in prioritized_links:
                if len(self.crawled_urls) >= self.config.max_pages:
                    break
                await self._crawl_recursive(link, depth + 1, parent_url=url)

    async def _crawl_page(self, url: str, depth: int) -> Page | None:
        """Crawl a single page and extract data.

        Args:
            url: URL to crawl
            depth: Current depth

        Returns:
            Page object if successful, None if failed
        """
        if not self.navigator or not self.extractor:
            return None

        try:
            logger.debug("crawling_page", url=url, depth=depth)

            # Navigate to URL with human-like behavior
            await self.navigator.navigate_with_human_behavior(url)

            # Wait for page to stabilize
            await asyncio.sleep(random.uniform(2.0, 4.0))

            # Extract page data
            page_data = await self.extractor.extract_page(url)

            # Create Page model
            page = Page(
                url=url,
                title=page_data.get("title", ""),
                depth=depth,
                html_snapshot=page_data.get("html", ""),
                screenshot_path=page_data.get("screenshot_path"),
                console_logs=page_data.get("console_logs", []),
                network_logs=page_data.get("network_requests", []),
                forms=page_data.get("forms", []),
                links=page_data.get("links", []),
                interactive_elements=page_data.get("interactive_elements", []),
                metadata=page_data.get("metadata", {}),
            )

            # Store page
            self.pages.append(page)
            self.url_to_page[url] = page
            self.crawled_urls.add(url)

            return page

        except Exception as e:
            logger.error("page_crawl_failed", url=url, error=str(e), exc_info=True)
            return None

    async def _should_crawl(self, url: str, depth: int) -> bool:
        """Determine if URL should be crawled.

        Args:
            url: URL to check
            depth: Current depth

        Returns:
            True if should crawl, False otherwise
        """
        # Already crawled
        if url in self.crawled_urls:
            return False

        # Check domain
        if not url.startswith(self.base_domain):
            logger.debug("url_outside_domain", url=url)
            return False

        # Check excluded patterns
        for pattern in self.config.excluded_patterns:
            if re.search(pattern, url):
                logger.debug("url_excluded_by_pattern", url=url, pattern=pattern)
                return False

        # Basic URL filtering (avoid obvious non-pages)
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Skip asset URLs
        asset_extensions = [".css", ".js", ".json", ".xml", ".txt", ".pdf", ".zip"]
        if any(path.endswith(ext) for ext in asset_extensions):
            return False

        # Skip image/media URLs
        media_extensions = [".jpg", ".jpeg", ".png", ".gif", ".svg", ".mp4", ".mp3"]
        if any(path.endswith(ext) for ext in media_extensions):
            return False

        # Skip common non-page endpoints
        skip_patterns = [
            r"/api/",
            r"/logout",
            r"/signout",
            r"/download",
            r"/export",
            r"/print",
        ]
        if any(re.search(pattern, path) for pattern in skip_patterns):
            return False

        # Use LLM for uncertain cases (random sample to avoid too many LLM calls)
        if random.random() < 0.3:  # 30% of URLs get LLM analysis
            prompt = SHOULD_CRAWL.format(
                url=url,
                base_domain=self.base_domain,
                excluded_patterns=json.dumps(self.config.excluded_patterns),
                crawled_count=len(self.crawled_urls),
                max_pages=self.config.max_pages,
                current_depth=depth,
                max_depth=self.config.max_depth,
            )

            try:
                response = await self.llm.route_task(
                    task="extract_navigation",
                    prompt=prompt,
                    page_content={"url": url},
                )
                decision = json.loads(response.strip())
                should_crawl = decision.get("should_crawl", True)
                reason = decision.get("reason", "")

                logger.debug(
                    "llm_crawl_decision",
                    url=url,
                    should_crawl=should_crawl,
                    reason=reason,
                )

                return should_crawl

            except Exception as e:
                logger.warning("llm_decision_failed", url=url, error=str(e))
                # Fall through to default True

        return True

    async def _plan_crawl_strategy(
        self, discovered_links: list[str], current_depth: int
    ) -> list[str]:
        """Use LLM to plan optimal crawl order.

        Args:
            discovered_links: List of discovered URLs
            current_depth: Current crawl depth

        Returns:
            List of URLs in priority order
        """
        # If few links, just return them
        if len(discovered_links) <= 5:
            return discovered_links

        try:
            # Prepare discovered pages summary
            pages_summary = [
                {"url": link, "crawled": link in self.crawled_urls}
                for link in discovered_links
            ]

            prompt = PLAN_CRAWL_STRATEGY.format(
                base_url=self.config.base_url,
                discovered_pages=json.dumps(pages_summary, indent=2),
                max_pages=self.config.max_pages,
                auth_required=self.config.auth_method != AuthMethod.NONE,
                current_depth=current_depth,
                max_depth=self.config.max_depth,
            )

            response = await self.llm.route_task(
                task="plan_crawl_strategy",
                prompt=prompt,
                page_content={"links": discovered_links},
            )

            result = json.loads(response.strip())
            prioritized_urls = result.get("prioritized_urls", discovered_links)
            reasoning = result.get("reasoning", "")

            logger.info(
                "crawl_strategy_planned",
                total_links=len(discovered_links),
                prioritized=len(prioritized_urls),
                reasoning=reasoning,
            )

            return prioritized_urls

        except Exception as e:
            logger.warning(
                "crawl_strategy_planning_failed",
                error=str(e),
                fallback="using original order",
            )
            return discovered_links

    def _extract_links(self, links_data: list[dict[str, Any]]) -> list[str]:
        """Extract and normalize links from page data.

        Args:
            links_data: List of link dictionaries from page extraction

        Returns:
            List of normalized URLs
        """
        normalized_links = set()

        for link in links_data:
            href = link.get("href", "")
            if not href:
                continue

            # Resolve relative URLs
            absolute_url = urljoin(self.config.base_url, href)

            # Parse and clean URL
            parsed = urlparse(absolute_url)

            # Remove fragments and normalize
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                # Keep query params for now (could optionally filter)
                clean_url += f"?{parsed.query}"

            # Only keep URLs from same domain
            if clean_url.startswith(self.base_domain):
                normalized_links.add(clean_url)

        return list(normalized_links)

    def get_page_by_url(self, url: str) -> Page | None:
        """Get a crawled page by URL.

        Args:
            url: Page URL

        Returns:
            Page object if found, None otherwise
        """
        return self.url_to_page.get(url)

    def get_pages_at_depth(self, depth: int) -> list[Page]:
        """Get all pages at a specific depth.

        Args:
            depth: Depth level

        Returns:
            List of pages at that depth
        """
        return [page for page in self.pages if page.depth == depth]

    def get_navigation_children(self, url: str) -> list[str]:
        """Get child URLs in navigation graph.

        Args:
            url: Parent URL

        Returns:
            List of child URLs
        """
        return self.navigation_graph.get(url, [])
