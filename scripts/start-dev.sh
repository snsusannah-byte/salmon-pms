#!/bin/bash
set -e

echo "=== Salmon PMS 开发环境启动 ==="

# 启动基础设施
echo "[1/3] 启动 Docker 基础设施 (PostgreSQL, Redis, MinIO)..."
cd "$(dirname "$0")/../docker"
docker-compose up -d db redis minio

# 等待 PostgreSQL 就绪
echo "等待 PostgreSQL 就绪..."
until docker-compose exec -T db pg_isready -U salmon -d salmon_pms > /dev/null 2>&1; do
  sleep 1
done

echo "[2/3] 启动后端 (FastAPI)..."
cd "$(dirname "$0")/../backend"
# 创建虚拟环境（如不存在）
if [ ! -d ".venv" ]; then
  uv venv
fi
source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000 &

echo "[3/3] 启动前端 (Vite)..."
cd "$(dirname "$0")/../frontend"
pnpm install
pnpm dev &

echo ""
echo "=== 服务地址 ==="
echo "前端: http://localhost:5173"
echo "后端: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo "MinIO 控制台: http://localhost:9001"
echo ""
echo "按 Ctrl+C 停止所有服务"
wait
