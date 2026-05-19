# 三文鱼PMS - 退货模块设计方案

## 一、需求分析

### 1.1 现有系统问题
- 售后记录仅有：`type`/`amount`/`reason`/`status`/`notes`，过于简单
- 无法记录退货重量、单价、加工厂来源
- 无图片/视频附件管理能力
- 退款处理与财务系统脱节，无法直接生成退款支出
- 成品销售和整鱼销售的售后数据分离，无法统一统计

### 1.2 业务需求
1. **退货数据登记**：退货原因、数量、重量、单价、金额
2. **加工厂追溯**：明确退货来自哪个加工厂
3. **多媒体附件**：问题图片、视频收集整理存放到本地
4. **财务联动**：退款通过支出给客户，或抵扣货款，或做预付款
5. **统一统计**：整鱼销售+成品销售的退货数据统一汇总
6. **退货审批流程**：创建 → 审批 → 执行退款 → 完成

---

## 二、数据模型设计

### 2.1 核心枚举

```python
class ReturnReason(str, PyEnum):
    """退货原因"""
    QUALITY_ISSUE = "quality_issue"           # 质量问题（变质/异味/色泽异常）
    LOGISTICS_DAMAGE = "logistics_damage"     # 物流损坏（包装破损/挤压）
    SPEC_MISMATCH = "spec_mismatch"           # 规格不符（大小/重量不达标）
    TEMPERATURE_ISSUE = "temperature_issue"   # 温控问题（解冻/温度不达标）
    FOREIGN_MATTER = "foreign_matter"         # 异物混入
    CUSTOMER_REASON = "customer_reason"       # 客户原因（订单错误/临时取消）
    EXPIRED = "expired"                       # 临期/过期
    OTHER = "other"                           # 其他

class ReturnStatus(str, PyEnum):
    """退货单状态"""
    DRAFT = "draft"                           # 草稿
    PENDING_APPROVAL = "pending_approval"     # 待审批
    APPROVED = "approved"                     # 已批准（待退款）
    REFUNDING = "refunding"                   # 退款中
    COMPLETED = "completed"                   # 已完成
    REJECTED = "rejected"                     # 已拒绝
    CANCELLED = "cancelled"                   # 已取消

class RefundMethod(str, PyEnum):
    """退款方式"""
    DIRECT_REFUND = "direct_refund"           # 直接退款（银行转账/扫码）
    BALANCE_DEDUCTION = "balance_deduction"   # 抵扣货款
    PREPAYMENT = "prepayment"                 # 转为预付款
    DEFERRED = "deferred"                     # 挂账/延期处理

class ReturnAttachmentType(str, PyEnum):
    """附件类型"""
    IMAGE = "image"                           # 图片
    VIDEO = "video"                           # 视频
    DOCUMENT = "document"                     # 文档
```

### 2.2 退货单模型 (ReturnOrder)

```python
class ReturnOrder(Base, TimestampMixin):
    """退货单（统一整鱼+成品销售退货）"""
    __tablename__ = "return_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    return_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)  # THYYYYMMDD-NNN
    
    # 关联销售单（二选一）
    sale_type: Mapped[str] = mapped_column(String(20), nullable=False)  # whole_fish / finished_product
    whole_fish_sale_id: Mapped[Optional[int]] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=True)
    finished_product_sale_id: Mapped[Optional[int]] = mapped_column(ForeignKey("finished_product_sales.id"), nullable=True)
    
    # 基本信息
    return_date: Mapped[Date] = mapped_column(Date, nullable=False)       # 退货日期
    customer_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)  # 客户
    
    # 加工厂追溯（冗余+自动计算）
    processing_plant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True)
    processing_plant_name: Mapped[Optional[str]] = mapped_column(String(200))  # 加工厂名称（冗余）
    
    # 退货汇总
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))   # 退货总重量(kg)
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)                            # 退货总数量（件/份/箱）
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))       # 退货总金额
    
    # 退款信息
    refund_method: Mapped[Optional[RefundMethod]] = mapped_column(Enum(RefundMethod), nullable=True)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))     # 实际退款金额（可能≠退货金额）
    refund_date: Mapped[Optional[Date]] = mapped_column(Date)                                 # 退款日期
    bank_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"))   # 退款银行账户
    transaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transaction_records.id"))  # 关联交易流水
    
    # 状态与审批
    status: Mapped[ReturnStatus] = mapped_column(Enum(ReturnStatus), default=ReturnStatus.DRAFT)
    
    # 问题描述
    problem_description: Mapped[Optional[str]] = mapped_column(Text)      # 售后问题描述
    customer_feedback: Mapped[Optional[str]] = mapped_column(Text)        # 客户反馈
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)           # 内部备注
    
    # 处理人
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)
    
    # 关联
    items: Mapped[List["ReturnItem"]] = relationship("ReturnItem", back_populates="return_order", cascade="all, delete-orphan")
    attachments: Mapped[List["ReturnAttachment"]] = relationship("ReturnAttachment", back_populates="return_order", cascade="all, delete-orphan")
```

