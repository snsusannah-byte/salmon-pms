# Salmon PMS — 部署与分支管理技术手册

> **版本**: v1.0  
> **适用对象**: OpenClaw Agent（技术人员参考）  
> **对应**: `OPERATIONS.md` 的技术实现细节

---

## 一、分支策略：简化版 Git Flow

### 分支结构

```
main                ← 生产环境代码，始终可部署
  │
  ├─ dev            ← 集成测试环境，合并多个 feature
  │    │
  │    ├─ feature/A  ← 功能 A 开发分支
  │    └─ feature/B  ← 功能 B 开发分支
  │
  ├─ hotfix/xxx     ← 紧急修复分支（直接从 main 切出）
```

### 分支规则

| 分支 | 用途 | 生命周期 | 保护规则 |
|------|------|---------|---------|
| `main` | 生产环境 | 永久 | 禁止直接提交，只能通过 PR/合并 |
| `dev` | 集成测试 | 永久 | 允许合并 feature |
| `feature/*` | 单个功能开发 | 开发完删除 | 从 main 或 dev 切出 |
| `hotfix/*` | 紧急修复 | 修复完删除 | 从 main 直接切出 |

### 提交规范（Commit Message）

```
feat(模块名): 功能描述
fix(模块名): 修复描述
docs(模块名): 文档更新
refactor(模块名): 重构描述
test(模块名): 测试相关
chore: 构建/工具链更新

例如：
feat(warehouse): 新增库存预警 API
fix(reports): 修复利润表周期过滤
```

---

## 二、环境配置

### 2.1 生产环境（Docker Compose）

**文件**: `docker/docker-compose.yml`

**配置要点**：
- PostgreSQL: `postgres:16-alpine`
- Redis: `redis:7-alpine`
- MinIO: `minio/minio:latest`
- 后端: 从 `backend/Dockerfile` 构建
- 前端: 从 `frontend/Dockerfile` 构建

**生产环境专用配置**：

```bash
# backend/.env.production（需要创建）
DATABASE_URL=postgresql+asyncpg://salmon:salmon123@db:5432/salmon_pms
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
SECRET_KEY=<随机生成的强密码>
DEBUG=false
```

### 2.2 开发环境（本地运行）

**配置**: `backend/.env`（已有）

```bash
DATABASE_URL=sqlite+aiosqlite:///./salmon_pms_dev.db
# 或独立的 PostgreSQL 实例
REDIS_URL=redis://localhost:6379/0
DEBUG=true
```

### 2.3 环境切换脚本

**创建** `scripts/switch-env.sh`：

```bash
#!/bin/bash
# 切换开发和生产环境

ENV=$1

if [ "$ENV" = "dev" ]; then
    echo "切换到开发环境..."
    # 停止生产容器
    cd docker && docker compose down
    # 启动开发服务
    cd ../backend
    source .venv/bin/activate
    uvicorn app.main:app --reload &
    cd ../frontend
    pnpm dev &
    echo "开发环境已启动"
elif [ "$ENV" = "prod" ]; then
    echo "切换到生产环境..."
    # 停止开发服务
    pkill -f "uvicorn" || true
    pkill -f "vite" || true
    # 启动生产容器
    cd docker
    docker compose up -d --build
    echo "生产环境已启动"
else
    echo "用法: ./switch-env.sh [dev|prod]"
    exit 1
fi
```

---

## 三、数据库迁移管理

### 3.1 迁移工作流

```
开发 feature → 修改 model → 生成迁移 → 测试迁移 → 合并 → 上线执行
```

### 3.2 迁移命令

```bash
cd backend

# 生成迁移（修改 model 后）
alembic revision --autogenerate -m "描述"

# 应用到开发数据库
alembic upgrade head

# 回滚一次迁移
alembic downgrade -1

# 查看历史
alembic history

# 查看当前版本
alembic current
```

### 3.3 生产环境迁移注意事项

1. **上线前**：先在开发环境测试迁移
2. **上线时**：先备份数据库，再执行迁移
3. **不可逆迁移**：需要特别小心（如删除列、修改约束）
4. **大数据量表**：迁移可能需要很长时间，选择低峰期

---

## 四、备份与恢复

### 4.1 数据库备份脚本

**改进现有** `scripts/backup-db.sh`：

