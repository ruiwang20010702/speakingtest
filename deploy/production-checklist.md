# 🚀 生产环境部署检查清单

## 📋 部署前检查

### 1. 环境变量配置 (`.env`)

```bash
# ⚠️ 必须修改的配置
DEBUG=false
ENABLE_TEST_AUTH=false
ENABLE_TOKEN_REENTRY=false
JWT_SECRET_KEY=<使用 openssl rand -hex 32 生成>
COOKIE_SECURE=true

# ⚠️ 必须配置的域名
FRONTEND_STUDENT_URL=https://student.yourdomain.com
FRONTEND_PARENT_URL=https://parent.yourdomain.com
FRONTEND_TEACHER_URL=https://teacher.yourdomain.com
CORS_ORIGINS=https://student.yourdomain.com,https://parent.yourdomain.com,https://teacher.yourdomain.com

# ⚠️ 必须配置的 Cookie 域名（支持子域名共享）
COOKIE_DOMAIN=.yourdomain.com

# ⚠️ 必须配置的服务
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
RABBITMQ_URL=amqp://user:pass@host:5672/

# ⚠️ 必须配置的 API 密钥
QWEN_API_KEY=sk-xxx
OSS_ACCESS_KEY_ID=xxx
OSS_ACCESS_KEY_SECRET=xxx
OSS_ENDPOINT=https://oss-cn-xxx.aliyuncs.com
OSS_BUCKET_NAME=xxx

# 可选：讯飞 API（Part1 语音评测）
XUNFEI_APP_ID=xxx
XUNFEI_API_KEY=xxx
XUNFEI_API_SECRET=xxx

# 可选：邮件服务
SMTP_HOST=smtp.xxx.com
SMTP_USER=xxx
SMTP_PASSWORD=xxx
SMTP_FROM_EMAIL=xxx@xxx.com
```

### 2. 数据库初始化

```bash
# 首次部署需要执行数据库初始化脚本
psql -h <host> -U <user> -d <dbname> -f backend/database/init.sql

# 如有增量迁移
psql -h <host> -U <user> -d <dbname> -f backend/database/migrations/001_interpretation_pages.sql
psql -h <host> -U <user> -d <dbname> -f backend/database/migrations/002_interpretation_status.sql
```

### 3. 前端构建

```bash
# Student H5
cd frontend/student-h5
npm install
npm run build

# Parent H5
cd frontend/parent-h5
npm install
npm run build

# Teacher Web
cd frontend/teacher-web
npm install
npm run build
```

### 4. 后端部署

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 使用 gunicorn + uvicorn workers 运行
gunicorn src.infrastructure.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/speakingtest/access.log \
    --error-logfile /var/log/speakingtest/error.log \
    --daemon
```

### 5. Nginx 配置

```bash
# 复制配置文件
sudo cp deploy/nginx.conf /etc/nginx/sites-available/speakingtest.conf

# 修改域名和 SSL 证书路径
sudo nano /etc/nginx/sites-available/speakingtest.conf

# 启用站点
sudo ln -s /etc/nginx/sites-available/speakingtest.conf /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载配置
sudo systemctl reload nginx
```

### 6. SSL 证书

```bash
# 使用 Let's Encrypt 获取免费证书
sudo certbot --nginx -d student.yourdomain.com -d parent.yourdomain.com -d teacher.yourdomain.com
```

---

## ✅ 部署后验证

### 1. 健康检查

```bash
# 基础健康检查
curl https://student.yourdomain.com/api/v1/health

# 详细健康检查（包含依赖状态）
curl https://student.yourdomain.com/api/v1/health/detailed
```

### 2. 功能验证

- [ ] 教师登录（验证码发送、Cookie 设置）
- [ ] 学生入口（Token 验证、Cookie 设置）
- [ ] Part1 录音上传和评测
- [ ] Part2 录音上传和评测
- [ ] 报告生成和分享
- [ ] 家长端报告查看

### 3. 安全验证

```bash
# 检查 Cookie 设置
curl -I https://teacher.yourdomain.com/api/v1/auth/login
# 应该看到 Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Lax

# 检查 CORS 头
curl -I -H "Origin: https://teacher.yourdomain.com" https://teacher.yourdomain.com/api/v1/health
# 应该看到 Access-Control-Allow-Origin: https://teacher.yourdomain.com

# 检查安全头
curl -I https://teacher.yourdomain.com
# 应该看到 X-Frame-Options, X-Content-Type-Options 等
```

---

## 🔧 常见问题

### 1. Cookie 不生效

- 检查 `COOKIE_SECURE=true`（HTTPS 必须）
- 检查 `COOKIE_DOMAIN` 是否正确设置
- 检查前端请求是否带 `withCredentials: true`

### 2. CORS 错误

- 检查 `CORS_ORIGINS` 是否包含前端域名
- 确保域名包含协议（`https://`）
- 检查是否有尾随斜杠问题

### 3. 401 错误

- 检查 Cookie 是否被浏览器阻止
- 检查 JWT 密钥是否一致
- 检查 Token 是否过期

### 4. Redis 连接失败

- 系统会自动 fallback 到内存限流
- 查看日志确认：`Redis unavailable for rate limiting, using in-memory fallback`
- 生产环境建议配置 Redis 以支持多实例

---

## 📊 监控建议

### 日志

- 应用日志：`/var/log/speakingtest/`
- Nginx 日志：`/var/log/nginx/`

### 指标

- API 响应时间
- 错误率
- 并发连接数
- 数据库连接池使用率

### 告警

- 健康检查失败
- 错误率 > 1%
- 响应时间 > 3s
- 磁盘空间 < 20%
