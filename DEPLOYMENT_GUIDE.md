# Salmon PMS 局域网生产部署方案

> **目标**：将 Salmon PMS 部署到局域网内的"部署机"（常年开机），开发机继续开发，通过 Git 同步更新。  
> **适用场景**：小型企业/团队内部使用，无需公网域名和备案。

---

## 一、整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           局域网 (192.168.x.x)                           │
│                                                                          │
│  ┌──────────────┐      HTTP (80)      ┌──────────────────────────────┐    │
│  │   用户电脑    │  ═══════════════►  │      部署机（Docker）         │    │
│  │   手机/平板   │                     │                              │    │
│  │   其他设备    │                     │  ┌────────┐  ┌──────────┐   │    │
│  └──────────────┘                     │  │ nginx  │  │ backend  │   │    │
│                                      │  │  :80   │  │  :8000   │   │    │
│                                      │  └───┬────┘  └────┬─────┘   │    │
│                                      │      │            │         │    │
│  ┌────────────────────────────────┐   │  ┌───┴────────────┴───┐     │    │
│  │      开发机（WSL/Windows）      │   │  │   salmon-net       │     │    │
│  │  /home/sannah/.../salmon-pms   │   │  └────────┬───────────┘     │    │
│  │         Git push ──────────────│───┼───────────┘                 │    │
│  │              ▲                 │   │                              │    │
│  └──────────────┼─────────────────┘   │  ┌────────┐  ┌────────┐      │    │
│                 │                      │  │  PG    │  │ Redis  │      │    │
│              Git pull                 │  │ :5432  │  │ :6379  │      │    │
│                 │                      │  └────────┘  └────────┘      │    │
│  ┌──────────────┼─────────────────┐   │                              │    │
│  │    部署机 Git 仓库              │   │  数据持久化: ./data/          │    │
│  │  /srv/salmon-pms               │   │  自动备份: ./data/backups/    │    │
│  └────────────────────────────────┘   └──────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 角色分工

| 机器 | 角色 | 职责 | 操作系统建议 |
|------|------|------|-------------|
| **部署机** | 生产服务器 | 运行 Docker 容器，提供局域网服务 | Ubuntu 22.04/24.04 LTS |
| **开发机** | 开发工作站 | 代码开发、测试、Git 提交 | Windows + WSL2 / macOS |
| **用户设备** | 客户端 | 浏览器访问系统 | 任意 |

---

## 二、部署机环境准备

### 2.1 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 2核 | 4核+ |
| 内存 | 4GB | 8GB+ |
| 磁盘 | 50GB SSD | 100GB+ SSD |
| 网络 | 千兆局域网 | 千兆局域网 |

### 2.2 系统初始化

```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 安装必要工具
sudo apt install -y curl git vim htop net-tools

# 3. 安装 Docker
# 官方安装脚本
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# 验证
docker --version
docker compose version

# 4. 配置防火墙（仅开放 80 端口，其他端口禁止外网访问）
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 80/tcp
sudo ufw allow 22/tcp   # SSH（如果通过远程管理）
sudo ufw enable

# 5. 设置静态 IP（确保局域网内 IP 不变）
# 编辑 /etc/netplan/00-installer-config.yaml
# 将 DHCP 改为 static，记录 IP 地址（如 192.168.1.100）
```

### 2.3 目录结构

```bash
sudo mkdir -p /srv/salmon-pms
cd /srv/salmon-pms

# 目录结构
/srv/salmon-pms/
├── docker-compose.yml      # 生产编排文件（从仓库拉取）
├── .env                    # 生产环境变量（本地创建，不提交Git）
├── data/                   # 数据持久化目录
│   ├── postgres/           # PostgreSQL 数据
│   ├── redis/              # Redis 数据
│   ├── minio/              # MinIO 对象存储
│   └── backups/            # 自动备份存放
└── scripts/
    ├── deploy.sh           # 一键更新脚本
    └── backup.sh           # 手动备份脚本
```

---

## 三、Git 仓库初始化（关键步骤）

### 3.1 在开发机上，将项目推送到远程仓库

**方案 A：使用 GitHub/GitLab（推荐）**

```bash
# 在开发机上
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms

# 添加远程仓库（如果还没有）
git remote add origin https://github.com/yourusername/salmon-pms.git
# 或 GitLab: git remote add origin https://gitlab.com/yourusername/salmon-pms.git

git add .
git commit -m "chore: 准备生产部署"
git push -u origin main
```

**方案 B：部署机作为裸仓库（纯局域网，无外网）**

