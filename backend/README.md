# AI 口语测评系统 - 后端服务 (Backend)

基于 **FastAPI + RabbitMQ + Qwen-Omni** 构建的高性能 AI 口语测评后端。采用 **Clean Architecture (整洁架构)** 设计，确保业务逻辑与外部依赖（AI、数据库、存储）的深度解耦。

---

## 🌟 核心功能

- **多模态 AI 评测**：
  - **Part 1 (Word Reading)**：基于 `qwen3-omni-flash` 的单词/短语朗读 4 维度评分。
  - **Part 2 (Dialogue)**：12 题连续问答评测，支持语义理解、语法纠错及流利度评估。
- **异步任务架构**：基于 RabbitMQ 实现任务削峰填谷，支持长耗时 AI 推理任务的稳定执行。
- **智能报告生成**：
  - 自动融合 Part 1 & 2 数据，生成五维能力雷达图。
  - 利用 `qwen-plus` 结构化输出生成家长建议与教师解读演讲稿。
- **精细化成本追踪**：实时记录每一笔 AI 调用的 Token 消耗，并根据模型单价换算为 RMB 成本。
- **运维与管理**：支持失败任务重试、审计日志追踪、题库动态管理。

---

## 🛠️ 技术栈

- **语言**: Python 3.11+
- **框架**: FastAPI (全异步)
- **数据库**: PostgreSQL (SQLAlchemy + AsyncPG)
- **任务队列**: RabbitMQ (aio-pika)
- **缓存/限流**: Redis
- **对象存储**: 阿里云 OSS
- **AI 模型**: Qwen-Omni (音频评测), Qwen-Plus (文本分析)

---

## 📂 项目结构 (Clean Architecture)

```text
src/
├── domain/                 # [核心层] 领域实体与业务规则 (纯 Python)
│   ├── entities/           # 核心业务对象 (Student, Test, Score)
│   └── ports/              # 抽象接口 (Repository, AI Gateway)
│
├── use_cases/              # [应用层] 业务用例编排
│   ├── evaluate_part1.py   # Part 1 评测逻辑
│   ├── evaluate_part2.py   # Part 2 异步评测逻辑
│   └── interpretation.py   # 报告解读生成逻辑
│
├── adapters/               # [适配器层] 外部依赖实现
│   ├── controllers/        # FastAPI 路由 (Admin, Student, Report)
│   ├── gateways/       # 外部服务网关 (QwenClient, OSSClient)
│   └── repositories/       # 数据库实现 (SQLAlchemy Models)
│
└── infrastructure/         # [基础设施层] 框架与配置
    ├── main.py             # App 入口
    ├── database.py         # 数据库连接池
    └── queue_service.py    # RabbitMQ 生产者/消费者封装
```

---

## 🚀 快速启动

### 1. 环境准备
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填入 API Keys 和数据库配置
```

### 2. 初始化数据库
```bash
python migrate_db.py
```

### 3. 一键启动 (API + 3 Workers)
```bash
./scripts/dev.sh
```

---

## ⚙️ Worker 职责说明

系统包含三个核心异步 Worker，通过 RabbitMQ 协同工作：

1.  **`part1_worker.py`**：处理单词朗读评测，调用 Qwen-Omni 音频接口。
2.  **`part2_worker.py`**：处理 12 题对话评测，生成转写、评分及家长端汇总分析。
3.  **`interpretation_worker.py`**：为教师生成报告解读演讲稿（约 10 分钟长度）。

---

## 📚 API 调试

启动服务后，可通过以下地址查看交互式文档：
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 🛡️ 安全与审计
- **鉴权**：基于 JWT 的教师/管理员认证。
- **审计**：所有敏感操作（Token 生成、报告重置、配置变更）均记录至 `audit_logs` 表。
- **限流**：基于 Redis 实现的接口频率限制，保护 AI 接口配额。
