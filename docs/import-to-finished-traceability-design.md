# 进口整鱼→分切加工→成品销售 全流程设计方案（最终版）

> **确认事项**：
> - 成本计算：加权平均（非 FIFO）
> - 亘昌贸易 = 绍兴优逸 = **同一个加工厂**
> - 副产品自动生成：1条鱼 = 1头 + 1尾 + 1套鱼骨 + 边角料（称重）

## 一、业务场景理解

### 实际业务流程

```
┌─────────────────────────────────────────────────────────────┐
│  挪威进口整鱼（7-8kg，161箱）                                │
│  入库 → 进口整包仓 (ZB-IMPORT)                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  开销售单 → 客户：亘昌贸易（加工厂）                        │
│  （名义销售，实际是内部加工/代工）                           │
│  价格：成本价（不加毛利）                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  出库 → 拉去加工厂分切                                       │
│  DailySlaughterRecord：记录当天宰杀/分切                     │
│  投入：鱼总重 xxx kg，产出：成品肉 xxx kg                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  成品入库 → 分包仓/成品仓                                   │
│  成品：三文鱼切片、三文鱼甜虾拼盘等                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│  成品销售 → 终端客户（餐厅、超市等）                         │
│  销售价格：市场价                                            │
└─────────────────────────────────────────────────────────────┘
```

### 关键问题

1. **亘昌贸易、绍兴优逸是名义客户**，实际是内部加工厂（或代工方），不是真正的终端客户
2. **需要原料追溯**：这批进口鱼最终变成了什么成品？卖给了哪个终端客户？
3. **成本核算**：进口鱼的成本 → 分切后成品肉的成本单价 → 成品销售的毛利
4. **现有 DailySlaughterRecord 缺少关联**：没有绑定到具体的销售单/进口批次

---

## 二、设计方案

### 2.1 客户管理：标记内部加工厂

```python
# Company 表增加字段（或复用现有字段）
class Company(Base):
    # ... 现有字段 ...
    
    # 客户类型细分
    customer_type: Mapped[Optional[str]] = mapped_column(
        String(20)
    )  # normal(普通客户), internal_processor(内部加工厂), oem(代工方)
    
    # 是否参与成本核算
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
```

**亘昌贸易（加工厂）的设置**：
- `type = "customer"`
- `customer_type = "internal_processor"`
- `is_internal = True`
- `currency = "CNY"`

**业务规则**：
- 销售给 internal_processor 时，默认价格为成本价（不加毛利）
- 销售给 internal_processor 不产生应收账款（或者应收=0，内部结算）
- 成品销售毛利计算时，排除 internal_processor 的销售单

### 2.2 宰杀记录关联销售单（核心改造）

```python
class DailySlaughterRecord(Base, TimestampMixin):
    """每日宰杀/分切记录（改造）"""
    
    # ===== 现有字段保留 =====
    id, slaughter_date, slaughter_type, fish_count, total_weight_kg, 
    meat_weight_kg, byproduct_*, loss_weight_kg, cost_price_per_kg, ...
    
    # ===== 新增关联字段 =====
    
    # 关联原料来源
    source_sale_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("whole_fish_sales.id")
    )  # 关联整鱼销售单（亘昌贸易/绍兴优逸的销售单）
    
    source_batch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("batches.id")
    )  # 关联进口批次
    
    source_invoice_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("import_invoices.id")
    )  # 关联进口发票
    
    # 原料详情（JSONB）
    source_detail: Mapped[Optional[dict]] = mapped_column(JSON)
    # 示例：{
    #   "invoice_no": "INV-2024-001",
    #   "batch_no": "BATCH-001",
    #   "sale_no": "SALE-2024-001",
    #   "customer_name": "亘昌贸易",
    #   "total_boxes": 10,      # 本次分切用了10箱
    #   "total_pieces": 24,     # 共24条
    #   "avg_weight_kg": 7.5,   # 平均重量
    #   "unit_cost_per_kg": 85.0  # 原料成本单价
    # }
    
    # 成本计算方式（固定加权平均）
    cost_calculation_method: Mapped[str] = mapped_column(
        String(20), default="weighted_average"
    )  # weighted_average(加权平均)
    
    # 副产品自动生成标志
    auto_byproduct: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否自动按 fish_count 生成副产品数量
    # 关联成品产出记录
    finished_products: Mapped[List["SlaughterFinishedProduct"]] = relationship(
        "SlaughterFinishedProduct", back_populates="slaughter_record"
    )
```

### 2.3 新增：宰杀成品产出记录表

