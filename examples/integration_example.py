"""Example showing PageAnalyzerAgent → BugClassifierAgent integration."""

import asyncio
from uuid import uuid4

# Note: This is a conceptual example showing how agents integrate.
# Requires full dependency installation to run.


async def example_analysis_and_classification():
    """
    Demonstrates the full pipeline from page analysis to classified bugs.

    Flow:
    1. PageAnalyzerAgent analyzes a page
    2. Detects raw issues (RawIssue objects)
    3. BugClassifierAgent processes issues
    4. Returns classified Bug objects
    5. Bugs stored in BugRepository
    """
    from src.agents import PageAnalyzerAgent, BugClassifierAgent
    from src.llm import LLMRouter, AnthropicClient, OpenRouterClient, CostTracker
    from src.db.repositories import BugRepository

    print("🔬 BugHive Agent Pipeline Demo")
    print("=" * 70)
    print()

    # Initialize infrastructure
    print("⚙️  Initializing LLM infrastructure...")
    anthropic_client = AnthropicClient()
    openrouter_client = OpenRouterClient()
    cost_tracker = CostTracker()
    llm_router = LLMRouter(anthropic_client, openrouter_client, cost_tracker)
    print("✓ LLM router initialized")
    print()

    # Initialize agents
    print("🤖 Initializing agents...")
    analyzer = PageAnalyzerAgent(llm_router)
    classifier = BugClassifierAgent(llm_router)
    print("✓ PageAnalyzerAgent ready")
    print("✓ BugClassifierAgent ready")
    print()

    # Initialize database
    print("💾 Connecting to database...")
    bug_repo = BugRepository()
    print("✓ BugRepository connected")
    print()

    # Session identifiers
    session_id = uuid4()
    page_id = uuid4()
    target_url = "https://example.com/products"

    print(f"🎯 Target: {target_url}")
    print(f"📊 Session: {session_id}")
    print()
    print("=" * 70)
    print()

    # Step 1: Analyze page
    print("STEP 1: Page Analysis")
    print("-" * 70)
    print(f"🔍 Analyzing page: {target_url}")

    # PageAnalyzerAgent scrapes the page and detects issues
    analysis_result = await analyzer.analyze(
        url=target_url,
        page_id=page_id,
        session_id=session_id,
    )

    print(f"✓ Analysis complete in {analysis_result.analysis_time:.2f}s")
    print(f"✓ {analysis_result.total_issues} raw issues detected")
    print()

    if analysis_result.total_issues > 0:
        print("Issues by type:")
        for issue_type, count in analysis_result.issues_by_type.items():
            print(f"  {issue_type:15s} {count}")
        print()

        print("Issues by severity:")
        for severity, count in analysis_result.issues_by_severity.items():
            print(f"  {severity:15s} {count}")
        print()

    print("=" * 70)
    print()

    # Step 2: Classify bugs
    print("STEP 2: Bug Classification")
    print("-" * 70)
    print(f"🏷️  Classifying {len(analysis_result.issues_found)} issues...")

    # BugClassifierAgent classifies and deduplicates issues
    bugs = await classifier.process_issues(
        issues=analysis_result.issues_found,
        session_id=session_id,
        page_id=page_id,
    )

    print(f"✓ Classification complete")
    print(f"✓ {len(bugs)} unique bugs identified")
    print()

    if bugs:
        print("Bugs by priority:")
        priority_counts = {}
        for bug in bugs:
            priority_counts[bug.priority] = priority_counts.get(bug.priority, 0) + 1

        for priority in ["critical", "high", "medium", "low"]:
            count = priority_counts.get(priority, 0)
            bar = "█" * count
            print(f"  {priority.upper():10s} {bar} {count}")
        print()

        print("Bugs by category:")
        category_counts = {}
        for bug in bugs:
            category_counts[bug.category] = category_counts.get(bug.category, 0) + 1

        for category, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            bar = "█" * count
            print(f"  {category:12s} {bar} {count}")
        print()

    print("=" * 70)
    print()

    # Step 3: Store bugs
    print("STEP 3: Database Storage")
    print("-" * 70)
    print(f"💾 Storing {len(bugs)} bugs in database...")

    stored_count = 0
    for bug in bugs:
        # Store in database
        bug_id = await bug_repo.create(bug)
        stored_count += 1
        print(f"  ✓ Stored: {bug.priority:8s} | {bug.category:12s} | {bug.title[:40]}...")

    print()
    print(f"✓ {stored_count} bugs stored successfully")
    print()

    print("=" * 70)
    print()

    # Step 4: Show sample bug
    if bugs:
        print("STEP 4: Sample Bug Report")
        print("-" * 70)

        # Find highest priority bug
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sample_bug = min(bugs, key=lambda b: priority_order[b.priority])

        print(f"Title:       {sample_bug.title}")
        print(f"Category:    {sample_bug.category}")
        print(f"Priority:    {sample_bug.priority.upper()}")
        print(f"Confidence:  {sample_bug.confidence:.2%}")
        print(f"Status:      {sample_bug.status}")
        print()

        print("Description:")
        print(f"  {sample_bug.description}")
        print()

        print("Steps to Reproduce:")
        for i, step in enumerate(sample_bug.steps_to_reproduce, 1):
            print(f"  {i}. {step}")
        print()

        print(f"Expected:    {sample_bug.expected_behavior}")
        print(f"Actual:      {sample_bug.actual_behavior}")
        print(f"Affected:    {sample_bug.affected_users}")
        print(f"Evidence:    {len(sample_bug.evidence)} item(s)")
        print()

        print("=" * 70)
        print()

    # Summary
    print("📈 Session Summary")
    print("-" * 70)
    print(f"Pages analyzed:       1")
    print(f"Raw issues detected:  {analysis_result.total_issues}")
    print(f"Unique bugs found:    {len(bugs)}")
    print(f"Bugs stored:          {stored_count}")
    print(f"Analysis time:        {analysis_result.analysis_time:.2f}s")
    print()

    # Cost summary
    print("💰 Cost Summary")
    print("-" * 70)
    costs = cost_tracker.get_session_summary(str(session_id))
    print(f"Analyzer cost:        ${costs.get('analyzer', 0):.4f}")
    print(f"Classifier cost:      ${costs.get('classifier', 0):.4f}")
    print(f"Total session cost:   ${costs.get('total', 0):.4f}")
    print()

    print("=" * 70)
    print()
    print("✅ Pipeline complete!")
    print()
    print("Next steps:")
    print("  1. ValidatorAgent validates high-confidence bugs")
    print("  2. ReporterAgent creates Linear tickets for validated bugs")
    print("  3. Monitor bugs in BugHive dashboard")
    print()


