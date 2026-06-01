#!/bin/bash
# ============================================================
# Salmon PMS 部署机一键更新脚本
# 用法: ./deploy.sh
# ============================================================

set -e

DEPLOY_DIR="/srv/salmon-pms"
LOG_FILE="/var/log/salmon-pms-deploy.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] 警告: $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] 错误: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

# 检查是否以root运行（Docker需要）
if [ "$EUID" -ne 0 ]; then
    warn "建议以 root 运行，否则 Docker 命令可能需要 sudo"
fi

log "开始部署 Salmon PMS..."

# 进入部署目录
cd "$DEPLOY_DIR" || error "部署目录不存在: $DEPLOY_DIR"

# 拉取最新代码
log "拉取最新代码..."
if [ -d ".git" ]; then
    git fetch origin
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})
    if [ "$LOCAL" = "$REMOTE" ]; then
        log "代码已是最新，无需更新"
        exit 0
    fi
    git pull origin main || error "Git pull 失败"
else
    error "部署目录不是 Git 仓库"
fi

# 备份数据库（更新前自动备份）
log "更新前自动备份数据库..."
if [ -f "scripts/backup.sh" ]; then
    bash scripts/backup.sh || warn "自动备份失败，继续部署"
else
    warn "备份脚本不存在，跳过自动备份"
fi

# 执行数据库迁移（如需要）
log "检查数据库迁移..."
if docker compose -f docker-compose.prod.yml ps db | grep -q "healthy"; then
    log "数据库运行正常"
else
    warn "数据库状态未知，继续部署..."
fi

# 构建并启动容器
log "构建并重启服务..."
docker compose -f docker-compose.prod.yml down || warn "停止旧容器失败"
docker compose -f docker-compose.prod.yml up --build -d || error "构建/启动失败"

# 等待服务就绪
log "等待服务就绪..."
sleep 5

# 健康检查
for i in {1..10}; do
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        log "✅ 服务健康检查通过"
        break
    fi
    if [ "$i" -eq 10 ]; then
        error "服务启动后健康检查失败，请查看日志: docker compose -f docker-compose.prod.yml logs"
    fi
    warn "健康检查重试 $i/10..."
    sleep 3
done

# 清理旧镜像
log "清理未使用的 Docker 资源..."
docker system prune -f --volumes || warn "清理旧资源失败"

log "✅ 部署完成！访问地址: http://$(hostname -I | awk '{print $1}')"
