# 🐛 生产环境问题排查手册

本文档总结了在生产环境部署和运行过程中可能遇到的常见问题及解决方案。

---

## 🔐 认证与授权问题

### 1. Cookie 无法设置或读取

**症状**：
- 登录后立即返回 401 未授权
- 浏览器 DevTools 中看不到 `access_token` Cookie
- 前端请求总是提示未登录

**可能原因**：
1. `COOKIE_SECURE=true` 但使用了 HTTP（非 HTTPS）
2. `COOKIE_DOMAIN` 配置错误（如 `.example.com` 但实际域名是 `student.example.com`）
3. Nginx 未正确传递 Cookie（缺少 `proxy_pass_header Set-Cookie`）
4. 前端未设置 `withCredentials: true`

**解决方案**：
```bash
# 1. 检查环境变量
grep COOKIE backend/.env
# 应看到：
# COOKIE_SECURE=true  # HTTPS 必须为 true
# COOKIE_DOMAIN=.your-domain.com  # 主域名，支持子域名

# 2. 检查 Nginx 配置
grep -A5 "location /api/" nginx/prod.conf
# 应包含：
# proxy_pass_header Set-Cookie;
# proxy_cookie_path / /;

# 3. 检查前端代码
grep "withCredentials" frontend/*/src/**/*.ts
# 应看到：withCredentials: true

# 4. 验证 Cookie 设置
curl -I https://teacher.your-domain.com/api/v1/auth/login
# 应看到：Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Lax
```

**预防措施**：
- 部署前检查 `.env` 中的 Cookie 配置
- 使用 HTTPS（Let's Encrypt 免费证书）
- 确保 Nginx 配置包含 Cookie 传递指令

---

### 2. CORS 跨域错误

**症状**：
```
Access to fetch at 'https://api.example.com/...' from origin 'https://teacher.example.com' 
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present.
```

**可能原因**：
1. `CORS_ORIGINS` 环境变量未配置或为空
2. 前端域名不在 `CORS_ORIGINS` 列表中
3. Nginx 层配置了 CORS 头，与后端冲突
4. 使用了通配符 `*` 但需要 Cookie 认证

**解决方案**：
```bash
# 1. 检查后端 CORS 配置
grep CORS_ORIGINS backend/.env
# 应看到：CORS_ORIGINS=https://student.example.com,https://teacher.example.com,https://parent.example.com

# 2. 检查后端日志
tail -f /var/log/speakingtest/error.log | grep CORS
# 应看到：CORS origins configured: ['https://student.example.com', ...]

# 3. 移除 Nginx 层的 CORS 配置（如果存在）
# nginx/prod.conf 中不应有：
# add_header Access-Control-Allow-Origin "*" always;  # ❌ 错误

# 4. 验证 CORS 响应头
curl -I -H "Origin: https://teacher.example.com" https://teacher.example.com/api/v1/health
# 应看到：Access-Control-Allow-Origin: https://teacher.example.com
```

**预防措施**：
- 生产环境必须显式配置 `CORS_ORIGINS`
- 不要使用通配符 `*`（与 Cookie 认证冲突）
- 确保前端域名完全匹配（包括协议 `https://`）

---

### 3. Token 过期或无效

**症状**：
- 登录后一段时间自动退出
- 401 错误：`Could not validate credentials`

**可能原因**：
1. `ACCESS_TOKEN_EXPIRE_MINUTES` 设置过短
2. JWT 密钥在生产环境未更改（仍使用默认值）
3. 多实例部署时 JWT 密钥不一致

**解决方案**：
```bash
# 1. 检查 Token 过期时间
grep ACCESS_TOKEN_EXPIRE_MINUTES backend/.env
# 建议：1440（24小时）或更长

# 2. 检查 JWT 密钥
grep JWT_SECRET_KEY backend/.env
# 不应是：your-secret-key-change-in-production

# 3. 生成新密钥
openssl rand -hex 32
# 更新到 .env 文件

# 4. 验证密钥一致性（多实例部署）
# 所有实例必须使用相同的 JWT_SECRET_KEY
```

