"""Prompt templates for the Crawler Agent.

Note: These prompts are used in conjunction with BUGHIVE_SYSTEM_PROMPT from __init__.py
to ensure consistent agent behavior and persona across the BugHive system.
"""

# Import system prompt for reference (actual use is in agent implementation)
from src.agents.prompts import BUGHIVE_SYSTEM_PROMPT  # noqa: F401

PLAN_CRAWL_STRATEGY = """
You are planning a crawl strategy for a web application.

Base URL: {base_url}
Discovered Pages: {discovered_pages}
Max Pages: {max_pages}
Auth Required: {auth_required}
Current Depth: {current_depth}
Max Depth: {max_depth}

Analyze the discovered pages and prioritize them by importance:
1. Core functionality pages (dashboards, main features)
2. User-facing features (forms, data entry, views)
3. Settings/admin pages (configuration, user management)
4. Static content (about, help, documentation)

Consider:
- Pages likely to have interactive elements
- Pages that represent different user workflows
- Pages that might contain forms or dynamic content
- Avoid duplicate or similar pages

Return a JSON array of URLs in priority order, limiting to the most important pages.

Format:
{{
  "prioritized_urls": ["url1", "url2", ...],
  "reasoning": "Step-by-step explanation of prioritization strategy"
}}
"""

SHOULD_CRAWL = """
Determine if this URL should be crawled based on the given context.

URL: {url}
Base Domain: {base_domain}
Excluded Patterns: {excluded_patterns}
Already Crawled: {crawled_count}/{max_pages}
Current Depth: {current_depth}/{max_depth}

Consider:
- Is this URL within the base domain?
- Does it match any excluded patterns?
- Is it likely to be a duplicate or similar to already crawled pages?
- Does it represent a unique page worth crawling?
- Would crawling this URL provide valuable information for QA testing?

Avoid:
- Logout/signout pages
- Download/export endpoints
- Pagination variants of the same page
- API endpoints (unless specifically needed)
- External links
- Asset URLs (images, CSS, JS)

Return your decision:
{{
  "should_crawl": true/false,
  "reason": "Brief explanation of the decision",
  "confidence": 0.0-1.0
}}
"""

EXTRACT_NAVIGATION_CONTEXT = """
Analyze the current page and extract navigation context.

Page URL: {url}
Page Title: {title}
Links Found: {links_count}
Forms Found: {forms_count}

From the page HTML structure and visible elements, identify:
1. Main navigation links (header, sidebar, menu)
2. Important action links (buttons, CTAs)
3. Contextual links (breadcrumbs, related pages)
4. Auth-related links (login, logout, profile)

Categorize each link by importance:
- critical: Must crawl (core functionality)
- high: Should crawl (important features)
- medium: Nice to crawl (secondary features)
- low: Optional (peripheral content)

Return:
{{
  "navigation_links": [
    {{"url": "...", "text": "...", "importance": "critical/high/medium/low", "category": "..."}},
    ...
  ],
  "page_type": "landing/dashboard/form/list/detail/settings/auth",
  "requires_auth": true/false
}}
"""

ANALYZE_AUTH_PAGE = """
Analyze this page to determine the authentication method and required fields.

Page URL: {url}
Page Title: {title}
Forms Found: {forms_count}
Form Details: {form_details}

Identify:
1. Authentication method (form-based, OAuth, SSO, API key, etc.)
2. Required input fields (username, email, password, 2FA, etc.)
3. Submit button or action
4. Any special requirements (CAPTCHA, terms acceptance, etc.)

Return:
{{
  "auth_method": "session/oauth/api_key/sso/unknown",
  "form_selector": "CSS selector for the form",
  "fields": [
    {{"name": "...", "type": "...", "label": "...", "required": true/false}},
    ...
  ],
  "submit_button": "CSS selector or text",
  "additional_steps": ["any additional steps required"],
  "confidence": 0.0-1.0,
  "reasoning": "Step-by-step explanation of authentication method analysis"
}}
"""
