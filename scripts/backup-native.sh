#!/bin/bash
# Salmon PMS 数据备份脚本（WSL2 原生部署）
set -e

DEPLOY_DIR="/mnt/e/salmon-pms-deploy"
BACKUP_DIR="$DEPLOY_DIR/data/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 备份 PostgreSQL
pg_dump -h localhost -U salmon -d salmon_pms | gzip > "$BACKUP_DIR/db.sql.gz"

# 备份 Redis
redis-cli BGSAVE
sleep 2
sudo cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis.rdb"

# 备份 MinIO（如果有）
if [ -d "$DEPLOY_DIR/data/minio" ]; then
    tar czf "$BACKUP_DIR/minio.tar.gz" -C "$DEPLOY_DIR/data" minio
fi

# 备份前端 dist
tar czf "$BACKUP_DIR/dist.tar.gz" -C "$DEPLOY_DIR" dist

echo "备份完成: $BACKUP_DIR"