```bash
#!/bin/bash
# Salmon PMS 数据库备份脚本

set -e

BACKUP_DIR="$(dirname "$0")/../backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"
CONTAINER_NAME="salmon-pms-db-1"
DB_NAME="salmon_pms"
DB_USER="salmon"
RETENTION_DAYS=30

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 检查容器是否在运行
if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "错误: PostgreSQL 容器 $CONTAINER_NAME 未运行"
    exit 1
fi

# 执行备份
echo "正在备份数据库..."
docker exec -t "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"

# 压缩备份
gzip "$BACKUP_FILE"
BACKUP_FILE="$BACKUP_FILE.gz"

# 显示备份信息
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "✅ 备份完成: $BACKUP_FILE ($FILE_SIZE)"

# 清理旧备份（保留30天）
echo "清理 $RETENTION_DAYS 天前的旧备份..."
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "清理完成"
```

### 4.2 数据库恢复脚本

**创建** `scripts/restore-db.sh`：

```bash
#!/bin/bash
# Salmon PMS 数据库恢复脚本

set -e

BACKUP_DIR="$(dirname "$0")/../backups"
CONTAINER_NAME="salmon-pms-db-1"
DB_NAME="salmon_pms"
DB_USER="salmon"

# 如果没有指定备份文件，使用最新的
if [ -z "$1" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/backup_*.sql.gz 2>/dev/null | head -1)
    if [ -z "$BACKUP_FILE" ]; then
        echo "错误: 找不到备份文件"
        exit 1
    fi
    echo "使用最新备份: $BACKUP_FILE"
else
    BACKUP_FILE="$1"
fi

# 确认
read -p "⚠️  这将覆盖现有数据库！确认恢复吗？ [y/N] " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "已取消"
    exit 0
fi

# 检查容器
if ! docker ps --format '{{.Names}}' | grep -q "^$CONTAINER_NAME$"; then
    echo "错误: PostgreSQL 容器未运行"
    exit 1
fi

# 恢复数据库
echo "正在恢复数据库..."
if [[ "$BACKUP_FILE" == *.gz ]]; then
    gunzip < "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME"
else
    docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE"
fi

echo "✅ 数据库恢复完成"
```

### 4.3 定时备份（Crontab）

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 3 点备份
0 3 * * * /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms/scripts/backup-db.sh >> /var/log/salmon-pms-backup.log 2>&1
```

---

## 五、上线流程（详细步骤）

### 5.1 上线前检查清单

- [ ] 功能在 dev 分支测试通过
- [ ] 所有单元测试通过（如果有）
- [ ] 代码审查完成（Agent 自我审查）
- [ ] 数据库迁移已生成并测试
- [ ] 备份脚本已执行，备份文件存在
- [ ] 无未解决的 TODO/FIXME
- [ ] 文档已更新（如果需要）

### 5.2 上线步骤

```bash
# 1. 确认在生产环境目录
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms

# 2. 备份数据库
./scripts/backup-db.sh

# 3. 切到 main 分支并更新
git checkout main
git pull origin main

# 4. 合并 dev 分支（或 feature 分支）
git merge dev

# 5. 解决冲突（如果有）
# ...

# 6. 打版本标签
VERSION=$(date +%Y%m%d-%H%M)
git tag -a "v$VERSION" -m "Release v$VERSION"

# 7. 推送
git push origin main
git push origin "v$VERSION"

# 8. 执行数据库迁移（如果有）
cd backend
source .venv/bin/activate
alembic upgrade head

# 9. 重新构建部署
cd ../docker
docker compose down
docker compose up -d --build

# 10. 验证部署
docker compose ps
sleep 5
curl -s http://localhost:8000/health || curl -s http://localhost:8000/

# 11. 健康检查
echo "等待服务启动..."
sleep 10
curl -s http://localhost:8000/health || echo "请手动检查 http://localhost:8000"
```

### 5.3 回滚步骤

```bash
# 1. 紧急回滚代码
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms
git checkout main
git revert -m 1 HEAD  # 撤销合并提交

# 2. 恢复数据库（使用上线前的备份）
./scripts/restore-db.sh backups/backup_YYYYMMDD_HHMMSS.sql.gz

# 3. 重新部署
cd docker
docker compose down
docker compose up -d --build

# 4. 验证
curl -s http://localhost:8000/health
```

---

## 六、Feature 开发工作流

### 6.1 标准流程

```bash
# 1. 确保 main 是最新的
git checkout main
git pull origin main

# 2. 创建 feature 分支
FEATURE_NAME="feature/warehouse-alert"
git checkout -b "$FEATURE_NAME"

# 3. 切换到开发环境
./scripts/switch-env.sh dev

# 4. 开发...
# ... 修改代码 ...

# 5. 提交更改
git add .
git commit -m "feat(warehouse): 新增库存预警功能"

