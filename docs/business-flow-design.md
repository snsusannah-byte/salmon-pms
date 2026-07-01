# 进口 → 批次 → 库存 → 销售 业务方案设计（V2 - 已确认）

## 一、业务规则确认

| 问题 | 确认结果 |
|------|----------|
| 入库单位 | **箱数、重量都记录** |
| 销售扣减 | **按箱数扣，不能为负；重量可以为负** |
| 默认仓库 | **整包仓（warehouse_type = whole_package）** |
| 产品匹配 | 发票 `product_spec`（如"6-7kg"）匹配产品档案 `Product.spec`，`category` 为 `whole_fish` 或 `fillet` |
| 负库存 | **箱数不允许负，重量允许负** |

---

## 二、数据模型调整

### 2.1 Stock 表扩展（新增箱数字段）

```python
class Stock(Base, TimestampMixin):
    """库存记录（按仓库+产品+批次）- 支持箱数和重量双维度"""
    # ... 现有字段不变 ...
    
    # 新增：箱数维度（与重量维度独立）
    box_count: Mapped[int | None] = mapped_column(Integer, default=0)           # 当前箱数
    reserved_box_count: Mapped[int | None] = mapped_column(Integer, default=0)  # 预留箱数
    available_box_count: Mapped[int | None] = mapped_column(Integer, default=0) # 可用箱数
```

**说明**：
- `current_qty` / `available_qty` 继续表示**重量(kg)**
- `box_count` / `available_box_count` 表示**箱数**
- 入库时同时更新两个维度
- 出库时按业务规则分别扣减

### 2.2 StockInbound 表扩展

```python
class StockInbound(Base, TimestampMixin):
    # ... 现有字段不变 ...
    
    # 新增：箱数维度
    box_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 入库箱数
    original_box_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 原始箱数（用于批次追溯）
```

### 2.3 StockOutbound 表扩展

```python
class StockOutbound(Base, TimestampMixin):
    # ... 现有字段不变 ...
    
    # 新增：箱数维度
    box_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 出库箱数
```

### 2.4 InvoiceProduct 表新增产品关联

```python
class InvoiceProduct(Base, TimestampMixin):
    # ... 现有字段不变 ...
    
    # 新增：关联产品档案
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    product: Mapped[Optional["Product"]] = relationship("Product", lazy="raise")
```

**产品匹配逻辑**：
```python
def match_product_by_spec(spec: str) -> Product | None:
    """按规格匹配产品档案"""
    # 1. 精确匹配 spec 字段
    # 2. category 为 whole_fish 或 fillet
    # 3. 取第一个匹配结果
```

---

## 三、业务流程详细设计

### 3.1 整体流程

```
进口单证登记 → 清关完成 → 创建批次 → 【自动入库整包仓】→ 销售 → 【自动扣减库存】
```

### 3.2 步骤一：批次创建 → 自动入库（核心新增）

**触发时机**：`BatchService.create()` 成功提交后

**入库流程**：

```
1. 获取批次关联的所有发票
   ↓
2. 遍历每个发票的产品明细（InvoiceProduct）
   ↓
3. 对每个产品明细：
   a. 按 product_spec 匹配 Product 档案（category = whole_fish/fillet）
   b. 获取或创建 Stock 记录（warehouse_id=整包仓, product_id, batch_id）
   c. 创建 StockInbound 记录
   d. 更新 Stock（重量 + 箱数）
   e. 创建 StockMovement 流水
   ↓
4. 更新批次状态为 "in_stock"
```

**入库数据映射**：

| 源数据 | 目标字段 | 值 |
|--------|----------|-----|
| InvoiceProduct.invoice_date | StockInbound.inbound_date | 发票日期 |
| 匹配到的 Product.id | StockInbound.product_id | 产品ID |
| Batch.id | StockInbound.batch_id | 批次ID |
| 整包仓ID | StockInbound.warehouse_id | 默认仓库 |
| InvoiceProduct.box_count | StockInbound.box_count | 箱数 |
| InvoiceProduct.net_weight_kg | StockInbound.qty | 重量(kg) |
| InvoiceProduct.unit_price | StockInbound.unit_cost | 单价 |
| InvoiceProduct.total_amount | StockInbound.total_cost | 金额 |
| "batch_inbound" | StockInbound.source_type | 来源类型 |

