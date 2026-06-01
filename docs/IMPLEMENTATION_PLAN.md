# 成品定义 V2 实施方案

> 日期：2026-05-26
> 方案版本：v2.0
> 状态：Step 1-4 已完成，Step 5 待开发

---

## 一、现状盘点

### 1.1 后端状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 数据库表 | ✅ 已创建 | `product_series`(5条), `product_specs`(2条), `variant_price_tiers`(0条) |
| Alembic 迁移 | ✅ 已跑 | head: `20260525_2352_f1a2b3c4d5e6` |
| 模型定义 | ✅ 完成 | `finished_products.py` 四层模型 + 关系 |
| API 端点 | ✅ 完成 | 系列/规格/价格层级 CRUD 全部可用 |
| 数据填充 | ⚠️ 部分 | 5个系列✓、2规格✓、2模板✓、2变体✓、**0价格层级** |
| Pydantic Schema | ✅ 修复 | `sort_order` NULL 问题已解决（`Optional[int]`） |

### 1.2 前端状态

| 模块 | 状态 | 说明 |
|---|---|---|
| 现有页面 | ✅ 可用 | `FinishedProductsPage.tsx`（旧成品管理，未使用新API） |
| 新页面 | ✅ 已开发 | 系列管理、SPU-规格管理、SKU价格层级（骨架+API接入） |
| API 调用 | ✅ 已接入 | `ProductSeriesPage` / `ProductTemplatePage` / `SkuPricingPage` |
| 路由 | ✅ 已配置 | `/product-series`, `/product-templates`, `/sku-pricing` |

### 1.3 数据现状

```
ProductSeries:     5 条 (CX/PP/JS/TG/FB)
ProductTemplate:   2 条 (全部已关联系列)
ProductSpec:       2 条 (TP-001/TP-002)
ProductVariant:    2 条 (全部已关联spec)
VariantPriceTier:  0 条 ⚠️
```

---

## 二、实施目标

### 2.1 第一阶段：管理后台（MVP，2-3天）✅ 已完成

让运营人员能在前端维护：
1. 产品系列（增删改查） ✅
2. SPU → 规格 树形管理（同一SPU下增删改规格） ✅
3. SKU 价格层级配置（为每个SKU设置客户分级价/渠道价） ✅

### 2.2 第二阶段：业务打通（1-2天）⏳ 待开发

1. 销售下单时按「客户等级 + 购买数量」自动匹配价格
2. 现有成品销售页面适配新规格字段（显示规格名称替代旧 `spec` 字符串）

### 2.3 第三阶段：数据补全（并行）

1. 为现有 SKU 批量创建价格层级（至少一套默认价）
2. 清洗旧模板数据，补充 `parts_config` JSON

---

## 三、详细实施步骤

### Step 1: 前端路由与菜单（0.5天）✅ 已完成

**文件**: `frontend/src/routes.tsx`, `Sidebar.tsx`

**动作**:
- 新增路由：`/product-series`, `/product-templates`, `/sku-pricing`
- 新增菜单组「产品定义」含：系列管理、SPU与规格、SKU价格配置

**验收**: 菜单可点，路由可进，页面骨架能显示。

### Step 2: 系列管理页面（0.5天）✅ 已完成（API已接入）

**文件**: `frontend/src/pages/ProductSeriesPage.tsx`

**功能**: ✅ 表格展示 + 搜索 + CRUD弹窗
**API接入**: ✅
- `GET  /api/v1/finished-products/series` — 列表
- `POST /api/v1/finished-products/series` — 创建
- `POST /api/v1/finished-products/series/{id}` — 更新
- `DELETE /api/v1/finished-products/series/{id}` — 删除

**复用**: 套用 `InvoicesPage.tsx` 布局模式。

### Step 3: SPU-规格管理页面（1天）✅ 已完成（API已接入）

**文件**: `frontend/src/pages/ProductTemplatePage.tsx`

**设计**: 左侧 SPU 列表 + 右侧规格列表（左右分栏）

**API接入**: ✅
- `GET /api/v1/finished-products/templates` — SPU 列表
- `GET /api/v1/finished-products/templates/{id}/specs` — 规格列表
- `POST /api/v1/finished-products/templates/{id}/specs` — 创建规格

**验收**: 选中 SPU → 显示规格 → 能新建规格（含 `parts_config` JSON 输入）。

### Step 4: SKU 价格层级配置页面（0.5-1天）✅ 已完成（API已接入）

