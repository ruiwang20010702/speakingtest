# Nginx 配置说明

本系统采用 Nginx 作为统一入口网关，负责静态资源分发、反向代理、SSL 终止及负载均衡。

---

## 📂 配置文件结构

| 文件 | 用途 | 说明 |
|------|------|------|
| `dev.conf` | 开发环境 | 统一入口 (8080)，代理到各 Vite 开发服务器及 FastAPI |
| `prod.conf` | 生产环境 | 多域名配置 (student/parent/teacher)，支持 HTTPS 与 Gzip 压缩 |

---

## 🛠️ 开发环境 (Local Development)

### 服务端口映射

| 服务 | 端口 | 路径 |
|------|------|------|
| **Nginx 入口** | **8080** | `http://localhost:8080` |
| 后端 API | 8000 | `/api/*` |
| 学生端 H5 | 3001 | `/s/*` |
| 家长端 H5 | 3000 | `/p/*` |
| 老师端 Web | 5173 | `/t/*` |

### 启动方法 (macOS)

```bash
# 启动 Nginx (指定当前目录配置)
nginx -c $(pwd)/nginx/dev.conf -p $(pwd)/nginx

# 重载配置
nginx -s reload

# 停止
nginx -s stop
```

---

## 🌐 生产环境 (Production)

### 域名规划建议

- **学生端**: `student.your-domain.com`
- **家长端**: `parent.your-domain.com`
- **老师端**: `teacher.your-domain.com`
- **API 服务**: `api.your-domain.com` (可选，也可统一使用主域名路径)

### 核心配置要点

1.  **静态文件服务**:
    ```nginx
    location / {
        root /var/www/speakingtest/student-h5;
        try_files $uri $uri/ /index.html;
    }
    ```
2.  **API 反向代理**:
    ```nginx
    location /api/ {
        proxy_pass http://backend_cluster;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    ```
3.  **SSL 终止**: 建议使用 `certbot` 自动管理 Let's Encrypt 证书。

---

## 🚀 性能优化建议

- **Gzip 压缩**: 开启 `gzip on;` 以减少 JS/CSS 传输体积。
- **缓存策略**: 为静态资源 (Images, Fonts) 设置长缓存 `expires 30d;`。
- **负载均衡**: 在 `upstream` 中配置多个后端实例以实现高可用。
