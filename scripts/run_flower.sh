#!/bin/bash
# Start Flower - Celery monitoring tool
#
# Flower provides a web UI for monitoring Celery tasks and workers
# Access at http://localhost:5555 by default
#
# Usage:
#   ./scripts/run_flower.sh
#
# Optional: Set FLOWER_PORT to change port (default: 5555)

set -euo pipefail

echo "🌸 Starting Flower - Celery Monitoring UI..."

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

# Configuration
FLOWER_PORT="${FLOWER_PORT:-5555}"
FLOWER_URL_PREFIX="${FLOWER_URL_PREFIX:-}"

# Display configuration
echo "📊 Flower Configuration:"
echo "   Port: ${FLOWER_PORT}"
echo "   Redis: ${REDIS_URL}"
echo "   URL: http://localhost:${FLOWER_PORT}${FLOWER_URL_PREFIX}"
echo ""

# Start Flower
exec celery -A src.workers.celery_app flower \
    --port="${FLOWER_PORT}" \
    --url_prefix="${FLOWER_URL_PREFIX}"
