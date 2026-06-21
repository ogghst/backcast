#!/usr/bin/env bash
# Run the agent scheduler locally (dev), reading the SAME env as the backend.
#
# The scheduler is a separate, always-on process that polls the shared DB every
# SCHEDULER_POLL_INTERVAL_SECONDS and fires due schedules by calling the backend
# trigger API as the schedule owner. It owns scheduling only — agent runs live in
# the backend process (the in-memory ExecutionLifecycle/event-bus are
# single-process), so it must be able to reach the backend over HTTP.
#
# Usage:
#   ./scripts/run-scheduler.sh            # from backend/ (or anywhere — it cd's)
#   SCHEDULER_API_BASE_URL=http://host.docker.internal:8020 ./scripts/run-scheduler.sh
#
# Env:
#   - Reads backend/.env (pydantic-settings loads it relative to CWD = backend/),
#     exactly like `uvicorn app.main:app` does.
#   - SCHEDULER_API_BASE_URL defaults to http://localhost:8020 (the local backend).
#     Override for non-default setups (e.g. docker-to-host).
set -euo pipefail

# Resolve the backend dir (this script lives in backend/scripts/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

# Local backend (uvicorn --port 8020 in dev-start.sh). Override via env if needed.
export SCHEDULER_API_BASE_URL="${SCHEDULER_API_BASE_URL:-http://localhost:8020}"

exec uv run python -m app.scheduler
