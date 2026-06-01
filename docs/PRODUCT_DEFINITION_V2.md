# 成品定义 — 四层架构方案 v2

> 日期：2026-05-26
> 状态：后端 API 已跑通，前端页面待开发

---

## 一、为什么要重构

旧方案把**规格**和**SPU**揉在一起（`ProductTemplate.spec` 存字符串），导致：

| 问题 | 表现 |
|---|---|
| 同一产品不同规格 = 重复建模板 | 三文鱼刺身 200g / 400g 是两个模板 |
| 规格没结构化 | `"鱼腩200g+中段200g"` 是文本，无法拆部位算成本 |
| 价格体系混乱 | 品牌价/客户价/阶梯价全塞在 `variant` 里 |
| 系列靠硬编码 | `series_code` 是字符串，筛选排序困难 |

新方案拆成**四层 + 价格层**，让同一 SPU 下挂多规格、同一规格下挂多品牌 SKU、每个 SKU 下挂多价格层级。

---

## 二、四层架构总览

```
┌─────────────────────────────────────────────────────────────────────┐
│  系列层 (ProductSeries)                                              │
│  纯享装 │ 拼盘装 │ 即食装 │ 团购装 │ 副产品                         │
│  ← 营销分类、礼盒风格、场景定位                                        │
├─────────────────────────────────────────────────────────────────────┤
│  SPU层 (ProductTemplate)                                             │
│  三文鱼刺身 │ 海鲜拼盘 │ 鱼头套餐                                     │
│  ← 产品概念，不含规格/品牌/价格                                        │
├─────────────────────────────────────────────────────────────────────┤
│  规格层 (ProductSpec)                                                │
│  鱼腩200g+中段200g │ 中段400g │ 中段130g+甜虾15只                    │
│  ← 物理规格、部位组合、重量、盒数                                      │
├─────────────────────────────────────────────────────────────────────┤
│  SKU层 (ProductVariant × Brand)                                      │
│  鱼腩200g+中段200g × 味库=SKU-001                                    │
│  鱼腩200g+中段200g × 美威=SKU-002                                    │
│  ← 品牌、库存、成本价、专属包装                                        │
├─────────────────────────────────────────────────────────────────────┤
│  价格层 (VariantPriceTier)                                           │
│  大客户价 │ VIP价 │ 普通价 │ 阶梯价(100盒起)                        │
│  ← 客户分级/渠道/起量折扣，时间有效期                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、各层详解

### 3.1 系列层 — ProductSeries

| 字段 | 说明 |
|---|---|
| `code` | 编码：CX/PP/JS/TG/FB |
| `name` | 名称：纯享装/拼盘装/即食装/团购装/副产品 |
| `sort_order` | 排序权重 |
| `is_active` | 是否上架 |

**业务含义**：
- **纯享装(CX)**：高端零售，礼盒腰封，送礼场景
- **拼盘装(PP)**：组合搭配，聚会场景
- **即食装(JS)**：现切现发，即时消费
- **团购装(TG)**：大份量实惠，聚餐场景
- **副产品(FB)**：鱼头鱼骨，低价引流/赠品

### 3.2 SPU层 — ProductTemplate

| 字段 | 说明 |
|---|---|
| `code` | SPU编码 |
| `name` | SPU名称：三文鱼刺身 |
| `series_id` | 关联系列（新增） |
| `spec` | **废弃保留**，迁移到 `ProductSpec` |
| `unit` | 计量单位 |
| `unit_weight_kg` | 单盒重量 |
| `portion_weight_g` | 部位重量（旧字段保留） |
| `portion_boxes` | 部位盒数（旧字段保留） |

**核心变化**：
- `spec` 字段不再维护，仅保留兼容旧数据
- 通过 `series_id` 关联系列（替代旧 `series_code` 字符串）

### 3.3 规格层 — ProductSpec

| 字段 | 说明 |
|---|---|
| `template_id` | 所属 SPU |
| `code` | 规格编码：TP-001 |
| `name` | 规格名称：鱼腩200g+中段200g |
| `parts_config` | 部位配置 JSON：鱼腩/中段/甜虾/希鲮鱼籽 |
| `total_weight_g` | 总克重 |
| `portion_count` | 部位数 |
| `box_count` | 盒数 |
| `sort_order` | 排序 |

**典型规格示例**：

| SPU | 规格 | parts_config | weight | box |
|---|---|---|---|---|
| 三文鱼刺身 | 鱼腩200g+中段200g | `[{"part":"鱼腩","g":200},{"part":"中段","g":200}]` | 400g | 1 |
| 海鲜拼盘 | 中段130g+甜虾15只 | `[{"part":"中段","g":130},{"part":"甜虾","只":15}]` | — | 1 |

### 3.4 SKU层 — ProductVariant

| 字段 | 说明 |
|---|---|
| `template_id` | 所属 SPU |
| `spec_id` | **新增**：关联规格 |
| `brand_id` | 品牌 |
| `code` | SKU编码 |
| `cost_price` | 成本价 |
| `suggested_retail_price` | 建议零售价 |
| `wholesale_price` | 批发价 |
| `stock_quantity` | 库存 |

**核心变化**：新增 `spec_id` 字段，让同一规格 × 不同品牌 = 不同 SKU。

### 3.5 价格层 — VariantPriceTier

| 字段 | 说明 |
|---|---|
| `variant_id` | 所属 SKU |
| `tier_type` | 类型：customer_level / channel / volume |
| `tier_key` | 键：vip / wholesale / online / offline |
| `tier_name` | 名称：VIP价 / 大客户价 |
| `min_qty` | 起订量 |
| `max_qty` | 封顶量（nullable） |
| `price` | 单价 |
| `valid_from / valid_to` | 有效期 |

**价格类型示例**：

| tier_type | tier_key | tier_name | min_qty | price |
|---|---|---|---|---|
| customer_level | vip | VIP价 | 1 | ¥128 |
| customer_level | normal | 普通价 | 1 | ¥148 |
| channel | online | 线上价 | 1 | ¥138 |
| volume | bulk_100 | 100盒价 | 100 | ¥118 |
| volume | bulk_500 | 500盒价 | 500 | ¥98 |

---

## 四、API 端点

### 4.1 系列 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/finished-products/series` | 列表（分页） |
| POST | `/api/v1/finished-products/series` | 创建 |
| GET | `/api/v1/finished-products/series/{id}` | 详情 |
| PUT | `/api/v1/finished-products/series/{id}` | 更新 |
| DELETE | `/api/v1/finished-products/series/{id}` | 删除（仅当无关联模板） |

