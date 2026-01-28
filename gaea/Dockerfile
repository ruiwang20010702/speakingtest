# ============================================
# AI Speaking Test System - Multi-service Container
# Base: Debian 11 (Bullseye) + s6-overlay
# Services: FastAPI + Workers + Nginx (static files)
# ============================================

# Build stage for frontend
FROM node:20-bullseye AS frontend-builder

WORKDIR /build

# Use Tencent Cloud npm registry for faster downloads in China
RUN npm config set registry https://npm.bjtest.51talk.biz/npm

# Copy all frontend projects
COPY frontend/student-h5 /build/student-h5
COPY frontend/parent-h5 /build/parent-h5
COPY frontend/teacher-web /build/teacher-web

# Build student-h5
WORKDIR /build/student-h5
RUN npm ci && npm run build

# Build parent-h5
WORKDIR /build/parent-h5
RUN npm ci && npm run build

# Build teacher-web
WORKDIR /build/teacher-web
RUN npm ci && npm run build

# ============================================
# Final runtime image
# ============================================
FROM python:3.11-slim-bullseye

# s6-overlay version
ARG S6_OVERLAY_VERSION=3.1.6.2

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV GAEA_BASE_URL="https://flow.51talk.biz/pkg/ops/app/files"
# Switch to Tencent Cloud mirror for faster downloads in China
RUN sed -i 's/deb.debian.org/mirrors.cloud.tencent.com/g' /etc/apt/sources.list && \
    sed -i 's/security.debian.org/mirrors.cloud.tencent.com/g' /etc/apt/sources.list

# Install system dependencies (Python already included in base image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    curl \
    ca-certificates \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install s6-overlay
ADD ${GAEA_BASE_URL}/${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
ADD ${GAEA_BASE_URL}/${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz \
    && tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz \
    && rm /tmp/s6-overlay-*.tar.xz

# Create app user
RUN useradd -m -s /bin/bash app

# Install Python dependencies (using Tencent Cloud PyPI mirror)
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -i https://mirrors.cloud.tencent.com/pypi/simple \
    --trusted-host mirrors.cloud.tencent.com \
    -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# Copy backend source code
COPY backend/src /app/src
COPY backend/scripts /app/scripts

# Copy frontend build artifacts
COPY --from=frontend-builder /build/student-h5/dist /var/www/student-h5
COPY --from=frontend-builder /build/parent-h5/dist /var/www/parent-h5
COPY --from=frontend-builder /build/teacher-web/dist /var/www/teacher-web

# Copy nginx configuration
COPY gaea/nginx/nginx.conf /etc/nginx/nginx.conf
COPY gaea/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy s6 service definitions
COPY gaea/s6-rc.d /etc/s6-overlay/s6-rc.d

# Copy startup scripts
COPY gaea/scripts /app/gaea-scripts
RUN chmod +x /app/gaea-scripts/*.sh

# Set permissions
RUN chown -R app:app /app /var/www \
    && chown -R app:app /var/log/nginx \
    && chown -R app:app /var/lib/nginx \
    && chmod -R 755 /etc/s6-overlay/s6-rc.d

# Working directory
WORKDIR /app

# Environment variables
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    # s6-overlay settings
    S6_KEEP_ENV=1 \
    S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=60000

# Expose ports
# 80 - Nginx (frontend static + API proxy)
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# s6-overlay entrypoint
ENTRYPOINT ["/init"]
