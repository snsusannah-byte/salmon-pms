from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import CompanyType, CustomerCategory, SupplierCategory


class BankAccountItem(BaseModel):
    """主体收款/银行账户信息"""
    id: int | None = Field(None, description="ID，新建不传或传 null")
    account_name: str = Field(..., max_length=100, description="账户名称/户名")
    bank_name: str = Field(..., max_length=200, description="开户行")
    account_number: str = Field(..., max_length=100, description="银行账号")
    currency: str = Field("CNY", max_length=10, description="币种")
    is_active: bool = Field(True, description="是否启用")
    notes: str | None = Field(None, description="备注")

# 主体业务角色分类
UPSTREAM_TYPES = {"processing_plant", "fish_farm", "exporter"}  # 上游溯源（不参与应收应付）
BUSINESS_PARTNER_TYPES = {"supplier", "customer", "customs_broker", "logistics", "internal"}  # 业务往来（参与应收应付）


def get_business_role(company_type: str) -> str:
    """根据主体类型返回业务角色：upstream(上游溯源) 或 business_partner(业务往来)"""
    if company_type in UPSTREAM_TYPES:
        return "upstream"
    return "business_partner"


class CompanyBase(BaseModel):
    """主体基础信息"""
    name: str = Field(..., max_length=200, description="主体名称")
    chinese_name: str | None = Field(None, max_length=200, description="中文名称（备用）")
    company_full_name: str | None = Field(None, max_length=200, description="公司全称")
    brands: str | None = Field(None, max_length=500, description="旗下品牌（逗号分隔）")
    type: CompanyType = Field(..., description="主体类型")
    code: str | None = Field(None, max_length=50, description="EU注册号（加工厂对外的短号）")
    cooperation_date: str | None = Field(None, description="合作日期")
    contact_person: str | None = Field(None, max_length=100, description="联系人")
    phone: str | None = Field(None, max_length=50, description="联系电话")
    email: str | None = Field(None, max_length=100, description="邮箱")
    address: str | None = Field(None, description="地址")
    registration_code: str | None = Field(None, max_length=100, description="CN海关准入")
    enterprise_registration_no: str | None = Field(None, max_length=100, description="养殖GGN")
    coc_cert_no: str | None = Field(None, max_length=100, description="监管链COC")
    farming_area: str | None = Field("FAO 27", max_length=100, description="养殖区")
    website: str | None = Field(None, max_length=255, description="网址")
    bank_name: str | None = Field(None, max_length=200, description="开户行")
    bank_account: str | None = Field(None, max_length=100, description="银行账号")
    payee: str | None = Field(None, max_length=200, description="收款人")
    credit_limit: Decimal | None = Field(None, ge=0, description="信用额度")
    # 客户专用字段
    logistics_info: str | None = Field(None, description="物流信息")
    salesperson_id: int | None = Field(None, description="业务员ID")
    customer_category: CustomerCategory | None = Field(None, description="客户分类: wholesaler/distributor/retailer/platform/group_buying")
    customer_level: str | None = Field(None, max_length=20, description="客户等级: normal/vip/wholesale/bulk")
    supplier_category: SupplierCategory | None = Field(None, description="供应商分类: raw_material/material_supply/customs_broker/service_provider")
    prepaid_balance: Decimal | None = Field(Decimal("0"), ge=0, description="客户预付款余额")
    customer_type: str | None = Field(None, description="客户类型: normal/internal_processor/oem")
    is_internal: bool | None = Field(False, description="是否内部客户（加工厂/代工方）")
    is_active: bool | None = Field(True, description="是否启用")
    notes: str | None = Field(None, description="备注")
    bank_accounts: list[BankAccountItem] | None = Field(None, description="收款账户列表")

    @field_validator("website", mode="before")
    @classmethod
    def validate_website(cls, v):
        if v is None or v == "":
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("网址必须以 http:// 或 https:// 开头")
        return v

    @field_validator("cooperation_date", mode="before")
    @classmethod
    def validate_cooperation_date(cls, v):
        if v is None:
            return None
        if isinstance(v, date):
            return v.isoformat()
        return v


