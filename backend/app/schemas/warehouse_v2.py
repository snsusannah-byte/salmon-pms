"""
仓库模块V2 - Schemas
"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ==================== 仓库 ====================

class WarehouseBase(BaseModel):
    code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=50)
    type: str = Field(..., max_length=20)
    business_scope: str = Field(default="all", max_length=20)
    is_active: bool = Field(default=True)
    notes: str | None = None


class WarehouseCreate(WarehouseBase):
    pass


class WarehouseUpdate(BaseModel):
    name: str | None = Field(None, max_length=50)
    is_active: bool | None = None
    notes: str | None = None


class WarehouseResponse(WarehouseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class WarehouseListResponse(BaseModel):
    total: int
    items: list[WarehouseResponse]
    skip: int = 0
    limit: int = 100


# ==================== 库存 ====================

class StockBase(BaseModel):
    warehouse_id: int
    product_id: int
    batch_id: int | None = None
    current_qty: Decimal = Field(default=Decimal("0"))
    reserved_qty: Decimal = Field(default=Decimal("0"))
    available_qty: Decimal = Field(default=Decimal("0"))
    current_box_count: int = Field(default=0)
    available_box_count: int = Field(default=0)
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
    unit: str = Field(default="kg", max_length=20)
    warning_threshold: int = Field(default=0)
    is_below_warning: bool = Field(default=False)
    last_in_date: date | None = None
    last_out_date: date | None = None
    location: str | None = Field(None, max_length=100)
    notes: str | None = None


class StockResponse(StockBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_name: str | None = None
    product_name: str | None = None
    product_category: str | None = None
    batch_no: str | None = None
    batch_nos: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class StockListResponse(BaseModel):
    total: int
    items: list[StockResponse]
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
    items: list[StockSummaryItem]


# ==================== 入库 ====================

class StockInboundBase(BaseModel):
    inbound_no: str = Field(..., max_length=50)
    source_type: str = Field(..., max_length=50)
    source_id: int | None = None
    source_no: str | None = Field(None, max_length=100)
    warehouse_id: int
    product_id: int
    batch_id: int | None = None
    qty: Decimal
    unit: str = Field(..., max_length=20)
    unit_cost: Decimal
    total_cost: Decimal
    supplier_id: int | None = None
    detail: dict | None = None
    inbound_date: date
    notes: str | None = None


class StockInboundCreate(BaseModel):
    source_type: str = Field(..., max_length=50)
    source_id: int | None = None
    source_no: str | None = Field(None, max_length=100)
    warehouse_id: int
    product_id: int
    batch_id: int | None = None
    qty: Decimal = Field(..., gt=0)
    unit: str = Field(..., max_length=20)
    unit_cost: Decimal = Field(..., ge=0)
    supplier_id: int | None = None
    detail: dict | None = None
    inbound_date: date
    notes: str | None = None


class StockInboundResponse(StockInboundBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    warehouse_name: str | None = None
    product_name: str | None = None


class StockInboundListResponse(BaseModel):
    total: int
    items: list[StockInboundResponse]
    skip: int = 0
    limit: int = 100


# ==================== 出库 ====================

class StockOutboundBase(BaseModel):
    outbound_no: str = Field(..., max_length=50)
    dest_type: str = Field(..., max_length=50)
    dest_id: int | None = None
    dest_no: str | None = Field(None, max_length=100)
    warehouse_id: int
    product_id: int
    batch_id: int | None = None
    qty: Decimal
    unit: str = Field(..., max_length=20)
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
    outbound_date: date
    notes: str | None = None


class StockOutboundCreate(BaseModel):
    dest_type: str = Field(..., max_length=50)
    dest_id: int | None = None
    dest_no: str | None = Field(None, max_length=100)
    warehouse_id: int
    product_id: int
    batch_id: int | None = None
    qty: Decimal = Field(..., gt=0)
    unit: str = Field(..., max_length=20)
    outbound_date: date
    notes: str | None = None


class StockOutboundResponse(StockOutboundBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    warehouse_name: str | None = None
    product_name: str | None = None


class StockOutboundListResponse(BaseModel):
    total: int
    items: list[StockOutboundResponse]
    skip: int = 0
    limit: int = 100


# ==================== 调拨 ====================

class StockTransferBase(BaseModel):
    transfer_no: str = Field(..., max_length=50)
    from_warehouse_id: int
    to_warehouse_id: int
    product_id: int
    batch_id: int | None = None
    from_qty: Decimal
    from_unit: str = Field(..., max_length=20)
    to_qty: Decimal
    to_unit: str = Field(..., max_length=20)
    conversion_ratio: Decimal
    detail: dict | None = None
    transfer_date: date
    notes: str | None = None


class StockTransferCreate(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    product_id: int
    batch_id: int | None = None
    from_qty: Decimal = Field(..., gt=0)
    from_unit: str = Field(..., max_length=20)
    to_qty: Decimal = Field(..., gt=0)
    to_unit: str = Field(..., max_length=20)
    conversion_ratio: Decimal = Field(..., gt=0)
    detail: dict | None = None
    transfer_date: date
    notes: str | None = None


class StockTransferResponse(StockTransferBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    from_warehouse_name: str | None = None
    to_warehouse_name: str | None = None
    product_name: str | None = None


class StockTransferListResponse(BaseModel):
    total: int
    items: list[StockTransferResponse]
    skip: int = 0
    limit: int = 100


# ==================== 库存变动 ====================

class StockMovementBase(BaseModel):
    warehouse_id: int
    product_id: int
    batch_id: int | None = None
    batch_no: str | None = None
    movement_type: str = Field(..., max_length=20)
    movement_date: date
    qty_change: Decimal
    qty_before: Decimal
    qty_after: Decimal
    box_count_change: int = Field(default=0)
    box_count_before: int = Field(default=0)
    box_count_after: int = Field(default=0)
    unit: str = Field(..., max_length=20)
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
    ref_type: str = Field(..., max_length=50)
    ref_id: int
    ref_no: str | None = Field(None, max_length=100)
    notes: str | None = None


class StockMovementResponse(StockMovementBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    warehouse_name: str | None = None
    product_name: str | None = None


class StockMovementListResponse(BaseModel):
    total: int
    items: list[StockMovementResponse]
    skip: int = 0
    limit: int = 100


# ==================== 单位转换 ====================

class ProductUnitConversionBase(BaseModel):
    product_id: int
    from_unit: str = Field(..., max_length=20)
    to_unit: str = Field(..., max_length=20)
    ratio: Decimal = Field(..., gt=0)
    is_default: bool = Field(default=True)
    notes: str | None = None


class ProductUnitConversionCreate(ProductUnitConversionBase):
    pass


class ProductUnitConversionResponse(ProductUnitConversionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    product_name: str | None = None


class ProductUnitConversionListResponse(BaseModel):
    total: int
    items: list[ProductUnitConversionResponse]
    skip: int = 0
    limit: int = 100


# ==================== 批次规格明细 ====================

class BatchSpecItem(BaseModel):
    spec: str
    box_count: int
    weight_kg: float
    unit_cost: float | None = None
    total_cost: float | None = None


class BatchSpecResponse(BaseModel):
    batch_no: str
    invoice_no: str | None = None
    inbound_date: date | None = None
    product_name: str
    warehouse_name: str
    total_boxes: int
    total_weight_kg: float
    specs: list[BatchSpecItem]
