# 进口单证模块设计方案

## 一、数据库设计

### 1.1 import_invoices（进口发票主表）

| 字段 | 类型 | 说明 | 状态 |
|------|------|------|------|
| id | Integer PK | 自增ID | ✅ |
| invoice_no | String(50) | 发票编号（唯一） | ✅ |
| invoice_date | Date | 发票日期 | ✅ |
| kill_date | Date | 宰杀日期 | ✅ |
| arrival_date | Date | 到货日期 | ✅ |
| processing_plant_id | Integer FK | 加工厂ID | ✅ |
| fish_farm_id | Integer FK | 渔场ID | ✅ |
| exporter_id | Integer FK | 出口商ID | ✅ |
| total_amount_usd | Numeric(15,2) | 总金额(USD) | ✅ |
| total_boxes | Integer | 总箱数 | ✅ |
| total_weight_kg | Numeric(12,3) | 总净重(kg) | ✅ |
| awb_no | String(50) | AWB航空运单号 | ✅ |
| gross_weight_kg | Numeric(12,3) | 毛重(kg) | ✅ |
| eta | DateTime | 预计到达时间 | ✅ |
| departure_date | Date | 发运时间 | ✅ |
| flight_info | String(100) | 航班信息 | ✅ |
| origin_certificate | String(100) | 原产地证书编号 | ✅ |
| inspection_certificate | String(100) | 检验检疫证书编号 | ✅ |
| customs_status | Enum | 报关状态(6种) | ✅ |
| exchange_status | Enum | 购汇状态(3种) | ✅ |
| is_locked | Boolean | 是否锁定（批次结算后） | ✅ |
| notes | Text | 备注 | ✅ |
| created_at | DateTime | 创建时间 | ✅ |
| updated_at | DateTime | 更新时间 | ✅ |

**报关状态(customs_status)**:
- `pending_shipment` — 未报关
- `in_transit` — 运输中
- `pending_customs` — 待报关
- `customs_processing` — 报关中
- `cleared` — 已清关
- `picked_up` — 已提货

**购汇状态(exchange_status)**:
- `not_exchanged` — 未购汇
- `partial` — 部分购汇
- `completed` — 全部购汇

### 1.2 invoice_products（发票产品明细表）

| 字段 | 类型 | 说明 | 状态 |
|------|------|------|------|
| id | Integer PK | 自增ID | ✅ |
| invoice_id | Integer FK | 关联发票ID | ✅ |
| product_name | String(100) | 产品名称 | ✅ |
| product_spec | String(100) | 规格 | ✅ |
| box_count | Integer | 箱数 | ✅ |
| net_weight_kg | Numeric(12,3) | 净重(kg) | ✅ |
| unit_price | Numeric(12,4) | 单价(USD) | ✅ |
| total_amount | Numeric(15,2) | 金额(USD) | ✅ |
| notes | Text | 备注 | ✅ |
| created_at | DateTime | 创建时间 | ✅ |
| updated_at | DateTime | 更新时间 | ✅ |

**产品名称枚举**: `三文鱼`, `虹鳟鱼`, `大西洋鲑`

**规格枚举**: `3-4kg`, `4-5kg`, `5-6kg`, `6-7kg`, `7-8kg`, `8-9kg`, `9-10kg`, `10kg+`

### 1.3 product_specs（产品规格配置表）

| 字段 | 类型 | 说明 | 状态 |
|------|------|------|------|
| id | Integer PK | 自增ID | ✅ |
| product_name | String(100) | 产品名称 | ✅ |
| spec_range | String(50) | 规格范围 | ✅ |
| full_spec | String(150) | 完整规格显示 | ✅ |
| is_active | Boolean | 是否启用 | ✅ |
| created_at | DateTime | 创建时间 | ✅ |
| updated_at | DateTime | 更新时间 | ✅ |

---

## 二、API 设计

### 2.1 发票管理

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| GET | `/api/v1/invoices/` | 发票列表（支持筛选/分页） | ✅ |
| GET | `/api/v1/invoices/summary` | 汇总统计 | ✅ |
| POST | `/api/v1/invoices/` | 创建发票（含产品明细） | ✅ |
| GET | `/api/v1/invoices/{id}` | 发票详情 | ✅ |
| PUT | `/api/v1/invoices/{id}` | 更新发票 | ✅ |
| DELETE | `/api/v1/invoices/{id}` | 删除发票 | ✅ |

**列表筛选参数**:
- `customs_status` — 报关状态筛选
- `exchange_status` — 购汇状态筛选
- `search` — 搜索发票号
- `skip/limit` — 分页

### 2.2 产品明细管理

| 方法 | 路径 | 说明 | 状态 |
|------|------|------|------|
| POST | `/api/v1/invoices/{id}/products` | 添加产品明细 | ✅ |
| PUT | `/api/v1/invoices/{id}/products/{pid}` | 更新产品明细 | ✅ |
| DELETE | `/api/v1/invoices/{id}/products/{pid}` | 删除产品明细 | ✅ |

