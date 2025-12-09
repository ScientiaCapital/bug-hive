"""Tests for agent tool definitions and integration."""

import pytest

from src.agents.tools import (
    ANALYZER_TOOLS,
    CRAWLER_TOOLS,
    get_analyzer_tools,
    get_crawler_tools,
    get_all_tools,
)


class TestToolSchemas:
    """Test that tool schemas are properly structured."""

    def test_analyzer_tools_structure(self):
        """Verify ANALYZER_TOOLS has correct structure."""
        assert isinstance(ANALYZER_TOOLS, list)
        assert len(ANALYZER_TOOLS) > 0

        for tool in ANALYZER_TOOLS:
            # Each tool must have required fields
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

            # Name must be non-empty string
            assert isinstance(tool["name"], str)
            assert len(tool["name"]) > 0

            # Description must be non-empty string
            assert isinstance(tool["description"], str)
            assert len(tool["description"]) > 0

            # Input schema must be a dict with type and properties
            schema = tool["input_schema"]
            assert isinstance(schema, dict)
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema

    def test_crawler_tools_structure(self):
        """Verify CRAWLER_TOOLS has correct structure."""
        assert isinstance(CRAWLER_TOOLS, list)
        assert len(CRAWLER_TOOLS) > 0

        for tool in CRAWLER_TOOLS:
            # Each tool must have required fields
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

            # Name must be non-empty string
            assert isinstance(tool["name"], str)
            assert len(tool["name"]) > 0

            # Description must be non-empty string
            assert isinstance(tool["description"], str)
            assert len(tool["description"]) > 0

            # Input schema must be a dict with type and properties
            schema = tool["input_schema"]
            assert isinstance(schema, dict)
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema

    def test_analyzer_tool_names_unique(self):
        """Ensure analyzer tool names are unique."""
        tool_names = [tool["name"] for tool in ANALYZER_TOOLS]
        assert len(tool_names) == len(set(tool_names)), "Duplicate tool names found"

    def test_crawler_tool_names_unique(self):
        """Ensure crawler tool names are unique."""
        tool_names = [tool["name"] for tool in CRAWLER_TOOLS]
        assert len(tool_names) == len(set(tool_names)), "Duplicate tool names found"

    def test_no_overlapping_tool_names(self):
        """Ensure analyzer and crawler tools don't have overlapping names."""
        analyzer_names = {tool["name"] for tool in ANALYZER_TOOLS}
        crawler_names = {tool["name"] for tool in CRAWLER_TOOLS}
        overlap = analyzer_names & crawler_names
        assert len(overlap) == 0, f"Tools with overlapping names: {overlap}"


class TestAnalyzerTools:
    """Test specific analyzer tools."""

    def test_take_screenshot_tool(self):
        """Test take_screenshot tool definition."""
        screenshot_tool = next(
            (t for t in ANALYZER_TOOLS if t["name"] == "take_screenshot"),
            None
        )
        assert screenshot_tool is not None
        assert "screenshot" in screenshot_tool["description"].lower()
        assert screenshot_tool["input_schema"]["required"] == []

    def test_get_element_details_tool(self):
        """Test get_element_details tool definition."""
        element_tool = next(
            (t for t in ANALYZER_TOOLS if t["name"] == "get_element_details"),
            None
        )
        assert element_tool is not None
        assert "selector" in element_tool["input_schema"]["properties"]
        assert "selector" in element_tool["input_schema"]["required"]
        assert "string" == element_tool["input_schema"]["properties"]["selector"]["type"]

    def test_check_accessibility_tool(self):
        """Test check_accessibility tool definition."""
        a11y_tool = next(
            (t for t in ANALYZER_TOOLS if t["name"] == "check_accessibility"),
            None
        )
        assert a11y_tool is not None
        assert "accessibility" in a11y_tool["description"].lower()
        assert a11y_tool["input_schema"]["required"] == []

    def test_get_console_errors_tool(self):
        """Test get_console_errors tool definition."""
        console_tool = next(
            (t for t in ANALYZER_TOOLS if t["name"] == "get_console_errors"),
            None
        )
        assert console_tool is not None
        assert "console" in console_tool["description"].lower()

    def test_get_network_logs_tool(self):
        """Test get_network_logs tool definition."""
        network_tool = next(
            (t for t in ANALYZER_TOOLS if t["name"] == "get_network_logs"),
            None
        )
        assert network_tool is not None
        assert "network" in network_tool["description"].lower()
        # Should have optional filter parameter
        if "filter_status" in network_tool["input_schema"]["properties"]:
            assert "filter_status" not in network_tool["input_schema"]["required"]

    def test_measure_performance_tool(self):
        """Test measure_performance tool definition."""
        perf_tool = next(
            (t for t in ANALYZER_TOOLS if t["name"] == "measure_performance"),
            None
        )
        assert perf_tool is not None
        assert "performance" in perf_tool["description"].lower()


