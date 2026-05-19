# 退货模块设计补充 — 销售单关联与售后数据读取方案

## 一、用户关切的问题

1. **退货单和销售单如何关联？**
2. **销售单列表页的"售后"列如何正确读取退货数据？**

---

## 二、现有系统售后数据现状分析

### 2.1 后端模型关系

```
WholeFishSale
  ├─ receipts (SalesReceipt[])
  ├─ aftersales (AftersalesRecord[])     ← 现有简单售后记录
  └─ items (WholeFishSaleItem[])

FinishedProductSale
  ├─ receipts (FinishedProductReceipt[])
  ├─ aftersales_records (FinishedProductAftersales[])  ← 现有简单售后记录
  └─ items (FinishedProductSaleItem[])
```

### 2.2 前端展示逻辑（SalesPage.tsx）

**列表页表格：**
```tsx
// 售后数量徽章（红色小圆点）
{sale.aftersales && sale.aftersales.length > 0 && (
  <span className="...">{sale.aftersales.length}</span>
)}

// 售后金额列
{Number(sale.after_sales_adjustment) > 0 ? (
  <span className="text-red-500">-¥{sale.after_sales_adjustment}</span>
) : "-"}

// 汇总行
const totalAfterSales = data.items.reduce((s, it) => s + Number(it.after_sales_adjustment || 0), 0);
```

**详情弹窗 — 售后标签页：**
```tsx
<Button>售后记录 ({sale.aftersales.length + (Number(sale.after_sales_adjustment) > 0 ? 1 : 0)})</Button>

// 显示 aftersales 列表 + after_sales_adjustment 行
{sale.aftersales.map((a) => (...))}
{Number(sale.after_sales_adjustment) > 0 && (
  <TableRow><TableCell>售后调整</TableCell><TableCell>-¥{sale.after_sales_adjustment}</TableCell></TableRow>
)}
```

### 2.3 问题

- 现有 `aftersales` 数组仅包含简单的 `AftersalesRecord`（type/amount/reason/status/notes）
- 无法展示退货重量、单价、加工厂、附件等丰富信息
- 销售单列表页和详情页的售后数据与新退货模块脱节

---

## 三、关联方案设计

### 3.1 模型层新增关系

```python
# WholeFishSale 模型增加
return_orders: Mapped[List["ReturnOrder"]] = relationship(
    "ReturnOrder",
    foreign_keys="ReturnOrder.whole_fish_sale_id",
    lazy="selectin",
    cascade="all, delete-orphan",  # 销售单删除时级联删除退货单
)

# FinishedProductSale 模型增加
return_orders: Mapped[List["ReturnOrder"]] = relationship(
    "ReturnOrder",
    foreign_keys="ReturnOrder.finished_product_sale_id",
    lazy="selectin",
    cascade="all, delete-orphan",
)
```

### 3.2 退货单 → 销售单（双向关联）

```
ReturnOrder
  ├─ whole_fish_sale_id → WholeFishSale (整鱼销售)
  ├─ finished_product_sale_id → FinishedProductSale (成品销售)
  └─ customer_id → Company (客户)

WholeFishSale / FinishedProductSale
  └─ return_orders → ReturnOrder[] (反向查询)
```

**创建退货单时：**
1. 用户选择原销售单（通过销售单号/客户/日期搜索）
2. 自动填充 `sale_type` + `whole_fish_sale_id`/`finished_product_sale_id`
3. 自动带出客户、批次/产品、加工厂信息
4. 自动加载销售单明细，用户选择要退货的子项

---

## 四、销售单列表页售后数据兼容方案

### 4.1 核心原则：保持前端字段名不变

前端代码大量使用 `aftersales.length` 和 `after_sales_adjustment`，如果直接改名需要修改几十处。方案是**后端计算合并值，保持字段名不变**。

### 4.2 响应模型扩展

```python
# schemas/sales.py — WholeFishSaleResponse 新增字段
class WholeFishSaleResponse(WholeFishSaleBase):
    # ... 现有字段 ...
    aftersales: List[AftersalesRecordResponse] = []           # ← 保留旧数据
    return_orders: List[ReturnOrderSummary] = []               # ← 新增退货单摘要
    
    # 计算属性（兼容前端）
    @computed_field
    @property
    def aftersales_total_amount(self) -> Decimal:
        """售后总金额 = 旧aftersales + 新退货单（已完成状态的金额）"""
        old_total = sum(a.amount for a in self.aftersales)
        new_total = sum(r.total_amount for r in self.return_orders 
                       if r.status in [ReturnStatus.COMPLETED, ReturnStatus.APPROVED])
        return old_total + new_total
    
    @computed_field
    @property
    def aftersales_total_count(self) -> int:
        """售后记录总数 = 旧aftersales条数 + 新退货单数量"""
        return len(self.aftersales) + len(self.return_orders)
```

