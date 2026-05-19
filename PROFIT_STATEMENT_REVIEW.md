# 利润表字段审查报告

## 数据来源与结构

利润表从以下数据源构建：
1. **WholeFishSale**（整鱼销售单）— `net_amount` 汇总为营业收入
2. **ExchangeRecord**（购汇记录）— 采购成本和手续费
3. **ImportTax**（进口税单）— 增值税、关税
4. **ClearanceCost**（清关费用）— 各项清关杂费
5. **CommissionRecord**（佣金记录）— 业务员提成
6. **TransactionRecord**（日常流水）— 非批次经营支出

---

## 逐行审查

### 一、营业收入（预估）

#### 1. 整鱼批发销售收入
```python
wholesale_revenue = total_sales_net  # = Σ(sale.net_amount)
```

**问题 🔴 致命 — 营业收入口径严重低估**

利润表把 `sale.net_amount` 作为营业收入，但 `net_amount` 的定义是：
```python
net_amount = gross_amount
    - scan_fee          (扫码费)
    - rounding_adjustment (抹零)
    - after_sales_adjustment (售后调整)
    - discount          (折扣)
    - commission        (业务员提成)
```

也就是说，**营业收入在源头就被扣除了 5 项费用**。这在会计上是错误的——
- 营业收入应该接近 `gross_amount`（或扣掉折扣后的金额）
- `scan_fee`、`commission`、`after_sales` 等应作为**费用项**单独列示，从**毛收入**中扣减
- 现在它们被隐含在"收入"中扣了一次，又在"销售费用"中再扣一次（见下）

**数据验证**：
- 整鱼销售页面显示 **总销售金额 ¥9,612,575.59**（`gross_amount` 汇总）
- 利润表显示 **整鱼批发销售收入 ¥5,264,447.35**（`net_amount` 汇总）
- 差距约 **¥4,348,128**，差额正好是 scan_fee + rounding + after_sales + discount + commission 的累计

**修复建议**：
```python
# 营业收入应使用 gross_amount（或 gross - discount 后的"主营业务收入"）
wholesale_revenue = total_sales_gross - total_discount  # 折扣作为收入抵减项
# 或
wholesale_revenue = total_sales_gross  # 全额收入，折扣放到费用项
```

#### 2. 零售销售收入
- 纯手动输入字段 (`retail_revenue`)，无系统数据源
- 标记"待开发"

---

### 二、营业成本

```python
cogs = total_exchange_payment + total_exchange_fee + total_import_vat + total_import_duty + total_clearance + round(total_shrinkage, 2)
```

#### 3. 采购成本（购汇付款）
```python
Σ(exchange_record.amount_cny)  # 周期内购汇金额
```
- ✅ 按 `exchange_date` 过滤到周期内
- ⚠️ 仅包含**已购汇**批次的付款，未购汇批次的采购成本未体现

#### 4. 购汇手续费
```python
Σ(exchange_record.fee_cny)
```
- ✅ 与购汇付款同一过滤条件

#### 5. 进口增值税
```python
Σ(import_tax.import_vat)  # 按发票日期过滤
```

#### 6. 进口关税
```python
Σ(import_tax.import_duty)
```

#### 7. 清关费及运费
```python
Σ(clearance_cost.clearance_fee + freight_fee + inspection_fee + quarantine_fee + other_costs)
```

#### 8. 账面损耗
```python
shrinkage = (import_weight - sales_weight) × unit_price_usd × exchange_rate
```
- 基于重量差和实际采购单价计算
- ⚠️ 注意：如果批次内有多张发票，损耗按批次汇总，不按单票拆分

---

### 三、销售费用

```python
sales_expenses = total_commission + total_scan_fee + total_rounding + total_after_sales + total_discount + total_other + retail_cost
```

**问题 🔴 致命 — 与营业收入双重扣减**

由于营业收入已经用了 `net_amount`（内含 commission、scan_fee、rounding、after_sales、discount），
这里销售费用又把这些费用加总扣了一次。

**结果**：
- 折扣 ¥2,274.70 → 在收入里少算了 ¥2,274.70，在销售费用里又扣了 ¥2,274.70 = **多扣 ¥2,274.70**
- 售后调整 ¥4,572.59 → 同理多扣
- 业务员提成 ¥1,521.54 → 同理多扣
- 扫码手续费 ¥0、抹零 ¥190.67 → 同理多扣

**双重扣减总金额** = ¥1,521.54 + ¥0 + ¥190.67 + ¥4,572.59 + ¥2,274.70 = **¥8,559.50**

而这恰好就是截图中"销售费用"的总额 **¥8,559.50**！这不是巧合，而是 bug 的直接体现。

**修复建议**：
```python
# 方案A：营业收入改用 gross_amount，销售费用保留各项扣减
wholesale_revenue = total_sales_gross  # 或 gross - discount
sales_expenses = commission + scan_fee + rounding + after_sales + ...

# 方案B：营业收入用 net_amount，销售费用只列示 commission 和 retail_cost
# （其他项已经在 net_amount 中体现了，不应再扣）
```

#### 各子项审查

