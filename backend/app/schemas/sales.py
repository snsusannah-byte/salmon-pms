from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import SalesStatus


class SalesReceiptBase(BaseModel):
    """收款记录基础"""
    receipt_date: date = Field(..., description="收款日期")
    amount: Decimal = Field(..., gt=0, description="收款金额")
    payment_method: str = Field(..., max_length=50, description="支付方式")
    bank_account_id: Optional[int] = Field(None, description="银行账户ID")
    reference_no: Optional[str] = Field(None, max_length=100, description="参考号")
    notes: Optional[str] = Field(None, description="备注")


class SalesReceiptCreate(SalesReceiptBase):
    pass


class SalesReceiptUpdate(BaseModel):
    receipt_date: Optional[date] = None
    amount: Optional[Decimal] = Field(None, gt=0)
    payment_method: Optional[str] = Field(None, max_length=50)
    bank_account_id: Optional[int] = None
    reference_no: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class SalesReceiptResponse(SalesReceiptBase):
    """收款记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    created_at: datetime
    updated_at: datetime


class AftersalesRecordBase(BaseModel):
    """售后记录基础"""
    record_date: date = Field(..., description="记录日期")
    type: str = Field(..., max_length=50, description="类型")  # return, refund, discount, compensation
    amount: Decimal = Field(..., gt=0, description="金额")
    reason: Optional[str] = Field(None, description="原因")
    status: str = Field("pending", max_length=20, description="状态")
    notes: Optional[str] = Field(None, description="备注")


class AftersalesRecordCreate(AftersalesRecordBase):
    pass


class AftersalesRecordUpdate(BaseModel):
    record_date: Optional[date] = None
    type: Optional[str] = Field(None, max_length=50)
    amount: Optional[Decimal] = Field(None, gt=0)
    reason: Optional[str] = None
    status: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class AftersalesRecordResponse(AftersalesRecordBase):
    """售后记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    created_at: datetime
    updated_at: datetime


class WholeFishSaleBase(BaseModel):
    """整鱼销售基础"""
    batch_id: int = Field(..., description="批次ID")
    sale_date: date = Field(..., description="销售日期")
    customer_id: int = Field(..., description="客户ID")
    weight_kg: Decimal = Field(..., gt=0, description="重量(kg)")
    unit_price: Decimal = Field(..., gt=0, description="单价")
    gross_amount: Decimal = Field(..., gt=0, description="毛金额")
    scan_fee: Decimal = Field(0, ge=0, description="扫码费")
    rounding_adjustment: Decimal = Field(0, description="抹零调整")
    after_sales_adjustment: Decimal = Field(0, description="售后调整")
    discount: Decimal = Field(0, ge=0, description="折扣")
    commission: Decimal = Field(0, ge=0, description="佣金")
    net_amount: Decimal = Field(..., gt=0, description="净金额")
    paid_amount: Decimal = Field(0, ge=0, description="已付金额")
    status: Optional[SalesStatus] = Field(SalesStatus.PENDING, description="收款状态")
    salesperson_id: Optional[int] = Field(None, description="销售员ID")
    notes: Optional[str] = Field(None, description="备注")


class WholeFishSaleCreate(WholeFishSaleBase):
    pass


class WholeFishSaleUpdate(BaseModel):
    batch_id: Optional[int] = None
    sale_date: Optional[date] = None
    customer_id: Optional[int] = None
    weight_kg: Optional[Decimal] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, gt=0)
    gross_amount: Optional[Decimal] = Field(None, gt=0)
    scan_fee: Optional[Decimal] = Field(None, ge=0)
    rounding_adjustment: Optional[Decimal] = None
    after_sales_adjustment: Optional[Decimal] = None
    discount: Optional[Decimal] = Field(None, ge=0)
    commission: Optional[Decimal] = Field(None, ge=0)
    net_amount: Optional[Decimal] = Field(None, gt=0)
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    status: Optional[SalesStatus] = None
    salesperson_id: Optional[int] = None
    notes: Optional[str] = None


class WholeFishSaleResponse(WholeFishSaleBase):
    """整鱼销售响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = None
    batch_name: Optional[str] = None
    batch_code: Optional[str] = None
    salesperson_name: Optional[str] = None
    receipts: List[SalesReceiptResponse] = []
    aftersales: List[AftersalesRecordResponse] = []


class WholeFishSaleListResponse(BaseModel):
    """整鱼销售列表响应"""
    total: int
    items: List[WholeFishSaleResponse]
    skip: int
    limit: int


class SaleSummary(BaseModel):
    """销售汇总统计"""
    total_sales: int
    total_weight_kg: Decimal
    total_gross_amount: Decimal
    total_net_amount: Decimal
    total_paid: Decimal
    total_unpaid: Decimal
    pending_count: int
    partial_count: int
    fully_paid_count: int
