from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import ExchangeStatus, InvoiceStatus


class InvoiceProductBase(BaseModel):
    """产品明细基础"""
    product_name: str = Field(..., max_length=100, description="产品名称")
    product_spec: str = Field(..., max_length=100, description="规格")
    box_count: int = Field(..., ge=1, description="箱数")
    net_weight_kg: Decimal = Field(..., ge=0, description="净重(kg)")
    unit_price: Decimal = Field(..., ge=0, description="单价(USD)")
    total_amount: Decimal = Field(..., ge=0, description="总金额(USD)")
    notes: str | None = Field(None, description="备注")


class InvoiceProductCreate(InvoiceProductBase):
    """创建产品明细"""
    pass


class InvoiceProductUpdate(BaseModel):
    """更新产品明细"""
    product_name: str | None = Field(None, max_length=100)
    product_spec: str | None = Field(None, max_length=100)
    box_count: int | None = Field(None, ge=1)
    net_weight_kg: Decimal | None = Field(None, ge=0)
    unit_price: Decimal | None = Field(None, ge=0)
    total_amount: Decimal | None = Field(None, ge=0)
    notes: str | None = None


class InvoiceProductResponse(InvoiceProductBase):
    """产品明细响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    invoice_id: int
    created_at: datetime
    updated_at: datetime


class InvoiceBase(BaseModel):
    """发票基础信息"""
    invoice_no: str = Field(..., max_length=50, description="发票编号")
    invoice_date: date = Field(..., description="发票日期")
    kill_date: date | None = Field(None, description="宰杀日期")
    arrival_date: date | None = Field(None, description="到货日期")
    
    processing_plant_id: int | None = Field(None, description="加工厂ID")
    fish_farm_id: int | None = Field(None, description="渔场ID")
    exporter_id: int | None = Field(None, description="出口商ID")
    supplier_id: int | None = Field(None, description="供应商ID")
    importer_id: int | None = Field(None, description="进口商ID")
    
    total_amount_usd: Decimal | None = Field(None, ge=0, description="总金额(USD)")
    total_boxes: int = Field(0, ge=0, description="总箱数")
    total_weight_kg: Decimal = Field(Decimal("0"), ge=0, description="总净重(kg)")
    
    # 物流与证书信息
    awb_no: str | None = Field(None, max_length=50, description="AWB航空运单号")
    gross_weight_kg: Decimal | None = Field(None, ge=0, description="毛重(kg)")
    eta: datetime | None = Field(None, description="ETA预计到达")
    departure_date: date | None = Field(None, description="发运时间")
    flight_info: str | None = Field(None, max_length=100, description="航班信息")
    origin_certificate: str | None = Field(None, max_length=100, description="原产地证书")
    inspection_certificate: str | None = Field(None, max_length=100, description="检验检疫证书")
    
    # 主从发票关系（V8.3新增）
    parent_invoice_id: int | None = Field(None, description="主票ID（从票关联主票）")
    is_master: bool = Field(False, description="是否主票（AWB级别费用录入方）")
    
    # 报关状态（清关流程）
    customs_status: InvoiceStatus | None = Field(InvoiceStatus.PENDING_SHIPMENT, description="报关状态")
    # 购汇状态
    exchange_status: ExchangeStatus | None = Field(ExchangeStatus.NOT_EXCHANGED, description="购汇状态")
    notes: str | None = Field(None, description="备注")

    @field_validator("customs_status", mode="before")
    @classmethod
    def normalize_customs_status(cls, v):
        """同时接受大写(name)和小写(value)"""
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("pending_shipment", "in_transit", "pending_customs", "customs_processing", "cleared", "picked_up"):
                return v_lower
        return v

    @field_validator("exchange_status", mode="before")
    @classmethod
    def normalize_exchange_status(cls, v):
        """同时接受大写(name)和小写(value)"""
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("not_exchanged", "partial", "completed"):
                return v_lower
        return v


class InvoiceCreate(InvoiceBase):
    """创建发票请求"""
    products: list[InvoiceProductCreate] | None = Field(None, description="产品明细列表")


class InvoiceUpdate(BaseModel):
    """更新发票请求"""
    invoice_no: str | None = Field(None, max_length=50)
    invoice_date: date | None = None
    kill_date: date | None = None
    arrival_date: date | None = None
    
    processing_plant_id: int | None = None
    fish_farm_id: int | None = None
    exporter_id: int | None = None
    supplier_id: int | None = None
    importer_id: int | None = None
    
    total_amount_usd: Decimal | None = Field(None, ge=0)
    total_boxes: int | None = Field(None, ge=0)
    total_weight_kg: Decimal | None = Field(None, ge=0)
    
    # 物流与证书信息
    awb_no: str | None = Field(None, max_length=50)
    gross_weight_kg: Decimal | None = Field(None, ge=0)
    eta: datetime | None = None
    departure_date: date | None = None
    flight_info: str | None = Field(None, max_length=100)
    origin_certificate: str | None = Field(None, max_length=100)
    inspection_certificate: str | None = Field(None, max_length=100)
    
    customs_status: InvoiceStatus | None = None
    exchange_status: ExchangeStatus | None = None
    is_locked: bool | None = None
    
    # 主从发票关系（V8.3新增）
    parent_invoice_id: int | None = Field(None, description="主票ID")
    is_master: bool | None = Field(None, description="是否主票")
    
    notes: str | None = None
    
    # 产品明细（编辑时可选）
    products: list[InvoiceProductCreate] | None = Field(None, description="产品明细列表（编辑时覆盖旧数据）")

    @field_validator("customs_status", mode="before")
    @classmethod
    def normalize_customs_status(cls, v):
        """同时接受大写(name)和小写(value)"""
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("pending_shipment", "in_transit", "pending_customs", "customs_processing", "cleared", "picked_up"):
                return v_lower
        return v

    @field_validator("exchange_status", mode="before")
    @classmethod
    def normalize_exchange_status(cls, v):
        """同时接受大写(name)和小写(value)"""
        if isinstance(v, str):
            v_lower = v.lower()
            if v_lower in ("not_exchanged", "partial", "completed"):
                return v_lower
        return v


class InvoiceResponse(InvoiceBase):
    """发票响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    
    # 关联信息
    processing_plant_name: str | None = None
    processing_plant_code: str | None = None
    fish_farm_name: str | None = None
    fish_farm_code: str | None = None
    exporter_name: str | None = None
    exporter_code: str | None = None
    supplier_name: str | None = None
    supplier_code: str | None = None
    importer_name: str | None = None
    importer_code: str | None = None
    
    # 主从发票关系（V8.3新增）
    parent_invoice_id: int | None = None
    is_master: bool = False
    parent_invoice_no: str | None = None  # 主票发票号
    sub_invoices: list[dict] = Field(default_factory=list)  # 子票列表（仅主票返回）
    
    # 产品明细 - 使用普通列表避免ORM映射问题
    products: list[InvoiceProductResponse] = []
    
    # 产品净重汇总（从明细计算，用于列表页显示真正的净重）
    net_weight_kg_sum: Decimal | None = Field(None, description="产品明细净重汇总(kg)")


class InvoiceListResponse(BaseModel):
    """发票列表响应"""
    total: int
    items: list[InvoiceResponse]
    skip: int
    limit: int


class InvoiceSummary(BaseModel):
    """发票汇总统计"""
    total_count: int
    total_amount_usd: Decimal
    this_month_count: int
    this_month_amount: Decimal
    pending_exchange_count: int
    pending_exchange_amount: Decimal
