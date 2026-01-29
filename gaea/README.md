# Gaea Deployment

基于 Debian 11 + s6-overlay 的单容器多服务部署方案。

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端 (React + Vite)                             │
├──────────────────┬───────────────────┬──────────────────────────────────────┤
│   Student H5     │    Parent H5      │         Teacher Web                  │
│   /s/*           │    /p/*           │         / (默认)                     │
│                  │                   │                                      │
│  • 学生测评入口   │  • 家长查看报告    │  • 教师登录/管理                      │
│  • 音频录制上传   │  • 分享链接访问    │  • 学生管理                          │
│  • Part1 朗读    │  • 无需登录        │  • 测评记录查看                       │
│  • Part2 问答    │                   │  • 报告编辑/分享                      │
└────────┬─────────┴─────────┬─────────┴──────────────────┬───────────────────┘
         │                   │                            │
         └───────────────────┼────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Nginx (反向代理 + 静态文件)                          │
│   /api/* → FastAPI:8000    |    /s/* /p/* / → 静态文件                      │
└─────────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FastAPI 后端 (API Server)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Controllers (路由层)                                                        │
│  ├── teacher_auth    → 教师登录 (邮箱验证码)                                  │
│  ├── student         → 学生入口 (Token 验证)                                 │
│  ├── upload          → 音频上传 → OSS                                        │
│  ├── test            → 测评管理 (创建/状态查询)                               │
│  ├── report          → 报告查看/编辑/分享                                    │
│  └── admin           → 管理员功能 (重试失败任务等)                            │
└──────────────┬──────────────────────────────────────┬───────────────────────┘
               │                                      │
               ▼                                      ▼
┌──────────────────────────┐          ┌───────────────────────────────────────┐
│      PostgreSQL          │          │           RabbitMQ                    │
│  (主数据存储)             │          │        (消息队列)                      │
├──────────────────────────┤          ├───────────────────────────────────────┤
│ • users (教师/学生)       │          │ • part1_evaluation_tasks              │
│ • student_profiles       │          │ • part2_evaluation_tasks              │
│ • tests (测评记录)        │          │ • interpretation_tasks                │
│ • test_items (Part2题目) │          │ • *_dlq (死信队列)                     │
│ • questions (题库)       │          └──────────────┬────────────────────────┘
│ • share_tokens          │                         │
└──────────────────────────┘                        ▼
                                    ┌───────────────────────────────────────┐
               ┌────────────────────┤          Workers (消费者)              │
               │                    ├───────────────────────────────────────┤
               │                    │ • part1_worker   → Part1 评测          │
               │                    │ • part2_worker   → Part2 评测          │
               │                    │ • interpretation → 报告解读生成        │
               │                    │ • dlq_worker     → 失败任务处理        │
               │                    └──────────────┬────────────────────────┘
               │                                   │
               ▼                                   ▼
┌──────────────────────────┐          ┌───────────────────────────────────────┐
│      阿里云 OSS           │          │          通义千问 API                  │
│   (音频文件存储)          │          │        (AI 评测引擎)                   │
├──────────────────────────┤          ├───────────────────────────────────────┤
│ • 学生录音上传            │ ◄─────── │ • qwen3-omni-flash (音频评测)          │
│ • Worker 下载评测         │          │ • qwen-plus (文本分析/报告解读)        │
└──────────────────────────┘          └───────────────────────────────────────┘

┌──────────────────────────┐
│        Redis             │
│    (可选 - 限流)          │
├──────────────────────────┤
│ • API 请求限流            │
│ • 多实例分布式限流        │
│ • 无则降级为内存限流      │
└──────────────────────────┘
```

---

## 核心流程

### 学生测评流程

```
教师创建测评链接 → 学生打开链接 → 录制 Part1 音频 → 上传 OSS
→ 入队 part1_evaluation_tasks → Worker 评测 → 录制 Part2 音频
→ 上传 OSS → 入队 part2_evaluation_tasks → Worker 评测
→ 生成报告 → 入队 interpretation_tasks → 生成 AI 解读
```

---

## 组件说明

### 必须组件

| 组件 | 用途 | 配置项 |
|------|------|--------|
| **PostgreSQL** | 存储用户、测评记录、题库等所有业务数据 | `DATABASE_URL` |
| **RabbitMQ** | 异步任务队列，解耦 API 和 AI 评测 | `RABBITMQ_URL` |
| **阿里云 OSS** | 存储学生录音文件 | `OSS_*` |
| **通义千问 API** | AI 评测核心，音频分析和文本生成 | `QWEN_API_KEY` |

### 可选组件

| 组件 | 用途 | 配置项 | 降级方案 |
|------|------|--------|----------|
| **Redis** | API 限流（多实例共享） | `REDIS_URL` | 自动降级为内存限流 |
| **SMTP** | 发送验证码邮件 | `SMTP_*` | 可用测试验证码 `888888` |

---

## Worker 职责

| Worker | 队列 | 功能 | AI 模型 |
|--------|------|------|---------|
| `part1_worker` | `part1_evaluation_tasks` | 评测 Part1 朗读（单词/短语发音） | qwen3-omni-flash |
| `part2_worker` | `part2_evaluation_tasks` | 评测 Part2 问答（12道对话题） | qwen3-omni-flash |
| `interpretation_worker` | `interpretation_tasks` | 生成 AI 报告解读（家长话术） | qwen-plus |
| `dlq_worker` | `*_dlq` | 处理失败任务，标记测评状态为 failed | - |

### 队列重试机制

- 最大重试次数：3 次
- 超过重试次数：进入死信队列 (DLQ)
- DLQ Worker：自动标记测评为 `failed` 状态
- 管理员可手动重试失败任务（额外 2 次）

---

## 前端路由

| 路径 | 应用 | 说明 |
|------|------|------|
| `/` | Teacher Web | 教师管理后台（默认） |
| `/s/{token}` | Student H5 | 学生测评入口 |
| `/p/{token}` | Parent H5 | 家长报告查看 |

---

## 快速开始

### 1. 配置环境变量

```bash
cp gaea/.env.example gaea/.env
# 编辑 .env 文件，填入必要的 API Key 和密钥
```

### 2. 构建镜像

```bash
# 在项目根目录执行
docker build -f gaea/Dockerfile -t speaking-test:latest .
```

### 3. 启动服务（开发环境）

```bash
cd gaea
docker-compose up -d
```

### 4. 访问服务

- 教师端: http://localhost/
- 学生端: http://localhost/s/
- 家长端: http://localhost/p/
- API 文档: http://localhost/docs
- 健康检查: http://localhost/health

---

## 环境变量配置

### 必须配置

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname

# 消息队列
RABBITMQ_URL=amqp://user:pass@host:5672/

# 阿里云 OSS
OSS_ACCESS_KEY_ID=xxx
OSS_ACCESS_KEY_SECRET=xxx
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=ai-speak-audio

# 通义千问
QWEN_API_KEY=sk-xxx

# JWT 密钥 (生产环境必须修改)
JWT_SECRET_KEY=your-secure-random-string

# 前端 URL
FRONTEND_STUDENT_URL=https://your-domain/s
FRONTEND_PARENT_URL=https://your-domain/p
FRONTEND_TEACHER_URL=https://your-domain

# CORS
CORS_ORIGINS=https://your-domain
```

### 可选配置

```bash
# API 进程数（默认 2）
API_WORKERS=2

# Redis (不配置则使用内存限流)
REDIS_URL=redis://host:6379/0

# SMTP 邮件
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=xxx
SMTP_PASSWORD=xxx
SMTP_FROM_EMAIL=noreply@example.com

# 管理员邮箱
ADMIN_EMAILS=admin@example.com

# 调试模式
DEBUG=false
```

---

## 目录结构

```
gaea/
├── Dockerfile              # 多阶段构建 Dockerfile
├── docker-compose.yml      # 开发环境编排
├── .env.example            # 环境变量示例
├── nginx/
│   ├── nginx.conf          # Nginx 主配置
│   └── default.conf        # 虚拟主机配置
├── s6-rc.d/                # s6-overlay 服务定义
│   ├── api/                # FastAPI 服务
│   ├── part1-worker/       # Part1 评测 Worker
│   ├── part2-worker/       # Part2 评测 Worker
│   ├── interpretation-worker/  # 报告解读 Worker
│   ├── dlq-worker/         # 死信队列 Worker
│   ├── nginx/              # Nginx 服务
│   └── user/contents.d/    # 启动服务列表
└── scripts/                # 辅助脚本
    ├── start-api.sh
    ├── start-worker.sh
    └── healthcheck.sh
```

---

## 服务管理

容器内使用 s6-overlay 管理服务，服务会自动重启。

```bash
# 查看服务状态
docker exec speaking-test s6-rc -a list

# 重启单个服务
docker exec speaking-test s6-svc -r /run/service/api

# 查看服务日志
docker logs speaking-test
```

---

## 故障排除

### 容器启动失败

```bash
# 查看启动日志
docker logs speaking-test

# 进入容器调试
docker run -it --entrypoint /bin/bash speaking-test:latest
```

### 服务健康检查失败

```bash
# 手动检查 API
docker exec speaking-test curl -f http://localhost:8000/health

# 检查 Nginx
docker exec speaking-test curl -f http://localhost/health
```
