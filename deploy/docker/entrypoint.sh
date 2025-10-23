#!/bin/bash
set -e

# Initialize data directory from baked-in data if PVC is empty
if [ ! "$(ls -A /app/data/output 2>/dev/null)" ]; then
    echo "Initializing data directory from initial-data..."
    mkdir -p /app/data/output
    cp -r /app/initial-data/* /app/data/output/
    echo "Data initialization complete."
else
    echo "Data directory already populated, skipping initialization."
fi

# Ensure Python can find packages in appuser's local directory (needed when running as root)
export PYTHONPATH="/home/appuser/.local/lib/python3.13/site-packages:${PYTHONPATH}"

# Start the application
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --loop asyncio
