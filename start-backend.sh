#!/bin/bash
# Salmon PMS 后端启动脚本
# 用法: bash start-backend.sh

cd "$(dirname "$0")/../backend"
source .venv/bin/activate
export DATABASE_URL="postgresql+asyncpg://salmon:001978@localhost:5432/salmon_pms"
export SALMON_ENV=development

# 清理旧进程
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 2

# 启动
echo "Starting Salmon PMS backend..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