**预防措施**：
- 部署前生成强随机密钥
- 使用密钥管理服务（如 AWS Secrets Manager）
- 确保所有实例配置一致

---

## 🌐 网络与代理问题

### 4. API 请求 502 Bad Gateway

**症状**：
- 前端请求返回 502
- Nginx 错误日志：`upstream prematurely closed connection`

**可能原因**：
1. 后端服务未启动或崩溃
2. 后端监听地址错误（应为 `127.0.0.1:8000` 而非 `0.0.0.0:8000`）
3. Nginx upstream 配置错误
4. 后端进程被 OOM 杀死

**解决方案**：
```bash
# 1. 检查后端服务状态
systemctl status speakingtest-api
# 或
ps aux | grep uvicorn

# 2. 检查后端日志
tail -f /var/log/speakingtest/error.log

# 3. 检查端口监听
netstat -tlnp | grep 8000
# 应看到：127.0.0.1:8000

# 4. 检查 Nginx upstream
grep -A5 "upstream backend_cluster" nginx/prod.conf
# 应看到：server 127.0.0.1:8000

# 5. 检查系统资源
free -h  # 内存
df -h    # 磁盘
```

**预防措施**：
- 配置 systemd 自动重启
- 设置资源限制（防止 OOM）
- 监控服务健康状态

---

### 5. 静态资源 404

**症状**：
- 前端页面空白
- 浏览器控制台：`Failed to load resource: 404`

**可能原因**：
1. 前端构建文件路径错误
2. Nginx `root` 配置路径不存在
3. 构建产物未正确部署

**解决方案**：
```bash
# 1. 检查构建产物
ls -la /var/www/speakingtest/teacher-web/dist/
# 应看到：index.html, assets/ 等

# 2. 检查 Nginx root 配置
grep "root /var/www" nginx/prod.conf
# 路径必须存在且可读

# 3. 检查文件权限
ls -ld /var/www/speakingtest/
# 应可读：drwxr-xr-x

# 4. 验证构建
cd frontend/teacher-web
npm run build
# 检查 dist/ 目录是否生成
```

**预防措施**：
- 使用 CI/CD 自动构建和部署
- 验证构建产物完整性
- 确保部署路径正确

---

## 🗄️ 数据库问题

### 6. 数据库连接失败

**症状**：
- 启动时报错：`Cannot start application: Database connection failed`
- API 返回 500：`database connection error`

**可能原因**：
1. `DATABASE_URL` 配置错误
2. 数据库服务未启动
3. 网络不通（RDS 白名单未配置）
4. 连接池耗尽

**解决方案**：
```bash
# 1. 检查数据库 URL
grep DATABASE_URL backend/.env
# 格式：postgresql+asyncpg://user:pass@host:5432/dbname

# 2. 测试连接
psql "postgresql://user:pass@host:5432/dbname" -c "SELECT 1"

# 3. 检查 RDS 白名单（阿里云）
# 控制台 → RDS → 数据安全性 → 白名单
# 添加后端服务器内网 IP

# 4. 检查连接池配置
grep DB_POOL backend/.env
# DB_POOL_SIZE=30
# DB_MAX_OVERFLOW=70

# 5. 检查活跃连接数
psql "..." -c "SELECT count(*) FROM pg_stat_activity;"
```

**预防措施**：
- 使用连接池（避免连接耗尽）
- 配置 RDS 白名单
- 监控数据库连接数

---

### 7. 数据库迁移未执行

**症状**：
- 启动时报错：`relation "xxx" does not exist`
- API 返回 500：`table not found`

**可能原因**：
1. 首次部署未执行初始化脚本
2. 增量迁移未执行
3. 迁移脚本执行失败但未发现

**解决方案**：
```bash
# 1. 检查数据库表
psql "..." -c "\dt"
# 应看到所有表：users, tests, student_profiles 等

# 2. 执行初始化脚本
psql "..." -f backend/database/init.sql

# 3. 执行增量迁移
psql "..." -f backend/database/migrations/001_interpretation_pages.sql
psql "..." -f backend/database/migrations/002_interpretation_status.sql

# 4. 验证表结构
psql "..." -c "\d+ tests"
```

