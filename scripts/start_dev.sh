#!/usr/bin/env bash
# Dev mode — hot reload + verbose logs

set -e
cd "$(dirname "$0")/.."

# Load .env
set -a
source .env
set +a

# Start
exec uvicorn pio_lab.main:app --reload --port "${APP_PORT:-8000}" --log-level debug
