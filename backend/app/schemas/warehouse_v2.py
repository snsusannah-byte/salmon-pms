"""
仓库模块V2 - Schemas
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ==================== 仓库 ====================

class WarehouseBase(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=50)
    type: str = Field(..., max_length=20)
    business_scope: str = Field(default="all", max_length=20)
    is_active: bool = Field(default=True)
    notes: Optional[str] = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class WarehouseResponse(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class WarehouseListResponse(BaseModel):
    total: int
    items: List[WarehouseResponse]
    skip: int = 0
    limit: int = 100


# ==================== 库存 ====================

class StockBase(BaseModel):
    warehouse_id: int
    product_id: int
    batch_id: Optional[int] = None
    current_qty: Decimal = Field(default=Decimal("0"))
    reserved_qty: Decimal = Field(default=Decimal("0"))
    available_qty: Decimal = Field(default=Decimal("0"))
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    unit: str = Field(default="kg", max_length=20)
    warning_threshold: int = Field(default=0)
    is_below_warning: bool = Field(default=False)
    last_in_date: Optional[date] = None
    last_out_date: Optional[date] = None
    location: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class StockResponse(StockBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_name: Optional[str] = None
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    batch_no: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class StockListResponse(BaseModel):
    total: int
    items: List[StockResponse]
    skip: int = 0
    limit: int = 100


class StockSummaryItem(BaseModel):
    warehouse_id: int
    warehouse_name: str
    warehouse_type: str
    product_count: int
    total_qty: Decimal
    total_cost: Decimal


class StockSummaryResponse(BaseModel):
    items: List[StockSummaryItem]


# ==================== 入库 ====================

class StockInboundBase(BaseModel):
    inbound_no: str = Field(..., max_length=50)
    source_type: str = Field(..., max_length=50)
    source_id: Optional[int] = None
    source_no: Optional[str] = Field(None, max_length=100)
    warehouse_id: int
    product_id: int
    batch_id: Optional[int] = None
    qty: Decimal
    unit: str = Field(..., max_length=20)
    unit_cost: Decimal
    total_cost: Decimal
    supplier_id: Optional[int] = None
    detail: Optional[dict] = None
    inbound_date: date
    notes: Optional[str] = None


class StockInboundCreate(BaseModel):
    source_type: str = Field(..., max_length=50)
    source_id: Optional[int] = None
    source_no: Optional[str] = Field(None, max_length=100)
    warehouse_id: int
    product_id: int
    batch_id: Optional[int] = None
    qty: Decimal = Field(..., gt=0)
    unit: str = Field(..., max_length=20)
    unit_cost: Decimal = Field(..., ge=0)
    supplier_id: Optional[int] = None
    detail: Optional[dict] = None
    inbound_date: date
    notes: Optional[str] = None


class StockInboundResponse(StockInboundBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    warehouse_name: Optional[str] = None
    product_name: Optional[str] = None


class StockInboundListResponse(BaseModel):
    total: int
    items: List[StockInboundResponse]
    skip: int = 0
    limit: int = 100


# ==================== 出库 ====================

class StockOutboundBase(BaseModel):
    outbound_no: str = Field(..., max_length=50)
    dest_type: str = Field(..., max_length=50)
    dest_id: Optional[int] = None
    dest_no: Optional[str] = Field(None, max_length=100)
    warehouse_id: int
    product_id: int
    batch_id: Optional[int] = None
    qty: Decimal
    unit: str = Field(..., max_length=20)
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    outbound_date: date
    notes: Optional[str] = None


class StockOutboundCreate(BaseModel):
    dest_type: str = Field(..., max_length=50)
    dest_id: Optional[int] = None
    dest_no: Optional[str] = Field(None, max_length=100)
    warehouse_id: int
    product_id: int
    batch_id: Optional[int] = None
    qty: Decimal = Field(..., gt=0)
    unit: str = Field(..., max_length=20)
    outbound_date: date
    notes: Optional[str] = None


class StockOutboundResponse(StockOutboundBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    warehouse_name: Optional[str] = None
    product_name: Optional[str] = None


class StockOutboundListResponse(BaseModel):
    total: int
    items: List[StockOutboundResponse]
    skip: int = 0
    limit: int = 100


# ==================== 调拨 ====================

class StockTransferBase(BaseModel):
    transfer_no: str = Field(..., max_length=50)
    from_warehouse_id: int
    to_warehouse_id: int
    product_id: int
    batch_id: Optional[int] = None
    from_qty: Decimal
    from_unit: str = Field(..., max_length=20)
    to_qty: Decimal
    to_unit: str = Field(..., max_length=20)
    conversion_ratio: Decimal
    detail: Optional[dict] = None
    transfer_date: date
    notes: Optional[str] = None


class StockTransferCreate(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    product_id: int
    batch_id: Optional[int] = None
    from_qty: Decimal = Field(..., gt=0)
    from_unit: str = Field(..., max_length=20)
    to_qty: Decimal = Field(..., gt=0)
    to_unit: str = Field(..., max_length=20)
    conversion_ratio: Decimal = Field(..., gt=0)
    detail: Optional[dict] = None
    transfer_date: date
    notes: Optional[str] = None


class StockTransferResponse(StockTransferBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    from_warehouse_name: Optional[str] = None
    to_warehouse_name: Optional[str] = None
    product_name: Optional[str] = None


class StockTransferListResponse(BaseModel):
    total: int
    items: List[StockTransferResponse]
    skip: int = 0
    limit: int = 100


# ==================== 库存变动 ====================

class StockMovementBase(BaseModel):
    warehouse_id: int
    product_id: int
    batch_id: Optional[int] = None
    movement_type: str = Field(..., max_length=20)
    movement_date: date
    qty_change: Decimal
    qty_before: Decimal
    qty_after: Decimal
    unit: str = Field(..., max_length=20)
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    ref_type: str = Field(..., max_length=50)
    ref_id: int
    ref_no: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class StockMovementResponse(StockMovementBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    warehouse_name: Optional[str] = None
    product_name: Optional[str] = None


class StockMovementListResponse(BaseModel):
    total: int
    items: List[StockMovementResponse]
    skip: int = 0
    limit: int = 100


# ==================== 单位转换 ====================

class ProductUnitConversionBase(BaseModel):
    product_id: int
    from_unit: str = Field(..., max_length=20)
    to_unit: str = Field(..., max_length=20)
    ratio: Decimal = Field(..., gt=0)
    is_default: bool = Field(default=True)
    notes: Optional[str] = None


class ProductUnitConversionCreate(ProductUnitConversionBase):
    pass


class ProductUnitConversionResponse(ProductUnitConversionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    product_name: Optional[str] = None


class ProductUnitConversionListResponse(BaseModel):
    total: int
    items: List[ProductUnitConversionResponse]
    skip: int = 0
    limit: int = 100
