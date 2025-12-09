"""Crawl session management endpoints."""

from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, status

from ..deps.auth import APIKeyDep
from ..deps.database import BugRepoDep, SessionRepoDep
from ..schemas import (
    CrawlStartRequest,
    CrawlStartResponse,
    CrawlStatusResponse,
    CrawlStopResponse,
    SessionBugsResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post(
    "/start",
    response_model=CrawlStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new crawl session",
    description="Create a new crawl session and queue it for processing",
)
async def start_crawl(
    request: CrawlStartRequest,
    session_repo: SessionRepoDep,
    api_key: APIKeyDep,
) -> CrawlStartResponse:
    """
    Start a new crawl session.

    Creates a crawl session in the database with status 'pending'
    and queues it for processing by the Celery worker.

    Args:
        request: Crawl configuration
        session_repo: Session repository
        api_key: Validated API key

    Returns:
        Created session information

    Raises:
        HTTPException: If session creation fails
    """
    try:
        # Convert request to CrawlConfig
        config = request.to_crawl_config()

        # Create session in database
        session = await session_repo.create_session(
            base_url=request.base_url,
            config=config,
        )

        logger.info(
            "crawl_session_created",
            session_id=str(session.id),
            base_url=request.base_url,
            max_pages=request.max_pages,
        )

        # Queue crawl task with Celery
        from src.workers.tasks import run_crawl_session

        task = run_crawl_session.delay(
            str(session.id),
            config.model_dump()
        )

        logger.info(
            "crawl_task_queued",
            session_id=str(session.id),
            task_id=task.id,
        )

        return CrawlStartResponse(
            session_id=session.id,
            base_url=session.base_url,
            status=session.status,
            created_at=session.created_at,
            message=f"Crawl session created. Task queued: {task.id}",
        )

    except Exception as exc:
        logger.error(
            "crawl_start_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            base_url=request.base_url,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create crawl session: {str(exc)}",
        ) from exc


@router.get(
    "/{session_id}/status",
    response_model=CrawlStatusResponse,
    summary="Get crawl session status",
    description="Retrieve current status and progress of a crawl session",
)
async def get_crawl_status(
    session_id: UUID,
    session_repo: SessionRepoDep,
    api_key: APIKeyDep,
) -> CrawlStatusResponse:
    """
    Get crawl session status and progress.

    Returns:
        Session status with metrics and progress

    Raises:
        HTTPException: If session not found
    """
    try:
        session = await session_repo.get_by_id(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Crawl session {session_id} not found",
            )

        # Calculate elapsed time
        elapsed_time = None
        if session.started_at:
            end_time = session.completed_at or datetime.utcnow()
            elapsed_time = (end_time - session.started_at).total_seconds()

        # Calculate metrics
        success_rate = None
        if session.pages_discovered > 0:
            success_rate = (session.pages_crawled / session.pages_discovered) * 100

        bugs_per_page = None
        if session.pages_crawled > 0:
            bugs_per_page = session.bugs_found / session.pages_crawled

        return CrawlStatusResponse(
            session_id=session.id,
            base_url=session.base_url,
            status=session.status,
            pages_discovered=session.pages_discovered,
            pages_crawled=session.pages_crawled,
            bugs_found=session.bugs_found,
            total_cost=float(session.total_cost),
            started_at=session.started_at,
            completed_at=session.completed_at,
            elapsed_time=elapsed_time,
            error_message=session.error_message,
            success_rate=success_rate,
            bugs_per_page=bugs_per_page,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "get_crawl_status_failed",
            session_id=str(session_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session status: {str(exc)}",
        ) from exc


@router.get(
    "/{session_id}/bugs",
    response_model=SessionBugsResponse,
    summary="Get bugs found in session",
    description="Retrieve all bugs found during a crawl session with pagination",
)
async def get_session_bugs(
    session_id: UUID,
    priority: str | None = None,
    category: str | None = None,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 100,
    bug_repo: BugRepoDep = None,
    session_repo: SessionRepoDep = None,
    api_key: APIKeyDep = None,
) -> SessionBugsResponse:
    """
    Get all bugs found in a crawl session.

    Supports filtering by priority, category, and status.
    Returns bugs with pagination and summary statistics.

    Args:
        session_id: Session ID
        priority: Filter by priority (critical, high, medium, low)
        category: Filter by category (ui_ux, data, edge_case, performance, security)
        status_filter: Filter by status (detected, validated, reported, dismissed)
        skip: Number of bugs to skip
        limit: Maximum number of bugs to return
        bug_repo: Bug repository
        session_repo: Session repository
        api_key: Validated API key

    Returns:
        List of bugs with statistics

    Raises:
        HTTPException: If session not found or query fails
    """
    try:
        # Verify session exists
        session = await session_repo.get_by_id(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Crawl session {session_id} not found",
            )

        # Get bugs with filters
        bugs = await bug_repo.get_session_bugs(
            session_id=session_id,
            status=status_filter,
            priority=priority,
            category=category,
            skip=skip,
            limit=limit,
        )

        # Get total count with same filters
        total = await bug_repo.count(
            session_id=session_id,
            status=status_filter,
            priority=priority,
            category=category,
        )

        # Get statistics
        by_priority = await bug_repo.count_by_priority(
            session_id=session_id,
            status=status_filter,
        )
        by_category = await bug_repo.count_by_category(
            session_id=session_id,
            status=status_filter,
        )

        # Convert DB models to Pydantic models
        from ...models.bug import Bug
        bug_models = [
            Bug(
                id=bug.id,
                session_id=bug.session_id,
                page_id=bug.page_id,
                category=bug.category,
                priority=bug.priority,
                title=bug.title,
                description=bug.description,
                steps_to_reproduce=bug.steps_to_reproduce,
                evidence=[],  # Evidence is stored as JSONB, convert if needed
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
            )
            for bug in bugs
        ]

        return SessionBugsResponse(
            session_id=session_id,
            bugs=bug_models,
            total=total,
            page=skip // limit + 1,
            page_size=limit,
            by_priority=by_priority,
            by_category=by_category,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "get_session_bugs_failed",
            session_id=str(session_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve bugs: {str(exc)}",
        ) from exc


@router.post(
    "/{session_id}/stop",
    response_model=CrawlStopResponse,
    summary="Stop a running crawl session",
    description="Stop a crawl session that is currently running",
)
async def stop_crawl(
    session_id: UUID,
    session_repo: SessionRepoDep,
    api_key: APIKeyDep,
) -> CrawlStopResponse:
    """
    Stop a running crawl session.

    Marks the session as completed and signals the worker to stop processing.

    Args:
        session_id: Session ID to stop
        session_repo: Session repository
        api_key: Validated API key

    Returns:
        Stop confirmation with final statistics

    Raises:
        HTTPException: If session not found or not running
    """
    try:
        # Get current session
        session = await session_repo.get_by_id(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Crawl session {session_id} not found",
            )

        if session.status not in ["pending", "running"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stop session with status '{session.status}'. "
                       f"Only pending or running sessions can be stopped.",
            )

        previous_status = session.status

        # Mark session as completed
        updated_session = await session_repo.complete_session(
            session_id=session_id,
            success=True,
        )

        logger.info(
            "crawl_session_stopped",
            session_id=str(session_id),
            previous_status=previous_status,
            pages_crawled=updated_session.pages_crawled,
            bugs_found=updated_session.bugs_found,
        )

        # Signal Celery worker to stop processing
        from src.workers.celery_app import celery_app
        from src.workers.session_manager import SessionManager

        # Get task ID from Redis
        session_manager = SessionManager()
        session_state = session_manager.get_session_state(str(session_id))

        if session_state and session_state.get("task_id"):
            task_id = session_state["task_id"]
            celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
            logger.info("crawl_task_revoked", task_id=task_id)

        return CrawlStopResponse(
            session_id=session_id,
            previous_status=previous_status,
            new_status=updated_session.status,
            message="Crawl session stopped successfully",
            pages_crawled=updated_session.pages_crawled,
            bugs_found=updated_session.bugs_found,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "stop_crawl_failed",
            session_id=str(session_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop crawl session: {str(exc)}",
        ) from exc
