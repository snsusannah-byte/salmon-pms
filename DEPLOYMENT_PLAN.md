# Salmon PMS 局域网生产部署实施方案

> **针对当前环境定制** | 生成时间: 2026-06-01
> **目标**: 从 WSL2 开发模式 → Docker 生产容器，局域网内任何设备通过浏览器访问

---

## 一、当前环境分析

| 项目 | 现状 |
|------|------|
| 开发机 | Windows + WSL2 (Linux 5.10.16.3-microsoft-standard-WSL2) |
| 后端运行 | 裸机 uvicorn（PID 5198，192.168.201.144:8000） |
| 前端运行 | vite dev（192.168.201.144:5173） |
| 数据库 | PostgreSQL（localhost:5432，已有生产数据） |
| 缓存 | Redis（localhost:6379） |
| 代码管理 | Git 仓库，大量未提交变更 |
| 现有 Docker 文件 | `backend/Dockerfile.prod`、`frontend/Dockerfile`、`docker/docker-compose*.yml` |

### ⚠️ 部署前必须处理的事项

1. **未提交代码** — 当前 workspace 有 ~50 个 modified/untracked 文件，部署前需提交
2. **Dockerfile.prod 构建隐患** — `uv pip install --system -e "."` 缺少 `build-system` 声明，可能构建失败
3. **数据迁移** — 开发环境 PostgreSQL 已有生产数据，需导出/导入
4. **MinIO** — 当前 .env 中没有 MinIO 配置，需确认是否在用（看代码中有 minio endpoint 变量）

---

## 二、部署架构选型

推荐 **方案 A：单台 WSL2 Docker 部署**（最省事，零额外硬件）

```
局域网设备 (手机/平板/其他电脑)
         │
         ▼ http://192.168.x.x:80
┌─────────────────────────────────────┐
│        当前 WSL2 机器                │
│                                     │
│  ┌─────────┐   proxy_pass        │
│  │ nginx   │ ──────────────────►  │
│  │  :80    │   /api/*             │
│  │         │   /uploads/*         │
│  │         │ ◄── / (静态文件)     │
│  └────┬────┘                      │
│       │                           │
│       │ Docker 内部网络           │
│       │                           │
│  ┌────┴────┐  ┌────────┐ ┌──────┐ │
│  │ backend │  │  PG    │ │Redis │ │
│  │ :8000   │  │ :5432  │ │:6379 │ │
│  └─────────┘  └────────┘ └──────┘ │
│                                     │
│  数据卷: ./data/postgres            │
│         ./data/redis                │
│         ./data/minio                │
│         ./data/backups              │
└─────────────────────────────────────┘
```

### 为什么不推荐「开发机 + 部署机」双机方案？

- 额外需要一台常年开机的 Linux 机器
- Git 同步、SSH 密钥、网络发现增加复杂度
- 当前场景下单机 Docker 完全够用，后期随时可迁移

---

## 三、实施步骤（按顺序执行）

### Step 0 — 前置检查清单

```bash
# 0.1 确认 Docker 已安装
docker --version          # 应 >= 24.x
docker compose version    # 应 >= 2.x

# 0.2 确认 PostgreSQL 可导出
pg_dump --version

# 0.3 确认 WSL2 内存充足（建议 >= 4GB）
free -h

# 0.4 确认 WSL2 防火墙/端口转发
# Windows PowerShell (管理员):
# netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=80 connectaddress=<WSL2_IP>
```

### Step 1 — 代码提交与清理

```bash
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms

# 1.1 先备份当前 workspace（以防万一）
tar czf ~/salmon-pms-pre-deploy-$(date +%Y%m%d).tar.gz \
  --exclude='*/node_modules' --exclude='*/.venv' \
  --exclude='*/dist' .

# 1.2 提交所有变更
git add -A
git commit -m "chore: pre-deploy checkpoint $(date +%Y-%m-%d)"

# 1.3 打版本标签
git tag -a "v$(date +%Y%m%d)" -m "生产部署版本"
```

### Step 2 — 修复 Dockerfile.prod 构建问题

**当前问题**：`pyproject.toml` 缺少 `[build-system]` 段，`uv pip install --system -e "."` 可能失败。

**修复** — 修改 `backend/Dockerfile.prod`：

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装 uv + setuptools（pyproject.toml 依赖 setuptools 构建）
RUN pip install uv setuptools wheel

# 复制依赖文件
COPY pyproject.toml ./

# 安装生产依赖（非 editable 模式更稳定）
RUN uv pip install --system .

