# Salmon PMS 项目审查报告

**审查时间**: 2026-06-09 17:32  
**审查范围**: 未提交变更（working tree）vs 最新 commit (2801c2d)  
**版本**: V8.2 → 预部署候选版本

---

## 一、变更概览

| 维度 | 数值 | 说明 |
|------|------|------|
| **修改文件** | 19 个 | 含前后端、Docker、配置 |
| **新增文件** | 10+ 个 | 脚本、报告、修复工具 |
| **代码变更** | +1,478 / -6,596 行 | 净删除约 5,000 行（报表重构大幅简化）|
| **未跟踪文件** | 含备份文件、Python 脚本散落 frontend/src/pages | 需要清理 |

---

## 二、✅ 正面发现（值得肯定）

### 1. 核心功能增强

| 功能 | 文件 | 评价 |
|------|------|------|
| **余额抵扣** | `sales_batch_collect.py` | 批量收款支持余额抵扣，余额不足自动按实际可用抵扣，逻辑完整 ✅ |
| **删除预付款时撤销余额抵扣** | `finance_service.py` | 删除客户预付款交易时，自动撤销所有 `balance` 类型的 SalesReceipt 并重新计算状态，解决数据一致性问题 ✅ |
| **关联发票号自动查找** | `finance_service.py` + `schemas/finance.py` | 填写发票号如 `8353`，后端自动查找 `ImportInvoice.id`，提升用户体验 ✅ |
| **退货单接入认证** | `returns.py` | 从 `created_by_id = None` 改为 `current_user.id`，审计可追溯 ✅ |
| **权限系统接入** | `sales.py`, `sales_batch_collect.py` | 新增 `require_sales`, `require_finance` 依赖，安全性提升 ✅ |
| **报表系统重构** | `reports.py` | 累积利润计算逻辑从 ~120 行重复代码简化为调用 `_calc_batch_financials`，维护性提升 ✅ |
| **购汇估算** | `reports.py` | 未购汇批次自动估算汇率 6.8 + 手续费，报表展示更完整 ✅ |
| **Docker 端口安全** | `docker-compose.prod.yml` | PostgreSQL 5432→15432, Redis 6379→16379, MinIO 9000→19000，避免默认端口暴露 ✅ |
| **上传文件持久化** | `docker-compose.prod.yml` | 新增 `../backend/uploads:/app/uploads` 卷映射，退货附件不会丢失 ✅ |
| **Decimal 安全运算** | `sales_service.py` | 提成、净金额、收款状态使用 `Decimal` 精确计算，避免浮点精度问题 ✅ |

### 2. 代码质量改进

- **main.py 重复导入清理**：删除了重复的 `materials`, `material_categories`, `warehouse` 导入和注册
- **backend.log 清理**：从 git 中移除了 6090 行日志内容（日志文件不应在版本控制中）
- **N+1 查询优化**：报表系统使用批量预加载替代循环内单查

### 3. 测试状态

- 21 个测试全部通过（`test_permissions.py`）
- 14 个模型测试可收集（`test_models.py`）

---

## 三、⚠️ 需要关注的问题

### 1. 代码质量（高优先级）

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| **ruff 2909 个 lint 错误** | 全局 | 主要是 I001（import 排序），但其中 2318 个可自动修复 | 运行 `ruff check app/ --fix` 自动修复 |
| **未使用导入 F401** | `app/api/v1/__init__.py:31` | `finance_v4_migration` 导入但未注册 | 移除或添加 `as _` 显式导出 |
| **typing.List 已弃用** | `audit.py:1` | Python 3.12+ 推荐使用 `list` | 替换为 `list` |
| **字段 shadow 警告** | `schemas/sales.py:104` | `amount` 在 `WholeFishSaleItemResponse` 中 shadow 父类属性 | 重命名或明确覆盖意图 |
| **测试覆盖率极低** | `app/tests/` | 仅 21 个测试，核心业务（销售、财务、报表）无测试 | 补充关键路径测试 |

### 2. 数据与逻辑问题（中优先级）

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| **SalesReceipt 与 TransactionRecord 不一致** | 已修复 | 亘昌贸易 4 笔收款残留导致状态错误 | ✅ 已修复，但需检查其他客户是否也有类似问题 |
| **余额抵扣收款未关联交易流水** | `sales_batch_collect.py` | `balance` 类型收款不创建 `TransactionRecord`，导致银行对账时缺失 | 这是设计意图，但需确保前端/报表明确标注 |
| **commission 变化后 net_amount 重算** | `sales_service.py` | 提成变化后重新计算净金额，但 `paid_amount` 不变可能导致状态不一致 | 逻辑正确，但需确保抹零等调整也同步 |
| **delete_transaction 中缺少 `await db.commit()`** | `finance_service.py:985` | 删除交易时清零抹零后缺少 commit（已在 batch-delete 中处理）| 需要确认单条删除是否也需要 commit |

