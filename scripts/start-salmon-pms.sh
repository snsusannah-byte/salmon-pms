#!/bin/bash
set -euo pipefail

# Salmon PMS 后端 + 前端一键启动脚本
# 用法: /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/scripts/start-salmon-pms.sh

ROOT_DIR="/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms"
BACKEND_PORT=8000
FRONTEND_PORT=4100
NODE_BIN="/home/sannah/.nvm/versions/node/v22.22.2/bin"
PNPM="$NODE_BIN/pnpm"
LOG_DIR="/tmp"
BOOT_LOG="$LOG_DIR/salmon-pms-boot.log"
BACKEND_LOG="$LOG_DIR/salmon-backend.log"
FRONTEND_LOG="$LOG_DIR/salmon-frontend.log"
BACKEND_PID="/tmp/salmon-backend.pid"
FRONTEND_PID="/tmp/salmon-frontend.pid"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$BOOT_LOG" >&2
}

log "================================================================"
log "Salmon PMS 启动脚本开始"
log "================================================================"

stop_by_pattern() {
    local pattern="$1"
    local pids
    pids=$(pgrep -f "$pattern" || true)
    if [ -n "$pids" ]; then
        log "发现旧进程 ($pattern)，正在停止: $pids"
        echo "$pids" | xargs -r kill 2>/dev/null || true
        sleep 2
        echo "$pids" | xargs -r kill -9 2>/dev/null || true
    fi
}

# 清理旧进程，避免重复启动
stop_by_pattern "[u]vicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT"
stop_by_pattern "[p]npm run dev"

# 确保端口已释放（pnpm 启动的 node/vite 子进程可能残留）
for P in $BACKEND_PORT $FRONTEND_PORT; do
    if ss -tlnp 2>/dev/null | grep -q ":$P "; then
        log "端口 $P 仍被占用，强制释放..."
        fuser -k "${P}/tcp" 2>/dev/null || true
        sleep 1
    fi
done

# 同步 WSL2 IP 到 Windows 端口转发（best-effort）
WSL_IP=$(ip -4 addr show eth0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || true)
NETSH="/mnt/c/Windows/System32/netsh.exe"
if [ -n "$WSL_IP" ] && [ -x "$NETSH" ]; then
    for P in $BACKEND_PORT $FRONTEND_PORT; do
        $NETSH interface portproxy delete v4tov4 listenport=$P listenaddress=0.0.0.0 >/dev/null 2>&1 || true
        $NETSH interface portproxy add v4tov4 listenport=$P listenaddress=0.0.0.0 connectport=$P connectaddress="$WSL_IP" >/dev/null 2>&1 || true
    done
    log "Windows 端口转发已更新: $WSL_IP"
fi

# 生成临时启动脚本（避免 setsid + bash -c 的引号地狱）
BACK_WRAPPER="/tmp/.start-salmon-backend.sh"
FRONT_WRAPPER="/tmp/.start-salmon-frontend.sh"

cat > "$BACK_WRAPPER" <<EOF
#!/bin/bash
cd "$ROOT_DIR/backend"
source .venv/bin/activate
exec nohup ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload >> "$BACKEND_LOG" 2>&1
EOF

cat > "$FRONT_WRAPPER" <<EOF
#!/bin/bash
cd "$ROOT_DIR/frontend"
export PATH="$NODE_BIN:\$PATH"
exec nohup "$PNPM" run dev >> "$FRONTEND_LOG" 2>&1
EOF

chmod +x "$BACK_WRAPPER" "$FRONT_WRAPPER"

# 启动后端（setsid 创建新会话，避免被 WSL 会话退出时杀掉）
log "启动后端 (FastAPI) ..."
setsid "$BACK_WRAPPER" &
echo $! > "$BACKEND_PID"
sleep 3

# 启动前端
log "启动前端 (Vite) ..."
setsid "$FRONT_WRAPPER" &
echo $! > "$FRONTEND_PID"
sleep 3

# 检查端口是否就绪
for i in {1..15}; do
    if ss -tlnp 2>/dev/null | grep -q ":$BACKEND_PORT " && ss -tlnp 2>/dev/null | grep -q ":$FRONTEND_PORT "; then
        log "✅ Salmon PMS 启动成功"
        log "  - 前端: http://0.0.0.0:$FRONTEND_PORT"
        log "  - 后端: http://0.0.0.0:$BACKEND_PORT"
        log "  - PID: 后端=$(cat "$BACKEND_PID" 2>/dev/null || echo '?'), 前端=$(cat "$FRONTEND_PID" 2>/dev/null || echo '?')"
        exit 0
    fi
    sleep 1
done

log "❌ Salmon PMS 端口未就绪，请查看日志:"
log "  - $BOOT_LOG"
log "  - $BACKEND_LOG"
log "  - $FRONTEND_LOG"
exit 1
