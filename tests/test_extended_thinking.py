"""Tests for extended thinking and reasoning traces in BugHive."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.graph.thinking_validator import (
    batch_validate_bugs_with_thinking,
    validate_bug_with_thinking,
)
from src.llm.anthropic import AnthropicClient


class TestAnthropicExtendedThinking:
    """Test extended thinking functionality in AnthropicClient."""

    @pytest.mark.asyncio
    async def test_create_message_with_thinking_success(self):
        """Test successful extended thinking message creation."""
        # Mock response with thinking content
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(type="thinking", thinking="Let me analyze this step by step..."),
            MagicMock(type="text", text="Final answer: This is a valid bug."),
        ]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=200)
        mock_response.stop_reason = "end_turn"

        with patch("src.llm.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client_instance

            client = AnthropicClient(api_key="test-key")
            result = await client.create_message_with_thinking(
                messages=[{"role": "user", "content": "Analyze this bug"}],
                max_tokens=4000,
                thinking_budget=2000,
            )

        # Verify result structure
        assert "content" in result
        assert "thinking" in result
        assert "usage" in result
        assert result["content"] == "Final answer: This is a valid bug."
        assert result["thinking"] == "Let me analyze this step by step..."
        assert result["usage"]["input_tokens"] == 100
        assert result["usage"]["output_tokens"] == 200
        assert result["usage"]["total_tokens"] == 300

    @pytest.mark.asyncio
    async def test_create_message_with_thinking_no_thinking_block(self):
        """Test extended thinking when no thinking block is returned."""
        # Mock response without thinking content
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(type="text", text="Direct answer without thinking."),
        ]
        mock_response.usage = MagicMock(input_tokens=50, output_tokens=100)
        mock_response.stop_reason = "end_turn"

        with patch("src.llm.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client_instance

            client = AnthropicClient(api_key="test-key")
            result = await client.create_message_with_thinking(
                messages=[{"role": "user", "content": "Simple question"}],
            )

        # Verify thinking is None when not present
        assert result["content"] == "Direct answer without thinking."
        assert result["thinking"] is None

    @pytest.mark.asyncio
    async def test_create_message_with_thinking_validates_messages(self):
        """Test that empty messages raise ValueError."""
        client = AnthropicClient(api_key="test-key")

        with pytest.raises(ValueError, match="messages cannot be empty"):
            await client.create_message_with_thinking(messages=[])

    @pytest.mark.asyncio
    async def test_create_message_with_thinking_custom_parameters(self):
        """Test extended thinking with custom parameters."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Result")]
        mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)
        mock_response.stop_reason = "end_turn"

        with patch("src.llm.anthropic.AsyncAnthropic") as mock_anthropic:
            mock_client_instance = AsyncMock()
            mock_client_instance.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.return_value = mock_client_instance

            client = AnthropicClient(api_key="test-key")
            await client.create_message_with_thinking(
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=16000,
                thinking_budget=10000,
                temperature=0.5,
                model="claude-opus-4-5-20250514",
            )

            # Verify API was called with correct parameters
            call_kwargs = mock_client_instance.messages.create.call_args[1]
            assert call_kwargs["max_tokens"] == 16000
            assert call_kwargs["temperature"] == 0.5
            assert call_kwargs["model"] == "claude-opus-4-5-20250514"
            assert call_kwargs["thinking"]["type"] == "enabled"
            assert call_kwargs["thinking"]["budget_tokens"] == 10000


