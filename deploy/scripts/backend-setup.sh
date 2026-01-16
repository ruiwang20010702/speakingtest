#!/bin/bash
# 后端服务器部署脚本
# 适用于 Ubuntu 22.04 / Debian 12
# 用法: sudo ./backend-setup.sh

set -e

echo "=========================================="
echo "  口语测评系统 - 后端服务器部署脚本"
echo "=========================================="

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 变量配置
APP_DIR="/opt/speakingtest"
APP_USER="speakingtest"
PYTHON_VERSION="3.11"
RABBITMQ_USER="speakingtest"
RABBITMQ_PASS="change-this-password"  # 请修改此密码

echo ""
echo ">>> 1. 更新系统包"
apt update && apt upgrade -y

echo ""
echo ">>> 2. 安装基础依赖"
apt install -y \
    curl \
    wget \
    git \
    build-essential \
    libpq-dev \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python${PYTHON_VERSION}-dev \
    python3-pip \
    supervisor

echo ""
echo ">>> 3. 安装 RabbitMQ"
# 添加 RabbitMQ 官方源
curl -1sLf "https://keys.openpgp.org/vks/v1/by-fingerprint/0A9AF2115F4687BD29803A206B73A36E6026DFCA" | gpg --dearmor | tee /usr/share/keyrings/com.rabbitmq.team.gpg > /dev/null
curl -1sLf "https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-erlang.E495BB49CC4BBE5B.key" | gpg --dearmor | tee /usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg > /dev/null
curl -1sLf "https://github.com/rabbitmq/signing-keys/releases/download/3.0/cloudsmith.rabbitmq-server.9F4587F226208342.key" | gpg --dearmor | tee /usr/share/keyrings/rabbitmq.9F4587F226208342.gpg > /dev/null

