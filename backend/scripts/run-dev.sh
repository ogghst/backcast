#! /usr/bin/env bash

# Run FastAPI development server on port 8010 by default
# Usage: ./scripts/run-dev.sh [port]
# Example: ./scripts/run-dev.sh  # Runs on port 8010
# Example: ./scripts/run-dev.sh 8000  # Runs on port 8000

set -e

PORT=${1:-8010}

fastapi run --reload --port "$PORT" app/main.py
