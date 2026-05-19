# 仓库模块设计方案 V2

## 一、业务现状分析

### 现有仓库能力（finished_product_v2）
- `WarehouseStock`：成品仓库实时库存（按 product_id 一对一）
- `WarehousePurchaseOrder`：采购入库单
- `WarehouseService`：采购入库、库存查询、预警
- **问题**：只有一层仓库（FINISHED），按重量/件数管理，不支持"箱→条"多级转换

### 实际业务需求

| 业务场景 | 入库 | 存储 | 出库 | 单位 |
|---------|------|------|------|------|
| 进口整鱼（7-8kg） | 进口单证 → 整包仓 | 按箱管理 | 整箱销售 / 调拨到分包仓 | 箱→条 |
| 国内采购整鱼 | 采购入库 → 整包仓 | 按箱管理 | 整箱销售 / 调拨到分包仓 | 箱→条 |
| 整鱼单条销售 | 调拨入库 → 分包仓 | 按条管理 | 单条销售 | 条 |
| 去尾甜虾 | 采购入库 → 整包仓 | 按箱/板管理 | 整板销售 / 调拨拆分 | 箱→板→只 |
| 成品拼盘 | 生产组装 → 分包仓 | 按盘管理 | 按盘销售 | 盘 |
| 包装物/消耗品 | 采购入库 → 辅料仓 | 按件/卷管理 | 生产领用 | 件 |
| 副产品 | 宰杀产生 → 副产品仓 | 按kg管理 | 销售出库 | kg |

**核心痛点**：
1. 现有库存是 product 一对一，不支持同一产品分仓存储
2. 不支持"箱→条"的单位转换（一箱可能有2条或3条，每箱实际内容不同）
3. 进口单证业务和国内业务混在一起，无法独立核算
4. 缺少调拨、拆分、组装等库内作业记录

---

## 二、设计原则

1. **业务隔离**：进口单证采购/销售 与 国内采购/销售 在库存层面独立
2. **多级单位**：支持"箱→条→片"、"箱→板→只"等多级单位转换
3. **批次追溯**：每批入库记录实际内容（如161箱中每箱的条数）
4. **最小改动**：复用现有 Product/Company/Invoice 模型，只新增仓库相关表
5. **库存准确**：每一笔出入库都有 movement 记录，支持追溯和对账

---

## 三、数据模型

### 3.1 仓库定义表（新增）

```python
class Warehouse(Base, TimestampMixin):
    """仓库定义"""
    __tablename__ = "warehouses"
    
    id: Mapped[int] = PK
    code: Mapped[str] = String(20)  # 仓库编码：ZB-01(整包1号), FB-01(分包1号), FL-01(辅料)
    name: Mapped[str] = String(50)  # 仓库名称
    type: Mapped[WarehouseType] = Enum  # whole_package(整包), sub_package(分包), accessory(辅料), byproduct(副产品)
    business_scope: Mapped[str] = String(20)  # import(进口单证), domestic(国内业务), all(通用)
    is_active: Mapped[bool] = default(True)
    notes: Mapped[Optional[str]]
```

**仓库初始化数据**：
| code | name | type | business_scope |
|------|------|------|----------------|
| ZB-IMPORT | 进口整包仓 | whole_package | import |
| ZB-DOMESTIC | 国内整包仓 | whole_package | domestic |
| FB-FISH | 分包仓（整鱼） | sub_package | all |
| FB-SHRIMP | 分包仓（甜虾） | sub_package | all |
| FL-MATERIAL | 辅料仓 | accessory | all |
| BY-PRODUCT | 副产品仓 | byproduct | all |

### 3.2 库存记录表（替代现有 WarehouseStock）

