# 物料管理与采购入库系统 — 最终定稿

> 日期: 2026-05-28
> 状态: 定稿 — 独立模块（不放入现有采购入库，新建表+复用组件）

---

## 一、设计决策

**核心决定：** 物料采购不放入现有 `purchase_orders_v2`，新建独立模块。

**原因：**
- 现有 `purchase_orders_v2` 是整鱼/辅料采购（按重量 kg），模型不匹配物料批次管理（按箱×每箱数量）
- 现有采购单状态只有 `completed`，物料需要 `pending→partial→completed` 完整流程
- 物料需要批次成本追溯（FIFO），与现有入库流程差异大
- 强行合并会导致前端/后端代码膨胀、维护困难

**方案：** 独立表结构 + 独立前端页面 + 复用供应商/仓库选择等通用组件

---

## 二、数据库设计

### 2.1 物料分类表（已有，不动）

```sql
-- material_categories — 现有增删改查完全够用
-- 用户分类：海鲜、包装物、办公物料
```

### 2.2 物料表（改造 products）

```sql
-- 确认 products 表已有以下字段：
-- id, code, name, spec, unit, category, material_category_id, cost_price, is_active

-- 如需新增（检查是否存在）：
ALTER TABLE products ADD COLUMN IF NOT EXISTS items_per_box INTEGER;
-- items_per_box: 每箱数量，如腰封 1箱=1300张
```

**示例：**

| id | code | name | spec | unit | material_category_id | items_per_box |
|----|------|------|------|------|----------------------|---------------|
| 1 | WF-TY | 腰封-通用 | 透明/无印刷 | 张 | 1(包装物) | 1300 |
| 2 | WF-PPA | 腰封-品牌A | 蓝色/品牌A印刷 | 张 | 1(包装物) | 1300 |
| 3 | WF-PPB | 腰封-品牌B | 红色/品牌B印刷 | 张 | 1(包装物) | 1200 |
| 4 | BD-200 | 冰袋-200g | 200g规格 | 个 | 1(包装物) | 500 |

> 一条记录就是一个具体物料，`name` 区分规格，`items_per_box` 存在物料上。

### 2.3 物料采购单表（新建）

```sql
CREATE TABLE material_purchase_orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) NOT NULL UNIQUE,       -- 单号 CG-20260528-001
    order_date DATE NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES companies(id),  -- 供应商（采购时选）
    
    -- 金额（由系统计算，用户确认）
    quoted_total NUMERIC(15, 2),                -- 报价总金额 = SUM(items.quoted_amount)
    actual_total NUMERIC(15, 2) NOT NULL,       -- 实际应付总金额
    paid_amount NUMERIC(15, 2) DEFAULT 0,       -- 已付金额
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',         -- pending/completed/cancelled
    payment_status VARCHAR(20) DEFAULT 'unpaid',  -- unpaid/partial_paid/paid
    
    warehouse_id INTEGER REFERENCES warehouses(id),  -- 入库仓库
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_mpo_supplier ON material_purchase_orders(supplier_id);
CREATE INDEX idx_mpo_status ON material_purchase_orders(status);
CREATE INDEX idx_mpo_date ON material_purchase_orders(order_date);
```

### 2.4 物料采购明细表（新建）

```sql
CREATE TABLE material_purchase_items (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL REFERENCES material_purchase_orders(id) ON DELETE CASCADE,
    
    -- 物料
    product_id INTEGER NOT NULL REFERENCES products(id),
    
    -- 数量
    box_count INTEGER NOT NULL,                     -- 箱数
    items_per_box INTEGER NOT NULL,                 -- 每箱数量（从物料复制，可修改）
    total_qty NUMERIC(12, 3) NOT NULL,              -- 总数量 = 箱数 × 每箱数量（最小单位）
    unit VARCHAR(20) NOT NULL,                      -- 最小单位
    
    -- 价格（双轨）
    quoted_unit_price NUMERIC(12, 4),               -- 报价单价（按最小单位）
    quoted_amount NUMERIC(15, 2),                   -- 报价金额 = total_qty × quoted_unit_price
    actual_amount NUMERIC(15, 2) NOT NULL,          -- 该项实付金额
    actual_unit_price NUMERIC(12, 4) NOT NULL,      -- 核算单价 = actual_amount / total_qty
    
    -- 入库状态
    received_qty NUMERIC(12, 3) DEFAULT 0,          -- 已入库数量
    is_fully_received BOOLEAN DEFAULT FALSE,
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_mpi_order ON material_purchase_items(purchase_order_id);
CREATE INDEX idx_mpi_product ON material_purchase_items(product_id);
```

