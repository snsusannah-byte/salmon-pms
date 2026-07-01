# Salmon PMS 项目报告

## 一、项目概述

| 项目属性 | 详情 |
|---------|------|
| **项目名称** | 三文鱼项目管理系统 (Salmon PMS) |
| **当前版本** | V8.2 |
| **项目状态** | 🚧 开发中 — 核心功能已完成，持续迭代优化 |
| **Git 总提交数** | 91 次 |
| **分支** | main（主分支，与 origin/main 同步） |
| **最后更新** | 2026-06-01 |

## 二、技术架构

### 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| **前端** | React + Vite + TypeScript | React 19.2.5 |
| **UI 框架** | Tailwind CSS + shadcn/ui + Base UI | - |
| **状态管理** | TanStack Query (React Query) | v5.100.6 |
| **路由** | React Router DOM | v7.14.2 |
| **图表** | Recharts | v3.8.1 |
| **后端** | FastAPI (Python) | v0.115.0+ |
| **数据库** | SQLite (开发) / PostgreSQL (生产) | - |
| **ORM** | SQLAlchemy | v2.0.36 |
| **缓存** | Redis | v5.2.0 |
| **任务队列** | Celery | v5.4.0 |
| **认证** | JWT (PyJWT) + bcrypt | - |
| **容器化** | Docker + Docker Compose | - |
| **监控** | Prometheus | - |
| **日志** | structlog | v24.4.0 |

## 三、代码规模统计

| 模块 | 文件数 | 代码行数 | 说明 |
|------|--------|----------|------|
| **后端 API** | 31 个端点 | 32,748 行 | FastAPI 路由处理器 |
| **后端服务层** | 19 个服务 | - | 核心业务逻辑 |
| **数据模型** | 21 个模型 | - | SQLAlchemy ORM 模型 |
| **数据库迁移** | 31 个版本 | - | Alembic 迁移脚本 |
| **前端页面** | 44 个页面 | 34,343 行 | React 页面组件 |
| **前端组件** | 34 个组件 | - | 可复用 UI 组件 |
| **脚本工具** | 15 个 Python 脚本 | - | 数据修复/迁移工具 |
| **Shell 脚本** | 9 个脚本 | - | 部署/备份/运维脚本 |

## 四、核心功能模块

### 业务模块（按复杂度排序）

| 模块 | 文件 | 行数 | 功能说明 |
|------|------|------|----------|
| 📊 **报表系统** | reports.py | 183,267 | 财务报表、业务报表、对账报表 |
| 💰 **财务管理** | finance.py | 33,286 | 收款、付款、银行对账、财务报表 |
| 🏭 **成品管理** | finished_products.py | 51,473 | 成品入库、出库、库存管理 |
| 📦 **仓库管理 V2** | warehouse_v2.py | 22,876 | 多仓库、批次追踪、库存预警 |
| 🐟 **三文鱼销售** | sales.py | 29,283 | 销售订单、客户管理、收款跟踪 |
| 📝 **发票管理** | invoices.py | 35,597 | 发票开具、红冲、统计 |
| 🔄 **退货管理** | returns.py | 19,679 | 退货处理、退款、换货 |
| 🛒 **采购管理** | material_purchases.py | 14,573 | 原料采购、供应商管理 |
| 📋 **批次管理** | batches.py | 10,968 | 生产批次、质量追踪 |
| 🏢 **公司管理** | companies.py | 9,913 | 客户/供应商档案 |
| 🔪 **每日宰杀** | daily_slaughter.py | 5,705 | 生产计划、原料消耗 |
| 👥 **业务员管理** | salespersons.py | 9,729 | 业绩统计、提成计算 |
| 📦 **采购订单** | purchase_orders.py | 4,267 | 采购下单、到货跟踪 |
| 🔍 **审计日志** | audit.py | 3,456 | 操作审计、数据追踪 |
| 🔔 **通知系统** | notifications.py | 2,795 | 系统通知、提醒 |

### 前端页面模块

| 页面 | 功能 |
|------|------|
| Dashboard | 数据概览、关键指标 |
| SalesPage | 销售订单管理 |
| FinancePage | 财务收支管理 |
| ReportsPage | 多维度报表 |
| WarehouseV2Page | 仓库 V2 管理 |
| MaterialPurchasePage | 原料采购 |
| FinishedProductSales | 成品销售 |
| InvoicesPage | 发票管理 |
| ReturnsPage | 退货处理 |
| BatchesPage | 批次管理 |
| CompaniesPage | 客户/供应商 |
| AuditLogsPage | 审计日志 |
| NettingStatementsTab | 往来对账 |
| FinancialStatementsTab | 财务报表 |
| BatchReportsTab | 批次报表 |
| ... (共 44 个页面) | ... |

## 五、最近开发动态（最近 5 次提交）

| 提交 | 日期 | 说明 |
|------|------|------|
| 2801c2d | 2026-06-01 | chore: pre-deploy checkpoint — 预部署检查点 |
| 7d105d7 | 2026-06-01 | chore(deploy): 添加上线部署方案和操作手册 |
| f3bb175 | 2026-05-30 | feat(finished-product-sales): 重构成品销售弹窗 + 采购入库以销定采 |
| 8450371 | 2026-05-30 | feat(daily_slaughter): 宰杀锁定后自动入库成品肉和副产品到FB-FISH |
| 41f0b33 | 2026-05-29 | perf(reports): N+1查询优化 — 批量预加载替代循环内单查 |
| 2b7525e | 2026-05-29 | refactor(models): 拆分 models/__init__.py（1315行 → 11个子模块） |
| 1fe7a5d | 2026-05-28 | feat(frontend): 引入 decimal.js 安全金额运算工具 |

