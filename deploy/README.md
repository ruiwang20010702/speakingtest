# 阿里云部署指南

## 架构概览

```
┌─────────────────────┐     ┌─────────────────────────────┐
│  ECS 1 - 前端服务器  │     │    ECS 2 - 后端服务器        │
│  (2C4G, CentOS/Ubuntu)│    │    (4C8G, CentOS/Ubuntu)    │
├─────────────────────┤     ├─────────────────────────────┤
│  Nginx              │     │  后端 API (uvicorn)         │
│  ├── 学生端 /s/     │────▶│  Part1 Worker               │
│  ├── 家长端 /p/     │     │  Part2 Worker               │
│  └── 老师端 /t/     │     │  Interpretation Worker      │
│                     │     │  RabbitMQ (自建)            │
└─────────────────────┘     └──────────────┬──────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              ▼                            ▼                            ▼
     ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
     │  阿里云 RDS      │         │   阿里云 OSS    │         │  外部 API       │
     │  PostgreSQL     │         │   (音频存储)    │         │  讯飞/通义千问  │
     └─────────────────┘         └─────────────────┘         └─────────────────┘
```

## 资源清单

| 资源 | 规格 | 预估费用 (月) | 说明 |
|------|------|--------------|------|
| ECS 1 (前端) | 2C4G | ¥100-150 | 静态文件 + Nginx |
| ECS 2 (后端) | 4C8G | ¥300-400 | API + Workers + RabbitMQ |
| RDS PostgreSQL | 2C4G 高可用版 | ¥200-300 | 数据库 |
| OSS | 按量付费 | ¥20-50 | 音频存储 |
| 带宽 | 按量/包月 | ¥50-100 | 公网带宽 |
| **总计** | | **¥670-1000** | |

## 部署步骤

### 1. 创建阿里云资源

#### 1.1 创建 VPC 和安全组

```bash
# 在阿里云控制台创建:
# 1. VPC (专有网络)
# 2. 交换机 (子网)
# 3. 安全组，开放以下端口:

# 前端服务器安全组:
- 80/443 (HTTP/HTTPS) - 0.0.0.0/0
- 22 (SSH) - 你的 IP

# 后端服务器安全组:
- 8000 (API) - 前端服务器内网 IP 或安全组
- 5672 (RabbitMQ) - 仅内网
- 22 (SSH) - 你的 IP
```

#### 1.2 创建 ECS 实例

| 实例 | 规格 | 系统 | 用途 |
|------|------|------|------|
| frontend-server | ecs.c6.large (2C4G) | Ubuntu 22.04 | 前端 |
| backend-server | ecs.c6.xlarge (4C8G) | Ubuntu 22.04 | 后端 |

#### 1.3 创建 RDS PostgreSQL

- 规格: 2C4G 高可用版
- 版本: PostgreSQL 14+
- 存储: 50GB SSD (可扩容)
- 网络: 与 ECS 同一 VPC

#### 1.4 创建 OSS Bucket

- 地域: 与 ECS 同一地域
- 权限: 私有
- 存储类型: 标准存储

---

### 2. 部署后端服务器

SSH 登录后端服务器，执行以下脚本:

```bash
# 下载部署脚本
curl -O https://raw.githubusercontent.com/your-repo/deploy/backend-setup.sh
chmod +x backend-setup.sh
./backend-setup.sh
```

或者手动执行 `deploy/scripts/backend-setup.sh` 中的步骤。

---

### 3. 部署前端服务器

SSH 登录前端服务器:

```bash
# 下载部署脚本
curl -O https://raw.githubusercontent.com/your-repo/deploy/frontend-setup.sh
chmod +x frontend-setup.sh
./frontend-setup.sh
```

---

### 4. 配置域名和 HTTPS

#### 4.1 域名解析

在阿里云 DNS 控制台添加解析:

