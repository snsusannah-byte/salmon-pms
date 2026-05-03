#!/bin/bash
# salmon-pms 数据库自动备份脚本
# 建议添加到 crontab: */5 * * * * /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/scripts/backup-db.sh

DB_PATH="/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend/salmon_pms_dev.db"
BACKUP_DIR="/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 确保备份目录存在
mkdir -p "$BACKUP_DIR"

# 使用 SQLite 在线备份（不锁定数据库）
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/salmon_pms_dev_${TIMESTAMP}.db'"

# 只保留最近 10 个备份
ls -t "$BACKUP_DIR"/salmon_pms_dev_*.db | tail -n +11 | xargs -r rm -f

echo "[$(date)] Backup completed: salmon_pms_dev_${TIMESTAMP}.db"
