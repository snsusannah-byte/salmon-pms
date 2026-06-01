"""
物料采购与批次管理 — Pydantic Schemas
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ==================== 物料采购明细 ====================

class MaterialPurchaseItemCreate(BaseModel):
    """创建采购明细"""
    product_id: int
    box_count: int = Field(..., gt=0)
    items_per_box: int = Field(..., gt=0)
    quoted_unit_price: Optional[Decimal] = None
    actual_amount: Decimal = Field(..., gt=0)
    notes: Optional[str] = None


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
    quoted_unit_price: Optional[Decimal]
    quoted_amount: Optional[Decimal]
    actual_amount: Decimal
    actual_unit_price: Decimal
    received_qty: Decimal
    is_fully_received: bool
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


# ==================== 物料采购单 ====================

class MaterialPurchaseOrderCreate(BaseModel):
    """创建物料采购单"""
    order_date: date
    supplier_id: int
    warehouse_id: Optional[int] = None
    quoted_total: Optional[Decimal] = None
    actual_total: Decimal = Field(..., gt=0)
    notes: Optional[str] = None
    items: List[MaterialPurchaseItemCreate] = Field(..., min_length=1)

    @field_validator('actual_total')
    @classmethod
    def validate_actual_total(cls, v: Decimal, info) -> Decimal:
        # 这里只做基本校验，详细一致性校验在 service 层
        return v


class MaterialPurchaseOrderUpdate(BaseModel):
    """更新采购单（仅待入库状态）"""
    order_date: Optional[date] = None
    supplier_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    quoted_total: Optional[Decimal] = None
    actual_total: Optional[Decimal] = None
    notes: Optional[str] = None


class MaterialPurchaseOrderResponse(BaseModel):
    """采购单响应"""
    id: int
    order_no: str
    order_date: date
    supplier_id: int
    supplier_name: str
    quoted_total: Optional[Decimal]
    actual_total: Decimal
    paid_amount: Decimal
    status: str
    payment_status: str
    warehouse_id: Optional[int]
    warehouse_name: Optional[str]
    notes: Optional[str]
    items: List[MaterialPurchaseItemResponse]
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
    batch_no: Optional[str] = None
    warehouse_name: Optional[str] = None
    total_boxes: int = 0
    total_qty: float = 0
    unit: Optional[str] = None
    product_names: List[str] = []

    class Config:
        from_attributes = True


# ==================== 入库 ====================

class MaterialInboundRequest(BaseModel):
    """入库请求"""
    item_id: int
    inbound_qty: Decimal = Field(..., gt=0)
    expiry_date: Optional[date] = None
    location: Optional[str] = None


class MaterialInboundResponse(BaseModel):
    """入库响应"""
    order_id: int
    order_no: str
    status: str
    inbound_records: List[dict]


# ==================== 出库 ====================

class MaterialOutboundRequest(BaseModel):
    """出库请求"""
    product_id: int
    qty: Decimal = Field(..., gt=0)
    strategy: str = Field(default="fifo", pattern="^(fifo|specific)$")
    batch_id: Optional[int] = None
    reason: Optional[str] = None


class MaterialOutboundResponse(BaseModel):
    """出库响应"""
    product_id: int
    product_name: str
    total_qty: Decimal
    allocations: List[dict]
    avg_cost: Decimal


# ==================== 批次 ====================

class MaterialBatchResponse(BaseModel):
    """批次响应"""
    id: int
    batch_no: str
    product_id: int
    product_name: str
    product_code: str
    supplier_name: Optional[str]
    inbound_qty: Decimal
    remaining_qty: Decimal
    unit: Optional[str]
    unit_cost: Decimal
    total_cost: Decimal
    inbound_date: date
    expiry_date: Optional[date]
    warehouse_name: Optional[str]
    location: Optional[str]
    status: str

    class Config:
        from_attributes = True


# ==================== 库存 ====================

class MaterialStockResponse(BaseModel):
    """物料库存响应"""
    product_id: int
    product_code: str
    product_name: str
    spec: Optional[str]
    unit: str
    items_per_box: Optional[int]
    total_qty: Decimal
    batch_count: int
    avg_cost: Decimal
    batches: List[MaterialBatchResponse]

    class Config:
        from_attributes = True


# ==================== 物料列表 ====================

class MaterialListItem(BaseModel):
    """物料列表项"""
    id: int
    code: str
    name: str
    spec: Optional[str]
    unit: str
    items_per_box: Optional[int]
    material_category_id: Optional[int]
    material_category_name: Optional[str] = None
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
    spec: Optional[str] = Field(default=None, max_length=100)
    unit: str = Field(..., min_length=1, max_length=20)
    material_category_id: Optional[int] = None
    items_per_box: Optional[int] = Field(default=None, gt=0)
    cost_price: Optional[Decimal] = None


class MaterialUpdate(BaseModel):
    """更新物料"""
    code: Optional[str] = Field(default=None, min_length=1, max_length=50)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    spec: Optional[str] = Field(default=None, max_length=100)
    unit: Optional[str] = Field(default=None, min_length=1, max_length=20)
    material_category_id: Optional[int] = None
    items_per_box: Optional[int] = Field(default=None, gt=0)
    cost_price: Optional[Decimal] = None
    is_active: Optional[bool] = None
