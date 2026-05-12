# Salmon PMS 项目审计报告

> 生成时间: 2026-05-11
> 范围: frontend/src/pages/ + backend/app/api/v1/endpoints/

---

## 一、模块完成度评分

| 模块 | 前端 | 后端 | 评分 | 状态 |
|------|------|------|------|------|
| **Dashboard** | ✅ 仪表盘 | ✅ API | 8/10 | 稳定 |
| **公司管理(Companies)** | ✅ CRUD | ✅ CRUD | 9/10 | 稳定 |
| **客户管理(Customers)** | ✅ CRUD | ✅ CRUD | 9/10 | 稳定 |
| **供应商(Suppliers)** | ✅ CRUD | ✅ (复用companies) | 8/10 | 稳定 |
| **产品管理(Products)** | ✅ CRUD | ✅ CRUD | 8/10 | 稳定 |
| **成品管理(FinishedProducts)** | ✅ CRUD | ✅ CRUD | 8/10 | 稳定 |
| **品牌(Brands)** | ✅ CRUD | ✅ CRUD | 9/10 | 稳定 |
| **发票(Invoices)** | ✅ 导入/清关 | ✅ CRUD | 8/10 | 稳定 |
| **批次(Batches)** | ✅ 批次+发票 | ✅ CRUD | 8/10 | 稳定 |
| **整鱼销售(Sales)** | ✅ 销售+收款 | ✅ CRUD | 8/10 | 稳定 |
| **成品销售(FinishedProductSales)** | ✅ CRUD | ✅ v1+v2 | 7/10 | 双版本 |
| **生产管理(Production)** | ✅ CRUD | ✅ | 8/10 | 稳定 |
| **物料管理(Materials)** | ✅ CRUD | ✅ CRUD | 8/10 | 稳定 |
| **库存(Warehouse)** | ✅ 出入库 | ✅ | 8/10 | 稳定 |
| **日屠宰(DailySlaughter)** | ✅ 记录 | ✅ | 7/10 | 可用 |
| **损耗记录(LossRecords)** | ✅ CRUD | ✅ | 8/10 | 稳定 |
| **银行账户(BankAccounts)** | ✅ CRUD | ✅ | 9/10 | 稳定 |
| **财务报表(Reports)** | ✅ 多维度 | ✅ 复杂 | 7/10 | 功能多但复杂 |
| **财务(Finance)** | ✅ 6个Tab | ✅ 完整 | 7/10 | **见问题#1-5** |
| **销售人员(Salespersons)** | ✅ CRUD | ✅ | 8/10 | 稳定 |
| **佣金(Commission)** | ✅ 计算 | ✅ | 7/10 | 可用 |
| **设置(Settings)** | ✅ 用户管理 | ✅ | 8/10 | 稳定 |
| **通知(Notifications)** | ✅ 列表 | ✅ | 7/10 | 基础功能 |
| **登录(Login)** | ✅ 认证 | ✅ JWT | 9/10 | 稳定 |

---

## 二、严重问题 🔴

### 1. FinancePage.tsx `related_sale_ids` 类型与存储格式不匹配

**问题**: `related_sale_ids` 在后端数据库中是 JSON text 字段，但 FinancePage.tsx 中有两处处理不一致：

- **行 1563**: `setSelectedSaleIds(transaction.related_sale_ids ?? [])` — 假设是数组
- **后端 model**: `related_sale_ids: Mapped[Optional[str]] = mapped_column(Text)` — 实际是 JSON 字符串

**风险**: 编辑时回显销售单选择状态可能失效；批量创建收款时 `related_sale_ids` 传递格式错误。

**建议**: 统一在 API response 层做 JSON 序列化/反序列化，确保前端始终拿到 `number[]`。

---

### 2. 交易流水筛选 `filterSaleId` 为空字符串时仍发请求

**问题**: `filterSaleId` 是字符串类型（`useState("")`），输入框清空后值为 `""`，但 API 参数判断：
```tsx
if (filterSaleId) params.append("related_sale_id", filterSaleId);
```
这没问题。但如果用户输入 `0` 会有 bug（`"0"` 是真值但后端可能找不到 ID 为 0 的记录）。

**建议**: 添加 `.trim()` 并处理非数字输入。

---

### 3. 后端 `list_transactions` JSON 模糊匹配效率低

**问题**: `finance_service.py` 中对 `related_sale_ids` 使用 4 个 LIKE 条件做 JSON 文本匹配：
```python
json_filter = or_(
    TransactionRecord.related_sale_ids == f"[{sid}]",
    TransactionRecord.related_sale_ids.like(f"[{sid},%"),
    TransactionRecord.related_sale_ids.like(f"%,{sid}]"),
    TransactionRecord.related_sale_ids.like(f"%,{sid},%"),
)
```

