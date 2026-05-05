#!/usr/bin/env bash
# Production — multiple workers, no reload

set -e
cd "$(dirname "$0")/.."

set -a
source .env
set +a

exec uvicorn pio_lab.main:app \
    --host 0.0.0.0 \
    --port "${APP_PORT:-8000}" \
    --workers 4 \
    --log-level info
