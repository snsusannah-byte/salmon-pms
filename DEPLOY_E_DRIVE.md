# ============================================================
# Salmon PMS — 本机 E 盘局域网部署完整方案
# ============================================================

## 一、适用场景

- **只有一台电脑**：Windows + WSL2（Ubuntu）
- **数据存 E 盘**：PostgreSQL/Redis/MinIO 数据都落到 E 盘，重装系统不丢数据
- **局域网共享**：办公室/家里其他电脑、手机通过浏览器访问
- **边开发边部署**：开发继续在 `/home/sannah/.../salmon-pms`，部署自动用最新代码构建

## 二、整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Windows 电脑（宿主机）                         │
│  E:\salmon-pms-deploy\                                               │
│  ├── data\                                                           │
│  │   ├── postgres\          ← 数据库文件（重装不丢）                  │
│  │   ├── redis\             ← 缓存数据                               │
│  │   ├── minio\             ← 上传的文件/图片                         │
│  │   └── backups\           ← 自动备份                               │
│  ├── docker-compose.e-drive.yml                                      │
│  └── .env                      ← 生产环境变量（不提交Git）             │
│                                                                      │
│  ┌──────────────────────┐     ┌────────────────────────────────────┐ │
│  │   WSL2 (Ubuntu)      │     │    Docker Desktop                  │ │
│  │                      │◄────│    WSL2 Backend                    │ │
│  │  /mnt/e/salmon-pms   │     │                                    │ │
│  │    -deploy/data      │     │  ┌────────┐  ┌────────┐  ┌──────┐ │ │
│  │                      │     │  │ nginx  │  │backend │  │  PG  │ │ │
│  │  开发目录（原目录）   │     │  │  :80   │  │ :8000  │  │:5432 │ │ │
│  │  /home/sannah/...    │     │  └───┬────┘  └───┬────┘  └──┬───┘ │ │
│  │    /salmon-pms       │     │      │           │          │      │ │
│  │      ← 继续开发       │     │      └───────────┴──────────┘      │ │
│  └──────────────────────┘     └────────────────────────────────────┘ │
│                                        │                             │
│                    http://192.168.x.x    │                             │
│              ┌─────────────────────────┘                             │
│              ▼                                                       │
│    ┌──────────────────┐  ┌──────────────────┐                      │
│    │  局域网其他电脑   │  │  手机/平板        │                      │
│    │  浏览器访问      │  │  浏览器访问       │                      │
│    └──────────────────┘  └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 三、要做的配置（按步骤）

### 步骤 1：E 盘创建部署目录

**在 Windows 资源管理器里**：
1. 打开 E 盘
2. 新建文件夹 `salmon-pms-deploy`
3. 在里面再建 `data\postgres`、`data\redis`、`data\minio`、`data\backups`

或者在 WSL2 终端里：

```bash
mkdir -p /mnt/e/salmon-pms-deploy/data/{postgres,redis,minio,backups}
```

### 步骤 2：复制/创建部署文件到 E 盘

```bash
cd /mnt/e/salmon-pms-deploy

# 1. 复制编排文件
cp /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/docker/docker-compose.e-drive.yml ./docker-compose.yml

# 2. 复制环境变量模板
cp /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/docker/.env.example ./.env

# 3. 编辑 .env（下面有详细说明）
nano .env
```

### 步骤 3：配置 `.env` 环境变量

```bash
# === 数据库 ===
POSTGRES_USER=salmon
POSTGRES_PASSWORD=你的强密码
POSTGRES_DB=salmon_pms
DATABASE_URL=postgresql+asyncpg://salmon:你的强密码@db:5432/salmon_pms

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === MinIO ===
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=salmon
MINIO_SECRET_KEY=你的强密码
MINIO_BUCKET=salmon-pms

# === 安全 ===
# 生成命令：openssl rand -hex 32
SECRET_KEY=随机生成的32位十六进制

# === 调试 ===
DEBUG=false

# === CORS ===
# 填入本机 Windows 的局域网 IP（下面会讲怎么查）
# 示例：CORS_ORIGINS=["http://192.168.1.5","http://localhost","http://127.0.0.1"]
CORS_ORIGINS=["http://localhost","http://127.0.0.1"]

# === 构建路径 ===
# 指向你当前的开发目录，Docker 构建时从那里拿代码
BACKEND_CONTEXT=/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend
FRONTEND_CONTEXT=/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/frontend
```

### 步骤 4：Windows 防火墙放行 80 端口

**打开 Windows PowerShell（管理员权限）**，执行：

```powershell
# 放行入站 80 端口（HTTP）
New-NetFirewallRule -DisplayName "Salmon PMS HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow

# 如果以后用 HTTPS，也放行 443
# New-NetFirewallRule -DisplayName "Salmon PMS HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow

# 查看规则是否添加成功
Get-NetFirewallRule -DisplayName "Salmon PMS*"
```

