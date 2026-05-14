from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExchangeRecordBase(BaseModel):
    """购汇记录基础"""
    invoice_id: Optional[int] = Field(None, description="发票ID")
    batch_id: Optional[int] = Field(None, description="批次ID")
    exchange_date: date = Field(..., description="购汇日期")
    amount_usd: Decimal = Field(..., gt=0, description="购汇金额(USD)")
    exchange_rate: Decimal = Field(..., gt=0, description="汇率")
    amount_cny: Decimal = Field(..., gt=0, description="购汇金额(CNY)")
    fee_cny: Decimal = Field(0, ge=0, description="手续费(CNY)")
    bank_account_id: Optional[int] = Field(None, description="银行账户ID")
    status: str = Field("completed", max_length=20, description="状态")
    notes: Optional[str] = Field(None, description="备注")


class ExchangeRecordCreate(ExchangeRecordBase):
    pass


class ExchangeRecordUpdate(BaseModel):
    invoice_id: Optional[int] = None
    batch_id: Optional[int] = None
    exchange_date: Optional[date] = None
    amount_usd: Optional[Decimal] = Field(None, gt=0)
    exchange_rate: Optional[Decimal] = Field(None, gt=0)
    amount_cny: Optional[Decimal] = Field(None, gt=0)
    fee_cny: Optional[Decimal] = Field(None, ge=0)
    bank_account_id: Optional[int] = None
    status: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class ExchangeRecordResponse(ExchangeRecordBase):
    """购汇记录响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ImportTaxBase(BaseModel):
    """进口税费基础"""
    invoice_id: int = Field(..., description="发票ID")
    tax_date: date = Field(..., description="税费日期")
    import_duty: Decimal = Field(0, ge=0, description="进口关税")
    import_vat: Decimal = Field(0, ge=0, description="进口增值税")
    consumption_tax: Optional[Decimal] = Field(0, ge=0, description="消费税")
    other_taxes: Optional[Decimal] = Field(0, ge=0, description="其他税费")
    total_tax: Decimal = Field(..., gt=0, description="税费合计")
    notes: Optional[str] = Field(None, description="备注")


class ImportTaxCreate(ImportTaxBase):
    pass


class ImportTaxUpdate(BaseModel):
    tax_date: Optional[date] = None
    import_duty: Optional[Decimal] = Field(None, ge=0)
    import_vat: Optional[Decimal] = Field(None, ge=0)
    consumption_tax: Optional[Decimal] = Field(None, ge=0)
    other_taxes: Optional[Decimal] = Field(None, ge=0)
    total_tax: Optional[Decimal] = Field(None, gt=0)
    notes: Optional[str] = None


class ImportTaxResponse(ImportTaxBase):
    """进口税费响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class ClearanceCostBase(BaseModel):
    """清关运费基础"""
    invoice_id: int = Field(..., description="发票ID")
    cost_date: date = Field(..., description="费用日期")
    clearance_fee: Decimal = Field(0, ge=0, description="清关费")
    freight_fee: Decimal = Field(0, ge=0, description="运费")
    inspection_fee: Optional[Decimal] = Field(0, ge=0, description="检验费")
    quarantine_fee: Optional[Decimal] = Field(0, ge=0, description="检疫费")
    other_costs: Optional[Decimal] = Field(0, ge=0, description="其他费用")
    total_cost: Decimal = Field(..., gt=0, description="费用合计")
    notes: Optional[str] = Field(None, description="备注")


class ClearanceCostCreate(ClearanceCostBase):
    pass


class ClearanceCostUpdate(BaseModel):
    cost_date: Optional[date] = None
    clearance_fee: Optional[Decimal] = Field(None, ge=0)
    freight_fee: Optional[Decimal] = Field(None, ge=0)
    inspection_fee: Optional[Decimal] = Field(None, ge=0)
    quarantine_fee: Optional[Decimal] = Field(None, ge=0)
    other_costs: Optional[Decimal] = Field(None, ge=0)
    total_cost: Optional[Decimal] = Field(None, gt=0)
    notes: Optional[str] = None


