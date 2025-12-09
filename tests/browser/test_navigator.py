"""Tests for Navigator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.browser.navigator import Navigator, NavigationError


class TestNavigator:
    """Test suite for Navigator."""

    @pytest.fixture
    def mock_page(self):
        """Create mock Playwright page."""
        page = MagicMock()
        page.url = "https://example.com"
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.evaluate = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.click = AsyncMock()
        page.type = AsyncMock()
        page.fill = AsyncMock()
        page.hover = AsyncMock()
        page.select_option = AsyncMock()
        page.add_style_tag = AsyncMock()
        page.query_selector_all = AsyncMock(return_value=[])
        page.expect_navigation = MagicMock()
        return page

    def test_random_delay_range(self):
        """Test random delay is within expected range."""
        for _ in range(100):
            delay = Navigator._random_delay(1.0, 2.0)
            assert 1.0 <= delay <= 2.0

    @pytest.mark.asyncio
    async def test_navigate_with_human_behavior_success(self, mock_page):
        """Test successful navigation with human behavior."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response

        # Navigate
        result = await Navigator.navigate_with_human_behavior(
            mock_page,
            "https://example.com",
            wait_until="domcontentloaded",
        )

        # Verify
        assert result is True
        mock_page.goto.assert_awaited_once()
        mock_page.wait_for_load_state.assert_awaited()
        mock_page.evaluate.assert_awaited()  # For scrolling

    @pytest.mark.asyncio
    async def test_navigate_with_human_behavior_no_response(self, mock_page):
        """Test navigation with no response raises error."""
        mock_page.goto.return_value = None

        with pytest.raises(NavigationError) as exc_info:
            await Navigator.navigate_with_human_behavior(
                mock_page,
                "https://example.com",
            )

        assert "No response received" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_random_scroll(self, mock_page):
        """Test random scrolling."""
        await Navigator.random_scroll(mock_page, num_scrolls=3)

        # Should have scrolled 3 times
        assert mock_page.evaluate.await_count == 3

        # Verify scroll commands
        for call in mock_page.evaluate.await_args_list:
            args = call[0]
            assert "window.scrollBy" in args[0]

    @pytest.mark.asyncio
    async def test_fill_form_with_char_delay(self, mock_page):
        """Test form filling with character delays."""
        value = "test@example.com"

        result = await Navigator.fill_form(
            mock_page,
            selector="#email",
            value=value,
            delay_between_chars=True,
        )

        # Verify
        assert result is True
        mock_page.wait_for_selector.assert_awaited_once()
        mock_page.click.assert_awaited_once()
        # Should type each character
        assert mock_page.type.await_count == len(value)

    @pytest.mark.asyncio
    async def test_fill_form_without_delay(self, mock_page):
        """Test form filling without character delays."""
        result = await Navigator.fill_form(
            mock_page,
            selector="#email",
            value="test@example.com",
            delay_between_chars=False,
        )

        # Verify
        assert result is True
        mock_page.fill.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fill_form_timeout(self, mock_page):
        """Test form filling timeout."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout")

        with pytest.raises(NavigationError) as exc_info:
            await Navigator.fill_form(
                mock_page,
                selector="#missing",
                value="test",
            )

        assert "Form field not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_click_element_success(self, mock_page):
        """Test clicking element successfully."""
        result = await Navigator.click_element(
            mock_page,
            selector="button.submit",
            wait_for_navigation=False,
        )

        assert result is True
        mock_page.wait_for_selector.assert_awaited_once()
        mock_page.click.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_click_element_with_navigation(self, mock_page):
        """Test clicking element with navigation wait."""
        # Mock expect_navigation context manager
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock()
        mock_context.__aexit__ = AsyncMock()
        mock_page.expect_navigation.return_value = mock_context

        result = await Navigator.click_element(
            mock_page,
            selector="a.link",
            wait_for_navigation=True,
        )

        assert result is True
        mock_page.expect_navigation.assert_called_once()

    @pytest.mark.asyncio
    async def test_dismiss_overlays_basic(self, mock_page):
        """Test basic overlay dismissal."""
        # Mock finding a cookie consent button
        mock_element = MagicMock()
        mock_element.is_visible = AsyncMock(return_value=True)
        mock_element.click = AsyncMock()
        mock_page.query_selector_all.return_value = [mock_element]
        mock_page.evaluate.return_value = 0

        result = await Navigator.dismiss_overlays(
            mock_page,
            aggressive=False,
        )

        # Should have tried to click buttons
        mock_page.query_selector_all.assert_awaited()

    @pytest.mark.asyncio
    async def test_dismiss_overlays_aggressive(self, mock_page):
        """Test aggressive overlay dismissal."""
        # Mock removing elements
        mock_page.evaluate.return_value = 5  # 5 elements removed

        result = await Navigator.dismiss_overlays(
            mock_page,
            aggressive=True,
        )

        # Should have added CSS and removed elements
        mock_page.add_style_tag.assert_awaited_once()
        mock_page.evaluate.assert_awaited()
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_element_success(self, mock_page):
        """Test waiting for element successfully."""
        result = await Navigator.wait_for_element(
            mock_page,
            selector=".element",
            timeout_ms=5000,
            state="visible",
        )

        assert result is True
        mock_page.wait_for_selector.assert_awaited_once_with(
            ".element",
            state="visible",
            timeout=5000,
        )

    @pytest.mark.asyncio
    async def test_wait_for_element_timeout(self, mock_page):
        """Test waiting for element timeout."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("Timeout")

        with pytest.raises(NavigationError) as exc_info:
            await Navigator.wait_for_element(
                mock_page,
                selector=".missing",
                timeout_ms=1000,
            )

        assert "did not reach visible state" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hover_element(self, mock_page):
        """Test hovering over element."""
        result = await Navigator.hover_element(mock_page, selector=".menu-item")

        assert result is True
        mock_page.wait_for_selector.assert_awaited_once()
        mock_page.hover.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_select_option_by_value(self, mock_page):
        """Test selecting option by value."""
        result = await Navigator.select_option(
            mock_page,
            selector="select#country",
            value="US",
        )

        assert result is True
        mock_page.select_option.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_select_option_by_label(self, mock_page):
        """Test selecting option by label."""
        result = await Navigator.select_option(
            mock_page,
            selector="select#country",
            label="United States",
        )

        assert result is True
        mock_page.select_option.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_select_option_no_value_or_label(self, mock_page):
        """Test selecting option without value or label raises error."""
        with pytest.raises(ValueError):
            await Navigator.select_option(
                mock_page,
                selector="select#country",
            )

    @pytest.mark.asyncio
    async def test_human_delay(self):
        """Test human delay actually waits."""
        import time

        start = time.time()
        await Navigator._human_delay(0.1, 0.2)
        elapsed = time.time() - start

        # Should have waited at least 0.1 seconds
        assert elapsed >= 0.1
        # Should not wait more than 0.3 seconds (with some buffer)
        assert elapsed < 0.3

    @pytest.mark.asyncio
    async def test_navigate_handles_networkidle_timeout(self, mock_page):
        """Test navigation handles networkidle timeout gracefully."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        # Mock goto success but networkidle timeout
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response
        mock_page.wait_for_load_state.side_effect = PlaywrightTimeoutError("Networkidle timeout")

        # Should still succeed
        result = await Navigator.navigate_with_human_behavior(
            mock_page,
            "https://example.com",
        )

        assert result is True