### 步骤 5：启动部署服务

```bash
cd /mnt/e/salmon-pms-deploy

# 首次启动（构建镜像 + 启动）
docker compose up --build -d

# 查看状态
docker compose ps

# 查看日志
docker compose logs -f

# 等 30 秒后测试
# 在浏览器打开 http://localhost（本机测试）
```

### 步骤 6：获取本机局域网 IP，更新 CORS

**在 Windows 命令提示符里**：

```cmd
ipconfig
```

找到类似这样的输出：
```
无线局域网适配器 WLAN:
   IPv4 地址 . . . . . . . . . . . . : 192.168.1.5
```

这个 `192.168.1.5` 就是你的局域网 IP。**更新 `.env`**：

```bash
CORS_ORIGINS=["http://192.168.1.5","http://localhost","http://127.0.0.1"]
```

然后重启后端：

```bash
cd /mnt/e/salmon-pms-deploy
docker compose restart backend
```

### 步骤 7：局域网其他设备访问

在其他电脑/手机的浏览器里输入：

```
http://192.168.1.5
```

（把 `192.168.1.5` 换成你实际的 IP）

## 四、开发 vs 部署的工作流程

### 日常开发（原目录不变）

```bash
# 继续在你现在的目录开发
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms

# 前端开发
pnpm dev          # http://localhost:5173

# 后端开发（如需本地测试）
cd backend && uvicorn app.main:app --reload

# 开发完成，提交代码
git add .
git commit -m "feat: xxx"
git push origin main
```

### 部署更新（E 盘）

```bash
cd /mnt/e/salmon-pms-deploy

# 重新构建并启动（会自动拉取最新代码）
docker compose up --build -d

# 或者只重启某个服务
docker compose restart backend
docker compose restart frontend
```

## 五、WSL2 网络优化（可选但推荐）

### 方案 A：启用 WSL2 Mirrored 网络模式（WSL 2.0+）

这个模式让 WSL2 和 Windows **共享同一个 IP**，网络访问更直接。

**在 Windows 用户目录下创建 `.wslconfig`**：

```
C:\Users\你的用户名\.wslconfig
```

内容：

```ini
[wsl2]
# 启用镜像网络模式（WSL2 和 Windows 共享 IP）
networkingMode=mirrored

# 内存限制（防止 WSL2 吃光内存）
memory=8GB
processors=4

# 自动释放未使用的内存
autoMemoryReclaim=gradual

# localhost 转发（Docker 端口可以直接通过 Windows IP 访问）
localhostForwarding=true
```

然后重启 WSL：

```powershell
# 在 PowerShell 里执行
wsl --shutdown
# 重新打开 WSL 终端
```

启用后：
- 局域网设备直接通过 Windows IP 访问
- 不再需要 `0.0.0.0` 特殊处理
- Windows 防火墙规则直接生效

### 方案 B：Windows 端口转发（兼容所有 WSL 版本）

如果不用 mirrored 模式，可以手动配置端口转发：

```powershell
# 在管理员 PowerShell 里执行
# 把 Windows 的 80 端口转发到 WSL2 的 localhost:80
$wslIp = (wsl hostname -I).Trim().Split()[0]
netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=80 connectaddress=127.0.0.1

# 查看转发规则
netsh interface portproxy show all

# 删除规则（如需）
# netsh interface portproxy delete v4tov4 listenport=80 listenaddress=0.0.0.0
```

> 注意：WSL2 IP 每次重启会变，mirrored 模式更稳定。

## 六、数据备份

### 自动备份脚本

```bash
# 创建备份脚本
cat > /mnt/e/salmon-pms-deploy/backup.sh << 'EOF'
#!/bin/bash
set -e
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/mnt/e/salmon-pms-deploy/data/backups/$DATE"
mkdir -p "$BACKUP_DIR"

# 备份数据库
docker exec $(docker ps -q -f name=salmon-pms-deploy-db-1) pg_dump -U salmon -d salmon_pms | gzip > "$BACKUP_DIR/db.sql.gz"

# 备份 Redis
docker cp $(docker ps -q -f name=salmon-pms-deploy-redis-1):/data/dump.rdb "$BACKUP_DIR/redis.rdb"

# 备份 MinIO
tar czf "$BACKUP_DIR/minio.tar.gz" -C /mnt/e/salmon-pms-deploy/data minio

echo "备份完成: $BACKUP_DIR"
EOF
chmod +x /mnt/e/salmon-pms-deploy/backup.sh
```

### 定时备份