**Stock 更新逻辑**：
```python
# 重量维度（加权平均成本）
old_total_cost = stock.current_qty * stock.unit_cost
new_total_cost = inbound.qty * inbound.unit_cost
stock.current_qty += inbound.qty
stock.unit_cost = (old_total_cost + new_total_cost) / stock.current_qty

# 箱数维度（直接累加）
stock.box_count += inbound.box_count
stock.available_box_count = stock.box_count - stock.reserved_box_count
```

### 3.3 步骤二：销售 → 自动出库（核心新增）

**触发时机**：`SalesService.create_sale()` / `update_sale()` 成功提交后

**出库流程**：

```
1. 获取销售单关联的 batch_id
   ↓
2. 遍历销售单的产品明细（WholeFishSaleItem）
   ↓
3. 对每个销售项：
   a. 按 spec 匹配 Product 档案
   b. 获取 Stock 记录（warehouse_id=整包仓, product_id, batch_id）
   c. 【校验】箱数：available_box_count >= 销售箱数？
      - 否 → 抛出异常 "库存不足：剩余X箱，销售Y箱"
   d. 【校验】重量：available_qty >= 销售重量？
      - 否 → 允许继续（重量可以为负）
   e. 创建 StockOutbound 记录
   f. 更新 Stock（扣减箱数和重量）
   g. 创建 StockMovement 流水
   ↓
4. 更新批次库存状态
```

**出库校验规则**：
| 维度 | 校验规则 | 失败处理 |
|------|----------|----------|
| 箱数 | `available_box_count >= 销售箱数` | **抛异常，阻止销售** |
| 重量 | `available_qty >= 销售重量` | **允许继续，重量可以为负** |

**Stock 扣减逻辑**：
```python
# 箱数维度（必须 >= 0）
stock.box_count -= sale_item.box_count
stock.available_box_count = stock.box_count - stock.reserved_box_count
assert stock.available_box_count >= 0, "箱数不能为负"

# 重量维度（允许为负）
stock.current_qty -= sale_item.weight_kg
stock.available_qty = stock.current_qty - stock.reserved_qty
```

### 3.4 步骤三：库存状态更新

**批次库存状态机**：
```
in_stock（在库）→ partial_sold（部分售出）→ sold_out（售罄）
```

**状态判断**：
```python
if 总箱数 == 已售箱数:
    status = "sold_out"
elif 已售箱数 > 0:
    status = "partial_sold"
else:
    status = "in_stock"
```

---

## 四、API 接口设计

### 4.1 批次自动入库接口（内部调用）

```python
# WarehouseV2Service.batch_inbound(db, batch_id, warehouse_id)
# 自动完成批次入库，无需前端调用
```

### 4.2 销售自动出库接口（内部调用）

```python
# WarehouseV2Service.sale_outbound(db, sale_id)
# 自动完成销售出库，无需前端调用
```

### 4.3 批次库存余量查询（新增API）

```
GET /api/v1/batches/{batch_id}/inventory
```

**响应**：
```json
{
  "batch_id": 1,
  "batch_code": "20260614-001",
  "warehouse_name": "整包仓",
  "products": [
    {
      "product_id": 1,
      "product_code": "WF-001",
      "product_name": "挪威冰鲜三文鱼",
      "spec": "6-7kg",
      // 箱数维度
      "total_boxes": 1000,
      "sold_boxes": 350,
      "remaining_boxes": 650,
      // 重量维度
      "total_weight_kg": 38500.0,
      "sold_weight_kg": 13475.0,
      "remaining_weight_kg": 25025.0
    }
  ],
  "summary": {
    "total_products": 3,
    "total_boxes": 1000,
    "remaining_boxes": 650,
    "total_weight_kg": 38500.0,
    "remaining_weight_kg": 25025.0,
    "stock_status": "partial_sold"
  }
}
```

