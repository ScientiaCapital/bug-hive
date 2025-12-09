"""Bug management endpoints."""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, status

from ...core.config import get_settings
from ..deps.auth import APIKeyDep
from ..deps.database import BugRepoDep, PageRepoDep
from ..schemas import (
    BugReportResponse,
    BugResponse,
    BugValidateRequest,
    BugValidateResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/bugs", tags=["bugs"])


@router.get(
    "/{bug_id}",
    response_model=BugResponse,
    summary="Get bug details",
    description="Retrieve detailed information about a specific bug",
)
async def get_bug(
    bug_id: UUID,
    bug_repo: BugRepoDep,
    page_repo: PageRepoDep,
    api_key: APIKeyDep,
) -> BugResponse:
    """
    Get bug details including evidence and page information.

    Args:
        bug_id: Bug ID
        bug_repo: Bug repository
        page_repo: Page repository
        api_key: Validated API key

    Returns:
        Bug details with page URL

    Raises:
        HTTPException: If bug not found
    """
    try:
        bug = await bug_repo.get_by_id(bug_id)

        if bug is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bug {bug_id} not found",
            )

        # Get page URL
        page = await page_repo.get_by_id(bug.page_id)
        page_url = page.url if page else None

        # Convert evidence from JSONB to Evidence models
        from ...models.evidence import Evidence
        evidence_models = [
            Evidence(**e) if isinstance(e, dict) else e
            for e in (bug.evidence or [])
        ]

        return BugResponse(
            id=bug.id,
            session_id=bug.session_id,
            page_id=bug.page_id,
            category=bug.category,
            priority=bug.priority,
            title=bug.title,
            description=bug.description,
            steps_to_reproduce=bug.steps_to_reproduce,
            evidence=evidence_models,
            confidence=float(bug.confidence),
            status=bug.status,
            linear_issue_id=bug.linear_issue_id,
            linear_issue_url=bug.linear_issue_url,
            expected_behavior=bug.expected_behavior,
            actual_behavior=bug.actual_behavior,
            affected_users=bug.affected_users,
            browser_info=bug.browser_info,
            dismissed_reason=bug.dismissed_reason,
            dismissed_at=bug.dismissed_at,
            reported_at=bug.reported_at,
            created_at=bug.created_at,
            updated_at=bug.updated_at,
            page_url=page_url,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "get_bug_failed",
            bug_id=str(bug_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bug: {str(exc)}",
        ) from exc


@router.post(
    "/{bug_id}/validate",
    response_model=BugValidateResponse,
    summary="Validate or dismiss a bug",
    description="Mark a bug as validated (real) or dismissed (false positive)",
)
async def validate_bug(
    bug_id: UUID,
    request: BugValidateRequest,
    bug_repo: BugRepoDep,
    api_key: APIKeyDep,
) -> BugValidateResponse:
    """
    Mark bug as validated or dismissed.

    This allows human review of AI-detected bugs.
    Validated bugs can be reported to Linear.
    Dismissed bugs are marked as false positives.

    Args:
        bug_id: Bug ID
        request: Validation decision
        bug_repo: Bug repository
        api_key: Validated API key

    Returns:
        Validation result

    Raises:
        HTTPException: If bug not found or validation fails
    """
    try:
        bug = await bug_repo.get_by_id(bug_id)

        if bug is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bug {bug_id} not found",
            )

        previous_status = bug.status

        if request.is_valid:
            # Mark as validated
            updated_bug = await bug_repo.mark_validated(bug_id)
            message = "Bug marked as validated"
            new_status = "validated"

            logger.info(
                "bug_validated",
                bug_id=str(bug_id),
                title=bug.title,
                notes=request.notes,
            )

        else:
            # Mark as dismissed
            notes = request.notes or "No reason provided"
            updated_bug = await bug_repo.mark_dismissed(
                bug_id=bug_id,
                reason=notes,
            )
            message = "Bug marked as dismissed"
            new_status = "dismissed"

            logger.info(
                "bug_dismissed",
                bug_id=str(bug_id),
                title=bug.title,
                reason=notes,
            )

        return BugValidateResponse(
            bug_id=bug_id,
            previous_status=previous_status,
            new_status=new_status,
            message=message,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "validate_bug_failed",
            bug_id=str(bug_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate bug: {str(exc)}",
        ) from exc


@router.post(
    "/{bug_id}/report",
    response_model=BugReportResponse,
    summary="Report bug to Linear",
    description="Create a Linear issue for this bug",
)
async def report_bug(
    bug_id: UUID,
    bug_repo: BugRepoDep,
    page_repo: PageRepoDep,
    api_key: APIKeyDep,
) -> BugReportResponse:
    """
    Create Linear ticket for this bug.

    Requires LINEAR_API_KEY to be configured.
    Creates a formatted issue in Linear with bug details and evidence.

    Args:
        bug_id: Bug ID
        bug_repo: Bug repository
        page_repo: Page repository
        api_key: Validated API key

    Returns:
        Linear issue information

    Raises:
        HTTPException: If bug not found, already reported, or Linear integration fails
    """
    try:
        settings = get_settings()

        # Check if Linear is configured
        if not settings.LINEAR_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Linear integration not configured. Set LINEAR_API_KEY.",
            )

        # Get bug
        bug = await bug_repo.get_by_id(bug_id)

        if bug is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bug {bug_id} not found",
            )

        # Check if already reported
        if bug.status == "reported":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bug already reported to Linear: {bug.linear_issue_url}",
            )

        # Get page URL
        page = await page_repo.get_by_id(bug.page_id)
        page_url = page.url if page else "Unknown"

        # Format bug report
        from ...models.bug import BugReport
        from ...models.evidence import Evidence

        # Convert evidence
        evidence_models = [
            Evidence(**e) if isinstance(e, dict) else e
            for e in (bug.evidence or [])
        ]
        evidence_urls = [
            e.content
            for e in evidence_models
            if e.type == "screenshot"
        ]

        bug_report = BugReport(
            title=bug.title,
            description=bug.description,
            priority=bug.priority,
            category=bug.category,
            steps_to_reproduce=bug.steps_to_reproduce,
            evidence_urls=evidence_urls,
            page_url=page_url,
            confidence=float(bug.confidence),
        )

        # TODO: Integrate with Linear API
        # For now, return mock response
        linear_issue_id = f"BUG-{bug_id.hex[:8]}"
        linear_issue_url = f"https://linear.app/bughive/issue/{linear_issue_id}"

        # Mock Linear API call
        logger.info(
            "bug_reported_to_linear",
            bug_id=str(bug_id),
            linear_issue_id=linear_issue_id,
            title=bug.title,
        )

        # Update bug with Linear information
        await bug_repo.mark_reported(
            bug_id=bug_id,
            linear_issue_id=linear_issue_id,
            linear_issue_url=linear_issue_url,
        )

        return BugReportResponse(
            bug_id=bug_id,
            linear_issue_id=linear_issue_id,
            linear_issue_url=linear_issue_url,
            reported_at=datetime.utcnow(),
            message="Bug successfully reported to Linear (mock implementation)",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "report_bug_failed",
            bug_id=str(bug_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to report bug: {str(exc)}",
        ) from exc