class ClearanceCostResponse(ClearanceCostBase):
    """清关运费响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class TransactionRecordBase(BaseModel):
    """统一交易流水基础"""
    transaction_date: date = Field(..., description="交易日期")
    type: str = Field(..., max_length=20, description="类型")  # income, expense, transfer, exchange
    category: str = Field(..., max_length=50, description="分类")
    amount: Decimal = Field(..., gt=0, description="金额")
    currency: str = Field("CNY", max_length=10, description="币种")
    from_account_id: Optional[int] = Field(None, description="转出账户")
    to_account_id: Optional[int] = Field(None, description="转入账户")
    counterparty_id: Optional[int] = Field(None, description="对方主体ID")
    counterparty_name: Optional[str] = Field(None, max_length=200, description="对方名称")
    reference_no: Optional[str] = Field(None, max_length=100, description="参考号")
    description: Optional[str] = Field(None, description="描述")
    related_invoice_id: Optional[int] = Field(None, description="关联发票ID")
    related_batch_id: Optional[int] = Field(None, description="关联批次ID")
    is_confirmed: bool = Field(True, description="是否已确认")
    notes: Optional[str] = Field(None, description="备注")


class TransactionRecordCreate(TransactionRecordBase):
    related_sale_ids: Optional[List[int]] = Field(None, description="关联销售单ID列表（合并收款时）")
    pass


class TransactionRecordUpdate(BaseModel):
    transaction_date: Optional[date] = None
    type: Optional[str] = Field(None, max_length=20)
    category: Optional[str] = Field(None, max_length=50)
    amount: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=10)
    from_account_id: Optional[int] = None
    to_account_id: Optional[int] = None
    counterparty_id: Optional[int] = None
    counterparty_name: Optional[str] = Field(None, max_length=200)
    reference_no: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    related_invoice_id: Optional[int] = None
    related_batch_id: Optional[int] = None
    related_sale_ids: Optional[List[int]] = None
    is_confirmed: Optional[bool] = None
    notes: Optional[str] = None


class TransactionRecordResponse(TransactionRecordBase):
    """交易流水响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_locked: bool = False
    related_sale_ids: Optional[List[int]] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("related_sale_ids", mode="before")
    @classmethod
    def parse_related_sale_ids(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return None


class FinanceSummary(BaseModel):
    """财务汇总"""
    total_exchange_usd: Decimal
    total_exchange_cny: Decimal
    total_tax: Decimal
    total_clearance_cost: Decimal
    total_income: Decimal
    total_expense: Decimal
    net_flow: Decimal


# ==================== 统一进口费用 (合并税费+清关) ====================

class ImportFeeCreate(BaseModel):
    """统一进口费用创建"""
    invoice_id: int = Field(..., description="发票ID")
    expense_date: date = Field(..., description="费用日期")
    customs_broker_id: Optional[int] = Field(15, description="报关行ID")
    # 海关税费
    import_duty: Decimal = Field(0, ge=0, description="进口关税")
    import_vat: Decimal = Field(0, ge=0, description="进口增值税")
    # 清关费用
    pickup_fee: Decimal = Field(0, ge=0, description="提货费")
    freight: Decimal = Field(0, ge=0, description="运费")
    yard_fee: Decimal = Field(0, ge=0, description="场地费")
    cold_storage_fee: Decimal = Field(0, ge=0, description="冷藏费")
    clearance_service_fee: Decimal = Field(0, ge=0, description="报关服务费")
    notes: Optional[str] = Field(None, description="备注")


class ImportFeeUpdate(BaseModel):
    """统一进口费用更新（invoice_id 从路径参数获取，body 中不需要）"""
    expense_date: date = Field(..., description="费用日期")
    customs_broker_id: Optional[int] = Field(15, description="报关行ID")
    import_duty: Decimal = Field(0, ge=0, description="进口关税")
    import_vat: Decimal = Field(0, ge=0, description="进口增值税")
    pickup_fee: Decimal = Field(0, ge=0, description="提货费")
    freight: Decimal = Field(0, ge=0, description="运费")
    yard_fee: Decimal = Field(0, ge=0, description="场地费")
    cold_storage_fee: Decimal = Field(0, ge=0, description="冷藏费")
    clearance_service_fee: Decimal = Field(0, ge=0, description="报关服务费")
    gross_weight_kg: Optional[Decimal] = Field(None, ge=0, description="出关毛重(kg)")
    notes: Optional[str] = Field(None, description="备注")


class ImportFeeResponse(BaseModel):
    """统一进口费用响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    invoice_no: Optional[str] = None
    expense_date: date
    customs_broker_id: Optional[int] = None
    customs_broker_name: Optional[str] = None
    import_duty: Decimal
    import_vat: Decimal
    pickup_fee: Decimal
    freight: Decimal
    yard_fee: Decimal
    cold_storage_fee: Decimal
    clearance_service_fee: Decimal
    tax_total: Decimal
    clearance_total: Decimal
    grand_total: Decimal
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ImportFeeListItem(BaseModel):
    """进口费用列表项 (JOIN 视图)"""
    invoice_id: int
    invoice_no: Optional[str] = None
    expense_date: Optional[date] = None
    customs_broker_id: Optional[int] = None
    customs_broker_name: Optional[str] = None
    import_duty: Optional[Decimal] = None
    import_vat: Optional[Decimal] = None
    tax_total: Optional[Decimal] = None
    pickup_fee: Optional[Decimal] = None
    freight: Optional[Decimal] = None
    yard_fee: Optional[Decimal] = None
    cold_storage_fee: Optional[Decimal] = None
    clearance_service_fee: Optional[Decimal] = None
    clearance_total: Optional[Decimal] = None


# ==================== 批次采购总额 ====================

class BatchPurchaseTotalResponse(BaseModel):
    """批次采购总额响应"""
    batch_id: int
    batch_code: Optional[str] = None
    batch_name: Optional[str] = None
    total_usd: Decimal
    invoice_count: int
    invoices: List[dict] = []
