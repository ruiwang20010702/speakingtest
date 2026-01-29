#!/bin/bash
# ============================================
# Health check script
# ============================================

set -e

# Check API
curl -sf http://localhost:8000/health > /dev/null || exit 1

# Check Nginx
curl -sf http://localhost/health > /dev/null || exit 1

echo "OK"
