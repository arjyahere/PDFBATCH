#!/bin/bash
# Start the Batch Highlighter API with multiple worker instances
# Uses Uvicorn's built-in multiprocessing

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-8}"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              Batch Highlighter API Cluster Mode                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Starting Uvicorn with $WORKERS workers on $HOST:$PORT"
echo ""

# Start the server with multiple workers
exec uvicorn main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --no-reload \
    --access-log \
    --log-level info