class TestCrawlerTools:
    """Test specific crawler tools."""

    def test_navigate_to_tool(self):
        """Test navigate_to tool definition."""
        nav_tool = next(
            (t for t in CRAWLER_TOOLS if t["name"] == "navigate_to"),
            None
        )
        assert nav_tool is not None
        assert "url" in nav_tool["input_schema"]["properties"]
        assert "url" in nav_tool["input_schema"]["required"]
        assert nav_tool["input_schema"]["properties"]["url"]["type"] == "string"

    def test_click_element_tool(self):
        """Test click_element tool definition."""
        click_tool = next(
            (t for t in CRAWLER_TOOLS if t["name"] == "click_element"),
            None
        )
        assert click_tool is not None
        assert "selector" in click_tool["input_schema"]["properties"]
        assert "selector" in click_tool["input_schema"]["required"]

    def test_fill_form_tool(self):
        """Test fill_form tool definition."""
        fill_tool = next(
            (t for t in CRAWLER_TOOLS if t["name"] == "fill_form"),
            None
        )
        assert fill_tool is not None
        assert "selector" in fill_tool["input_schema"]["properties"]
        assert "value" in fill_tool["input_schema"]["properties"]
        assert "selector" in fill_tool["input_schema"]["required"]
        assert "value" in fill_tool["input_schema"]["required"]

    def test_scroll_page_tool(self):
        """Test scroll_page tool definition."""
        scroll_tool = next(
            (t for t in CRAWLER_TOOLS if t["name"] == "scroll_page"),
            None
        )
        assert scroll_tool is not None
        assert scroll_tool["input_schema"]["required"] == []

    def test_wait_for_element_tool(self):
        """Test wait_for_element tool definition."""
        wait_tool = next(
            (t for t in CRAWLER_TOOLS if t["name"] == "wait_for_element"),
            None
        )
        assert wait_tool is not None
        assert "selector" in wait_tool["input_schema"]["properties"]
        assert "selector" in wait_tool["input_schema"]["required"]

    def test_hover_element_tool(self):
        """Test hover_element tool definition."""
        hover_tool = next(
            (t for t in CRAWLER_TOOLS if t["name"] == "hover_element"),
            None
        )
        assert hover_tool is not None
        assert "selector" in hover_tool["input_schema"]["properties"]
        assert "selector" in hover_tool["input_schema"]["required"]

    def test_select_dropdown_tool(self):
        """Test select_dropdown tool definition."""
        select_tool = next(
            (t for t in CRAWLER_TOOLS if t["name"] == "select_dropdown"),
            None
        )
        assert select_tool is not None
        assert "selector" in select_tool["input_schema"]["properties"]
        assert "value" in select_tool["input_schema"]["properties"]
        assert set(select_tool["input_schema"]["required"]) == {"selector", "value"}


