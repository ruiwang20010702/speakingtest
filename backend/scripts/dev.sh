#!/bin/bash
# 开发环境启动脚本
# 自动启动 RabbitMQ、后端 API、Part 2 Worker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# 确保 Erlang 在 PATH 中
export PATH="/opt/homebrew/opt/erlang/bin:$PATH"

# 存储子进程 PID
WORKER_PID=""

# RabbitMQ 控制函数
start_rabbitmq() {
    echo "🐰 启动 RabbitMQ..."
    if lsof -i :5672 > /dev/null 2>&1; then
        echo "   RabbitMQ 已在运行"
    else
        /opt/homebrew/opt/rabbitmq/sbin/rabbitmq-server &
        echo "   等待 RabbitMQ 启动..."
        sleep 3
        if lsof -i :5672 > /dev/null 2>&1; then
            echo "   ✅ RabbitMQ 启动成功"
        else
            echo "   ❌ RabbitMQ 启动失败"
            exit 1
        fi
    fi
}

stop_rabbitmq() {
    echo "🐰 关闭 RabbitMQ..."
    /opt/homebrew/opt/rabbitmq/sbin/rabbitmqctl stop 2>/dev/null || true
    echo "   ✅ RabbitMQ 已关闭"
}

start_worker() {
    echo "👷 启动 Part 2 Worker..."
    cd "$BACKEND_DIR"
    source venv/bin/activate
    python scripts/part2_worker.py &
    WORKER_PID=$!
    echo "   ✅ Worker PID: $WORKER_PID"
}

stop_worker() {
    if [ -n "$WORKER_PID" ]; then
        echo "👷 关闭 Part 2 Worker..."
        kill $WORKER_PID 2>/dev/null || true
        echo "   ✅ Worker 已关闭"
    fi
}

# 捕获退出信号
cleanup() {
    echo ""
    echo "🛑 收到退出信号，清理资源..."
    stop_worker
    stop_rabbitmq
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 启动服务
start_rabbitmq
start_worker

# 启动后端 API
echo ""
echo "🚀 启动后端 API 服务..."
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn src.infrastructure.main:app --reload --host 0.0.0.0 --port 8000
