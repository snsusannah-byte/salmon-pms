# 致外包团队：数据库变更通知

> 发件方：salmon-pms 项目组  
> 日期：2026-05-03  
> 收件方：成品销售模块外包团队

---

## 📢 重要变更通知

本项目已于 **2026-05-03** 将数据库从 **SQLite** 迁移至 **PostgreSQL**。此变更影响开发环境配置，请仔细阅读以下说明。

---

## 1. 为什么变更

| SQLite 问题 | PostgreSQL 解决 |
|-------------|-------------------|
| 多人开发时文件锁冲突 | 进程级并发，无锁冲突 |
| 进程崩溃导致数据库损坏 | 事务保证数据完整性 |
| 频繁 git 提交导致文件损坏 | 服务端数据库，不受文件操作影响 |
| 外键约束不严格 | 严格外键约束，数据一致性 |

---

## 2. 开发环境变更

### 2.1 你需要安装 PostgreSQL

**Windows 安装**：
1. 下载：https://www.postgresql.org/download/windows/
2. 安装时记住密码（建议：`salmon123`）
3. 保持默认端口 `5432`

**或使用 Docker**（如果你熟悉）：
```bash
docker run -d --name postgres \
  -e POSTGRES_PASSWORD=salmon123 \
  -p 5432:5432 postgres:16
```

### 2.2 创建数据库

安装完成后执行：
```bash
# 使用 psql（PostgreSQL 命令行）
psql -U postgres

# 在 psql 中执行：
CREATE USER salmon WITH PASSWORD 'salmon123';
CREATE DATABASE salmon_pms OWNER salmon;
GRANT ALL PRIVILEGES ON DATABASE salmon_pms TO salmon;
```

### 2.3 后端配置

`.env` 文件已更新为 PostgreSQL：
```
DATABASE_URL=postgresql+asyncpg://salmon:salmon123@localhost:5432/salmon_pms
```

**依赖安装**：
```bash
cd backend
uv add asyncpg
```

---

## 3. 数据库初始化

### 3.1 创建表结构

```bash
cd backend
source .venv/bin/activate  # Windows: .venv\Scripts\activate
alembic upgrade head
```

### 3.2 导入测试数据

如果需要测试数据，请向我们索取 `salmon_pms_dev.sql` 导出文件：
```bash
psql -U salmon -d salmon_pms -f salmon_pms_dev.sql
```

---

## 4. 技术约束更新

### 4.1 Schema 变更

从 SQLite 迁移后发现的问题，**你的代码需要注意**：

| 字段 | SQLite（之前） | PostgreSQL（现在） |
|------|---------------|-------------------|
| `fish_farm_id` | 允许传 `0` | 必须传 `null` 或不传 |
| `exporter_id` | 允许传 `0` | 必须传 `null` 或不传 |
| `processing_plant_id` | 允许传 `0` | 必须传 `null` 或不传 |
| `total_amount_usd` | 前端可传 | 后端自动计算，前端无需传 |

**影响**：发票创建/更新接口，如果前端传了 `fish_farm_id=0` 会导致 422 错误。

### 4.2 枚举值大小写

PostgreSQL 严格区分大小写，请确保：
- `category=WHOLE_FISH`（大写）
- `customs_status=pending_customs`（小写）

---

## 5. 新增模块

### 5.1 通知系统

新增模块，**不在你的外包范围内**，但需要注意不要冲突：
- 新增表：`notifications`
- 新增 API：`/v1/notifications/*`
- 新增服务：`notification_service.py`

### 5.2 当前表结构

数据库现有表：
```
companies, users, import_invoices, invoice_products, products,
product_boms, product_packagings, batches, batch_invoices,
whole_fish_sales, sales_receipts, aftersales_records,
finished_product_sales, finished_product_receipts, finished_product_aftersales,
transaction_records, commission_records, bank_accounts, notifications,
inventory, inventory_movements, audit_trail, system_configs
```

---

## 6. 开发注意事项

### 6.1 不要修改的文件

| 文件 | 原因 |
|------|------|
| `app/core/config.py` | 数据库连接配置已固定 |
| `app/core/database.py` | 移除了 SQLite 特有的 PRAGMA |
| `alembic.ini` | 已配置为 PostgreSQL |

### 6.2 迁移脚本

新增/修改表结构必须通过 Alembic：
```bash
cd backend
alembic revision --autogenerate -m "your change description"
alembic upgrade head
```

### 6.3 测试

每次提交前请确认：
```bash
cd backend
alembic upgrade head   # 确保迁移可执行
pytest                 # 运行测试（如果有）
```

---

## 7. 联系方式

如有问题，请通过以下方式联系：
- GitHub Issues
- 即时通讯

---

**请确认收到此通知，并回复预计完成环境配置的时间。**

---

附：数据库连接信息（开发环境）
```
Host: localhost
Port: 5432
Database: salmon_pms
User: salmon
Password: salmon123
```