| 主机记录 | 类型 | 记录值 |
|----------|------|--------|
| student | A | 前端 ECS 公网 IP |
| parent | A | 前端 ECS 公网 IP |
| teacher | A | 前端 ECS 公网 IP |
| api | A | 后端 ECS 公网 IP (可选) |

#### 4.2 申请 SSL 证书

```bash
# 在前端服务器安装 certbot
apt install certbot python3-certbot-nginx -y

# 申请证书
certbot --nginx -d student.your-domain.com -d parent.your-domain.com -d teacher.your-domain.com

# 自动续期
certbot renew --dry-run
```

---

## 环境变量配置

后端服务器 `/opt/speakingtest/.env`:

```bash
# 应用
APP_NAME="Speaking Test System"
DEBUG=false

# 数据库 (替换为 RDS 内网地址)
DATABASE_URL=postgresql+asyncpg://user:password@rm-xxx.pg.rds.aliyuncs.com:5432/speakingtest

# RabbitMQ (本地)
RABBITMQ_URL=amqp://speakingtest:your-password@localhost:5672/

# JWT (生成随机密钥)
JWT_SECRET_KEY=your-random-secret-key-here

# 讯飞 API
XUNFEI_APP_ID=xxx
XUNFEI_API_KEY=xxx
XUNFEI_API_SECRET=xxx

# 通义千问 API
QWEN_API_KEY=xxx

# 阿里云 OSS
OSS_ACCESS_KEY_ID=xxx
OSS_ACCESS_KEY_SECRET=xxx
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=your-bucket-name

# 前端 URL (用于生成链接)
FRONTEND_STUDENT_URL=https://student.your-domain.com/s
FRONTEND_PARENT_URL=https://parent.your-domain.com
FRONTEND_TEACHER_URL=https://teacher.your-domain.com

# CORS
CORS_ORIGINS=https://student.your-domain.com,https://parent.your-domain.com,https://teacher.your-domain.com
```

---

## 运维命令

### 服务管理

```bash
# 后端服务器
sudo systemctl status speakingtest-api
sudo systemctl status speakingtest-worker-part1
sudo systemctl status speakingtest-worker-part2
sudo systemctl status speakingtest-worker-interp
sudo systemctl status rabbitmq-server

# 重启所有服务
sudo systemctl restart speakingtest-api
sudo systemctl restart speakingtest-worker-part1
sudo systemctl restart speakingtest-worker-part2
sudo systemctl restart speakingtest-worker-interp

# 查看日志
sudo journalctl -u speakingtest-api -f
sudo journalctl -u speakingtest-worker-part1 -f
```

### 更新部署

```bash
# 后端更新
cd /opt/speakingtest
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart speakingtest-api
sudo systemctl restart speakingtest-worker-part1
sudo systemctl restart speakingtest-worker-part2
sudo systemctl restart speakingtest-worker-interp

# 前端更新 (本地构建后上传)
scp -r frontend/student-h5/dist/* root@frontend-server:/var/www/speakingtest/student-h5/
scp -r frontend/parent-h5/dist/* root@frontend-server:/var/www/speakingtest/parent-h5/
scp -r frontend/teacher-web/dist/* root@frontend-server:/var/www/speakingtest/teacher-web/
```

### 健康检查

```bash
# API 健康检查
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed

# RabbitMQ 状态
sudo rabbitmqctl status
sudo rabbitmqctl list_queues
```

---

## 故障排查

### 常见问题

1. **API 无法连接数据库**
   - 检查 RDS 白名单是否添加后端 ECS IP
   - 检查 DATABASE_URL 是否正确

2. **RabbitMQ 连接失败**
   - `sudo systemctl status rabbitmq-server`
   - `sudo rabbitmqctl list_users`

3. **前端无法访问 API**
   - 检查后端安全组是否开放 8000 端口给前端
   - 检查 CORS 配置

4. **Worker 不消费消息**
   - `sudo journalctl -u speakingtest-worker-part1 -f`
   - 检查 RabbitMQ 队列状态
