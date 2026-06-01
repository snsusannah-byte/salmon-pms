#!/bin/bash
# ============================================================
# Salmon PMS — WSL2 原生部署脚本（无 Docker）
# 数据持久化到 E 盘
# ============================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')] $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] 警告: $1${NC}"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] 错误: $1${NC}"; exit 1; }

DEPLOY_DIR="/mnt/e/salmon-pms-deploy"
PROJECT_DIR="/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms"

log "开始 WSL2 原生部署..."

# ============================================================
# 1. 安装系统依赖
# ============================================================
log "检查并安装系统依赖..."
sudo apt-get update

for pkg in postgresql postgresql-contrib redis-server nginx; do
    if ! dpkg -l | grep -q "^ii  $pkg "; then
        log "安装 $pkg..."
        sudo apt-get install -y "$pkg"
    else
        log "$pkg 已安装"
    fi
done

# ============================================================
# 2. 配置 PostgreSQL（数据落 E 盘）
# ============================================================
PG_DATA="$DEPLOY_DIR/data/postgres"
mkdir -p "$PG_DATA"
sudo chown postgres:postgres "$PG_DATA"

# 如果 E 盘还没有初始化过数据库，初始化
if [ ! -f "$PG_DATA/PG_VERSION" ]; then
    log "初始化 PostgreSQL 数据目录（E 盘）..."
    sudo -u postgres pg_ctl initdb -D "$PG_DATA"
    
    # 允许本地连接（WSL2 内）
    sudo -u postgres sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" "$PG_DATA/postgresql.conf"
    echo "host all all 127.0.0.1/32 md5" | sudo -u postgres tee -a "$PG_DATA/pg_hba.conf"
fi

# 配置 postgresql.service 使用 E 盘数据目录
if ! grep -q "Environment=PGDATA=$PG_DATA" /etc/systemd/system/postgresql.service 2>/dev/null; then
    log "配置 PostgreSQL 使用 E 盘数据目录..."
    sudo mkdir -p /etc/systemd/system/postgresql.service.d
    cat <<EOF | sudo tee /etc/systemd/system/postgresql.service.d/override.conf
[Service]
Environment=PGDATA=$PG_DATA
ExecStart=
ExecStart=/usr/lib/postgresql/16/bin/pg_ctlcluster 16 main start --foreground
EOF
    sudo sed -i "s|/var/lib/postgresql/16/main|$PG_DATA|" /etc/systemd/system/postgresql.service.d/override.conf 2>/dev/null || true
fi

# 启动 PostgreSQL
sudo systemctl daemon-reload
sudo systemctl enable postgresql
sudo systemctl restart postgresql

# 创建数据库和用户
log "创建 salmon 数据库..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='salmon'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER salmon WITH PASSWORD '001978';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='salmon_pms'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE salmon_pms OWNER salmon;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE salmon_pms TO salmon;"

# ============================================================
# 3. 配置 Redis（数据落 E 盘）
# ============================================================
REDIS_DATA="$DEPLOY_DIR/data/redis"
mkdir -p "$REDIS_DATA"

sudo systemctl enable redis-server
sudo systemctl restart redis-server

# ============================================================
# 4. 前端构建
# ============================================================
log "构建前端..."
cd "$PROJECT_DIR/frontend"

# 确保生产构建时 API 地址是相对路径（由 nginx 反代）
export VITE_API_URL=/api
pnpm install
pnpm run build

# 复制构建产物到 E 盘
cp -r dist "$DEPLOY_DIR/"
log "前端构建完成，已复制到 $DEPLOY_DIR/dist"

# ============================================================
# 5. 后端环境准备
# ============================================================
cd "$PROJECT_DIR/backend"

# 确保 venv 存在
if [ ! -d ".venv" ]; then
    log "创建 Python 虚拟环境..."
    python3 -m venv .venv
fi

# 激活并安装依赖
source .venv/bin/activate
pip install uv
uv pip install -e "."

# ============================================================
# 6. 数据库迁移
# ============================================================
log "执行数据库迁移..."
if command -v alembic &> /dev/null; then
    alembic upgrade head || warn "Alembic 迁移失败（可能无需迁移或手动执行）"
else
    warn "alembic 未安装，跳过自动迁移"
fi

# ============================================================
# 7. 配置 systemd 服务
# ============================================================
log "配置 systemd 服务..."

# 后端服务
sudo cp "$PROJECT_DIR/scripts/salmon-backend.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable salmon-backend

# 前端 nginx 配置
sudo mkdir -p "$DEPLOY_DIR"
sudo cp "$PROJECT_DIR/scripts/nginx-e-drive.conf" "$DEPLOY_DIR/nginx.conf"

# 前端服务（用 systemd 启动 nginx，加载 E 盘的配置）
sudo cp "$PROJECT_DIR/scripts/salmon-frontend.service" /etc/systemd/system/
sudo systemctl enable salmon-frontend

# ============================================================
# 8. 启动所有服务
# ============================================================
log "启动服务..."
sudo systemctl restart postgresql
sudo systemctl restart redis-server
sudo systemctl restart salmon-backend
sudo systemctl restart salmon-frontend

# ============================================================
# 9. 健康检查
# ============================================================
log "等待服务就绪..."
sleep 5

for i in {1..10}; do
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        log "✅ nginx 健康检查通过"
        break
    fi
    if [ "$i" -eq 10 ]; then
        warn "nginx 健康检查失败，查看日志: sudo journalctl -u salmon-frontend"
    fi
    sleep 2
done

if curl -sf http://localhost/api/v1/dashboard > /dev/null 2>&1; then
    log "✅ 后端 API 检查通过"
else
    warn "后端 API 未响应，查看日志: sudo journalctl -u salmon-backend"
fi

# ============================================================
# 10. Windows 防火墙提示
# ============================================================
IP=$(hostname -I | awk '{print $1}')
log ""
log "========================================"
log "🎉 部署完成！"
log "========================================"
log "本机访问: http://localhost"
log "局域网访问: http://$IP"
log ""
log "⚠️  请在 Windows 防火墙放行 80 端口："
log "    管理员 PowerShell:"
log "    New-NetFirewallRule -DisplayName 'Salmon PMS' -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow"
log ""
log "数据目录: $DEPLOY_DIR"
log "备份脚本: $PROJECT_DIR/scripts/backup-native.sh"
log "========================================"
