# Salmon-PMS 三大报表模块审查报告

## 📋 审查范围
- **后端**: `backend/app/api/v1/endpoints/reports.py` (~1100行)
- **模型**: `backend/app/schemas/report.py`
- **前端**: `frontend/src/pages/ReportsPage.tsx` (FinancialStatementsTab)

---

## 🔴 严重问题（数据准确性风险）

### 1. 利润表——全量数据硬编码，无视查询周期 【致命】

**位置**: `get_financial_statements()` 第 ~950 行

**问题描述**:
利润表遍历 **所有已购汇批次** (`purchased_batch_ids`)，**完全不按用户选择的周期过滤**。

```python
# 获取所有已购汇批次（利润表用）——没有任何日期过滤！
exchange_batch_result = await db.execute(
    select(ExchangeRecord.batch_id)
    .where(ExchangeRecord.batch_id.isnot(None))
    .distinct()
)
purchased_batch_ids = [r[0] for r in exchange_batch_result.all() if r[0]]

for batch_id in purchased_batch_ids:
    # 销售、购汇、税费、清关、损耗——全部累加
    # ... 完全无视 sdt / edt 周期参数 ...
```

**影响**:
无论用户选择"本季度"还是"上年度"，利润表永远显示 **全部历史累计数据**。

**修复建议**:
```python
# 按周期过滤批次
batch_result = await db.execute(
    select(Batch.id)
    .join(BatchInvoice, BatchInvoice.batch_id == Batch.id)
    .join(ImportInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
    .where(ImportInvoice.invoice_date >= sdt)
    .where(ImportInvoice.invoice_date <= edt)
    .where(ImportInvoice.exchange_status == ExchangeStatus.COMPLETED)
    .distinct()
)
purchased_batch_ids = [r[0] for r in batch_result.all()]
```

---

### 2. 现金流量表——销售现金流入按"权责发生制"而非"收付实现制" 【严重】

**位置**: `get_financial_statements()` 第 ~1080 行

**问题描述**:
```python
period_sales_result = await db.execute(
    select(
        func.sum(WholeFishSale.gross_amount).label("total_sales"),
        ...
    )
    .where(WholeFishSale.sale_date >= sdt, WholeFishSale.sale_date <= edt)
)
cash_from_sales = row[0] - row[1] - row[2] - row[3]
```

现金流量表的销售流入用的是 **销售单的 gross_amount**，而不是 **实际收款金额**。这是权责发生制（Accrual），但现金流量表必须采用 **收付实现制（Cash Basis）**。

**影响**:
客户赊账的销售也被算成当期现金流入，严重高估经营活动现金流。

**修复建议**:
```python
# 应基于 SalesReceipt 表统计实际收款
select(func.sum(SalesReceipt.amount))
.where(SalesReceipt.receipt_date >= sdt, SalesReceipt.receipt_date <= edt)
# 或者基于 sale.paid_amount 累计
```

---

### 3. 资产负债表——货币资金计算口径混乱 【严重】

**位置**: `get_financial_statements()` 第 ~1020 行

**问题描述**:
```python
cash_balance = round(
    opening_balance                # 银行期初（全量）
    + paid_sales                   # 已收销售款（截至 end_date）
    + daily_income_total           # 日常收入（截至 end_date）
    - daily_expense_total          # 日常支出（截至 end_date）
    - exchange_total               # 购汇支出（全量历史！）
    - import_fees                  # 进口费用（全量历史！）
, 2)
```

`exchange_total` 和 `import_fees` 是 **全量累加**，而 `paid_sales` / `daily_income` / `daily_expense` 只到 `end_date`。

**影响**:
资产负债表货币资金 = 期初 + 截止到某日收入 - 全部历史支出。数字不可能对。

**修复建议**:
统一口径：全部按 `<= edt` 时间点快照计算。

---

### 4. 现金流量表税费查询 INNER JOIN 导致数据丢失 【中等】

**位置**: `get_financial_statements()` 第 ~1095 行

**问题描述**:
```python
select(...)
.join(ImportInvoice, ImportTax.invoice_id == ImportInvoice.id)
.join(ClearanceCost, ClearanceCost.invoice_id == ImportInvoice.id)  # ← 这里！
.where(ImportInvoice.invoice_date >= sdt, ImportInvoice.invoice_date <= edt)
```

`ImportTax` 和 `ClearanceCost` 同时 INNER JOIN，意味着：
- 有税单但无清关费的发票 → **被丢弃**
- 有清关费但无税单的发票 → **被丢弃**

**影响**:
税费和清关费的现金流统计不完整。

**修复建议**:
拆成两个独立查询，或改用 LEFT JOIN + COALESCE。

---

