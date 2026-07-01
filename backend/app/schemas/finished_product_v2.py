"""
成品销售模块V2 - Pydantic Schemas
"""
from datetime import date, datetime
from decimal import Decimal

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
    fish_count: int | None = 0
    total_weight_kg: Decimal
    meat_weight_kg: Decimal
    byproduct_head_count: int = 0
    byproduct_tail_count: int = 0
    byproduct_bone_count: int = 0
    byproduct_trim_weight_kg: Decimal = Decimal("0")
    loss_weight_kg: Decimal = Decimal("0")
    cost_price_per_kg: Decimal | None = None
    notes: str | None = None


class DailySlaughterRecordCreate(DailySlaughterRecordBase):
    pass


class DailySlaughterRecordUpdate(BaseModel):
    fish_count: int | None = None
    total_weight_kg: Decimal | None = None
    meat_weight_kg: Decimal | None = None
    byproduct_head_count: int | None = None
    byproduct_tail_count: int | None = None
    byproduct_bone_count: int | None = None
    byproduct_trim_weight_kg: Decimal | None = None
    loss_weight_kg: Decimal | None = None
    cost_price_per_kg: Decimal | None = None
    notes: str | None = None


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
    items: list[DailySlaughterRecordResponse]
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
    supplier_id: int | None = None
    batch_no: str | None = None
    quantity: Decimal
    unit: str = "kg"
    unit_price: Decimal
    total_amount: Decimal | None = None
    actual_amount: Decimal | None = None  # 实付金额
    box_count: int | None = None  # 箱数
    items_per_box: int | None = None  # 每箱数量
    lead_time_days: int = 0
    warehouse_location: str | None = None
    notes: str | None = None


class WarehousePurchaseOrderCreate(WarehousePurchaseOrderBase):
    pass


class WarehousePurchaseOrderUpdate(BaseModel):
    order_date: date | None = None
    product_id: int | None = None
    supplier_id: int | None = None
    batch_no: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    total_amount: Decimal | None = None
    actual_amount: Decimal | None = None
    box_count: int | None = None
    items_per_box: int | None = None
    lead_time_days: int | None = None
    warehouse_location: str | None = None
    notes: str | None = None


class WarehousePurchaseOrderResponse(WarehousePurchaseOrderBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_name: str | None = None
    supplier_name: str | None = None
    created_at: datetime
    updated_at: datetime


class WarehousePurchaseOrderListResponse(BaseModel):
    total: int
    items: list[WarehousePurchaseOrderResponse]
    skip: int
    limit: int


class WarehouseStockBase(BaseModel):
    product_id: int
    current_quantity: Decimal = Decimal("0")
    reserved_quantity: Decimal = Decimal("0")
    available_quantity: Decimal = Decimal("0")
    unit_cost: Decimal | None = None
    warehouse_location: str | None = None
    warning_threshold: int | None = 0
    is_below_warning: bool = False
    notes: str | None = None


class WarehouseStockResponse(WarehouseStockBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_name: str | None = None
    product_category: str | None = None
    product_unit: str | None = None
    last_in_date: date | None = None
    last_out_date: date | None = None
    created_at: datetime
    updated_at: datetime


class WarehouseStockListResponse(BaseModel):
    total: int
    items: list[WarehouseStockResponse]


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
    items: list[WarehouseStockWarningResponse]


class StockInRequest(BaseModel):
    product_id: int
    quantity: Decimal
    unit_price: Decimal
    order_date: date | None = None
    batch_no: str | None = None
    supplier_id: int | None = None
    warehouse_location: str | None = None
    notes: str | None = None


class StockOutRequest(BaseModel):
    product_id: int
    quantity: Decimal
    reason: str | None = None


# ==================== LossRecord Schemas ====================

class LossRecordBase(BaseModel):
    loss_date: date
    loss_type: str
    slaughter_date: date | None = None
    product_id: int | None = None
    weight_kg: Decimal = Decimal("0")
    quantity: int = 0
    reason: str | None = None
    notes: str | None = None


class LossRecordCreate(LossRecordBase):
    pass


class LossRecordUpdate(BaseModel):
    loss_date: date | None = None
    loss_type: str | None = None
    slaughter_date: date | None = None
    product_id: int | None = None
    weight_kg: Decimal | None = None
    quantity: int | None = None
    reason: str | None = None
    notes: str | None = None


class LossRecordResponse(LossRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_name: str | None = None
    created_at: datetime
    updated_at: datetime


class LossRecordListResponse(BaseModel):
    total: int
    items: list[LossRecordResponse]
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
    weight_kg: Decimal | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    amount: Decimal = Decimal("0")
    notes: str | None = None


class FinishedProductSaleItemCreate(FinishedProductSaleItemBase):
    pass


class FinishedProductSaleItemResponse(FinishedProductSaleItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    product_name: str | None = None
    product_spec: str | None = None
    created_at: datetime
    updated_at: datetime


# ==================== FinishedProductSale with Items Create Schema ====================

class FinishedProductSaleWithItemsCreate(BaseModel):
    """创建成品销售（带子项）的请求体"""
    sale_date: date
    customer_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    gross_amount: Decimal
    net_amount: Decimal
    slaughter_date: date | None = None
    total_weight_kg: Decimal | None = None
    scan_fee: Decimal | None = Decimal("0")
    discount: Decimal | None = Decimal("0")
    commission: Decimal | None = Decimal("0")
    salesperson_id: int | None = None
    notes: str | None = None
    items: list[dict] | None = None
