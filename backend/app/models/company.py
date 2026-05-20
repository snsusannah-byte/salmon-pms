# ruff: noqa: F821
from decimal import Decimal
from app.models.enums import CompanyType, CustomerCategory
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

class Company(Base, TimestampMixin):
    """主体管理：加工厂/渔场/出口商/供应商/客户/报关行/物流/内部"""
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    chinese_name: Mapped[Optional[str]] = mapped_column(String(200))
    company_full_name: Mapped[Optional[str]] = mapped_column(String(200))
    brands: Mapped[Optional[str]] = mapped_column(String(500))
    type: Mapped[CompanyType] = mapped_column(Enum(CompanyType, values_callable=lambda obj: [e.value for e in obj]), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    cooperation_date: Mapped[Optional[Date]] = mapped_column(Date)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    registration_code: Mapped[Optional[str]] = mapped_column(String(100))  # CN海关准入号
    enterprise_registration_no: Mapped[Optional[str]] = mapped_column(String(100))  # 养殖GGN（GlobalGAP Number）
    coc_cert_no: Mapped[Optional[str]] = mapped_column(String(100))  # 监管链COC认证号
    farming_area: Mapped[Optional[str]] = mapped_column(String(100), default="FAO 27")
    website: Mapped[Optional[str]] = mapped_column(String(255))
    bank_name: Mapped[Optional[str]] = mapped_column(String(200))
    bank_account: Mapped[Optional[str]] = mapped_column(String(100))
    payee: Mapped[Optional[str]] = mapped_column(String(200))  # 收款人
    currency: Mapped[str] = mapped_column(String(10), default="CNY")  # 币种: CNY/USD/EUR
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    # 客户专用字段
    logistics_info: Mapped[Optional[str]] = mapped_column(Text)  # 物流信息
    salesperson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))  # 业务员
    customer_category: Mapped[Optional[CustomerCategory]] = mapped_column(Enum(CustomerCategory))  # 客户分类
    supplier_category: Mapped[Optional[str]] = mapped_column(String(50))  # 供应商分类: raw_material/material_supply/customs_broker/service_provider
    # 客户类型细分（用于区分内部加工厂和普通客户）
    customer_type: Mapped[Optional[str]] = mapped_column(String(20))  # normal(普通客户), internal_processor(内部加工厂), oem(代工方)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否内部客户（加工厂/代工方）
    # 客户预付余额（仅 customer 类型有效）
    prepaid_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    salesperson: Mapped["User"] = relationship("User", foreign_keys=[salesperson_id], lazy="raise")



class Salesperson(Base, TimestampMixin):
    """业务员管理"""
    __tablename__ = "salespersons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0"))  # 默认提成单价 元/kg
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)



class CommissionRecord(Base, TimestampMixin):
    """提成记录"""
    __tablename__ = "commission_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    salesperson_id: Mapped[int] = mapped_column(ForeignKey("salespersons.id"), nullable=False)
    sale_id: Mapped[int] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=False)
    sale_date: Mapped[Date] = mapped_column(Date, nullable=False)
    sale_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # 销售金额
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=Decimal("0"))  # 销售重量(kg)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)  # 实际提成单价 元/kg
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # 提成金额 = weight_kg * rate
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / paid
    paid_date: Mapped[Optional[Date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    salesperson: Mapped["Salesperson"] = relationship("Salesperson", lazy="raise")



class BankAccount(Base, TimestampMixin):
    """银行账户管理"""
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)  # 编号
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    type: Mapped[str] = mapped_column(String(20), default="public")  # public, private, scan
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)


