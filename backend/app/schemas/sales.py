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
    rounding_adjustment: Optional[Decimal] = Field(0, ge=0, description="抹零调整金额")


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
    transaction_id: Optional[int] = None
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


# ==================== 整鱼销售子项 ====================

class WholeFishSaleItemBase(BaseModel):
    """整鱼销售子项基础"""
    spec: str = Field(..., max_length=100, description="规格")
    box_count: int = Field(0, ge=0, description="箱数")
    weight_kg: Decimal = Field(..., gt=0, description="重量(kg)")
    unit_price: Decimal = Field(..., gt=0, description="单价")
    sort_order: Optional[int] = Field(0, description="排序")
    notes: Optional[str] = Field(None, description="备注")

    @property
    def amount(self) -> Decimal:
        return self.weight_kg * self.unit_price


class WholeFishSaleItemCreate(WholeFishSaleItemBase):
    pass


class WholeFishSaleItemUpdate(BaseModel):
    spec: Optional[str] = Field(None, max_length=100)
    box_count: Optional[int] = Field(None, ge=0)
    weight_kg: Optional[Decimal] = Field(None, gt=0)
    unit_price: Optional[Decimal] = Field(None, gt=0)
    sort_order: Optional[int] = None
    notes: Optional[str] = None


class WholeFishSaleItemResponse(WholeFishSaleItemBase):
    """整鱼销售子项响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    amount: Decimal
    created_at: datetime
    updated_at: datetime


# ==================== 整鱼销售（带子项） ====================

class WholeFishSaleBase(BaseModel):
    """整鱼销售基础"""
    sale_no: Optional[str] = Field(None, max_length=20, description="销售单号")
    batch_id: int = Field(..., description="批次ID")
    sale_date: date = Field(..., description="销售日期")
    customer_id: int = Field(..., description="客户ID")
    spec: Optional[str] = Field(None, max_length=50, description="规格")
    box_count: Optional[int] = Field(None, ge=0, description="箱数")
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
    is_internal_sale: Optional[bool] = Field(False, description="是否内部销售（加工厂流转）")
    notes: Optional[str] = Field(None, description="备注")

from .returns import ReturnOrderSummary


class WholeFishSaleCreate(WholeFishSaleBase):
    items: Optional[List[WholeFishSaleItemCreate]] = Field(None, description="规格明细列表")


class WholeFishSaleUpdate(BaseModel):
    batch_id: Optional[int] = None
    sale_date: Optional[date] = None
    customer_id: Optional[int] = None
    spec: Optional[str] = Field(None, max_length=50)
    box_count: Optional[int] = Field(None, ge=0)
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
    items: Optional[List[WholeFishSaleItemCreate]] = Field(None, description="规格明细列表（编辑时替换）")


class WholeFishSaleResponse(WholeFishSaleBase):
    """整鱼销售响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_locked: bool
    batch_is_locked: Optional[bool] = False  # 批次是否已锁定
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = None
    batch_name: Optional[str] = None
    batch_code: Optional[str] = None
    salesperson_name: Optional[str] = None
    items: List[WholeFishSaleItemResponse] = []
    receipts: List[SalesReceiptResponse] = []
    aftersales: List[AftersalesRecordResponse] = []
    return_orders: List[ReturnOrderSummary] = []  # 退货单列表
    _aftersales_count: int = 0  # 合并后的售后记录数（用于前端徽章）
    processing_plant_eu_no: Optional[str] = None  # 加工厂EU注册号


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
