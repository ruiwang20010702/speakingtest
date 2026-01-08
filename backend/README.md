# Speaking Test System - Backend

## 依赖服务

| 服务 | 用途 | 安装命令 |
|------|------|----------|
| PostgreSQL | 主数据库 | `brew install postgresql@15` |
| RabbitMQ | Part 2 异步任务队列 | `brew install rabbitmq` |

## Quick Start

### 方式一：使用开发脚本（推荐）

```bash
cd backend

# 首次运行需创建虚拟环境并安装依赖
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动开发服务器（自动管理 RabbitMQ + Worker）
./scripts/dev.sh
```

> 💡 `dev.sh` 会自动启动：
> - RabbitMQ 消息队列
> - Part 2 Worker（处理队列中的评测任务）
> - FastAPI 后端 API
> 
> 按 `Ctrl+C` 退出时会自动清理所有服务

### 方式二：手动启动

```bash
cd backend

# 1. 启动 RabbitMQ（新终端）
PATH="/opt/homebrew/opt/erlang/bin:$PATH" /opt/homebrew/opt/rabbitmq/sbin/rabbitmq-server

# 2. 启动后端
source venv/bin/activate
uvicorn src.infrastructure.main:app --reload --host 0.0.0.0 --port 8000
```


## Project Structure

```
backend/
├── src/
│   ├── domain/           # Core business entities & interfaces
│   ├── use_cases/        # Application logic
│   ├── adapters/         # External implementations
│   │   ├── repositories/ # Database access
│   │   ├── gateways/     # External APIs (Xunfei, Qwen)
│   │   └── controllers/  # FastAPI routers
│   └── infrastructure/   # App config & framework setup
└── database/
    └── init.sql          # PostgreSQL schema
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
