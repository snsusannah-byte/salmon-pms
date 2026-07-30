from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import SalesStatus

from .returns import ReturnOrderSummary


class SalesReceiptBase(BaseModel):
    """收款记录基础"""
    receipt_date: date = Field(..., description="收款日期")
    amount: Decimal = Field(..., gt=0, description="收款金额")
    payment_method: str = Field(..., max_length=50, description="支付方式")
    bank_account_id: int | None = Field(None, description="银行账户ID")
    reference_no: str | None = Field(None, max_length=100, description="参考号")
    notes: str | None = Field(None, description="备注")


class SalesReceiptCreate(SalesReceiptBase):
    rounding_adjustment: Decimal | None = Field(0, ge=0, description="抹零调整金额")


class SalesReceiptUpdate(BaseModel):
    receipt_date: date | None = None
    amount: Decimal | None = Field(None, gt=0)
    payment_method: str | None = Field(None, max_length=50)
    bank_account_id: int | None = None
    reference_no: str | None = Field(None, max_length=100)
    notes: str | None = None


class SalesReceiptResponse(SalesReceiptBase):
    """收款记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_id: int
    transaction_id: int | None = None
    created_at: datetime
    updated_at: datetime


class AftersalesRecordBase(BaseModel):
    """售后记录基础"""
    record_date: date = Field(..., description="记录日期")
    type: str = Field(..., max_length=50, description="类型")  # return, refund, discount, compensation
    amount: Decimal = Field(..., gt=0, description="金额")
    reason: str | None = Field(None, description="原因")
    status: str = Field("pending", max_length=20, description="状态")
    notes: str | None = Field(None, description="备注")


class AftersalesRecordCreate(AftersalesRecordBase):
    pass


class AftersalesRecordUpdate(BaseModel):
    record_date: date | None = None
    type: str | None = Field(None, max_length=50)
    amount: Decimal | None = Field(None, gt=0)
    reason: str | None = None
    status: str | None = Field(None, max_length=20)
    notes: str | None = None


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
    unit_price: Decimal = Field(..., ge=0, description="单价")
    sort_order: int | None = Field(0, description="排序")
    notes: str | None = Field(None, description="备注")

    @property
    def amount(self) -> Decimal:
        return self.weight_kg * self.unit_price


class WholeFishSaleItemCreate(WholeFishSaleItemBase):
    pass


class WholeFishSaleItemUpdate(BaseModel):
    spec: str | None = Field(None, max_length=100)
    box_count: int | None = Field(None, ge=0)
    weight_kg: Decimal | None = Field(None, gt=0)
    unit_price: Decimal | None = Field(None, ge=0)
    sort_order: int | None = None
    notes: str | None = None


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
    sale_no: str | None = Field(None, max_length=20, description="销售单号")
    batch_id: int = Field(..., description="批次ID")
    sale_date: date = Field(..., description="销售日期")
    customer_id: int = Field(..., description="客户ID")
    spec: str | None = Field(None, max_length=50, description="规格")
    box_count: int | None = Field(None, ge=0, description="箱数")
    weight_kg: Decimal = Field(..., gt=0, description="重量(kg)")
    unit_price: Decimal = Field(..., ge=0, description="单价")
    gross_amount: Decimal = Field(..., ge=0, description="毛金额")
    scan_fee: Decimal = Field(0, ge=0, description="扫码费")
    rounding_adjustment: Decimal = Field(0, description="抹零调整")
    after_sales_adjustment: Decimal = Field(0, description="售后调整")
    discount: Decimal = Field(0, description="折扣")
    balance_adjustment: Decimal = Field(0, description="账平调整")
    balance_adjustment_reason: str | None = Field(None, description="账平调整原因")

    commission: Decimal = Field(0, ge=0, description="佣金")
    net_amount: Decimal = Field(..., ge=0, description="净金额")
    paid_amount: Decimal = Field(0, ge=0, description="已付金额")
    status: SalesStatus | None = Field(SalesStatus.PENDING, description="收款状态")
    salesperson_id: int | None = Field(None, description="销售员ID")
    discount_reason: str | None = Field(None, description="折扣原因")
    is_internal_sale: bool | None = Field(False, description="是否内部销售（加工厂流转）")
    notes: str | None = Field(None, description="备注")



class WholeFishSaleCreate(WholeFishSaleBase):
    balance_adjustment: Decimal = Field(0, description="账平调整（正数表示从应收中扣减，负数表示追加应收）")

    items: list[WholeFishSaleItemCreate] | None = Field(None, description="规格明细列表")


class WholeFishSaleUpdate(BaseModel):
    batch_id: int | None = None
    sale_date: date | None = None
    customer_id: int | None = None
    spec: str | None = Field(None, max_length=50)
    box_count: int | None = Field(None, ge=0)
    weight_kg: Decimal | None = Field(None, gt=0)
    unit_price: Decimal | None = Field(None, ge=0)
    gross_amount: Decimal | None = Field(None, ge=0)
    scan_fee: Decimal | None = Field(None, ge=0)
    rounding_adjustment: Decimal | None = None
    after_sales_adjustment: Decimal | None = None
    discount: Decimal | None = Field(None, description="折扣")
    balance_adjustment: Decimal | None = Field(None, description="账平调整（正数表示从应收中扣减，负数表示追加应收）")
    balance_adjustment_reason: str | None = None

    commission: Decimal | None = Field(None, ge=0)
    net_amount: Decimal | None = Field(None, ge=0)
    paid_amount: Decimal | None = Field(None, ge=0)
    status: SalesStatus | None = None
    salesperson_id: int | None = None
    discount_reason: str | None = None
    notes: str | None = None
    items: list[WholeFishSaleItemCreate] | None = Field(None, description="规格明细列表（编辑时替换）")


class WholeFishSaleResponse(WholeFishSaleBase):
    """整鱼销售响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_locked: bool
    batch_is_locked: bool | None = False  # 批次是否已锁定
    created_at: datetime
    updated_at: datetime
    customer_name: str | None = None
    batch_name: str | None = None
    batch_code: str | None = None
    salesperson_name: str | None = None
    items: list[WholeFishSaleItemResponse] = []
    receipts: list[SalesReceiptResponse] = []
    aftersales: list[AftersalesRecordResponse] = []
    return_orders: list[ReturnOrderSummary] = []  # 退货单列表
    _aftersales_count: int = 0  # 合并后的售后记录数（用于前端徽章）
    processing_plant_eu_no: str | None = None  # 加工厂EU注册号


class WholeFishSaleListResponse(BaseModel):
    """整鱼销售列表响应"""
    total: int
    items: list[WholeFishSaleResponse]
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
