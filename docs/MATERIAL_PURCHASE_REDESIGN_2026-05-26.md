# 物料管理与采购入库系统改造方案

> 日期: 2026-05-26
> 状态: 待实施

---

## 一、核心问题诊断

### 1.1 现有痛点

| # | 问题 | 影响 |
|---|------|------|
| 1 | **物料-供应商紧耦合** | 通用腰封和品牌腰封各自独立维护供应商，同一供应商重复录入 |
| 2 | **无物料层级** | 无法表达"腰封→通用腰封/品牌A腰封/品牌B腰封"的继承关系 |
| 3 | **采购入库简陋** | 不支持按箱入库、不自动核算单价、无批次管理 |
| 4 | **库存关联弱** | 入库后只更新总库存，没有按批次/按供应商的明细 |
| 5 | **供应商信息缺失** | 表格看不到物料绑定了哪些供应商，必须点开详情 |

### 1.2 设计目标

- **一物多规格**：腰封一个基础物料，多个规格变体共享供应商
- **供应商独立**：供应商库统一管理，通过"供应关系"关联物料
- **采购单据化**：采购单→入库单→库存流水，完整链路
- **智能核算**：箱数×每箱数量=总量，实付金额÷总量=单价
- **批次追溯**：每批入库独立批次号，支持按批次查库存

---

## 二、数据库模型改造

### 2.1 新增表

#### `material_variants` 物料规格变体表

```sql
CREATE TABLE material_variants (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER NOT NULL REFERENCES products(id),  -- 指向基础物料
    variant_name VARCHAR(100) NOT NULL,                   -- 规格名称（如"品牌A腰封"）
    variant_code VARCHAR(50),                             -- 规格编码
    spec VARCHAR(200),                                    -- 规格参数（颜色/尺寸/品牌）
    brand_id INTEGER REFERENCES brands(id),               -- 关联品牌
    cost_price NUMERIC(15, 4),                            -- 成本单价（可覆盖基础物料）
    items_per_box INTEGER,                                -- 每箱数量
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**示例数据：**

| id | parent_id | variant_name | spec | brand_id | cost_price | items_per_box |
|----|-----------|-------------|------|----------|------------|---------------|
| 1 | 100 | 通用腰封 | 透明/无印刷 | NULL | 0.15 | 1300 |
| 2 | 100 | 品牌A腰封 | 蓝色/品牌A印刷 | 1 | 0.25 | 1300 |
| 3 | 100 | 品牌B腰封 | 红色/品牌B印刷 | 2 | 0.20 | 1300 |

> 腰封（基础物料 id=100）→ 三个变体共享同一个 parent_id

#### `purchase_orders` 采购单表

```sql
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) NOT NULL UNIQUE,     -- 采购单号（CG-20260526-001）
    order_date DATE NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES companies(id),
    
    -- 金额汇总
    total_amount NUMERIC(15, 2) NOT NULL,     -- 应付总金额
    actual_amount NUMERIC(15, 2),             -- 实付金额（可能含运费/折扣差异）
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',     -- pending/confirmed/completed/cancelled
    
    -- 付款
    paid_amount NUMERIC(15, 2) DEFAULT 0,     -- 已付金额
    payment_status VARCHAR(20) DEFAULT 'unpaid', -- unpaid/partial_paid/paid
    
    warehouse_type VARCHAR(20) DEFAULT 'accessories', -- 入库仓库
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `purchase_order_items` 采购单明细表

```sql
CREATE TABLE purchase_order_items (
    id SERIAL PRIMARY KEY,
    purchase_order_id INTEGER NOT NULL REFERENCES purchase_orders(id),
    
    -- 物料信息
    product_id INTEGER REFERENCES products(id),        -- 基础物料（可选）
    variant_id INTEGER REFERENCES material_variants(id), -- 规格变体（必填其一）
    
    -- 数量
    box_count INTEGER,                                    -- 箱数
    items_per_box INTEGER,                                -- 每箱数量
    quantity NUMERIC(12, 3) NOT NULL,                    -- 总数量（= 箱数 × 每箱数量）
    unit VARCHAR(20) NOT NULL,
    
    -- 金额
    unit_price NUMERIC(12, 4) NOT NULL,                 -- 核算单价（= 实付÷总量）
    total_amount NUMERIC(15, 2) NOT NULL,                 -- 明细金额
    
    -- 批次
    batch_no VARCHAR(100),                                -- 入库批次号
    
    -- 入库状态
    received_qty NUMERIC(12, 3) DEFAULT 0,              -- 已入库数量
    is_fully_received BOOLEAN DEFAULT FALSE,
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `material_supplier_links` 物料-供应商关联表（增强版）

```sql
-- 已存在 material_suppliers 表，改造如下：
ALTER TABLE material_suppliers ADD COLUMN IF NOT EXISTS variant_id INTEGER REFERENCES material_variants(id);
ALTER TABLE material_suppliers ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE;
```

**关联规则：**
- 基础物料可以绑定供应商（所有变体继承）
- 变体可以单独覆盖供应商（如品牌A腰封有专属供应商）
- `is_default=true` 表示默认供应商

#### `material_batches` 物料批次库存表

```sql
CREATE TABLE material_batches (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id),
    variant_id INTEGER REFERENCES material_variants(id),
    
    batch_no VARCHAR(100) NOT NULL,            -- 批次号
    supplier_id INTEGER REFERENCES companies(id), -- 供应商
    
    -- 入库信息
    inbound_qty NUMERIC(12, 3) NOT NULL,       -- 入库数量
    remaining_qty NUMERIC(12, 3) NOT NULL,       -- 剩余数量
    unit_price NUMERIC(12, 4),                   -- 入库单价
    
    -- 关联
    purchase_order_item_id INTEGER REFERENCES purchase_order_items(id),
    
    -- 有效期
    expiry_date DATE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 改造现有表