```python
class Stock(Base, TimestampMixin):
    """库存记录（按仓库+产品+批次）"""
    __tablename__ = "stocks"
    
    id: Mapped[int] = PK
    warehouse_id: Mapped[int] = FK("warehouses.id")
    product_id: Mapped[int] = FK("products.id")
    batch_id: Mapped[Optional[int]] = FK("batches.id")  # 进口批次（进口单证业务）
    
    # 数量（按当前仓库的管理单位）
    current_qty: Mapped[Decimal] = Numeric(12,3)  # 当前数量
    reserved_qty: Mapped[Decimal] = Numeric(12,3)  # 预留（已售未出）
    available_qty: Mapped[Decimal] = Numeric(12,3)  # 可用 = current - reserved
    
    # 成本
    unit_cost: Mapped[Optional[Decimal]] = Numeric(12,4)  # 加权平均成本
    total_cost: Mapped[Optional[Decimal]] = Numeric(15,2)  # 总成本 = current_qty * unit_cost
    
    # 单位（与 Product.unit 一致或仓库特定）
    unit: Mapped[str] = String(20)  # box(箱), piece(条), board(板), kg, plate(盘)
    
    # 预警
    warning_threshold: Mapped[int] = default(0)
    is_below_warning: Mapped[bool] = default(False)
    
    # 最后异动日期
    last_in_date: Mapped[Optional[date]]
    last_out_date: Mapped[Optional[date]]
    
    # 库位
    location: Mapped[Optional[str]] = String(100)
    
    # 关联
    warehouse: Mapped[Warehouse]
    product: Mapped[Product]
    batch: Mapped[Optional[Batch]]
    
    # 唯一约束：同一仓库+产品+批次只有一条记录
    __table_args__ = (UniqueConstraint("warehouse_id", "product_id", "batch_id"),)
```

### 3.3 入库记录表（替代现有 WarehousePurchaseOrder）

```python
class StockInbound(Base, TimestampMixin):
    """入库记录（统一入口）"""
    __tablename__ = "stock_inbounds"
    
    id: Mapped[int] = PK
    
    # 来源
    source_type: Mapped[str] = String(50)  # import_invoice(进口单证), purchase_order(采购单), transfer_in(调拨入), return(退货)
    source_id: Mapped[Optional[int]] = Integer  # 关联单据ID
    source_no: Mapped[Optional[str]] = String(100)  # 单据编号（发票号/采购单号）
    
    # 仓库和产品
    warehouse_id: Mapped[int] = FK("warehouses.id")
    product_id: Mapped[int] = FK("products.id")
    batch_id: Mapped[Optional[int]] = FK("batches.id")
    
    # 数量
    qty: Mapped[Decimal] = Numeric(12,3)  # 入库数量
    unit: Mapped[str] = String(20)  # 入库单位
    
    # 成本
    unit_cost: Mapped[Decimal] = Numeric(12,4)  # 单位成本
    total_cost: Mapped[Decimal] = Numeric(15,2)  # 总成本
    
    # 供应商
    supplier_id: Mapped[Optional[int]] = FK("companies.id")
    
    # 入库详情（JSONB，记录实际内容）
    detail: Mapped[Optional[dict]] = JSON  # { "boxes": 161, "pieces_per_box": [2,3,2,3,...], "avg_weight_kg": 7.5 }
    
    # 状态
    status: Mapped[str] = String(20)  # pending, completed, cancelled
    inbound_date: Mapped[date] = Date
    notes: Mapped[Optional[str]]
```

**detail 示例（进口整鱼）**：
```json
{
  "total_boxes": 161,
  "total_pieces": 387,
  "avg_pieces_per_box": 2.4,
  "boxes_detail": [
    { "box_no": "B001", "pieces": 2, "weight_kg": 15.2 },
    { "box_no": "B002", "pieces": 3, "weight_kg": 22.1 }
  ],
  "spec": "7-8kg",
  "origin": "Norway"
}
```

**detail 示例（去尾甜虾）**：
```json
{
  "total_boxes": 50,
  "boards_per_box": 40,
  "pieces_per_board": 30,
  "total_boards": 2000,
  "total_pieces": 60000,
  "unit": "box"
}
```