### 2.3 退货明细模型 (ReturnItem)

```python
class ReturnItem(Base, TimestampMixin):
    """退货明细"""
    __tablename__ = "return_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    return_order_id: Mapped[int] = mapped_column(ForeignKey("return_orders.id"), nullable=False)
    
    # 产品信息
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"), nullable=True)  # 成品用
    product_name: Mapped[Optional[str]] = mapped_column(String(100))                              # 产品名称（冗余）
    spec: Mapped[Optional[str]] = mapped_column(String(100))                                       # 规格（整鱼用）
    
    # 退货数量
    quantity: Mapped[int] = mapped_column(Integer, default=0)           # 数量（件/份/箱）
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 重量(kg)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))  # 单价
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))     # 金额 = weight_kg * unit_price
    
    # 退货原因
    return_reason: Mapped[ReturnReason] = mapped_column(Enum(ReturnReason), nullable=False)
    reason_detail: Mapped[Optional[str]] = mapped_column(Text)          # 原因详细说明
    
    # 关联原销售子项
    whole_fish_sale_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("whole_fish_sale_items.id"), nullable=True)
    finished_product_sale_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("finished_product_sale_items.id"), nullable=True)
    
    return_order: Mapped["ReturnOrder"] = relationship("ReturnOrder", back_populates="items")
```

### 2.4 退货附件模型 (ReturnAttachment)

```python
class ReturnAttachment(Base, TimestampMixin):
    """退货附件（图片/视频/文档）"""
    __tablename__ = "return_attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    return_order_id: Mapped[int] = mapped_column(ForeignKey("return_orders.id"), nullable=False)
    
    file_type: Mapped[ReturnAttachmentType] = mapped_column(Enum(ReturnAttachmentType), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)    # 原始文件名
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)        # 存储文件名（UUID）
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)        # 相对存储路径
    file_size: Mapped[int] = mapped_column(Integer, default=0)                 # 文件大小(字节)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))              # MIME类型
    description: Mapped[Optional[str]] = mapped_column(Text)                   # 文件描述
    
    return_order: Mapped["ReturnOrder"] = relationship("ReturnOrder", back_populates="attachments")
```

### 2.5 加工厂追溯逻辑

```
整鱼销售退货:
  whole_fish_sale_id → batch_id → batch_invoices → invoice → processing_plant_id
  
成品销售退货:
  finished_product_sale_id → slaughter_record / source_sale_id → batch_id → processing_plant_id
  或 material_traceability → source_invoice_id → processing_plant_id
```

---

## 三、API接口设计

### 3.1 退货单管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/returns` | 退货单列表（支持筛选：客户、日期范围、状态、加工厂、退货原因） |
| POST | `/returns` | 创建退货单 |
| GET | `/returns/{id}` | 退货单详情（含明细+附件） |
| PUT | `/returns/{id}` | 更新退货单（草稿/待审批状态可修改） |
| DELETE | `/returns/{id}` | 删除退货单（仅草稿） |
| POST | `/returns/{id}/submit` | 提交审批 |
| POST | `/returns/{id}/approve` | 审批通过 |
| POST | `/returns/{id}/reject` | 审批拒绝 |
| POST | `/returns/{id}/refund` | 执行退款（生成交易流水） |
| POST | `/returns/{id}/cancel` | 取消退货单 |

### 3.2 退货明细

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/returns/{id}/items` | 添加退货明细 |
| PUT | `/returns/{id}/items/{item_id}` | 更新明细 |
| DELETE | `/returns/{id}/items/{item_id}` | 删除明细 |

### 3.3 附件管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/returns/{id}/attachments` | 上传附件（multipart/form-data） |
| GET | `/returns/{id}/attachments` | 附件列表 |
| GET | `/returns/attachments/{file_name}` | 下载附件 |
| DELETE | `/returns/{id}/attachments/{attach_id}` | 删除附件 |

### 3.4 统计报表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/returns/stats/summary` | 退货汇总（金额/重量/数量） |
| GET | `/returns/stats/by-reason` | 按退货原因统计 |
| GET | `/returns/stats/by-plant` | 按加工厂统计 |
| GET | `/returns/stats/by-customer` | 按客户统计 |
| GET | `/returns/stats/by-product` | 按产品统计 |
| GET | `/returns/stats/trend` | 退货趋势（按日/周/月） |

---

## 四、业务流程设计

### 4.1 退货单生命周期

```
草稿(DRAFT) → 提交审批 → 待审批(PENDING_APPROVAL) → 审批通过 → 已批准(APPROVED)
                                                    → 审批拒绝 → 已拒绝(REJECTED)
                                                                         ↓
已批准(APPROVED) → 执行退款 → 退款中(REFUNDING) → 完成 → 已完成(COMPLETED)
                                                          → 挂账 → 已批准(保持)
```