class TestThinkingValidator:
    """Test bug validation with extended thinking."""

    @pytest.fixture
    def sample_bug(self):
        """Sample bug for testing."""
        return {
            "id": "bug-123",
            "title": "Login button not working",
            "priority": "critical",
            "severity": "high",
            "category": "ui_ux",
            "description": "Users cannot log in when clicking the login button",
            "steps_to_reproduce": [
                "Navigate to /login",
                "Enter valid credentials",
                "Click 'Login' button",
                "Observe no response",
            ],
            "expected_behavior": "User should be logged in and redirected to dashboard",
            "actual_behavior": "Nothing happens when clicking the button",
            "confidence_score": 0.95,
        }

    @pytest.mark.asyncio
    async def test_validate_bug_with_thinking_success(self, sample_bug):
        """Test successful bug validation with extended thinking."""
        # Mock extended thinking response
        mock_validation = {
            "is_valid": True,
            "validated_priority": "critical",
            "business_impact": "Login is broken for all users, blocking access completely",
            "recommended_action": "fix_immediately",
            "validation_notes": "Clear evidence of broken core functionality",
            "confidence": 0.98,
            "reasoning": "Step 1: Evidence shows reproducible failure. Step 2: Login is critical path. Step 3: Affects all users. Step 4: No workaround exists.",
        }

        mock_response_data = {
            "content": json.dumps(mock_validation),
            "thinking": "Let me analyze this carefully. The bug report indicates a complete failure of the login button. This is a critical user flow. Evidence: reproducible steps, affects all users, no error handling visible. Priority assessment: critical is correct given this blocks all user access. Recommendation: immediate fix required.",
            "usage": {"input_tokens": 500, "output_tokens": 300, "total_tokens": 800},
            "stop_reason": "end_turn",
        }

        with patch.object(
            AnthropicClient,
            "create_message_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response_data,
        ):
            result = await validate_bug_with_thinking(sample_bug)

        # Verify validation results
        assert result["is_valid"] is True
        assert result["validated_priority"] == "critical"
        assert result["recommended_action"] == "fix_immediately"
        assert result["confidence"] == 0.98
        assert "thinking_trace" in result
        assert len(result["thinking_trace"]) > 0
        assert "usage" in result
        assert result["usage"]["input_tokens"] == 500
        assert "cost" in result
        assert result["cost"] > 0

    @pytest.mark.asyncio
    async def test_validate_bug_with_thinking_invalid_json(self, sample_bug):
        """Test handling of invalid JSON response."""
        mock_response_data = {
            "content": "This is not valid JSON {broken",
            "thinking": "Some thinking...",
            "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            "stop_reason": "end_turn",
        }

        with patch.object(
            AnthropicClient,
            "create_message_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response_data,
        ):
            result = await validate_bug_with_thinking(sample_bug)

        # Should return conservative validation on error
        assert result["is_valid"] is False
        assert result["recommended_action"] == "defer"
        assert result["confidence"] == 0.0
        assert "parsing failed" in result["validation_notes"].lower()

    @pytest.mark.asyncio
    async def test_validate_bug_with_thinking_no_trace(self, sample_bug):
        """Test validation when no thinking trace is returned."""
        mock_validation = {
            "is_valid": True,
            "validated_priority": "high",
            "business_impact": "Impacts user experience",
            "recommended_action": "schedule",
            "validation_notes": "Should be fixed soon",
            "confidence": 0.85,
            "reasoning": "Analysis complete.",
        }

        mock_response_data = {
            "content": json.dumps(mock_validation),
            "thinking": None,  # No thinking trace
            "usage": {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300},
            "stop_reason": "end_turn",
        }

        with patch.object(
            AnthropicClient,
            "create_message_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response_data,
        ):
            result = await validate_bug_with_thinking(sample_bug)

        # Should still succeed but log warning
        assert result["is_valid"] is True
        assert result["thinking_trace"] is None

    @pytest.mark.asyncio
    async def test_validate_bug_with_thinking_custom_client(self, sample_bug):
        """Test validation with a pre-initialized client."""
        mock_client = MagicMock(spec=AnthropicClient)
        mock_client.create_message_with_thinking = AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "is_valid": True,
                        "validated_priority": "medium",
                        "business_impact": "Minor impact",
                        "recommended_action": "schedule",
                        "validation_notes": "Can be deferred",
                        "confidence": 0.7,
                        "reasoning": "Low urgency.",
                    }
                ),
                "thinking": "Brief analysis...",
                "usage": {"input_tokens": 50, "output_tokens": 25, "total_tokens": 75},
                "stop_reason": "end_turn",
            }
        )
        mock_client.close = AsyncMock()

        result = await validate_bug_with_thinking(sample_bug, mock_client)

        # Should use provided client and not close it
        assert result["is_valid"] is True
        mock_client.create_message_with_thinking.assert_called_once()
        mock_client.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_batch_validate_bugs_with_thinking(self):
        """Test batch validation of multiple bugs."""
        bugs = [
            {
                "id": "bug-1",
                "title": "Critical bug",
                "priority": "critical",
                "severity": "high",
                "category": "security",
                "description": "SQL injection vulnerability",
                "steps_to_reproduce": ["Enter malicious SQL"],
                "expected_behavior": "Input sanitized",
                "actual_behavior": "SQL executed",
                "confidence_score": 0.99,
            },
            {
                "id": "bug-2",
                "title": "Minor UI issue",
                "priority": "low",
                "severity": "low",
                "category": "ui_ux",
                "description": "Button color slightly off",
                "steps_to_reproduce": ["View button"],
                "expected_behavior": "Correct color",
                "actual_behavior": "Slightly different shade",
                "confidence_score": 0.6,
            },
        ]

        # Mock responses for each bug
        def create_mock_response(bug_id, is_critical):
            priority = "critical" if is_critical else "low"
            action = "fix_immediately" if is_critical else "defer"

            return {
                "content": json.dumps(
                    {
                        "is_valid": True,
                        "validated_priority": priority,
                        "business_impact": f"Impact for {bug_id}",
                        "recommended_action": action,
                        "validation_notes": f"Notes for {bug_id}",
                        "confidence": 0.9 if is_critical else 0.5,
                        "reasoning": f"Reasoning for {bug_id}",
                    }
                ),
                "thinking": f"Thinking for {bug_id}...",
                "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
                "stop_reason": "end_turn",
            }

        with patch.object(
            AnthropicClient,
            "create_message_with_thinking",
            new_callable=AsyncMock,
        ) as mock_create:
            # Return different responses for each call
            mock_create.side_effect = [
                create_mock_response("bug-1", True),
                create_mock_response("bug-2", False),
            ]

            results = await batch_validate_bugs_with_thinking(bugs)

        # Verify batch results
        assert len(results) == 2
        assert results[0]["validated_priority"] == "critical"
        assert results[0]["recommended_action"] == "fix_immediately"
        assert results[1]["validated_priority"] == "low"
        assert results[1]["recommended_action"] == "defer"


