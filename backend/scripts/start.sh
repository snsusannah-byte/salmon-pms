#!/bin/bash
# 一键启动 Salmon PMS 后端

cd "$(dirname "$0")/.."
source .venv/bin/activate

export DATABASE_URL="postgresql+asyncpg://salmon:001978@localhost:5432/salmon_pms"
export SALMON_ENV=development

# 清理旧进程
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 1

# 启动
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