#### `products` 基础物料表

```sql
-- 新增字段
ALTER TABLE products ADD COLUMN IF NOT EXISTS material_type VARCHAR(20) DEFAULT 'basic';
-- material_type: basic(基础物料) / variant(规格变体) / standalone(独立物料)
ALTER TABLE products ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES products(id);
```

**物料层级示例：**

| id | name | category | material_type | parent_id |
|----|------|----------|---------------|-----------|
| 100 | 腰封 | BOM_MATERIAL | basic | NULL |
| 101 | 通用腰封 | BOM_MATERIAL | variant | 100 |
| 102 | 品牌A腰封 | BOM_MATERIAL | variant | 100 |
| 103 | 品牌B腰封 | BOM_MATERIAL | variant | 100 |
| 200 | 真空袋 | BOM_MATERIAL | standalone | NULL |

> `standalone` 物料不区分规格，直接独立管理

### 2.3 库存联动机制

**入库流程：**
```
创建采购单 (purchase_orders)
  ↓
添加采购明细 (purchase_order_items) -- 箱数×每箱数量=总量
  ↓
确认入库 → 生成批次记录 (material_batches)
  ↓
更新物料总库存 (warehouse_stocks.current_quantity +=)
  ↓
记录库存流水 (warehouse_movements / 新建 material_stock_movements)
```

**出库流程：**
```
出库请求
  ↓
按批次扣减（先进先出）-- material_batches.remaining_qty -=
  ↓
更新物料总库存 (warehouse_stocks.current_quantity -=)
  ↓
记录库存流水
```

---

## 三、前端交互设计

### 3.1 物料列表页

```
┌──────────────────────────────────────────────────────────────┐
│ [基础物料▼] [包装物料▼] [全部变体▼] 🔍搜索...    [新增物料]     │ ← 三级筛选
├──────────────────────────────────────────────────────────────┤
│ 编码      物料名称    规格       单位  供应商    单价   库存   │
│ WF-001    腰封        基础物料    张    张三印刷   ¥0.15  3000  │ ← 基础物料（可展开）
│  ├ WF-001A  通用腰封  透明       张    张三印刷   ¥0.15  1500  │ ← 变体1
│  ├ WF-001B  品牌A腰封 蓝色/印刷  张    李四包装   ¥0.25   800  │ ← 变体2
│  └ WF-001C  品牌B腰封 红色/印刷  张    张三印刷   ¥0.20   700  │ ← 变体3
│                                                             │
│ ZD-002    真空袋      独立物料    个    王五包装   ¥0.30   500  │ ← standalone
├──────────────────────────────────────────────────────────────┤
│ 选中物料详情...                                              │
└──────────────────────────────────────────────────────────────┘
```

**设计要点：**
- 基础物料行可展开/折叠，显示下属变体
- 变体行缩进显示，视觉上形成层级
- "供应商"列显示默认供应商名称

### 3.2 采购入库弹窗

```
┌──────────────────────────────────────────────────┐
│ 采购入库 — 腰封（品牌A腰封）                       │
├──────────────────────────────────────────────────┤
│ 日期: [2026-05-26        ]                        │
│ 供应商: [品牌A印刷厂 ▼]   默认单价: ¥0.25          │
├──────────────────────────────────────────────────┤
│ 箱数: [10  ] × 每箱数量: [1300 ] = 总数量: 13000  │
│                                              张  │
├──────────────────────────────────────────────────┤
│ 实付金额: [¥3250.00    ]                        │
│ 核算单价: ¥0.2500（自动计算: 3250÷13000）          │
├──────────────────────────────────────────────────┤
│ 批次号: BM-WF001B-20260526-001（自动生成）        │
│ 入库仓库: [辅料仓库 ▼]                            │
├──────────────────────────────────────────────────┤
│ [取消]                              [确认入库]     │
└──────────────────────────────────────────────────┘
```

