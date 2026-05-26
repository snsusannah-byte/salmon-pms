#!/bin/bash
# Salmon PMS 紧急回滚脚本
# 回滚到上线前的状态

set -e

PROJECT_DIR="$(dirname "$0")/.."
cd "$PROJECT_DIR"

echo "⏪ Salmon PMS 紧急回滚"
echo "========================"
echo ""

# 1. 确认
read -p "⚠️  这将回滚代码和数据到上线前！确认吗？ [y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# 2. 停止服务
echo ""
echo "🛑 步骤 1/4: 停止服务..."
cd docker && docker compose down 2>/dev/null || true
cd ..
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# 3. 回滚代码
echo ""
echo "📦 步骤 2/4: 回滚代码..."
git checkout main

# 撤销最后一次合并提交（如果是合并）
if git log -1 --pretty=%B | grep -q "Merge"; then
    git revert -m 1 HEAD --no-edit
    git push origin main
else
    git revert HEAD --no-edit
    git push origin main
fi
echo "✅ 代码已回滚"

# 4. 恢复数据库
echo ""
echo "🗄️  步骤 3/4: 恢复数据库..."
BACKUP_FILE=$(ls -t backups/backup_*.sql.gz 2>/dev/null | head -1)
if [ -n "$BACKUP_FILE" ]; then
    ./scripts/restore-db.sh "$BACKUP_FILE"
else
    echo "⚠️  未找到备份文件！数据库未恢复。"
fi

# 5. 重新部署旧版本
echo ""
echo "🐳 步骤 4/4: 重新部署..."
cd docker
docker compose up -d --build

echo ""
echo "⏳ 等待服务启动..."
sleep 10

echo ""
echo "🔍 验证服务..."
if curl -s http://localhost:8000 >/dev/null 2>&1; then
    echo "✅ 服务已恢复"
else
    echo "⚠️  服务未响应，请检查日志: docker compose logs"
fi

echo ""
echo "✅ 回滚完成"
echo ""
echo "📱 请验证: http://localhost:5173"
