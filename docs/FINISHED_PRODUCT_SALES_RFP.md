# 成品销售模块外包需求文档 (RFP)

> **项目**: salmon-pms 三文鱼项目管理系统  
> **版本**: V8.2  
> **文档版本**: v1.0  
> **日期**: 2026-05-03  
> **外包范围**: 成品产品管理 + 成品销售管理 + 成品库存联动 + 成品销售报表

---

## 一、项目背景

salmon-pms 是一个三文鱼全产业链项目管理系统，涵盖进口采购、批次管理、整鱼销售、成品加工销售、财务、报表等模块。

**现有技术栈**:
- **后端**: Python 3.12 + FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2 + Alembic
- **前端**: React 19 + TypeScript 5.4 + Vite 6 + TanStack Query + Zustand + shadcn/ui + Tailwind CSS
- **数据库**: SQLite(开发环境) / PostgreSQL 16(生产环境)
- **包管理**: uv (Python) / pnpm (Node)

**已有基础**:
- 成品产品管理：基础CRUD、BOM物料清单、包装物配置 ✅
- 成品销售：基础CRUD列表+表单 ✅
- 整鱼销售：完整功能（含收款、售后、批量导入、详情页）✅ — **作为成品销售的功能标杆**

**外包目标**: 在现有骨架基础上，完善成品产品管理和成品销售的完整业务闭环，使其达到与整鱼销售同等甚至更高的功能完整度。

---

## 二、外包模块范围

### 模块1: 成品产品管理增强 (Product Management)

在现有 `ProductsPage` 基础上扩展以下功能：

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 成品成本核算 | 基于BOM物料+包装物自动计算单品成本 | P0 |
| 成品价格策略 | 支持设置建议零售价、批发价、最低价 | P0 |
| 成品库存预警 | 设置安全库存线，低库存提醒 | P1 |
| 成品上下架 | 支持批量启停，停用后不可销售 | P1 |
| 成品分类标签 | 支持自定义标签（如热销、新品、清仓） | P2 |
| 成品图片管理 | 支持上传成品图片（使用现有文件存储） | P2 |
| 成品生产计划 | 关联生产批次，记录加工日期、保质期 | P2 |

**已有数据库表**: `products`, `product_boms`, `product_packagings`

---

### 模块2: 成品销售管理完善 (Finished Product Sales)

成品销售现有功能非常基础，需**对标整鱼销售 (`sales.py` + `SalesPage.tsx`)** 完善以下功能：

| 功能 | 说明 | 优先级 | 参考实现 |
|------|------|--------|----------|
| 销售详情页 | 点击行查看完整详情（抽屉/弹窗） | P0 | 整鱼销售详情页 |
| 收款记录管理 | 每笔销售可添加多笔收款，自动更新收款状态 | P0 | `/v1/sales/whole-fish/{id}/receipts` |
| 售后记录管理 | 退货/退款/折扣/补偿记录 | P0 | `/v1/sales/whole-fish/{id}/aftersales` |
| 客户信用额度校验 | 销售时检查客户是否超信用额度 | P0 | 参考 `companies.credit_limit` |
| 业务员提成联动 | 销售时自动计算业务员提成，关联提成记录表 | P1 | 参考 `CommissionRecord` |
| 批量导入 | Excel批量导入成品销售记录 | P1 | 参考 `sales.py` batch_import |
| 销售价格历史 | 记录每次销售的实际成交价，供定价参考 | P1 | 新增 |
| 销售订单状态机 | 待确认→已确认→已发货→已完成→已取消 | P2 | 新增 |
| 发货管理 | 关联物流，记录发货单号、物流公司、发货日期 | P2 | 新增 |
| 销售报价单 | 正式报价→客户确认→转销售单 | P2 | 新增 |

**已有数据库表**: `finished_product_sales`

**需新增/扩展表**:
- `finished_product_receipts` — 成品销售收款记录（参考 `sales_receipts`）
- `finished_product_aftersales` — 成品销售售后记录（参考 `aftersales_records`）
- `finished_product_sale_orders` — 销售订单（可选，支持订单状态）
- `finished_product_sale_shipments` — 发货记录（可选）

---

### 模块3: 成品库存联动 (Inventory Integration)

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 销售出库扣减 | 成品销售创建时自动扣减成品库存 | P0 |
| 库存实时查询 | 成品库存实时查询页面 | P0 |
| 库存变动记录 | 记录每次出入库的原因（销售、生产、调整） | P1 |
| 库存预警通知 | 库存低于安全线时触发通知 | P1 |

