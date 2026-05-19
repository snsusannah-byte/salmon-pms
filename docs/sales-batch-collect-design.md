# 销售单功能栏 + 合并收款 + 交易流水编辑设计方案

**日期**: 2026-05-15  
**需求**: 
1. 销售单列表加功能栏
2. 合并收款功能从交易流水迁移到销售单页面
3. 交易流水仅允许编辑已产生的销售收款

---

## 一、销售单功能栏设计

### 当前界面
```
┌─────────────────────────────────────────────────────────────┐
│ 整鱼销售管理                              [新建] [批量导入]  │
├─────────────────────────────────────────────────────────────┤
│ 销售单号    客户    规格    重量(kg)    金额    已付    状态 │
│ XS2026...   张三    7-8kg   6120.38    ¥XXX   ¥XXX   已完成 │
│ ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

### 新界面（增加功能栏）
```
┌─────────────────────────────────────────────────────────────┐
│ 整鱼销售管理                              [新建] [批量导入]  │
├─────────────────────────────────────────────────────────────┤
│ [全选] 已选中 3 个销售单                                    │
│                                                         │
│   [合并收款] [批量删除] [导出Excel]                         │
│   (仅勾选未收款的销售单时"合并收款"可用)                     │
├─────────────────────────────────────────────────────────────┤
│ ☑ 销售单号    客户    规格    重量(kg)    金额    已付    状态│
│ ☑ XS2026...   张三    7-8kg   6120.38    ¥XXX   ¥XXX   已完成│
│ ☐ XS2026...   李四    7-8kg   5000.00    ¥XXX   ¥0     未收款│
│ ☐ XS2026...   王五    7-8kg   3000.00    ¥XXX   ¥0     未收款│
└─────────────────────────────────────────────────────────────┘
```

### 功能栏交互
- **合并收款**: 勾选 ≥2 个销售单，且所有选中销售单都有未收金额时启用
- **批量删除**: 勾选 ≥1 个销售单时启用（仅限未锁定/未收款）
- **导出Excel**: 始终可用，导出当前筛选结果

---

## 二、合并收款功能（从交易流水迁移到销售单）

### 业务流程
```
销售单列表页
  ├── 用户勾选 3 个未收款销售单
  ├── 点击 [合并收款]
  └── 弹出收款确认弹窗
        ├── 显示选中的销售单列表
        ├── 自动计算：总金额 = Σ(净金额 - 已付金额)
        ├── 选择银行账户
        ├── 填写收款日期（默认今天）
        ├── 自动设置：category = "main_business_revenue"
        └── [确认收款] / [取消]
  
  提交后：
    ├── 创建 1 条 transaction record
    │     ├── type = "income"
    │     ├── category = "main_business_revenue"
    │     ├── amount = 总金额
    │     ├── related_sale_ids = [sale1.id, sale2.id, sale3.id]
    │     └── counterparty_name = 客户名称（多个用逗号分隔）
    ├── 更新每个销售单的 paid_amount += 各自应收金额
    └── 刷新销售单列表
```

### 收款分配逻辑
```
总金额 = 销售单A应收 + 销售单B应收 + 销售单C应收

销售单A应收 = net_amount_A - paid_amount_A
销售单B应收 = net_amount_B - paid_amount_B
销售单C应收 = net_amount_C - paid_amount_C

创建 transaction 时：
  related_sale_ids = [A.id, B.id, C.id]
  amount = 总金额

更新销售单：
  A.paid_amount += A应收
  B.paid_amount += B应收
  C.paid_amount += C应收
