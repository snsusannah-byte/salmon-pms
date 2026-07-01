# Salmon PMS 完整项目审查报告

**审查日期**: 2026-06-05  
**审查人**: OpenClaw Agent  
**项目版本**: V8.2+  
**最新提交**: 2801c2d (2026-06-01 pre-deploy checkpoint)

---

## 一、项目概况

### 基本信息

| 属性 | 详情 |
|------|------|
| **项目名称** | 三文鱼项目管理系统 (Salmon PMS) |
| **业务领域** | 三文鱼加工厂 ERP |
| **技术栈** | FastAPI + React + PostgreSQL + Redis + MinIO |
| **当前版本** | V8.2+ |
| **Git 提交数** | 91 次 |
| **数据库** | PostgreSQL 16 |

### 代码规模

| 模块 | 文件数 | 代码行数 | 说明 |
|------|--------|----------|------|
| 后端 API | 102 个 Python 文件 | 32,741 行 | 包含端点、服务、模型、Schema |
| 前端页面 | 44 个页面 + 34 个组件 | 34,343 行 | React + TypeScript |
| 测试代码 | 2 个测试文件 | 253 行 | 覆盖率 < 1% |
| **总计** | — | **67,000+ 行** | 生产级 ERP 系统 |

### 核心模块

| 模块 | 端点数 | 状态 |
|------|--------|------|
| 认证 (auth) | 4 | ✅ 有权限控制 |
| 财务管理 (finance) | 33 | ⚠️ 部分有权限 |
| 报表中心 (reports) | 12 | ❌ 无权限控制 |
| 销售管理 (sales) | 22 | ❌ 无权限控制 |
| 进口单证 (invoices) | 13 | ❌ 无权限控制 |
| 批次管理 (batches) | 10 | ⚠️ 部分有权限 |
| 仓库管理 (warehouse) | 33 | ⚠️ 部分有权限 |
| 成品管理 (finished) | 42 | ⚠️ 部分有权限 |
| 合并收款 (batch-collect) | 1 | ✅ **刚修复** |

---

## 二、🔴 严重问题（P0 - 必须立即修复）

### 问题 1：15 个 API 端点无权限控制（安全漏洞）

**状态**: 部分已修复（1个），剩余 15 个未修复  
**风险等级**: 🔴 高危

以下端点文件完全没有使用 `require_*` 或 `get_current_user` 权限控制：

| # | 文件 | 风险 | 说明 |
|---|------|------|------|
| 1 | `sales.py` | 🔴 极高 | 任何用户可修改/删除销售单、收款记录 |
| 2 | `invoices.py` | 🔴 极高 | 任何用户可修改进口报关数据 |
| 3 | `reports.py` | 🔴 极高 | 任何用户可查看全部财务数据 |
| 4 | `finished_product_sales.py` | 🔴 高 | 成品销售数据暴露 |
| 5 | `returns.py` | 🔴 高 | 退货操作无限制 |
| 6 | `purchase_orders.py` | 🔴 高 | 采购数据可篡改 |
| 7 | `dashboard.py` | 🟡 中 | 看板数据暴露 |
| 8 | `material_purchases.py` | 🟡 中 | 物料采购数据暴露 |
| 9 | `loss_records.py` | 🟡 中 | 损耗数据可篡改 |
| 10 | `traceability.py` | 🟡 中 | 追溯数据暴露 |
| 11 | `notifications.py` | 🟡 中 | 通知管理暴露 |
| 12 | `material_categories.py` | 🟡 低 | 物料分类可篡改 |
| 13 | `finance_v4_migration.py` | 🟡 低 | 迁移接口暴露 |
| 14 | `client_errors.py` | 🟡 低 | 错误日志暴露 |
| 15 | `finished_product_sales_v2.py` | 🟡 低 | 成品销售 v2 暴露 |
| 16 | `warehouse.py` (旧) | 🟡 中 | 仓库操作暴露 |
| ✅ | `sales_batch_collect.py` | — | **已修复**（添加 `require_sales`）|

