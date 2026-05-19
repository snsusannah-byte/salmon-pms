# 采购入库模块设计方案

**版本**: V1  
**日期**: 2026-05-15  
**核心定位**: **三文鱼是主产品**，其他（甜虾、北极贝、包装物等）均为搭配/辅料  
**适用场景**: 三文鱼国内采购、搭配品采购、包材采购

---

## 一、业务场景分析

### 1.1 业务定位：三文鱼为主 · 其他为搭配

```
┌─────────────────────────────────────────────────────────────┐
│                     三文鱼为主 · 其他为搭配                    │
├─────────────────────────────────────────────────────────────┤
│  主产品（核心业务）                                          │
│  ├── 三文鱼进口整鱼 → ZB-IMPORT（进口整包仓）               │
│  ├── 三文鱼国内整鱼 → ZB-DOMESTIC（国内整包仓）           │
│  └── 三文鱼分切成品 → FB-FISH（分包仓-整鱼）               │
│                                                             │
│  搭配品（围绕三文鱼销售）                                     │
│  ├── 甜虾整包/分包 → FB-SHRIMP（分包仓-甜虾）             │
│  ├── 北极贝整包/分包 → FB-SHRIMP（分包仓-甜虾）           │
│  └── 其他海鲜搭配 → FB-SHRIMP（分包仓-甜虾）               │
│                                                             │
│  辅料（生产消耗）                                            │
│  ├── 包装物 → FL-MATERIAL（辅料仓）                        │
│  ├── 标签/泡沫箱 → FL-MATERIAL（辅料仓）                   │
│  └── 其他消耗品 → FL-MATERIAL（辅料仓）                    │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 采购类型

| 采购类型 | 定位 | 目标仓库 | 产品分类 | 计量单位 |
|----------|------|----------|----------|----------|
| 三文鱼进口整鱼 | **主产品·核心** | ZB-IMPORT | whole_fish | 箱/kg |
| 三文鱼国内整鱼 | **主产品·核心** | ZB-DOMESTIC | whole_fish | 箱/kg |
| 三文鱼分切成品 | **主产品·成品** | FB-FISH | finished_product | 条/板 |
| 甜虾整包 | 搭配品 | ZB-DOMESTIC | whole_fish | 箱 |
| 甜虾分包 | 搭配品 | FB-SHRIMP | finished_product | 板/只 |
| 北极贝整包 | 搭配品 | ZB-DOMESTIC | whole_fish | 箱 |
| 北极贝分包 | 搭配品 | FB-SHRIMP | finished_product | 板/只 |
| 包装物/消耗品 | 辅料 | FL-MATERIAL | packaging / accessory | 个/卷/箱 |

### 1.3 业务流程

```
┌──────────────────────────────────────────────────────────────┐
│  三文鱼采购（主产品）                                         │
│  ─────────────────                                           │
│  供应商发货 → 入 ZB-IMPORT 或 ZB-DOMESTIC                   │
│  整鱼销售：从整包仓直接出库                                  │
│  分切销售：调拨到 FB-FISH → 分包仓按条/板管理               │
└──────────────────────────────────────────────────────────────┘
                              │
                              │ 搭配品采购（同步进行）
                              ↓