## 六、开发活跃度

### 代码变更统计（最近 5 次提交）

- **新增文件**: 161 个
- **新增代码行**: +28,436 行
- **删除代码行**: -2,489 行
- **净增量**: +25,947 行

### 开发重点

1. **部署准备**: 完善 Docker 生产配置、部署脚本、运维手册
2. **性能优化**: 报表系统 N+1 查询优化、模型拆分
3. **功能重构**: 成品销售弹窗、采购入库流程
4. **自动化**: 宰杀后自动入库成品
5. **金额安全**: 引入 decimal.js 防止浮点精度问题

## 七、部署架构

### 容器化配置

| 服务 | 配置 | 说明 |
|------|------|------|
| **后端** | Dockerfile + Dockerfile.prod | 多阶段构建 |
| **前端** | Dockerfile + nginx.conf | 静态资源服务 |
| **数据库** | PostgreSQL (生产) / SQLite (开发) | 数据持久化 |
| **缓存** | Redis | 会话缓存、任务队列 |
| **存储** | MinIO | 文件上传、图片存储 |
| **编排** | docker-compose.prod.yml | 生产环境编排 |

### 部署脚本

| 脚本 | 用途 |
|------|------|
| `deploy.sh` | 标准部署 |
| `deploy-native.sh` | 原生部署（无 Docker） |
| `backup.sh` | 数据备份 |
| `backup-db.sh` | 数据库备份 |
| `restore-db.sh` | 数据库恢复 |
| `rollback.sh` | 版本回滚 |
| `switch-env.sh` | 环境切换 |

## 八、项目文档

| 文档 | 说明 |
|------|------|
| `README.md` | 项目说明、快速启动 |
| `DEPLOYMENT.md` | 部署技术手册 |
| `DEPLOYMENT_GUIDE.md` | 部署操作指南 |
| `OPERATIONS.md` | 运维手册 |
| `AUDIT_REPORT.md` | 审计报告 |
| `COMPLETENESS_REVIEW_*.md` | 完整性审查报告 |
| `PROFIT_STATEMENT_REVIEW.md` | 利润表审查 |
| `FINANCIAL_STATEMENTS_REVIEW.md` | 财务报表审查 |

## 九、未提交的变更（Working Tree）

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `backend/Dockerfile.prod` | 修改 | 生产 Docker 配置 |
| `backend/app/api/v1/endpoints/finance.py` | 修改 | 财务 API |
| `backend/app/api/v1/endpoints/reports.py` | 修改 | 报表 API |
| `backend/app/api/v1/endpoints/returns.py` | 修改 | 退货 API |
| `backend/app/api/v1/endpoints/sales.py` | 修改 | 销售 API |
| `backend/app/api/v1/endpoints/sales_batch_collect.py` | 修改 | 批量收款 |
| `backend/app/main.py` | 修改 | 主入口 |
| `backend/app/schemas/finance.py` | 修改 | 财务 Schema |
| `backend/app/schemas/report.py` | 修改 | 报表 Schema |
| `backend/app/services/finance_service.py` | 修改 | 财务服务 |
| `backend/app/services/sales_service.py` | 修改 | 销售服务 |
| `backend/pyproject.toml` | 修改 | 依赖配置 |
| `docker/docker-compose.prod.yml` | 修改 | 生产编排 |
| `frontend/Dockerfile` | 修改 | 前端 Docker |
| `frontend/src/components/BatchCollectDialog.tsx` | 修改 | 批量收款弹窗 |
| `frontend/src/pages/BatchReportsTab.tsx` | 修改 | 批次报表 |
| `frontend/src/pages/FinancePage.tsx` | 修改 | 财务页面 |
| `frontend/src/pages/SalesPage.tsx` | 修改 | 销售页面 |
| `AUDIT_REPORT_2026-06-05.md` | 新增 | 审计报告 |
| `backend/refactor_reports.py` | 新增 | 报表重构脚本 |
| `backend/scripts/analyze_exchange_fee.py` | 新增 | 汇率费用分析 |
| `backend/scripts/check_sales_consistency.py` | 新增 | 销售一致性检查 |
| `backend/scripts/fix_sales_net_amount.py` | 新增 | 销售金额修复 |
| `data/` | 新增 | 数据目录 |
| `docker/.env.prod` | 新增 | 生产环境变量 |
| ... | ... | ... |

## 十、总结

Salmon PMS 是一个功能完整的三文鱼产业管理系统，覆盖了从采购、生产、销售到财务的全业务流程。项目采用现代化的前后端分离架构，具备以下特点：

✅ **功能完整**: 30+ API 端点、44 个前端页面、19 个服务层模块  
✅ **架构清晰**: 分层设计（API/Service/Model/Schema）  
✅ **部署就绪**: Docker 容器化、完整的部署脚本和文档  
✅ **持续迭代**: 91 次 Git 提交，活跃开发中  
✅ **质量保障**: 审计日志、数据一致性检查、修复脚本  

**下一步建议**: 将当前 working tree 的变更提交，完成部署准备。

---
*报告生成时间: 2026-06-09 13:32 GMT+8*  
*数据来源: Git 仓库、代码统计、配置文件*