# 复制应用代码
COPY . .

EXPOSE 8000

# 生产模式：4 个 worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Step 3 — 创建生产环境文件

**3.1 创建 `docker/.env.prod`**（不提交 Git）：

```bash
# === 数据库（Docker 内部网络）===
POSTGRES_USER=salmon
POSTGRES_PASSWORD=$(openssl rand -hex 16)   # 生成强密码，记下来
POSTGRES_DB=salmon_pms
DATABASE_URL=postgresql+asyncpg://salmon:<上面密码>@db:5432/salmon_pms

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === MinIO ===
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=salmon
MINIO_SECRET_KEY=$(openssl rand -hex 16)
MINIO_BUCKET=salmon-pms

# === 安全 ===
SECRET_KEY=$(openssl rand -hex 32)
DEBUG=false

# === CORS ===
# 填入所有可能访问的 IP（部署机 WSL2 IP + Windows IP + localhost）
CORS_ORIGINS=["http://192.168.201.144","http://localhost","http://127.0.0.1"]

# === 构建 ===
BUILD_DATE=2026-06-01
```

**3.2 生成密码并保存**（在 WSL2 执行）：

```bash
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms

# 生成密码
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
echo "MINIO_SECRET_KEY=$(openssl rand -hex 16)"
echo "SECRET_KEY=$(openssl rand -hex 32)"

# 把上面输出填入 docker/.env.prod，然后：
chmod 600 docker/.env.prod
```

### Step 4 — 数据导出（从开发 PostgreSQL）

```bash
# 4.1 导出当前数据库
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms
mkdir -p data/backups
pg_dump -h localhost -U salmon -d salmon_pms -Fc > data/backups/prod_init.dump

# 4.2 如果 pg_dump 提示密码，设置环境变量或 ~/.pgpass
# 或直接用：
# PGPASSWORD='001978' pg_dump -h localhost -U salmon -d salmon_pms -Fc > data/backups/prod_init.dump

# 4.3 确认导出成功
ls -lh data/backups/prod_init.dump
```

### Step 5 — 启动 Docker 生产环境

```bash
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/docker

# 5.1 首次启动（只启动 DB + Redis，不启动应用）
docker compose -f docker-compose.prod.yml up -d db redis minio

# 5.2 等待 PG 就绪（约 10 秒）
sleep 10

# 5.3 导入数据到 Docker PG
# 先找到 db 容器名
DB_CONTAINER=$(docker ps -q -f name=salmon-pms-db)

# 复制 dump 进容器
docker cp ../data/backups/prod_init.dump $DB_CONTAINER:/tmp/

# 进入容器导入
docker exec -it $DB_CONTAINER bash
pg_restore -U salmon -d salmon_pms /tmp/prod_init.dump --no-owner --no-privileges
# 如果报错说 database 不存在，先创建：
# createdb -U salmon salmon_pms
# 再重新导入

# 5.4 验证数据
docker exec $DB_CONTAINER psql -U salmon -d salmon_pms -c "SELECT count(*) FROM batches;"

# 5.5 启动完整服务
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/docker
docker compose -f docker-compose.prod.yml up --build -d

# 5.6 健康检查
sleep 10
curl http://localhost/health
curl http://localhost/api/v1/dashboard
```

### Step 6 — 配置 Windows 端口转发

WSL2 的 Docker 容器监听的是 WSL2 内部的端口，局域网其他设备访问的是 Windows 主机的 IP。需要把 Windows 的 80 端口转发到 WSL2。

**在 Windows PowerShell (管理员)** 执行：

```powershell
# 6.1 查看 WSL2 IP
wsl hostname -I
# 假设输出：192.168.201.144

# 6.2 添加端口转发（将 Windows 所有网卡的 80 转发到 WSL2 的 80）
netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=80 connectaddress=192.168.201.144

# 6.3 配置 Windows 防火墙允许 80 端口入站
New-NetFirewallRule -DisplayName "Salmon-PMS-HTTP" -Direction Inbound -LocalPort 80 -Protocol TCP -Action Allow

# 6.4 验证
netsh interface portproxy show all
```

### Step 7 — 局域网访问测试

```bash
# 7.1 在 WSL2 内部测试
curl http://localhost/
curl http://localhost/api/v1/dashboard

# 7.2 在 Windows 上测试（浏览器或 PowerShell）
# http://localhost
# http://192.168.201.144

# 7.3 在手机/其他电脑上测试
# http://<Windows_实际局域网IP>
# Windows IP 查看：ipconfig | findstr "IPv4"
```