```

### 与现有交易流水的关系
- 合并收款本质上是创建一条 `category = "main_business_revenue"` 的交易流水
- 只是入口从"交易流水页手动填写"改为"销售单页勾选自动生成"
- 生成的交易流水可以在交易流水页面查看、锁定

---

## 三、交易流水编辑功能设计

### 问题：是否允许编辑已产生的销售收款？

**可行，但有条件和限制。**

### 允许编辑的范围

| 字段 | 是否可编辑 | 说明 |
|------|-----------|------|
| **交易日期** | ✅ 允许 | 仅修改日期，不影响销售单 |
| **银行账户** | ✅ 允许 | 改从哪个账户收款，不影响金额 |
| **描述** | ✅ 允许 | 备注信息 |
| **参考号** | ✅ 允许 | 银行流水号等 |
| **对方名称** | ✅ 允许 | 客户名称 |
| **关联销售单** | ❌ 不允许 | 增删销售单会导致 paid_amount 重新分配，复杂且易出错 |
| **金额** | ⚠️ 限制允许 | 见下方"金额修改方案" |

### 金额修改方案（两种选择）

#### 方案A：不允许改金额（最安全）
- 编辑时金额字段只读
- 如需改金额，删除该交易流水后重新收款
- **优点**：100% 数据一致性，无副作用
- **缺点**：用户体验稍差（需要删了重建）

#### 方案B：允许改金额，自动重新分配（推荐）
- 编辑时可以改金额
- 保存时按**原应收比例**重新分配 paid_amount

```
原总金额 = ¥10,000（A:¥6,000 + B:¥4,000）
新总金额 = ¥9,000

分配比例：
  A 占 60% → A.paid_amount = ¥9,000 × 60% = ¥5,400
  B 占 40% → B.paid_amount = ¥9,000 × 40% = ¥3,600

更新：
  A.paid_amount 从 ¥6,000 改为 ¥5,400
  B.paid_amount 从 ¥4,000 改为 ¥3,600
```

**方案B的优点**：
- 用户体验好，直接修改即可

**方案B的弊端**：
1. **并发风险**：多人同时编辑同一笔收款可能导致 paid_amount 计算错误
2. **历史追溯困难**：改了金额后，销售单的收款历史看起来不连贯
3. **售后场景冲突**：如果销售单已有售后调整，改金额可能导致净额计算混乱
4. **实现复杂度**：需要写额外的 Service 逻辑处理重新分配

### 我的建议

**采用方案A的变体：软编辑**
- 允许编辑日期、银行账户、描述、参考号（不影响金额）
- **金额字段显示但不可编辑**
- 如需改金额，提供"删除并重新收款"按钮
- 删除时自动：
  1. 将该交易流水的 related_sale_ids 清空
  2. 对应销售单的 paid_amount 减去各自应收
  3. 删除 transaction record
  4. 用户回到销售单页面重新收款

这样既安全，用户体验也不错。

---

## 四、技术实现方案

### 1. 销售单功能栏 + 合并收款

**前端改动** (`SalesPage.tsx`):
```tsx
// 新增状态
const [selectedSaleIds, setSelectedSaleIds] = useState<number[]>([]);
const [batchCollectOpen, setBatchCollectOpen] = useState(false);

// 勾选处理
const toggleSelectSale = (id: number) => {
  setSelectedSaleIds(prev => 
    prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
  );
};

// 功能栏
{selectedSaleIds.length > 0 && (
  <div className="flex items-center gap-2 py-2">
    <span>已选中 {selectedSaleIds.length} 个</span>
    <Button onClick={() => setBatchCollectOpen(true)} 
            disabled={!canCollect(selectedSaleIds)}>
      合并收款
    </Button>
    <Button variant="destructive" onClick={handleBatchDelete}>
      批量删除
    </Button>
  </div>
)}

// 合并收款弹窗
<BatchCollectDialog
  open={batchCollectOpen}
  sales={selectedSales}
  onConfirm={handleBatchCollect}
