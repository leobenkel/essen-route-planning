#!/bin/bash
set -e

# Force watchfiles to use polling for Docker volume mounts
export WATCHFILES_FORCE_POLLING=true

# Ensure data directories exist
mkdir -p /app/data/cache /app/data/output

# Run uvicorn with auto-reload
# Don't specify --reload-dir to avoid permission issues with mounted volumes
cd /app
exec python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-delay 1
