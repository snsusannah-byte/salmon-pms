from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import SalesStatus


class FinishedProductSaleBase(BaseModel):
    """成品销售基础"""
    sale_date: date = Field(..., description="销售日期")
    customer_id: int = Field(..., description="客户ID")
    product_id: int = Field(..., description="成品产品ID")
    quantity: int = Field(..., gt=0, description="数量(件)")
    unit_price: Decimal = Field(..., gt=0, description="单价")
    gross_amount: Decimal = Field(..., gt=0, description="毛金额")
    scan_fee: Decimal = Field(0, ge=0, description="扫码费")
    discount: Decimal = Field(0, ge=0, description="折扣")
    commission: Decimal = Field(0, ge=0, description="佣金")
    net_amount: Decimal = Field(..., gt=0, description="净金额")
    paid_amount: Decimal = Field(0, ge=0, description="已付金额")
    status: Optional[SalesStatus] = Field(SalesStatus.PENDING, description="收款状态")
    salesperson_id: Optional[int] = Field(None, description="销售员ID")
    notes: Optional[str] = Field(None, description="备注")


class FinishedProductSaleCreate(FinishedProductSaleBase):
    pass


class FinishedProductSaleUpdate(BaseModel):
    sale_date: Optional[date] = None
    customer_id: Optional[int] = None
    product_id: Optional[int] = None
    quantity: Optional[int] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, gt=0)
    gross_amount: Optional[Decimal] = Field(None, gt=0)
    scan_fee: Optional[Decimal] = Field(None, ge=0)
    discount: Optional[Decimal] = Field(None, ge=0)
    commission: Optional[Decimal] = Field(None, ge=0)
    net_amount: Optional[Decimal] = Field(None, gt=0)
    paid_amount: Optional[Decimal] = Field(None, ge=0)
    status: Optional[SalesStatus] = None
    salesperson_id: Optional[int] = None
    notes: Optional[str] = None


class FinishedProductSaleResponse(FinishedProductSaleBase):
    """成品销售响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    product_spec: Optional[str] = None
    salesperson_name: Optional[str] = None


class FinishedProductSaleListResponse(BaseModel):
    """成品销售列表响应"""
    total: int
    items: List[FinishedProductSaleResponse]
    skip: int
    limit: int


class FinishedProductSaleSummary(BaseModel):
    """成品销售汇总统计"""
    total_sales: int
    total_quantity: int
    total_gross_amount: Decimal
    total_net_amount: Decimal
    total_paid: Decimal
    total_unpaid: Decimal
    pending_count: int
    partial_count: int
    fully_paid_count: int
