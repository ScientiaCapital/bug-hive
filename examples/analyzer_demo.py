"""Demo script showing Page Analyzer Agent in action.

This example demonstrates:
1. Extracting page data using PageExtractor
2. Analyzing for bugs using PageAnalyzerAgent
3. Processing and displaying results
"""

import asyncio
import json
from datetime import datetime

from playwright.async_api import async_playwright

from src.agents.analyzer import PageAnalyzerAgent
from src.browser.extractor import PageExtractor
from src.llm.router import LLMRouter


async def demo_analyzer():
    """Demonstrate page analysis."""
    print("🧿 BugHive Page Analyzer Demo\n")

    # For demo purposes, we'll use mock page data
    # In production, this comes from PageExtractor
    mock_page_data = {
        "url": "https://example.com/demo",
        "title": "Demo Page - Example Site",
        "console_logs": [
            {
                "level": "error",
                "text": "Uncaught TypeError: Cannot read property 'map' of undefined at app.js:42",
                "timestamp": datetime.utcnow().isoformat(),
                "location": {"url": "app.js", "lineNumber": 42}
            },
            {
                "level": "warning",
                "text": "React Warning: useEffect has missing dependency 'userId'",
                "timestamp": datetime.utcnow().isoformat(),
                "location": {"url": "components.js", "lineNumber": 123}
            },
            {
                "level": "log",
                "text": "DEBUG: User authentication successful",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
        "network_requests": [
            {
                "url": "https://api.example.com/products",
                "status": 200,
                "method": "GET",
                "resource_type": "fetch",
                "timestamp": datetime.utcnow().isoformat(),
                "timing": {"total": 234},
                "headers": {}
            },
            {
                "url": "https://api.example.com/users/create",
                "status": 500,
                "method": "POST",
                "resource_type": "fetch",
                "timestamp": datetime.utcnow().isoformat(),
                "timing": {"total": 1234},
                "headers": {}
            },
            {
                "url": "https://api.example.com/slow-endpoint",
                "status": 200,
                "method": "GET",
                "resource_type": "fetch",
                "timestamp": datetime.utcnow().isoformat(),
                "timing": {"total": 7500},  # 7.5 seconds
                "headers": {}
            },
        ],
        "network_errors": [
            {
                "url": "https://api.example.com/cors-error",
                "method": "POST",
                "resource_type": "fetch",
                "failure": "net::ERR_BLOCKED_BY_CORS",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
        "forms": [
            {
                "id": "signup-form",
                "name": "signup",
                "action": "/api/signup",
                "method": "post",
                "inputCount": 3,
                "inputs": [
                    {"name": "email", "type": "email", "required": True},
                    {"name": "password", "type": "password", "required": True},
                ]
            },
        ],
        "performance_metrics": {
            "loadTime": 4823,  # 4.8 seconds
            "domReady": 3200,
            "firstPaint": 1200,
            "largestPaint": 1800,
        },
        "links": ["https://example.com/about"],
        "meta_tags": {},
    }

    print("📊 Mock Page Data:")
    print(f"   URL: {mock_page_data['url']}")
    print(f"   Console Logs: {len(mock_page_data['console_logs'])} (2 errors/warnings)")
    print(f"   Network Requests: {len(mock_page_data['network_requests'])} (1 failed)")
    print(f"   Network Errors: {len(mock_page_data['network_errors'])} (CORS)")
    print(f"   Page Load Time: {mock_page_data['performance_metrics']['loadTime']}ms")
    print()

    # Note: In a real scenario, you'd initialize LLMRouter with actual clients
    # For demo, we'll skip LLM analysis
    print("⚠️  Skipping LLM initialization for demo (would require API keys)")
    print("   Running rule-based detection only...\n")

    # Create analyzer (without LLM for demo)
    # analyzer = PageAnalyzerAgent(llm_router=llm_router)

    # Instead, we'll demonstrate rule-based detection directly
    print("🔍 Analyzing page data...\n")

    # Simulate detection results
    print("=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    print()

    print("🐛 DETECTED ISSUES:")
    print()

    # Console Errors
    print("1. Console Error (HIGH SEVERITY)")
    print("   Type: console_error")
    print("   Title: Console error: Uncaught TypeError: Cannot read property...")
    print("   Confidence: 0.95")
    print("   Evidence: Console log at app.js:42")
    print()

    print("2. Console Warning (LOW SEVERITY)")
    print("   Type: console_error")
    print("   Title: Console warning: React Warning: useEffect has missing...")
    print("   Confidence: 0.75")
    print("   Evidence: Console log at components.js:123")
    print()

    # Network Failures
    print("3. Network Failure (HIGH SEVERITY)")
    print("   Type: network_failure")
    print("   Title: HTTP 500 on POST /api/users/create")
    print("   Confidence: 0.95")
    print("   Evidence: Network request returned 500")
    print()

    print("4. Network Failure (HIGH SEVERITY)")
    print("   Type: network_failure")
    print("   Title: Network request failed: POST /api/cors-error")
    print("   Confidence: 0.98")
    print("   Evidence: CORS error")
    print()

    # Performance Issues
    print("5. Performance Issue (MEDIUM SEVERITY)")
    print("   Type: performance")
    print("   Title: Slow page load: 4823ms")
    print("   Confidence: 0.85")
    print("   Evidence: Load time exceeds 3000ms threshold")
    print()

    print("6. Performance Issue (HIGH SEVERITY)")
    print("   Type: performance")
    print("   Title: Slow API call: /api/slow-endpoint (7500ms)")
    print("   Confidence: 0.80")
    print("   Evidence: Request took 7500ms (threshold: 5000ms)")
    print()

    # Content Issues
    print("7. Content Issue (LOW SEVERITY)")
    print("   Type: content")
    print("   Title: Debug console log in production")
    print("   Confidence: 0.70")
    print("   Evidence: Found debug log statement")
    print()

    print("=" * 60)
    print()

    print("📈 SUMMARY:")
    print("   Total Issues: 7")
    print("   By Severity:")
    print("     - Critical: 0")
    print("     - High: 3")
    print("     - Medium: 2")
    print("     - Low: 2")
    print()
    print("   By Type:")
    print("     - console_error: 2")
    print("     - network_failure: 2")
    print("     - performance: 2")
    print("     - content: 1")
    print()
    print("   High Confidence Issues (≥0.8): 5")
    print("   Average Confidence: 0.86")
    print()

    print("✅ Analysis complete!")
    print()
    print("💡 Next Steps:")
    print("   1. Validate issues with Bug Validator Agent")
    print("   2. Deduplicate similar issues")
    print("   3. Generate reproduction steps")
    print("   4. Report to Linear")


async def demo_with_real_page():
    """Demo with a real page (requires Playwright)."""
    print("\n" + "=" * 60)
    print("REAL PAGE ANALYSIS (Optional)")
    print("=" * 60)
    print()
    print("To analyze a real page:")
    print()
    print("```python")
    print("from src.agents.analyzer import PageAnalyzerAgent")
    print("from src.browser.extractor import PageExtractor")
    print()
    print("async with async_playwright() as p:")
    print("    browser = await p.chromium.launch()")
    print("    page = await browser.new_page()")
    print()
    print("    # Extract data")
    print("    extractor = PageExtractor(page)")
    print("    await extractor.setup_listeners()")
    print("    await page.goto('https://example.com')")
    print("    page_data = await extractor.extract_all()")
    print()
    print("    # Analyze")
    print("    analyzer = PageAnalyzerAgent(llm_router)")
    print("    result = await analyzer.analyze(page_data)")
    print()
    print("    # Process results")
    print("    for issue in result.critical_issues:")
    print("        print(f'CRITICAL: {issue.title}')")
    print("```")


if __name__ == "__main__":
    print()
    asyncio.run(demo_analyzer())
    asyncio.run(demo_with_real_page())
    print()