### 4.4 仓库库存查询（扩展已有API）

```
GET /api/v1/warehouse/stocks?batch_id={batch_id}&warehouse_type=whole_package
```

**扩展字段**：
```json
{
  "id": 1,
  "warehouse_name": "整包仓",
  "product_name": "挪威冰鲜三文鱼",
  "spec": "6-7kg",
  "batch_code": "20260614-001",
  // 箱数维度（新增）
  "box_count": 650,
  "available_box_count": 650,
  // 重量维度（已有）
  "current_qty": 25025.0,
  "available_qty": 25025.0,
  "unit": "kg",
  "unit_cost": 45.50
}
```

---

## 五、前端交互设计

### 5.1 批次管理页面

**批次列表增加库存状态列**：
| 批次编号 | 发票号 | 总箱数 | 库存状态 | 操作 |
|----------|--------|--------|----------|------|
| 20260614-001 | 8812&8813 | 1000 | 🟢 在库 | 入库/查看 |
| 20260613-002 | 8805 | 500 | 🟡 部分售出 350箱 | 查看 |
| 20260610-003 | 8790 | 800 | 🔴 售罄 | 查看 |

**批次详情增加库存卡片**：
```
┌─────────────────────────────────────────┐
│ 库存余量                                │
├─────────────────────────────────────────┤
│ 规格: 6-7kg                             │
│ 总箱数: 1000    已售: 350    剩余: 650  │
│ 总重量: 38,500kg  已售: 13,475kg  剩余: 25,025kg │
│ 状态: 🟡 部分售出                       │
└─────────────────────────────────────────┘
```

### 5.2 销售页面

**选择批次时显示库存**：
```
批次: [B20260614-001 ▼]
      └─ 6-7kg: 剩余 650 箱 / 25,025 kg
      └─ 7-8kg: 剩余 420 箱 / 17,640 kg
```

**库存不足提示**：
```
⚠️ 库存不足
   6-7kg 剩余 650 箱，您输入了 700 箱
   请减少销售数量或选择其他批次
```

**重量可以为负的提示**：
```
⚠️ 重量出库将超过库存
   当前重量库存 25,025 kg，销售 26,000 kg
   确认继续？出库后重量库存将为 -975 kg
   [取消] [确认继续]
```

### 5.3 库存查询页面（新增"批次库存"Tab）

| 批次编号 | 产品规格 | 入库箱数 | 已售箱数 | 剩余箱数 | 入库重量 | 已售重量 | 剩余重量 | 状态 |
|----------|----------|----------|----------|----------|----------|----------|----------|------|
| 20260614-001 | 6-7kg | 1000 | 350 | 650 | 38,500 | 13,475 | 25,025 | 部分售出 |
| 20260614-001 | 7-8kg | 800 | 0 | 800 | 30,400 | 0 | 30,400 | 在库 |

---

## 六、实现优先级

| 优先级 | 功能 | 文件 | 说明 |
|--------|------|------|------|
| P0 | 数据库迁移 | Alembic migration | 新增 box_count 等字段 |
| P0 | 批次自动入库 | `warehouse_v2_service.py` + `batch_service.py` | 创建批次后自动入库 |
| P0 | 销售自动出库 | `warehouse_v2_service.py` + `sales_service.py` | 销售时自动扣减库存 |
| P0 | 库存不足校验 | `sales_service.py` | 箱数不能为负 |
| P1 | 批次库存查询API | `batches.py` | 批次级库存余量 |
| P1 | 仓库库存查询扩展 | `warehouse_v2_service.py` | 返回箱数字段 |
| P1 | 批次列表库存状态 | `BatchesPage.tsx` | 显示库存状态列 |
| P1 | 批次详情库存卡片 | `BatchesPage.tsx` | 显示库存余量 |
| P1 | 销售页面库存显示 | `SalesPage.tsx` | 选择批次时显示库存 |
| P2 | 库存查询页面 | 新增页面 | 批次库存Tab |

---

## 七、关键代码逻辑

### 7.1 产品规格匹配

