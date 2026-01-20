# AI 口语测评系统 (AI Speaking Test System)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-6-646CFF.svg)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-4-38B2AC.svg)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

基于 **通义千问 (Qwen-Omni)** 全链路驱动的 AI 口语测评系统。系统涵盖了从学生端录音测评、AI 自动化评分、家长端深度报告展示到教师端管理后台的全流程闭环。

---

## 🌟 核心特性

### 1. 多模态 AI 评测引擎
- **Part 1 核心词汇**：基于 `qwen3-omni-flash` 的音频理解能力，对单词/短语朗读进行 4 维度评分（准确度、流利度、发音、完整度），支持逐词纠错。
- **Part 2 对话问答**：模拟真实教学场景的 12 题连续问答，评估流利度、发音、自信度、词汇量及整句输出能力。
- **异步处理架构**：基于 RabbitMQ 的任务队列，确保高并发下的评测稳定性，支持任务重试与状态追踪。

### 2. 智能报告与深度解读
- **五维能力图谱**：自动生成学生口语能力的雷达图，包含 AI 生成的个性化维度评语。
- **AI 汇总分析**：利用 `qwen-plus` 深度分析测评数据，自动提炼学习亮点、短板，并制定本周练习计划。
- **班主任解读助手**：为教师自动生成针对单一学生的 10 分钟报告解读演讲稿，支持 6 页报告的深度拆解。

### 3. 专业级管理后台 (Admin Dashboard)
- **数据看板**：实时监控学生总数、测评总数、分享率及家长打开率。
- **转化漏斗分析**：从扫码进入到完成测评、老师分享、家长查看的全链路转化追踪。
- **成本监控**：基于 Token 消耗实时计算每一笔 AI 调用的真实成本（RMB），支持按教师、按项目统计。
- **运维工具**：审计日志追踪、失败任务一键重试、题库动态管理。

---

## 📂 项目结构

```text
.
├── backend/                # 后端服务 (Python/FastAPI)
│   ├── src/                # 核心业务逻辑 (Clean Architecture)
│   │   ├── domain/         # 领域实体与接口定义
│   │   ├── use_cases/      # 业务用例 (评测逻辑、报告生成)
│   │   ├── adapters/       # 适配器 (API 控制器、Qwen/OSS 网关)
│   │   └── infrastructure/ # 基础设施 (数据库、队列、配置)
│   ├── scripts/            # 运维脚本 (Worker 进程、数据库迁移)
│   └── tests/              # 自动化测试套件
│
├── frontend/               # 前端应用 (React/Vite/Tailwind)
│   ├── student-h5/         # 学生端：游戏化答题界面 (Port: 3001)
│   ├── parent-h5/          # 家长端：深度测评报告 (Port: 3000)
│   └── teacher-web/        # 教师端：管理后台与数据看板 (Port: 5173)
│
├── deploy/                 # 部署配置 (Docker/Nginx)
├── docs/                   # 项目文档 (PRD、API 设计、数据字典)
└── nginx/                  # Nginx 反向代理配置
```

---

## 🚀 快速开始

### 1. 环境准备
- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL 15+**
- **RabbitMQ 3.9+**
- **Redis** (用于限流)

### 2. 后端启动
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # 填入 Qwen API Key, OSS, DB 等配置
python migrate_db.py  # 初始化数据库

# 一键启动所有服务 (API + 3个 Workers)
./scripts/dev.sh
```

### 3. 前端启动
```bash
# 学生端
cd frontend/student-h5 && npm install && npm run dev
# 家长端
cd frontend/parent-h5 && npm install && npm run dev
# 教师端
cd frontend/teacher-web && npm install && npm run dev
```

---

## 🛠️ 技术栈

| 领域 | 技术选型 |
| :--- | :--- |
| **后端框架** | FastAPI (异步) |
| **AI 模型** | Qwen3-Omni-flash (音频), Qwen-Plus (文本) |
| **数据库** | PostgreSQL (SQLAlchemy + AsyncPG) |
| **任务队列** | RabbitMQ (aio-pika) |
| **缓存/限流** | Redis |
| **对象存储** | 阿里云 OSS |
| **前端框架** | React 19 + Vite 6 |
| **样式方案** | Tailwind CSS 4 |
| **状态管理** | Zustand |
| **数据可视化** | Recharts |

---

## 📖 文档索引

- [产品需求文档 (PRD)](docs/PRD_口语测评系统.md)
- [架构与 API 设计](docs/architecture_and_api.md)
- [数据字段对比文档](docs/数据字段对比文档.md)
- [部署指南](deploy/README.md)

---

## 🛡️ 授权说明
本项目为企业内部系统，采用 Proprietary License 授权。