/>
```

**后端改动** (`sales.py`):
```python
@router.post("/sales/batch-collect")
async def batch_collect_sales(
    sale_ids: List[int],
    bank_account_id: int,
    collect_date: date,
    db: AsyncSession = Depends(get_db),
):
    """合并收款：勾选多个销售单，一键收款"""
    # 1. 查询所有销售单
    sales = await db.execute(select(WholeFishSale).where(WholeFishSale.id.in_(sale_ids)))
    sales = list(sales.scalars().all())
    
    # 2. 计算各自应收金额
    total_amount = Decimal("0")
    sale_amounts = {}
    for sale in sales:
        receivable = sale.net_amount - sale.paid_amount
        if receivable <= 0:
            raise HTTPException(400, f"销售单 {sale.sale_no} 已收齐")
        sale_amounts[sale.id] = receivable
        total_amount += receivable
    
    # 3. 创建交易流水
    transaction = TransactionRecord(
        type="income",
        category="main_business_revenue",
        amount=total_amount,
        related_sale_ids=list(sale_ids),
        to_account_id=bank_account_id,
        transaction_date=collect_date,
        counterparty_name=", ".join([s.customer.name for s in sales]),
    )
    db.add(transaction)
    
    # 4. 更新销售单 paid_amount
    for sale in sales:
        sale.paid_amount += sale_amounts[sale.id]
    
    await db.commit()
    return {"transaction_id": transaction.id, "total_amount": total_amount}
```

### 2. 交易流水编辑限制

**前端改动** (`FinancePage.tsx`):
```tsx
// 判断是否可以编辑
const canEdit = (record: Transaction) => {
  // 只允许编辑未锁定的、category为销售收款的交易
  return !record.is_locked && 
         (record.category === "main_business_revenue" || record.category === "customer_deposit");
};

// 编辑弹窗中，金额字段根据类型决定是否可编辑
<Input 
  value={amount}
  readOnly={category === "main_business_revenue"}  // 销售收款金额不可改
  // ...
/>
```

**后端改动** (`finance.py`):
```python
@router.put("/transactions/{record_id}")
async def update_transaction(
    record_id: int,
    data: TransactionRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    record = await db.get(TransactionRecord, record_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    
    # 锁定后不能编辑
    if record.is_locked:
        raise HTTPException(400, "已锁定的交易不能编辑")
    
    # 只允许编辑特定分类
    if record.category not in ["main_business_revenue", "customer_deposit"]:
        raise HTTPException(400, "该类型交易不允许编辑")
    
    # 销售收款不能改金额（如需改金额请删除重建）
    if data.amount is not None and data.amount != record.amount:
        raise HTTPException(400, "销售收款金额不能修改，请删除后重新收款")
    
    # 允许改其他字段
    if data.transaction_date: record.transaction_date = data.transaction_date
    if data.to_account_id: record.to_account_id = data.to_account_id
    if data.description: record.description = data.description
    if data.reference_no: record.reference_no = data.reference_no
    
    await db.commit()
    return record
```

---

## 五、实施计划

| 优先级 | 任务 | 预计时间 | 依赖 |
|--------|------|---------|------|
| 🔴 P0 | 销售单功能栏（勾选框 + 合并收款按钮） | 2h | 无 |
| 🔴 P0 | 合并收款弹窗 + API | 3h | 功能栏 |
| 🟡 P1 | 交易流水编辑限制（分类检查 + 金额保护） | 1h | 无 |
| 🟡 P1 | 交易流水删除重建流程 | 1h | 编辑限制 |
| 🟢 P2 | 批量删除销售单（Dialog确认） | 1h | 功能栏 |

---

## 六、总结

**合并收款功能**：可行，从销售单页面勾选 → 一键收款，用户体验更好。生成的交易流水和手动创建的一样。

**交易流水编辑**：
- **可行**，但建议限制编辑范围
- **最佳方案**：允许编辑日期/银行/描述，不允许改金额和关联销售单
- **如需改金额**：提供"删除并重建"按钮，自动回退 paid_amount
- **弊端可控**：只要不允许改金额，数据一致性就不会被破坏

**下一步**：用户确认方案后，按 P0 → P1 → P2 顺序开发。
