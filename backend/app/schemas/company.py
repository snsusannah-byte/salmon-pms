from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import CompanyType, CustomerCategory

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
    chinese_name: Optional[str] = Field(None, max_length=200, description="中文名称（备用）")
    company_full_name: Optional[str] = Field(None, max_length=200, description="公司全称")
    brands: Optional[str] = Field(None, max_length=500, description="旗下品牌（逗号分隔）")
    type: CompanyType = Field(..., description="主体类型")
    code: Optional[str] = Field(None, max_length=50, description="EU注册号（加工厂对外的短号）")
    cooperation_date: Optional[str] = Field(None, description="合作日期")
    contact_person: Optional[str] = Field(None, max_length=100, description="联系人")
    phone: Optional[str] = Field(None, max_length=50, description="联系电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    address: Optional[str] = Field(None, description="地址")
    registration_code: Optional[str] = Field(None, max_length=100, description="CN海关准入")
    enterprise_registration_no: Optional[str] = Field(None, max_length=100, description="养殖GGN")
    coc_cert_no: Optional[str] = Field(None, max_length=100, description="监管链COC")
    farming_area: Optional[str] = Field("FAO 27", max_length=100, description="养殖区")
    website: Optional[str] = Field(None, max_length=255, description="网址")
    bank_name: Optional[str] = Field(None, max_length=200, description="开户行")
    bank_account: Optional[str] = Field(None, max_length=100, description="银行账号")
    payee: Optional[str] = Field(None, max_length=200, description="收款人")
    credit_limit: Optional[Decimal] = Field(None, ge=0, description="信用额度")
    # 客户专用字段
    logistics_info: Optional[str] = Field(None, description="物流信息")
    salesperson_id: Optional[int] = Field(None, description="业务员ID")
    customer_category: Optional[CustomerCategory] = Field(None, description="客户分类: wholesaler/distributor/retailer/platform/group_buying")
    is_active: Optional[bool] = Field(True, description="是否启用")
    notes: Optional[str] = Field(None, description="备注")

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
    name: Optional[str] = Field(None, max_length=200)
    chinese_name: Optional[str] = Field(None, max_length=200)
    company_full_name: Optional[str] = Field(None, max_length=200)
    brands: Optional[str] = Field(None, max_length=500)
    type: Optional[CompanyType] = None
    code: Optional[str] = Field(None, max_length=50)
    cooperation_date: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    address: Optional[str] = None
    registration_code: Optional[str] = Field(None, max_length=100)
    enterprise_registration_no: Optional[str] = Field(None, max_length=100)
    coc_cert_no: Optional[str] = Field(None, max_length=100)
    farming_area: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=255)
    bank_name: Optional[str] = Field(None, max_length=200)
    bank_account: Optional[str] = Field(None, max_length=100)
    payee: Optional[str] = Field(None, max_length=200)
    currency: Optional[str] = Field("CNY", max_length=10, description="币种: CNY/USD/EUR")
    credit_limit: Optional[Decimal] = Field(None, ge=0)
    logistics_info: Optional[str] = Field(None)
    salesperson_id: Optional[int] = Field(None)
    customer_category: Optional[CustomerCategory] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class CompanyResponse(CompanyBase):
    """主体响应"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    salesperson_name: Optional[str] = Field(None, description="业务员名称")
    business_role: str = Field(default="business_partner", description="业务角色：upstream(上游溯源) / business_partner(业务往来)")
    payable_usd: Optional[float] = Field(None, description="应付款(USD)")
    payable_cny: Optional[float] = Field(None, description="应付款(CNY)")
    created_at: datetime
    updated_at: datetime


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
    phone: Optional[str] = Field(None, max_length=50, description="电话")
    email: Optional[str] = Field(None, max_length=100, description="邮箱")
    commission_rate: Decimal = Field(Decimal("0"), ge=0, description="默认提成单价 元/kg")
    is_active: bool = Field(True, description="是否在职")
    notes: Optional[str] = Field(None, description="备注")


class SalespersonCreate(SalespersonBase):
    """创建业务员"""
    pass


class SalespersonUpdate(BaseModel):
    """更新业务员"""
    name: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    commission_rate: Optional[Decimal] = Field(None, ge=0, description="提成单价 元/kg")
    is_active: Optional[bool] = None
    notes: Optional[str] = None


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
    salesperson_name: Optional[str] = None
    sale_id: int
    sale_date: Optional[str] = None
    customer_name: Optional[str] = None
    sale_amount: float
    weight_kg: float
    commission_rate: float
    commission_amount: float
    status: str
    paid_date: Optional[str] = None
    notes: Optional[str] = None