### 4.2 退款处理流程

```
1. 用户选择退款方式：
   - 直接退款 → 选择银行账户 → 生成支出交易流水 → 更新退货单状态为"已完成"
   - 抵扣货款 → 更新客户余额（减少应收）→ 生成余额抵扣流水 → 更新状态
   - 转为预付款 → 增加客户预付余额 → 生成预付款流水 → 更新状态
   - 挂账 → 仅记录，不生成流水，状态保持"已批准"

2. 自动更新关联销售单：
   - 累加销售单的 after_sales_adjustment 字段
   - 重新计算销售单净金额和收款状态
   - 如整单退货，销售单状态变为"售后中"
```

### 4.3 加工厂自动识别

```
创建退货单时：
  IF sale_type == "whole_fish":
    processing_plant_id = sale.batch.invoices[0].processing_plant_id
  IF sale_type == "finished_product":
    # 优先从追溯链获取
    trace = material_traceability.where(finished_product_sale_id = sale.id)
    IF trace exists:
      processing_plant_id = trace.source_invoice.processing_plant_id
    ELSE:
      # 从宰杀记录获取
      slaughter = daily_slaughter.where(source_sale_id = sale.source_sale_id)
      IF slaughter exists:
        processing_plant_id = slaughter.source_invoice.processing_plant_id
```

---

## 五、文件存储设计

### 5.1 目录结构

```
workspace-codeingman/projects/salmon-pms/
├── backend/
│   └── uploads/
│       └── returns/
│           └── YYYYMM/
│               └── {uuid}.{ext}          # 实际存储文件
```

### 5.2 文件命名规则

- 存储文件名：`{return_order_id}_{uuid8}.{ext}`
- 例如：`42_a1b2c3d4.jpg`

### 5.3 文件访问

- 通过 `/uploads/returns/YYYYMM/{file_name}` 提供静态文件服务
- 生产环境建议配置nginx直接服务静态文件

---

## 六、前端页面设计

### 6.1 新增页面

1. **退货管理页面** (`ReturnsPage.tsx`)
   - 退货单列表（表格）
   - 筛选：日期范围、客户、加工厂、状态、退货原因
   - 操作：查看详情、编辑、提交审批、执行退款
   - 统计卡片：本月退货金额、退货率、TOP退货原因

2. **退货单详情弹窗/页面**
   - 基本信息（退货单号、客户、加工厂、状态）
   - 退货明细表格（规格、数量、重量、单价、金额、退货原因）
   - 附件画廊（图片缩略图+视频播放）
   - 审批记录
   - 退款信息

3. **创建/编辑退货单弹窗**
   - 选择原销售单（整鱼/成品）
   - 自动加载销售单明细
   - 填写退货数量和重量
   - 选择退货原因
   - 上传图片/视频
   - 填写问题描述

### 6.2 集成到现有页面

1. **SalesPage.tsx**（整鱼销售）
   - 销售单行增加"退货"按钮
   - 销售单详情增加"退货记录"标签页
   
2. **FinishedProductSalesPage.tsx**（成品销售）
   - 销售单行增加"退货"按钮
   - 销售单详情增加"退货记录"标签页

---

## 七、数据库迁移计划

### 7.1 新表