## 🟡 中等问题（逻辑缺陷）

### 5. 存货/应付账款估值汇率写死为 7.0

**位置**: 资产负债表 ~1040 行

```python
inventory_value = round(total_uncleared * Decimal("7"), 2)
accounts_payable = round(total_owed * Decimal("7"), 2)
```

未报关/未购汇发票的存货和应付，**固定按 7.0 汇率折算**，不考虑发票自身预估汇率。

**建议**: 优先使用 `invoice.estimated_exchange_rate`，回退到 7.0。

---

### 6. 资产负债表"当前系统状态"公式错误

**位置**: `balance_sheet.items` 最后一行

```python
FinancialStatementItem(
    label="当前系统状态",
    amount=round(total_assets - accounts_payable + cumulative_profit, 2),
    ...
)
```

正确公式应为 **资产 = 负债 + 权益**，即验证：
```
total_assets - total_liabilities - owners_equity == 0
```

当前写的是 `assets - payable + profit`，数学含义不明。

---

### 7. 利润表 `total_other` 永远是 0

**位置**: 利润表计算段

```python
total_other = Decimal("0")
# ... 没有任何地方给它赋值 ...
sales_expenses = ... + total_other + retail_cost
```

有一个占位字段但从无数据灌入。

---

### 8. 佣金逻辑双轨制，可能不一致

**位置**: 多处

- 批次/单票财报中，佣金从 `CommissionRecord` 表查询
- 三大报表利润表中，佣金直接累加 `sale.commission` 字段

如果 `WholeFishSale.commission` 和 `CommissionRecord` 不同步，利润表与批次财报数据会 **对不上**。

**建议**: 利润表也应查 `CommissionRecord` 表。

---

### 9. 损耗(Shrinkage)计算重复代码过多

损耗逻辑在 `reports.py` 中至少出现了 **6 次**，完全复制粘贴：
1. `_calculate_invoice_report_data()`
2. `list_batch_reports()`
3. `get_batch_report()`
4. `list_invoice_reports()`
5. `get_invoice_report()`
6. `get_financial_statements()`

任何一次汇率取法或四舍五入规则的修改，都要改 6 处，极易遗漏。

---

## 🟢 一般问题（性能/可维护性）

### 10. N+1 查询严重

几乎每个循环里都有：
```python
for inv in invoices:
    tax = await _get_invoice_taxes(db, inv.id)          # 1次查询
    clearance = await _get_invoice_clearance(db, inv.id)  # 1次查询
    exchange = await _get_invoice_exchange(db, inv.id)    # 1次查询
```

20 张发票 = 60 次额外查询。可改为 JOIN + 内存分组。

---

### 11. 前端 Decimal 精度隐患

前端直接用 `Number()` 转换金额：
```javascript
Number(detailData.total_exchange_payment || 0) + Number(detailData.total_exchange_fee || 0)
```

对于大金额（如 ¥9,449,761.28），JavaScript Number 的浮点精度可能造成 **分位误差**。

**建议**: 金额运算使用 `decimal.js` 或字符串处理。

---

### 12. 利润表零售模块未接入真实数据

前端显示：
```
2. 零售销售收入 (待开发)
零售销售成本 (待开发)
```

`retail_revenue` 和 `retail_cost` 依赖用户手动输入，无系统数据源。

---

## 📊 数据流总结

| 报表 | 主要数据源 | 关键问题 |
|------|-----------|---------|
| **利润表** | WholeFishSale, ExchangeRecord, ImportTax, ClearanceCost, TransactionRecord | **无视周期**，全量累加 |
| **资产负债表** | BankAccount, WholeFishSale, TransactionRecord, ImportInvoice | **货币资金口径混乱**，汇率固定7.0 |
| **现金流量表** | WholeFishSale, ExchangeRecord, TransactionRecord, ImportTax, ClearanceCost | **销售流入非实收**，税费JOIN丢数据 |

---

## ✅ 优先修复建议

1. **【P0】利润表增加周期过滤** — 按 `invoice_date / sale_date / exchange_date` 限定批次范围
2. **【P0】现金流量表改用实收实付** — 销售流入查 `SalesReceipt`，税费清关拆独立查询
3. **【P0】资产负债表统一口径** — 货币资金全部按 `<= edt` 快照计算
4. **【P1】资产负债表汇率优化** — 存货/应付优先用 `estimated_exchange_rate`
5. **【P1】佣金统一取 CommissionRecord** — 消除双轨制
6. **【P2】提取损耗计算为公共函数** — 消除 6 处重复代码
7. **【P2】优化 N+1** — 批量 JOIN 取税单/清关/购汇数据

---

*审查人: AI Assistant*  
*时间: 2026-05-19*
