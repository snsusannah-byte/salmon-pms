"""
成品销售模块 Pydantic Schemas
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class FinishedProductSaleItemBase(BaseModel):
    item_type: str
    product_id: int
    product_name: Optional[str] = None
    quantity: int = 0
    weight_kg: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None


class FinishedProductSaleItemCreate(FinishedProductSaleItemBase):
    pass


class FinishedProductSaleItemResponse(FinishedProductSaleItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FinishedProductReceiptBase(BaseModel):
    receipt_date: date
    amount: Decimal
    payment_method: Optional[str] = None
    bank_account_id: Optional[int] = None
    reference_no: Optional[str] = None
    notes: Optional[str] = None


class FinishedProductReceiptCreate(FinishedProductReceiptBase):
    pass


class FinishedProductReceiptUpdate(BaseModel):
    receipt_date: Optional[date] = None
    amount: Optional[Decimal] = None
    payment_method: Optional[str] = None
    bank_account_id: Optional[int] = None
    reference_no: Optional[str] = None
    notes: Optional[str] = None


class FinishedProductReceiptResponse(FinishedProductReceiptBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FinishedProductAftersalesBase(BaseModel):
    record_date: date
    type: str
    amount: Decimal
    reason: Optional[str] = None
    status: Optional[str] = "pending"
    notes: Optional[str] = None


class FinishedProductAftersalesCreate(FinishedProductAftersalesBase):
    pass


class FinishedProductAftersalesUpdate(BaseModel):
    record_date: Optional[date] = None
    type: Optional[str] = None
    amount: Optional[Decimal] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class FinishedProductAftersalesResponse(FinishedProductAftersalesBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


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
    paid_date: Optional[date] = None
    notes: Optional[str] = None
    salesperson: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class FinishedProductSaleBase(BaseModel):
    sale_date: date
    customer_id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    gross_amount: Decimal
    net_amount: Decimal
    scan_fee: Optional[Decimal] = Decimal("0")
    discount: Optional[Decimal] = Decimal("0")
    commission: Optional[Decimal] = Decimal("0")
    paid_amount: Optional[Decimal] = Decimal("0")
    status: Optional[str] = "pending"
    salesperson_id: Optional[int] = None
    is_locked: Optional[bool] = False
    notes: Optional[str] = None
    slaughter_date: Optional[date] = None
    total_weight_kg: Optional[Decimal] = None  # V3: 新增总重量(kg)
    # V4: 支持整鱼销售模式
    sale_type: Optional[str] = "finished_product"  # "finished_product" | "whole_fish"
    spec: Optional[str] = None  # 整鱼规格
    box_count: Optional[int] = None  # 整鱼箱数
    purchase_order_id: Optional[int] = None  # 关联采购入库单


class FinishedProductSaleCreate(FinishedProductSaleBase):
    pass


class FinishedProductSaleUpdate(BaseModel):
    sale_date: Optional[date] = None
    customer_id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    gross_amount: Optional[Decimal] = None
    net_amount: Optional[Decimal] = None
    scan_fee: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    paid_amount: Optional[Decimal] = None
    status: Optional[str] = None
    salesperson_id: Optional[int] = None
    is_locked: Optional[bool] = None
    notes: Optional[str] = None
    slaughter_date: Optional[date] = None
    total_weight_kg: Optional[Decimal] = None  # V3: 新增
    # V4: 支持整鱼销售模式
    sale_type: Optional[str] = None
    spec: Optional[str] = None
    box_count: Optional[int] = None
    purchase_order_id: Optional[int] = None


class FinishedProductSaleResponse(FinishedProductSaleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    items: List[FinishedProductSaleItemResponse] = []
    receipts: List[FinishedProductReceiptResponse] = []
    aftersales: List[FinishedProductAftersalesResponse] = []
    commissions: List[FinishedProductCommissionResponse] = []
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    product_spec: Optional[str] = None
    salesperson_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 退货模块兼容字段
    return_orders: List[dict] = []
    _aftersales_count: int = 0


class FinishedProductSaleListResponse(BaseModel):
    total: int
    items: List[FinishedProductSaleResponse]
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
    total_weight_kg: Optional[Decimal] = Decimal("0")


class FinishedProductBatchImportRow(BaseModel):
    customer_name: str
    sale_date: Optional[str] = None
    product_code: str
    quantity: int
    unit_price: Decimal
    salesperson_name: Optional[str] = None
    scan_fee: Optional[Decimal] = Decimal("0")
    discount: Optional[Decimal] = Decimal("0")
    commission: Optional[Decimal] = Decimal("0")
    notes: Optional[str] = None


class FinishedProductBatchImportRequest(BaseModel):
    rows: List[FinishedProductBatchImportRow]