### 2.5 物料批次表（新建）

```sql
CREATE TABLE material_batches (
    id SERIAL PRIMARY KEY,
    batch_no VARCHAR(100) NOT NULL,                -- 批次号
    
    -- 物料
    product_id INTEGER NOT NULL REFERENCES products(id),
    
    -- 来源（快照，不关联）
    supplier_name VARCHAR(200),                     -- 供应商名称（只记录）
    purchase_order_item_id INTEGER REFERENCES material_purchase_items(id),
    
    -- 数量
    inbound_qty NUMERIC(12, 3) NOT NULL,            -- 入库数量
    remaining_qty NUMERIC(12, 3) NOT NULL,          -- 剩余数量
    unit VARCHAR(20),                               -- 最小单位
    
    -- 成本
    unit_cost NUMERIC(12, 4) NOT NULL,              -- 实际成本单价
    total_cost NUMERIC(15, 2) NOT NULL,             -- 总成本
    
    -- 时间
    inbound_date DATE NOT NULL,
    expiry_date DATE,
    
    -- 仓库
    warehouse_id INTEGER REFERENCES warehouses(id),
    location VARCHAR(100),
    
    -- 状态
    status VARCHAR(20) DEFAULT 'active',            -- active/frozen/empty
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_mb_product_active ON material_batches(product_id) 
WHERE status = 'active' AND remaining_qty > 0;
CREATE INDEX idx_mb_inbound_date ON material_batches(inbound_date);

-- 批次号生成: BM-{物料编码}-{日期}-{随机后缀}
-- 示例: BM-WF-PPA-20260528-a3f7
```

---

## 三、关键设计修正

### 3.1 表名冲突解决

| 现有表 | 新建表 | 说明 |
|--------|--------|------|
| `purchase_orders` | ❌ 不动 | 旧表（空表），不动 |
| `purchase_orders_v2` | ❌ 不动 | 整鱼/辅料采购，不动 |
| — | ✅ `material_purchase_orders` | 物料采购单（新建） |
| — | ✅ `material_purchase_items` | 物料采购明细（新建） |
| — | ✅ `material_batches` | 物料批次（新建） |

### 3.2 金额一致性

```python
# 创建采购单时，后端强制校验：
# actual_total == SUM(items.actual_amount)
# quoted_total == SUM(items.quoted_amount)
# 不一致时报错
```

### 3.3 入库状态流

```
pending（待入库）
  → 部分入库 → 仍是 pending（received_qty < total_qty）
  → 全部入库 → completed（received_qty == total_qty）
  → 取消 → cancelled
```

> 不设置 partial 状态，简化状态机。通过 received_qty / total_qty 判断入库进度。

### 3.4 批次号避免并发冲突

```python
import uuid
from datetime import date

batch_no = f"BM-{product_code}-{date.today().strftime('%Y%m%d')}-{uuid4().hex[:4]}"
# 示例: BM-WF-PPA-20260528-a3f7
```

### 3.5 入库/出库调用现有仓库服务

```python
# 入库时：
# 1. 生成 material_batches 记录（批次成本）
# 2. 调用 WarehouseV2Service.create_inbound() 更新仓库总库存
# 3. 记录 warehouse_movements 流水

# 出库时：
# 1. 按 FIFO 扣减 material_batches.remaining_qty
# 2. 调用 WarehouseV2Service.create_outbound() 更新仓库总库存
# 3. 记录 warehouse_movements 流水
```

---

## 四、采购入库流程

### 4.1 创建采购单

```
用户输入：
  供应商：李四印刷
  日期：2026-05-28
  
  物料：腰封-品牌A
  箱数：10
  每箱数量：1300张（从物料带出，可改）
  报价单价：¥0.25/张
  实付金额：¥3000

系统处理：
  ① total_qty = 10 × 1300 = 13000 张
  ② quoted_amount = 13000 × 0.25 = ¥3250
     actual_unit_price = 3000 / 13000 = ¥0.2308/张
  ③ 写入 material_purchase_orders:
     supplier_id = 李四印刷ID
     actual_total = SUM(items.actual_amount) = 3000（自动计算）
     status = 'pending'
  ④ 写入 material_purchase_items:
     product_id = 腰封-品牌A ID
     box_count = 10, items_per_box = 1300, total_qty = 13000
     actual_amount = 3000, actual_unit_price = 0.2308
```

### 4.2 执行入库

