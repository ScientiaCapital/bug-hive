"""Simple test of MockLinearClient without dependencies.

This test demonstrates the Linear integration without requiring
any external dependencies or API keys.

Run:
    python3 examples/test_linear_mock_only.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import only what we need (avoid LLM dependencies)
# Import directly to avoid loading __init__.py which imports reporter
from src.integrations.linear import LinearIssue
from src.integrations.linear_mock import MockLinearClient


async def test_mock_client():
    """Test MockLinearClient operations."""
    print("\n" + "="*60)
    print("MockLinearClient Test Suite")
    print("="*60)

    # Create client
    client = MockLinearClient()
    print("\n✅ Created MockLinearClient")

    # Test 1: Create issue
    print("\n--- Test 1: Create Issue ---")
    issue1 = await client.create_issue(
        title="Submit button not responding",
        description="The submit button on the checkout page does not respond to clicks.",
        team_id="qa-team",
        priority=2,  # High
        labels=["bug", "frontend"],
        attachments=["https://example.com/screenshot1.png"]
    )
    print(f"✅ Created: {issue1.identifier}")
    print(f"   Title: {issue1.title}")
    print(f"   URL: {issue1.url}")
    print(f"   Priority: {issue1.priority} (2=High)")

    # Test 2: Create another issue
    print("\n--- Test 2: Create Second Issue ---")
    issue2 = await client.create_issue(
        title="Login page 500 error",
        description="Login page returns 500 error when accessed",
        team_id="backend-team",
        priority=1,  # Urgent
        labels=["critical", "backend"]
    )
    print(f"✅ Created: {issue2.identifier}")
    print(f"   Title: {issue2.title}")
    print(f"   Priority: {issue2.priority} (1=Urgent)")

    # Test 3: Get issue
    print("\n--- Test 3: Get Issue ---")
    retrieved = await client.get_issue(issue1.id)
    if retrieved:
        print(f"✅ Retrieved: {retrieved.identifier}")
        print(f"   Title: {retrieved.title}")
    else:
        print("❌ Failed to retrieve issue")

    # Test 4: Update issue
    print("\n--- Test 4: Update Issue ---")
    updated = await client.update_issue(
        issue_id=issue1.id,
        title="Updated: Submit button not responding on mobile",
        priority=1  # Upgrade to urgent
    )
    print(f"✅ Updated: {updated.identifier}")
    print(f"   New title: {updated.title}")
    print(f"   New priority: {updated.priority} (1=Urgent)")

    # Test 5: Get team ID
    print("\n--- Test 5: Get Team ID ---")
    team_id = await client.get_team_id("engineering")
    print(f"✅ Team ID: {team_id}")

    # Test 6: Get all issues
    print("\n--- Test 6: Get All Issues ---")
    all_issues = client.get_all_issues()
    print(f"✅ Total issues created: {len(all_issues)}")
    for issue in all_issues:
        print(f"   - {issue.identifier}: {issue.title}")

    # Test 7: Error handling
    print("\n--- Test 7: Error Handling ---")
    try:
        await client.update_issue("invalid-id", title="Test")
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}")

    print("\n" + "="*60)
    print("All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_mock_client())
