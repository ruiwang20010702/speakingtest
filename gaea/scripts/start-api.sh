#!/bin/bash
# ============================================
# Startup script for API service
# ============================================

set -e

echo "[API] Waiting for database..."
sleep 3

echo "[API] Starting FastAPI server..."
cd /app
exec uvicorn src.infrastructure.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${API_WORKERS:-2} \
    --log-level ${LOG_LEVEL:-info}