### 4.3 _build_sale_response 改造

```python
async def _build_sale_response(db: AsyncSession, sale: WholeFishSale) -> WholeFishSaleResponse:
    # ... 现有代码 ...
    
    # 加载退货单（新增）
    return_orders = [
        ReturnOrderSummary.model_validate(r) for r in (sale.return_orders or [])
    ]
    
    # 计算合并后的售后金额
    old_aftersales_amount = sum(a.amount for a in (sale.aftersales or []))
    new_return_amount = sum(
        r.total_amount for r in (sale.return_orders or [])
        if r.status in [ReturnStatus.COMPLETED, ReturnStatus.APPROVED, ReturnStatus.REFUNDING]
    )
    combined_aftersales_adjustment = old_aftersales_amount + new_return_amount
    
    # 计算合并后的售后数量
    combined_aftersales_count = len(sale.aftersales or []) + len(sale.return_orders or [])
    
    return WholeFishSaleResponse(
        # ... 现有字段 ...
        aftersales=aftersales,           # 旧售后记录
        return_orders=return_orders,     # 新退货单（前端详情页可用）
        after_sales_adjustment=combined_aftersales_adjustment,  # 合并金额
        _aftersales_count=combined_aftersales_count,             # 合并数量（前端徽章用）
    )
```

### 4.4 前端兼容：最小化改动

**列表页表格 — 只需微调：**

```tsx
// 售后数量徽章：改用合并后的数量
{sale._aftersales_count > 0 && (
  <span className="...">{sale._aftersales_count}</span>
)}

// 售后金额列：保持现有字段名（后端已合并计算）
{Number(sale.after_sales_adjustment) > 0 ? (
  <span className="text-red-500">-¥{sale.after_sales_adjustment}</span>
) : "-"}
```

**详情弹窗 — 售后标签页改造：**

```tsx
// 标签名改为"售后/退货"，计数包含两种
<Button>售后/退货 ({sale._aftersales_count})</Button>

// 标签页内容：同时展示旧售后和新退货单
{activeTab === "aftersales" && (
  <div>
    {/* 旧的 aftersales 记录（兼容历史数据） */}
    {sale.aftersales?.length > 0 && (
      <div className="mb-4">
        <h4 className="text-sm font-medium mb-2">历史售后记录</h4>
        <Table>...</Table>
      </div>
    )}
    
    {/* 新的退货单 */}
    {sale.return_orders?.length > 0 && (
      <div>
        <h4 className="text-sm font-medium mb-2">退货记录</h4>
        {sale.return_orders.map((ro) => (
          <div key={ro.id} className="border rounded-md p-3 mb-2">
            <div className="flex justify-between">
              <span className="font-medium">{ro.return_no}</span>
              <Badge>{ro.status}</Badge>
            </div>
            <div className="text-sm text-muted-foreground">
              退货日期: {ro.return_date} · 加工厂: {ro.processing_plant_name}
            </div>
            <div className="text-sm">
              重量: {ro.total_weight_kg}kg · 金额: ¥{ro.total_amount}
            </div>
            <div className="text-sm text-red-500">
              原因: {ro.problem_description}
            </div>
            {/* 附件缩略图 */}
            {ro.attachments?.length > 0 && (
              <div className="flex gap-2 mt-2">
                {ro.attachments.map((att) => (
                  <img key={att.id} src={att.thumbnail_url} className="w-16 h-16 rounded object-cover" />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    )}
    
    {/* 合计 */}
    {Number(sale.after_sales_adjustment) > 0 && (
      <div className="flex justify-between text-red-500 font-medium border-t pt-2 mt-2">
        <span>售后调整合计</span>
        <span>-¥{sale.after_sales_adjustment}</span>
      </div>
    )}
  </div>
)}
```

---

## 五、关键实现细节

### 5.1 售后金额实时同步

