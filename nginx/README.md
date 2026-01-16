# Nginx 配置说明

## 文件说明

| 文件 | 用途 |
|------|------|
| `dev.conf` | 开发环境配置，统一入口代理到各服务 |
| `prod.conf` | 生产环境配置，多域名 + HTTPS + 负载均衡 |

---

## 开发环境

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 API | 8000 | FastAPI + Uvicorn |
| 学生端 H5 | 3001 | Vite dev server |
| 家长端 H5 | 3000 | Vite dev server |
| 老师端 Web | 5173 | Vite dev server |
| **Nginx 入口** | **8080** | 统一代理 |

### 路由规则

通过 `http://localhost:8080` 访问：

| 路径 | 代理目标 |
|------|----------|
| `/api/*` | 后端 API (8000) |
| `/s/*` | 学生端 H5 (3001) |
| `/p/*` 或 `/parent/*` | 家长端 H5 (3000) |
| `/t/*` 或 `/teacher/*` | 老师端 Web (5173) |
| `/` | 重定向到 `/s/` |

### macOS 启动方法

```bash
# 1. 安装 nginx (如果没有)
brew install nginx

# 2. 方法 A: 直接使用配置文件
cd /Users/ruiwang/Desktop/speakingtest
nginx -c $(pwd)/nginx/dev.conf -p $(pwd)/nginx

# 3. 方法 B: 链接到 nginx 配置目录
ln -sf $(pwd)/nginx/dev.conf /opt/homebrew/etc/nginx/servers/speakingtest.conf
brew services restart nginx

# 4. 测试配置
nginx -t

# 5. 重载配置
nginx -s reload

# 6. 停止
nginx -s stop
```

### 开发时启动顺序

```bash
# 终端 1: 后端
cd backend && ./scripts/dev.sh

# 终端 2: 学生端
cd frontend/student-h5 && npm run dev

# 终端 3: 家长端
cd frontend/parent-h5 && npm run dev

# 终端 4: 老师端
cd frontend/teacher-web && npm run dev

# 终端 5: Nginx (可选，不用 Nginx 也能单独访问各服务)
nginx -c $(pwd)/nginx/dev.conf -p $(pwd)/nginx
```

---

## 生产环境

### 域名规划

| 子域名 | 用途 |
|--------|------|
| `student.your-domain.com` | 学生端 H5 |
| `parent.your-domain.com` | 家长端 H5 |
| `teacher.your-domain.com` | 老师端 Web |
| `api.your-domain.com` | API 服务 (可选) |

### 部署步骤

1. **构建前端**
   ```bash
   # 学生端
   cd frontend/student-h5 && npm run build
   
   # 家长端
   cd frontend/parent-h5 && npm run build
   
   # 老师端
   cd frontend/teacher-web && npm run build
   ```

2. **部署静态文件**
   ```bash
   # 复制到 nginx 静态目录
   cp -r frontend/student-h5/dist /var/www/speakingtest/student-h5/
   cp -r frontend/parent-h5/dist /var/www/speakingtest/parent-h5/
   cp -r frontend/teacher-web/dist /var/www/speakingtest/teacher-web/
   ```

3. **配置 SSL 证书**
   ```bash
   # 使用 Let's Encrypt
   certbot certonly --nginx -d student.your-domain.com -d parent.your-domain.com -d teacher.your-domain.com
   
   # 或者放置购买的证书
   cp your-cert.pem /etc/nginx/ssl/your-domain.com.pem
   cp your-key.key /etc/nginx/ssl/your-domain.com.key
   ```

4. **修改配置文件**
   - 替换 `your-domain.com` 为实际域名
   - 修改 SSL 证书路径
   - 修改静态文件路径

5. **启动 Nginx**
   ```bash
   # 测试配置
   nginx -t
   
   # 重载
   nginx -s reload
   ```

### 后端部署

```bash
# 使用 gunicorn + uvicorn workers
cd backend
gunicorn src.infrastructure.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/speakingtest/access.log \
    --error-logfile /var/log/speakingtest/error.log
```

---

## 常见问题

### Q: 开发时是否必须使用 Nginx?

**不需要**。每个前端项目已配置 Vite 代理：
- 学生端 `vite.config.ts` 已配置 `/api` 代理到 `localhost:8000`
- 直接访问 `localhost:3001` 即可开发

Nginx 的好处是**统一入口**，方便测试多端协作。

### Q: 生产环境用云 SLB 还是 Nginx?

都可以：
- **云 SLB**: 省心，自带健康检查、SSL 终止
- **Nginx**: 更灵活，适合自建服务器

推荐：**云 SLB + Nginx**
- SLB 做负载均衡和 SSL 终止
- Nginx 做静态文件服务和路由

### Q: 如何扩展后端实例?

修改 `prod.conf` 中的 upstream:

```nginx
upstream backend_cluster {
    least_conn;
    server 10.0.0.1:8000 weight=1;
    server 10.0.0.2:8000 weight=1;
    server 10.0.0.3:8000 weight=1;
    keepalive 32;
}
```