async def quick_classification_demo():
    """
    Simplified demo showing just classification without full infrastructure.

    This demonstrates the classifier with mock data, no LLM or DB required.
    """
    from src.agents import BugClassifierAgent
    from src.models.raw_issue import RawIssue
    from src.models.evidence import Evidence
    from datetime import datetime
    from uuid import uuid4

    print("🏷️  Bug Classifier Quick Demo")
    print("=" * 70)
    print()

    # Create classifier (no LLM for demo)
    classifier = BugClassifierAgent(llm_router=None)

    # Create mock issues
    issues = [
        RawIssue(
            type="security",
            title="XSS vulnerability in search",
            description="User input not escaped in search results",
            confidence=0.95,
            url="https://example.com/search",
            evidence=[Evidence(
                type="security_scan",
                content="XSS detected",
                timestamp=datetime.utcnow()
            )],
        ),
        RawIssue(
            type="network_failure",
            title="HTTP 500 on /api/users",
            description="Server error creating user",
            confidence=0.92,
            url="https://example.com/signup",
            evidence=[],
        ),
        RawIssue(
            type="visual",
            title="Button overlaps text on mobile",
            description="Submit button position incorrect on 375px viewport",
            confidence=0.88,
            url="https://example.com/contact",
            evidence=[],
        ),
    ]

    session_id = uuid4()
    page_id = uuid4()

    print(f"📊 Processing {len(issues)} issues...")
    print()

    # Classify without LLM (rule-based only)
    bugs = []
    for issue in issues:
        bug = await classifier._classify_issue(issue, session_id, page_id)
        bugs.append(bug)

        print(f"✓ {issue.type}")
        print(f"  Title:    {bug.title[:50]}...")
        print(f"  Category: {bug.category}")
        print(f"  Priority: {bug.priority.upper()}")
        print(f"  Steps:    {len(bug.steps_to_reproduce)} steps")
        print()

    print("=" * 70)
    print()
    print("✅ Classification complete!")
    print()


if __name__ == "__main__":
    import sys

    if "--quick" in sys.argv:
        # Quick demo with no dependencies
        asyncio.run(quick_classification_demo())
    else:
        # Full pipeline demo (requires dependencies)
        print("Note: Full demo requires dependencies installed.")
        print("Run with --quick for simplified demo.")
        print()
        asyncio.run(example_analysis_and_classification())
