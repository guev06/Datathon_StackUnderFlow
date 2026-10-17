#!/usr/bin/env bash
# Builds the FlowState frontend and serves it together with the AI backend on one port.
#   ./backend/start.sh            -> http://localhost:8000
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FRONTEND="$HERE/../frontend/flowstate"
PORT="${PORT:-8000}"

if [ ! -d "$HERE/.venv" ]; then
  python3 -m venv "$HERE/.venv"
  CMAKE_ARGS="${CMAKE_ARGS:--DGGML_METAL=on}" "$HERE/.venv/bin/pip" install -r "$HERE/repo_dataflow_ai/requirements.txt"
fi
if [ ! -d "$FRONTEND/node_modules" ]; then (cd "$FRONTEND" && npm install); fi
(cd "$FRONTEND" && npm run build)

cd "$HERE/repo_dataflow_ai"
exec "$HERE/.venv/bin/uvicorn" server:app --host 127.0.0.1 --port "$PORT"