**预防措施**：
- 部署前检查迁移脚本
- 使用数据库迁移工具（如 Alembic）
- 记录迁移执行日志

---

## 🤖 AI 服务问题

### 8. Qwen API 调用失败

**症状**：
- 测评任务一直处于 `processing` 状态
- Worker 日志：`Qwen API error: 401` 或 `rate limit exceeded`

**可能原因**：
1. `QWEN_API_KEY` 无效或过期
2. API 配额用尽
3. 网络问题（无法访问 dashscope.aliyuncs.com）
4. 请求频率超限

**解决方案**：
```bash
# 1. 检查 API Key
grep QWEN_API_KEY backend/.env
# 格式：sk-xxx

# 2. 测试 API 连接
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer sk-xxx" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"test"}]}'

# 3. 检查 Worker 日志
tail -f /var/log/speakingtest/worker-part2.log | grep -i "qwen\|error"

# 4. 检查限流配置
grep QWEN_RPM_LIMIT backend/.env
# 建议：60（每分钟 60 次）

# 5. 查看阿里云控制台
# 检查 API 调用量、余额、配额
```

**预防措施**：
- 配置 API 调用监控
- 设置合理的限流值
- 准备备用 API Key

---

### 9. 音频上传到 OSS 失败

**症状**：
- 学生录音上传失败
- 错误：`OSS upload failed: AccessDenied`

**可能原因**：
1. OSS AccessKey 配置错误
2. Bucket 权限设置错误
3. 跨域配置未开启（前端直传）
4. 网络问题

**解决方案**：
```bash
# 1. 检查 OSS 配置
grep OSS_ backend/.env
# OSS_ACCESS_KEY_ID=xxx
# OSS_ACCESS_KEY_SECRET=xxx
# OSS_ENDPOINT=oss-cn-xxx.aliyuncs.com
# OSS_BUCKET_NAME=xxx

# 2. 测试 OSS 连接
python3 << EOF
import oss2
auth = oss2.Auth('ACCESS_KEY_ID', 'ACCESS_KEY_SECRET')
bucket = oss2.Bucket(auth, 'ENDPOINT', 'BUCKET_NAME')
print(bucket.list_objects(max_keys=1))
EOF

# 3. 检查 Bucket 权限
# 阿里云控制台 → OSS → Bucket → 权限管理
# 读写权限：公共读（或私有 + 签名 URL）

# 4. 检查跨域配置（如前端直传）
# Bucket → 跨域设置 → 添加规则
# 允许来源：https://student.example.com
# 允许方法：POST, PUT
# 允许头：Content-Type, Authorization
```

**预防措施**：
- 使用子账号 AccessKey（最小权限）
- 配置 Bucket 跨域规则
- 监控 OSS 使用量

---

## ⚡ 性能问题

### 10. 限流不生效（多实例部署）

**症状**：
- 单实例限流正常，多实例时无效
- 攻击者可以绕过限流

**可能原因**：
1. Redis 未配置或连接失败
2. 限流使用内存模式（单实例有效）
3. Redis 连接配置错误

**解决方案**：
```bash
# 1. 检查 Redis 配置
grep REDIS_URL backend/.env
# 格式：redis://host:6379/0

# 2. 测试 Redis 连接
redis-cli -h host -p 6379 ping
# 应返回：PONG

# 3. 检查后端日志
tail -f /var/log/speakingtest/error.log | grep -i redis
# 应看到：Redis rate limiting enabled
# 不应看到：Redis unavailable, using in-memory fallback

# 4. 验证限流键
redis-cli -h host -p 6379
> KEYS rate_limit:*
# 应看到限流键存在
```

**预防措施**：
- 生产环境必须配置 Redis
- 使用 Redis 集群（高可用）
- 监控 Redis 连接状态

---

### 11. 任务队列积压

**症状**：
- 测评任务长时间处于 `pending` 状态
- Worker 日志显示处理缓慢