```python
async def match_invoice_product_to_product(
    db: AsyncSession, 
    product_spec: str
) -> Product | None:
    """按规格匹配产品档案"""
    from sqlalchemy import select
    from app.models import Product, ProductCategory
    
    result = await db.execute(
        select(Product)
        .where(
            Product.spec == product_spec,
            Product.category.in_([ProductCategory.WHOLE_FISH, ProductCategory.FILLET]),
            Product.is_active == True
        )
        .limit(1)
    )
    return result.scalar_one_or_none()
```

### 7.2 入库核心逻辑

```python
async def batch_inbound(
    db: AsyncSession,
    batch_id: int,
    warehouse_id: int | None = None
) -> list[StockInbound]:
    """批次入库 - 创建批次后自动调用"""
    
    # 1. 获取默认仓库（整包仓）
    if not warehouse_id:
        wh = await get_default_whole_package_warehouse(db)
        warehouse_id = wh.id
    
    # 2. 获取批次关联的发票
    batch = await BatchService.get_by_id(db, batch_id)
    
    inbounds = []
    for bi in batch.batch_invoices:
        invoice = bi.invoice
        for ip in invoice.products:
            # 3. 匹配产品
            product = await match_invoice_product_to_product(db, ip.product_spec)
            if not product:
                continue  # 或者记录日志
            
            # 4. 创建入库记录
            inbound = await create_inbound(db, {
                "source_type": "batch_inbound",
                "source_id": batch_id,
                "warehouse_id": warehouse_id,
                "product_id": product.id,
                "batch_id": batch_id,
                "qty": ip.net_weight_kg,
                "unit": "kg",
                "box_count": ip.box_count,
                "unit_cost": ip.unit_price,
                "total_cost": ip.total_amount,
                "inbound_date": invoice.invoice_date,
            })
            
            # 5. 确认入库（更新库存）
            await confirm_inbound(db, inbound)
            inbounds.append(inbound)
    
    return inbounds
```

### 7.3 出库核心逻辑

```python
async def sale_outbound(
    db: AsyncSession,
    sale_id: int
) -> list[StockOutbound]:
    """销售出库 - 创建销售单后自动调用"""
    
    sale = await SalesService.get_sale_by_id(db, sale_id)
    wh = await get_default_whole_package_warehouse(db)
    
    outbounds = []
    for item in sale.items:
        # 1. 匹配产品
        product = await match_invoice_product_to_product(db, item.spec)
        if not product:
            continue
        
        # 2. 获取库存
        stock = await get_or_create_stock(db, wh.id, product.id, sale.batch_id)
        
        # 3. 校验箱数（不能为负）
        if stock.available_box_count < item.box_count:
            raise ValueError(
                f"库存不足：规格 {item.spec} 剩余 {stock.available_box_count} 箱，"
                f"销售 {item.box_count} 箱"
            )
        
        # 4. 创建出库记录
        outbound = await create_outbound(db, {
            "dest_type": "sale",
            "dest_id": sale_id,
            "warehouse_id": wh.id,
            "product_id": product.id,
            "batch_id": sale.batch_id,
            "qty": item.weight_kg,
            "unit": "kg",
            "box_count": item.box_count,
            "outbound_date": sale.sale_date,
        })
        
        # 5. 确认出库（更新库存）
        await confirm_outbound(db, outbound)
        outbounds.append(outbound)
    
    return outbounds
```

---

## 八、异常处理

| 场景 | 处理 |
|------|------|
| 发票产品规格匹配不到产品档案 | 记录日志，跳过该产品，继续入库其他产品 |
| 箱数库存不足 | 抛异常，阻止销售单创建 |
| 重量库存不足 | 提示用户，允许继续（重量可以为负） |
| 批次已售罄后再次销售 | 抛异常，"该批次已售罄" |

---

## 九、数据一致性保障

1. **事务控制**：入库和出库操作在数据库事务中完成
2. **乐观锁**：Stock 表增加 `version` 字段防止并发冲突
3. **对账机制**：每日定时任务校验批次总箱数 = 入库箱数 - 出库箱数
