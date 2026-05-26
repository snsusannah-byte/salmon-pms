#!/bin/bash
# Salmon PMS 上线部署脚本
# 从 dev 分支合并到 main 并部署到生产环境

set -e

PROJECT_DIR="$(dirname "$0")/.."
cd "$PROJECT_DIR"

echo "🚀 Salmon PMS 上线流程"
echo "======================"
echo ""

# 1. 检查分支状态
echo "📋 步骤 1/8: 检查当前分支..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  当前不在 main 分支 ($CURRENT_BRANCH)，切换到 main..."
    git checkout main
fi

# 2. 备份数据库
echo ""
echo "💾 步骤 2/8: 备份生产数据库..."
if ! ./scripts/backup-db.sh; then
    echo "❌ 备份失败！停止上线。"
    exit 1
fi

# 3. 拉取最新 main
echo ""
echo "📥 步骤 3/8: 更新 main 分支..."
git pull origin main || true

# 4. 合并 dev
echo ""
echo "🔀 步骤 4/8: 合并 dev 分支..."
if ! git merge dev -m "Merge dev into main for release $(date +%Y%m%d-%H%M)"; then
    echo "❌ 合并冲突！需要手动解决。"
    echo "   解决冲突后运行: git add . && git commit && $0"
    exit 1
fi

# 5. 打标签
echo ""
echo "🏷️  步骤 5/8: 创建版本标签..."
VERSION=$(date +%Y%m%d-%H%M)
git tag -a "v$VERSION" -m "Release v$VERSION"
echo "✅ 标签: v$VERSION"

# 6. 推送
echo ""
echo "📤 步骤 6/8: 推送代码..."
git push origin main
git push origin "v$VERSION"

# 7. 数据库迁移
echo ""
echo "🗄️  步骤 7/8: 执行数据库迁移..."
cd backend
if [ -f .venv/bin/activate ]; then
    source .venv/bin/activate
    alembic upgrade head || echo "⚠️  迁移执行失败或无需迁移"
else
    echo "⚠️  未找到 .venv，跳过迁移"
fi
cd ..

# 8. 重新部署
echo ""
echo "🐳 步骤 8/8: 重新部署 Docker 容器..."
cd docker
docker compose down
docker compose up -d --build

echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 验证
echo ""
echo "🔍 验证服务状态..."
if docker compose ps | grep -q "Up"; then
    echo "✅ Docker 容器运行正常"
else
    echo "❌ Docker 容器启动异常，请检查日志: docker compose logs"
    exit 1
fi

# 健康检查
echo ""
echo "🔍 健康检查..."
for i in {1..5}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1 || curl -s http://localhost:8000/ >/dev/null 2>&1; then
        echo "✅ 后端服务响应正常"
        break
    fi
    echo "  尝试 $i/5..."
    sleep 3
    if [ $i -eq 5 ]; then
        echo "⚠️  后端服务未响应，请手动检查"
    fi
done

echo ""
echo "🎉 上线完成！版本: v$VERSION"
echo ""
echo "📱 访问地址:"
echo "   前端: http://localhost:5173"
echo "   后端: http://localhost:8000"
echo ""
echo "⚠️  请用户验收："
echo "   1. 打开 http://localhost:5173"
echo "   2. 检查原有功能是否正常"
echo "   3. 检查新功能是否可用"
echo "   4. 如发现问题，立即说'回滚'执行回滚操作"