### 3. 安全与配置（中优先级）

| 问题 | 位置 | 影响 | 建议 |
|------|------|------|------|
| **backend 端口从 127.0.0.1:8000 改为 18000** | `docker-compose.prod.yml` | 从仅本机访问变为所有接口可访问 | 确认这是意图（通过防火墙/Nginx 控制），否则应恢复 `127.0.0.1:18000` |
| **Docker 端口映射不一致** | `docker-compose.prod.yml` | 数据库/Redis 仍有 `127.0.0.1:`，但 backend 没有 | 统一安全策略 |
| **.env.prod 未跟踪** | `docker/.env.prod` | 环境变量文件在 git 中，可能含敏感信息 | 确认是否应加入 `.gitignore` |

### 4. 文件管理（低优先级）

| 问题 | 文件 | 建议 |
|------|------|------|
| **备份文件在 git 中** | `BatchReportsTab.tsx.备份_含利润汇总` | 删除 |
| **Python 脚本散落在 frontend 目录** | `frontend/src/pages/add_net_sales.py` 等 | 移动到 `backend/scripts/` 或清理 |
| **临时修复脚本** | `clear_genchang_receipts.py`, `fix_genchang_status.py` | 修复完成后可删除或移入 `scripts/` |
| **PROJECT_REPORT 在仓库中** | `PROJECT_REPORT_2026-06-09.md` | 可保留，但建议用 `docs/` 目录管理 |

### 5. 前端问题（低优先级）

| 问题 | 位置 | 建议 |
|------|------|------|
| **BatchCollectDialog 中 `onSuccess` 未传递** | `BatchCollectDialog.tsx` | 接口定义了 `onSuccess?: () => void`，但调用方未传，不影响功能但类型不匹配 |
| **customer_id 重复检查** | `BatchCollectDialog.tsx:60` | `sales[0]?.customer_id || sales[0]?.customer_id` 是冗余表达式 |

---

## 四、🔴 高风险项

### 1. 端口暴露风险

`docker-compose.prod.yml` 中 backend 端口改为 `18000:8000`（无 `127.0.0.1` 限制），这意味着 backend 直接暴露在所有网络接口上。如果服务器没有防火墙，攻击面增大。

**建议**：
```yaml
# 当前（风险）
ports:
  - "18000:8000"

# 建议（安全）
ports:
  - "127.0.0.1:18000:8000"
```

### 2. 余额抵扣数据一致性

余额抵扣不创建 `TransactionRecord`，这导致：
- 银行对账时，收款明细和交易流水总额对不上
- 删除预付款时，需要额外扫描 `SalesReceipt` 表来撤销抵扣

当前已有处理逻辑，但这是一个**设计债务**——后续维护需要记住这种特殊关系。

### 3. 报表累积利润逻辑变更

`reports.py` 中累积利润计算从"仅 completed 批次"改为"所有批次"，且逻辑大幅简化。需要确认：
- 这是否会影响历史报表数据的准确性？
- 是否已通过 `check_sales_consistency.py` 等脚本验证？

---

## 五、📋 建议的提交前检查清单

```
□ 运行 ruff check app/ --fix 修复 import 排序和未使用导入
□ 删除 frontend/src/pages/*.py 临时脚本
□ 删除 BatchReportsTab.tsx.备份_含利润汇总
□ 确认 docker-compose.prod.yml 端口暴露是意图
□ 运行 pytest 确认所有测试通过
□ 清理 backend.log（已做，保持忽略）
□ 确认 .env.prod 不含真实密码（或使用占位符）
□ 删除 clear_genchang_receipts.py 等一次性修复脚本
□ 检查是否还有其他客户有残留的 SalesReceipt 问题
□ 提交并打 tag：git tag v8.2.1
```

---

## 六、评分

| 维度 | 评分 | 说明 |
|------|------|------|
| **功能完整性** | ⭐⭐⭐⭐⭐ | 余额抵扣、发票号查找、权限接入、报表重构都完整 |
| **代码质量** | ⭐⭐⭐☆☆ | 功能正确但 lint 错误多，需要自动修复 |
| **测试覆盖** | ⭐⭐☆☆☆ | 仅权限测试，核心业务无测试 |
| **安全性** | ⭐⭐⭐⭐☆ | 权限系统接入，但端口暴露需确认 |
| **部署就绪** | ⭐⭐⭐⭐☆ | Docker 配置完善，但需检查端口策略 |
| **数据一致性** | ⭐⭐⭐⭐☆ | 已修复已知问题，但余额抵扣设计债务存在 |

**总体评价**: 功能改动有价值，代码质量需要一轮自动修复，部署前需确认端口安全策略。建议修复后提交，打 tag 部署。

---

*审查人: OpenClaw Agent*  
*审查依据: git diff, ruff lint, pytest, 代码走读*
