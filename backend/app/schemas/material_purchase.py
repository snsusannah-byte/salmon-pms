"""
物料采购与批次管理 — Pydantic Schemas
"""
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# ==================== 物料采购明细 ====================

class MaterialPurchaseItemCreate(BaseModel):
    """创建采购明细"""
    product_id: int
    box_count: int = Field(..., gt=0)
    items_per_box: int = Field(..., gt=0)
    quoted_unit_price: Decimal | None = None
    actual_amount: Decimal = Field(..., gt=0)
    notes: str | None = None


class MaterialPurchaseItemResponse(BaseModel):
    """采购明细响应"""
    id: int
    product_id: int
    product_name: str
    product_code: str
    box_count: int
    items_per_box: int
    total_qty: Decimal
    unit: str
    quoted_unit_price: Decimal | None
    quoted_amount: Decimal | None
    actual_amount: Decimal
    actual_unit_price: Decimal
    received_qty: Decimal
    is_fully_received: bool
    notes: str | None
    created_at: str

    class Config:
        from_attributes = True


# ==================== 物料采购单 ====================

class MaterialPurchaseOrderCreate(BaseModel):
    """创建物料采购单"""
    order_date: date
    supplier_id: int
    warehouse_id: int | None = None
    quoted_total: Decimal | None = None
    actual_total: Decimal = Field(..., gt=0)
    notes: str | None = None
    items: list[MaterialPurchaseItemCreate] = Field(..., min_length=1)

    @field_validator('actual_total')
    @classmethod
    def validate_actual_total(cls, v: Decimal, info) -> Decimal:
        # 这里只做基本校验，详细一致性校验在 service 层
        return v


class MaterialPurchaseOrderUpdate(BaseModel):
    """更新采购单（仅待入库状态）"""
    order_date: date | None = None
    supplier_id: int | None = None
    warehouse_id: int | None = None
    quoted_total: Decimal | None = None
    actual_total: Decimal | None = None
    notes: str | None = None


class MaterialPurchaseOrderResponse(BaseModel):
    """采购单响应"""
    id: int
    order_no: str
    order_date: date
    supplier_id: int
    supplier_name: str
    quoted_total: Decimal | None
    actual_total: Decimal
    paid_amount: Decimal
    status: str
    payment_status: str
    warehouse_id: int | None
    warehouse_name: str | None
    notes: str | None
    items: list[MaterialPurchaseItemResponse]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class MaterialPurchaseOrderList(BaseModel):
    """采购单列表项"""
    id: int
    order_no: str
    order_date: date
    supplier_id: int
    supplier_name: str
    actual_total: Decimal
    status: str
    payment_status: str
    item_count: int
    batch_no: str | None = None
    warehouse_name: str | None = None
    total_boxes: int = 0
    total_qty: float = 0
    unit: str | None = None
    product_names: list[str] = []

    class Config:
        from_attributes = True


# ==================== 入库 ====================

class MaterialInboundRequest(BaseModel):
    """入库请求"""
    item_id: int
    inbound_qty: Decimal = Field(..., gt=0)
    expiry_date: date | None = None
    location: str | None = None


class MaterialInboundResponse(BaseModel):
    """入库响应"""
    order_id: int
    order_no: str
    status: str
    inbound_records: list[dict]


# ==================== 出库 ====================

class MaterialOutboundRequest(BaseModel):
    """出库请求"""
    product_id: int
    qty: Decimal = Field(..., gt=0)
    strategy: str = Field(default="fifo", pattern="^(fifo|specific)$")
    batch_id: int | None = None
    reason: str | None = None


class MaterialOutboundResponse(BaseModel):
    """出库响应"""
    product_id: int
    product_name: str
    total_qty: Decimal
    allocations: list[dict]
    avg_cost: Decimal


# ==================== 批次 ====================

class MaterialBatchResponse(BaseModel):
    """批次响应"""
    id: int
    batch_no: str
    product_id: int
    product_name: str
    product_code: str
    supplier_name: str | None
    inbound_qty: Decimal
    remaining_qty: Decimal
    unit: str | None
    unit_cost: Decimal
    total_cost: Decimal
    inbound_date: date
    expiry_date: date | None
    warehouse_name: str | None
    location: str | None
    status: str

    class Config:
        from_attributes = True


# ==================== 库存 ====================

class MaterialStockResponse(BaseModel):
    """物料库存响应"""
    product_id: int
    product_code: str
    product_name: str
    spec: str | None
    unit: str
    items_per_box: int | None
    total_qty: Decimal
    batch_count: int
    avg_cost: Decimal
    batches: list[MaterialBatchResponse]

    class Config:
        from_attributes = True


# ==================== 物料列表 ====================

class MaterialListItem(BaseModel):
    """物料列表项"""
    id: int
    code: str
    name: str
    spec: str | None
    unit: str
    items_per_box: int | None
    material_category_id: int | None
    material_category_name: str | None = None
    total_qty: Decimal = Decimal("0")
    batch_count: int = 0
    avg_cost: Decimal = Decimal("0")
    is_active: bool

    class Config:
        from_attributes = True


class MaterialCreate(BaseModel):
    """创建物料"""
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    spec: str | None = Field(default=None, max_length=100)
    unit: str = Field(..., min_length=1, max_length=20)
    material_category_id: int | None = None
    items_per_box: int | None = Field(default=None, gt=0)
    cost_price: Decimal | None = None


class MaterialUpdate(BaseModel):
    """更新物料"""
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    spec: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    material_category_id: int | None = None
    items_per_box: int | None = Field(default=None, gt=0)
    cost_price: Decimal | None = None
    is_active: bool | None = None
