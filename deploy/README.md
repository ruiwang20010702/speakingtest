# 阿里云部署指南

## 架构概览

```text
┌─────────────────────┐     ┌─────────────────────────────┐
│  ECS 1 - 前端服务器  │     │    ECS 2 - 后端服务器        │
│  (2C4G, CentOS/Ubuntu)│    │    (4C8G, CentOS/Ubuntu)    │
├─────────────────────┤     ├─────────────────────────────┤
│  Nginx              │     │  后端 API (uvicorn)         │
│  ├── 学生端 /s/     │────▶│  Part1 Worker               │
│  ├── 家长端 /p/     │     │  Part2 Worker               │
│  └── 老师端 /t/     │     │  Interpretation Worker      │
│                     │     │  DLQ Worker (死信队列)       │
│                     │     │  RabbitMQ (自建/云托管)      │
└─────────────────────┘     └──────────────┬──────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              ▼                            ▼                            ▼
     ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
     │  阿里云 RDS      │         │   阿里云 OSS    │         │  外部 AI 服务   │
     │  PostgreSQL     │         │   (音频存储)    │         │  通义千问 Qwen  │
     └─────────────────┘         └─────────────────┘         └─────────────────┘
```

## 资源清单

| 资源 | 规格 | 预估费用 (月) | 说明 |
|------|------|--------------|------|
| ECS 1 (前端) | 2C4G | ¥100-150 | 静态文件 + Nginx |
| ECS 2 (后端) | 4C8G | ¥300-400 | API + 4个 Workers + RabbitMQ + Redis |
| RDS PostgreSQL | 2C4G 高可用版 | ¥200-300 | 数据库 |
| OSS | 按量付费 | ¥20-50 | 音频存储 |
| 带宽 | 按量/包月 | ¥50-100 | 公网带宽 |
| **总计** | | **¥670-1000** | |

## 部署步骤

### 1. 创建阿里云资源

#### 1.1 创建 VPC 和安全组
- **前端服务器安全组**: 开放 80/443 (HTTP/HTTPS)。
- **后端服务器安全组**: 开放 8000 (API) 给前端内网，5672 (RabbitMQ) 仅限内网。

#### 1.2 创建实例
- **RDS**: PostgreSQL 17，高可用版。
- **OSS**: 私有 Bucket，开启跨域配置（允许前端直传）。

---

### 2. 部署后端服务器

1.  **安装依赖**:
    ```bash
    sudo apt update && sudo apt install -y python3.11 python3.11-venv rabbitmq-server redis-server
    ```
2.  **配置服务**:
    - 使用 `systemd` 管理 `speakingtest-api` 和 4 个 Worker 进程。
    - 配置文件路径: `/etc/systemd/system/speakingtest-*.service`

---

### 3. 环境变量配置 (.env)

```bash
# ========== 安全配置（必须修改） ==========
DEBUG=false
ENABLE_TEST_AUTH=false
ENABLE_TOKEN_REENTRY=false
JWT_SECRET_KEY=<使用 openssl rand -hex 32 生成>

# Cookie 安全（httpOnly Cookie 认证）
COOKIE_NAME=access_token
COOKIE_DOMAIN=.your-domain.com
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
COOKIE_PATH=/api

# CORS（必须显式配置）
CORS_ORIGINS=https://student.your-domain.com,https://parent.your-domain.com,https://teacher.your-domain.com

# ========== 数据库与队列 ==========
DATABASE_URL=postgresql+asyncpg://user:pass@rm-xxx.pg.rds.aliyuncs.com:5432/speakingtest
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
REDIS_URL=redis://localhost:6379/0

# ========== AI 配置 (通义千问) ==========
QWEN_API_KEY=sk-xxxx

# ========== 阿里云 OSS ==========
OSS_ACCESS_KEY_ID=LTAIxxxx
OSS_ACCESS_KEY_SECRET=xxxx
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=speaking-test-audio

# ========== 前端 URL (用于生成分享链接) ==========
FRONTEND_STUDENT_URL=https://student.your-domain.com/s
FRONTEND_PARENT_URL=https://parent.your-domain.com
FRONTEND_TEACHER_URL=https://teacher.your-domain.com
```

---

### 4. 运维常用命令

```bash
# 查看所有服务状态
sudo systemctl status "speakingtest-*"

# 重启所有 Worker
sudo systemctl restart speakingtest-worker-part1
sudo systemctl restart speakingtest-worker-part2
sudo systemctl restart speakingtest-worker-interp
sudo systemctl restart speakingtest-worker-dlq

# 查看 AI 处理日志
sudo journalctl -u speakingtest-worker-part2 -f
```

---

## 🛡️ 生产环境安全清单

### 必须配置
- [ ] **JWT 密钥**: 使用 `openssl rand -hex 32` 生成强密钥
- [ ] **Cookie 安全**: `COOKIE_SECURE=true` + `COOKIE_DOMAIN=.your-domain.com`
- [ ] **CORS**: 显式配置 `CORS_ORIGINS`（不能为空）
- [ ] **禁用测试模式**: `ENABLE_TEST_AUTH=false` + `ENABLE_TOKEN_REENTRY=false`
- [ ] **HTTPS**: 所有端配置 SSL 证书（推荐 Certbot）

### 网络安全
- [ ] **数据库白名单**: RDS 仅允许后端 ECS 内网 IP 访问
- [ ] **Redis 白名单**: 仅允许内网访问
- [ ] **RabbitMQ**: 修改默认 guest 账号密码

### 验证命令
```bash
# 检查 Cookie 设置
curl -I https://teacher.your-domain.com/api/v1/auth/login
# 应看到: Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Lax

# 检查 CORS
curl -I -H "Origin: https://teacher.your-domain.com" https://teacher.your-domain.com/api/v1/health
# 应看到: Access-Control-Allow-Origin: https://teacher.your-domain.com
```

详细部署清单请参考 [production-checklist.md](./production-checklist.md)