┌──────────────────────────────────────────────────────────────┐
│  搭配品采购（甜虾/北极贝）                                   │
│  ─────────────────                                           │
│  整包采购 → 入 ZB-DOMESTIC（与三文鱼同仓）                  │
│  调拨分包 → FB-SHRIMP（按板/只管理）                        │
│  拼盘销售时：三文鱼 + 甜虾 + 北极贝 组合出库                  │
└──────────────────────────────────────────────────────────────┘
```

### 1.4 核心原则

1. **三文鱼优先**：采购单默认聚焦三文鱼，搭配品作为附加项
2. **同仓管理**：三文鱼和搭配品整包阶段共用 ZB-DOMESTIC，方便统一管理
3. **分包分离**：三文鱼分切入 FB-FISH，甜虾/北极贝入 FB-SHRIMP，分类清晰
4. **组合销售**：拼盘以三文鱼为主，搭配品为辅，分别扣减库存

---

## 二、数据模型设计

### 2.1 采购单表（purchase_orders）

```sql
CREATE TABLE purchase_orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(50) UNIQUE NOT NULL,    -- PO20260515-001
    order_date DATE NOT NULL,
    
    supplier_id INTEGER NOT NULL REFERENCES companies(id),  -- 供应商
    
    -- 主产品信息（三文鱼）
    main_product_type VARCHAR(20) NOT NULL,    -- import_whole_fish / domestic_whole_fish
    main_warehouse_id INTEGER NOT NULL REFERENCES warehouses(id), -- 主产品目标仓库
    
    -- 搭配品标志
    has_accessories BOOLEAN DEFAULT false,       -- 是否含搭配品
    
    total_qty NUMERIC(12,3) NOT NULL,        -- 总数量（主产品）
    total_amount NUMERIC(15,2) NOT NULL,       -- 总金额
    
    status VARCHAR(20) DEFAULT 'pending',      -- pending(待入库) / partial(部分入库) / completed(已完成) / cancelled(已取消)
    
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2.2 采购单项表（purchase_order_items）

```sql
CREATE TABLE purchase_order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES purchase_orders(id),
    
    product_id INTEGER NOT NULL REFERENCES products(id),     -- 产品
    batch_id INTEGER REFERENCES batches(id),                  -- 可选：关联批次
    
    item_type VARCHAR(20) NOT NULL DEFAULT 'main',  -- main(主产品·三文鱼) / accessory(搭配品) / material(辅料)
    
    qty NUMERIC(12,3) NOT NULL,              -- 采购数量
    unit VARCHAR(20) NOT NULL,               -- 单位
    unit_price NUMERIC(12,4) NOT NULL,       -- 单价
    total_amount NUMERIC(15,2) NOT NULL,     -- 小计
    
    received_qty NUMERIC(12,3) DEFAULT 0,    -- 已入库数量
    warehouse_id INTEGER REFERENCES warehouses(id),  -- 目标仓库（搭配品可能不同仓）
    
    notes TEXT
);
```

### 2.3 与现有表的关系

```
purchase_orders
    ├── supplier_id → companies (type='supplier')
    ├── main_warehouse_id → warehouses（主产品仓库：ZB-IMPORT/ZB-DOMESTIC）
    └── items → purchase_order_items
            ├── product_id → products
            ├── warehouse_id → warehouses（搭配品仓库：FB-SHRIMP/FL-MATERIAL）
            └── batch_id → batches (可选)

到货后生成：
    └── stock_inbounds (source_type='purchase_order', source_id=po.id)
```

---

## 三、API设计

### 3.1 采购单管理

```
POST   /api/v1/purchase-orders              # 创建采购单
GET    /api/v1/purchase-orders              # 列表
GET    /api/v1/purchase-orders/{id}         # 详情
PUT    /api/v1/purchase-orders/{id}        # 修改（待入库状态）
POST   /api/v1/purchase-orders/{id}/cancel  # 取消
```

### 3.2 创建采购单（支持主产品+搭配品）

```
POST /api/v1/purchase-orders

Body:
{
  "supplier_id": 15,
  "main_product_type": "domestic_whole_fish",
  "main_warehouse_id": 2,          -- ZB-DOMESTIC
  "order_date": "2026-05-15",
  
  -- 主产品（三文鱼）
  "main_item": {
    "product_id": 45,              -- 7-8kg三文鱼整鱼
    "qty": 50,
    "unit": "box",
    "unit_price": 85.50
  },
  
  -- 搭配品（可选）
  "accessory_items": [
    {
      "product_id": 201,           -- 甜虾整包
      "qty": 10,
      "unit": "box",
      "unit_price": 120.00,
      "warehouse_id": 2            -- ZB-DOMESTIC（与三文鱼同仓）
    },
    {
      "product_id": 202,           -- 北极贝整包
      "qty": 5,
      "unit": "box",
      "unit_price": 200.00,
      "warehouse_id": 2
    }
  ],
  
  -- 辅料（可选）
  "material_items": [
    {
      "product_id": 301,           -- 真空袋
      "qty": 500,
      "unit": "个",
      "unit_price": 0.50,
      "warehouse_id": 5             -- FL-MATERIAL
    }
  ]
}
```

