#!/bin/bash
# Salmon PMS 数据库恢复脚本

set -e

BACKUP_DIR="$(dirname "$0")/../backups"
CONTAINER_NAME="salmon-pms-db-1"
DB_NAME="salmon_pms"
DB_USER="salmon"

# 如果没有指定备份文件，使用最新的
if [ -z "$1" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo "❌ 错误: 找不到备份文件"
        exit 1
    fi
    echo "📦 使用最新备份: $BACKUP_FILE"
else
    BACKUP_FILE="$1"
fi

# 确认
read -p "⚠️  这将覆盖现有数据库！确认恢复吗？ [y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# 查找容器
if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    CONTAINER_NAME=$(docker ps --format '{{.Names}}' | grep -E 'db|postgres' | head -1)
    if [ -z "$CONTAINER_NAME" ]; then
        echo "❌ 错误: PostgreSQL 容器未运行"
        exit 1
    fi
fi

# 恢复数据库
echo "🔄 正在恢复数据库..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip < "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME"
else
    docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
fi

echo "✅ 数据库恢复完成"
