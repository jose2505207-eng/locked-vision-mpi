#!/usr/bin/env bash
# Demo-safe launcher for the sponsor-stack build.
#
# Loads .env (sponsor flags + keys) if present, starts backend + frontend, and
# prints the sponsor status. It does NOT require any sponsor to be configured —
# anything missing simply shows inactive and the core demo runs normally.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Load local env if present (never fail if absent).
if [ -f .env ]; then set -a; . ./.env; set +a; fi

VENV="$ROOT/.venv/bin"
echo "==============================================="
echo " Locked Vision MPI — sponsor demo"
echo "   ENABLE_SPONSOR_STACK = ${ENABLE_SPONSOR_STACK:-false}"
echo "   (missing sponsor keys just show as inactive)"
echo "==============================================="

cleanup() { kill "${BACK:-}" "${FRONT:-}" 2>/dev/null || true; }
trap cleanup INT TERM EXIT

# Backend
( cd "$ROOT/backend" && "$VENV/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload ) &
BACK=$!

# Frontend
( cd "$ROOT/frontend" && npm run dev ) &
FRONT=$!

# Wait for the backend, then show what's active.
for _ in $(seq 1 15); do
  if curl -sf -o /dev/null http://localhost:8000/health 2>/dev/null; then break; fi
  sleep 1
done
echo "--- sponsor status ---"
curl -s http://localhost:8000/api/sponsors/status | python3 -m json.tool 2>/dev/null || \
  echo "(status endpoint not ready yet)"
echo "----------------------"
echo "Backend  : http://localhost:8000  (docs: /docs)"
echo "Frontend : http://localhost:5173"
echo "Ctrl+C to stop both."

wait