```sql
-- 退货单
CREATE TABLE return_orders (
    id SERIAL PRIMARY KEY,
    return_no VARCHAR(30) UNIQUE NOT NULL,
    sale_type VARCHAR(20) NOT NULL,  -- whole_fish / finished_product
    whole_fish_sale_id INTEGER REFERENCES whole_fish_sales(id),
    finished_product_sale_id INTEGER REFERENCES finished_product_sales(id),
    return_date DATE NOT NULL,
    customer_id INTEGER NOT NULL REFERENCES companies(id),
    processing_plant_id INTEGER REFERENCES companies(id),
    processing_plant_name VARCHAR(200),
    total_weight_kg NUMERIC(12,3) DEFAULT 0,
    total_quantity INTEGER DEFAULT 0,
    total_amount NUMERIC(15,2) DEFAULT 0,
    refund_method VARCHAR(20),
    refund_amount NUMERIC(15,2) DEFAULT 0,
    refund_date DATE,
    bank_account_id INTEGER REFERENCES bank_accounts(id),
    transaction_id INTEGER REFERENCES transaction_records(id),
    status VARCHAR(20) DEFAULT 'draft',
    problem_description TEXT,
    customer_feedback TEXT,
    internal_notes TEXT,
    created_by_id INTEGER REFERENCES users(id),
    approved_by_id INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 退货明细
CREATE TABLE return_items (
    id SERIAL PRIMARY KEY,
    return_order_id INTEGER NOT NULL REFERENCES return_orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),
    product_name VARCHAR(100),
    spec VARCHAR(100),
    quantity INTEGER DEFAULT 0,
    weight_kg NUMERIC(12,3) DEFAULT 0,
    unit_price NUMERIC(12,4) DEFAULT 0,
    amount NUMERIC(15,2) DEFAULT 0,
    return_reason VARCHAR(30) NOT NULL,
    reason_detail TEXT,
    whole_fish_sale_item_id INTEGER REFERENCES whole_fish_sale_items(id),
    finished_product_sale_item_id INTEGER REFERENCES finished_product_sale_items(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 退货附件
CREATE TABLE return_attachments (
    id SERIAL PRIMARY KEY,
    return_order_id INTEGER NOT NULL REFERENCES return_orders(id) ON DELETE CASCADE,
    file_type VARCHAR(20) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER DEFAULT 0,
    mime_type VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 7.2 索引

```sql
CREATE INDEX idx_return_orders_sale_type ON return_orders(sale_type);
CREATE INDEX idx_return_orders_whole_fish_sale_id ON return_orders(whole_fish_sale_id);
CREATE INDEX idx_return_orders_finished_product_sale_id ON return_orders(finished_product_sale_id);
CREATE INDEX idx_return_orders_customer_id ON return_orders(customer_id);
CREATE INDEX idx_return_orders_processing_plant_id ON return_orders(processing_plant_id);
CREATE INDEX idx_return_orders_status ON return_orders(status);
CREATE INDEX idx_return_orders_return_date ON return_orders(return_date);
CREATE INDEX idx_return_items_return_order_id ON return_items(return_order_id);
CREATE INDEX idx_return_items_return_reason ON return_items(return_reason);
CREATE INDEX idx_return_attachments_return_order_id ON return_attachments(return_order_id);
```

---

## 八、与现有系统的兼容方案

### 8.1 向后兼容

1. 保留现有的 `AftersalesRecord` 和 `FinishedProductAftersales` 表和数据
2. 新退货模块通过独立表实现，不影响现有功能
3. 销售单列表中，售后金额 = 现有 after_sales_adjustment + 关联退货单总金额

### 8.2 数据迁移（可选）

- 如有需要将历史售后记录迁移到新的退货单，可编写一次性迁移脚本
- 迁移后保留原表作为历史备份

### 8.3 销售单状态联动

```python
# 创建/更新退货单时，自动更新销售单
def sync_sale_after_sales_adjustment(sale, return_order):
    # 计算该销售单所有关联退货单的总金额
    total_return_amount = sum(r.total_amount for r in sale.return_orders if r.status == ReturnStatus.COMPLETED)
    
    # 更新销售单售后调整
    sale.after_sales_adjustment = total_return_amount
    
    # 重新计算净金额
    sale.net_amount = sale.gross_amount - sale.scan_fee - sale.rounding_adjustment - sale.after_sales_adjustment - sale.discount - sale.commission
    
    # 更新收款状态
    if sale.paid_amount >= sale.net_amount:
        sale.status = SalesStatus.FULLY_PAID
    elif sale.paid_amount > 0:
        sale.status = SalesStatus.PARTIAL_PAID
    else:
        sale.status = SalesStatus.PENDING
    
    # 如果有未完成的退货，标记为售后中
    if any(r.status not in [ReturnStatus.COMPLETED, ReturnStatus.CANCELLED, ReturnStatus.REJECTED] for r in sale.return_orders):
        sale.status = SalesStatus.AFTER_SALES
```

---

## 九、实施计划

### Phase 1: 后端基础
1. 创建模型和枚举
2. 数据库迁移（Alembic）
3. 退货单CRUD API
4. 退货明细API
5. 附件上传/下载API

### Phase 2: 业务逻辑
6. 加工厂自动识别逻辑
7. 退款处理逻辑（生成交易流水）
8. 销售单状态联动
9. 审批流程

### Phase 3: 统计报表
10. 退货统计API

### Phase 4: 前端
11. 退货管理页面
12. 创建/编辑退货单弹窗
13. 附件上传/预览组件
14. 集成到销售页面

### Phase 5: 测试与优化
15. 功能测试
16. 数据一致性校验
17. 性能优化

---

## 十、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 文件存储空间不足 | 高 | 限制单文件大小（20MB），定期清理草稿附件 |
| 退款金额与销售单不匹配 | 高 | 创建退货单时校验退货金额≤销售金额 |
| 加工厂追溯不准确 | 中 | 允许手动修正，自动识别作为默认值 |
| 并发操作导致金额不一致 | 中 | 使用数据库事务+乐观锁 |
| 历史数据兼容问题 | 低 | 保留原表，新模块独立运行 |

---

*设计日期: 2026-05-15*
*版本: v1.0*
