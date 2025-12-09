"""Example usage of BugHive database layer."""

import asyncio
from datetime import datetime

from src.db import (
    BugRepository,
    CrawlSessionRepository,
    PageRepository,
    close_database,
    get_database,
    init_database,
)
from src.models import CrawlConfig, Evidence


async def main():
    """Demonstrate database layer usage."""

    # Initialize database
    print("Initializing database...")
    await init_database(drop_existing=True)

    db = get_database()

    async with db.session() as session:
        # Create repositories
        session_repo = CrawlSessionRepository(session)
        page_repo = PageRepository(session)
        bug_repo = BugRepository(session)

        print("\n1. Creating crawl session...")
        # Create a crawl session
        config = CrawlConfig(
            base_url="https://example.com",
            auth_method="none",
            max_pages=50,
            max_depth=3,
        )

        crawl_session = await session_repo.create_session(
            base_url="https://example.com",
            config=config,
        )
        print(f"   Created session: {crawl_session.id}")
        print(f"   Status: {crawl_session.status}")

        # Start the session
        print("\n2. Starting crawl session...")
        await session_repo.start_session(crawl_session.id)
        print("   Session started")

        # Create pages
        print("\n3. Creating pages...")
        base_page = await page_repo.create_page(
            session_id=crawl_session.id,
            url="https://example.com",
            depth=0,
            title="Example Domain",
        )
        print(f"   Created base page: {base_page.url}")

        about_page = await page_repo.create_page(
            session_id=crawl_session.id,
            url="https://example.com/about",
            depth=1,
            parent_page_id=base_page.id,
            title="About Us",
        )
        print(f"   Created about page: {about_page.url}")

        products_page = await page_repo.create_page(
            session_id=crawl_session.id,
            url="https://example.com/products",
            depth=1,
            parent_page_id=base_page.id,
            title="Products",
        )
        print(f"   Created products page: {products_page.url}")

        # Update page statuses
        print("\n4. Updating page statuses...")
        await page_repo.mark_crawling(about_page.id)
        await page_repo.mark_analyzed(
            about_page.id,
            screenshot_url="https://storage.example.com/screenshots/about.png",
            response_time_ms=234,
            status_code=200,
        )
        print("   Marked about page as analyzed")

        # Create bugs
        print("\n5. Creating bugs...")
        evidence = [
            Evidence(
                type="screenshot",
                content="https://storage.example.com/screenshots/bug1.png",
                timestamp=datetime.utcnow(),
            ),
            Evidence(
                type="console_log",
                content='{"level": "error", "message": "TypeError: Cannot read property..."}',
                timestamp=datetime.utcnow(),
            ),
        ]

        bug1 = await bug_repo.create_bug(
            session_id=crawl_session.id,
            page_id=about_page.id,
            category="ui_ux",
            priority="high",
            title="Submit button overlaps text on mobile",
            description="On mobile viewports (< 768px), the submit button overlaps the form label text.",
            steps_to_reproduce=[
                "Navigate to /about",
                "Resize browser to 375px width",
                "Observe button overlapping text",
            ],
            evidence=evidence,
            confidence=0.92,
            expected_behavior="Button should be properly positioned below the text",
            actual_behavior="Button overlaps and obscures the text",
            affected_users="Mobile users",
        )
        print(f"   Created bug 1: {bug1.title}")

        bug2 = await bug_repo.create_bug(
            session_id=crawl_session.id,
            page_id=products_page.id,
            category="performance",
            priority="medium",
            title="Slow page load time",
            description="Products page takes over 5 seconds to load.",
            steps_to_reproduce=[
                "Navigate to /products",
                "Measure load time",
            ],
            evidence=[
                Evidence(
                    type="network_request",
                    content='{"url": "/api/products", "duration": 5200}',
                    timestamp=datetime.utcnow(),
                )
            ],
            confidence=0.85,
        )
        print(f"   Created bug 2: {bug2.title}")

        bug3 = await bug_repo.create_bug(
            session_id=crawl_session.id,
            page_id=products_page.id,
            category="data",
            priority="critical",
            title="Product prices show as NaN",
            description="Product prices are displaying as 'NaN' instead of actual prices.",
            steps_to_reproduce=[
                "Navigate to /products",
                "Observe price field",
            ],
            evidence=[
                Evidence(
                    type="screenshot",
                    content="https://storage.example.com/screenshots/nan-prices.png",
                    timestamp=datetime.utcnow(),
                )
            ],
            confidence=0.98,
        )
        print(f"   Created bug 3: {bug3.title}")

        # Update session metrics
        print("\n6. Updating session metrics...")
        await session_repo.update_metrics(
            crawl_session.id,
            pages_discovered=3,
            pages_crawled=2,
            bugs_found=3,
            total_cost=0.15,
        )
        print("   Metrics updated")

        # Query data
        print("\n7. Querying data...")

        # Get session statistics
        stats = await session_repo.get_session_statistics(crawl_session.id)
        print(f"   Session stats: {stats}")

        # Get high confidence bugs
        high_confidence = await bug_repo.get_high_confidence_bugs(
            crawl_session.id,
            min_confidence=0.9
        )
        print(f"   High confidence bugs: {len(high_confidence)}")
        for bug in high_confidence:
            print(f"     - {bug.title} (confidence: {bug.confidence})")

        # Get critical bugs
        critical = await bug_repo.get_critical_bugs(crawl_session.id)
        print(f"   Critical bugs: {len(critical)}")
        for bug in critical:
            print(f"     - {bug.title}")

        # Get bug statistics
        bug_stats = await bug_repo.get_bug_statistics(crawl_session.id)
        print("   Bug statistics:")
        print(f"     Total: {bug_stats['total_bugs']}")
        print(f"     By priority: {bug_stats['bugs_by_priority']}")
        print(f"     By category: {bug_stats['bugs_by_category']}")
        print(f"     Avg confidence: {bug_stats['average_confidence']:.2%}")

        # Get page analytics
        page_analytics = await page_repo.get_page_analytics(products_page.id)
        print(f"   Page analytics for {products_page.url}:")
        print(f"     Bugs found: {page_analytics['bugs_found']}")
        print(f"     By priority: {page_analytics['bug_severity_distribution']}")

        # Get navigation graph
        nav_graph = await page_repo.get_navigation_graph(crawl_session.id)
        print("   Navigation graph:")
        for parent, children in nav_graph.items():
            print(f"     {parent}")
            for child in children:
                print(f"       -> {child}")

        # Report a bug to Linear
        print("\n8. Reporting bug to Linear...")
        await bug_repo.mark_reported(
            bug3.id,
            linear_issue_id="BUG-123",
            linear_issue_url="https://linear.app/team/issue/BUG-123"
        )
        print(f"   Reported bug: {bug3.title}")

        # Dismiss a bug
        print("\n9. Dismissing bug...")
        await bug_repo.mark_dismissed(
            bug2.id,
            reason="Performance is acceptable for current traffic"
        )
        print(f"   Dismissed bug: {bug2.title}")

        # Complete session
        print("\n10. Completing session...")
        await session_repo.complete_session(
            crawl_session.id,
            success=True
        )
        print("   Session completed")

        # Final statistics
        print("\n11. Final session statistics:")
        final_stats = await session_repo.get_session_statistics(crawl_session.id)
        print(f"   Status: {final_stats['status']}")
        print(f"   Pages discovered: {final_stats['pages_discovered']}")
        print(f"   Pages crawled: {final_stats['pages_crawled']}")
        print(f"   Bugs found: {final_stats['bugs_found']}")
        print(f"   Total cost: ${final_stats['total_cost']:.2f}")
        print(f"   Duration: {final_stats['duration_seconds']:.2f}s")

        # Recent sessions
        print("\n12. Listing recent sessions...")
        recent = await session_repo.get_recent_sessions(limit=5)
        print(f"   Found {len(recent)} recent sessions")
        for s in recent:
            print(f"     - {s.base_url} ({s.status}) - {s.bugs_found} bugs")

    # Cleanup
    print("\n13. Closing database...")
    await close_database()
    print("   Done!")


if __name__ == "__main__":
    asyncio.run(main())