**影响**: 任何登录用户（甚至通过猜测 API 路径）都可以访问/修改所有业务数据。

**修复建议**:
```python
# 为所有 POST/PUT/DELETE 操作添加权限
from app.core.permissions import require_finance, require_sales, require_warehouse, require_admin
from app.core.deps import get_current_user
from app.models import User

@router.post("/...")
async def create_xxx(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_finance),  # 根据模块选择
):
```

**预计工作量**: 每个端点文件 2-3 行修改，总计约 2 天。

---

### 问题 2：数据库迁移完全缺失（架构风险）

**状态**: 未修复  
**风险等级**: 🔴 高危

```
backend/alembic.ini          ✅ 存在
backend/alembic/versions/     ❌ 目录为空（0 个迁移文件）
```

**问题**: 虽然 `alembic` 已安装且配置了 `alembic.ini`，但 `versions/` 目录为空。这意味着：
- 数据库 schema 无法通过迁移脚本管理
- 生产环境升级时无法安全地修改表结构
- 团队协作时无法同步数据库变更
- 回滚和版本控制 impossible

**修复建议**:
```bash
cd backend
# 初始化迁移（首次）
alembic revision --autogenerate -m "initial"
alembic upgrade head

# 后续每次修改 model 后：
alembic revision --autogenerate -m "描述"
```

**预计工作量**: 首次生成约 1-2 天（需要检查所有 model 是否一致），后续每次修改 model 后执行命令即可。

---

### 问题 3：TODO 未处理（功能缺陷）

**状态**: 未修复  
**风险等级**: 🟡 中

```python
# returns.py:190
approved_by_id = None  # TODO: 从认证获取当前用户ID

# returns.py:295
approved_by_id = None  # TODO: 从认证获取

# returns.py:313
processed_by_id = None  # TODO: 从认证获取

# finance_v4_migration_service.py:16
# TODO: 实现迁移逻辑

# purchase_orders.py:54
# TODO: 返回完整详情
```

**影响**: 退货审批记录没有记录操作人，审计追踪失效。

**修复建议**: 添加 `current_user: User = Depends(get_current_user)` 参数并赋值给 `approved_by_id` / `processed_by_id`。

**预计工作量**: 0.5 天

---

## 三、🟡 中等问题（P1 - 近期修复）

### 问题 4：测试覆盖率极低

**状态**: 未修复  
**风险等级**: 🟡 中

| 指标 | 数值 | 目标 |
|------|------|------|
| 后端代码行 | 32,741 | — |
| 测试代码行 | 253 | — |
| 覆盖率 | **< 1%** | > 70% |
| 核心财务逻辑测试 | 0 | 全部覆盖 |
| 报表端点测试 | 0 | 全部覆盖 |

**问题**: `test_api.py` 中仅测试了健康检查、登录验证和报表端点可访问性，且使用了 `@pytest.mark.xfail` 跳过 PostgreSQL 特有函数测试。

**修复建议**:
```bash
# 使用 PostgreSQL 测试数据库（而非 SQLite）
pytest tests/ -v --cov=app --cov-report=html
```

**预计工作量**: 3-5 天（核心模块优先）

---

### 问题 5：前端大文件未拆分

**状态**: 未修复  
**风险等级**: 🟡 中

| 文件 | 行数 | 模块 |
|------|------|------|
| `FinancePage.tsx` | 2,771 | 财务管理 |
| `SalesPage.tsx` | 1,950 | 销售管理 |
| `ProductsPage.tsx` | 1,777 | 产品管理 |
| `FinishedProductSales.tsx` | 1,347 | 成品销售 |
| `reports.py` | 4,285 | 后端报表 |
| `finance_service.py` | 1,199 | 后端财务服务 |

**问题**: 单个文件超过 2,000 行，维护困难，容易产生冲突。

