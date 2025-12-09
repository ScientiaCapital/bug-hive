"""Test script to verify BugClassifierAgent logic (without dependencies)."""

# Test the classification mapping logic
def test_category_mapping():
    """Verify issue type to category mapping."""
    from src.agents.classifier import BugClassifierAgent

    agent = BugClassifierAgent(llm_router=None)  # No LLM needed for rules

    test_cases = {
        "console_error": "ui_ux",
        "network_failure": "data",
        "performance": "performance",
        "visual": "ui_ux",
        "content": "data",
        "form": "edge_case",
        "accessibility": "ui_ux",
        "security": "security",
    }

    for issue_type, expected_category in test_cases.items():
        result = agent._get_category_from_type(issue_type)
        assert result == expected_category, f"Expected {expected_category}, got {result}"
        print(f"✓ {issue_type} → {expected_category}")

    print("\n✅ Category mapping tests passed")


def test_priority_estimation():
    """Verify priority estimation logic."""
    from src.models.raw_issue import RawIssue
    from src.agents.classifier import BugClassifierAgent

    agent = BugClassifierAgent(llm_router=None)

    # Critical: security
    issue = RawIssue(
        type="security",
        title="XSS vulnerability in search",
        description="Unescaped user input",
        confidence=0.95,
    )
    priority = agent._estimate_priority(issue)
    assert priority == "critical", f"Security should be critical, got {priority}"
    print(f"✓ Security issue → critical")

    # High: 500 error
    issue = RawIssue(
        type="network_failure",
        title="HTTP 500 on /api/users",
        description="Server error",
        confidence=0.90,
    )
    priority = agent._estimate_priority(issue)
    assert priority == "high", f"500 error should be high, got {priority}"
    print(f"✓ 500 error → high")

    # Medium: good confidence
    issue = RawIssue(
        type="visual",
        title="Button misaligned",
        description="Submit button is 5px too low",
        confidence=0.75,
    )
    priority = agent._estimate_priority(issue)
    assert priority == "medium", f"Visual with good confidence should be medium, got {priority}"
    print(f"✓ Visual defect (0.75 conf) → medium")

    # Low: cosmetic
    issue = RawIssue(
        type="visual",
        title="Minor styling issue",
        description="Button color slightly off",
        confidence=0.60,
    )
    priority = agent._estimate_priority(issue)
    assert priority == "low", f"Cosmetic should be low, got {priority}"
    print(f"✓ Cosmetic issue → low")

    print("\n✅ Priority estimation tests passed")


def test_steps_generation():
    """Verify steps to reproduce generation."""
    from src.models.raw_issue import RawIssue
    from src.agents.classifier import BugClassifierAgent

    agent = BugClassifierAgent(llm_router=None)

    # Console error
    issue = RawIssue(
        type="console_error",
        title="TypeError in app.js",
        description="Cannot read property 'map' of undefined",
        confidence=0.90,
        url="https://example.com/products",
    )
    steps = agent._generate_steps(issue)
    assert "Navigate to https://example.com/products" in steps
    assert "developer console" in steps[1].lower()
    print(f"✓ Console error steps: {len(steps)} steps generated")

    # Network failure
    issue = RawIssue(
        type="network_failure",
        title="HTTP 500",
        description="API error",
        confidence=0.95,
        url="https://example.com/api",
    )
    steps = agent._generate_steps(issue)
    assert "Network tab" in steps[1]
    print(f"✓ Network failure steps: {len(steps)} steps generated")

    # Security issue
    issue = RawIssue(
        type="security",
        title="XSS vulnerability",
        description="Unescaped input",
        confidence=0.98,
    )
    steps = agent._generate_steps(issue)
    assert any("⚠️" in step or "WARNING" in step for step in steps)
    print(f"✓ Security issue includes warning")

    print("\n✅ Steps generation tests passed")


def test_similarity_computation():
    """Verify text similarity computation."""
    from src.agents.classifier import BugClassifierAgent
    import asyncio

    agent = BugClassifierAgent(llm_router=None)

    async def run_tests():
        # Identical text
        sim = await agent._compute_similarity(
            "Button is misaligned on mobile",
            "Button is misaligned on mobile"
        )
        assert sim == 1.0, f"Identical should be 1.0, got {sim}"
        print(f"✓ Identical text: {sim:.2f}")

        # Very similar
        sim = await agent._compute_similarity(
            "Submit button overlaps text",
            "Submit button overlaps content"
        )
        assert sim > 0.5, f"Similar should be > 0.5, got {sim}"
        print(f"✓ Similar text: {sim:.2f}")

        # Different
        sim = await agent._compute_similarity(
            "Network request failed",
            "Visual styling issue"
        )
        assert sim < 0.3, f"Different should be < 0.3, got {sim}"
        print(f"✓ Different text: {sim:.2f}")

    asyncio.run(run_tests())
    print("\n✅ Similarity computation tests passed")


if __name__ == "__main__":
    print("🧪 Testing BugClassifierAgent logic\n")
    print("=" * 50)

    try:
        test_category_mapping()
        test_priority_estimation()
        test_steps_generation()
        test_similarity_computation()

        print("=" * 50)
        print("\n🎉 All tests passed!")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        exit(1)