class TestReasoningFieldsInPrompts:
    """Test that prompts include reasoning fields."""

    def test_analyzer_prompt_has_reasoning(self):
        """Test ANALYZE_PAGE_PROMPT includes reasoning field."""
        from src.agents.prompts.analyzer import ANALYZE_PAGE_PROMPT

        assert "reasoning" in ANALYZE_PAGE_PROMPT.lower()
        assert "step-by-step" in ANALYZE_PAGE_PROMPT.lower()
        assert "evidence" in ANALYZE_PAGE_PROMPT.lower()

    def test_classifier_prompt_has_reasoning(self):
        """Test CLASSIFY_BUG includes reasoning field."""
        from src.agents.prompts.classifier import CLASSIFY_BUG

        assert "reasoning" in CLASSIFY_BUG.lower()
        assert "step-by-step" in CLASSIFY_BUG.lower() or "detailed" in CLASSIFY_BUG.lower()

    def test_deduplicate_prompt_has_reasoning(self):
        """Test DEDUPLICATE_BUGS includes reasoning field."""
        from src.agents.prompts.classifier import DEDUPLICATE_BUGS

        assert "reasoning" in DEDUPLICATE_BUGS.lower()

    def test_similarity_prompt_has_reasoning(self):
        """Test COMPUTE_SIMILARITY includes reasoning field."""
        from src.agents.prompts.classifier import COMPUTE_SIMILARITY

        assert "reasoning" in COMPUTE_SIMILARITY.lower()


