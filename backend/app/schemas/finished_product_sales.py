"""
成品销售模块 Pydantic Schemas
"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FinishedProductSaleItemBase(BaseModel):
    item_type: str
    product_id: int
    product_name: str | None = None
    quantity: int = 0
    weight_kg: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None
    notes: str | None = None


class FinishedProductSaleItemCreate(FinishedProductSaleItemBase):
    pass


class FinishedProductSaleItemResponse(FinishedProductSaleItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FinishedProductReceiptBase(BaseModel):
    receipt_date: date
    amount: Decimal
    payment_method: str | None = None
    bank_account_id: int | None = None
    reference_no: str | None = None
    notes: str | None = None


class FinishedProductReceiptCreate(FinishedProductReceiptBase):
    pass


class FinishedProductReceiptUpdate(BaseModel):
    receipt_date: date | None = None
    amount: Decimal | None = None
    payment_method: str | None = None
    bank_account_id: int | None = None
    reference_no: str | None = None
    notes: str | None = None


class FinishedProductReceiptResponse(FinishedProductReceiptBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FinishedProductAftersalesBase(BaseModel):
    record_date: date
    type: str
    amount: Decimal
    reason: str | None = None
    status: str | None = "pending"
    notes: str | None = None


class FinishedProductAftersalesCreate(FinishedProductAftersalesBase):
    pass


class FinishedProductAftersalesUpdate(BaseModel):
    record_date: date | None = None
    type: str | None = None
    amount: Decimal | None = None
    reason: str | None = None
    status: str | None = None
    notes: str | None = None


class FinishedProductAftersalesResponse(FinishedProductAftersalesBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FinishedProductCommissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    salesperson_id: int
    sale_id: int
    sale_date: date
    sale_amount: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    status: str
    paid_date: date | None = None
    notes: str | None = None
    salesperson: dict | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FinishedProductSaleBase(BaseModel):
    sale_date: date
    customer_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    gross_amount: Decimal
    net_amount: Decimal
    scan_fee: Decimal | None = Decimal("0")
    discount: Decimal | None = Decimal("0")
    commission: Decimal | None = Decimal("0")
    paid_amount: Decimal | None = Decimal("0")
    status: str | None = "pending"
    salesperson_id: int | None = None
    is_locked: bool | None = False
    notes: str | None = None
    slaughter_date: date | None = None
    total_weight_kg: Decimal | None = None  # V3: 新增总重量(kg)
    # V4: 支持整鱼销售模式
    sale_type: str | None = "finished_product"  # "finished_product" | "whole_fish"
    spec: str | None = None  # 整鱼规格
    box_count: int | None = None  # 整鱼箱数
    purchase_order_id: int | None = None  # 关联采购入库单


class FinishedProductSaleCreate(FinishedProductSaleBase):
    pass


class FinishedProductSaleUpdate(BaseModel):
    sale_date: date | None = None
    customer_id: int | None = None
    product_id: int | None = None
    quantity: int | None = None
    unit_price: Decimal | None = None
    gross_amount: Decimal | None = None
    net_amount: Decimal | None = None
    scan_fee: Decimal | None = None
    discount: Decimal | None = None
    commission: Decimal | None = None
    paid_amount: Decimal | None = None
    status: str | None = None
    salesperson_id: int | None = None
    is_locked: bool | None = None
    notes: str | None = None
    slaughter_date: date | None = None
    total_weight_kg: Decimal | None = None  # V3: 新增
    # V4: 支持整鱼销售模式
    sale_type: str | None = None
    spec: str | None = None
    box_count: int | None = None
    purchase_order_id: int | None = None


class FinishedProductSaleResponse(FinishedProductSaleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    items: list[FinishedProductSaleItemResponse] = []
    receipts: list[FinishedProductReceiptResponse] = []
    aftersales: list[FinishedProductAftersalesResponse] = []
    commissions: list[FinishedProductCommissionResponse] = []
    customer_name: str | None = None
    product_name: str | None = None
    product_spec: str | None = None
    salesperson_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # 退货模块兼容字段
    return_orders: list[dict] = []
    _aftersales_count: int = 0


class FinishedProductSaleListResponse(BaseModel):
    total: int
    items: list[FinishedProductSaleResponse]
    skip: int
    limit: int


class FinishedProductSaleSummary(BaseModel):
    total_sales: int
    total_quantity: int  # 总份数
    total_gross_amount: Decimal
    total_net_amount: Decimal
    total_paid_amount: Decimal
    total_unpaid_amount: Decimal
    total_scan_fee: Decimal
    total_discount: Decimal
    total_commission: Decimal
    # V3: 新增重量统计
    total_weight_kg: Decimal | None = Decimal("0")


class FinishedProductBatchImportRow(BaseModel):
    customer_name: str
    sale_date: str | None = None
    product_code: str
    quantity: int
    unit_price: Decimal
    salesperson_name: str | None = None
    scan_fee: Decimal | None = Decimal("0")
    discount: Decimal | None = Decimal("0")
    commission: Decimal | None = Decimal("0")
    notes: str | None = None


class FinishedProductBatchImportRequest(BaseModel):
    rows: list[FinishedProductBatchImportRow]
