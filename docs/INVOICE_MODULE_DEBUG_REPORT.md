# 进口单证模块调试审查报告

> 审查时间: 2026-05-03 17:10
> 审查范围: 数据完整性、计算逻辑、前后端一致性

---

## 🚨 严重数据问题

### 1. Invoice #29 (8468) — 产品明细严重缺失

| 项目 | 发票级别 | 产品明细汇总 | 差异 |
|------|---------|-------------|------|
| 箱数 | 161 | 100 | ❌ 缺61箱 |
| 重量 | 3255.2kg | 2000kg | ❌ 缺1255.2kg |
| 金额 | $33766.06 | $1000 | ❌ 缺$32766 |

**问题**: 发票主表显示161箱，但产品明细只有1条记录（100箱三文鱼），缺失大量产品明细。

### 2. 25/26 张发票存在重量不匹配

| 发票号 | 发票重量 | 产品重量汇总 | 差额 |
|--------|---------|-------------|------|
| 8553 | 0 | 3125.3kg | -3125.3kg |
| 8412 | 7690kg | 6357.2kg | +1332.8kg |
| 8468 | 3255.2kg | 2000kg | +1255.2kg |
| 8663 | 3792kg | 3135.4kg | +656.6kg |
| 8689 | 3927kg | 3327.78kg | +599.22kg |

**模式**: 几乎所有发票的 `total_weight_kg`（发票级别）≠ 产品明细 `net_weight_kg` 汇总。

---

## ✅ 计算逻辑审查

### 金额计算公式

**数据库验证**:
```
产品金额 = net_weight_kg × unit_price（单价是每公斤价格）
```

例如 Invoice #25:
- 产品1: 2687kg × $10 = $26870 ✅
- 产品2: 640.78kg × $10 = $6407.80 ✅

**结论**: 金额计算逻辑正确（`total_amount = 重量 × 单价`）。

### 汇总逻辑

**后端 `invoice_service.py`**:
- `create()`: 自动从产品明细汇总 `total_amount_usd`, `total_boxes`, `total_weight_kg`
- `update()`: 重新计算并更新汇总字段

**前端 `InvoiceFormDialog.tsx`**:
- `onSubmit()`: 重新计算 `lineAmount = netWeight * unitPrice`
- 重新汇总 `tBoxes`, `tWeight`, `tAmount`
- 提交时覆盖用户输入的汇总值

**结论**: 代码逻辑正确，但**已有数据是用旧代码/错误方式录入的**。

---

## 🔍 前端显示审查

### 列表页 (`InvoicesPage.tsx`)

| 显示项 | 来源 | 状态 |
|--------|------|------|
| 发票编号 | `invoice_no` | ✅ |
| 发票日期 | `invoice_date` | ✅ |
| 加工厂 | `processing_plant_name` | ✅ |
| 总金额 | `total_amount_usd` | ✅ |
| 报关状态 | `customs_status` | ✅（Badge） |
| 购汇状态 | `exchange_status` | ✅（Badge） |
| 锁定状态 | `is_locked` | ✅（🔒图标） |

### 详情弹窗 (`InvoiceDetailDrawer.tsx`)

| 显示项 | 来源 | 状态 |
|--------|------|------|
| 基本信息 | 发票主表 | ✅ |
| 产品明细列表 | `products` | ✅ |
| 加工厂/渔场/出口商名称 | 关联查询 | ✅ |
| 锁定状态 | `is_locked` | ✅ |

### 表单页 (`InvoiceFormDialog.tsx`)

| 功能 | 实现 | 状态 |
|------|------|------|
| 产品规格下拉 | 从 `/products?category=whole_fish` 加载 | ✅ |
| 自动对应产品名称 | `specToProductMap` | ✅ |
| 金额自动计算 | `lineAmount = netWeight * unitPrice` | ✅ |
| 汇总自动计算 | `totalBoxes`, `totalWeight`, `totalAmount` | ✅ |
| 自动编号生成 | 后端 `generate_invoice_no()` | ✅ |

---

## ⚠️ 代码级问题

### 1. 前端 TypeScript 编译警告

| 文件 | 问题 | 影响 |
|------|------|------|
| `InvoiceFormDialog.tsx` | `useEffect` 导入未使用 | 无功能影响 |
| `InvoiceFormDialog.tsx` | `productNameOptions` 声明未使用 | 无功能影响 |
| `BatchesPage.tsx` | `DollarSign`, `Weight` 导入未使用 | 无功能影响 |

### 2. `total_amount` 字段冗余

- 前端计算了 `total_amount`，提交给后端
- 后端本应从 `net_weight_kg × unit_price` 重新计算，但实际使用了前端传的值
- **风险**: 如果前端计算有误，后端不会纠正

### 3. 产品明细缺失校验

- 后端没有校验发票必须有至少1条产品明细（前端有校验）
- 数据库中存在 Invoice #29 这种产品明细严重缺失的情况

---

## 🧪 数据修复建议

### 立即修复

1. **Invoice #29 (8468)** 需要补充产品明细，或重新录入
2. **所有发票的重量字段** 需要重新从产品明细汇总计算

### 脚本修复

```python
# 建议执行的数据修复脚本
for each invoice in import_invoices:
    products = get_products(invoice.id)
    
    invoice.total_boxes = sum(p.box_count for p in products)
    invoice.total_weight_kg = sum(p.net_weight_kg for p in products)
    invoice.total_amount_usd = sum(p.total_amount for p in products)
    
    # 同时修正每个产品的 total_amount
    for p in products:
        p.total_amount = p.net_weight_kg * p.unit_price
```

---

## 📋 功能验证清单

请逐项验证：

- [ ] **发票列表** — 26条记录正常显示
- [ ] **新增发票** — 产品明细金额自动计算正确
- [ ] **编辑发票** — 修改产品后汇总自动更新
- [ ] **详情弹窗** — 产品明细列表完整显示
- [ ] **锁定功能** — 锁定后禁止编辑/删除
- [ ] **批次关联** — 发票添加到批次正常
- [ ] **状态变更** — 报关/购汇状态可正常修改
- [ ] **批量导入** — Excel导入功能正常

---

## 🎯 需要用户确认

1. **Invoice #29 (8468)** 的数据是否需要修复？（产品明细缺失）
2. **重量不匹配**的问题是否需要批量修复？
3. 你希望我现在执行数据修复脚本吗？