**修复建议**: 按功能拆分为子组件（Tab 组件已部分拆分，但 FinancePage 和 SalesPage 仍然过大）。

**预计工作量**: 2-3 天

---

### 问题 6：生产环境端口配置

**状态**: 已修复 ✅  
**风险等级**: 🔴 高（已修复）

**修改前**:
```yaml
# docker-compose.prod.yml
db:
  ports:
    - "15432:5432"  # ❌ 暴露到 0.0.0.0:15432
```

**修改后**:
```yaml
db:
  ports:
    - "127.0.0.1:15432:5432"  # ✅ 仅本机可访问
```

**注意**: Redis 和 MinIO 的端口已正确绑定 `127.0.0.1`。

---

### 问题 7：`main.py` 重复路由注册

**状态**: 未修复  
**风险等级**: 🟡 中

```python
# backend/app/main.py:58
app.include_router(materials.router, prefix="/api/v4/materials", ...)
app.include_router(warehouse.router, prefix="/api/v4/warehouse", ...)

# backend/app/main.py:64 — 重复注册！
app.include_router(materials.router, prefix="/api/v4/materials", ...)
app.include_router(warehouse.router, prefix="/api/v4/warehouse", ...)
```

**影响**: 路由重复注册可能导致中间件执行两次或缓存异常。

**修复建议**: 删除重复的两行。

**预计工作量**: 5 分钟

---

### 问题 8：Raw SQL 混合使用

**状态**: 未修复  
**风险等级**: 🟡 低

**位置**: `finance_service.py`（3 处）、`material_purchase_service.py`（1 处）

```python
# finance_service.py:388
result = await db.execute(text(sql), params)
```

**问题**: 虽然使用了参数化查询（`:invoice_id`），但混合使用 ORM 和 raw SQL 增加了维护成本。不过目前没有 SQL 注入风险。

---

## 四、🟢 数据准确性问题（已修复）

### 销售净额差异（1.64 元）✅ 已修复

**问题**: 批次财报显示 ¥532,258.20，进口销售显示 ¥532,256.56，差异 1.64 元。

**根因**:
1. `sales_service.py` 的 `_sync_commission_record` 只创建 `CommissionRecord` 记录，但没有同步更新 `sale.commission` 字段
2. 当删除业务员时，`sale.commission` 未清零，导致 `net_amount` 计算错误
3. `update_sale` 中调用 `_sync_commission_record` 后，没有重新计算 `net_amount`

**修复**:
- `sales_service.py`: `_sync_commission_record` 现在同步更新 `sale.commission`
- `sales_service.py`: `update_sale` 在 `_sync_commission_record` 后重新计算 `net_amount`
- `scripts/fix_sales_net_amount.py`: 修复了数据库中 1 条不一致记录（ID=303）

**验证**: 批次 4 的 14 条销售单汇总，net_amount = expected = ¥532,258.20 ✅

---

## 五、架构评估

### 技术选型

| 技术 | 版本 | 评估 |
|------|------|------|
| FastAPI | 现代 | ✅ 现代异步框架，OpenAPI 自动生成 |
| SQLAlchemy 2.0 | 2.0+ | ✅ 类型安全，现代 ORM |
| PostgreSQL | 16 | ✅ 生产级关系数据库 |
| Redis | 7 | ✅ 缓存/会话存储 |
| MinIO | Latest | ✅ 对象存储 |
| React | 18 | ✅ 现代前端框架 |
| TanStack Query | 5 | ✅ 数据获取/缓存 |
| shadcn/ui | — | ✅ 现代 UI 组件库 |
| ruff | — | ✅ 现代 Python linter |
| mypy | — | ✅ 类型检查 |

### 架构亮点

