#!/bin/bash
# Start the Batch Highlighter API with multiple worker instances
# Uses Uvicorn's built-in multiprocessing

set -e

# Resolve repo root from this script's location, then work in the backend folder
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/batch_highlighter_api_integrated"
cd "$BACKEND"

# Load environment variables (handles values containing spaces and Windows line endings)
if [ -f .env ]; then
    set -a
    while IFS='=' read -r key value || [ -n "$key" ]; do
        key="${key%$'\r'}"
        value="${value%$'\r'}"
        case "$key" in
            ''|\#*) continue ;;
        esac
        export "$key=$value"
    done < .env
    set +a
fi

# Default values
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-8}"

# Uvicorn is installed in the backend virtual environment
if [ -f "$BACKEND/.venv/Scripts/activate" ]; then
    . "$BACKEND/.venv/Scripts/activate"
elif [ -f "$BACKEND/.venv/bin/activate" ]; then
    . "$BACKEND/.venv/bin/activate"
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              Batch Highlighter API Cluster Mode                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Starting Uvicorn with $WORKERS workers on $HOST:$PORT"
echo "Backend: $BACKEND"
echo ""

# Start the server with multiple workers
exec uvicorn main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --no-reload \
    --access-log \
    --log-level info