### 3.4 出库记录表（新增）

```python
class StockOutbound(Base, TimestampMixin):
    """出库记录"""
    __tablename__ = "stock_outbounds"
    
    id: Mapped[int] = PK
    
    # 去向
    dest_type: Mapped[str] = String(50)  # sale(销售), transfer_out(调拨出), production(生产领用), loss(损耗)
    dest_id: Mapped[Optional[int]] = Integer
    dest_no: Mapped[Optional[str]] = String(100)
    
    warehouse_id: Mapped[int] = FK("warehouses.id")
    product_id: Mapped[int] = FK("products.id")
    batch_id: Mapped[Optional[int]] = FK("batches.id")
    
    qty: Mapped[Decimal] = Numeric(12,3)
    unit: Mapped[str] = String(20)
    
    unit_cost: Mapped[Optional[Decimal]] = Numeric(12,4)  # 出库成本（加权平均）
    total_cost: Mapped[Optional[Decimal]] = Numeric(15,2)
    
    outbound_date: Mapped[date] = Date
    status: Mapped[str] = String(20)  # pending, completed, cancelled
    notes: Mapped[Optional[str]]
```

### 3.5 调拨记录表（新增）

```python
class StockTransfer(Base, TimestampMixin):
    """调拨记录（整包仓 → 分包仓）"""
    __tablename__ = "stock_transfers"
    
    id: Mapped[int] = PK
    
    # 调拨方向
    from_warehouse_id: Mapped[int] = FK("warehouses.id")
    to_warehouse_id: Mapped[int] = FK("warehouses.id")
    
    product_id: Mapped[int] = FK("products.id")
    batch_id: Mapped[Optional[int]] = FK("batches.id")
    
    # 调出数量（整包仓单位）
    from_qty: Mapped[Decimal] = Numeric(12,3)
    from_unit: Mapped[str] = String(20)
    
    # 调入数量（分包仓单位）
    to_qty: Mapped[Decimal] = Numeric(12,3)
    to_unit: Mapped[str] = String(20)
    
    # 转换比例
    conversion_ratio: Mapped[Decimal] = Numeric(10,4)  # to_qty / from_qty（如：2.4条/箱）
    
    # 实际内容（拆分详情）
    detail: Mapped[Optional[dict]] = JSON  # { "pieces": 387, "pieces_detail": [...] }
    
    status: Mapped[str] = String(20)  # pending, completed, cancelled
    transfer_date: Mapped[date] = Date
    notes: Mapped[Optional[str]]
```

### 3.6 库存变动记录表（统一审计）

```python
class StockMovement(Base, TimestampMixin):
    """库存变动记录（每一笔异动都记录）"""
    __tablename__ = "stock_movements"
    
    id: Mapped[int] = PK
    
    warehouse_id: Mapped[int] = FK("warehouses.id")
    product_id: Mapped[int] = FK("products.id")
    batch_id: Mapped[Optional[int]] = FK("batches.id")
    
    movement_type: Mapped[str] = String(20)  # INBOUND, OUTBOUND, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT
    movement_date: Mapped[date] = Date
    
    # 数量变动（正数=增加，负数=减少）
    qty_change: Mapped[Decimal] = Numeric(12,3)
    qty_before: Mapped[Decimal] = Numeric(12,3)
    qty_after: Mapped[Decimal] = Numeric(12,3)
    unit: Mapped[str] = String(20)
    
    # 关联单据
    ref_type: Mapped[str] = String(50)  # StockInbound, StockOutbound, StockTransfer, Sale, Adjustment
    ref_id: Mapped[int] = Integer
    ref_no: Mapped[Optional[str]] = String(100)
    
    notes: Mapped[Optional[str]]
```

### 3.7 产品单位转换规则表（新增）