### 4.2 规格 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/finished-products/templates/{id}/specs` | 某 SPU 下全部规格 |
| POST | `/api/v1/finished-products/templates/{id}/specs` | 为 SPU 创建规格 |
| GET | `/api/v1/finished-products/templates/{id}/specs/{spec_id}` | 规格详情 |
| PUT | `/api/v1/finished-products/templates/{id}/specs/{spec_id}` | 更新规格 |
| DELETE | `/api/v1/finished-products/templates/{id}/specs/{spec_id}` | 删除（仅当无 SKU 关联） |

### 4.3 价格层级 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/finished-products/variants/{id}/price-tiers` | 某 SKU 下全部价格层级 |
| POST | `/api/v1/finished-products/variants/{id}/price-tiers` | 创建价格层级 |
| GET | `/api/v1/finished-products/variants/{id}/price-tiers/{tier_id}` | 详情 |
| PUT | `/api/v1/finished-products/variants/{id}/price-tiers/{tier_id}` | 更新 |
| DELETE | `/api/v1/finished-products/variants/{id}/price-tiers/{tier_id}` | 删除 |

---

## 五、向后兼容策略

| 措施 | 说明 |
|---|---|
| 保留 `template_id` | 现有 `ProductVariant` 继续可用，不强制迁移 |
| 保留 `series_code` / `series_name` | `ProductTemplate` 旧字段保留，逐步废弃 |
| 保留 `spec` 字符串字段 | 旧规格描述保留，新数据写入 `ProductSpec` |
| `spec_id` nullable | SKU 层新增字段可为空，旧数据不受影响 |
| 渐进式迁移 | 存量数据可分批洗入新表，不强制一次性迁移 |

---

## 六、前端待办

| 模块 | 状态 |
|---|---|
| 系列管理页面 | ❌ 未开发 |
| SPU → 规格管理（树形/卡片） | ❌ 未开发 |
| SKU 价格层级配置面板 | ❌ 未开发 |
| 订单下单时按客户等级自动匹配价格 | ❌ 未开发 |
| 现有页面适配新字段 | ✅ 后端兼容，前端无需改 |

---

## 七、文件清单

| 文件 | 作用 |
|---|---|
| `backend/app/models/finished_products.py` | 四层模型定义（ProductSeries / ProductSpec / VariantPriceTier + 改造 ProductTemplate / ProductVariant） |
| `backend/app/api/v1/endpoints/finished_products.py` | API 端点实现（~line 1020+ 为新增 CRUD） |
| `backend/app/models/finished_products_refactor.py` | 早期重构草稿（参考用） |
| 本文档 | 方案说明 |
