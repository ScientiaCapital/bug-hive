"""Tests for Page Analyzer Agent."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.agents.analyzer import PageAnalyzerAgent
from src.llm.router import LLMRouter
from src.models.raw_issue import PageAnalysisResult, RawIssue


@pytest.fixture
def mock_llm_router():
    """Create a mock LLM router."""
    router = Mock(spec=LLMRouter)
    router.route = AsyncMock()
    return router


@pytest.fixture
def analyzer(mock_llm_router):
    """Create analyzer agent with mocked LLM."""
    return PageAnalyzerAgent(llm_router=mock_llm_router)


@pytest.fixture
def sample_page_data():
    """Sample page data with various issues."""
    return {
        "url": "https://example.com/products",
        "title": "Products - Example Site",
        "console_logs": [
            {
                "level": "error",
                "text": "Uncaught TypeError: Cannot read property 'map' of undefined",
                "timestamp": datetime.utcnow().isoformat(),
                "location": {"url": "app.js", "lineNumber": 42}
            },
            {
                "level": "warning",
                "text": "React: Warning - useEffect has missing dependency",
                "timestamp": datetime.utcnow().isoformat(),
                "location": {"url": "components.js", "lineNumber": 123}
            },
            {
                "level": "log",
                "text": "User logged in successfully",
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
            },
            {
                "url": "https://api.example.com/users",
                "status": 500,
                "method": "POST",
                "resource_type": "fetch",
                "timestamp": datetime.utcnow().isoformat(),
                "timing": {"total": 1234},
            },
            {
                "url": "https://cdn.example.com/image.png",
                "status": 404,
                "method": "GET",
                "resource_type": "image",
                "timestamp": datetime.utcnow().isoformat(),
                "timing": {"total": 123},
            },
            {
                "url": "https://api.example.com/slow-endpoint",
                "status": 200,
                "method": "GET",
                "resource_type": "fetch",
                "timestamp": datetime.utcnow().isoformat(),
                "timing": {"total": 6500},  # > 5s threshold
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
                    {"name": "confirm", "type": "password", "required": True},
                ]
            },
            {
                "id": "search-form",
                "name": "",
                "action": "",  # Missing action
                "method": "get",
                "inputCount": 1,
                "inputs": [
                    {"name": "", "type": "text", "required": False},  # Missing name
                ]
            }
        ],
        "performance_metrics": {
            "loadTime": 4523,  # > 3s threshold
            "domReady": 3200,
            "firstPaint": 1200,
            "largestPaint": 1800,
            "dns": 23,
            "tcp": 45,
            "request": 234,
            "response": 123,
            "domProcessing": 2100,
        },
        "links": [
            "https://example.com/about",
            "https://example.com/contact",
        ],
        "meta_tags": {
            "description": "Example product page",
        }
    }


@pytest.mark.asyncio
async def test_detect_console_errors(analyzer, sample_page_data):
    """Test console error detection."""
    issues = await analyzer._detect_console_errors(sample_page_data)

    # Should detect 2 issues (error and warning, not the log)
    assert len(issues) == 2

    # Check error detection
    error_issue = [i for i in issues if "TypeError" in i.title][0]
    assert error_issue.type == "console_error"
    assert error_issue.severity in ["high", "medium"]
    assert error_issue.confidence >= 0.85
    assert len(error_issue.evidence) == 1
    assert error_issue.evidence[0].type == "console_log"

    # Check warning detection
    warning_issue = [i for i in issues if "warning" in i.title.lower()][0]
    assert warning_issue.type == "console_error"
    assert warning_issue.severity == "low"


@pytest.mark.asyncio
async def test_detect_network_failures(analyzer, sample_page_data):
    """Test network failure detection."""
    issues = await analyzer._detect_network_failures(sample_page_data)

    # Should detect 3 issues (500 error, 404 error, CORS error)
    assert len(issues) == 3

    # Check 500 error
    server_error = [i for i in issues if i.metadata.get("status_code") == 500][0]
    assert server_error.type == "network_failure"
    assert server_error.severity == "high"
    assert server_error.confidence >= 0.90
    assert "500" in server_error.title

    # Check 404 error
    not_found = [i for i in issues if i.metadata.get("status_code") == 404][0]
    assert not_found.type == "network_failure"
    assert "404" in not_found.title

    # Check CORS error
    cors_error = [i for i in issues if "cors" in i.title.lower()][0]
    assert cors_error.type == "network_failure"
    assert cors_error.severity == "high"
    assert "CORS" in cors_error.title or "cors" in cors_error.title.lower()


@pytest.mark.asyncio
async def test_detect_performance_issues(analyzer, sample_page_data):
    """Test performance issue detection."""
    issues = await analyzer._detect_performance_issues(sample_page_data)

    # Should detect 2 issues (slow page load + slow API call)
    assert len(issues) == 2

    # Check slow page load
    slow_load = [i for i in issues if "page load" in i.title.lower()][0]
    assert slow_load.type == "performance"
    assert slow_load.metadata["load_time_ms"] == 4523
    assert slow_load.severity in ["medium", "high"]
    assert "4523ms" in slow_load.title

    # Check slow API call
    slow_api = [i for i in issues if "API call" in i.title or "slow-endpoint" in i.title][0]
    assert slow_api.type == "performance"
    assert slow_api.metadata["duration_ms"] == 6500


@pytest.mark.asyncio
async def test_detect_form_issues(analyzer, sample_page_data):
    """Test form issue detection."""
    issues = await analyzer._detect_form_issues(sample_page_data)

    # Should detect 1 issue (form without action)
    assert len(issues) == 1

    # Check missing action
    missing_action = issues[0]
    assert missing_action.type == "form"
    assert "action" in missing_action.title.lower()
    assert missing_action.severity == "low"


@pytest.mark.asyncio
async def test_analyze_full_page(analyzer, mock_llm_router, sample_page_data):
    """Test full page analysis."""
    # Mock LLM response
    mock_llm_router.route.return_value = {
        "content": json.dumps([
            {
                "type": "accessibility",
                "title": "Missing alt text on images",
                "description": "Several images lack alt attributes",
                "confidence": 0.75,
                "severity": "medium",
                "metadata": {"images_affected": 3}
            }
        ]),
        "model": "deepseek/deepseek-chat",
        "usage": {"input_tokens": 1000, "output_tokens": 200},
    }

    result = await analyzer.analyze(sample_page_data, session_id="test-session")

    # Check result structure
    assert isinstance(result, PageAnalysisResult)
    assert result.url == "https://example.com/products"
    assert result.page_title == "Products - Example Site"
    assert result.analysis_time > 0

    # Should have issues from both rule-based and LLM detection
    assert result.total_issues > 0

    # Check issues by severity
    severity_counts = result.issues_by_severity
    assert all(k in severity_counts for k in ["critical", "high", "medium", "low"])

    # Check LLM was called
    mock_llm_router.route.assert_called_once()
    call_args = mock_llm_router.route.call_args
    assert call_args.kwargs["task"] == "analyze_page"
    assert call_args.kwargs["session_id"] == "test-session"


@pytest.mark.asyncio
async def test_analyze_clean_page(analyzer, mock_llm_router):
    """Test analysis of a page with no issues."""
    clean_page_data = {
        "url": "https://example.com/clean",
        "title": "Clean Page",
        "console_logs": [],
        "network_requests": [
            {
                "url": "https://api.example.com/data",
                "status": 200,
                "method": "GET",
                "resource_type": "fetch",
                "timestamp": datetime.utcnow().isoformat(),
                "timing": {"total": 234},
            }
        ],
        "network_errors": [],
        "forms": [],
        "performance_metrics": {
            "loadTime": 1200,  # Fast load
            "domReady": 800,
        },
        "links": [],
        "meta_tags": {},
    }

    # Mock LLM returning no issues
    mock_llm_router.route.return_value = {
        "content": "[]",
        "model": "deepseek/deepseek-chat",
        "usage": {"input_tokens": 500, "output_tokens": 10},
    }

    result = await analyzer.analyze(clean_page_data)

    # Should have no issues
    assert result.total_issues == 0
    assert result.issues_found == []


@pytest.mark.asyncio
async def test_confidence_score_calculation(analyzer):
    """Test confidence score calculation."""
    issues = [
        RawIssue(
            type="console_error",
            title="Error 1",
            description="Test",
            confidence=0.9,
            severity="high"
        ),
        RawIssue(
            type="console_error",
            title="Error 2",
            description="Test",
            confidence=0.8,
            severity="medium"
        ),
        RawIssue(
            type="performance",
            title="Slow load",
            description="Test",
            confidence=0.7,
            severity="medium"
        ),
    ]

    scores = analyzer._calculate_confidence_scores(issues)

    # Should have average for each type
    assert "console_error" in scores
    assert "performance" in scores
    assert scores["console_error"] == 0.85  # (0.9 + 0.8) / 2
    assert scores["performance"] == 0.7


@pytest.mark.asyncio
async def test_llm_analysis_error_handling(analyzer, mock_llm_router, sample_page_data):
    """Test LLM analysis handles errors gracefully."""
    # Mock LLM throwing error
    mock_llm_router.route.side_effect = Exception("API error")

    result = await analyzer.analyze(sample_page_data)

    # Should still complete with rule-based issues only
    assert isinstance(result, PageAnalysisResult)
    assert result.total_issues > 0  # Rule-based issues still detected


@pytest.mark.asyncio
async def test_high_confidence_issues_property(analyzer):
    """Test high confidence issues property."""
    result = PageAnalysisResult(
        url="https://example.com",
        issues_found=[
            RawIssue(
                type="console_error",
                title="High confidence",
                description="Test",
                confidence=0.95,
                severity="high"
            ),
            RawIssue(
                type="performance",
                title="Low confidence",
                description="Test",
                confidence=0.6,
                severity="medium"
            ),
        ],
        analysis_time=1.23,
    )

    high_conf = result.high_confidence_issues
    assert len(high_conf) == 1
    assert high_conf[0].confidence >= 0.8


@pytest.mark.asyncio
async def test_critical_issues_property(analyzer):
    """Test critical issues property."""
    result = PageAnalysisResult(
        url="https://example.com",
        issues_found=[
            RawIssue(
                type="security",
                title="Security vulnerability",
                description="Test",
                confidence=0.95,
                severity="critical"
            ),
            RawIssue(
                type="performance",
                title="Slow load",
                description="Test",
                confidence=0.8,
                severity="medium"
            ),
        ],
        analysis_time=1.23,
    )

    critical = result.critical_issues
    assert len(critical) == 1
    assert critical[0].severity == "critical"