```python
class ProductUnitConversion(Base, TimestampMixin):
    """产品单位转换规则"""
    __tablename__ = "product_unit_conversions"
    
    id: Mapped[int] = PK
    product_id: Mapped[int] = FK("products.id")
    
    from_unit: Mapped[str] = String(20)  # box
    to_unit: Mapped[str] = String(20)    # piece
    ratio: Mapped[Decimal] = Numeric(10,4)  # 1 box = 2.4 piece（平均值）
    
    is_default: Mapped[bool] = default(True)  # 是否默认规则
    notes: Mapped[Optional[str]]
```

---

## 四、业务流程

### 4.1 进口整鱼入库

```
进口发票到港 → 创建 StockInbound
  │
  ▼
填写入库信息：
  - warehouse_id = ZB-IMPORT（进口整包仓）
  - source_type = "import_invoice"
  - source_id = ImportInvoice.id
  - product_id = 7-8kg整鱼产品ID
  - qty = 161（箱）
  - unit = "box"
  - detail = { boxes: 161, total_pieces: 387, boxes_detail: [...] }
  │
  ▼
后端处理：
  1. 创建 StockInbound 记录
  2. 更新 Stock：ZB-IMPORT +161箱
  3. 创建 StockMovement：INBOUND +161
  4. 计算加权平均成本
```

### 4.2 国内采购整鱼入库

```
国内采购到货 → 创建 StockInbound
  │
  ▼
填写入库信息：
  - warehouse_id = ZB-DOMESTIC（国内整包仓）
  - source_type = "purchase_order"
  - 其余同上
  │
  ▼
后端处理：
  1. 创建 StockInbound 记录
  2. 更新 Stock：ZB-DOMESTIC +N箱
  3. 创建 StockMovement：INBOUND +N
```

**关键：进口和国内分仓存储，互不干扰**

### 4.3 整鱼销售出库（整箱）

```
创建销售单 → 选择整鱼产品 → 填写箱数
  │
  ▼
后端自动出库：
  1. 校验库存：ZB-IMPORT 可用箱数 >= 销售箱数？
  2. 创建 StockOutbound
  3. 更新 Stock：ZB-IMPORT -N箱
  4. 创建 StockMovement：OUTBOUND -N
  5. 关联销售单
```

### 4.4 整箱调拨到分包仓（拆分成单条）

```
创建调拨单
  │
  ▼
填写调拨信息：
  - from_warehouse = ZB-IMPORT
  - to_warehouse = FB-FISH
  - product_id = 7-8kg整鱼
  - from_qty = 10（箱）
  - from_unit = "box"
  │
  ▼
后端处理：
  1. 校验 ZB-IMPORT 可用箱数 >= 10
  2. 根据 StockInbound.detail 获取这10箱的实际条数
     （如：B001有2条，B002有3条... 共24条）
  3. 创建 StockTransfer：
     - from_qty = 10, to_qty = 24
     - conversion_ratio = 2.4
     - detail = { pieces: 24, boxes: [...] }
  4. 更新 Stock：
     - ZB-IMPORT：-10箱
     - FB-FISH：+24条
  5. 创建 StockMovement：
     - TRANSFER_OUT -10（ZB-IMPORT）
     - TRANSFER_IN +24（FB-FISH）
```

### 4.5 分包仓单条销售

```
创建销售单 → 选择单条整鱼 → 填写条数
  │
  ▼
后端自动出库：
  1. 校验 FB-FISH 可用条数 >= 销售条数
  2. 创建 StockOutbound
  3. 更新 Stock：FB-FISH -N条
  4. 创建 StockMovement：OUTBOUND -N
```

### 4.6 去尾甜虾入库

```
采购入库 → ZB-DOMESTIC
  │
  ▼
detail = {
  total_boxes: 50,
  boards_per_box: 40,
  pieces_per_board: 30,
  total_boards: 2000,
  total_pieces: 60000
}
  │
  ▼
Stock：ZB-DOMESTIC +50箱
```