class CompanyCreate(CompanyBase):
    """创建主体请求"""
    pass


class CompanyUpdate(BaseModel):
    """更新主体请求"""
    name: str | None = Field(None, max_length=200)
    chinese_name: str | None = Field(None, max_length=200)
    company_full_name: str | None = Field(None, max_length=200)
    brands: str | None = Field(None, max_length=500)
    type: CompanyType | None = None
    code: str | None = Field(None, max_length=50)
    cooperation_date: str | None = None
    contact_person: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=100)
    address: str | None = None
    registration_code: str | None = Field(None, max_length=100)
    enterprise_registration_no: str | None = Field(None, max_length=100)
    coc_cert_no: str | None = Field(None, max_length=100)
    farming_area: str | None = Field(None, max_length=100)
    website: str | None = Field(None, max_length=255)
    bank_name: str | None = Field(None, max_length=200)
    bank_account: str | None = Field(None, max_length=100)
    payee: str | None = Field(None, max_length=200)
    currency: str | None = Field("CNY", max_length=10, description="币种: CNY/USD/EUR")
    credit_limit: Decimal | None = Field(None, ge=0)
    logistics_info: str | None = Field(None)
    salesperson_id: int | None = Field(None)
    customer_category: CustomerCategory | None = None
    customer_level: str | None = Field(None, max_length=20)
    supplier_category: SupplierCategory | None = None
    is_active: bool | None = None
    notes: str | None = None
    bank_accounts: list[BankAccountItem] | None = Field(None, description="收款账户列表")


class CompanyResponse(CompanyBase):
    """主体响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    salesperson_name: str | None = Field(None, description="业务员名称")
    business_role: str = Field(default="business_partner", description="业务角色：upstream(上游溯源) / business_partner(业务往来)")
    payable_usd: Decimal | None = Field(None, description="应付款(USD)")
    payable_cny: Decimal | None = Field(None, description="应付款(CNY)")
    created_at: datetime
    updated_at: datetime
    bank_accounts: list[BankAccountItem] = Field(default_factory=list, description="收款账户列表")


class CompanyListResponse(BaseModel):
    """主体列表响应"""
    total: int
    items: list[CompanyResponse]
    skip: int
    limit: int


# ==================== 业务员管理 ====================

class SalespersonBase(BaseModel):
    """业务员基础"""
    name: str = Field(..., max_length=100, description="姓名")
    phone: str | None = Field(None, max_length=50, description="电话")
    email: str | None = Field(None, max_length=100, description="邮箱")
    commission_type: str = Field("per_kg", description="提成方式: per_kg=按公斤; percentage_of_receipt=按实收金额比例")
    commission_rate: Decimal = Field(Decimal("0"), ge=0, description="提成率: per_kg 为元/kg; percentage_of_receipt 为千分比(‰)")
    is_active: bool = Field(True, description="是否在职")
    notes: str | None = Field(None, description="备注")


class SalespersonCreate(SalespersonBase):
    """创建业务员"""
    pass


class SalespersonUpdate(BaseModel):
    """更新业务员"""
    name: str | None = Field(None, max_length=100)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=100)
    commission_type: str | None = Field(None, description="提成方式: per_kg=按公斤; percentage_of_receipt=按实收金额比例")
    commission_rate: Decimal | None = Field(None, ge=0, description="提成率: per_kg 为元/kg; percentage_of_receipt 为千分比(‰)")
    is_active: bool | None = None
    notes: str | None = None


class SalespersonResponse(SalespersonBase):
    """业务员响应"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class CommissionResponse(BaseModel):
    """提成记录响应"""
    id: int
    salesperson_id: int
    salesperson_name: str | None = None
    sale_id: int
    sale_date: str | None = None
    customer_name: str | None = None
    sale_amount: Decimal
    weight_kg: Decimal
    received_amount: Decimal = Decimal("0")
    commission_type: str = "per_kg"
    commission_rate: Decimal
    commission_amount: Decimal
    status: str
    paid_date: str | None = None
    notes: str | None = None
