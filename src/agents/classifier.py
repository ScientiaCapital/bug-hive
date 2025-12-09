"""Bug Classifier Agent - Classifies, prioritizes, and deduplicates bugs."""

import json
import logging
from uuid import UUID, uuid4

from src.llm.router import LLMRouter
from src.models.bug import Bug
from src.models.raw_issue import RawIssue

from .prompts.classifier import (
    CLASSIFY_BUG,
    COMPUTE_SIMILARITY,
    DEDUPLICATE_BUGS,
)

logger = logging.getLogger(__name__)


class BugClassifierAgent:
    """
    Agent for classifying, prioritizing, and deduplicating bugs.

    Uses rule-based classification for high-confidence issues and LLM fallback
    for uncertain cases. Implements efficient deduplication to avoid duplicate
    bug reports.
    """

    def __init__(self, llm_router: LLMRouter):
        """
        Initialize classifier agent.

        Args:
            llm_router: LLMRouter instance for LLM-based classification
        """
        self.llm = llm_router
        self._bug_cache: dict[str, Bug] = {}  # For deduplication across sessions

    async def process_issues(
        self,
        issues: list[RawIssue],
        session_id: UUID,
        page_id: UUID,
    ) -> list[Bug]:
        """
        Process raw issues into classified bugs.

        Args:
            issues: List of RawIssue objects from page analyzer
            session_id: Current crawl session ID
            page_id: Current page ID

        Returns:
            List of classified Bug objects after deduplication
        """
        if not issues:
            logger.info("No issues to process")
            return []

        logger.info(f"Processing {len(issues)} raw issues for classification")

        classified_bugs: list[Bug] = []

        for i, issue in enumerate(issues, 1):
            try:
                logger.debug(f"Classifying issue {i}/{len(issues)}: {issue.title}")

                # Classify the issue
                bug = await self._classify_issue(issue, session_id, page_id)

                # Check for duplicates
                if not await self._is_duplicate(bug, classified_bugs):
                    classified_bugs.append(bug)
                    logger.info(
                        f"Classified bug: {bug.category}/{bug.priority} - {bug.title}"
                    )
                else:
                    logger.info(f"Skipped duplicate bug: {bug.title}")

            except Exception as e:
                logger.error(f"Failed to classify issue '{issue.title}': {e}")
                continue

        logger.info(
            f"Classification complete: {len(classified_bugs)}/{len(issues)} "
            f"unique bugs identified"
        )

        return classified_bugs

    async def _classify_issue(
        self,
        issue: RawIssue,
        session_id: UUID,
        page_id: UUID,
    ) -> Bug:
        """
        Classify a single issue into a Bug with category and priority.

        Uses rule-based classification first for efficiency. Falls back to LLM
        for uncertain cases (confidence < 0.8).

        Args:
            issue: RawIssue to classify
            session_id: Session ID
            page_id: Page ID

        Returns:
            Classified Bug object
        """
        # Rule-based classification first (free and fast)
        category = self._get_category_from_type(issue.type)
        priority = self._estimate_priority(issue)
        confidence = issue.confidence

        # Use LLM for uncertain cases (task: "classify_bug" → DeepSeek-V3)
        if issue.confidence < 0.8:
            logger.debug(
                f"Low confidence ({issue.confidence:.2f}), using LLM classification"
            )
            try:
                classification = await self._llm_classify(issue, str(session_id))

                # Override with LLM results if confidence is higher
                if classification["confidence"] > confidence:
                    category = classification["category"]
                    priority = classification["priority"]
                    confidence = classification["confidence"]
                    logger.debug(
                        f"LLM classification improved confidence: "
                        f"{issue.confidence:.2f} → {confidence:.2f}"
                    )

            except Exception as e:
                logger.warning(f"LLM classification failed, using rule-based: {e}")

        # Generate steps to reproduce
        steps = self._generate_steps(issue)

        # Create Bug object
        bug = Bug(
            id=uuid4(),
            session_id=session_id,
            page_id=page_id,
            category=category,
            priority=priority,
            title=issue.title,
            description=issue.description,
            steps_to_reproduce=steps,
            evidence=issue.evidence,
            confidence=confidence,
            status="detected",
            expected_behavior=self._infer_expected_behavior(issue),
            actual_behavior=issue.description,
            affected_users=self._estimate_affected_users(issue),
        )

        return bug

    def _get_category_from_type(self, issue_type: str) -> str:
        """
        Map issue type to bug category using rules.

        Args:
            issue_type: Type from RawIssue

        Returns:
            Bug category string
        """
        mapping = {
            "console_error": "ui_ux",  # Usually JS errors affecting UI
            "network_failure": "data",  # API/data issues
            "performance": "performance",  # Performance category
            "visual": "ui_ux",  # Visual defects
            "content": "data",  # Missing/incorrect content
            "form": "edge_case",  # Form validation, input handling
            "accessibility": "ui_ux",  # A11y issues
            "security": "security",  # Security vulnerabilities
        }
        return mapping.get(issue_type, "ui_ux")

    def _estimate_priority(self, issue: RawIssue) -> str:
        """
        Estimate priority based on issue characteristics using rules.

        Args:
            issue: RawIssue to evaluate

        Returns:
            Priority level string
        """
        title_lower = issue.title.lower()
        desc_lower = issue.description.lower()

        # Critical: security, crashes, data loss
        if issue.type == "security":
            return "critical"

        if any(
            keyword in title_lower or keyword in desc_lower
            for keyword in [
                "crash",
                "fatal",
                "data loss",
                "security",
                "injection",
                "xss",
                "auth bypass",
            ]
        ):
            return "critical"

        # High: 5xx errors, broken core features
        if issue.type == "network_failure":
            if any(code in issue.title for code in ["500", "502", "503", "504"]):
                return "high"

        if any(
            keyword in title_lower or keyword in desc_lower
            for keyword in [
                "broken",
                "not working",
                "fails",
                "error",
                "cannot",
                "unable to",
            ]
        ):
            if issue.confidence > 0.7:
                return "high"

        # Medium: most issues with good confidence
        if issue.confidence >= 0.7:
            return "medium"

        # Low: cosmetic, low confidence
        if any(
            keyword in title_lower or keyword in desc_lower
            for keyword in [
                "cosmetic",
                "styling",
                "minor",
                "alignment",
                "spacing",
                "color",
            ]
        ):
            return "low"

        return "medium"  # Default

    async def _is_duplicate(self, bug: Bug, existing_bugs: list[Bug]) -> bool:
        """
        Check if bug is duplicate of existing bugs.

        Uses efficient heuristics first, then LLM for uncertain cases.

        Args:
            bug: Bug to check
            existing_bugs: List of existing bugs to compare against

        Returns:
            True if bug is a duplicate, False otherwise
        """
        if not existing_bugs:
            return False

        # Fast exact match by title (same error message)
        for existing in existing_bugs:
            if bug.title == existing.title:
                logger.debug(f"Exact title match duplicate: {bug.title}")
                return True

        # Check same category bugs for similarity
        same_category_bugs = [b for b in existing_bugs if b.category == bug.category]

        for existing in same_category_bugs:
            # High priority bugs: use LLM for careful deduplication
            if bug.priority in ["critical", "high"] or existing.priority in [
                "critical",
                "high"
            ]:
                try:
                    is_dup = await self._llm_deduplicate(bug, existing)
                    if is_dup:
                        logger.debug(
                            f"LLM identified duplicate: {bug.title} ≈ {existing.title}"
                        )
                        return True
                except Exception as e:
                    logger.warning(f"LLM deduplication failed: {e}")
                    # Fall through to similarity check

            # Compute text similarity for other cases
            similarity = await self._compute_similarity(
                bug.description, existing.description
            )

            if similarity > 0.85:
                logger.debug(
                    f"High similarity duplicate ({similarity:.2f}): "
                    f"{bug.title} ≈ {existing.title}"
                )
                return True

        return False

    async def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute text similarity using simple heuristics.

        For production, could use embeddings or LLM, but this is fast and free.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score 0-1
        """
        # Simple word overlap similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        jaccard = len(intersection) / len(union) if union else 0.0

        return jaccard

    async def _llm_classify(self, issue: RawIssue, session_id: str) -> dict:
        """
        Use LLM for classification (task: classify_bug → DeepSeek-V3).

        Args:
            issue: RawIssue to classify
            session_id: Session ID for cost tracking

        Returns:
            Dict with category, priority, confidence, reasoning
        """
        prompt = CLASSIFY_BUG.format(
            title=issue.title,
            type=issue.type,
            description=issue.description,
            evidence_count=len(issue.evidence),
            url=issue.url or "N/A",
        )

        response = await self.llm.route(
            task="classify_bug",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.3,  # Low temperature for consistent classification
            session_id=session_id,
        )

        # Parse JSON response
        content = response["content"]
        try:
            result = json.loads(content)
            logger.debug(f"LLM classification: {result.get('reasoning', '')}")
            return result
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM response: {content}")
            # Return fallback
            return {
                "category": self._get_category_from_type(issue.type),
                "priority": "medium",
                "confidence": 0.5,
                "reasoning": "JSON parse failed",
            }

    async def _llm_deduplicate(self, bug1: Bug, bug2: Bug) -> bool:
        """
        Use LLM for deduplication (task: deduplicate_bugs → DeepSeek-V3).

        Args:
            bug1: First bug
            bug2: Second bug

        Returns:
            True if bugs are duplicates
        """
        prompt = DEDUPLICATE_BUGS.format(
            title1=bug1.title,
            description1=bug1.description,
            category1=bug1.category,
            url1=bug1.evidence[0].content if bug1.evidence else "N/A",
            title2=bug2.title,
            description2=bug2.description,
            category2=bug2.category,
            url2=bug2.evidence[0].content if bug2.evidence else "N/A",
        )

        response = await self.llm.route(
            task="deduplicate_bugs",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.3,
            session_id=None,  # Don't track deduplication costs separately
        )

        # Parse JSON response
        content = response["content"]
        try:
            result = json.loads(content)
            logger.debug(
                f"LLM deduplication ({result.get('similarity', 0):.2f}): "
                f"{result.get('reasoning', '')}"
            )
            return result.get("is_duplicate", False)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse LLM deduplication response: {content}")
            return False

    def _generate_steps(self, issue: RawIssue) -> list[str]:
        """
        Generate steps to reproduce from issue data.

        Args:
            issue: RawIssue with context

        Returns:
            List of reproduction steps
        """
        steps = []

        # Add navigation step
        if issue.url:
            steps.append(f"Navigate to {issue.url}")
        else:
            steps.append("Navigate to the affected page")

        # Add type-specific steps
        if issue.type == "console_error":
            steps.append("Open browser developer console (F12)")
            steps.append("Observe the console error as described")

        elif issue.type == "network_failure":
            steps.append("Open browser Network tab (F12 → Network)")
            steps.append("Perform the action that triggers the network request")
            steps.append("Observe the failed network request")

        elif issue.type == "performance":
            steps.append("Open browser Performance tab (F12 → Performance)")
            steps.append("Reload the page and observe the slow load time")

        elif issue.type == "visual":
            steps.append("Observe the visual defect as described")
            if "mobile" in issue.description.lower():
                steps.append("Resize browser to mobile viewport (375px width)")

        elif issue.type == "form":
            steps.append("Attempt to submit the form with the described input")
            steps.append("Observe the validation error or failure")

        elif issue.type == "accessibility":
            steps.append("Use screen reader or accessibility tools")
            steps.append("Observe the accessibility issue")

        elif issue.type == "security":
            steps.append("⚠️  WARNING: Security issue - handle with care")
            steps.append("Follow security team's reproduction guidelines")

        else:
            steps.append("Observe the issue as described in the description")

        # Add evidence step
        if issue.evidence:
            steps.append("Refer to attached evidence for additional details")

        return steps

    def _infer_expected_behavior(self, issue: RawIssue) -> str | None:
        """
        Infer expected behavior from issue type and description.

        Args:
            issue: RawIssue to analyze

        Returns:
            Expected behavior string or None
        """
        if issue.type == "console_error":
            return "No console errors should appear"

        if issue.type == "network_failure":
            return "Network request should succeed with 2xx status code"

        if issue.type == "performance":
            return "Page should load in under 3 seconds"

        if issue.type == "visual":
            return "UI should display correctly without visual defects"

        if issue.type == "form":
            return "Form should accept valid input and provide clear error messages"

        if issue.type == "accessibility":
            return "UI should be accessible to all users including those using assistive technologies"

        if issue.type == "security":
            return "Application should be secure against common vulnerabilities"

        return None

    def _estimate_affected_users(self, issue: RawIssue) -> str:
        """
        Estimate which users are affected by the issue.

        Args:
            issue: RawIssue to analyze

        Returns:
            Description of affected users
        """
        desc_lower = issue.description.lower()

        if "mobile" in desc_lower or "small screen" in desc_lower:
            return "Mobile users"

        if "desktop" in desc_lower or "large screen" in desc_lower:
            return "Desktop users"

        if "safari" in desc_lower:
            return "Safari users"

        if "firefox" in desc_lower:
            return "Firefox users"

        if "chrome" in desc_lower:
            return "Chrome users"

        if issue.priority == "critical":
            return "All users"

        if issue.priority == "high":
            return "Most users"

        return "Some users"