# 6. 推送分支
git push -u origin "$FEATURE_NAME"

# 7. 开发环境测试
# 启动服务，调用 API，验证前端

# 8. 合并到 dev
git checkout dev
git pull origin dev
git merge "$FEATURE_NAME"
git push origin dev

# 9. 用户验收后，合并到 main
git checkout main
git merge dev
git push origin main

# 10. 删除 feature 分支
git branch -d "$FEATURE_NAME"
git push origin --delete "$FEATURE_NAME"

# 11. 部署上线
./scripts/switch-env.sh prod
```

### 6.2 Agent 开发时的注意事项

1. **数据库选择**：
   - Feature 开发：用 SQLite（`salmon_pms_dev.db`）或独立 PostgreSQL
   - 绝不直接连接生产数据库

2. **端口冲突处理**：
   - 生产环境 Docker 占用 8000/5173/5432
   - 开发环境也默认用 8000/5173
   - 切换时必须先停掉另一套

3. **环境变量管理**：
   - `backend/.env` — 开发环境
   - `backend/.env.production` — 生产环境（需创建）
   - 不要将 `.env.production` 提交到 Git

4. **数据库迁移注意事项**：
   - 开发新 feature 如果改了 model，必须生成 migration
   - migration 文件要提交到 Git
   - 上线时按顺序执行 migration

---

## 七、监控与健康检查

### 7.1 健康检查端点

确保后端有以下端点：

```python
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": settings.VERSION,
        "database": check_db_connection(),
        "timestamp": datetime.now().isoformat()
    }
```

### 7.2 Docker 健康检查

在 `docker-compose.yml` 中为各服务添加 healthcheck：

```yaml
services:
  backend:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

---

## 八、版本标签管理

### 8.1 标签规范

```
vYYYYMMDD-HHMM    # 时间戳版本（推荐，简单）
v1.2.3           # SemVer（项目稳定后使用）
```

### 8.2 创建标签

```bash
# 时间戳版本（当前推荐）
VERSION=$(date +%Y%m%d-%H%M)
git tag -a "v$VERSION" -m "Release v$VERSION - 功能描述"

# 推送标签
git push origin "v$VERSION"
```

### 8.3 查看历史版本

```bash
# 查看所有标签
git tag -l

# 查看标签详情
git show v20260526-1500

# 回滚到某个标签
git checkout v20260526-1500
```

---

## 九、故障排查

### 9.1 常见问题

| 问题 | 排查步骤 |
|------|---------|
| 服务启动失败 | `docker compose logs backend` 查看错误 |
| 数据库连接失败 | 检查 `DATABASE_URL` 是否正确，容器是否启动 |
| 前端空白 | 检查 `VITE_API_URL` 是否正确，浏览器控制台错误 |
| 端口被占用 | `lsof -i :8000` 或 `lsof -i :5173` 找出占用进程 |
| 数据丢失 | 检查 backups/ 目录，执行恢复脚本 |

### 9.2 日志查看

```bash
# Docker 日志
docker compose logs -f backend
docker compose logs -f frontend

# 实时跟踪
docker compose logs -f --tail=100
```

---

## 十、附录

### A. 初始化分支（首次设置）

如果当前只有 main 分支，执行：

```bash
cd /home/sannah/.openclaw/workspace-codeingman/projects/salmon-pms

# 创建 dev 分支
git checkout -b dev

# 推送
git push -u origin dev

# 回到 main
git checkout main

# 创建 .env.production 模板（不提交敏感信息）
cat > backend/.env.production.example << 'EOF'
DATABASE_URL=postgresql+asyncpg://salmon:salmon123@db:5432/salmon_pms
REDIS_URL=redis://redis:6379/0
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=salmon
MINIO_SECRET_KEY=<CHANGE_ME>
SECRET_KEY=<GENERATE_STRONG_SECRET>
DEBUG=false
EOF
```

### B. 生产环境初始化

```bash
# 1. 安装 Docker
curl -fsSL https://get.docker.com | sh

# 2. 启动服务
cd docker
docker compose up -d

# 3. 初始化数据库（首次）
docker exec -i salmon-pms-db-1 psql -U salmon -d salmon_pms < ../database/init.sql

# 4. 执行迁移
cd ../backend
source .venv/bin/activate
alembic upgrade head

# 5. 验证
curl http://localhost:8000/health
```

### C. 开发环境快速启动

```bash
# 后端
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# 前端（新终端）
cd frontend
pnpm dev --port 5173
```

---

> **本手册对应**: `OPERATIONS.md`（用户版操作手册）  
> **更新日期**: 2026-05-26