```bash
# 在部署机上创建裸仓库
mkdir -p /srv/git
cd /srv/git
git init --bare salmon-pms.git

# 在开发机上添加远程
# 假设部署机局域网 IP 为 192.168.1.100
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms
git remote add deploy ssh://sannah@192.168.1.100/srv/git/salmon-pms.git

git push deploy main
```

### 3.2 在部署机上克隆代码

```bash
cd /srv/salmon-pms

# 方案 A（GitHub）
git clone https://github.com/yourusername/salmon-pms.git .

# 方案 B（局域网裸仓库）
git clone /srv/git/salmon-pms.git .

# 创建生产环境变量文件
cp docker/.env.example .env

# 编辑 .env，修改密码和密钥
nano .env
```

---

## 四、生产环境变量配置（.env）

### 4.1 生成强密码和密钥

```bash
# 在部署机上执行
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)"
echo "MINIO_SECRET_KEY=$(openssl rand -hex 16)"
echo "SECRET_KEY=$(openssl rand -hex 32)"
```

### 4.2 完整的 .env 文件示例

```bash
# === 数据库 ===
POSTGRES_USER=salmon
POSTGRES_PASSWORD=abcd1234efgh5678  # 替换为上面生成的
POSTGRES_DB=salmon_pms
DATABASE_URL=postgresql+asyncpg://salmon:abcd1234efgh5678@db:5432/salmon_pms

# === Redis ===
REDIS_URL=redis://redis:6379/0

# === MinIO ===
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=salmon
MINIO_SECRET_KEY=wxyz9876mnop6543  # 替换为上面生成的
MINIO_BUCKET=salmon-pms

# === 安全 ===
SECRET_KEY=a1b2c3d4e5f6...32位十六进制字符串  # 替换为上面生成的

# === 调试 ===
DEBUG=false

# === CORS ===
# 填入部署机IP和所有可能访问的设备IP
CORS_ORIGINS=["http://192.168.1.100","http://localhost","http://127.0.0.1"]

# === 构建 ===
BUILD_DATE=2026-05-27
```

> ⚠️ **重要**：`.env` 文件已列入 `.gitignore`，不会被提交到 Git。请手动在部署机上创建。

---

## 五、首次部署启动

### 5.1 启动所有服务

```bash
cd /srv/salmon-pms

# 首次启动（会拉取镜像、构建前端、初始化数据库）
docker compose -f docker/docker-compose.prod.yml up --build -d

# 查看日志
docker compose -f docker/docker-compose.prod.yml logs -f

# 等待约 30 秒后检查健康状态
curl http://localhost/health
```

### 5.2 初始化数据库（首次）

```bash
# 运行数据库迁移
# 方案 1：如果后端容器已启动，进入容器执行
docker exec -it $(docker ps -q -f name=salmon-pms-backend) bash
# 在容器内执行 alembic upgrade head（需要安装alembic）

# 方案 2：如果已有现有数据库，直接导入
# docker cp your_dump.sql $(docker ps -q -f name=db):/tmp/
# docker exec $(docker ps -q -f name=db) psql -U salmon -d salmon_pms -f /tmp/your_dump.sql
```

### 5.3 验证部署

```bash
# 检查所有容器状态
docker compose -f docker/docker-compose.prod.yml ps

# 局域网访问测试（在任意电脑浏览器打开）
# http://192.168.1.100  （替换为部署机实际IP）

# 检查后端API
curl http://192.168.1.100/api/v1/dashboard
```

---

## 六、开发与部署同步流程

### 6.1 日常开发流程（开发机）

```bash
# 1. 开发新功能
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms

# 前端开发
pnpm dev          # http://localhost:5173

# 后端开发（如果需要本地启动后端）
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# 2. 开发完成，提交代码
git add .
git commit -m "feat: 新增供应商联想输入功能"
git push origin main
```

### 6.2 部署机更新（两种方式）

**方式 A：手动更新（推荐，可控）**

```bash
# 在部署机上执行
ssh sannah@192.168.1.100
cd /srv/salmon-pms
sudo bash scripts/deploy.sh
```

**方式 B：自动定时更新**

```bash
# 在部署机上添加 crontab
crontab -e

# 每 30 分钟检查一次更新
*/30 * * * * cd /srv/salmon-pms && bash scripts/deploy.sh >> /var/log/salmon-auto-deploy.log 2>&1

# 或者更保守：每天凌晨 3 点自动更新
0 3 * * * cd /srv/salmon-pms && bash scripts/deploy.sh >> /var/log/salmon-auto-deploy.log 2>&1
```

### 6.3 热更新 vs 冷更新

