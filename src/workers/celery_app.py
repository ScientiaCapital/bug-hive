"""Celery application configuration for BugHive.

Celery is configured to use Redis as both broker and result backend.
Tasks are serialized as JSON for transparency and debuggability.

Worker Configuration:
- Max 2 concurrent tasks (crawls are resource-intensive)
- 1-hour hard limit per task
- 50-minute soft limit for graceful shutdown
- Task acks after completion (for reliability)
- Results expire after 24 hours

Task Queues:
- crawl: Heavy crawl tasks (run_crawl_session)
- tickets: Linear ticket creation (create_linear_ticket)
- media: Screenshot uploads (upload_screenshot)
- default: Misc tasks (cleanup, etc.)
"""

from celery import Celery

from src.core.config import get_settings

settings = get_settings()

# Initialize Celery app
celery_app = Celery(
    "bughive",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.workers.tasks"],  # Auto-discover tasks
)

# Core Celery Configuration
celery_app.conf.update(
    # Serialization (JSON for transparency)
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_track_started=True,  # Track when task starts (not just queued)
    task_time_limit=3600,  # Hard limit: 1 hour max per task
    task_soft_time_limit=3000,  # Soft limit: 50 minutes (graceful shutdown)
    task_ignore_result=False,  # Store results in backend
    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time (crawls are heavy)
    worker_concurrency=2,  # Max 2 concurrent crawls per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,  # Store additional metadata
    # Reliability settings
    task_acks_late=True,  # Ack after task completes (not when starting)
    task_reject_on_worker_lost=True,  # Requeue if worker crashes
    # Retry settings
    task_autoretry_for=(Exception,),  # Auto-retry on any exception
    task_retry_backoff=True,  # Exponential backoff
    task_retry_backoff_max=600,  # Max 10 minutes between retries
    task_retry_jitter=True,  # Add randomness to avoid thundering herd
)

# Task routing (organize tasks into queues)
celery_app.conf.task_routes = {
    "src.workers.tasks.run_crawl_session": {"queue": "crawl"},
    "src.workers.tasks.create_linear_ticket": {"queue": "tickets"},
    "src.workers.tasks.upload_screenshot": {"queue": "media"},
    "src.workers.tasks.cleanup_old_sessions": {"queue": "default"},
}

# Periodic task schedule (Celery Beat)
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "cleanup-old-sessions-daily": {
        "task": "src.workers.tasks.cleanup_old_sessions",
        "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM UTC
        "args": (30,),  # Delete sessions older than 30 days
    },
}