### 4.7 甜虾调拨到分包仓（拆分成板/只）

```
调拨单：ZB-DOMESTIC → FB-SHRIMP
  - from_qty = 5箱
  - to_qty = 200板（5×40）
  - conversion_ratio = 40
  │
  ▼
或拆分成只：
  - from_qty = 5箱
  - to_qty = 6000只（5×40×30）
  - conversion_ratio = 1200
```

### 4.8 成品拼盘生产组装

```
生产领料（从分包仓出库）：
  - FB-FISH：-0.5kg 三文鱼切片
  - FB-SHRIMP：-10只 甜虾
  - FL-MATERIAL：-1个 包装盒
  │
  ▼
生产组装 → 成品入库 FB-FINISHED
  - 产品：三文鱼甜虾拼盘
  - qty：+1盘
  │
  ▼
记录 StockMovement：
  - OUTBOUND（生产领用）
  - INBOUND（成品入库）
```

---

## 五、API 设计

### 5.1 仓库管理

```
GET    /api/v1/warehouses              # 仓库列表
POST   /api/v1/warehouses              # 创建仓库
GET    /api/v1/warehouses/{id}         # 仓库详情
PUT    /api/v1/warehouses/{id}         # 更新仓库
```

### 5.2 库存查询

```
GET    /api/v1/warehouse/stocks        # 库存列表
       ?warehouse_id=1                # 按仓库筛选
       &product_id=123                # 按产品筛选
       &batch_id=456                  # 按批次筛选
       &is_below_warning=true         # 预警筛选
       
GET    /api/v1/warehouse/stocks/summary  # 库存汇总
       ?warehouse_type=whole_package  # 按仓库类型汇总
```

### 5.3 入库管理

```
POST   /api/v1/warehouse/inbounds      # 创建入库单
GET    /api/v1/warehouse/inbounds      # 入库列表
GET    /api/v1/warehouse/inbounds/{id} # 入库详情
PUT    /api/v1/warehouse/inbounds/{id} # 修改入库单（未确认前）
POST   /api/v1/warehouse/inbounds/{id}/confirm  # 确认入库
POST   /api/v1/warehouse/inbounds/{id}/cancel   # 取消入库
```

### 5.4 出库管理

```
POST   /api/v1/warehouse/outbounds     # 创建出库单
GET    /api/v1/warehouse/outbounds     # 出库列表
POST   /api/v1/warehouse/outbounds/{id}/confirm  # 确认出库
POST   /api/v1/warehouse/outbounds/{id}/cancel   # 取消出库
```

### 5.5 调拨管理

```
POST   /api/v1/warehouse/transfers     # 创建调拨单
GET    /api/v1/warehouse/transfers     # 调拨列表
POST   /api/v1/warehouse/transfers/{id}/confirm  # 确认调拨
POST   /api/v1/warehouse/transfers/{id}/cancel   # 取消调拨
```

### 5.6 库存变动查询

```
GET    /api/v1/warehouse/movements     # 变动记录
       ?warehouse_id=1
       &product_id=123
       &movement_type=INBOUND
       &start_date=2024-01-01
```

---

## 六、前端页面设计

### 6.1 仓库管理页（新增）

```
仓库管理
├── 仓库列表（表格）
│   ├── 编码 / 名称 / 类型 / 业务范围 / 状态
│   └── 操作：编辑 / 停用
└── 新增仓库（弹窗）
```

### 6.2 库存查询页（重构 WarehousePage）

```
库存查询
├── 筛选栏
│   ├── 仓库选择（多选）
│   ├── 产品分类（整鱼/甜虾/成品/辅料/副产品）
│   ├── 业务类型（进口/国内）
│   └── 预警状态
├── 库存汇总卡片
│   ├── 总库存金额
│   ├── 进口仓库存
│   ├── 国内仓库存
│   └── 预警项数
├── 库存列表（表格）
│   ├── 仓库 / 产品 / 批次 / 当前数量 / 可用数量
│   ├── 单位 / 成本 / 总金额 / 库位
│   └── 操作：查看明细 / 调拨 / 盘点调整
└── 库存明细弹窗
    ├── 入库记录
    ├── 出库记录
    ├── 调拨记录
    └── 变动流水
```