```
用户操作：确认入库

系统处理：
  ① 生成批次：
     batch_no = BM-WF-PPA-20260528-a3f7
     supplier_name = "李四印刷"
     inbound_qty = 13000, remaining_qty = 13000
     unit_cost = 0.2308, total_cost = 3000
  
  ② 更新物料总库存：
     调用 WarehouseV2Service.create_inbound()
     warehouse_stocks.current_quantity += 13000
  
  ③ 记录流水：
     warehouse_movements: type='inbound', qty=13000
  
  ④ 更新采购单：
     received_qty = 13000, is_fully_received = true
     检查全部明细 received_qty == total_qty → status = 'completed'
```

---

## 五、出库流程

### 5.1 FIFO 先进先出

```python
async def fifo_outbound(product_id, qty_needed):
    batches = await db.query(MaterialBatch).filter(
        MaterialBatch.product_id == product_id,
        MaterialBatch.remaining_qty > 0,
        MaterialBatch.status == 'active'
    ).order_by(
        MaterialBatch.inbound_date.asc()
    ).all()
    
    allocations = []
    remaining = qty_needed
    for batch in batches:
        if remaining <= 0: break
        take = min(batch.remaining_qty, remaining)
        allocations.append({
            'batch_id': batch.id,
            'batch_no': batch.batch_no,
            'qty': take,
            'unit_cost': batch.unit_cost,
            'supplier_name': batch.supplier_name,
        })
        batch.remaining_qty -= take
        remaining -= take
    
    if remaining > 0:
        raise InsufficientStock(f"库存不足，缺 {remaining}")
    
    return allocations
```

### 5.2 指定批次出库

```python
async def specific_batch_outbound(batch_id, qty):
    batch = await db.get(MaterialBatch, batch_id)
    if batch.remaining_qty < qty:
        raise InsufficientStock(f"批次 {batch.batch_no} 只有 {batch.remaining_qty}")
    batch.remaining_qty -= qty
    return {
        'batch_id': batch_id,
        'qty': qty,
        'unit_cost': batch.unit_cost,
        'supplier_name': batch.supplier_name,
    }
```

---

## 六、前端交互设计

### 6.1 物料列表页

```
┌────────────────────────────────────────────────────────────────┐
│ [全部▼] [包装物▼] [海鲜▼] [办公物料▼] 🔍搜索...    [新增物料]   │
├────────────────────────────────────────────────────────────────┤
│ 编码      物料名称      规格            单位  每箱    库存      │
│ WF-TY     腰封-通用     透明/无印刷      张   1300    15,000    │
│ WF-PPA    腰封-品牌A    蓝色/品牌A印刷   张   1300    8,000     │
│ WF-PPB    腰封-品牌B    红色/品牌B印刷   张   1200    12,000    │
│ BD-200    冰袋-200g     200g规格        个   500     2,000     │
├────────────────────────────────────────────────────────────────┤
│ 点击行展开详情面板（批次明细 + 采购记录）                   │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 采购入库弹窗（独立页面）

```
┌──────────────────────────────────────────────────────────┐
│ 物料采购入库                                              │
├──────────────────────────────────────────────────────────┤
│ 日期：[2026-05-28      ]                                  │
│ 供应商：[选择供应商 ▼]     ← 复用现有供应商选择组件        │
│ 入库仓库：[辅料仓库 ▼]     ← 复用现有仓库选择组件          │
├──────────────────────────────────────────────────────────┤
│ 物料：[腰封-品牌A ▼]                                      │
│                                                          │
│ 箱数：[10  ] 箱                                           │
│ 每箱数量：[1300 ] 张（从物料带出，可修改）                │
│ ─────────────────────────────────────                    │
│ 总数量：13,000 张（自动计算）                            │
├──────────────────────────────────────────────────────────┤
│ 报价单价：¥[0.25   ]/张    报价金额：¥3,250.00（自动）   │
│ 实付金额：¥[3,000.00]                                   │
│ ─────────────────────────────────────                    │
│ 核算单价：¥0.2308/张（自动：实付÷总数量）                │
├──────────────────────────────────────────────────────────┤
│ 批次号：[BM-WF-PPA-20260528-a3f7]（自动生成）            │
│ 有效期：[          ]                                      │
├──────────────────────────────────────────────────────────┤
│ [取消]                                    [确认入库]      │
└──────────────────────────────────────────────────────────┘
```

### 6.3 物料详情面板

```
┌──────────────────────────────────────────────────────────────────┐
│ [WF-PPA] 腰封-品牌A    规格：蓝色/品牌A印刷    [编辑][×]         │
├──────────────────────────────────────────────────────────────────┤
│ 库存：8,000 张  |  平均成本：¥0.2308  |  批次：1                  │
│                                                                   │
│ 批次明细：                                                         │
│ ┌─────────────┬──────────┬─────────┬──────────┬─────────┐       │
│ │ 批次号      │ 入库日期 │ 供应商  │ 剩余数量 │ 成本单价│       │
│ ├─────────────┼──────────┼─────────┼──────────┼─────────┤       │
│ │ BM-...-a3f7 │ 05-28    │ 李四印刷│ 8,000    │ ¥0.2308 │       │
│ └─────────────┴──────────┴─────────┴──────────┴─────────┘       │
│                                                                   │
│ [采购记录] [出库] [冻结批次]                                      │
└──────────────────────────────────────────────────────────────────┘
```

### 6.4 出库弹窗

```
┌──────────────────────────────────────────────────────────┐
│ 物料出库 — 腰封-品牌A                                     │
├──────────────────────────────────────────────────────────┤
│ 当前库存：8,000 张                                        │
├──────────────────────────────────────────────────────────┤
│ 出库数量：[      ] 张                                      │
├──────────────────────────────────────────────────────────┤
│ 出库策略：                                               │
│ ○ 先进先出（默认）                                       │
│ ○ 指定批次 — [选择批次 ▼]                                │
├──────────────────────────────────────────────────────────┤
│ 用途/备注：[              ]                                │
├──────────────────────────────────────────────────────────┤
│ [取消]                                    [确认出库]      │
└──────────────────────────────────────────────────────────┘
```

---

## 七、API 接口

### 7.1 物料管理

```
GET    /v4/materials?category_id=&keyword=
       → 返回物料列表（含库存汇总）

