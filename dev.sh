#!/usr/bin/env bash
#
# StudyLoop development command.
#
# Starts the FastAPI backend and the Vite frontend together, keeps their logs
# visible in one terminal (each line prefixed), forwards termination signals,
# and shuts both down cleanly on Ctrl+C (or when either process exits).
#
# Ports and the Python interpreter can be overridden via env vars:
#   BACKEND_PORT=8000 FRONTEND_PORT=3000 PYTHON="$ROOT/.venv/bin/python" ./dev.sh
set -euo pipefail
set -m   # run each background job in its own process group for clean signalling

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-$ROOT_DIR/.venv/bin/python}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"

# Ensure the Python virtual environment exists and is ready before starting.
if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  echo "[dev] Creating virtual environment with uv…"
  if ! command -v uv >/dev/null 2>&1; then
    echo "[dev] ERROR: uv is required. Install it: https://docs.astral.sh/uv/"
    exit 1
  fi
  (cd "$ROOT_DIR" && uv venv .venv) || exit 1
  echo "[dev] Installing backend dependencies…"
  (cd "$ROOT_DIR" && uv pip install --python "$ROOT_DIR/.venv/bin/python" -r backend/requirements.txt)
fi

BACKEND_PGID=""
FRONTEND_PGID=""
STOPPED=0

quit() {
  [[ "$STOPPED" == "1" ]] && return
  STOPPED=1
  echo
  echo "[dev] stopping backend and frontend…"
  for pg in "$BACKEND_PGID" "$FRONTEND_PGID"; do
    if [[ -n "$pg" ]]; then
      kill -TERM -- -"$pg" 2>/dev/null || kill -TERM "$pg" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
  echo "[dev] stopped."
}

trap quit INT TERM EXIT

echo "[dev] StudyLoop development server"
echo "[dev] backend  → http://127.0.0.1:$BACKEND_PORT  (Ctrl+C to stop both)"
echo "[dev] frontend → http://127.0.0.1:$FRONTEND_PORT"

(
  cd "$ROOT_DIR/backend"
  exec "$PYTHON" -m uvicorn src.main:app --reload --host 127.0.0.1 --port "$BACKEND_PORT"
) > >(sed -u "s/^/  [backend] /") 2>&1 &
BACKEND_PGID=$!

(
  cd "$ROOT_DIR/frontend"
  exec npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
) > >(sed -u "s/^/  [frontend] /") 2>&1 &
FRONTEND_PGID=$!

# Keep the script alive until one of the services exits, then stop the other.
wait -n "$BACKEND_PGID" "$FRONTEND_PGID" 2>/dev/null || true
quit