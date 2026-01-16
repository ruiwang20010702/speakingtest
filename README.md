# AI 口语测评系统 (AI Speaking Test System)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

基于通义千问 (Qwen-Omni) 的全链路 AI 口语测评系统，支持单词朗读 (Part 1) 和开放式问答 (Part 2) 评测，自动生成多维度的学生能力画像与家长报告。

---

## 🌟 核心特性

- **多模态 AI 评测**
  - **Part 1 单词朗读**：基于 Qwen-Omni 音频理解，精准评分（准确度、流利度、发音、完整度）。
  - **Part 2 开放问答**：多轮对话评测，评估流利度、发音、自信度、词汇量及整句输出能力。
  
- **智能报告生成**
  - **家长端 H5**：自动生成五维雷达图、强弱项分析及个性化学习建议。
  - **教师端后台**：班级维度的数据看板，支持手动修正 AI 评分与评语。

- **高可用架构**
  - **异步处理**：基于 RabbitMQ 的任务队列设计，削峰填谷，保障高并发下的服务稳定性。
  - **前后端分离**：
    - 后端：Python FastAPI + PostgreSQL + RabbitMQ + Redis
    - 前端：Student H5 (学生端), Parent H5 (家长端), Teacher Web (教师端)

---

## 📂 项目结构

```
.
├── backend/                # 后端服务 (Python)
│   ├── src/                # 核心业务代码 (Clean Architecture)
│   │   ├── adapters/       # 接口适配层 (API Controllers, Gateways)
│   │   ├── use_cases/      # 应用业务逻辑 (Evaluation, Report)
│   │   └── infrastructure/ # 基础设施 (DB, Config, Logging)
│   ├── scripts/            # 运维与测试脚本 (Workers, Migration)
│   └── database/           # 数据库迁移文件
│
├── frontend/               # 前端应用
│   ├── student-h5/         # 学生端 H5 (答题入口)
│   ├── parent-h5/          # 家长端 H5 (报告查看)
│   └── teacher-web/        # 教师端 Web (管理后台)
│
├── deploy/                 # 部署相关
│   ├── scripts/            # 自动化部署脚本
│   └── README.md           # 部署文档
│
├── nginx/                  # Nginx 配置 (反向代理)
└── docs/                   # 项目文档 (架构图, API, 数据字典)
```

---

## 🚀 快速开始 (开发环境)

### 前置要求
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- RabbitMQ 3.9+
- Redis (可选，生产环境建议)

### 1. 启动后端

```bash
cd backend

# 创建并激活虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量 (参考 .env.example)
cp .env.example .env

# 初始化数据库
python migrate_db.py

# 启动开发环境 (包含 API 服务和 Workers)
./scripts/dev.sh
```

后端 API 文档地址: `http://localhost:8000/docs`

### 2. 启动前端

**学生端 H5**:
```bash
cd frontend/student-h5
npm install && npm run dev
# 访问: http://localhost:3001
```

**家长端 H5**:
```bash
cd frontend/parent-h5
npm install && npm run dev
# 访问: http://localhost:3000
```

**教师端 Web**:
```bash
cd frontend/teacher-web
npm install && npm run dev
# 访问: http://localhost:5173
```

---

## 📖 文档索引

- [架构与 API 设计](docs/architecture_and_api.md)
- [数据字段与评分标准](docs/数据字段对比文档.md)
- [部署指南](deploy/README.md)
- [Nginx 配置说明](nginx/README.md)

---

## 🛠️ 部署

本项目支持单机部署与集群部署，详情请参考 [部署指南](deploy/README.md)。

**生产环境架构：**
- **接入层**：阿里云 SLB + Nginx
- **应用层**：API Server 集群 + 异步 Worker 集群
- **数据层**：阿里云 RDS (PostgreSQL) + OSS (音频存储)