### 6.3 入库管理页（新增）

```
入库管理
├── 筛选栏（日期/仓库/来源类型/状态）
├── 入库列表（表格）
│   ├── 入库单号 / 日期 / 仓库 / 产品 / 数量
│   ├── 来源 / 供应商 / 状态
│   └── 操作：查看 / 确认 / 取消
└── 新增入库（弹窗）
    ├── 选择仓库
    ├── 选择产品
    ├── 填写数量和单位
    ├── 填写来源（发票/采购单）
    ├── 填写实际内容（detail JSON）
    └── 确认入库
```

### 6.4 调拨管理页（新增）

```
调拨管理
├── 筛选栏
├── 调拨列表（表格）
│   ├── 调拨单号 / 日期 / 调出仓 → 调入仓
│   ├── 产品 / 数量 / 转换比例
│   └── 操作：查看 / 确认 / 取消
└── 新增调拨（弹窗）
    ├── 选择调出仓库
    ├── 选择调入仓库
    ├── 选择产品
    ├── 填写调出数量（箱/板）
    ├── 系统自动计算调入数量（条/只）
    ├── 确认实际拆分内容
    └── 保存调拨单
```

---

## 七、关键业务规则

### 7.1 库存校验规则

```python
# 出库前校验
def validate_outbound(warehouse_id, product_id, batch_id, qty):
    stock = get_stock(warehouse_id, product_id, batch_id)
    if stock.available_qty < qty:
        raise "库存不足：可用{}，需要{}".format(stock.available_qty, qty)
    
    # 检查预留
    if stock.reserved_qty > 0:
        # 允许出库，但需确认是否优先释放预留
        pass

# 调拨前校验
def validate_transfer(from_id, to_id, product_id, qty):
    from_stock = get_stock(from_id, product_id, None)
    if from_stock.available_qty < qty:
        raise "调出仓库存不足"
    
    # 检查仓库类型兼容性
    from_wh = get_warehouse(from_id)
    to_wh = get_warehouse(to_id)
    if from_wh.type == "whole_package" and to_wh.type != "sub_package":
        raise "整包仓只能调拨到分包仓"
```

### 7.2 单位转换规则

```python
# 调拨时单位转换
def convert_on_transfer(from_unit, to_unit, from_qty, inbound_detail=None):
    """
    1. 优先使用入库时的实际 detail（精确）
    2. 其次使用 ProductUnitConversion 规则（平均）
    3. 最后使用固定比例（默认）
    """
    if inbound_detail:
        # 从 detail 中获取实际条数
        total_pieces = inbound_detail.get("total_pieces")
        total_boxes = inbound_detail.get("total_boxes")
        ratio = total_pieces / total_boxes
        return from_qty * ratio
    
    # 使用转换规则
    rule = ProductUnitConversion.query(
        from_unit=from_unit, to_unit=to_unit
    ).first()
    if rule:
        return from_qty * rule.ratio
    
    raise "无法转换单位：{} → {}".format(from_unit, to_unit)
```

### 7.3 成本计算规则

```python
# 入库时加权平均成本
def update_unit_cost_on_inbound(stock, inbound_qty, inbound_unit_cost):
    old_total = stock.current_qty * (stock.unit_cost or 0)
    new_total = inbound_qty * inbound_unit_cost
    total_qty = stock.current_qty + inbound_qty
    
    if total_qty > 0:
        stock.unit_cost = (old_total + new_total) / total_qty
    stock.total_cost = total_qty * stock.unit_cost

# 出库时成本（先进先出或加权平均）
def get_outbound_cost(stock, outbound_qty):
    # 使用加权平均
    return stock.unit_cost * outbound_qty
```