# 添加仓库
tee /etc/apt/sources.list.d/rabbitmq.list <<EOF
deb [signed-by=/usr/share/keyrings/rabbitmq.E495BB49CC4BBE5B.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-erlang/deb/ubuntu jammy main
deb [signed-by=/usr/share/keyrings/rabbitmq.9F4587F226208342.gpg] https://ppa1.novemberain.com/rabbitmq/rabbitmq-server/deb/ubuntu jammy main
EOF

apt update
apt install -y erlang-base erlang-asn1 erlang-crypto erlang-eldap erlang-ftp erlang-inets \
    erlang-mnesia erlang-os-mon erlang-parsetools erlang-public-key \
    erlang-runtime-tools erlang-snmp erlang-ssl erlang-syntax-tools \
    erlang-tftp erlang-tools erlang-xmerl rabbitmq-server

# 启动 RabbitMQ
systemctl enable rabbitmq-server
systemctl start rabbitmq-server

# 配置 RabbitMQ 用户
rabbitmqctl add_user $RABBITMQ_USER $RABBITMQ_PASS || true
rabbitmqctl set_permissions -p / $RABBITMQ_USER ".*" ".*" ".*"
rabbitmqctl set_user_tags $RABBITMQ_USER administrator

# 启用管理界面 (可选，调试用)
rabbitmq-plugins enable rabbitmq_management

echo ""
echo ">>> 4. 创建应用用户和目录"
id -u $APP_USER &>/dev/null || useradd -r -m -s /bin/bash $APP_USER
mkdir -p $APP_DIR
chown -R $APP_USER:$APP_USER $APP_DIR

echo ""
echo ">>> 5. 克隆代码 (请替换为你的仓库地址)"
echo "注意: 请手动执行以下命令克隆代码:"
echo "  cd $APP_DIR"
echo "  git clone https://github.com/your-repo/speakingtest.git ."
echo ""
echo "或者手动上传代码到 $APP_DIR"

# 创建目录结构
mkdir -p $APP_DIR/backend
mkdir -p $APP_DIR/logs

echo ""
echo ">>> 6. 创建 Python 虚拟环境"
cd $APP_DIR/backend
python${PYTHON_VERSION} -m venv venv
source venv/bin/activate

echo ""
echo ">>> 7. 创建环境变量模板"
cat > $APP_DIR/.env.example << 'EOF'
# 应用配置
APP_NAME="Speaking Test System"
DEBUG=false

# 数据库 (替换为 RDS 内网地址)
DATABASE_URL=postgresql+asyncpg://user:password@rm-xxx.pg.rds.aliyuncs.com:5432/speakingtest

# RabbitMQ (本地)
RABBITMQ_URL=amqp://speakingtest:change-this-password@localhost:5672/

# JWT 密钥 (请生成随机字符串)
JWT_SECRET_KEY=your-random-secret-key-change-in-production

# 讯飞 API
XUNFEI_APP_ID=
XUNFEI_API_KEY=
XUNFEI_API_SECRET=

# 通义千问 API
QWEN_API_KEY=

# 阿里云 OSS
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=

# 前端 URL
FRONTEND_STUDENT_URL=https://student.your-domain.com/s
FRONTEND_PARENT_URL=https://parent.your-domain.com
FRONTEND_TEACHER_URL=https://teacher.your-domain.com

# CORS
CORS_ORIGINS=https://student.your-domain.com,https://parent.your-domain.com,https://teacher.your-domain.com
EOF

cp $APP_DIR/.env.example $APP_DIR/.env
echo "请编辑 $APP_DIR/.env 填写实际配置"

echo ""
echo ">>> 8. 创建 systemd 服务文件"

# API 服务
cat > /etc/systemd/system/speakingtest-api.service << EOF
[Unit]
Description=Speaking Test API Server
After=network.target rabbitmq-server.service
Wants=rabbitmq-server.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/backend/venv/bin/uvicorn src.infrastructure.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Part1 Worker
cat > /etc/systemd/system/speakingtest-worker-part1.service << EOF
[Unit]
Description=Speaking Test Part1 Worker
After=network.target rabbitmq-server.service
Wants=rabbitmq-server.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/backend/venv/bin/python scripts/part1_worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Part2 Worker
cat > /etc/systemd/system/speakingtest-worker-part2.service << EOF
[Unit]
Description=Speaking Test Part2 Worker
After=network.target rabbitmq-server.service
Wants=rabbitmq-server.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/backend/venv/bin/python scripts/part2_worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Interpretation Worker
cat > /etc/systemd/system/speakingtest-worker-interp.service << EOF
[Unit]
Description=Speaking Test Interpretation Worker
After=network.target rabbitmq-server.service
Wants=rabbitmq-server.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/backend/venv/bin/python scripts/interpretation_worker.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 重载 systemd
systemctl daemon-reload

echo ""
echo ">>> 9. 设置目录权限"
chown -R $APP_USER:$APP_USER $APP_DIR

echo ""
echo "=========================================="
echo "  后端服务器部署完成！"
echo "=========================================="
echo ""
echo "接下来请手动完成以下步骤:"
echo ""
echo "1. 上传代码到 $APP_DIR/backend/"
echo ""
echo "2. 安装 Python 依赖:"
echo "   cd $APP_DIR/backend"
echo "   source venv/bin/activate"
echo "   pip install -r requirements.txt"
echo ""
echo "3. 编辑环境变量:"
echo "   vim $APP_DIR/.env"
echo ""
echo "4. 初始化数据库 (在 RDS 上执行 SQL):"
echo "   psql -h <RDS地址> -U <用户名> -d speakingtest -f database/init.sql"
echo ""
echo "5. 启动服务:"
echo "   sudo systemctl enable speakingtest-api"
echo "   sudo systemctl enable speakingtest-worker-part1"
echo "   sudo systemctl enable speakingtest-worker-part2"
echo "   sudo systemctl enable speakingtest-worker-interp"
echo ""
echo "   sudo systemctl start speakingtest-api"
echo "   sudo systemctl start speakingtest-worker-part1"
echo "   sudo systemctl start speakingtest-worker-part2"
echo "   sudo systemctl start speakingtest-worker-interp"
echo ""
echo "6. 验证服务:"
echo "   curl http://localhost:8000/health"
echo ""
echo "RabbitMQ 管理界面: http://<服务器IP>:15672"
echo "用户名: $RABBITMQ_USER"
echo "密码: $RABBITMQ_PASS"
echo ""
