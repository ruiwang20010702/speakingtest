# Gaea Deployment

基于 Debian 11 + s6-overlay 的单容器多服务部署方案。

## 架构

单个 Docker 容器内运行以下服务（由 s6-overlay 管理）：

```
┌─────────────────────────────────────────────┐
│                Container                     │
│  ┌─────────────────────────────────────────┐│
│  │          Nginx (Port 80)                ││
│  │  ┌─────────┬─────────┬─────────────────┐││
│  │  │/s/*     │/p/*     │/ (default)      │││
│  │  │Student  │Parent   │Teacher          │││
│  │  │H5       │H5       │Web              │││
│  │  └─────────┴─────────┴─────────────────┘││
│  │            ↓ /api/*                     ││
│  │  ┌─────────────────────────────────────┐││
│  │  │    FastAPI (Port 8000)              │││
│  │  └─────────────────────────────────────┘││
│  └─────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────┐│
│  │            Workers (s6 services)        ││
│  │  • part1-worker                         ││
│  │  • part2-worker                         ││
│  │  • interpretation-worker                ││
│  │  • dlq-worker                           ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
         ↓              ↓              ↓
    PostgreSQL      RabbitMQ        Redis
```

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

## 生产环境部署

### 环境变量配置

必须配置以下环境变量：

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `JWT_SECRET_KEY` | JWT 签名密钥（至少32字符） | `your-secure-random-string` |
| `QWEN_API_KEY` | 通义千问 API Key | `sk-xxxxx` |
| `OSS_ACCESS_KEY_ID` | 阿里云 OSS Access Key | `LTAI5t...` |
| `OSS_ACCESS_KEY_SECRET` | 阿里云 OSS Secret | `xxxxx` |
| `OSS_ENDPOINT` | OSS 端点 | `oss-cn-hangzhou.aliyuncs.com` |
| `OSS_BUCKET_NAME` | OSS Bucket 名称 | `my-bucket` |

### 安全配置

```bash
# 生产环境必须设置
DEBUG=false
COOKIE_SECURE=true
CORS_ORIGINS=https://your-domain.com
```

### 单独运行容器

```bash
docker run -d \
  --name speaking-test \
  -p 80:80 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/speakingtest \
  -e REDIS_URL=redis://redis-host:6379/0 \
  -e RABBITMQ_URL=amqp://user:pass@rabbitmq-host:5672/ \
  -e JWT_SECRET_KEY=your-secret-key \
  -e QWEN_API_KEY=your-qwen-key \
  -e OSS_ACCESS_KEY_ID=xxx \
  -e OSS_ACCESS_KEY_SECRET=xxx \
  -e OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com \
  -e OSS_BUCKET_NAME=your-bucket \
  speaking-test:latest
```

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