**已有数据库表**: `inventory`, `inventory_movements`

---

### 模块4: 成品销售报表 (Reports)

| 功能 | 说明 | 优先级 |
|------|------|--------|
| 销售日报/月报 | 按日期汇总销售额、销量、利润 | P0 |
| 客户销售分析 | 按客户统计销售额、回款率、欠款 | P1 |
| 产品销售分析 | 按成品统计销量、销售额、毛利 | P1 |
| 业务员业绩报表 | 按业务员统计销售额、提成 | P1 |
| 库存周转报表 | 成品库存周转率分析 | P2 |

---

## 三、接口规范（接入标准）

### 3.1 后端 API 规范

所有新接口必须遵循现有规范：

```
Base URL: /api/v1/
认证: Bearer Token (JWT)
Content-Type: application/json
```

**命名约定**:
- 成品产品管理: `/v1/products/...` （复用现有，扩展新端点）
- 成品销售: `/v1/finished-product-sales/...` （复用现有，扩展新端点）
- 成品收款: `/v1/finished-product-sales/{id}/receipts`
- 成品售后: `/v1/finished-product-sales/{id}/aftersales`

**响应格式**:
```json
{
  "total": 100,
  "items": [...],
  "skip": 0,
  "limit": 100
}
```

**错误格式**:
```json
{
  "detail": "错误描述"
}
```

### 3.2 前端页面规范

所有新页面必须遵循现有规范：

- **路由**: 在 `routes.tsx` 中注册
- **页面组件**: 放在 `src/pages/` 下，使用函数组件 + hooks
- **数据获取**: 使用 TanStack Query (`useQuery` / `useMutation`)
- **UI组件**: 使用 shadcn/ui + Tailwind CSS
- **API封装**: 使用 `src/lib/api.ts` 中的 axios 实例
- **状态提示**: 使用 `sonner` toast

**新页面清单**:
- `FinishedProductSalesPage.tsx` — 重写/增强现有页面
- `FinishedProductDetailDialog.tsx` — 销售详情（收款+售后标签页）
- `FinishedProductInventoryPage.tsx` — 成品库存查询
- `FinishedProductReportsPage.tsx` — 成品销售报表

---

## 四、数据模型要求

### 4.1 新增表（SQLAlchemy Model）

**必须遵循现有模型风格**:
- 继承 `Base` + `TimestampMixin`
- 使用 `Mapped` + `mapped_column`
- 使用 SQLAlchemy 2.0 风格
- Enum 使用 Python `Enum` + SQLAlchemy `Enum` 类型
- Decimal 使用 `Numeric(15, 2)` / `Numeric(12, 4)`

**示例**（成品销售收款记录）:
```python
class FinishedProductReceipt(Base, TimestampMixin):
    __tablename__ = "finished_product_receipts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("finished_product_sales.id"), nullable=False)
    receipt_date: Mapped[Date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50))
    bank_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"))
    reference_no: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)
```

### 4.2 Alembic 迁移

所有数据库变更必须通过 Alembic 迁移脚本管理：
```bash
cd backend
alembic revision --autogenerate -m "add finished product receipts and aftersales"
alembic upgrade head
```

---

## 五、代码质量标准

### 5.1 后端
- 使用 `ruff` 进行代码格式化
- 使用 `mypy` 进行类型检查
- Service 层封装业务逻辑，不直接在 API 层写 SQL
- 所有数据库操作使用 AsyncSession
- 异常处理使用 FastAPI HTTPException

### 5.2 前端
- TypeScript 严格模式，所有接口定义类型
- 组件使用函数式 + hooks
- 表单使用受控组件
- 加载状态必须处理（skeleton 或 loading 提示）
- 错误状态必须处理（toast 提示）

### 5.3 测试
- 后端: 使用 pytest + pytest-asyncio
- 至少覆盖核心 Service 方法的单元测试
- 至少覆盖关键 API 端点的集成测试

---

## 六、交付物清单

| 交付物 | 说明 | 格式 |
|--------|------|------|
| 源代码 | 完整前后端代码 | GitHub/GitLab PR |
| API文档 | 新增/修改的API接口文档 | Markdown / Swagger |
| 数据库迁移脚本 | Alembic migration 文件 | Python |
| 前端页面 | 新增/重写的 React 页面 | TypeScript TSX |
| 单元测试 | 后端 Service + API 测试 | pytest |
| 部署文档 | 如何部署到现有系统 | Markdown |
| 验收清单 | 功能验收测试步骤 | Markdown |

