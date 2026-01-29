#!/bin/bash
# ============================================
# Startup script for worker services
# ============================================

set -e

WORKER_TYPE=${1:-part1}

echo "[Worker] Starting ${WORKER_TYPE} worker..."
cd /app

case $WORKER_TYPE in
    part1)
        exec python /app/scripts/part1_worker.py
        ;;
    part2)
        exec python /app/scripts/part2_worker.py
        ;;
    interpretation)
        exec python /app/scripts/interpretation_worker.py
        ;;
    dlq)
        exec python /app/scripts/dlq_worker.py
        ;;
    *)
        echo "Unknown worker type: $WORKER_TYPE"
        exit 1
        ;;
esac