```python
# return_service.py
class ReturnService:
    @staticmethod
    async def sync_sale_after_sales(sale: WholeFishSale | FinishedProductSale):
        """退货单状态变更时，同步更新销售单的 after_sales_adjustment"""
        from decimal import Decimal
        
        # 计算该销售单所有已完成/已批准退货单的总金额
        total_return = Decimal("0")
        for ro in sale.return_orders:
            if ro.status in [ReturnStatus.COMPLETED, ReturnStatus.APPROVED, ReturnStatus.REFUNDING]:
                total_return += ro.total_amount or Decimal("0")
        
        # 加上旧的 aftersales 金额
        old_aftersales = Decimal("0")
        if hasattr(sale, 'aftersales'):
            old_aftersales = sum(a.amount for a in (sale.aftersales or []))
        elif hasattr(sale, 'aftersales_records'):
            old_aftersales = sum(a.amount for a in (sale.aftersales_records or []))
        
        sale.after_sales_adjustment = total_return + old_aftersales
        
        # 重新计算净金额
        sale.net_amount = max(
            Decimal("0"),
            sale.gross_amount
            - (sale.scan_fee or Decimal("0"))
            - (sale.rounding_adjustment or Decimal("0"))
            - sale.after_sales_adjustment
            - (sale.discount or Decimal("0"))
            - (sale.commission or Decimal("0"))
        )
        
        # 更新收款状态
        if sale.paid_amount >= sale.net_amount:
            sale.status = SalesStatus.FULLY_PAID
        elif sale.paid_amount > 0:
            sale.status = SalesStatus.PARTIAL_PAID
        else:
            sale.status = SalesStatus.PENDING
        
        # 如果有进行中的退货单，标记为售后中
        if any(r.status in [ReturnStatus.DRAFT, ReturnStatus.PENDING_APPROVAL] for r in sale.return_orders):
            sale.status = SalesStatus.AFTER_SALES
```

### 5.2 销售单列表查询优化

```python
# sales_service.py — list_sales
@staticmethod
async def list_sales(...) -> Tuple[List[WholeFishSale], int]:
    query = select(WholeFishSale).options(
        selectinload(WholeFishSale.items),
        selectinload(WholeFishSale.receipts),
        selectinload(WholeFishSale.aftersales),
        selectinload(WholeFishSale.return_orders).selectinload(ReturnOrder.items),  # 新增
    )
    # ... 现有代码 ...
```

### 5.3 退货金额校验

```python
# 创建退货单时校验：退货金额不能超过销售金额
async def validate_return_amount(sale: WholeFishSale, return_items: List[ReturnItemCreate]):
    total_return = sum(item.weight_kg * item.unit_price for item in return_items)
    existing_return = sum(r.total_amount for r in sale.return_orders 
                         if r.status != ReturnStatus.CANCELLED)
    
    if total_return + existing_return > sale.gross_amount:
        raise HTTPException(400, f"退货总额(¥{total_return + existing_return})超过销售金额(¥{sale.gross_amount})")
```

---

## 六、成品销售的兼容

成品销售（`FinishedProductSale`）采用完全相同的模式：

```python
# FinishedProductSale 响应模型
class FinishedProductSaleResponse:
    # ... 现有字段 ...
    aftersales_records: List[FinishedProductAftersalesResponse] = []  # 保留旧数据
    return_orders: List[ReturnOrderSummary] = []                       # 新增退货单
    after_sales_adjustment: Decimal  # 合并后的售后金额
    _aftersales_count: int           # 合并后的数量
```

成品销售页面（`FinishedProductSalesPage.tsx`）的改造与整鱼销售完全一致。

---

## 七、总结：关联与读取方案

| 问题 | 方案 |
|------|------|
| 退货单→销售单关联 | `ReturnOrder` 通过 `whole_fish_sale_id`/`finished_product_sale_id` 外键关联，模型层增加双向 relationship |
| 列表页售后列读取 | 后端 `_build_sale_response` 合并计算旧 aftersales + 新退货单金额，保持 `after_sales_adjustment` 字段名不变 |
| 列表页售后数量徽章 | 后端增加 `_aftersales_count` 计算字段 = 旧记录数 + 新退货单数 |
| 详情页售后标签 | 同时展示旧 aftersales 表格 + 新退货单卡片（含附件缩略图） |
| 金额同步 | 退货单创建/审批/完成时自动调用 `sync_sale_after_sales` 更新销售单 |
| 向后兼容 | 保留旧 `AftersalesRecord`/`FinishedProductAftersales` 表和数据，新模块独立运行 |

---

*补充日期: 2026-05-15*
