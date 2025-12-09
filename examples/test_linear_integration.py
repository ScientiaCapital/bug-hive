"""Example script demonstrating Linear integration.

This script shows how to use the Linear integration layer with both
mock and real clients.

Run:
    python examples/test_linear_integration.py
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import BugHive components
from src.integrations import get_linear_client, get_reporter_agent
from src.models.bug import Bug, Evidence
from src.llm import LLMRouter


async def test_mock_client():
    """Test MockLinearClient directly."""
    print("\n" + "="*60)
    print("TEST 1: MockLinearClient Direct Usage")
    print("="*60)

    # Get mock client (no API key needed)
    client = get_linear_client()

    # Create a test issue
    issue = await client.create_issue(
        title="Test bug: Button not working",
        description="The submit button does not respond to clicks.",
        team_id="qa-team",
        priority=2,  # High priority
        labels=["bug", "frontend"],
        attachments=["https://example.com/screenshot.png"]
    )

    print(f"\n✅ Created issue: {issue.identifier}")
    print(f"   Title: {issue.title}")
    print(f"   URL: {issue.url}")
    print(f"   Priority: {issue.priority}")

    # Get the issue
    retrieved = await client.get_issue(issue.id)
    print(f"\n✅ Retrieved issue: {retrieved.identifier}")

    # Update the issue
    updated = await client.update_issue(
        issue.id,
        title="Updated: Button not working on checkout",
        priority=1  # Urgent
    )
    print(f"\n✅ Updated issue: {updated.identifier}")
    print(f"   New title: {updated.title}")
    print(f"   New priority: {updated.priority}")

    # Get team ID
    team_id = await client.get_team_id("engineering")
    print(f"\n✅ Team ID for 'engineering': {team_id}")


async def test_reporter_agent():
    """Test ReportWriterAgent with mock LLM."""
    print("\n" + "="*60)
    print("TEST 2: ReportWriterAgent")
    print("="*60)

    # Import UUID for creating a proper Bug
    from uuid import uuid4

    # Create a sample bug (using actual Bug model fields)
    bug = Bug(
        id=uuid4(),
        session_id=uuid4(),
        page_id=uuid4(),
        title="Login button unresponsive on mobile",
        description="When testing on mobile devices, the login button does not respond to touch events.",
        category="ui_ux",  # Use valid category from Bug model
        priority="high",
        steps_to_reproduce=[
            "Navigate to https://example.com/login on mobile device",
            "Tap the login button",
            "Observe no response to touch events"
        ],
        confidence=0.90,
        evidence=[
            Evidence(
                type="screenshot",
                content="https://example.com/screenshots/login-bug.png",
                timestamp=datetime.now()
            ),
            Evidence(
                type="console_log",
                content="TypeError: Cannot read property 'addEventListener' of null\n    at login.js:42:15",
                timestamp=datetime.now()
            )
        ]
    )

    print(f"\n📝 Bug to report:")
    print(f"   Title: {bug.title}")
    print(f"   Category: {bug.category}")
    print(f"   Priority: {bug.priority}")
    print(f"   Evidence count: {len(bug.evidence)}")

    # Note: This requires actual LLM credentials
    # For now, we'll skip the LLM part and just test the Linear integration
    try:
        # Initialize LLM router (will fail without API keys - expected)
        llm_router = LLMRouter(
            anthropic_api_key="test-key",
            openrouter_api_key="test-key"
        )

        # Get reporter agent with mock Linear client
        reporter = get_reporter_agent(llm_router)

        # This would create the ticket (will fail without real LLM)
        # issue = await reporter.create_ticket(bug, team_id="qa-team")
        # print(f"\n✅ Created Linear issue: {issue.identifier}")

        print("\n⚠️  Skipping actual ticket creation (requires LLM API keys)")
        print("   In production, this would:")
        print("   1. Format the bug using LLM (Qwen 32B)")
        print("   2. Create a Linear issue with formatted content")
        print("   3. Return the issue URL")

    except Exception as e:
        print(f"\n⚠️  Expected error (no real API keys): {type(e).__name__}")


async def test_manual_report():
    """Test creating a ticket without LLM (manual formatting)."""
    print("\n" + "="*60)
    print("TEST 3: Manual Ticket Creation (No LLM)")
    print("="*60)

    # Import UUID for creating a proper Bug
    from uuid import uuid4

    # Create a sample bug (using actual Bug model fields)
    bug = Bug(
        id=uuid4(),
        session_id=uuid4(),
        page_id=uuid4(),
        title="404 error on profile page",
        description="Users get 404 when navigating to /profile",
        category="data",  # Use valid category from Bug model
        priority="critical",
        steps_to_reproduce=[
            "Navigate to https://example.com/profile",
            "Observe 404 error",
            "Check network tab"
        ],
        confidence=0.95,
        evidence=[
            Evidence(
                type="network_request",
                content="GET /api/profile 404 Not Found",
                timestamp=datetime.now()
            )
        ]
    )

    # Get mock client
    client = get_linear_client()

    # Format report manually (without LLM)
    steps = "\n".join([f"{i}. {step}" for i, step in enumerate(bug.steps_to_reproduce, 1)])

    report = f"""## Summary
{bug.description}

## Steps to Reproduce
{steps}

## Evidence
- Network Request: {bug.evidence[0].content}

## Environment
- Bug ID: {bug.id}
- Browser: Chrome (via Browserbase)
- Timestamp: {bug.created_at.isoformat()}

## Suggested Priority
**{bug.priority}** - Breaks core functionality
"""

    # Create ticket
    issue = await client.create_issue(
        title=bug.title,
        description=report,
        team_id="engineering",
        priority=1,  # Critical
        labels=[bug.category]
    )

    print(f"\n✅ Created issue: {issue.identifier}")
    print(f"   Title: {issue.title}")
    print(f"   URL: {issue.url}")
    print(f"   Priority: {issue.priority} (1=Urgent)")


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("BugHive Linear Integration Test Suite")
    print("="*60)

    await test_mock_client()
    await test_reporter_agent()
    await test_manual_report()

    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
