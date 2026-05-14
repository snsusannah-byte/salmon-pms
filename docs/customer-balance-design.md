# 客户预付款余额管理方案

## 背景

当前收款流程的问题：
- `SalesReceipt` 必须绑定到具体 `WholeFishSale`（整鱼销售单）
- 客户打预付款时，没有对应的销售单可以绑定
- 后面开销售单时，无法从客户已有预付款中扣款
- `Company` 只有 `credit_limit`（信用额度），没有实际余额字段

## 目标

1. 支持登记客户预付款（不绑定销售单）
2. 支持销售单从客户余额中扣款
3. 支持混合收款（余额 + 现金/转账）
4. 余额变动全程可审计

## 方案概述

**轻量方案：Company 加余额字段 + TransactionRecord 做审计**

不动大模型，改动控制在最小范围：
- `Company` 表新增 `prepaid_balance` 字段
- `TransactionCategory` 新增 `customer_deposit` / `balance_deduction`
- `SalesReceipt.payment_method` 新增 `"balance"` 选项
- 所有余额变动通过 Service 层统一处理，保证一致性

## 详细设计

### 1. 数据模型变更

```python
# models/__init__.py - Company
class Company(Base):
    # ... 现有字段 ...
    prepaid_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), default=Decimal("0")
    )  # 客户预付款余额（仅 customer 类型有效）

# TransactionCategory 新增
class TransactionCategory(str, PyEnum):
    # ... 现有分类 ...
    CUSTOMER_DEPOSIT = "customer_deposit"       # 客户预付款
    BALANCE_DEDUCTION = "balance_deduction"     # 余额抵扣销售单
```

**Alembic 迁移**：仅给 `companies` 表加 `prepaid_balance` 字段（Numeric(15,2), default=0）

### 2. 业务流程

#### 流程 A：客户预付款登记

```
FinancePage → 新增交易流水
  │
  ▼
用户填写：
  - 类型：收入
  - 分类：客户预付款（新增）
  - 客户：选择客户（counterparty_id）
  - 收款账户：选择银行账户（to_account_id）
  - 金额、日期、备注
  │
  ▼
后端处理（finance_service.create_transaction）：
  1. 创建 TransactionRecord
     - type = income, category = customer_deposit
     - to_account_id = 银行账户
     - counterparty_id = 客户ID
     - related_sale_ids = null（不绑定销售单）
  2. 银行账户余额 += amount（现有逻辑）
  3. 客户预付余额 += amount
     - Company.prepaid_balance += amount
```

#### 流程 B：销售单从余额扣款

```
SalesPage → 销售单详情 → 收款
  │
  ▼
用户填写：
  - 收款方式：余额抵扣（新增选项）
  - 金额
  - 日期、备注
  │
  ▼
后端处理（sales_service.add_receipt）：
  1. 校验：客户余额 >= 扣款金额？
     - 不足则报错，不允许透支
  2. 创建 SalesReceipt
     - payment_method = "balance"
     - bank_account_id = null（不从银行扣款）
  3. 创建 TransactionRecord（用于审计）
     - type = transfer
     - category = balance_deduction
     - counterparty_id = 客户ID
     - related_sale_ids = [sale.id]
     - from_account_id / to_account_id = null（虚拟转账，不影响银行余额）
     - amount = 扣款金额
  4. 客户预付余额 -= amount
     - Company.prepaid_balance -= amount
  5. 更新销售单已付金额和状态
     - _update_paid_amount(sale)
```

#### 流程 C：混合收款（余额 + 现金）

```
分两步收款：
  第 1 步：余额抵扣 ¥5,000
  第 2 步：银行转账补齐 ¥1,000

最终：
  - sale.paid_amount = ¥6,000
  - Company.prepaid_balance -= ¥5,000
  - BankAccount.current_balance += ¥1,000
```

#### 流程 D：预付款退款

```
FinancePage → 新增交易流水
  - 类型：支出
  - 分类：non_business_expense（或新增 refund）
  - from_account_id = 银行账户
  - counterparty_id = 客户ID
  - amount = 退款金额
  │
  ▼
后端同时：Company.prepaid_balance -= amount
```

### 3. API 变更

#### 后端

**无需新增 API**，修改现有接口：