class TestToolGetters:
    """Test tool getter functions."""

    def test_get_analyzer_tools(self):
        """Test get_analyzer_tools() returns correct tools."""
        tools = get_analyzer_tools()
        assert isinstance(tools, list)
        assert len(tools) == len(ANALYZER_TOOLS)
        assert tools == ANALYZER_TOOLS

    def test_get_crawler_tools(self):
        """Test get_crawler_tools() returns correct tools."""
        tools = get_crawler_tools()
        assert isinstance(tools, list)
        assert len(tools) == len(CRAWLER_TOOLS)
        assert tools == CRAWLER_TOOLS

    def test_get_all_tools(self):
        """Test get_all_tools() returns organized dict."""
        all_tools = get_all_tools()
        assert isinstance(all_tools, dict)
        assert "analyzer" in all_tools
        assert "crawler" in all_tools
        assert all_tools["analyzer"] == ANALYZER_TOOLS
        assert all_tools["crawler"] == CRAWLER_TOOLS


class TestAnthropicCompatibility:
    """Test that tools are compatible with Anthropic's format."""

    def test_analyzer_tools_anthropic_format(self):
        """Verify analyzer tools follow Anthropic tool format."""
        for tool in ANALYZER_TOOLS:
            # Anthropic requires these exact fields
            assert set(tool.keys()) == {"name", "description", "input_schema"}

            # input_schema must have type: object
            assert tool["input_schema"]["type"] == "object"

            # properties must be a dict
            assert isinstance(tool["input_schema"]["properties"], dict)

            # required must be a list
            assert isinstance(tool["input_schema"]["required"], list)

            # All required fields must exist in properties
            for req in tool["input_schema"]["required"]:
                assert req in tool["input_schema"]["properties"]

    def test_crawler_tools_anthropic_format(self):
        """Verify crawler tools follow Anthropic tool format."""
        for tool in CRAWLER_TOOLS:
            # Anthropic requires these exact fields
            assert set(tool.keys()) == {"name", "description", "input_schema"}

            # input_schema must have type: object
            assert tool["input_schema"]["type"] == "object"

            # properties must be a dict
            assert isinstance(tool["input_schema"]["properties"], dict)

            # required must be a list
            assert isinstance(tool["input_schema"]["required"], list)

            # All required fields must exist in properties
            for req in tool["input_schema"]["required"]:
                assert req in tool["input_schema"]["properties"]

    def test_property_types_valid(self):
        """Ensure all property types are valid JSON Schema types."""
        valid_types = {"string", "number", "boolean", "object", "array"}

        all_tools = ANALYZER_TOOLS + CRAWLER_TOOLS
        for tool in all_tools:
            for prop_name, prop_schema in tool["input_schema"]["properties"].items():
                assert "type" in prop_schema, f"Property '{prop_name}' missing type"
                assert prop_schema["type"] in valid_types, \
                    f"Invalid type '{prop_schema['type']}' for property '{prop_name}'"


class TestToolDescriptions:
    """Test that tool descriptions are clear and helpful."""

    def test_descriptions_minimum_length(self):
        """Ensure descriptions are sufficiently detailed."""
        min_length = 20  # Minimum characters for a good description

        all_tools = ANALYZER_TOOLS + CRAWLER_TOOLS
        for tool in all_tools:
            assert len(tool["description"]) >= min_length, \
                f"Tool '{tool['name']}' has too short description"

    def test_descriptions_mention_use_case(self):
        """Ensure descriptions mention when to use the tool."""
        all_tools = ANALYZER_TOOLS + CRAWLER_TOOLS
        for tool in all_tools:
            desc_lower = tool["description"].lower()
            # Good descriptions should contain action words or use cases
            has_action = any(word in desc_lower for word in [
                "use", "get", "capture", "check", "run", "measure",
                "navigate", "click", "fill", "scroll", "wait", "hover", "select"
            ])
            assert has_action, \
                f"Tool '{tool['name']}' description doesn't clearly explain usage"

    def test_property_descriptions_present(self):
        """Ensure all properties have descriptions."""
        all_tools = ANALYZER_TOOLS + CRAWLER_TOOLS
        for tool in all_tools:
            for prop_name, prop_schema in tool["input_schema"]["properties"].items():
                # Properties should have descriptions to help the LLM
                if prop_name not in ["timeout", "amount"]:  # Allow some to skip
                    assert "description" in prop_schema, \
                        f"Property '{prop_name}' in tool '{tool['name']}' missing description"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