### 7.4 业务隔离规则

```python
# 进口单证和国内业务隔离
def validate_business_isolation(warehouse_id, source_type):
    wh = get_warehouse(warehouse_id)
    
    if source_type == "import_invoice" and wh.business_scope == "domestic":
        raise "进口单证不能入库到国内仓"
    
    if source_type == "purchase_order" and wh.business_scope == "import":
        raise "国内采购不能入库到进口仓"
```

---

## 八、实施计划

### 第一阶段：基础模型（1-2天）

1. **数据库迁移**
   - 创建 `warehouses` 表
   - 创建 `stocks` 表（替代 warehouse_stocks）
   - 创建 `stock_inbounds` 表（替代 warehouse_purchase_orders）
   - 创建 `stock_outbounds` 表
   - 创建 `stock_transfers` 表
   - 创建 `stock_movements` 表
   - 创建 `product_unit_conversions` 表
   - 迁移现有 warehouse_stocks 数据到 stocks

2. **后端模型**
   - 新增/修改 models
   - 新增 schemas

### 第二阶段：核心 API（2-3天）

1. **仓库管理 API**
2. **库存查询 API**
3. **入库管理 API**
4. **出库管理 API**
5. **调拨管理 API**
6. **库存变动查询 API**

### 第三阶段：业务集成（2-3天）

1. **进口发票入库集成**
   - 发票确认到港时自动创建入库单
2. **销售出库集成**
   - 销售单确认时自动扣减库存
3. **调拨集成**
   - 整包仓 → 分包仓调拨
4. **生产领料集成**
   - 成品组装时自动扣减原料库存

### 第四阶段：前端页面（2-3天）

1. **仓库管理页**
2. **库存查询页（重构）**
3. **入库管理页**
4. **调拨管理页**
5. **库存变动查询页**

---

## 九、Q&A

**Q：现有 WarehouseStock/WarehousePurchaseOrder 怎么办？**  
A：保留现有表不动，新增 stocks/stock_inbounds 等表。通过数据迁移把现有数据导入新表，前端逐步切换到新页面。等验证稳定后，再删除旧表。

**Q：一箱有2条或3条，调拨时怎么知道具体条数？**  
A：入库时在 `StockInbound.detail` 中记录每箱的实际条数。调拨时系统根据 detail 计算精确条数。如果 detail 中没有记录，则使用 `ProductUnitConversion` 的平均比例。

**Q：进口和国内业务怎么隔离？**  
A：通过仓库的 `business_scope` 字段控制。进口发票只能入库到 `business_scope="import"` 的仓库，国内采购只能入库到 `business_scope="domestic"` 的仓库。销售时也按仓库类型筛选。

**Q：成品拼盘的库存怎么管理？**  
A：成品拼盘作为独立的 Product（category="finished_product"），入库到分包仓或成品仓。生产时通过"生产领料"从原料仓扣减原料，同时入库成品。

**Q：包装物和消耗品怎么管理？**  
A：放入辅料仓（accessory）。采购入库时按件/卷管理，生产领用时扣减库存。可以设置安全库存预警。

**Q：副产品怎么管理？**  
A：放入副产品仓（byproduct）。宰杀时自动产生副产品入库记录，销售时从副产品仓出库。副产品不做预警。

---

## 十、预估工作量

| 阶段 | 文件数 | 工作量 |
|------|--------|--------|
| 数据库迁移 | 1-2个 | 0.5天 |
| 后端模型+Schema | 5-6个 | 1天 |
| 后端 Service | 3-4个 | 2天 |
| 后端 API | 5-6个 | 2天 |
| 前端页面 | 4-5个 | 3天 |
| 业务集成 | 修改现有文件 | 2天 |
| **总计** | **~25个文件** | **~10天** |

---

_方案确定后开始实现。如有调整请指出。_