### 3.3 一键入库（按产品类型分流）

```
POST /api/v1/purchase-orders/{id}/inbound

-- 自动根据采购单创建入库单：
-- 1. 三文鱼 → ZB-DOMESTIC（整包仓）
-- 2. 甜虾/北极贝 → ZB-DOMESTIC（整包仓，与三文鱼同仓）
-- 3. 辅料 → FL-MATERIAL（辅料仓）
-- 4. 更新采购单状态
-- 5. 创建库存变动记录
```

---

## 四、前端页面设计

### 4.1 采购管理页面（/purchase-orders）

```
┌──────────────────────────────────────────────────────────────┐
│ 采购管理（三文鱼为主）              [新建采购单]               │
├──────────────────────────────────────────────────────────────┤
│ [全部] [待入库] [部分入库] [已完成] [已取消]                   │
├──────────────────────────────────────────────────────────────┤
│ 采购单号    供应商    主产品      搭配品    金额      状态     │
│ PO20260515  XX渔业   三文鱼50箱   甜虾10箱  ¥6,475   待入库   │
│ PO20260514  YY商行   三文鱼30箱   无        ¥2,565   已完成   │
│ ...                                                         │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 新建采购单弹窗

```
┌──────────────────────────────────────────────────────────────┐
│ 新建采购单 — 三文鱼为主                                       │
├──────────────────────────────────────────────────────────────┤
│ 供应商: [下拉选择]                                           │
│ 采购日期: [日期选择]                                         │
├──────────────────────────────────────────────────────────────┤
│ 【主产品·三文鱼】 ← 蓝色高亮                                 │
│ 类型: [进口整鱼 / 国内整鱼]                                  │
│ 仓库: [自动匹配: ZB-IMPORT / ZB-DOMESTIC]                    │
│ 产品: [下拉选择三文鱼规格]                                   │
│ 数量: [   ] 单位: [箱/kg]                                   │
│ 单价: [   ]                                                 │
├──────────────────────────────────────────────────────────────┤
│ 【搭配品】（可选）← 灰色可折叠                               │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ [+ 添加搭配品]                                           ││
│ │ 产品      数量    单位    单价    仓库                    ││
│ │ [甜虾]   [10]   [箱]   [120]   [ZB-DOMESTIC]           ││
│ │ [北极贝]  [5]    [箱]   [200]   [ZB-DOMESTIC]           ││
│ └─────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│ 【辅料】（可选）← 灰色可折叠                                   │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ [+ 添加辅料]                                             ││
│ │ [真空袋] [500] [个] [0.5] [FL-MATERIAL]                 ││
│ └─────────────────────────────────────────────────────────┘│
├──────────────────────────────────────────────────────────────┤
│ 主产品金额: ¥4,275                                           │
│ 搭配品金额: ¥2,200                                           │
│ 合计: ¥6,475                                                 │
│ [取消]                              [确认创建]               │
└──────────────────────────────────────────────────────────────┘
```

---

## 五、与现有系统集成

### 5.1 仓库自动匹配

```javascript
const warehouseMap = {
  // 三文鱼主产品
  'import_whole_fish': 'ZB-IMPORT',      // 进口整包仓
  'domestic_whole_fish': 'ZB-DOMESTIC',  // 国内整包仓
  
  // 搭配品（整包阶段与三文鱼同仓）
  'shrimp_whole': 'ZB-DOMESTIC',         // 甜虾整包
  'scallop_whole': 'ZB-DOMESTIC',        // 北极贝整包
  
  // 辅料
  'packaging': 'FL-MATERIAL',            // 辅料仓
  'accessory': 'FL-MATERIAL',            // 辅料仓
};
```

### 5.2 产品选择过滤

| 采购类型 | 产品分类过滤 | 说明 |
|----------|-------------|------|
| 三文鱼进口整鱼 | category = 'whole_fish' + 系列=进口 | 进口三文鱼规格 |
| 三文鱼国内整鱼 | category = 'whole_fish' + 系列=国内 | 国内三文鱼规格 |
| 三文鱼分切成品 | category = 'finished_product' + 系列=三文鱼 | 分切后的三文鱼成品 |
| 甜虾整包 | category = 'whole_fish' + 名称含"甜虾" | 甜虾整包 |
| 甜虾分包 | category = 'finished_product' + 名称含"甜虾" | 分包后的甜虾 |
| 北极贝整包 | category = 'whole_fish' + 名称含"北极贝" | 北极贝整包 |
| 北极贝分包 | category = 'finished_product' + 名称含"北极贝" | 分包后的北极贝 |
| 包装物/辅料 | category = 'packaging' / 'accessory' | 包材/消耗品 |

### 5.3 入库后自动联动

```
采购单入库确认
  ├── 按 item_type 分流：
  │   ├── main（三文鱼）→ ZB-IMPORT/ZB-DOMESTIC
  │   ├── accessory（甜虾/北极贝）→ ZB-DOMESTIC（与三文鱼同仓）
  │   └── material（辅料）→ FL-MATERIAL
  ├── 创建 stock_inbounds 记录
  ├── 更新库存（stocks.current_qty +）
  ├── 更新采购单状态
  │   ├── received_qty == qty → status = 'completed'
  │   ├── received_qty < qty  → status = 'partial'
  └── 创建库存变动记录（stock_movements）