**交互逻辑：**
1. 选择供应商 → 自动带出默认单价
2. 修改箱数/每箱数量 → 自动计算总数量（可手动覆盖）
3. 输入实付金额 → 自动核算单价 = 实付金额 ÷ 总数量
4. 自动生成批次号

### 3.3 物料详情面板（底部）

```
┌──────────────────────────────────────────────────────────────────┐
│ [WF-001B] 品牌A腰封  蓝色/品牌A印刷 · 张    [编辑][删除][×]       │
├──────────────────────────────────────────────────────────────────┤
│ ┌────────┬──────────┬──────────────┬────────────────────────┐  │
│ │库存 800│ 单价 ¥0.25│ 每箱 1300张  │ 最近采购记录            │  │
│ │上次采购│ 品牌A印刷 │ 批次号       │ 2026-05-20 品牌A印刷厂  │  │
│ │¥0.25   │ 厂        │ BM-...-001   │ 10箱×1300=13000张 ¥3250│  │
│ │        │           │              │ 2026-05-10 张三印刷     │  │
│ └────────┴──────────┴──────────────┴────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 四、API 接口设计

### 4.1 物料管理接口

```
GET    /v4/materials?include_variants=true&category_id=1
       → 返回基础物料 + 嵌套变体数组

POST   /v4/materials
       → 创建基础物料（material_type=basic）
       
POST   /v4/materials/{id}/variants
       → 为基础物料创建规格变体

PUT    /v4/materials/{id}
       → 更新基础物料（自动级联更新所有变体的供应商信息）

GET    /v4/materials/{id}/suppliers
       → 获取物料绑定的所有供应商（含变体专属供应商）
```

### 4.2 采购单接口

```
POST   /v4/purchase-orders
       → 创建采购单（含明细）
       Body: { order_date, supplier_id, items: [{ variant_id, box_count, items_per_box, quantity, actual_amount, ... }] }

POST   /v4/purchase-orders/{id}/inbound
       → 采购单入库（批量入库）
       → 自动生成批次记录 + 更新库存

GET    /v4/purchase-orders?supplier_id=&status=&date_from=&date_to=
       → 采购单列表

GET    /v4/materials/{id}/batches
       → 物料批次库存明细
```

### 4.3 库存查询接口

```
GET    /v4/warehouse/material-stocks?product_id=&variant_id=
       → 物料总库存 + 批次明细

GET    /v4/warehouse/stock-movements?product_id=&type=inbound
       → 物料库存流水
```

---

## 五、实施计划

### Phase 1: 数据库改造（1天）
1. [ ] 创建 `material_variants` 表
2. [ ] 改造 `products` 表（加 `material_type`, `parent_id`）
3. [ ] 创建 `purchase_orders` / `purchase_order_items` 表
4. [ ] 创建 `material_batches` 表
5. [ ] 改造 `material_suppliers` 表（加 `variant_id`, `is_default`）
6. [ ] 编写 Alembic 迁移脚本

### Phase 2: 后端 API（1-2天）
1. [ ] 物料 CRUD（含变体嵌套）
2. [ ] 采购单 CRUD
3. [ ] 入库接口（自动生成批次 + 更新库存）
4. [ ] 库存查询接口（总库存 + 批次明细）
5. [ ] 库存流水记录

### Phase 3: 前端改造（1-2天）
1. [ ] 物料列表（树形结构：基础物料→变体）
2. [ ] 采购入库弹窗（箱数联动、单价核算）
3. [ ] 物料详情面板（批次库存展示）
4. [ ] 新增"采购单管理"页面

### Phase 4: 数据迁移（半天）
1. [ ] 将现有物料标记为 `standalone`
2. [ ] 腰封等需要拆分的物料，创建基础物料 + 变体
3. [ ] 迁移供应商关联关系

---

## 六、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 数据迁移丢失 | 中 | 高 | 备份数据库，分步迁移，验证后删除旧数据 |
| 库存计算错误 | 低 | 高 | 入库后自动校验：批次剩余之和 = 总库存 |
| 前端性能（树形列表） | 低 | 中 | 虚拟滚动，限制展开层级 |
| 批次号冲突 | 低 | 中 | 使用 UUID 后缀或数据库序列号 |

---

## 七、预期收益

1. **供应商维护效率提升 70%**：同一供应商只需录入一次，多个变体共享
2. **采购入库时间缩短 50%**：箱数自动算总量，实付自动算单价
3. **库存追溯能力增强**：按批次查库存来源、成本、供应商
4. **财务报表更准确**：批次成本价支持先进先出/加权平均核算

---

> 方案设计完成，等待用户确认后实施。