1. **前后端权限对应**: `permissions.py` 和 `permissions.ts` 完全对应
2. **审计日志系统**: `audit.py` 记录所有操作
3. **全局异常处理**: 500 错误自动记录到 `client_errors.jsonl`
4. **Decimal 安全运算**: 引入 `decimal.js`，避免浮点误差
5. **模型拆分**: 已从单文件拆分为 11 个子模块
6. **N+1 查询优化**: 批量预加载替代循环内单查
7. **Docker 化**: 前后端 + 数据库 + 缓存 + 对象存储全部容器化

### 架构问题

1. **前端 hooks/stores 为空**: `frontend/src/hooks/` 和 `frontend/src/stores/` 目录为空，状态管理依赖 useState 和 localStorage
2. **缺少 API 层抽象**: 前端直接调用 `api.get()`，没有统一的 API client 层
3. **缺少错误边界**: 没有 React Error Boundary 处理组件崩溃
4. **缺少加载状态统一处理**: 各页面独立处理 loading 状态

---

## 六、生产就绪性评估

### 配置安全

| 配置项 | 状态 | 说明 |
|--------|------|------|
| `.env` 在 `.gitignore` | ✅ | 环境变量不会提交 |
| `.env.local` 在 `.gitignore` | ✅ | 前端环境变量不会提交 |
| `SECRET_KEY` 环境变量化 | ⚠️ | 默认生成弱密钥，需要生产环境强制配置 |
| `DEBUG` 生产环境 | ❌ | 默认 `True`，需要生产环境设为 `false` |
| `CORS` 配置 | ✅ | 通过环境变量配置 |

### 部署配置

| 配置 | 状态 | 说明 |
|------|------|------|
| `Dockerfile` | ✅ | 开发环境使用 |
| `Dockerfile.prod` | ✅ | 生产环境优化 |
| `docker-compose.yml` | ✅ | 开发环境 |
| `docker-compose.prod.yml` | ✅ | 生产环境（端口已修复） |
| `DEPLOYMENT.md` | ✅ | 详细的部署手册 |
| `OPERATIONS.md` | ✅ | 用户操作手册 |
| 数据库备份脚本 | ✅ | `scripts/backup-db.sh` |
| 数据库恢复脚本 | ✅ | `scripts/restore-db.sh` |
| 环境切换脚本 | ✅ | `scripts/switch-env.sh` |

### 缺少的生产环境要素

1. **CI/CD 流水线**: 没有 GitHub Actions / GitLab CI 配置
2. **自动化测试**: 没有提交前自动运行测试
3. **代码覆盖率报告**: 没有自动化覆盖率检查
4. **API 文档**: Swagger UI 可访问，但没有单独的 API 文档站点
5. **监控/告警**: 没有健康检查告警、错误告警
6. **日志聚合**: 没有 ELK / Loki 等日志系统
7. **性能监控**: 没有 APM 工具（如 Sentry、New Relic）

---

## 七、综合评分

| 维度 | 评分 | 权重 | 加权分 | 说明 |
|------|------|------|--------|------|
| **功能完整度** | 8.5/10 | 20% | 1.70 | 28+ 模块，核心功能闭环 |
| **代码质量** | 6.5/10 | 15% | 0.98 | 结构清晰但测试缺失、大文件过多 |
| **数据准确性** | 8.5/10 | 20% | 1.70 | 关键报表 bug 已修复 |
| **架构成熟度** | 7.5/10 | 15% | 1.13 | 技术选型现代，但缺少 hooks/stores |
| **安全性** | 5.0/10 | 15% | 0.75 | 权限框架已建立但未应用（已修复1个） |
| **工程实践** | 5.5/10 | 10% | 0.55 | 有 ruff/mypy，但无 CI/CD、无迁移 |
| **用户体验** | 7.5/10 | 5% | 0.38 | 功能齐全，部分页面过大 |
| **文档完善度** | 8.0/10 | — | — | 部署文档、操作手册齐全 |

### 🏆 **综合评分: 7.2 / 10**

> 比上次 (7.0) 提升，主要因为修复了权限应用问题（1个端点）和关键数据不一致问题。

---

## 八、修复建议（按优先级排序）

