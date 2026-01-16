#!/bin/bash
# 本地构建并部署脚本
# 在开发机上运行，构建前端并上传到服务器

set -e

# ============================================
# 配置区域 - 请修改为你的服务器信息
# ============================================
FRONTEND_SERVER="root@your-frontend-server-ip"
BACKEND_SERVER="root@your-backend-server-ip"
FRONTEND_WEB_DIR="/var/www/speakingtest"
BACKEND_APP_DIR="/opt/speakingtest"

# ============================================
# 颜色输出
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
echo_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
echo_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ============================================
# 获取项目根目录
# ============================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "=========================================="
echo "  口语测评系统 - 构建部署脚本"
echo "=========================================="
echo ""
echo "项目根目录: $PROJECT_ROOT"
echo "前端服务器: $FRONTEND_SERVER"
echo "后端服务器: $BACKEND_SERVER"
echo ""

# ============================================
# 选择部署目标
# ============================================
echo "请选择部署目标:"
echo "  1) 仅前端"
echo "  2) 仅后端"
echo "  3) 全部"
echo ""
read -p "请输入选项 [1/2/3]: " DEPLOY_TARGET

case $DEPLOY_TARGET in
    1) DEPLOY_FRONTEND=true; DEPLOY_BACKEND=false ;;
    2) DEPLOY_FRONTEND=false; DEPLOY_BACKEND=true ;;
    3) DEPLOY_FRONTEND=true; DEPLOY_BACKEND=true ;;
    *) echo_error "无效选项"; exit 1 ;;
esac

# ============================================
# 部署前端
# ============================================
deploy_frontend() {
    echo ""
    echo_info "========== 部署前端 =========="
    
    # 构建学生端
    echo_info "构建学生端 H5..."
    cd "$PROJECT_ROOT/frontend/student-h5"
    npm install
    npm run build
    
    # 构建家长端
    echo_info "构建家长端 H5..."
    cd "$PROJECT_ROOT/frontend/parent-h5"
    npm install
    npm run build
    
    # 构建老师端
    echo_info "构建老师端 Web..."
    cd "$PROJECT_ROOT/frontend/teacher-web"
    npm install
    npm run build
    
    # 上传到服务器
    echo_info "上传前端文件到服务器..."
    
    ssh $FRONTEND_SERVER "mkdir -p $FRONTEND_WEB_DIR/student-h5 $FRONTEND_WEB_DIR/parent-h5 $FRONTEND_WEB_DIR/teacher-web"
    
    rsync -avz --delete "$PROJECT_ROOT/frontend/student-h5/dist/" "$FRONTEND_SERVER:$FRONTEND_WEB_DIR/student-h5/"
    rsync -avz --delete "$PROJECT_ROOT/frontend/parent-h5/dist/" "$FRONTEND_SERVER:$FRONTEND_WEB_DIR/parent-h5/"
    rsync -avz --delete "$PROJECT_ROOT/frontend/teacher-web/dist/" "$FRONTEND_SERVER:$FRONTEND_WEB_DIR/teacher-web/"
    
    echo_info "前端部署完成!"
}

# ============================================
# 部署后端
# ============================================
deploy_backend() {
    echo ""
    echo_info "========== 部署后端 =========="
    
    # 同步后端代码
    echo_info "同步后端代码..."
    rsync -avz --delete \
        --exclude 'venv' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.env' \
        --exclude 'logs/*' \
        --exclude '*.db' \
        "$PROJECT_ROOT/backend/" "$BACKEND_SERVER:$BACKEND_APP_DIR/backend/"
    
    # 远程安装依赖并重启服务
    echo_info "安装依赖并重启服务..."
    ssh $BACKEND_SERVER << 'ENDSSH'
        cd /opt/speakingtest/backend
        source venv/bin/activate
        pip install -r requirements.txt
        
        sudo systemctl restart speakingtest-api
        sudo systemctl restart speakingtest-worker-part1
        sudo systemctl restart speakingtest-worker-part2
        sudo systemctl restart speakingtest-worker-interp
        
        # 等待服务启动
        sleep 3
        
        # 健康检查
        curl -s http://localhost:8000/health || echo "API 健康检查失败"
ENDSSH
    
    echo_info "后端部署完成!"
}

# ============================================
# 执行部署
# ============================================
if [ "$DEPLOY_FRONTEND" = true ]; then
    deploy_frontend
fi

if [ "$DEPLOY_BACKEND" = true ]; then
    deploy_backend
fi

echo ""
echo "=========================================="
echo "  部署完成!"
echo "=========================================="
