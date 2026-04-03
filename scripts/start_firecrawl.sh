#!/usr/bin/env bash
# start_firecrawl.sh — Start the self-hosted Firecrawl Docker Compose stack
# with pre-flight checks before running docker compose up -d.
set -euo pipefail

COMPOSE_FILE="$(dirname "$(realpath "$0")")/../docker-compose.firecrawl.yml"
API_PORT="3002"

echo "=== Firecrawl pre-flight checks ==="

# 1. Docker daemon must be running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running or not accessible."
    echo "       Start Docker and try again."
    exit 1
fi
echo "[OK] Docker daemon is running."

# 2. Compose file must exist
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "ERROR: Compose file not found: $COMPOSE_FILE"
    exit 1
fi
echo "[OK] Compose file found: $COMPOSE_FILE"

# 3. Port 3002 must be free
if command -v lsof > /dev/null 2>&1; then
    if lsof -iTCP:"$API_PORT" -sTCP:LISTEN > /dev/null 2>&1; then
        echo "ERROR: Port $API_PORT is already in use."
        echo "       Stop the conflicting process and try again."
        exit 1
    fi
elif command -v ss > /dev/null 2>&1; then
    if ss -tlnp | grep -q ":${API_PORT} "; then
        echo "ERROR: Port $API_PORT is already in use."
        exit 1
    fi
fi
echo "[OK] Port $API_PORT is available."

echo ""
echo "=== Starting Firecrawl stack ==="
docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "Firecrawl API will be reachable at http://localhost:${API_PORT}"
echo "Health endpoint: http://localhost:${API_PORT}/health"
echo "Logs: docker compose -f $COMPOSE_FILE logs -f"