---

## 七、验收标准

### 7.1 功能验收

**成品产品管理**:
- [ ] 成品BOM成本自动计算正确
- [ ] 成品价格策略可配置（零售价/批发价/最低价）
- [ ] 成品库存预警可设置并触发
- [ ] 成品启停状态正确控制销售可用性

**成品销售管理**:
- [ ] 销售CRUD完整可用
- [ ] 销售详情页显示完整信息（含收款+售后标签页）
- [ ] 收款记录可增删，自动更新销售收款状态
- [ ] 售后记录可增删改
- [ ] 超信用额度客户销售时给出警告/阻止
- [ ] 业务员提成自动计算并关联提成表
- [ ] Excel批量导入功能正常
- [ ] 销售状态流转正确

**成品库存**:
- [ ] 销售创建时自动扣减库存
- [ ] 库存实时查询页面数据准确
- [ ] 库存变动记录完整

**报表**:
- [ ] 销售日报/月报表数据准确
- [ ] 客户/产品/业务员分析报表正常

### 7.2 技术验收
- [ ] 代码通过 `ruff` 格式化检查
- [ ] 代码通过 `mypy` 类型检查（无错误）
- [ ] 所有 Alembic 迁移可正常执行
- [ ] 单元测试通过率 100%
- [ ] 与现有系统其他模块无冲突
- [ ] 前端构建无错误 (`pnpm build`)

---

## 八、接入计划（我方负责）

外包团队完成开发后，由我方负责接入现有 salmon-pms 系统：

### 8.1 代码合并
- Review PR，确保代码风格与现有项目一致
- 解决合并冲突
- 运行完整测试套件

### 8.2 数据库迁移
- 在开发环境执行 Alembic 迁移
- 验证生产环境迁移脚本
- 备份生产数据库后执行迁移

### 8.3 集成测试
- 端到端测试：从成品创建 → 销售下单 → 收款 → 售后 → 报表
- 与现有模块联动测试（财务、库存、客户管理）

### 8.4 部署上线
- 更新 Docker 镜像
- 部署到生产环境
- 监控日志和错误

---

## 九、技术约束

### 9.1 不允许变更
- **技术栈不变**: 必须使用现有技术栈（FastAPI + React 19 + SQLAlchemy 2.0）
- **数据库结构**: 现有核心表结构（products, finished_product_sales, companies, users 等）不能破坏，只能扩展
- **认证体系**: 必须使用现有的 JWT Bearer Token 认证
- **UI框架**: 必须使用 shadcn/ui + Tailwind CSS

### 9.2 必须兼容
- 现有 `finished_product_sales` API 需保持向后兼容，或提供迁移方案
- 现有 `ProductsPage` 的成品定义Tab需保持兼容
- 现有数据库中的成品销售数据不能丢失

### 9.3 推荐做法
- 复用现有的 `SalesStatus` 枚举
- 复用现有的 `Company`（客户）、`Product`（成品）、`User`（业务员）模型
- 复用现有的 `BankAccount` 模型做收款关联
- 复用现有的 `api.ts` 做 HTTP 请求

---

## 十、参考代码

以下现有代码作为开发参考，外包团队必须熟悉：

**后端参考**:
- `backend/app/api/v1/endpoints/sales.py` — 整鱼销售完整API（含收款、售后）
- `backend/app/services/sales_service.py` — 整鱼销售Service
- `backend/app/schemas/sales.py` — 整鱼销售Schema
- `backend/app/models/__init__.py` — 数据模型定义

**前端参考**:
- `frontend/src/pages/SalesPage.tsx` — 整鱼销售页面（含详情弹窗）
- `frontend/src/pages/ProductsPage.tsx` — 产品管理页面
- `frontend/src/pages/FinishedProductSalesPage.tsx` — 现有成品销售页面（需重写增强）
- `frontend/src/lib/api.ts` — API 封装

**设计文档**:
- `docs/INVOICE_MODULE_DESIGN.md` — 设计文档模板

---

## 十一、联系方式与协作

- **代码仓库**: salmon-pms (GitHub/GitLab)
- **开发分支**: `feature/finished-product-sales-v2`
- **PR目标分支**: `main`
- **沟通方式**: GitHub Issues / PR Comments / 即时通讯
- **我方言责人**: 负责代码Review、测试、部署接入

---

**本需求文档为外包开发的唯一依据。开发过程中如有需求变更，须经双方确认后更新本文档。**