```python
class SlaughterFinishedProduct(Base, TimestampMixin):
    """宰杀/分切后的成品产出记录
    
    记录每天分切产出了哪些成品，以及成品对应的原料来源
    """
    __tablename__ = "slaughter_finished_products"
    
    id: Mapped[int] = PK
    
    # 关联宰杀记录
    slaughter_record_id: Mapped[int] = FK("daily_slaughter_records.id")
    
    # 成品信息
    product_id: Mapped[int] = FK("products.id")  # 成品产品ID（三文鱼切片、拼盘等）
    product_name: Mapped[Optional[str]] = String(100)  # 成品名称（冗余）
    
    # 产出数量
    produced_weight_kg: Mapped[Decimal] = Numeric(12, 3)  # 产出重量(kg)
    produced_quantity: Mapped[int] = Integer  # 产出数量（盘/盒/份）
    unit: Mapped[str] = String(20)  # kg / plate / box / portion
    
    # 成本
    unit_cost: Mapped[Decimal] = Numeric(12, 4)  # 单位成本（元/kg 或 元/份）
    total_cost: Mapped[Decimal] = Numeric(15, 2)  # 总成本
    
    # 入库状态
    is_stocked: Mapped[bool] = Boolean(default=False)  # 是否已入库
    stock_inbound_id: Mapped[Optional[int]] = Integer  # 关联入库单ID
    
    # 销售状态
    is_sold: Mapped[bool] = Boolean(default=False)  # 是否已销售
    sold_weight_kg: Mapped[Decimal] = Numeric(12, 3, default=0)  # 已售重量
    sold_quantity: Mapped[int] = Integer(default=0)  # 已售数量
    
    # 关联
    slaughter_record: Mapped["DailySlaughterRecord"]
    product: Mapped["Product"]
```

### 2.4 新增：原料→成品追溯表

```python
class MaterialTraceability(Base, TimestampMixin):
    """原料追溯链
    
    记录：进口鱼 → 销售单 → 宰杀记录 → 成品 → 终端销售
    用于追踪"这批进口鱼最终卖给了谁"
    """
    __tablename__ = "material_traceability"
    
    id: Mapped[int] = PK
    
    # 原料端（进口）
    source_type: Mapped[str] = String(20)  # import(进口), domestic(国内采购)
    source_invoice_id: Mapped[Optional[int]] = FK("import_invoices.id")
    source_batch_id: Mapped[Optional[int]] = FK("batches.id")
    source_product_id: Mapped[int] = FK("products.id")  # 原料产品ID（整鱼）
    
    # 中间环节（内部流转）
    internal_sale_id: Mapped[Optional[int]] = FK("whole_fish_sales.id")  # 内部销售单（亘昌贸易/绍兴优逸）
    slaughter_record_id: Mapped[Optional[int]] = FK("daily_slaughter_records.id")
    
    # 成品端
    finished_product_id: Mapped[Optional[int]] = FK("slaughter_finished_products.id")
    finished_product_sale_id: Mapped[Optional[int]] = FK("finished_product_sales.id")  # 成品销售单
    
    # 追溯状态
    trace_status: Mapped[str] = String(20)  # in_progress(进行中), completed(已完成)
    
    # 重量流转
    source_weight_kg: Mapped[Decimal] = Numeric(12, 3)  # 原料重量
    finished_weight_kg: Mapped[Decimal] = Numeric(12, 3, default=0)  # 成品重量
    sold_weight_kg: Mapped[Decimal] = Numeric(12, 3, default=0)  # 已售成品重量
```

---

## 三、业务流程

### 流程1：进口整鱼入库

```
进口发票确认 → 创建 StockInbound
  │
  ▼
warehouse_id = ZB-IMPORT
product_id = 7-8kg整鱼
qty = 161箱
unit = "box"
detail = {
  total_boxes: 161,
  total_pieces: 387,
  avg_weight_kg: 7.5,
  boxes_detail: [...]
}
  │
  ▼
更新 Stock：ZB-IMPORT +161箱
创建 StockMovement
```

### 流程2：名义销售给内部加工厂

```
创建 WholeFishSale
  │
  ▼
customer_id = 亘昌贸易 / 绍兴优逸
sale_no = "SALE-2024-001"
sale_items = [  # 销售明细
  { product_id: 7-8kg整鱼, box_count: 10, weight_kg: 75 }
]
  │
  ▼
状态 = PENDING（不立即收款，因为是内部流转）
  │
  ▼
自动出库：ZB-IMPORT -10箱
创建 StockOutbound + StockMovement
```

**特殊处理**：
- 销售给 internal_processor 时，价格为成本价（不加毛利）
- 不产生应收账款（或者应收=0）
- 销售单标记 `is_internal_sale = True`