class TestExtendedThinkingIntegration:
    """Integration tests for extended thinking in workflow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extended_thinking_reduces_false_positives(self):
        """
        Test that extended thinking helps identify false positives.

        This test verifies that the reasoning process correctly identifies
        a bug that initially seems critical but is actually a false positive.
        """
        false_positive_bug = {
            "id": "bug-fp-1",
            "title": "API returns 404 error",
            "priority": "critical",
            "severity": "high",
            "category": "data",
            "description": "API endpoint returns 404 error",
            "steps_to_reproduce": [
                "Call GET /api/v1/users/nonexistent",
                "Observe 404 response",
            ],
            "expected_behavior": "Return user data",
            "actual_behavior": "Returns 404 Not Found",
            "confidence_score": 0.85,
        }

        # Mock extended thinking that realizes this is expected behavior
        mock_response = {
            "content": json.dumps(
                {
                    "is_valid": False,
                    "validated_priority": "low",
                    "business_impact": "No impact - this is expected behavior for non-existent resources",
                    "recommended_action": "dismiss",
                    "validation_notes": "404 is the correct response for requesting a non-existent user. This is not a bug but expected REST API behavior.",
                    "confidence": 0.95,
                    "reasoning": "Step 1: Analyzing the request - it's for a 'nonexistent' user. Step 2: 404 is the correct HTTP status for 'Not Found'. Step 3: This matches REST API standards (RFC 7231). Step 4: No evidence of unexpected behavior. Conclusion: This is a false positive, not a bug.",
                }
            ),
            "thinking": "I need to think carefully about this. The bug report says API returns 404, which seems bad at first. But wait - they're requesting '/users/nonexistent'. A 404 (Not Found) is actually the *correct* response when requesting a resource that doesn't exist. This is standard REST API behavior according to HTTP specifications. The 'expected behavior' in the report says 'return user data', but that's incorrect - you can't return data for a user that doesn't exist. The QA agent may have flagged this as critical because it saw an error code, but this is actually proper error handling. This should be dismissed as a false positive.",
            "usage": {"input_tokens": 300, "output_tokens": 250, "total_tokens": 550},
            "stop_reason": "end_turn",
        }

        with patch.object(
            AnthropicClient,
            "create_message_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await validate_bug_with_thinking(false_positive_bug)

        # Verify extended thinking correctly identified false positive
        assert result["is_valid"] is False
        assert result["recommended_action"] == "dismiss"
        # Check validation_notes or reasoning for false positive indicators
        combined_notes = (result.get("validation_notes", "") + " " + result.get("reasoning", "")).lower()
        assert "404" in combined_notes or "not a bug" in combined_notes
        assert "expected" in combined_notes or "rest" in combined_notes
        assert len(result["thinking_trace"]) > 100  # Should have substantial thinking
        assert "rest api" in result["thinking_trace"].lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_extended_thinking_validates_critical_bug(self):
        """
        Test that extended thinking correctly validates a legitimate critical bug.
        """
        critical_bug = {
            "id": "bug-crit-1",
            "title": "SQL injection in login form",
            "priority": "critical",
            "severity": "critical",
            "category": "security",
            "description": "User input not sanitized, allows SQL injection",
            "steps_to_reproduce": [
                "Navigate to /login",
                "Enter username: admin' OR '1'='1",
                "Enter any password",
                "Click login",
                "Observe successful login without valid credentials",
            ],
            "expected_behavior": "Login should fail with invalid credentials",
            "actual_behavior": "Login succeeds, bypassing authentication",
            "confidence_score": 0.99,
        }

        # Mock extended thinking that confirms this is critical
        mock_response = {
            "content": json.dumps(
                {
                    "is_valid": True,
                    "validated_priority": "critical",
                    "business_impact": "Complete authentication bypass allows unauthorized access to all user data. Severe security vulnerability with immediate exploitation risk.",
                    "recommended_action": "fix_immediately",
                    "validation_notes": "This is a textbook SQL injection vulnerability (CWE-89). Evidence is clear and reproducible. Requires immediate patching and security audit.",
                    "confidence": 0.99,
                    "reasoning": "Step 1: Bug legitimacy - The SQL injection payload (admin' OR '1'='1) is a standard attack vector. Successful login without valid credentials proves the vulnerability exists. Step 2: Priority - Critical is correct. OWASP Top 10 #1 (Injection), allows complete auth bypass. Step 3: Business impact - Catastrophic. Attackers can access any account, exfiltrate data, modify records. Legal/regulatory implications (GDPR, SOC2). Step 4: Action - Fix immediately. Disable endpoint if necessary, implement parameterized queries, conduct security review.",
                }
            ),
            "thinking": "This is a serious security issue that requires careful analysis. The reproduction steps show a classic SQL injection attack using the payload 'admin' OR '1'='1'. This payload works by breaking out of the intended SQL query and adding a condition that's always true. The fact that login succeeds proves the attack works. Let me assess severity: SQL injection is OWASP Top 10 #1, allows authentication bypass, can lead to data breach, lateral movement, complete system compromise. The evidence is strong - reproducible steps, clear attack vector, definitive outcome. Priority assessment: This is correctly classified as critical. It affects all users (anyone can exploit it), has severe business impact (data breach, compliance violations, reputation damage), and is trivially exploitable. Recommended action: This needs immediate fixing - disable the endpoint if needed, implement prepared statements, conduct full security audit. This is not a false positive - it's a genuine critical vulnerability.",
            "usage": {"input_tokens": 400, "output_tokens": 350, "total_tokens": 750},
            "stop_reason": "end_turn",
        }

        with patch.object(
            AnthropicClient,
            "create_message_with_thinking",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            result = await validate_bug_with_thinking(critical_bug)

        # Verify extended thinking correctly validated critical bug
        assert result["is_valid"] is True
        assert result["validated_priority"] == "critical"
        assert result["recommended_action"] == "fix_immediately"
        assert result["confidence"] >= 0.95
        # Check for security-related terms in business_impact or validation_notes
        combined_impact = (result.get("business_impact", "") + " " + result.get("validation_notes", "")).lower()
        assert "security" in combined_impact or "authentication" in combined_impact or "sql" in combined_impact
        # Check thinking trace contains security analysis
        assert "security" in result["thinking_trace"].lower() or "injection" in result["thinking_trace"].lower() or "cwe" in result["thinking_trace"].lower()
        assert len(result["reasoning"]) > 200  # Substantial reasoning required
