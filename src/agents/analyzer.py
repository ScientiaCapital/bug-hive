"""Page Analyzer Agent for detecting bugs and issues."""

import json
import time
from datetime import datetime
from typing import Any

import structlog

from src.llm.router import LLMRouter
from src.models.evidence import Evidence
from src.models.raw_issue import PageAnalysisResult, RawIssue

from .prompts.analyzer import ANALYZE_PAGE_PROMPT
from .tools import get_analyzer_tools

logger = structlog.get_logger(__name__)


class PageAnalyzerAgent:
    """Agent for analyzing pages and detecting issues.

    This agent combines rule-based detection (fast, free) with LLM-enhanced
    analysis (intelligent, cost-effective) to identify bugs and issues.

    Detection Capabilities:
    - Console errors (JS exceptions, React errors, promise rejections)
    - Network failures (4xx/5xx responses, timeouts, CORS)
    - Visual issues (broken images, text overflow, z-index problems)
    - Performance problems (slow loads, large bundles, excessive requests)
    - Accessibility issues (missing alt text, low contrast, missing labels)
    - Content issues (lorem ipsum, TODO comments, debug logs)
    """

    def __init__(self, llm_router: LLMRouter):
        """Initialize the analyzer agent.

        Args:
            llm_router: LLMRouter instance for LLM calls
        """
        self.llm = llm_router

    async def analyze(
        self,
        page_data: dict[str, Any],
        session_id: str | None = None
    ) -> PageAnalysisResult:
        """Analyze page data and return detected issues.

        Args:
            page_data: Extracted page data from PageExtractor
            session_id: Optional session ID for cost tracking

        Returns:
            PageAnalysisResult with all detected issues
        """
        start_time = time.time()
        url = page_data.get("url", "unknown")

        logger.info(
            "starting_page_analysis",
            url=url,
            console_logs=len(page_data.get("console_logs", [])),
            network_requests=len(page_data.get("network_requests", [])),
        )

        issues: list[RawIssue] = []

        # Rule-based detection (fast, no LLM cost)
        try:
            issues.extend(await self._detect_console_errors(page_data))
            issues.extend(await self._detect_network_failures(page_data))
            issues.extend(await self._detect_performance_issues(page_data))
            issues.extend(await self._detect_content_issues(page_data))
            issues.extend(await self._detect_form_issues(page_data))
        except Exception as e:
            logger.error("rule_based_detection_failed", error=str(e))

        # LLM-enhanced detection (uses DeepSeek-V3 for deeper analysis)
        try:
            llm_issues = await self._analyze_with_llm(page_data, session_id)
            issues.extend(llm_issues)
        except Exception as e:
            logger.error("llm_analysis_failed", error=str(e))

        # Calculate confidence scores by type
        confidence_scores = self._calculate_confidence_scores(issues)

        analysis_time = time.time() - start_time

        result = PageAnalysisResult(
            url=url,
            issues_found=issues,
            analysis_time=analysis_time,
            confidence_scores=confidence_scores,
            page_title=page_data.get("title"),
            metadata={
                "rule_based_issues": sum(1 for i in issues if i.metadata and i.metadata.get("detection") == "rule_based"),
                "llm_issues": sum(1 for i in issues if i.metadata and i.metadata.get("detection") == "llm"),
            }
        )

        logger.info(
            "page_analysis_complete",
            url=url,
            total_issues=result.total_issues,
            analysis_time=analysis_time,
            issues_by_severity=result.issues_by_severity,
        )

        return result

    async def _detect_console_errors(self, page_data: dict[str, Any]) -> list[RawIssue]:
        """Detect JavaScript console errors.

        Looks for:
        - Uncaught exceptions
        - React/framework errors
        - Unhandled promise rejections
        - Type errors
        """
        issues = []
        console_logs = page_data.get("console_logs", [])

        for log in console_logs:
            level = log.get("level", "")
            text = log.get("text", "")

            # Only process errors and warnings
            if level not in ("error", "warning"):
                continue

            # Determine severity based on error type
            severity = "medium"
            confidence = 0.85

            # Check for critical errors
            if any(keyword in text.lower() for keyword in [
                "uncaught",
                "unhandled rejection",
                "fatal",
                "critical",
            ]):
                severity = "high"
                confidence = 0.95

            # React errors are often critical
            if any(keyword in text for keyword in [
                "React",
                "ReactDOM",
                "useEffect",
                "useState",
            ]):
                severity = "high"
                confidence = 0.92

            # Warnings are typically lower severity
            if level == "warning":
                severity = "low"
                confidence = 0.75

            # Truncate very long error messages
            title = text[:100] + "..." if len(text) > 100 else text

            issues.append(RawIssue(
                type="console_error",
                title=f"Console {level}: {title}",
                description=text,
                evidence=[Evidence(
                    type="console_log",
                    content=json.dumps(log),
                    timestamp=datetime.fromisoformat(log["timestamp"])
                    if isinstance(log.get("timestamp"), str)
                    else datetime.utcnow(),
                    metadata={
                        "level": level,
                        "location": log.get("location"),
                    }
                )],
                confidence=confidence,
                severity=severity,
                url=page_data.get("url"),
                metadata={
                    "detection": "rule_based",
                    "log_level": level,
                }
            ))

        logger.debug(
            "console_errors_detected",
            count=len(issues),
            errors=[i.title for i in issues]
        )

        return issues

    async def _detect_network_failures(self, page_data: dict[str, Any]) -> list[RawIssue]:
        """Detect failed network requests.

        Looks for:
        - 4xx client errors
        - 5xx server errors
        - Network request failures
        - CORS issues
        """
        issues = []
        network_requests = page_data.get("network_requests", [])
        network_errors = page_data.get("network_errors", [])

        # Check HTTP error responses
        for request in network_requests:
            status = request.get("status", 0)

            if status < 400:
                continue

            # Determine severity based on status code
            if status >= 500:
                severity = "high"
                confidence = 0.95
            elif status >= 400:
                severity = "medium"
                confidence = 0.90
            else:
                continue

            # 404 on assets might be lower severity
            resource_type = request.get("resource_type", "")
            if status == 404 and resource_type in ["image", "stylesheet", "script"]:
                severity = "medium"

            url = request.get("url", "")
            method = request.get("method", "GET")

            # Truncate long URLs
            url_display = url[:80] + "..." if len(url) > 80 else url

            issues.append(RawIssue(
                type="network_failure",
                title=f"HTTP {status} on {method} {url_display}",
                description=f"Request to {url} returned {status} {self._get_status_text(status)}",
                evidence=[Evidence(
                    type="network_request",
                    content=json.dumps(request),
                    timestamp=datetime.fromisoformat(request["timestamp"])
                    if isinstance(request.get("timestamp"), str)
                    else datetime.utcnow(),
                    metadata={
                        "status_code": status,
                        "request_method": method,
                        "request_url": url,
                    }
                )],
                confidence=confidence,
                severity=severity,
                url=page_data.get("url"),
                metadata={
                    "detection": "rule_based",
                    "status_code": status,
                    "resource_type": resource_type,
                }
            ))

        # Check network errors (failed requests)
        for error in network_errors:
            url = error.get("url", "")
            failure = error.get("failure", "")
            method = error.get("method", "GET")

            url_display = url[:80] + "..." if len(url) > 80 else url

            # Network failures are typically high severity
            severity = "high"
            confidence = 0.92

            # CORS errors
            if "cors" in failure.lower():
                confidence = 0.98

            issues.append(RawIssue(
                type="network_failure",
                title=f"Network request failed: {method} {url_display}",
                description=f"Request to {url} failed: {failure}",
                evidence=[Evidence(
                    type="network_request",
                    content=json.dumps(error),
                    timestamp=datetime.fromisoformat(error["timestamp"])
                    if isinstance(error.get("timestamp"), str)
                    else datetime.utcnow(),
                    metadata={
                        "failure": failure,
                        "request_method": method,
                        "request_url": url,
                    }
                )],
                confidence=confidence,
                severity=severity,
                url=page_data.get("url"),
                metadata={
                    "detection": "rule_based",
                    "failure_type": failure,
                }
            ))

        logger.debug(
            "network_failures_detected",
            count=len(issues),
            failures=[i.title for i in issues]
        )

        return issues

    async def _detect_performance_issues(self, page_data: dict[str, Any]) -> list[RawIssue]:
        """Detect performance problems.

        Looks for:
        - Slow page loads (> 3s)
        - Slow API calls (> 5s)
        - Large response sizes
        """
        issues = []
        metrics = page_data.get("performance_metrics", {})
        network_requests = page_data.get("network_requests", [])

        # Check page load time
        load_time = metrics.get("loadTime", 0)
        if load_time > 3000:  # 3 seconds threshold
            severity = "high" if load_time > 5000 else "medium"
            confidence = 0.85

            issues.append(RawIssue(
                type="performance",
                title=f"Slow page load: {load_time:.0f}ms",
                description=f"Page took {load_time:.0f}ms to load (threshold: 3000ms). This impacts user experience and SEO.",
                evidence=[Evidence(
                    type="performance_metrics",
                    content=json.dumps(metrics),
                    timestamp=datetime.utcnow(),
                    metadata={"load_time_ms": load_time}
                )],
                confidence=confidence,
                severity=severity,
                url=page_data.get("url"),
                metadata={
                    "detection": "rule_based",
                    "load_time_ms": load_time,
                }
            ))

        # Check for slow API calls
        for request in network_requests:
            timing = request.get("timing")
            if not timing:
                continue

            total_time = timing.get("total", 0)
            if total_time > 5000:  # 5 seconds threshold
                url = request.get("url", "")
                url_display = url[:80] + "..." if len(url) > 80 else url

                severity = "high" if total_time > 10000 else "medium"
                confidence = 0.80

                issues.append(RawIssue(
                    type="performance",
                    title=f"Slow API call: {url_display} ({total_time:.0f}ms)",
                    description=f"Request to {url} took {total_time:.0f}ms (threshold: 5000ms). This causes delays and poor UX.",
                    evidence=[Evidence(
                        type="network_request",
                        content=json.dumps(request),
                        timestamp=datetime.fromisoformat(request["timestamp"])
                        if isinstance(request.get("timestamp"), str)
                        else datetime.utcnow(),
                        metadata={
                            "duration_ms": total_time,
                            "request_url": url,
                        }
                    )],
                    confidence=confidence,
                    severity=severity,
                    url=page_data.get("url"),
                    metadata={
                        "detection": "rule_based",
                        "duration_ms": total_time,
                    }
                ))

        logger.debug(
            "performance_issues_detected",
            count=len(issues),
            issues=[i.title for i in issues]
        )

        return issues

    async def _detect_content_issues(self, page_data: dict[str, Any]) -> list[RawIssue]:
        """Detect content issues like lorem ipsum, TODO comments.

        Looks for:
        - Lorem ipsum placeholder text
        - TODO/FIXME comments
        - Debug console logs
        """
        issues = []
        console_logs = page_data.get("console_logs", [])

        # Check for debug console logs in production
        for log in console_logs:
            level = log.get("level", "")
            text = log.get("text", "")

            # Look for debug patterns
            if level == "log" and any(keyword in text.lower() for keyword in [
                "debug:",
                "test:",
                "fixme:",
                "todo:",
                "console.log",
            ]):
                issues.append(RawIssue(
                    type="content",
                    title="Debug console log in production",
                    description=f"Found debug log statement: {text[:200]}",
                    evidence=[Evidence(
                        type="console_log",
                        content=json.dumps(log),
                        timestamp=datetime.fromisoformat(log["timestamp"])
                        if isinstance(log.get("timestamp"), str)
                        else datetime.utcnow(),
                    )],
                    confidence=0.70,
                    severity="low",
                    url=page_data.get("url"),
                    metadata={
                        "detection": "rule_based",
                        "pattern": "debug_log",
                    }
                ))

        logger.debug(
            "content_issues_detected",
            count=len(issues),
            issues=[i.title for i in issues]
        )

        return issues

    async def _detect_form_issues(self, page_data: dict[str, Any]) -> list[RawIssue]:
        """Detect form-related issues.

        Looks for:
        - Forms without action
        - Required fields without validation
        - Inputs without labels
        """
        issues = []
        forms = page_data.get("forms", [])

        for idx, form in enumerate(forms):
            form_id = form.get("id") or form.get("name") or f"form_{idx}"

            # Check for forms without action
            if not form.get("action"):
                issues.append(RawIssue(
                    type="form",
                    title=f"Form missing action attribute: {form_id}",
                    description=f"Form '{form_id}' has no action attribute, which may cause submission issues.",
                    evidence=[Evidence(
                        type="dom_snapshot",
                        content=json.dumps(form),
                        timestamp=datetime.utcnow(),
                        metadata={"form_id": form_id}
                    )],
                    confidence=0.65,
                    severity="low",
                    url=page_data.get("url"),
                    metadata={
                        "detection": "rule_based",
                        "form_id": form_id,
                    }
                ))

            # Check for required fields without proper setup
            inputs = form.get("inputs", [])
            required_inputs = [i for i in inputs if i.get("required")]

            if required_inputs:
                for inp in required_inputs:
                    # Check if required field has name
                    if not inp.get("name"):
                        issues.append(RawIssue(
                            type="form",
                            title=f"Required field without name in {form_id}",
                            description=f"Required {inp.get('type', 'input')} field lacks name attribute.",
                            evidence=[Evidence(
                                type="dom_snapshot",
                                content=json.dumps(inp),
                                timestamp=datetime.utcnow(),
                            )],
                            confidence=0.75,
                            severity="medium",
                            url=page_data.get("url"),
                            metadata={
                                "detection": "rule_based",
                                "form_id": form_id,
                            }
                        ))

        logger.debug(
            "form_issues_detected",
            count=len(issues),
            issues=[i.title for i in issues]
        )

        return issues

    async def _analyze_with_llm(
        self,
        page_data: dict[str, Any],
        session_id: str | None = None
    ) -> list[RawIssue]:
        """Use LLM for deeper analysis.

        This supplements rule-based detection with intelligent analysis
        for complex issues like visual problems, accessibility, etc.
        """
        try:
            # Format data for LLM
            console_logs_str = self._format_console_logs(page_data.get("console_logs", []))
            network_requests_str = self._format_network_requests(page_data.get("network_requests", []))
            forms_str = self._format_forms(page_data.get("forms", []))
            performance_str = self._format_performance(page_data.get("performance_metrics", {}))

            # Build prompt
            prompt = ANALYZE_PAGE_PROMPT.format(
                url=page_data.get("url", "unknown"),
                title=page_data.get("title", "Unknown"),
                console_logs=console_logs_str,
                network_requests=network_requests_str,
                forms=forms_str,
                performance_metrics=performance_str,
            )

            # Call LLM (uses DeepSeek-V3 via task routing)
            response = await self.llm.route(
                task="analyze_page",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2048,
                temperature=0.3,  # Lower temperature for more deterministic analysis
                session_id=session_id,
                tools=get_analyzer_tools(),  # Provide analyzer tools for LLM to use
            )

            content = response.get("content", "")

            # Parse JSON response
            try:
                issues_data = json.loads(content)
                if not isinstance(issues_data, list):
                    logger.warning("llm_returned_non_array", content=content[:200])
                    return []

                # Convert to RawIssue objects
                issues = []
                for issue_dict in issues_data:
                    try:
                        issues.append(RawIssue(
                            type=issue_dict.get("type", "content"),
                            title=issue_dict.get("title", "Unknown issue"),
                            description=issue_dict.get("description", ""),
                            evidence=[],  # LLM doesn't provide evidence
                            confidence=issue_dict.get("confidence", 0.5),
                            severity=issue_dict.get("severity", "medium"),
                            url=page_data.get("url"),
                            metadata={
                                "detection": "llm",
                                "model": response.get("model"),
                                **(issue_dict.get("metadata", {}))
                            }
                        ))
                    except Exception as e:
                        logger.warning("failed_to_parse_llm_issue", error=str(e), issue=issue_dict)
                        continue

                logger.info(
                    "llm_analysis_complete",
                    issues_found=len(issues),
                    model=response.get("model"),
                )

                return issues

            except json.JSONDecodeError as e:
                logger.error("failed_to_parse_llm_response", error=str(e), content=content[:500])
                return []

        except Exception as e:
            logger.error("llm_analysis_failed", error=str(e))
            return []

    def _format_console_logs(self, logs: list[dict]) -> str:
        """Format console logs for LLM prompt."""
        if not logs:
            return "No console logs captured."

        # Only include errors and warnings
        relevant_logs = [log for log in logs if log.get("level") in ("error", "warning")]

        if not relevant_logs:
            return "No errors or warnings in console logs."

        formatted = []
        for log in relevant_logs[:10]:  # Limit to 10 most recent
            formatted.append(f"[{log.get('level', 'unknown').upper()}] {log.get('text', '')[:200]}")

        return "\n".join(formatted)

    def _format_network_requests(self, requests: list[dict]) -> str:
        """Format network requests for LLM prompt."""
        if not requests:
            return "No network requests captured."

        # Only include failed requests
        failed = [req for req in requests if req.get("status", 0) >= 400]

        if not failed:
            return f"{len(requests)} network requests, all successful."

        formatted = [f"Total requests: {len(requests)}, Failed: {len(failed)}\n"]
        for req in failed[:10]:  # Limit to 10 failures
            url = req.get("url", "")[:100]
            formatted.append(f"- {req.get('method', 'GET')} {url} → {req.get('status', '?')}")

        return "\n".join(formatted)

    def _format_forms(self, forms: list[dict]) -> str:
        """Format forms for LLM prompt."""
        if not forms:
            return "No forms found on page."

        formatted = [f"Found {len(forms)} form(s):\n"]
        for idx, form in enumerate(forms[:5]):  # Limit to 5 forms
            form_id = form.get("id") or form.get("name") or f"form_{idx}"
            input_count = form.get("inputCount", 0)
            formatted.append(f"- {form_id}: {input_count} inputs, method={form.get('method', 'get')}")

        return "\n".join(formatted)

    def _format_performance(self, metrics: dict) -> str:
        """Format performance metrics for LLM prompt."""
        if not metrics:
            return "No performance metrics available."

        load_time = metrics.get("loadTime", 0)
        dom_ready = metrics.get("domReady", 0)

        return f"""
Load time: {load_time:.0f}ms
DOM ready: {dom_ready:.0f}ms
First paint: {metrics.get('firstPaint', 0):.0f}ms
"""

    def _calculate_confidence_scores(self, issues: list[RawIssue]) -> dict[str, float]:
        """Calculate average confidence scores by issue type."""
        scores: dict[str, list[float]] = {}

        for issue in issues:
            if issue.type not in scores:
                scores[issue.type] = []
            scores[issue.type].append(issue.confidence)

        # Calculate averages
        return {
            issue_type: sum(confidences) / len(confidences)
            for issue_type, confidences in scores.items()
            if confidences
        }

    @staticmethod
    def _get_status_text(status_code: int) -> str:
        """Get human-readable status text for HTTP status code."""
        status_texts = {
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            408: "Request Timeout",
            429: "Too Many Requests",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout",
        }
        return status_texts.get(status_code, "Unknown Error")