**风险**: 无法利用索引，数据量大时性能差。JSON text 字段没有 GIN 索引支持。

**建议**: 改为独立的关联表 `transaction_sale_links` 做外键关联，或至少使用 PostgreSQL JSONB 类型 + GIN 索引。

---

### 4. `FinancePage.tsx` 分类筛选后未同步重置子分类

**问题**: 类型/分类级联逻辑只在表单里处理（`setType` 时 `setCategory("")`），但筛选栏里的类型/分类没有级联：
- 选择类型"收入"后，分类下拉仍显示支出分类
- 用户可能选到无效组合

**建议**: 筛选栏也添加级联逻辑，或根据 `filterType` 过滤分类选项。

---

### 5. `allSalesData` 加载 500 条做映射表可能内存问题

**问题**: 
```tsx
const { data: allSalesData } = useQuery({
  queryKey: ["all-sales-for-transaction-list"],
  queryFn: async () => {
    const res = await api.get("/v1/sales/whole-fish?limit=500");
    return res.data?.items || [];
  },
});
```

销售单量大时 500 条不够，且全部加载到前端内存做映射表不合理。

**建议**: 后端 `list_transactions` 直接 JOIN 返回 `related_sale_nos`，或按需懒加载。

---

## 三、数据格式不一致 ⚠️

| 位置 | 问题 | 详情 |
|------|------|------|
| FinancePage 金额显示 | 混用 `en-US` 和 `zh-CN` | 表格用 `en-US`，汇总行用 `zh-CN`，千分位格式不统一 |
| 日期格式 | 前后端不一致 | 前端 `<Input type="date">` 用 ISO (`YYYY-MM-DD`)，后端接收 `date` 对象，转换逻辑分散 |
| Decimal/Numeric | 后端Decimal vs 前端number | `TransactionRecord.amount` 是 `Numeric(15,2)`，前端用 `Number()` 转换，大数值可能精度丢失 |
| 货币代码 | 大小写不统一 | 数据库默认 `CNY`，但部分硬编码检查用 `currency === "CNY"`，建议统一枚举 |
| 发票税率 | 百分比 vs 小数 |  unclear whether 13% is stored as 0.13 or 13 in different modules |

---

## 四、下拉框/选择器问题 🎛️

| 位置 | 问题 | 状态 |
|------|------|------|
| FinancePage 类型筛选 | 切换类型后分类未联动过滤 | ⚠️ 待修复 |
| FinancePage 关联销售单 | 从下拉(500条)改为输入框 | ✅ 已修复 |
| FinancePage 客户选择器 | 自定义下拉，点击外部关闭逻辑有 z-index 竞争 | ⚠️ 偶发问题 |
| SalesPage 客户选择 | 不同页面客户选择组件重复实现 | ⚠️ 建议抽象为通用组件 |
| 银行账户选择 | 多页面重复 `getBankAccountName` 逻辑 | ⚠️ 建议提取工具函数 |
| 分类映射 | `transactionCategoryMap` 等硬编码在页面里，未集中管理 | ⚠️ 维护困难 |

---

## 五、各模块快速评估

### 高完成度 (8-9分)
- **Companies/Customers/Suppliers/Brands/BankAccounts**: 标准CRUD，无异常
- **Login/Settings**: 功能完整，JWT认证正常

### 中等完成度 (6-7分)
- **Finance**: 功能最多但复杂度高，存在上述5个问题
- **Reports**: 2441行后端，功能极多但维护困难
- **FinishedProductSales**: v1+v2 双API，前端可能调用不一致
- **Commission**: 计算逻辑复杂，需验证边界情况

### 需要关注
- **FinancePage 交易流水Tab**: `TransactionsTab` 之前被截断过，虽然已修复，但代码 2200+ 行，建议拆分组件
- **Dashboard**: 数据聚合查询多，慢查询风险

---

## 六、建议修复优先级

| 优先级 | 问题 | 文件 |
|--------|------|------|
| P0 | `related_sale_ids` JSON 字符串/数组类型不匹配 | backend model + frontend |
| P1 | 交易流水筛选分类未联动 | FinancePage.tsx |
| P1 | JSON text LIKE 查询性能 | finance_service.py |
| P2 | 金额格式化统一 `zh-CN` | FinancePage.tsx |
| P2 | `allSalesData` 500条限制 | FinancePage.tsx + backend |
| P3 | 客户选择器组件抽象复用 | 多页面 |
| P3 | 分类映射集中管理 | 新建 constants 文件 |

---

*报告结束*
