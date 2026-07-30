#!/bin/bash
set -e

# 获取当前 WSL2 IP，并同步 Windows 端口转发
WSL_IP=$(ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
NETSH="/mnt/c/Windows/System32/netsh.exe"

if [ -n "$WSL_IP" ]; then
    $NETSH interface portproxy delete v4tov4 listenport=4100 listenaddress=0.0.0.0 >/dev/null 2>&1 || true
    $NETSH interface portproxy delete v4tov4 listenport=8000 listenaddress=0.0.0.0 >/dev/null 2>&1 || true
    $NETSH interface portproxy add v4tov4 listenport=4100 listenaddress=0.0.0.0 connectport=4100 connectaddress="$WSL_IP" >/dev/null 2>&1 || true
    $NETSH interface portproxy add v4tov4 listenport=8000 listenaddress=0.0.0.0 connectport=8000 connectaddress="$WSL_IP" >/dev/null 2>&1 || true
fi

# 清理旧进程（防止重复启动）
pkill -f 'uvicorn app.main:app --host 0.0.0.0 --port 8000' 2>/dev/null || true
pkill -f 'pnpm run dev' 2>/dev/null || true

sleep 2

# 启动后端（nohup 忽略 SIGHUP，关闭窗口后仍可继续运行）
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend
nohup ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  >> /tmp/salmon-backend.log 2>&1 &

sleep 3

# 启动前端
export PATH=/home/sannah/.nvm/versions/node/v22.22.2/bin:$PATH
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/frontend
nohup /home/sannah/.nvm/versions/node/v22.22.2/bin/pnpm run dev \
  >> /tmp/salmon-frontend.log 2>&1 &

sleep 3

# 写入 PID，方便后续管理
pgrep -f 'uvicorn app.main:app --host 0.0.0.0 --port 8000' > /tmp/salmon-pms.pids 2>/dev/null || true
pgrep -f 'pnpm run dev' >> /tmp/salmon-pms.pids 2>/dev/null || true

echo "salmon-pms started, PIDs: $(cat /tmp/salmon-pms.pids 2>/dev/null | tr '\n' ' ')"
# 脚本立即退出，后台进程由 nohup 接管，不会随窗口关闭而被杀掉
exit 0
