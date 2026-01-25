#!/bin/bash
# 开发环境启动脚本
# 自动启动 Redis、RabbitMQ、后端 API、Part 1 Worker、Part 2 Worker、Interpretation Worker、DLQ Worker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

# 确保 Erlang 在 PATH 中
export PATH="/opt/homebrew/opt/erlang/bin:$PATH"

# 存储子进程 PID
WORKER1_PID=""
WORKER2_PID=""
WORKER3_PID=""
DLQ_WORKER_PID=""
REDIS_PID=""

# Redis 控制函数
start_redis() {
    echo "🔴 启动 Redis..."
    if lsof -i :6379 > /dev/null 2>&1; then
        echo "   Redis 已在运行"
    else
        # 尝试使用 Homebrew 安装的 Redis
        if [ -x "/opt/homebrew/opt/redis/bin/redis-server" ]; then
            /opt/homebrew/opt/redis/bin/redis-server /opt/homebrew/etc/redis.conf --daemonize yes
        elif command -v redis-server > /dev/null 2>&1; then
            redis-server --daemonize yes
        else
            echo "   ⚠️  Redis 未安装，跳过（缓存和限流将使用内存模式）"
            echo "   💡 安装 Redis: brew install redis"
            return 0
        fi
        
        sleep 2
        if lsof -i :6379 > /dev/null 2>&1; then
            echo "   ✅ Redis 启动成功"
        else
            echo "   ⚠️  Redis 启动失败，继续运行（缓存和限流将使用内存模式）"
        fi
    fi
}

stop_redis() {
    echo "🔴 关闭 Redis..."
    if command -v redis-cli > /dev/null 2>&1; then
        redis-cli shutdown 2>/dev/null || true
    fi
    echo "   ✅ Redis 已关闭"
}

# RabbitMQ 控制函数
start_rabbitmq() {
    echo "🐰 启动 RabbitMQ..."
    if lsof -i :5672 > /dev/null 2>&1; then
        echo "   RabbitMQ 已在运行"
    else
        /opt/homebrew/opt/rabbitmq/sbin/rabbitmq-server &
        echo "   等待 RabbitMQ 启动..."
        sleep 10
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

start_workers() {
    cd "$BACKEND_DIR"
    source venv/bin/activate
    
    echo "👷 启动 Part 1 Worker..."
    python scripts/part1_worker.py &
    WORKER1_PID=$!
    echo "   ✅ Part 1 Worker PID: $WORKER1_PID"
    
    echo "👷 启动 Part 2 Worker..."
    python scripts/part2_worker.py &
    WORKER2_PID=$!
    echo "   ✅ Part 2 Worker PID: $WORKER2_PID"
    
    echo "👷 启动 Interpretation Worker..."
    python scripts/interpretation_worker.py &
    WORKER3_PID=$!
    echo "   ✅ Interpretation Worker PID: $WORKER3_PID"
    
    echo "👷 启动 DLQ Worker (死信队列)..."
    python scripts/dlq_worker.py &
    DLQ_WORKER_PID=$!
    echo "   ✅ DLQ Worker PID: $DLQ_WORKER_PID"
}

stop_workers() {
    if [ -n "$WORKER1_PID" ]; then
        echo "👷 关闭 Part 1 Worker..."
        kill $WORKER1_PID 2>/dev/null || true
    fi
    if [ -n "$WORKER2_PID" ]; then
        echo "👷 关闭 Part 2 Worker..."
        kill $WORKER2_PID 2>/dev/null || true
    fi
    if [ -n "$WORKER3_PID" ]; then
        echo "👷 关闭 Interpretation Worker..."
        kill $WORKER3_PID 2>/dev/null || true
    fi
    if [ -n "$DLQ_WORKER_PID" ]; then
        echo "👷 关闭 DLQ Worker..."
        kill $DLQ_WORKER_PID 2>/dev/null || true
    fi
    echo "   ✅ Workers 已关闭"
}

# 捕获退出信号
cleanup() {
    echo ""
    echo "🛑 收到退出信号，清理资源..."
    stop_workers
    stop_rabbitmq
    stop_redis
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 启动服务
start_redis
start_rabbitmq
start_workers

# 启动后端 API
echo ""
echo "🚀 启动后端 API 服务..."
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn src.infrastructure.main:app --reload --host 0.0.0.0 --port 8000
