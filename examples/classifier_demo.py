"""Demo of Bug Classifier Agent usage."""

import asyncio
from datetime import datetime
from uuid import uuid4

from src.agents.classifier import BugClassifierAgent
from src.models.evidence import Evidence
from src.models.raw_issue import RawIssue


async def demo_classification():
    """Demonstrate bug classification without LLM (rule-based only)."""
    print("=" * 70)
    print("Bug Classifier Agent Demo")
    print("=" * 70)
    print()

    # Create classifier (without LLM for demo)
    classifier = BugClassifierAgent(llm_router=None)

    # Create sample raw issues
    raw_issues = [
        RawIssue(
            type="console_error",
            title="Uncaught TypeError: Cannot read property 'map' of undefined",
            description=(
                "JavaScript error in product listing component. "
                "Occurs when trying to render products array."
            ),
            confidence=0.95,
            url="https://example.com/products",
            evidence=[
                Evidence(
                    type="console_log",
                    content='{"level": "error", "message": "TypeError at line 42"}',
                    timestamp=datetime.utcnow(),
                )
            ],
        ),
        RawIssue(
            type="network_failure",
            title="HTTP 500 Internal Server Error on POST /api/users",
            description=(
                "Server returns 500 error when attempting to create new user. "
                "Occurs consistently on signup form submission."
            ),
            confidence=0.98,
            url="https://example.com/signup",
            evidence=[
                Evidence(
                    type="network_request",
                    content='{"url": "/api/users", "status": 500, "method": "POST"}',
                    timestamp=datetime.utcnow(),
                )
            ],
        ),
        RawIssue(
            type="visual",
            title="Submit button overlaps form text on mobile",
            description=(
                "On mobile viewports (< 768px), the submit button overlaps "
                "with the email input field label."
            ),
            confidence=0.85,
            url="https://example.com/contact",
            evidence=[
                Evidence(
                    type="screenshot",
                    content="https://storage.example.com/screenshots/mobile-overlap.png",
                    timestamp=datetime.utcnow(),
                )
            ],
        ),
        RawIssue(
            type="security",
            title="Potential XSS vulnerability in search query",
            description=(
                "User input in search query is not properly escaped. "
                "Able to inject script tags that execute in browser."
            ),
            confidence=0.92,
            url="https://example.com/search?q=<script>alert('xss')</script>",
            evidence=[
                Evidence(
                    type="security_scan",
                    content='{"vulnerability": "XSS", "cwe": "CWE-79"}',
                    timestamp=datetime.utcnow(),
                )
            ],
        ),
        RawIssue(
            type="performance",
            title="Slow page load: 4823ms",
            description=(
                "Product listing page takes 4.8 seconds to load, "
                "exceeding the 3 second threshold. Large bundle size detected."
            ),
            confidence=0.88,
            url="https://example.com/products",
            evidence=[
                Evidence(
                    type="performance_metrics",
                    content='{"loadTime": 4823, "domReady": 3200, "bundleSize": "2.4MB"}',
                    timestamp=datetime.utcnow(),
                )
            ],
        ),
        RawIssue(
            type="form",
            title="Email validation accepts invalid format",
            description=(
                "Form accepts email addresses without @ symbol. "
                "Validation regex appears to be incorrect."
            ),
            confidence=0.90,
            url="https://example.com/signup",
            evidence=[
                Evidence(
                    type="form_interaction",
                    content='{"field": "email", "value": "invalidemail.com", "accepted": true}',
                    timestamp=datetime.utcnow(),
                )
            ],
        ),
        # Duplicate of first issue (different page)
        RawIssue(
            type="console_error",
            title="Uncaught TypeError: Cannot read property 'map' of undefined",
            description=(
                "Same JavaScript error but on cart page. "
                "Likely same root cause in shared component."
            ),
            confidence=0.93,
            url="https://example.com/cart",
            evidence=[
                Evidence(
                    type="console_log",
                    content='{"level": "error", "message": "TypeError at line 42"}',
                    timestamp=datetime.utcnow(),
                )
            ],
        ),
        RawIssue(
            type="visual",
            title="Minor color inconsistency in footer links",
            description=(
                "Footer links are #333333 instead of brand blue #2E5090. "
                "Purely cosmetic styling issue."
            ),
            confidence=0.60,
            url="https://example.com",
            evidence=[],
        ),
    ]

    # Session identifiers
    session_id = uuid4()
    page_id = uuid4()

    print(f"📊 Input: {len(raw_issues)} raw issues detected\n")

    # Classify issues (rule-based only for demo)
    print("🔍 Classifying issues...")
    print("-" * 70)

    classified_bugs = []
    for i, issue in enumerate(raw_issues, 1):
        print(f"\n[{i}/{len(raw_issues)}] {issue.type}: {issue.title[:50]}...")
        print(f"  Confidence: {issue.confidence:.2%}")

        # Use internal method for demo (normally call process_issues)
        bug = await classifier._classify_issue(issue, session_id, page_id)

        print(f"  → Category: {bug.category}")
        print(f"  → Priority: {bug.priority.upper()}")
        print(f"  → Steps: {len(bug.steps_to_reproduce)} steps to reproduce")
        print(f"  → Affected: {bug.affected_users}")

        classified_bugs.append(bug)

    print()
    print("=" * 70)
    print()

    # Check for duplicates
    print("🔄 Deduplication check...")
    print("-" * 70)

    unique_bugs = []
    duplicates = []

    for bug in classified_bugs:
        if await classifier._is_duplicate(bug, unique_bugs):
            duplicates.append(bug)
            print(f"  ✗ DUPLICATE: {bug.title[:50]}...")
        else:
            unique_bugs.append(bug)
            print(f"  ✓ UNIQUE: {bug.title[:50]}...")

    print()
    print("=" * 70)
    print()

    # Summary statistics
    print("📈 Classification Results")
    print("-" * 70)
    print(f"Total issues analyzed:    {len(raw_issues)}")
    print(f"Unique bugs identified:   {len(unique_bugs)}")
    print(f"Duplicates removed:       {len(duplicates)}")
    print()

    # By priority
    print("Priority Breakdown:")
    priority_counts = {}
    for bug in unique_bugs:
        priority_counts[bug.priority] = priority_counts.get(bug.priority, 0) + 1

    for priority in ["critical", "high", "medium", "low"]:
        count = priority_counts.get(priority, 0)
        bar = "█" * count
        print(f"  {priority.capitalize():10s} {bar} {count}")

    print()

    # By category
    print("Category Breakdown:")
    category_counts = {}
    for bug in unique_bugs:
        category_counts[bug.category] = category_counts.get(bug.category, 0) + 1

    for category in ["security", "data", "ui_ux", "performance", "edge_case"]:
        count = category_counts.get(category, 0)
        bar = "█" * count
        print(f"  {category:12s} {bar} {count}")

    print()

    # Average confidence
    avg_confidence = sum(bug.confidence for bug in unique_bugs) / len(unique_bugs)
    print(f"Average confidence:       {avg_confidence:.2%}")

    print()
    print("=" * 70)
    print()

    # Show sample bug details
    print("📋 Sample Bug Report")
    print("-" * 70)

    # Show the critical security bug
    security_bug = next(
        (bug for bug in unique_bugs if bug.category == "security"), None
    )

    if security_bug:
        print(f"Title: {security_bug.title}")
        print(f"Category: {security_bug.category}")
        print(f"Priority: {security_bug.priority.upper()}")
        print(f"Confidence: {security_bug.confidence:.2%}")
        print()
        print("Description:")
        print(f"  {security_bug.description}")
        print()
        print("Steps to Reproduce:")
        for i, step in enumerate(security_bug.steps_to_reproduce, 1):
            print(f"  {i}. {step}")
        print()
        print(f"Expected: {security_bug.expected_behavior}")
        print(f"Affected: {security_bug.affected_users}")
        print(f"Evidence: {len(security_bug.evidence)} item(s)")

    print()
    print("=" * 70)
    print()
    print("✅ Demo complete!")
    print()

    # Show cost savings
    print("💰 Cost Optimization")
    print("-" * 70)
    high_conf_count = sum(1 for issue in raw_issues if issue.confidence >= 0.8)
    low_conf_count = len(raw_issues) - high_conf_count

    print(f"High confidence issues (>= 0.8): {high_conf_count}")
    print(f"  → Rule-based classification (FREE)")
    print()
    print(f"Low confidence issues (< 0.8):   {low_conf_count}")
    print(f"  → Would use LLM classification (~$0.0001 each)")
    print()
    estimated_cost = low_conf_count * 0.0001
    print(f"Estimated cost for this batch: ${estimated_cost:.4f}")
    print(f"Cost savings from rule-based:  ${high_conf_count * 0.0001:.4f}")

    print()


if __name__ == "__main__":
    asyncio.run(demo_classification())
