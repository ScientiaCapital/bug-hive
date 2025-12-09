#!/bin/bash
# Start Celery Beat scheduler for BugHive
#
# Celery Beat is responsible for triggering periodic tasks
# (e.g., daily cleanup of old sessions)
#
# Usage:
#   ./scripts/run_beat.sh
#
# Note: Run this in a separate process from the worker

set -euo pipefail

echo "⏰ Starting BugHive Celery Beat Scheduler..."

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Load environment variables
if [ -f .env ]; then
    echo "📝 Loading environment variables from .env"
    set -a
    source .env
    set +a
else
    echo "⚠️  Warning: .env file not found"
    exit 1
fi

# Validate required environment variables
if [ -z "${REDIS_URL:-}" ]; then
    echo "❌ Error: REDIS_URL not set in .env"
    exit 1
fi

# Display configuration
echo "📊 Beat Configuration:"
echo "   Redis: ${REDIS_URL}"
echo "   Periodic Tasks:"
echo "     - cleanup-old-sessions-daily: Daily at 3:00 AM UTC"
echo ""

# Start Celery Beat
# -A: Application module
# beat: Run in beat (scheduler) mode
# --loglevel: Logging verbosity

exec celery -A src.workers.celery_app beat \
    --loglevel=info