### P0 — 生产前必须完成（1-2 周）

| # | 任务 | 文件 | 预估工时 | 风险 |
|---|------|------|----------|------|
| 1 | **15 个端点添加权限控制** | 15 个文件 | 2 天 | 🔴 安全漏洞 |
| 2 | **生成数据库迁移** | `alembic/versions/` | 1-2 天 | 🔴 架构风险 |
| 3 | **修复 `returns.py` TODO** | `returns.py` | 0.5 天 | 🟡 审计失效 |
| 4 | **修复 `main.py` 重复路由** | `main.py` | 5 分钟 | 🟡 路由异常 |
| 5 | **生产环境强制配置** | `config.py` | 0.5 天 | 🔴 配置泄露 |

### P1 — 本月完成

| # | 任务 | 预估工时 | 说明 |
|---|------|----------|------|
| 6 | **核心模块单元测试** | 3-5 天 | `reports.py` + `finance_service.py` 优先 |
| 7 | **前端大文件拆分** | 2-3 天 | `FinancePage.tsx` + `SalesPage.tsx` |
| 8 | **前端 hooks/stores** | 1-2 天 | 通用 hooks + Zustand stores |
| 9 | **API 限流中间件** | 0.5 天 | 防止暴力破解/爬虫 |
| 10 | **TODO/FIXME 清理** | 0.5 天 | 6 个待处理项 |

### P2 — 近期完成

| # | 任务 | 预估工时 | 说明 |
|---|------|----------|------|
| 11 | **GitHub Actions CI/CD** | 1 天 | 自动测试 + 构建 + 部署 |
| 12 | **Celery 任务启用** | 2 天 | 报表生成异步化 |
| 13 | **前端 Error Boundary** | 0.5 天 | 防止白屏崩溃 |
| 14 | **API 文档站点** | 1 天 | 独立文档而非仅 Swagger |
| 15 | **性能监控** | 1-2 天 | Sentry 或类似工具 |

---

## 九、今日修复记录（2026-06-05）

### 已修复 ✅

1. **销售净额差异（1.64元）**
   - `sales_service.py`: `_sync_commission_record` 同步更新 `sale.commission`
   - `sales_service.py`: `update_sale` 重新计算 `net_amount`
   - `scripts/fix_sales_net_amount.py`: 修复数据库不一致记录

2. **交易流水关联发票号**
   - `finance.py`: 批量查询 `import_invoices` 表
   - `FinancePage.tsx`: 新增"关联发票号"列 + 导出 Excel

3. **`sales_batch_collect.py` 权限控制**
   - 添加 `current_user: User = Depends(require_sales)`

4. **`docker-compose.prod.yml` 端口安全**
   - PostgreSQL 端口从 `15432:5432` 改为 `127.0.0.1:15432:5432`

---

## 十、结论

Salmon PMS 是一个 **功能丰富、架构现代** 的三文鱼加工厂 ERP 系统。经过今日的审查和修复，系统在以下方面有了显著改进：

✅ **销售净额数据一致性** — 已修复  
✅ **交易流水关联发票号** — 已实现  
✅ **批量收款权限控制** — 已修复  
✅ **生产环境端口安全** — 已修复  

但最大的 **安全隐患** 仍然是 **15 个端点无权限控制**。虽然权限框架已建立，但大部分端点未实际应用，这意味着任何登录用户都可以访问/修改所有业务数据。

**建议立即执行的修复**:
1. 为所有 `POST/PUT/DELETE` 端点添加 `Depends(require_*)`
2. 生成数据库迁移脚本（`alembic revision --autogenerate`）
3. 修复 `returns.py` 的 TODO
4. 清理 `main.py` 的重复路由
5. 生产环境强制使用环境变量密钥（`SECRET_KEY` 和 `DATABASE_URL`）

---

*报告生成时间: 2026-06-05 15:09*  
*审查范围: 后端 API、前端页面、数据库、配置文件、安全设置、生产环境*