```bash
# 添加到 crontab（每天凌晨 2 点备份）
crontab -e

0 2 * * * /mnt/e/salmon-pms-deploy/backup.sh >> /mnt/e/salmon-pms-deploy/data/backups/backup.log 2>&1

# 保留最近 30 天备份（添加到 crontab）
0 3 * * * find /mnt/e/salmon-pms-deploy/data/backups -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;
```

## 七、常见问题

### Q1：浏览器访问 `http://192.168.1.x` 显示 "拒绝连接"

排查：
1. Windows 防火墙是否放行了 80 端口？
2. `docker compose ps` 看看 frontend 是否 running
3. `docker compose logs frontend` 看前端日志
4. 试试本机 `http://localhost` 能否访问

### Q2：E 盘的数据库性能慢

WSL2 访问 Windows 挂载点（`/mnt/e/`）比原生 ext4 慢，但对于小型系统够用。如果数据量大了，可以：
- 把 PostgreSQL 数据移到 WSL2 的 ext4 分区（比如 `/var/lib/postgres-data`），但重装 WSL 会丢
- 或者保持 E 盘，增加 SSD 缓存

### Q3：WSL2 重启后 IP 变了

如果启用了 mirrored 模式（`.wslconfig`），IP 不会变。
如果没启用，每次 WSL2 重启后可能需要更新 CORS_ORIGINS。

### Q4：如何停止所有部署服务？

```bash
cd /mnt/e/salmon-pms-deploy
docker compose down
```

数据不会丢（因为映射到了 E 盘），下次 `docker compose up -d` 直接恢复。

### Q5：开发时修改了数据库结构（Alembic 迁移），部署怎么办？

```bash
# 进入后端容器执行迁移
cd /mnt/e/salmon-pms-deploy
docker exec -it $(docker ps -q -f name=backend) bash
# 在容器里执行 alembic upgrade head
```

或者更简单：开发时先在开发环境跑完迁移，部署时数据库已经是最新结构。

## 八、一键启动/停止脚本

### `start.sh`

```bash
#!/bin/bash
cd /mnt/e/salmon-pms-deploy
echo "启动 Salmon PMS..."
docker compose up --build -d
echo "等待服务就绪..."
sleep 10
echo "本机访问: http://localhost"
echo "局域网访问: http://$(hostname -I | awk '{print $1}')"
```

### `stop.sh`

```bash
#!/bin/bash
cd /mnt/e/salmon-pms-deploy
docker compose down
echo "Salmon PMS 已停止，数据保存在 E 盘"
```

### `update.sh`（开发后更新部署）

```bash
#!/bin/bash
cd /mnt/e/salmon-pms-deploy
echo "更新 Salmon PMS..."

# 备份（可选）
# bash backup.sh

# 重新构建
docker compose up --build -d

echo "更新完成"
```

## 九、配置清单总结

| 配置项 | 位置 | 说明 |
|--------|------|------|
| E 盘部署目录 | `E:\salmon-pms-deploy\` | 数据和编排文件 |
| Docker Compose | `E:\salmon-pms-deploy\docker-compose.yml` | 服务编排 |
| 环境变量 | `E:\salmon-pms-deploy\.env` | 密码、密钥、CORS |
| 数据库数据 | `E:\salmon-pms-deploy\data\postgres\` | 重装系统不丢 |
| 上传文件 | `E:\salmon-pms-deploy\data\minio\` | 附件/图片 |
| 自动备份 | `E:\salmon-pms-deploy\data\backups\` | 每天2点执行 |
| Windows 防火墙 | PowerShell 命令 | 放行 80 端口 |
| WSL2 网络优化 | `C:\Users\用户名\.wslconfig` | 可选 mirrored 模式 |
| 开发目录 | 原目录不变 | `/home/sannah/.../salmon-pms` |

## 十、关键命令速查

```bash
# ── 启动 ──
cd /mnt/e/salmon-pms-deploy && docker compose up --build -d

# ── 停止 ──
cd /mnt/e/salmon-pms-deploy && docker compose down

# ── 查看状态 ──
cd /mnt/e/salmon-pms-deploy && docker compose ps

# ── 查看日志 ──
cd /mnt/e/salmon-pms-deploy && docker compose logs -f frontend
cd /mnt/e/salmon-pms-deploy && docker compose logs -f backend

# ── 重启单个服务 ──
cd /mnt/e/salmon-pms-deploy && docker compose restart backend

# ── 进入数据库 ──
docker exec -it $(docker ps -q -f name=db) psql -U salmon -d salmon_pms

# ── 手动备份 ──
cd /mnt/e/salmon-pms-deploy && bash backup.sh

# ── 清理旧备份（保留30天）──
find /mnt/e/salmon-pms-deploy/data/backups -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;

# ── 查看磁盘占用 ──
du -sh /mnt/e/salmon-pms-deploy/data/*
```

---

*文档版本: 2026-05-27*
*适用: Windows + WSL2 + Docker Desktop 环境*
