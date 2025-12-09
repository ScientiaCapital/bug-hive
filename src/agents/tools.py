"""Tool definitions for BugHive agents.

This module defines tools that LLMs can call during reasoning to interact
with the browser, inspect elements, and gather information during QA testing.

These tools follow the Anthropic tool calling format and are compatible with
Claude models via the LLMRouter.
"""

# Analyzer Agent Tools
# These tools help the analyzer agent inspect page state and gather evidence
ANALYZER_TOOLS = [
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot of the current page state. Use this to document visual issues, layout problems, or preserve evidence of bugs before they disappear.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_element_details",
        "description": "Get detailed attributes and properties of a specific DOM element by CSS selector. Returns element type, classes, IDs, data attributes, computed styles, and current state. Use this to investigate specific elements that may be causing issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector to identify the element (e.g., '#login-button', '.nav-menu', 'form[name=\"signup\"]')"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "check_accessibility",
        "description": "Run an automated accessibility audit on the current page using industry-standard tools (WCAG 2.1 AA/AAA). Returns violations, warnings, and recommendations for screen readers, keyboard navigation, color contrast, ARIA attributes, and semantic HTML. Use this to identify accessibility issues.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_console_errors",
        "description": "Retrieve all JavaScript console errors, warnings, and exceptions from the current page. Use this to identify runtime errors, unhandled promise rejections, or framework-specific issues.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_network_logs",
        "description": "Get network request logs including failed requests, slow API calls, and HTTP errors. Returns status codes, response times, request/response headers, and failure reasons. Use this to diagnose API issues, CORS errors, or performance problems.",
        "input_schema": {
            "type": "object",
            "properties": {
                "filter_status": {
                    "type": "string",
                    "description": "Optional filter: 'errors' (4xx/5xx only), 'slow' (>5s), or 'all' (default: 'all')",
                    "enum": ["all", "errors", "slow"]
                }
            },
            "required": []
        }
    },
    {
        "name": "measure_performance",
        "description": "Measure page performance metrics including load time, time to interactive, first contentful paint, largest contentful paint, and cumulative layout shift. Use this to identify performance bottlenecks.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

# Crawler Agent Tools
# These tools help the crawler agent navigate and interact with web applications
CRAWLER_TOOLS = [
    {
        "name": "navigate_to",
        "description": "Navigate to a specific URL. Waits for page load and network idle before returning. Use this to move between pages or test deep links.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Full URL to navigate to (e.g., 'https://example.com/dashboard')"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "click_element",
        "description": "Click a DOM element identified by CSS selector. Simulates human-like clicking with configurable delays. Use this to interact with buttons, links, or other clickable elements.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the element to click (e.g., 'button.submit', '#login-btn')"
                },
                "wait_for_navigation": {
                    "type": "boolean",
                    "description": "Whether to wait for navigation after clicking (default: false)"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "fill_form",
        "description": "Fill a form field with a specific value. Simulates human typing with realistic delays. Use this to populate input fields, textareas, or other form controls.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the form field (e.g., 'input[name=\"email\"]', '#password')"
                },
                "value": {
                    "type": "string",
                    "description": "Value to fill into the field"
                }
            },
            "required": ["selector", "value"]
        }
    },
    {
        "name": "scroll_page",
        "description": "Scroll the page vertically to trigger lazy loading or reveal hidden content. Use this to load additional content or test scroll-based functionality.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "description": "Scroll direction: 'down', 'up', 'top', or 'bottom' (default: 'down')",
                    "enum": ["down", "up", "top", "bottom"]
                },
                "amount": {
                    "type": "number",
                    "description": "Pixels to scroll (only for 'down' or 'up', default: 500)"
                }
            },
            "required": []
        }
    },
    {
        "name": "wait_for_element",
        "description": "Wait for an element to appear on the page (useful for dynamic content). Times out after specified duration. Use this before interacting with elements that load asynchronously.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the element to wait for"
                },
                "timeout": {
                    "type": "number",
                    "description": "Maximum wait time in milliseconds (default: 5000)"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "hover_element",
        "description": "Hover over an element to trigger hover states, tooltips, or dropdown menus. Use this to test interactive UI components that respond to mouse hover.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the element to hover over"
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "select_dropdown",
        "description": "Select an option from a dropdown/select element. Use this to interact with dropdown menus and select controls.",
        "input_schema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector for the select element"
                },
                "value": {
                    "type": "string",
                    "description": "Value or visible text of the option to select"
                }
            },
            "required": ["selector", "value"]
        }
    }
]


def get_analyzer_tools() -> list[dict]:
    """Get analyzer agent tool definitions.

    Returns:
        List of tool definition dictionaries for analyzer agent
    """
    return ANALYZER_TOOLS


def get_crawler_tools() -> list[dict]:
    """Get crawler agent tool definitions.

    Returns:
        List of tool definition dictionaries for crawler agent
    """
    return CRAWLER_TOOLS


def get_all_tools() -> dict[str, list[dict]]:
    """Get all agent tool definitions organized by agent type.

    Returns:
        Dictionary mapping agent names to their tool lists
    """
    return {
        "analyzer": ANALYZER_TOOLS,
        "crawler": CRAWLER_TOOLS,
    }