**可能原因**：
1. Worker 进程未启动或崩溃
2. RabbitMQ 连接失败
3. Worker 处理速度慢（AI API 慢）
4. 队列配置错误

**解决方案**：
```bash
# 1. 检查 Worker 状态
systemctl status speakingtest-worker-part1
systemctl status speakingtest-worker-part2
systemctl status speakingtest-worker-interp

# 2. 检查 RabbitMQ
systemctl status rabbitmq-server
rabbitmqctl status

# 3. 检查队列积压
rabbitmqctl list_queues name messages
# 应看到消息数较少（< 100）

# 4. 检查 Worker 日志
tail -f /var/log/speakingtest/worker-part2.log

# 5. 增加 Worker 实例（如需要）
# 复制 systemd service 文件，修改实例编号
```

**预防措施**：
- 配置 Worker 自动重启
- 监控队列长度
- 根据负载调整 Worker 数量

---

## 🔒 安全问题

### 12. 测试模式未关闭

**症状**：
- 任何人都可以用 `888888` 登录
- 非 @51talk.com 邮箱可以登录

**可能原因**：
1. `ENABLE_TEST_AUTH=true` 未改为 `false`
2. `TEST_EMAIL_WHITELIST` 配置了测试邮箱

**解决方案**：
```bash
# 1. 检查测试模式
grep ENABLE_TEST_AUTH backend/.env
# 必须为：ENABLE_TEST_AUTH=false

# 2. 检查测试邮箱白名单
grep TEST_EMAIL_WHITELIST backend/.env
# 应为空或注释掉

# 3. 验证登录接口
# 尝试用非 @51talk.com 邮箱登录，应被拒绝
```

**预防措施**：
- 部署前检查 `.env` 配置
- 使用配置检查脚本
- 代码审查时注意安全开关

---

### 13. 学生 Token 可重复使用

**症状**：
- 学生入口链接可多次使用
- 链接泄露后被多人使用

**可能原因**：
1. `ENABLE_TOKEN_REENTRY=true` 未改为 `false`

**解决方案**：
```bash
# 1. 检查 Token 策略
grep ENABLE_TOKEN_REENTRY backend/.env
# 必须为：ENABLE_TOKEN_REENTRY=false

# 2. 验证 Token 使用
# 使用同一个 Token 两次，第二次应失败
```

**预防措施**：
- 生产环境默认禁用重复使用
- 仅在测试环境启用

---

## 📊 监控与日志

### 14. 日志文件过大

**症状**：
- 磁盘空间不足
- 日志文件占用大量空间

**解决方案**：
```bash
# 1. 配置日志轮转
cat > /etc/logrotate.d/speakingtest << EOF
/var/log/speakingtest/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload speakingtest-api > /dev/null 2>&1 || true
    endscript
}
EOF

# 2. 手动清理旧日志
find /var/log/speakingtest -name "*.log.*" -mtime +7 -delete
```

**预防措施**：
- 配置 logrotate
- 使用集中式日志（如 ELK）
- 定期清理旧日志

---

## 🚨 紧急恢复流程

### 服务完全不可用

1. **检查服务状态**
   ```bash
   systemctl status speakingtest-*
   ```

2. **查看错误日志**
   ```bash
   tail -100 /var/log/speakingtest/error.log
   journalctl -u speakingtest-api -n 100
   ```

3. **重启服务**
   ```bash
   systemctl restart speakingtest-api
   systemctl restart speakingtest-worker-*
   ```

4. **回滚到上一个版本**（如需要）
   ```bash
   git checkout <previous-commit>
   systemctl restart speakingtest-api
   ```

---

## 📝 问题记录模板

遇到新问题时，请记录：

```markdown
### 问题编号：XX

**时间**：2024-XX-XX
**环境**：生产/测试
**症状**：
- 具体错误信息
- 影响范围

**原因**：
- 根本原因分析

**解决方案**：
- 具体操作步骤

**预防措施**：
- 如何避免再次发生
```

---

## 🔗 相关文档

- [部署检查清单](./production-checklist.md)
- [Nginx 配置说明](../nginx/README.md)
- [后端 README](../backend/README.md)
