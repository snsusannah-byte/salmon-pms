#!/bin/bash
# Salmon PMS 环境切换脚本

ENV=$1

if [ "$ENV" = "dev" ]; then
    echo "🔄 切换到开发环境..."
    
    # 停止生产容器
    echo "🛑 停止生产容器..."
    cd "$(dirname "$0")/../docker" && docker compose down 2>/dev/null || true
    
    # 杀死可能的残留进程
    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    echo "✅ 生产环境已停止"
    echo ""
    echo "💡 开发环境启动命令:"
    echo "   后端: cd backend && source .venv/bin/activate && uvicorn app.main:app --reload"
    echo "   前端: cd frontend && pnpm dev"
    
elif [ "$ENV" = "prod" ]; then
    echo "🔄 切换到生产环境..."
    
    # 停止开发服务
    echo "🛑 停止开发服务..."
    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    # 启动生产容器
    echo "🚀 启动生产容器..."
    cd "$(dirname "$0")/../docker"
    docker compose up -d --build
    
    echo "✅ 生产环境已启动"
    echo ""
    echo "💡 访问地址:"
    echo "   前端: http://localhost:5173"
    echo "   后端: http://localhost:8000"
    
else
    echo "用法: $0 [dev|prod]"
    echo ""
    echo "  dev  - 切换到开发环境（本地运行，适合开发新功能）"
    echo "  prod - 切换到生产环境（Docker运行，正式使用）"
    exit 1
fi
