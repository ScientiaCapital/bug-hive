"""Tests for PageExtractor."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.browser.extractor import PageExtractor


class TestPageExtractor:
    """Test suite for PageExtractor."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = MagicMock()
        page.url = "https://example.com"
        page.title = AsyncMock(return_value="Example Page")
        page.evaluate = AsyncMock()
        page.on = MagicMock()
        return page

    @pytest.fixture
    def extractor(self, mock_page):
        """Create test extractor."""
        return PageExtractor(mock_page, base_url="https://example.com")

    def test_init(self, extractor, mock_page):
        """Test extractor initialization."""
        assert extractor.page == mock_page
        assert extractor.base_url == "https://example.com"
        assert extractor._console_logs == []
        assert extractor._network_responses == []
        assert extractor._network_errors == []

    async def test_setup_listeners(self, extractor, mock_page):
        """Test listener setup."""
        await extractor.setup_listeners()

        # Verify listeners were registered
        assert mock_page.on.call_count >= 3
        calls = [call[0][0] for call in mock_page.on.call_args_list]
        assert "console" in calls
        assert "response" in calls
        assert "requestfailed" in calls

    def test_handle_console_error(self, extractor):
        """Test console error handling."""
        # Create mock console message
        msg = MagicMock()
        msg.type = "error"
        msg.text = "TypeError: Cannot read property 'foo'"
        msg.location = {"url": "app.js", "lineNumber": 42}

        # Handle message
        extractor._handle_console(msg)

        # Verify it was captured
        assert len(extractor._console_logs) == 1
        log = extractor._console_logs[0]
        assert log["level"] == "error"
        assert log["text"] == "TypeError: Cannot read property 'foo'"

    def test_handle_console_warning(self, extractor):
        """Test console warning handling."""
        msg = MagicMock()
        msg.type = "warning"
        msg.text = "Deprecated API usage"

        extractor._handle_console(msg)

        assert len(extractor._console_logs) == 1
        assert extractor._console_logs[0]["level"] == "warning"

    def test_handle_response(self, extractor):
        """Test network response handling."""
        # Create mock response
        response = MagicMock()
        response.url = "https://api.example.com/data"
        response.status = 200
        response.request.method = "GET"
        response.request.resource_type = "fetch"
        response.request.timing = {}
        response.headers = {"content-type": "application/json"}

        # Handle response
        extractor._handle_response(response)

        # Verify it was captured
        assert len(extractor._network_responses) == 1
        resp = extractor._network_responses[0]
        assert resp["url"] == "https://api.example.com/data"
        assert resp["status"] == 200
        assert resp["method"] == "GET"

    def test_handle_response_error(self, extractor):
        """Test error response handling."""
        response = MagicMock()
        response.url = "https://api.example.com/not-found"
        response.status = 404
        response.request.method = "GET"
        response.request.resource_type = "fetch"
        response.request.timing = {}

        extractor._handle_response(response)

        assert len(extractor._network_responses) == 1
        assert extractor._network_responses[0]["status"] == 404

    def test_handle_request_failed(self, extractor):
        """Test failed request handling."""
        request = MagicMock()
        request.url = "https://api.example.com/timeout"
        request.method = "GET"
        request.resource_type = "fetch"
        request.failure = "net::ERR_TIMED_OUT"

        extractor._handle_request_failed(request)

        assert len(extractor._network_errors) == 1
        error = extractor._network_errors[0]
        assert error["url"] == "https://api.example.com/timeout"
        assert error["failure"] == "net::ERR_TIMED_OUT"

    @pytest.mark.asyncio
    async def test_extract_forms(self, extractor, mock_page):
        """Test form extraction."""
        # Mock form data
        form_data = [
            {
                "id": "login-form",
                "action": "/login",
                "method": "post",
                "inputs": [
                    {"name": "email", "type": "email", "required": True},
                    {"name": "password", "type": "password", "required": True},
                ],
            }
        ]

        mock_page.evaluate.return_value = form_data

        # Extract forms
        forms = await extractor.extract_forms()

        # Verify
        assert len(forms) == 1
        assert forms[0]["id"] == "login-form"
        assert forms[0]["method"] == "post"
        assert len(forms[0]["inputs"]) == 2

    @pytest.mark.asyncio
    async def test_extract_links(self, extractor, mock_page):
        """Test link extraction."""
        # Mock links
        all_links = [
            "https://example.com/about",
            "https://example.com/contact",
            "https://other-site.com/external",
        ]

        mock_page.evaluate.return_value = all_links

        # Extract internal links only
        links = await extractor.extract_links(internal_only=True)

        # Should filter to only internal links
        assert len(links) == 2
        assert all(link.startswith("https://example.com") for link in links)

    @pytest.mark.asyncio
    async def test_extract_links_all(self, extractor, mock_page):
        """Test extracting all links including external."""
        all_links = [
            "https://example.com/about",
            "https://external.com/page",
        ]

        mock_page.evaluate.return_value = all_links

        # Extract all links
        links = await extractor.extract_links(internal_only=False)

        assert len(links) == 2

    @pytest.mark.asyncio
    async def test_extract_performance_metrics(self, extractor, mock_page):
        """Test performance metrics extraction."""
        metrics = {
            "loadTime": 1234,
            "domReady": 890,
            "firstPaint": 456,
            "largestPaint": 678,
        }

        mock_page.evaluate.return_value = metrics

        # Extract metrics
        result = await extractor.extract_performance_metrics()

        assert result["loadTime"] == 1234
        assert result["domReady"] == 890

    @pytest.mark.asyncio
    async def test_extract_meta_tags(self, extractor, mock_page):
        """Test meta tag extraction."""
        meta_tags = {
            "description": "Example site description",
            "keywords": "test, example, demo",
            "og:title": "Example Site",
        }

        mock_page.evaluate.return_value = meta_tags

        # Extract meta tags
        result = await extractor.extract_meta_tags()

        assert result["description"] == "Example site description"
        assert "og:title" in result

    @pytest.mark.asyncio
    async def test_extract_all(self, extractor, mock_page):
        """Test comprehensive data extraction."""
        # Setup mock data
        mock_page.evaluate.side_effect = [
            [],  # forms
            [],  # links
            {"loadTime": 1000},  # performance
            {"description": "Test"},  # meta tags
        ]
        mock_page.title.return_value = "Test Page"

        # Add some console logs
        msg = MagicMock()
        msg.type = "error"
        msg.text = "Test error"
        extractor._handle_console(msg)

        # Extract all
        data = await extractor.extract_all()

        # Verify structure
        assert "url" in data
        assert "title" in data
        assert "console_logs" in data
        assert "network_requests" in data
        assert "forms" in data
        assert "links" in data
        assert "performance_metrics" in data
        assert "meta_tags" in data

        # Verify data
        assert data["title"] == "Test Page"
        assert len(data["console_logs"]) == 1

    def test_get_console_errors(self, extractor):
        """Test getting console errors."""
        # Add different log levels
        extractor._console_logs = [
            {"level": "error", "text": "Error 1"},
            {"level": "warning", "text": "Warning 1"},
            {"level": "error", "text": "Error 2"},
            {"level": "info", "text": "Info 1"},
        ]

        errors = extractor.get_console_errors()

        assert len(errors) == 2
        assert all(log["level"] == "error" for log in errors)

    def test_get_console_warnings(self, extractor):
        """Test getting console warnings."""
        extractor._console_logs = [
            {"level": "error", "text": "Error 1"},
            {"level": "warning", "text": "Warning 1"},
            {"level": "warning", "text": "Warning 2"},
        ]

        warnings = extractor.get_console_warnings()

        assert len(warnings) == 2
        assert all(log["level"] == "warning" for log in warnings)

    def test_get_failed_requests(self, extractor):
        """Test getting failed requests."""
        extractor._network_responses = [
            {"url": "http://test.com/ok", "status": 200},
            {"url": "http://test.com/not-found", "status": 404},
            {"url": "http://test.com/error", "status": 500},
        ]

        failed = extractor.get_failed_requests()

        assert len(failed) == 2
        assert all(req["status"] >= 400 for req in failed)

    def test_get_slow_requests(self, extractor):
        """Test getting slow requests."""
        extractor._network_responses = [
            {"url": "http://test.com/fast", "timing": {"total": 500}},
            {"url": "http://test.com/slow", "timing": {"total": 2000}},
            {"url": "http://test.com/very-slow", "timing": {"total": 5000}},
        ]

        slow = extractor.get_slow_requests(threshold_ms=1000)

        assert len(slow) == 2
        assert all(req["timing"]["total"] > 1000 for req in slow)

    def test_clear_data(self, extractor):
        """Test clearing captured data."""
        # Add some data
        extractor._console_logs = [{"level": "error", "text": "Test"}]
        extractor._network_responses = [{"url": "http://test.com"}]
        extractor._network_errors = [{"url": "http://error.com"}]

        # Clear
        extractor.clear_data()

        # Verify cleared
        assert len(extractor._console_logs) == 0
        assert len(extractor._network_responses) == 0
        assert len(extractor._network_errors) == 0