| 接口 | 修改 |
|------|------|
| `POST /api/v1/finance/transactions` | 支持 `category=customer_deposit`；创建时自动更新 `Company.prepaid_balance` |
| `POST /whole-fish/{sale_id}/receipts` | 支持 `payment_method="balance"`；校验余额充足；不关联银行账户 |
| `DELETE /whole-fish/{sale_id}/receipts/{receipt_id}` | 如果收款方式是 balance，恢复 Company.prepaid_balance |
| `GET /api/v1/companies` | 响应中增加 `prepaid_balance` |
| `GET /api/v1/companies/{id}` | 响应中增加 `prepaid_balance` |

**新增内部方法：**
- `CompanyService.adjust_balance(company_id, amount, reason)` - 统一调整余额入口
- `CompanyService.get_balance(company_id)` - 获取实时余额

#### 前端

| 页面 | 修改 |
|------|------|
| **FinancePage** | 交易分类下拉新增"客户预付款"；列表显示客户余额变动标记 |
| **SalesPage** | 收款方式下拉新增"余额抵扣"；选择时隐藏银行账户；显示客户当前余额提示 |
| **CompaniesPage** | 客户列表/详情显示 `prepaid_balance` |

### 4. 余额一致性保障

**问题**：`Company.prepaid_balance` 是缓存值，可能与 TransactionRecord 历史不一致。

**解决**：
1. **Service 层统一入口**：所有余额变动必须通过 `CompanyService.adjust_balance()`，禁止直接修改字段
2. **创建收款时事务包裹**：`prepaid_balance` 修改和 `SalesReceipt` 创建在同一个事务中
3. **定期对账**（可选）：通过 TransactionRecord 计算余额，与 Company.prepaid_balance 比对

```python
# 对账 SQL（可选 cron 任务）
SELECT c.id, c.name, c.prepaid_balance,
       COALESCE(SUM(CASE WHEN t.category = 'customer_deposit' THEN t.amount ELSE 0 END), 0)
       - COALESCE(SUM(CASE WHEN t.category = 'balance_deduction' THEN t.amount ELSE 0 END), 0)
       AS computed_balance
FROM companies c
LEFT JOIN transaction_records t ON t.counterparty_id = c.id
WHERE c.type = 'customer'
GROUP BY c.id
HAVING c.prepaid_balance != computed_balance
```

### 5. 边界情况

| 场景 | 处理 |
|------|------|
| 余额不足 | 拒绝余额扣款，提示"客户预付款余额不足，当前余额 ¥X" |
| 余额扣款后退款 | 删除 SalesReceipt 时恢复 prepaid_balance |
| 销售单取消 | 删除所有关联 SalesReceipt，自动恢复余额 |
| 多客户同名 | 通过 company_id 精确匹配，不依赖名称 |
| 负数余额 | 禁止，任何操作后 prepaid_balance < 0 时回滚 |

### 6. 实施步骤

1. **数据库迁移**：Company 表加 `prepaid_balance` 字段
2. **后端**：
   - 新增 TransactionCategory 枚举值
   - 修改 `FinanceService.create_transaction`：支持 customer_deposit，更新余额
   - 修改 `SalesService.add_receipt`：支持 balance 收款方式
   - 修改 `SalesService.delete_receipt`：恢复余额
   - Company schema 增加 `prepaid_balance` 字段
3. **前端**：
   - FinancePage 分类下拉新增"客户预付款"
   - SalesPage 收款方式新增"余额抵扣"，显示客户余额
   - CompaniesPage 显示预付余额
4. **测试**：
   - 预付款登记 → 余额正确
   - 销售单余额扣款 → 余额正确，销售单状态正确
   - 删除收款 → 余额恢复
   - 混合收款 → 银行余额 + 客户余额都正确

## 预估改动量

- 后端文件：~5 个（models, schemas, services, endpoints）
- 前端文件：~3 个（FinancePage, SalesPage, CompaniesPage）
- 数据库迁移：1 个
- 工作量：约 2-3 小时

## Q&A

**Q：为什么不通过 TransactionRecord 实时计算余额？**  
A：可以，但每个销售单扣款时都要查询该客户的所有历史交易，性能差。加一个字段缓存最实用。

**Q：balance_deduction 为什么是 transfer 类型而不是 expense？**  
A：因为预付款已经在到账时记为 income 了，余额抵扣只是内部资金划转（从客户预付款虚拟账户到主营业务收入），不重复影响银行余额。transfer 类型最准确。

**Q：成品销售（FinishedProductSale）是否支持？**  
A：当前 `SalesReceipt` 只关联 `WholeFishSale`。如需成品销售也支持余额扣款，需要扩展 `SalesReceipt` 的 `sale_id` 外键或新增 `finished_product_sale_id`。建议先支持整鱼销售，成品销售后续可复用同一套逻辑。
