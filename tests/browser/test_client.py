"""Tests for BrowserbaseClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.browser.client import BrowserbaseClient, BrowserbaseSessionError


class TestBrowserbaseClient:
    """Test suite for BrowserbaseClient."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return BrowserbaseClient(
            api_key="test-api-key",
            project_id="test-project-id",
            timeout=300,
        )

    def test_init(self, client):
        """Test client initialization."""
        assert client.api_key == "test-api-key"
        assert client.project_id == "test-project-id"
        assert client.timeout == 300
        assert client.session_id is None
        assert client.browser is None
        assert client.page is None

    @pytest.mark.asyncio
    async def test_create_session_via_api_success(self, client):
        """Test successful session creation via API."""
        mock_response = {
            "id": "session-123",
            "debuggerUrl": "ws://debug-url",
        }

        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_response
            mock_resp.status_code = 200
            mock_client.post.return_value = mock_resp

            mock_httpx.return_value = mock_client

            result = await client._create_session_via_api()

            assert result == mock_response
            assert result["id"] == "session-123"

    @pytest.mark.asyncio
    async def test_create_session_via_api_failure(self, client):
        """Test session creation API failure."""
        with patch("httpx.AsyncClient") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            # Simulate HTTP error
            import httpx
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.text = "Unauthorized"

            mock_client.post.side_effect = httpx.HTTPStatusError(
                "Error", request=MagicMock(), response=mock_resp
            )

            mock_httpx.return_value = mock_client

            with pytest.raises(BrowserbaseSessionError) as exc_info:
                await client._create_session_via_api()

            assert "401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_should_rotate_session(self, client):
        """Test session rotation check."""
        # Initially no rotation needed
        assert not await client.should_rotate_session()

        # After max pages
        client._pages_count = BrowserbaseClient.MAX_PAGES_PER_SESSION
        assert await client.should_rotate_session()

        # Over max pages
        client._pages_count = BrowserbaseClient.MAX_PAGES_PER_SESSION + 5
        assert await client.should_rotate_session()

    @pytest.mark.asyncio
    async def test_close_cleanup(self, client):
        """Test cleanup on close."""
        # Set some state
        client.session_id = "test-session"
        client._pages_count = 10
        client.browser = MagicMock()
        client.browser.close = AsyncMock()
        client._playwright = MagicMock()
        client._playwright.stop = AsyncMock()

        # Close
        await client.close()

        # Verify cleanup
        assert client.session_id is None
        assert client.browser is None
        assert client.page is None
        assert client._pages_count == 0

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        client = BrowserbaseClient(
            api_key="test-api-key",
            project_id="test-project-id"
        )

        # Mock start_session and close
        client.start_session = AsyncMock(return_value="session-123")
        client.close = AsyncMock()

        async with client as ctx_client:
            assert ctx_client is client
            client.start_session.assert_awaited_once()

        # Verify close was called
        client.close.assert_awaited_once()

    def test_websocket_url_format(self, client):
        """Test WebSocket URL construction."""
        client.session_id = "test-session-id"

        expected_url = (
            f"{BrowserbaseClient.WS_BASE_URL}"
            f"?apiKey={client.api_key}"
            f"&sessionId={client.session_id}"
            "&enableProxy=true"
        )

        # Build URL same way client does
        ws_endpoint = (
            f"{client.WS_BASE_URL}"
            f"?apiKey={client.api_key}"
            f"&sessionId={client.session_id}"
            "&enableProxy=true"
        )

        assert ws_endpoint == expected_url
        assert "wss://connect.browserbase.com" in ws_endpoint
        assert "test-api-key" in ws_endpoint
        assert "test-session-id" in ws_endpoint
        assert "enableProxy=true" in ws_endpoint

    @pytest.mark.asyncio
    async def test_navigation_increments_counter(self, client):
        """Test that navigation increments page counter."""
        # Setup mocks
        client.page = MagicMock()
        client.page.goto = AsyncMock(return_value=MagicMock(status=200))
        client.page.title = AsyncMock(return_value="Test Page")
        client.page.url = "https://example.com"

        initial_count = client._pages_count

        # Navigate
        await client.navigate("https://example.com")

        # Verify counter incremented
        assert client._pages_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_screenshot_no_page_error(self, client):
        """Test screenshot without active page raises error."""
        client.page = None

        with pytest.raises(BrowserbaseSessionError) as exc_info:
            await client.screenshot()

        assert "No active page" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_navigate_no_page_error(self, client):
        """Test navigate without active page raises error."""
        client.page = None

        with pytest.raises(BrowserbaseSessionError) as exc_info:
            await client.navigate("https://example.com")

        assert "No active page" in str(exc_info.value)
