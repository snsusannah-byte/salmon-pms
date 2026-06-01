#!/bin/bash
# ============================================================
# Salmon PMS 数据库自动备份脚本
# 用法: ./backup.sh [备份目录]
# 定时任务: 0 2 * * * /srv/salmon-pms/scripts/backup.sh
# ============================================================

set -e

BACKUP_BASE="${1:-/srv/salmon-pms/data/backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_BASE/$DATE"
LOG_FILE="/var/log/salmon-pms-backup.log"
RETAIN_DAYS=30  # 保留30天备份

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

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

log "开始备份 Salmon PMS 数据..."

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 1. 数据库备份
log "备份 PostgreSQL 数据库..."
if docker ps | grep -q "salmon-pms-db"; then
    docker exec $(docker ps -q -f name=db) pg_dump -U salmon -d salmon_pms | gzip > "$BACKUP_DIR/db_salmon_pms.sql.gz" || error "数据库备份失败"
    log "数据库备份完成: $BACKUP_DIR/db_salmon_pms.sql.gz"
else
    # 直接使用宿主机数据目录备份（如果Docker不可用）
    if [ -d "/srv/salmon-pms/data/postgres" ]; then
        tar czf "$BACKUP_DIR/postgres_data.tar.gz" -C /srv/salmon-pms/data postgres || warn "宿主机数据目录备份失败"
        log "宿主机数据目录备份完成"
    else
        error "未找到数据库容器或数据目录"
    fi
fi

# 2. Redis 数据备份
log "备份 Redis 数据..."
if docker ps | grep -q "salmon-pms-redis"; then
    docker exec $(docker ps -q -f name=redis) redis-cli BGSAVE || warn "Redis BGSAVE 失败"
    sleep 2
    docker cp $(docker ps -q -f name=redis):/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb" || warn "Redis 备份失败"
    log "Redis 备份完成"
fi

# 3. MinIO 数据备份
log "备份 MinIO 数据..."
if [ -d "/srv/salmon-pms/data/minio" ]; then
    tar czf "$BACKUP_DIR/minio_data.tar.gz" -C /srv/salmon-pms/data minio || warn "MinIO 备份失败"
    log "MinIO 备份完成"
fi

# 4. 生成备份清单
cat > "$BACKUP_DIR/backup_manifest.json" <<EOF
{
    "backup_time": "$DATE",
    "hostname": "$(hostname)",
    "files": [
        "db_salmon_pms.sql.gz",
        "redis_dump.rdb",
        "minio_data.tar.gz"
    ],
    "retain_days": $RETAIN_DAYS
}
EOF

log "备份清单已生成"

# 5. 清理旧备份
log "清理 $RETAIN_DAYS 天前的旧备份..."
find "$BACKUP_BASE" -maxdepth 1 -type d -mtime +$RETAIN_DAYS -exec rm -rf {} \; || warn "旧备份清理失败"

# 统计
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
BACKUP_COUNT=$(find "$BACKUP_BASE" -maxdepth 1 -type d | wc -l)

log "✅ 备份完成"
log "备份位置: $BACKUP_DIR"
log "备份大小: $BACKUP_SIZE"
log "总备份数: $BACKUP_COUNT"