**文件**: `frontend/src/pages/SkuPricingPage.tsx`

**设计**: 搜索 SKU → 展开显示价格层级 → 添加价格

**后端补充**: ✅ 新增 `GET /api/v1/finished-products/variants` 端点（全量 SKU 列表，含 `spec_name`/`brand_name`）

**API接入**: ✅
- `GET /api/v1/finished-products/variants` — 全量 SKU（含品牌/规格名）
- `GET /api/v1/finished-products/variants/{id}/price-tiers` — 价格层级
- `POST /api/v1/finished-products/variants/{id}/price-tiers` — 创建价格

### Step 5: 销售页面适配（0.5天）⏳ 待开发

**文件**: `frontend/src/pages/FinishedProductSales.tsx`

**修改点**:
1. 产品选择器：以前是选 SKU，现在要能看到 **系列 → SPU → 规格** 的树形选择
2. 价格计算：根据客户等级 + 购买数量，调 `GET /api/v1/finished-products/variants/{id}/price-tiers` 匹配最优价格
3. 显示规格名称：从 `ProductSpec.name` 取，替代旧的 `spec` 字符串

**价格匹配逻辑**:
```typescript
function matchPriceTier(tiers: PriceTier[], customerLevel: string, qty: number): PriceTier | null {
  // 1. 按 customer_level 精确匹配
  const levelMatch = tiers.filter(t => t.tier_type === 'customer_level' && t.tier_key === customerLevel);
  if (levelMatch.length) return levelMatch[0];
  
  // 2. 按数量匹配阶梯价
  const volumeMatch = tiers
    .filter(t => t.tier_type === 'volume' && qty >= t.min_qty && (t.max_qty === null || qty <= t.max_qty))
    .sort((a, b) => b.min_qty - a.min_qty); // 取最大起订量的
  if (volumeMatch.length) return volumeMatch[0];
  
  // 3. fallback：普通价
  return tiers.find(t => t.tier_key === 'normal') || null;
}
```

---

## 四、后端变更记录

### 4.1 新增端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/finished-products/variants` | 全量 SKU 列表（含 brand_name / spec_name） |

### 4.2 Schema 更新

| 文件 | 变更 |
|---|---|
| `finished_products.py` | `ProductVariantResponse` 新增 `spec_id` / `spec_name` 字段 |
| `finished_products.py` | `list_variants`  endpoint 返回时填充 `spec_id` / `spec_name` |

---

## 五、文件清单

| 文件 | 状态 | 说明 |
|---|---|---|
| `routes.tsx` | ✅ | 新增 3 条路由 |
| `Sidebar.tsx` | ✅ | 新增「产品定义」菜单组 |
| `ProductSeriesPage.tsx` | ✅ | 系列管理，API 已接入 |
| `ProductTemplatePage.tsx` | ✅ | SPU+规格管理，API 已接入 |
| `SkuPricingPage.tsx` | ✅ | SKU价格配置，API 已接入 |
| `finished_products.py` | ✅ | 新增 `/variants` 端点 + schema 扩展 |

---

## 六、风险与预案

| 风险 | 概率 | 预案 |
|---|---|---|
| `parts_config` JSON 编辑体验差 | 中 | 先用简单 textarea 填 JSON，后续做可视化部位编辑器 |
| 旧页面改造范围大 | 中 | 分两阶段：第一阶段只做管理后台，第二阶段再改造销售页面 |
| 价格匹配逻辑复杂 | 低 | 先只支持「客户等级」一种匹配，阶梯价延后 |
| 数据迁移失败 | 低 | 保留旧字段，新字段 nullable，随时可回滚 |

---

## 七、验收标准

### 7.1 管理后台
- [x] 运营人员能在前端创建/编辑/删除产品系列
- [x] 运营人员能为 SPU 添加多个规格，每个规格能配置部位组合
- [x] 运营人员能为 SKU 设置至少一套价格层级

### 7.2 业务打通
- [ ] 销售下单选择产品时，能看到规格名称（不是旧 spec 字符串）
- [ ] 保存订单时，价格按客户等级自动匹配（不用手动输入单价）
- [ ] VIP 客户和普通客户购买同一 SKU，显示不同单价

### 7.3 稳定性
- [x] 现有成品销售页面不因改造而报错
- [x] 现有数据不因迁移而丢失

---

**下一步**: 继续 Step 5（销售页面适配）或先 commit 现有改动？