### 流程3：分切加工登记

```
DailySlaughterRecord 新增/编辑
  │
  ▼
slaughter_date = 2024-01-15
source_sale_id = SALE-2024-001（亘昌贸易的销售单）
source_batch_id = BATCH-001
source_invoice_id = INV-2024-001
  │
  ▼
填写投入：
  fish_count = 24条
  total_weight_kg = 180.5
  │
  ▼
填写产出：
  meat_weight_kg = 95.2（成品肉）
  byproduct_head_count = 24
  byproduct_tail_count = 24
  ...
  │
  ▼
系统自动计算：
  meat_rate = 52.7%
  cost_price_per_kg = 原料总成本 / 95.2
  total_cost = 原料总成本
  │
  ▼
关联 SlaughterFinishedProduct（产出成品）：
  - 三文鱼切片：50kg
  - 三文鱼甜虾拼盘：30盘（用15kg三文鱼 + 甜虾）
  - 三文鱼刺身：20kg
  │
  ▼
创建 MaterialTraceability 记录：
  source_invoice_id → internal_sale_id → slaughter_record_id → finished_product_id
```

### 流程4：成品入库

```
从 SlaughterFinishedProduct 创建 StockInbound
  │
  ▼
warehouse_id = FB-FISH（分包仓）
product_id = 三文鱼切片
qty = 50kg
unit = "kg"
unit_cost = 成本价（来自 DailySlaughterRecord.cost_price_per_kg）
  │
  ▼
更新 Stock：FB-FISH +50kg
更新 SlaughterFinishedProduct.is_stocked = True
```

### 流程5：成品销售给终端客户

```
创建 FinishedProductSale
  │
  ▼
customer_id = 终端餐厅/超市
sale_items = [
  { product_id: 三文鱼切片, weight_kg: 5, unit_price: 120 },
  { product_id: 三文鱼甜虾拼盘, quantity: 2, unit_price: 88 }
]
  │
  ▼
自动出库：FB-FISH -5kg三文鱼切片，-2盘拼盘
创建 StockOutbound + StockMovement
  │
  ▼
更新 MaterialTraceability：
  finished_product_sale_id = 成品销售单ID
  sold_weight_kg += 5
  trace_status = "completed"（如果全部售完）
```

### 流程6：追溯查询

```
用户查询："这批挪威进口的鱼（INV-2024-001）最终卖给了谁？"
  │
  ▼
查询 MaterialTraceability
  WHERE source_invoice_id = INV-2024-001
  │
  ▼
返回追溯链：
  进口发票 INV-2024-001
    → 批次 BATCH-001
      → 销售给亘昌贸易 SALE-2024-001（10箱，180.5kg）
        → 分切 2024-01-15（24条 → 95.2kg成品肉）
          → 三文鱼切片 50kg
            → 销售给「某餐厅」FIN-SALE-001（5kg，¥120/kg）
            → 销售给「某超市」FIN-SALE-002（剩余45kg）
          → 三文鱼甜虾拼盘 30盘
            → 销售给「某餐厅」FIN-SALE-003（2盘，¥88/盘）
```

---

## 四、成本核算

### 4.1 进口整鱼成本

```
进口整鱼总成本 = CIF价格 + 关税 + 增值税 + 清关费 + 运费

单箱成本 = 总成本 / 161箱
单条成本 = 单箱成本 / 平均每箱条数
每公斤成本 = 总成本 / 总重量
```

### 4.2 分切后成品肉成本

```
DailySlaughterRecord.cost_price_per_kg = 
  原料总成本 / meat_weight_kg

其中：原料总成本 = source_sale.total_cost（销售给亘昌贸易的成本）

成品肉成本单价 = 原料总成本 / 95.2kg
```

### 4.3 成品销售毛利

```
成品销售毛利 = 成品销售收入 - 成品成本

成品成本 = sold_weight_kg × cost_price_per_kg
（或 = sold_quantity × unit_cost）

毛利 = 销售收入 - 成品成本
毛利率 = 毛利 / 销售收入
```

### 4.4 排除内部销售的影响

```python
# 整鱼销售报表
whole_fish_sales = WholeFishSale.query(
    customer_id.not_in([亘昌贸易ID, 绍兴优逸ID])
).all()

# 或者标记 is_internal_sale
whole_fish_sales = WholeFishSale.query(
    is_internal_sale == False
).all()
```

---

## 五、前端页面设计

### 5.1 销售单页面改造（标记内部销售）