POST   /v4/materials
       → 创建物料
       Body: { code, name, spec, unit, material_category_id, items_per_box }

PUT    /v4/materials/{id}
       → 更新物料

DELETE /v4/materials/{id}
       → 删除物料（检查无活跃批次）

GET    /v4/materials/{id}
       → 物料详情（含批次明细）
```

### 7.2 物料采购管理

```
POST   /v4/material-purchase-orders
       → 创建物料采购单
       Body: { order_date, supplier_id, warehouse_id, items: [
         { product_id, box_count, items_per_box, quoted_unit_price, actual_amount }
       ]}
       → 后端自动计算：total_qty, quoted_amount, actual_unit_price, actual_total

GET    /v4/material-purchase-orders?supplier_id=&status=&date_from=&date_to=
       → 采购单列表

GET    /v4/material-purchase-orders/{id}
       → 采购单详情

POST   /v4/material-purchase-orders/{id}/inbound
       → 执行入库（生成批次 + 更新仓库库存）
       → 自动更新 received_qty，检查是否全部入库

PUT    /v4/material-purchase-orders/{id}/cancel
       → 取消采购单（仅 pending 状态可取消）
```

### 7.3 库存管理

```
GET    /v4/warehouse/material-stocks?product_id=&include_batches=true
       → 物料库存（总库存 + 批次明细）

POST   /v4/warehouse/material-outbound
       → 出库
       Body: { product_id, qty, strategy: 'fifo'|'specific', batch_id?, reason? }

GET    /v4/warehouse/material-stock-movements?product_id=&type=
       → 库存流水
```

---

## 八、实施计划

### Phase 1: 数据库迁移（半天）

1. [ ] 检查 `products` 表，如没有 `items_per_box` 则添加
2. [ ] 创建 `material_purchase_orders` 表
3. [ ] 创建 `material_purchase_items` 表
4. [ ] 创建 `material_batches` 表 + 索引
5. [ ] Alembic 迁移脚本
6. [ ] 验证：与现有 `purchase_orders_v2` 无冲突

### Phase 2: 后端 API（1.5天）

1. [ ] 物料列表/详情 API（含库存汇总）
2. [ ] 物料采购单 CRUD（自动计算金额、校验一致性）
3. [ ] 入库接口（生成批次 + 调用 WarehouseV2Service 更新库存）
4. [ ] 出库接口（FIFO + 指定批次 + 调用 WarehouseV2Service）
5. [ ] 库存查询接口

### Phase 3: 前端改造（1.5天）

1. [ ] 物料列表页（显示库存 + 展开详情）
2. [ ] 物料采购入库页面（箱数×每箱数量=总量 + 实付÷总量=核算单价）
3. [ ] 出库弹窗（FIFO/指定批次）
4. [ ] 物料采购单列表页面

### Phase 4: 测试验证（半天）

1. [ ] 采购入库流程测试
2. [ ] 批次出库测试
3. [ ] 库存核对：批次剩余之和 = 总库存
4. [ ] 确认与现有采购模块无冲突

**总计：4天**

---

*定稿 — 物料采购为独立模块，新建表、独立页面、复用通用组件。*
