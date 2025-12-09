#!/bin/bash
# Start Celery worker for BugHive
#
# Usage:
#   ./scripts/run_worker.sh
#
# Environment variables are loaded from .env file
# Worker processes tasks from multiple queues with different priorities

set -euo pipefail

echo "🚀 Starting BugHive Celery Worker..."

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
    echo "   Please create .env file with required variables"
    exit 1
fi

# Validate required environment variables
if [ -z "${REDIS_URL:-}" ]; then
    echo "❌ Error: REDIS_URL not set in .env"
    exit 1
fi

# Display configuration
echo "📊 Worker Configuration:"
echo "   Concurrency: 2 workers"
echo "   Queues: crawl, tickets, media, default"
echo "   Log Level: info"
echo "   Redis: ${REDIS_URL}"
echo ""

# Start the Celery worker
# -A: Application module
# worker: Run in worker mode
# --loglevel: Logging verbosity
# --concurrency: Number of worker processes
# -Q: Queues to consume from
# --hostname: Unique worker identifier

exec celery -A src.workers.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    -Q crawl,tickets,media,default \
    --hostname=worker@%h \
    --max-tasks-per-child=50 \
    --time-limit=3600 \
    --soft-time-limit=3000