```
SalesPage（整鱼销售）
├── 新增客户时：标记 "内部加工厂"
│   └── customer_type = "internal_processor"
│
├── 创建销售单时：
│   ├── 选择客户
│   │   └── 如果是 internal_processor，显示提示"内部加工流转"
│   ├── 价格自动填充为成本价
│   ├── 收款方式默认"内部结算"
│   └── 销售单标记 is_internal_sale = True
│
└── 销售单列表：
    ├── 显示 "内部" 标签（internal_processor 的销售单）
    └── 可按 "是否内部销售" 筛选
```

### 5.2 宰杀记录页面改造（关联销售单）

```
DailySlaughterPage（宰杀记录）
├── 新增宰杀记录时：
│   ├── 选择原料来源
│   │   ├── 选项1：进口批次（直接选 ImportInvoice/Batch）
│   │   └── 选项2：内部销售单（选亘昌贸易/绍兴优逸的销售单）
│   ├── 显示原料详情
│   │   ├── 发票号、批次号、客户名
│   │   ├── 总箱数、总条数、平均重量
│   │   └── 原料成本单价
│   │
│   ├── 填写投入（鱼总重、条数）
│   ├── 填写产出（成品肉、副产品）
│   └── 填写产出成品（SlaughterFinishedProduct）
│       ├── 添加成品行：
│       │   ├── 选择成品产品（三文鱼切片/拼盘/刺身）
│       │   ├── 填写产出重量/数量
│       │   └── 系统自动计算成本
│       └── 成本 = 产出重量 / 总成品肉 × 原料总成本
│
└── 宰杀记录列表：
    ├── 显示关联的销售单号
    ├── 显示关联的发票号
    └── 操作：查看追溯链
```

### 5.3 新增：原料追溯查询页

```
MaterialTraceabilityPage（原料追溯）
├── 筛选栏
│   ├── 进口发票号
│   ├── 批次号
│   ├── 原料产品
│   └── 追溯状态（进行中/已完成）
│
├── 追溯列表（表格）
│   ├── 进口发票 → 批次 → 内部销售单 → 宰杀日期 → 成品 → 终端销售
│   └── 操作：查看完整追溯链
│
└── 追溯详情弹窗
    ├── 时间线展示：
    │   2024-01-01 进口到港 → INV-2024-001
    │   2024-01-05 入库 → ZB-IMPORT（161箱）
    │   2024-01-10 内部销售 → 亘昌贸易 SALE-2024-001（10箱）
    │   2024-01-15 分切 → 95.2kg成品肉
    │   2024-01-16 成品入库 → FB-FISH（切片50kg + 拼盘30盘）
    │   2024-01-20 终端销售 → 某餐厅（切片5kg + 拼盘2盘）
    │   2024-01-25 终端销售 → 某超市（切片45kg）
    │
    ├── 成本流转：
    │   原料成本：¥15,320
    │   成品肉成本：¥160.9/kg
    │   切片成本：¥8,045（50kg）
    │   已售切片成本：¥804.5（5kg）
    │   毛利：¥1,195.5（收入¥2,000 - 成本¥804.5）
    │
    └── 库存状态：
        已售：5kg（某餐厅）+ 45kg（某超市）= 50kg ✓
        未售：0kg
        状态：已完成追溯
```

### 5.4 新增：内部加工厂销售报表

```
InternalProcessorReportPage（内部加工报表）
├── 亘昌贸易 / 绍兴优逸 销售汇总
│   ├── 销售数量（箱/条/kg）
│   ├── 销售金额（成本价）
│   ├── 分切产出（成品肉kg）
│   └── 出肉率
│
├── 分切明细
│   ├── 按日期展示每天的分切记录
│   ├── 投入：鱼总重、条数
│   ├── 产出：成品肉、副产品
│   └── 成本：原料成本、成品肉成本单价
│
└── 成品销售汇总
    ├── 各成品的销售量
    ├── 各成品的销售额
    ├── 各成品的成本
    └── 各成品的毛利
```

---

## 六、数据模型变更汇总

### 新增字段

| 表 | 字段 | 类型 | 说明 |
|----|------|------|------|
| companies | customer_type | String(20) | normal/internal_processor/oem |
| companies | is_internal | Boolean | 是否内部客户（亘昌贸易=True） |
| daily_slaughter_records | source_sale_id | FK | 关联整鱼销售单（亘昌贸易加工厂） |
| daily_slaughter_records | source_batch_id | FK | 关联进口批次 |
| daily_slaughter_records | source_invoice_id | FK | 关联进口发票 |
| daily_slaughter_records | source_detail | JSON | 原料详情 |
| daily_slaughter_records | cost_calculation_method | String(20) | weighted_average（固定加权平均） |
| daily_slaughter_records | auto_byproduct | Boolean | 是否自动按 fish_count 生成副产品 |