| 场景 | 方式 | 影响 |
|------|------|------|
| 前端小改动 | `deploy.sh` 自动 | 约 30 秒不可用 |
| 后端 API 改动 | `deploy.sh` 自动 | 约 30 秒不可用 |
| 数据库结构改动 | 手动执行迁移 | 需要计划停机窗口 |
| 紧急修复 | 直接修改部署机代码 + 重启 | 快速但不规范 |

---

## 七、数据备份策略

### 7.1 自动备份（强烈推荐）

```bash
# 在部署机上设置定时任务
crontab -e

# 每天凌晨 2 点自动备份
0 2 * * * /srv/salmon-pms/scripts/backup.sh >> /var/log/salmon-backup.log 2>&1

# 每周日凌晨 3 点额外备份到外置硬盘
0 3 * * 0 /srv/salmon-pms/scripts/backup.sh /mnt/external-drive/salmon-backups >> /var/log/salmon-backup-ext.log 2>&1
```

### 7.2 备份文件结构

```
/srv/salmon-pms/data/backups/
├── 20260527_020000/
│   ├── db_salmon_pms.sql.gz      # 数据库（压缩后通常 1-10MB）
│   ├── redis_dump.rdb            # Redis 缓存
│   ├── minio_data.tar.gz         # 上传的文件/图片
│   └── backup_manifest.json      # 备份清单
├── 20260528_020000/
│   └── ...
└── ...
```

### 7.3 数据恢复

```bash
# 1. 停止服务
cd /srv/salmon-pms
docker compose -f docker/docker-compose.prod.yml down

# 2. 恢复数据库
BACKUP_DATE="20260527_020000"
gunzip -c data/backups/$BACKUP_DATE/db_salmon_pms.sql.gz | docker exec -i $(docker ps -q -f name=db) psql -U salmon -d salmon_pms

# 3. 恢复 Redis（如需要）
docker cp data/backups/$BACKUP_DATE/redis_dump.rdb $(docker ps -q -f name=redis):/data/dump.rdb

# 4. 启动服务
docker compose -f docker/docker-compose.prod.yml up -d
```

---

## 八、日常运维命令

### 8.1 查看状态

```bash
cd /srv/salmon-pms

# 查看所有容器状态
docker compose -f docker/docker-compose.prod.yml ps

# 查看后端日志（实时）
docker compose -f docker/docker-compose.prod.yml logs -f backend

# 查看最后 100 行日志
docker compose -f docker/docker-compose.prod.yml logs --tail=100 backend

# 查看资源占用
docker stats
```

### 8.2 重启单个服务

```bash
# 重启后端
docker compose -f docker/docker-compose.prod.yml restart backend

# 重启前端
docker compose -f docker/docker-compose.prod.yml restart frontend

# 重启所有
docker compose -f docker/docker-compose.prod.yml restart
```

### 8.3 数据库维护

```bash
# 进入数据库容器
docker exec -it $(docker ps -q -f name=db) psql -U salmon -d salmon_pms

# 在容器内执行 SQL
\dt                    # 查看所有表
SELECT count(*) FROM products;
\q                     # 退出

# 导出当前数据库
docker exec $(docker ps -q -f name=db) pg_dump -U salmon -d salmon_pms > manual_backup.sql
```

### 8.4 磁盘空间监控

```bash
# 查看 Docker 占用空间
docker system df -v

# 清理未使用的镜像/容器/卷
docker system prune -a --volumes

# 查看数据目录大小
du -sh /srv/salmon-pms/data/*
```

---

## 九、网络配置详解

### 9.1 局域网访问方式

| 访问方式 | URL | 适用场景 |
|---------|-----|---------|
| 部署机本机 | `http://localhost` | 部署机直接测试 |
| 局域网IP | `http://192.168.1.100` | 同一局域网内的所有设备 |
| 固定域名（可选）| `http://salmon.lan` | 在路由器DNS或hosts文件配置 |

### 9.2 配置局域网域名（可选但推荐）

**在路由器上**（如果路由器支持自定义DNS）：
- 添加 A 记录：`salmon.lan` → `192.168.1.100`

**在每台电脑的 hosts 文件中**（Windows）：
```
192.168.1.100  salmon.lan
```

这样用户可以通过 `http://salmon.lan` 访问，比记IP更方便。

### 9.3 端口安全策略

```
部署机防火墙规则:
┌─────────────┬──────────┬──────────────┐
│ 端口        │ 访问来源  │ 用途          │
├─────────────┼──────────┼──────────────┤
│ 80 (TCP)    │ 局域网    │ 前端入口      │
│ 22 (TCP)    │ 仅管理IP  │ SSH 远程管理  │
│ 5432 (TCP)  │ 仅本机    │ 数据库（禁止外网）│
│ 6379 (TCP)  │ 仅本机    │ Redis（禁止外网） │
│ 9000 (TCP)  │ 仅本机    │ MinIO（禁止外网） │
│ 8000 (TCP)  │ 仅本机    │ 后端API（禁止外网）│
└─────────────┴──────────┴──────────────┘
```