---

## 三、前端页面设计

### 3.1 列表页 (`/invoices`)

**页面结构**:
```
┌─────────────────────────────────────────┐
│ 进口单证                    [新增发票]   │
├─────────────────────────────────────────┤
│ [搜索框] [报关状态▼] [购汇状态▼]        │
├─────────────────────────────────────────┤
│ 发票号 | 日期 | 宰杀 | ETA | 加工厂 | 出口商 │
│ 规格(箱数) | 总箱数 | 总净重 | 总金额 | AWB │
│ 报关状态 | 购汇状态 | 操作               │
├─────────────────────────────────────────┤
│ 共 X 张发票 | 总金额: $XXX               │
└─────────────────────────────────────────┘
```

**功能**:
- ✅ 汇总统计卡片（总发票数/总金额/本月新增/待购汇）
- ✅ 搜索（发票号）
- ✅ 双状态筛选（报关状态 + 购汇状态）
- ✅ 分页
- ✅ 编辑/删除操作

**规格显示格式**: `产品名称 规格(箱数)`，如 `三文鱼 6-7kg(10)`

### 3.2 新增/编辑弹窗

**弹窗尺寸**: 1000px宽，95vw，90vh高，可滚动

**表单分区**:

**基本信息** (3列布局):
- 发票编号 *
- 发票日期 *
- 宰杀日期
- 加工厂 *
- 渔场 *
- 出口商 *

**物流与证书信息** (3列布局):
- AWB航空运单号
- 毛重(kg)
- ETA预计到达
- 发运时间
- 航班信息
- 原产地证书
- 检验检疫证书

**产品明细** (表格形式):
| 产品 | 规格 | 箱数 | 重量(kg) | 单价(USD) | 金额(USD) | 操作 |

- 产品名称下拉（三文鱼/虹鳟鱼/大西洋鲑）
- 规格下拉（3-4kg到10kg+）
- 金额自动计算（箱数 × 单价）
- 底部汇总行（总箱数/总重量/总金额）

**备注**: 多行文本框

---

## 四、已实现功能清单

### 4.1 后端 ✅

- [x] 数据库模型（import_invoices + invoice_products + product_specs）
- [x] Pydantic Schema（创建/更新/响应）
- [x] CRUD Service（发票+产品明细）
- [x] API 端点（列表/详情/创建/更新/删除）
- [x] 汇总统计
- [x] 双状态筛选（报关+购汇）
- [x] 产品名称字段
- [x] 规格独立（产品名称+规格分开）

### 4.2 前端 ✅

- [x] 列表页（表格+搜索+筛选+分页）
- [x] 汇总统计卡片
- [x] 新增/编辑弹窗（1000px宽）
- [x] 基本信息表单（3列布局）
- [x] 物流信息表单（3列布局）
- [x] 产品明细表格（产品+规格分开）
- [x] 金额自动计算
- [x] 汇总行（总箱数/总重量/总金额）
- [x] ETA列显示
- [x] 规格显示格式（产品 规格(箱数)）

---

## 五、待实现功能（按优先级）

### 5.1 高优先级

- [ ] **公司选择器**: 加工厂/渔场/出口商用下拉选择（当前是ID输入框）
- [ ] **数据验证**: 表单提交前的完整验证
- [ ] **批量导入**: Excel批量导入发票
- [ ] **发票详情页**: 点击行查看完整详情（抽屉或新页面）

### 5.2 中优先级

- [ ] **附件上传**: 单证附件上传（发票/装箱单/原产地证等）
- [ ] **批次关联**: 发票关联到批次
- [ ] **购汇记录**: 发票下记录购汇明细
- [ ] **操作日志**: 发票变更记录

### 5.3 低优先级

- [ ] **打印功能**: 发票打印模板
- [ ] **导出功能**: Excel/PDF导出
- [ ] **智能提醒**: 待报关/待购汇提醒

---

## 六、当前项目文件

```
backend/
  app/models/__init__.py          — 数据库模型
  app/schemas/invoice.py            — Pydantic Schema
  app/services/invoice_service.py   — 业务逻辑
  app/api/v1/endpoints/invoices.py  — API端点

frontend/
  src/pages/InvoicesPage.tsx        — 列表页
  src/components/InvoiceFormDialog.tsx — 新增/编辑弹窗
```

---

## 七、测试数据

已创建测试发票:
- 发票号: 8407
- 日期: 2026-04-28
- 产品1: 三文鱼 6-7kg × 10箱
- 产品2: 虹鳟鱼 4-5kg × 5箱
- 报关状态: 运输中
- 购汇状态: 部分购汇

---

**整理完成。当前进口单证模块基础功能已实现，可按优先级继续开发待实现功能。**