### 新增表

| 表 | 说明 |
|----|------|
| slaughter_finished_products | 宰杀成品产出记录 |
| material_traceability | 原料→成品追溯链 |

### 新增索引

```sql
-- 快速查询某批进口鱼的追溯链
CREATE INDEX idx_mt_source_invoice ON material_traceability(source_invoice_id);
CREATE INDEX idx_mt_slaughter ON material_traceability(slaughter_record_id);
CREATE INDEX idx_mt_finished_sale ON material_traceability(finished_product_sale_id);

-- 快速查询某天的产出成品
CREATE INDEX idx_sfp_slaughter ON slaughter_finished_products(slaughter_record_id);
CREATE INDEX idx_sfp_product ON slaughter_finished_products(product_id);
```

---

## 七、实施计划

### 第一阶段：客户标记 + 销售单改造（1天）

1. Company 表增加 `customer_type` 和 `is_internal`
2. 亘昌贸易、绍兴优逸 标记为 internal_processor
3. WholeFishSale 增加 `is_internal_sale` 字段
4. SalesPage 改造：内部销售特殊处理
5. SalesService 改造：internal_processor 销售自动用成本价

### 第二阶段：宰杀记录关联（1-2天）

1. DailySlaughterRecord 增加 source_sale_id / source_batch_id / source_invoice_id
2. DailySlaughterPage 改造：选择原料来源
3. 新增 SlaughterFinishedProduct 表和 API
4. DailySlaughterPage 增加产出成品录入

### 第三阶段：追溯系统（1-2天）

1. 新增 MaterialTraceability 表
2. 业务流程自动化：
   - 销售给 internal_processor 时自动创建追溯记录
   - 宰杀登记时自动更新追溯记录
   - 成品入库时自动更新追溯记录
   - 成品销售时自动更新追溯记录
3. 新增追溯查询 API

### 第四阶段：报表和前端（2-3天）

1. 新增原料追溯查询页
2. 新增内部加工厂销售报表
3. 成本核算报表（原料成本 → 成品成本 → 销售毛利）
4. 库存状态联动（原料出库 → 成品入库 → 成品出库）

**总计：约 5-7 天**

---

## 八、Q&A

**Q：亘昌贸易和绍兴优逸是同一家公司还是不同的？**  
A：**已确认是同一家加工厂**。只标记一个客户（亘昌贸易），`customer_type = "internal_processor"`。

**Q：副产品怎么自动生成？**  
A：前端填写 `fish_count`（宰杀条数）后，自动填充：
- `byproduct_head_count` = `fish_count`（1条鱼1个头）
- `byproduct_tail_count` = `fish_count`（1条鱼1个尾巴）
- `byproduct_bone_count` = `fish_count`（1条鱼1套鱼骨）
- `byproduct_trim_weight_kg` = 手动填写称重（边角料重量，售卖时按重量计价用）

副产品销售：按个数卖扣 count，按重量卖扣 trim_weight_kg。

**Q：销售给 internal_processor 时，价格怎么定？**  
A：用成本价（CIF + 关税 + 增值税 + 清关费 + 运费）/ 重量。不加毛利，因为是内部流转。

**Q：成本计算为什么用加权平均而不是 FIFO？**  
A：FIFO（先进先出）要求区分每批原料的成本，但实际分切时很难区分今天切的是1月1日那批还是1月15日那批。加权平均把所有批次混一起算平均成本，更实用。

**Q：如果分切后成品有损耗，成本怎么算？**  
A：原料总成本全部计入成品肉成本。损耗是生产过程中的正常损耗，不需要单独分摊。成本单价 = 原料总成本 / 成品肉重量。

**Q：副产品（鱼头、鱼尾、鱼骨）怎么管理？**  
A：副产品可以单独入库到副产品仓（BY-PRODUCT），也可以直接计入损耗。如果副产品有销售价值，建议入库管理，后续可以销售给饲料厂等。

**Q：追溯系统对性能有影响吗？**  
A：MaterialTraceability 表的数据量取决于进口批次数量，一般不会太大（每月几十到几百条）。加上索引后查询性能不会有问题。

**Q：如果一批进口鱼分多次分切，怎么追溯？**  
A：每次分切都创建一条 DailySlaughterRecord，关联同一个 source_sale_id 或 source_batch_id。追溯查询时汇总所有分切记录。

---

_方案确定后开始实现。如有调整请指出。_