> 关键：除 80 端口外，其他服务仅监听 `127.0.0.1`，外网无法直接访问。所有 API 请求都经过 nginx 反向代理，增加一层安全隔离。

---

## 十、常见问题与故障排除

### Q1：部署后浏览器显示 "Unable to connect"

**排查步骤：**
```bash
# 1. 检查容器是否运行
docker ps

# 2. 检查前端日志
docker logs $(docker ps -q -f name=frontend)

# 3. 检查防火墙
sudo ufw status

# 4. 检查局域网连通性
# 在另一台电脑上 ping 部署机
ping 192.168.1.100
```

### Q2：前端能打开，但 API 请求失败（CORS 错误）

**解决：** 编辑部署机的 `.env`，将访问设备的 IP 加入 `CORS_ORIGINS`：
```bash
CORS_ORIGINS=["http://192.168.1.100","http://192.168.1.101","http://localhost"]
```
然后重启后端：
```bash
docker compose -f docker/docker-compose.prod.yml restart backend
```

### Q3：数据库迁移（Alembic）如何执行？

**方案：** 在部署机进入后端容器执行
```bash
# 进入后端容器
docker exec -it $(docker ps -q -f name=backend) bash

# 安装 alembic（如果容器里没有）
pip install alembic

# 执行迁移
alembic upgrade head

# 退出
exit
```

### Q4：部署机重启后服务没有自动启动？

**解决：** Docker Compose 已配置 `restart: unless-stopped`，系统重启后 Docker 服务会自动拉起容器。确保 Docker 服务开机自启：
```bash
sudo systemctl enable docker
```

### Q5：如何更新部署机的 Docker Compose 文件本身？

因为 `docker-compose.prod.yml` 在仓库里，更新它也需要 Git pull：
```bash
cd /srv/salmon-pms
git pull origin main
# 然后重新部署
docker compose -f docker/docker-compose.prod.yml up --build -d
```

### Q6：如何在局域网内使用 HTTPS？

**方案 A：自签名证书（最简单）**
```bash
# 在部署机上生成自签名证书
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /srv/salmon-pms/data/ssl/nginx.key \
  -out /srv/salmon-pms/data/ssl/nginx.crt \
  -subj "/C=CN/ST=Beijing/L=Beijing/O=SalmonPMS/CN=salmon.lan"
```
然后修改 `frontend/nginx.conf` 添加 443 端口和证书路径，重新构建。

**方案 B：局域网 CA（推荐团队使用）**
使用 `mkcert` 工具为局域网内所有设备签发受信任的证书。

---

## 十一、方案总结

### 已创建的部署文件

| 文件 | 作用 | 位置 |
|------|------|------|
| `docker-compose.prod.yml` | 生产环境 Docker 编排 | `docker/` |
| `Dockerfile.prod` | 后端生产镜像（4 worker） | `backend/` |
| `nginx.conf` | 前端 nginx 配置（含反代） | `frontend/` |
| `.env.example` | 生产环境变量模板 | `docker/` |
| `deploy.sh` | 一键更新脚本 | `scripts/` |
| `backup.sh` | 自动备份脚本 | `scripts/` |

### 部署总览

```
开发机                          部署机
─────────────────────────────────────────────────
代码开发 ──► Git push ──► Git pull
                             │
                             ▼
                    ┌─────────────────┐
                    │  docker compose  │
                    │    up --build    │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
    ┌─────────┐      ┌──────────┐      ┌──────────┐
    │ nginx   │      │ backend  │      │  PostgreSQL│
    │  :80    │      │  :8000   │      │  :5432    │
    └─────────┘      └──────────┘      └──────────┘
         │
         ▼
    局域网用户
    http://192.168.x.x
```

### 维护节奏建议

| 任务 | 频率 | 方式 |
|------|------|------|
| 代码更新 | 按需 | 开发机 push → 部署机 deploy.sh |
| 数据库备份 | 每天凌晨 2 点 | crontab 自动 |
| 外置硬盘备份 | 每周日凌晨 3 点 | crontab 自动 |
| 检查磁盘空间 | 每周一次 | 手动 `df -h` |
| 系统安全更新 | 每月一次 | `apt upgrade` |
| 查看日志异常 | 每周一次 | 手动查看 |

---

*文档版本: 2026-05-27*  
*适用项目版本: Salmon PMS V8.2+*