---

## 四、运维流程

### 4.1 一键更新脚本（部署后使用）

当前 `scripts/deploy.sh` 路径假设部署目录为 `/srv/salmon-pms`，需要改为 WSL2 实际路径。

创建 `scripts/deploy-wsl2.sh`：

```bash
#!/bin/bash
set -e

DEPLOY_DIR="/home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms"
COMPOSE_FILE="$DEPLOY_DIR/docker/docker-compose.prod.yml"

echo "[$(date)] 开始更新..."

cd "$DEPLOY_DIR"

# 拉取最新代码
git pull origin main 2>/dev/null || echo "未配置远程仓库，使用本地代码"

# 备份数据库
docker exec $(docker ps -q -f name=db) pg_dump -U salmon -d salmon_pms | gzip > \
  "$DEPLOY_DIR/data/backups/auto_$(date +%Y%m%d_%H%M%S).sql.gz"

# 重建并重启
docker compose -f "$COMPOSE_FILE" down
docker compose -f "$COMPOSE_FILE" up --build -d

# 等待就绪
sleep 10
curl -sf http://localhost/health && echo "✅ 更新成功" || echo "❌ 健康检查失败"
```

```bash
chmod +x scripts/deploy-wsl2.sh
```

### 4.2 自动备份

```bash
# 添加到 crontab（WSL2 需先安装并启动 cron）
crontab -e

# 每天凌晨 3 点自动备份
0 3 * * * /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/scripts/backup.sh /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/data/backups >> /tmp/salmon-backup.log 2>&1
```

### 4.3 日常命令速查

```bash
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/docker

# 查看所有服务状态
docker compose -f docker-compose.prod.yml ps

# 查看后端日志（实时）
docker compose -f docker-compose.prod.yml logs -f backend

# 查看前端日志
docker compose -f docker-compose.prod.yml logs -f frontend

# 重启后端
docker compose -f docker-compose.prod.yml restart backend

# 进入数据库
docker exec -it $(docker ps -q -f name=db) psql -U salmon -d salmon_pms

# 进入后端容器（临时调试）
docker exec -it $(docker ps -q -f name=backend) bash

# 查看资源占用
docker stats
```

### 4.4 数据库迁移（Alembic）

如果后续代码有数据库迁移脚本：

```bash
# 进入后端容器执行迁移
docker exec -it $(docker ps -q -f name=backend) bash
# 容器内：
alembic upgrade head
exit
```

---

## 五、已知问题与对策

| 问题 | 对策 |
|------|------|
| WSL2 重启后 IP 变化 | 使用 `localhost` 访问或重新配置端口转发；长期方案建议给 WSL2 设固定 IP |
| Windows 重启后 Docker 不自动启动 | 设置 Docker Desktop "Start Docker Desktop when you log in" |
| `uv pip install` 构建失败 | 已修复：Dockerfile.prod 增加 `setuptools wheel` 安装 |
| CORS 拒绝 | 更新 `docker/.env.prod` 中的 `CORS_ORIGINS`，加入访问者 IP |
| 数据丢失风险 | 数据卷映射到 `./data/`（宿主机目录），容器删除不影响数据 |
| 备份脚本找不到容器 | 脚本使用 `docker ps -q -f name=db` 匹配，确保 compose 中服务名一致 |

---

## 六、文件变更清单

执行本方案会修改/创建以下文件：

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/Dockerfile.prod` | 修改 | 增加 setuptools/wheel，改为非 editable 安装 |
| `docker/.env.prod` | 新建 | 生产环境变量（不提交 Git） |
| `docker/docker-compose.prod.yml` | 复用 | 已有，路径需确认 |
| `scripts/deploy-wsl2.sh` | 新建 | WSL2 专用更新脚本 |
| `data/backups/` | 自动创建 | 备份数据存放 |
| `data/postgres/` | 自动创建 | PG 数据卷 |
| `data/redis/` | 自动创建 | Redis 数据卷 |

---

## 七、回滚方案

如果部署失败，最快恢复方式：

```bash
# 1. 停止 Docker 服务
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/docker
docker compose -f docker-compose.prod.yml down

# 2. 恢复裸机后端（原来的方式）
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# 3. 前端恢复开发模式
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/frontend
pnpm dev --host
```

> PostgreSQL 数据在 Docker 和裸机是两套独立的，回滚到裸机不影响。

---

*方案版本: 2026-06-01-v1*
*下一步: 用户确认方案后，按 Step 1-7 顺序执行*