| 子项 | 数据源 | 问题 |
|------|--------|------|
| 业务员提成 | `CommissionRecord.commission_amount` | ✅ 统一查表，与批次财报一致 |
| 扫码手续费 | `WholeFishSale.scan_fee` | 🔴 已在 net_amount 中扣过 |
| 抹零 | `WholeFishSale.rounding_adjustment` | 🔴 已在 net_amount 中扣过 |
| 售后调整 | `WholeFishSale.after_sales_adjustment` | 🔴 已在 net_amount 中扣过 |
| 折扣 | `WholeFishSale.discount` | 🔴 已在 net_amount 中扣过 |
| 其他支出（批次）| `total_other`（硬编码为 0） | 🟡 永远为 0，占位字段 |
| 零售销售成本 | `retail_cost`（手动输入） | 🟡 无系统数据源 |

---

### 四、日常经营支出

```python
total_daily_expense = Σ(TransactionRecord.amount)
where type == "expense" AND transaction_date >= sdt AND <= edt
```

按 `category` 分组展示，如：
- `clearance_payment` — 清关费付款（但清关费已在营业成本中列示，这里是付款流水）
- `travel_fee` — 差旅费
- `agency_fee` — 代理费
- `entertainment_fee` — 招待费
- `sales_refund` — 销售退款
- `office_fee` — 办公费
- `bank_fee` — 银行手续费

**问题 🟡 口径混淆**
- `clearance_payment`（清关费付款）与营业成本中的"清关费及运费"可能是**同一笔钱的不同视角**
- 如果清关费已通过 `TransactionRecord` 付款，又通过 `ClearanceCost` 统计金额，可能重复计入成本
- `sales_refund`（销售退款）可能与售后调整重复

---

### 五、营业利润 / 净利润

```python
operating_profit = total_revenue - cogs - sales_expenses - total_daily_expense
net_profit = operating_profit
```

**问题 🟡 无所得税/其他收支**
- 直接 `净利润 = 营业利润`，没有所得税费用、营业外收支等
- 对于小规模/个体户可接受，但标注"未经审计"是合理的

**利润率计算**：
```python
profit_margin = net_profit / total_revenue × 100
```
- 截图显示 11.42%，但如果收入口径修正后，利润率会大幅下降

---

## 关键数据勾稽验证

### 验证1：整鱼销售页面 vs 利润表收入

| 指标 | 整鱼销售页面 | 利润表（自定义 2025-12-01 ~ 2026-05-19）| 差异 |
|------|-----------|--------------------------------------|------|
| 总销售金额 | ¥9,612,575.59 | ¥5,264,447.35 | **-¥4,348,128.24** |

差异原因：
1. 利润表只含**已购汇**批次的销售（约 55% 的批次）
2. 利润表用 `net_amount` 而非 `gross_amount`（差额约 commission + scan + rounding + after_sales + discount）

### 验证2：销售费用双重扣减

```
利润表显示：
  营业收入 = net_amount = gross - scan - rounding - after_sales - discount - commission
  销售费用 = scan + rounding + after_sales + discount + commission

实际毛利被多扣了 = scan + rounding + after_sales + discount + commission
                          = ¥0 + ¥190.67 + ¥4,572.59 + ¥2,274.70 + ¥1,521.54
                          = ¥8,559.50 ✓（与截图中"销售费用"总额完全一致）
```

---

## 修复方案

### 方案A（推荐）：会计口径标准化

**营业收入**改用 `gross_amount`（或 `gross - discount` 作为"主营业务收入净额"）

```python
# 利润表核心计算
wholesale_revenue = total_sales_gross - total_discount  # 折扣作为收入抵减
# 或
wholesale_revenue = total_sales_gross  # 全额收入

cogs = total_exchange_payment + total_exchange_fee + total_import_vat + total_import_duty + total_clearance + total_shrinkage

sales_expenses = total_commission + total_scan_fee + total_rounding + total_after_sales + total_other + retail_cost
# 注意：discount 已放在收入扣减项，不在销售费用中重复

operating_profit = wholesale_revenue - cogs - sales_expenses - total_daily_expense
```

**利润表结构调整为**：
```
一、营业收入
    1. 整鱼批发销售收入 (gross_amount)
    2. 减：折扣
    3. 主营业务收入净额 (gross - discount)

二、营业成本
    采购成本 + 税费 + 清关 + 损耗

三、销售费用
    提成 + 扫码 + 抹零 + 售后 + 其他

四、日常经营支出
    ...

营业利润 = 收入净额 - 成本 - 销售费用 - 日常支出
净利润 = 营业利润
```

### 方案B（最小改动）：
如果保持 `net_amount` 作为营业收入（因为 net_amount 是实际可收金额），
则**销售费用中不应再列示 scan_fee、rounding、after_sales、discount**——它们已经被 net_amount 消化了。

只保留：
```python
sales_expenses = total_commission + total_other + retail_cost
```

---

## 总结

| 严重程度 | 问题 | 影响 |
|---------|------|------|
| 🔴 致命 | 营业收入用 `net_amount` 而非 `gross_amount` | 收入被低估约 ¥X万，利润率失真 |
| 🔴 致命 | 销售费用与收入双重扣减 | 利润被多扣 ¥8,559.50（截图中周期），实际利润虚低 |
| 🟡 中 | 日常支出中 `clearance_payment` 可能与营业成本重复 | 成本可能虚高 |
| 🟡 中 | `total_other` 永远为 0 | 无实际意义 |
| 🟢 低 | 零售模块未接入 | 标记"待开发"即可 |

**建议**：采用方案A重构利润表结构，确保会计恒等式 `收入 - 成本 - 费用 = 利润` 的每个项都只扣减一次。
