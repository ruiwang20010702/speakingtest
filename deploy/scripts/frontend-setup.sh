#!/bin/bash
# 前端服务器部署脚本
# 适用于 Ubuntu 22.04 / Debian 12
# 用法: sudo ./frontend-setup.sh

set -e

echo "=========================================="
echo "  口语测评系统 - 前端服务器部署脚本"
echo "=========================================="

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 变量配置
WEB_DIR="/var/www/speakingtest"
BACKEND_INTERNAL_IP="10.0.0.x"  # 替换为后端服务器内网 IP

echo ""
echo ">>> 1. 更新系统包"
apt update && apt upgrade -y

echo ""
echo ">>> 2. 安装 Nginx"
apt install -y nginx certbot python3-certbot-nginx

echo ""
echo ">>> 3. 创建网站目录"
mkdir -p $WEB_DIR/student-h5
mkdir -p $WEB_DIR/parent-h5
mkdir -p $WEB_DIR/teacher-web

# 创建占位文件
echo "<h1>Student H5 - 待部署</h1>" > $WEB_DIR/student-h5/index.html
echo "<h1>Parent H5 - 待部署</h1>" > $WEB_DIR/parent-h5/index.html
echo "<h1>Teacher Web - 待部署</h1>" > $WEB_DIR/teacher-web/index.html

chown -R www-data:www-data $WEB_DIR

echo ""
echo ">>> 4. 配置 Nginx"

# 备份默认配置
mv /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.bak 2>/dev/null || true

# 创建站点配置
cat > /etc/nginx/sites-available/speakingtest << EOF
# 后端 API (内网地址)
upstream backend {
    server $BACKEND_INTERNAL_IP:8000;
    keepalive 32;
}

# 学生端
server {
    listen 80;
    server_name student.your-domain.com;
    
    root $WEB_DIR/student-h5;
    index index.html;

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # API 代理
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 健康检查
    location /health {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
    }

    # 前端路由 (SPA)
    location / {
        try_files \$uri \$uri/ /index.html;
        
        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}

# 家长端
server {
    listen 80;
    server_name parent.your-domain.com;
    
    root $WEB_DIR/parent-h5;
    index index.html;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}

# 老师端
server {
    listen 80;
    server_name teacher.your-domain.com;
    
    root $WEB_DIR/teacher-web;
    index index.html;

    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
EOF

# 启用站点
ln -sf /etc/nginx/sites-available/speakingtest /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重启 Nginx
systemctl restart nginx
systemctl enable nginx

echo ""
echo "=========================================="
echo "  前端服务器部署完成！"
echo "=========================================="
echo ""
echo "接下来请手动完成以下步骤:"
echo ""
echo "1. 修改 Nginx 配置中的域名:"
echo "   vim /etc/nginx/sites-available/speakingtest"
echo "   - 替换 student.your-domain.com 为实际域名"
echo "   - 替换 parent.your-domain.com 为实际域名"
echo "   - 替换 teacher.your-domain.com 为实际域名"
echo ""
echo "2. 修改后端服务器内网 IP:"
echo "   - 替换 $BACKEND_INTERNAL_IP 为实际内网 IP"
echo ""
echo "3. 测试配置并重载:"
echo "   nginx -t && nginx -s reload"
echo ""
echo "4. 在本地构建前端并上传:"
echo ""
echo "   # 学生端"
echo "   cd frontend/student-h5"
echo "   npm run build"
echo "   scp -r dist/* root@<前端服务器>:$WEB_DIR/student-h5/"
echo ""
echo "   # 家长端"
echo "   cd frontend/parent-h5"
echo "   npm run build"
echo "   scp -r dist/* root@<前端服务器>:$WEB_DIR/parent-h5/"
echo ""
echo "   # 老师端"
echo "   cd frontend/teacher-web"
echo "   npm run build"
echo "   scp -r dist/* root@<前端服务器>:$WEB_DIR/teacher-web/"
echo ""
echo "5. 配置 HTTPS (域名解析生效后):"
echo "   certbot --nginx -d student.your-domain.com -d parent.your-domain.com -d teacher.your-domain.com"
echo ""
echo "6. 验证部署:"
echo "   curl http://student.your-domain.com"
echo "   curl http://student.your-domain.com/api/health"
echo ""