```

### 5.4 调拨分包（搭配品特殊流程）

```
甜虾/北极贝整包入库后
  └── 需要分包时：
      ├── 创建调拨单: ZB-DOMESTIC → FB-SHRIMP
      ├── 转换: 1箱 → N板（如 20板）
      ├── 扣减整包仓库存
      └── 增加分包仓库存（单位=板/只）
```

---

## 六、开发优先级

### 阶段1：核心功能（1-2天）
- [ ] 采购单 DB 表 + 迁移
- [ ] 采购单 CRUD API（支持主产品+搭配品）
- [ ] 前端页面：列表 + 新建弹窗 + 详情
- [ ] 一键入库（按产品类型分流）

### 阶段2：增强功能（1天）
- [ ] 供应商供货历史查询
- [ ] 采购价格趋势分析
- [ ] 库存预警（基于采购未到货数量）
- [ ] 打印采购单

### 阶段3：高级功能（可选）
- [ ] 采购审批流程
- [ ] 多批次分批入库
- [ ] 采购退货（红冲）
- [ ] 拼盘配方管理（甜虾+北极贝+三文鱼组合）

---

## 七、用户操作流程

### 场景1：采购三文鱼（主产品）

1. 进入【采购管理】页面
2. 点击【新建采购单】
3. **主产品区域**（默认展开，蓝色高亮）：
   - 类型 = "国内整鱼"
   - 仓库 = ZB-DOMESTIC（自动匹配）
   - 产品 = 7-8kg三文鱼整鱼
   - 数量 = 50箱，单价 = ¥85.5
4. 如需搭配品，展开【搭配品】区域添加甜虾/北极贝
5. 如需辅料，展开【辅料】区域添加包材
6. 保存采购单
7. 到货后，点击【入库】→ 自动分流入库

### 场景2：仅采购搭配品/辅料

1. 进入【采购管理】页面
2. 点击【新建采购单】
3. 主产品区域留空（或标记为"无"）
4. 在【搭配品】区域添加甜虾/北极贝
5. 在【辅料】区域添加包材
6. 保存并入库

### 场景3：调拨分包（甜虾/北极贝）

1. 甜虾/北极贝整包已入库到 ZB-DOMESTIC
2. 进入【仓库管理V2】→ 创建调拨单
3. 从 ZB-DOMESTIC 调拨到 FB-SHRIMP
4. 填写转换比例：1箱 = 20板
5. 确认调拨后，分包仓按板管理

---

## 八、相关文件位置

| 文件 | 说明 |
|------|------|
| `docs/warehouse-module-design-v2.md` | 仓库模块V2设计（已参考） |
| `backend/app/api/v1/endpoints/warehouse_v2.py` | 入库API |
| `frontend/src/pages/MaterialManagementPage.tsx` | 现有物料管理（参考） |
| `backend/migrations/versions/` | Alembic 迁移文件 |

---

**下一步**: 用户确认方案后，开始阶段1开发。
