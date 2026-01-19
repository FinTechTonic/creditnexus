#!/usr/bin/env bash
# Run .nexus file transfer E2E test with PM2 dev stack.
# 1) Ensures PM2 stack is running (backend 8000, frontend 5000).
# 2) Waits for GET /api/health 200.
# 3) Runs tests/compatibility/test_nexus_file_transfer_e2e.py
#
# Usage: from project root:
#   ./scripts/dev/run_nexus_e2e.sh

set -e
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
BASE_URL="${BASE_URL%/}"
HEALTH_URL="${BASE_URL}/api/health"
TIMEOUT="${NEXUS_E2E_HEALTH_TIMEOUT:-60}"

echo "[run_nexus_e2e] Ensuring PM2 stack..."
npm run dev:pm2 2>/dev/null || true
sleep 3

echo "[run_nexus_e2e] Waiting for backend at $HEALTH_URL ..."
t=0
while [ "$t" -lt "$TIMEOUT" ]; do
  if curl -sSf -m 5 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "[run_nexus_e2e] Backend healthy."
    break
  fi
  echo "[run_nexus_e2e] Waiting... ($t/$TIMEOUT)"
  sleep 1
  t=$((t + 1))
done
if [ "$t" -ge "$TIMEOUT" ]; then
  echo "[run_nexus_e2e] ERROR: Backend not healthy after ${TIMEOUT}s. Run: npm run dev:pm2" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"
uv run python tests/compatibility/test_nexus_file_transfer_e2e.py
exit $?
