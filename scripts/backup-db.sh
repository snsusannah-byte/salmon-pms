#!/bin/bash
# Salmon PMS 数据库备份脚本

set -e

BACKUP_DIR="$(dirname "$0")/../backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"
CONTAINER_NAME="salmon-pms-db-1"
DB_NAME="salmon_pms"
DB_USER="salmon"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 检查容器是否在运行
if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "⚠️  PostgreSQL 容器 $CONTAINER_NAME 未运行，尝试用 docker compose ps 查找..."
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -E 'db|postgres' | head -1)
    if [ -z "$CONTAINER_NAME" ]; then
        echo "❌ 错误: 找不到 PostgreSQL 容器"
        exit 1
    fi
    echo "✅ 找到容器: $CONTAINER_NAME"
fi

# 执行备份
echo "🔄 正在备份数据库..."
docker exec -t "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"

# 压缩备份
gzip "$BACKUP_FILE"
BACKUP_FILE="$BACKUP_FILE.gz"

# 显示备份信息
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ 备份完成: $BACKUP_FILE ($FILE_SIZE)"

# 清理旧备份（保留30天）
echo "🧹 清理 $RETENTION_DAYS 天前的旧备份..."
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "backup_*.sql.gz" | wc -l)
echo "📦 当前共有 $BACKUP_COUNT 个备份文件"
