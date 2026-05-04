"""
成品销售模块V2 - Pydantic Schemas
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


# ==================== 枚举值字符串常量 ====================

SLAUGHTER_TYPE_WHOLE_FISH = "whole_fish"
SLAUGHTER_TYPE_FILLET = "fillet"

LOSS_TYPE_SPOILAGE = "spoilage"
LOSS_TYPE_INVENTORY_DIFF = "inventory_diff"
LOSS_TYPE_EXPIRED = "expired"
LOSS_TYPE_OTHER = "other"

ITEM_TYPE_MAIN = "main"
ITEM_TYPE_GIFT = "gift"
ITEM_TYPE_ACCESSORY = "accessory"


# ==================== DailySlaughterRecord Schemas ====================

class DailySlaughterRecordBase(BaseModel):
    slaughter_date: date
    slaughter_type: str = SLAUGHTER_TYPE_WHOLE_FISH
    fish_count: Optional[int] = 0
    total_weight_kg: Decimal
    meat_weight_kg: Decimal
    byproduct_head_count: int = 0
    byproduct_tail_count: int = 0
    byproduct_bone_count: int = 0
    byproduct_trim_weight_kg: Decimal = Decimal("0")
    loss_weight_kg: Decimal = Decimal("0")
    cost_price_per_kg: Optional[Decimal] = None
    notes: Optional[str] = None


class DailySlaughterRecordCreate(DailySlaughterRecordBase):
    pass


class DailySlaughterRecordUpdate(BaseModel):
    fish_count: Optional[int] = None
    total_weight_kg: Optional[Decimal] = None
    meat_weight_kg: Optional[Decimal] = None
    byproduct_head_count: Optional[int] = None
    byproduct_tail_count: Optional[int] = None
    byproduct_bone_count: Optional[int] = None
    byproduct_trim_weight_kg: Optional[Decimal] = None
    loss_weight_kg: Optional[Decimal] = None
    cost_price_per_kg: Optional[Decimal] = None
    notes: Optional[str] = None


class DailySlaughterRecordResponse(DailySlaughterRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    loss_rate: Decimal
    meat_rate: Decimal
    cost_price_per_kg: Decimal
    total_cost: Decimal
    cost_source: str
    available_meat_kg: Decimal
    sold_meat_kg: Decimal
    is_locked: bool
    created_at: datetime
    updated_at: datetime


class DailySlaughterListResponse(BaseModel):
    total: int
    items: List[DailySlaughterRecordResponse]
    skip: int
    limit: int


class DailySlaughterSummary(BaseModel):
    total_days: int
    total_fish_count: int
    total_meat_kg: Decimal
    avg_meat_rate: Decimal
    avg_cost_price: Decimal
    total_loss_kg: Decimal
    avg_loss_rate: Decimal


class SlaughterDateOption(BaseModel):
    slaughter_date: date
    available_meat_kg: Decimal
    cost_price_per_kg: Decimal
    is_locked: bool


# ==================== Warehouse Schemas ====================

class WarehousePurchaseOrderBase(BaseModel):
    order_date: date
    product_id: int
    supplier_id: Optional[int] = None
    batch_no: Optional[str] = None
    quantity: Decimal
    unit: str = "kg"
    unit_price: Decimal
    total_amount: Optional[Decimal] = None
    lead_time_days: int = 0
    warehouse_location: Optional[str] = None
    notes: Optional[str] = None


class WarehousePurchaseOrderCreate(WarehousePurchaseOrderBase):
    pass


class WarehousePurchaseOrderUpdate(BaseModel):
    order_date: Optional[date] = None
    product_id: Optional[int] = None
    supplier_id: Optional[int] = None
    batch_no: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    lead_time_days: Optional[int] = None
    warehouse_location: Optional[str] = None
    notes: Optional[str] = None


class WarehousePurchaseOrderResponse(WarehousePurchaseOrderBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_name: Optional[str] = None
    supplier_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WarehousePurchaseOrderListResponse(BaseModel):
    total: int
    items: List[WarehousePurchaseOrderResponse]
    skip: int
    limit: int


class WarehouseStockBase(BaseModel):
    product_id: int
    current_quantity: Decimal = Decimal("0")
    reserved_quantity: Decimal = Decimal("0")
    available_quantity: Decimal = Decimal("0")
    unit_cost: Optional[Decimal] = None
    warehouse_location: Optional[str] = None
    warning_threshold: Optional[int] = 0
    is_below_warning: bool = False
    notes: Optional[str] = None


class WarehouseStockResponse(WarehouseStockBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_name: Optional[str] = None
    product_category: Optional[str] = None
    product_unit: Optional[str] = None
    last_in_date: Optional[date] = None
    last_out_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class WarehouseStockListResponse(BaseModel):
    total: int
    items: List[WarehouseStockResponse]


class WarehouseStockWarningResponse(BaseModel):
    product_id: int
    product_name: str
    product_category: str
    current_quantity: Decimal
    warning_threshold: int
    shortage: Decimal
    lead_time_days: int
    avg_daily_consumption: Decimal
    safety_buffer: int


class WarehouseStockWarningListResponse(BaseModel):
    total: int
    items: List[WarehouseStockWarningResponse]


class StockInRequest(BaseModel):
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    order_date: Optional[date] = None
    batch_no: Optional[str] = None
    supplier_id: Optional[int] = None
    warehouse_location: Optional[str] = None
    notes: Optional[str] = None


class StockOutRequest(BaseModel):
    product_id: int
    quantity: Decimal
    reason: Optional[str] = None


# ==================== LossRecord Schemas ====================

class LossRecordBase(BaseModel):
    loss_date: date
    loss_type: str
    slaughter_date: Optional[date] = None
    product_id: Optional[int] = None
    weight_kg: Decimal = Decimal("0")
    quantity: int = 0
    reason: Optional[str] = None
    notes: Optional[str] = None


class LossRecordCreate(LossRecordBase):
    pass


class LossRecordUpdate(BaseModel):
    loss_date: Optional[date] = None
    loss_type: Optional[str] = None
    slaughter_date: Optional[date] = None
    product_id: Optional[int] = None
    weight_kg: Optional[Decimal] = None
    quantity: Optional[int] = None
    reason: Optional[str] = None
    notes: Optional[str] = None


class LossRecordResponse(LossRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LossRecordListResponse(BaseModel):
    total: int
    items: List[LossRecordResponse]
    skip: int
    limit: int


class LossRecordSummary(BaseModel):
    total_loss_weight_kg: Decimal
    total_loss_quantity: int
    by_type: dict


# ==================== FinishedProductSaleItem Schemas ====================

class FinishedProductSaleItemBase(BaseModel):
    item_type: str
    product_id: int
    weight_kg: Optional[Decimal] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    amount: Decimal = Decimal("0")
    notes: Optional[str] = None


class FinishedProductSaleItemCreate(FinishedProductSaleItemBase):
    pass


class FinishedProductSaleItemResponse(FinishedProductSaleItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    product_name: Optional[str] = None
    product_spec: Optional[str] = None
    created_at: datetime
    updated_at: datetime
