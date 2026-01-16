# Speaking Test System - Backend

基于 **FastAPI + RabbitMQ + Qwen-Omni** 构建的 AI 口语测评后端服务。

## 🌟 核心功能

- **Token 鉴权**：基于 JWT 的教师/管理员认证，一次性 Token 的学生入口。
- **Part 1 测评**：单词朗读评测，基于 Qwen-Omni 音频理解。
- **Part 2 测评**：开放式问答评测，异步处理，支持流利度/内容/语法多维度评分。
- **报告生成**：自动生成学生能力雷达图、强弱项分析及个性化建议。
- **数据管理**：学生档案、题库管理、测评记录持久化。

## 🛠️ 技术栈

- **Language**: Python 3.11+
- **Framework**: FastAPI (Async)
- **Database**: PostgreSQL (SQLAlchemy + AsyncPG)
- **Queue**: RabbitMQ (aio-pika)
- **Storage**: Aliyun OSS
- **AI**: Qwen-Omni (Audio), Qwen-Plus (Text Analysis)

## 📋 前置依赖

| 服务 | 用途 | 必须? | 安装命令 (macOS) |
|------|------|-------|------------------|
| **PostgreSQL** | 主数据库 | ✅ | `brew install postgresql@15` |
| **RabbitMQ** | 异步任务队列 | ✅ | `brew install rabbitmq` |
| **Redis** | 限流/缓存 | ❌ (生产建议) | `brew install redis` |

## 🚀 快速启动 (Quick Start)

### 1. 环境准备

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库、OSS、Qwen API Key 等配置
```

### 2. 初始化数据库

```bash
# 运行迁移脚本
python migrate_db.py
```

### 3. 启动服务 (推荐)

使用 `scripts/dev.sh` 脚本一键启动所有服务（RabbitMQ + Workers + API）：

```bash
./scripts/dev.sh
```

> **提示**: 该脚本会自动检查端口、启动 RabbitMQ、启动 3 个异步 Worker 进程以及 FastAPI 服务。按 `Ctrl+C` 可一键停止所有进程。

### 4. 手动启动 (可选)

如果需要单独调试：

```bash
# 启动 RabbitMQ
brew services start rabbitmq

# 启动 API 服务
uvicorn src.infrastructure.main:app --reload --host 0.0.0.0 --port 8000

# 启动 Worker (新终端)
python scripts/part1_worker.py
python scripts/part2_worker.py
python scripts/interpretation_worker.py
```

## 📂 项目结构

```
backend/
├── src/
│   ├── adapters/           # 接口适配层
│   │   ├── controllers/    # API 路由 (Restful)
│   │   ├── gateways/       # 外部服务 (Qwen, OSS)
│   │   └── repositories/   # 数据库访问 (SQLAlchemy)
│   ├── use_cases/          # 应用业务逻辑 (Evaluation, Report)
│   ├── domain/             # 领域实体与接口定义
│   └── infrastructure/     # 基础设施 (Config, DB, Queue)
├── scripts/                # 运维脚本 (Workers, Migration)
├── database/               # SQL 迁移文件
└── tests/                  # 单元测试
```

## 📚 API 文档

启动服务后访问：
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
