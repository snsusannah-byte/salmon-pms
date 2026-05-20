# ruff: noqa: F821
from decimal import Decimal
from app.models.enums import InvoiceStatus, ExchangeStatus
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

class ImportInvoice(Base, TimestampMixin):
    """进口发票（核心表，保持原有编号）"""
    __tablename__ = "import_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_no: Mapped[str] = mapped_column(String(100), nullable=False)       # 发票编号
    invoice_date: Mapped[Date] = mapped_column(Date, nullable=False)           # 发票日期
    kill_date: Mapped[Optional[Date]] = mapped_column(Date)
    arrival_date: Mapped[Optional[Date]] = mapped_column(Date)
    
    processing_plant_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    fish_farm_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"))
    exporter_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)  # 供应商/收款方
    
    total_amount_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_boxes: Mapped[int] = mapped_column(Integer, default=0)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    
    # 物流与证书信息
    awb_no: Mapped[Optional[str]] = mapped_column(String(50))  # AWB航空运单号
    gross_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 毛重(kg)
    eta: Mapped[Optional[DateTime]] = mapped_column(DateTime)  # ETA预计到达
    departure_date: Mapped[Optional[Date]] = mapped_column(Date)  # 发运时间
    flight_info: Mapped[Optional[str]] = mapped_column(String(100))  # 航班信息
    origin_certificate: Mapped[Optional[str]] = mapped_column(String(100))  # 原产地证书
    inspection_certificate: Mapped[Optional[str]] = mapped_column(String(100))  # 检验检疫证书
    
    # 主从发票关系（V8.3新增）
    parent_invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("import_invoices.id"), nullable=True)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否主票（AWB级别费用录入方）
    
    # 成本相关（V8.2新增）
    unit_price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))  # 采购单价(USD)
    estimated_exchange_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6))  # 预估汇率
    estimated_cost_cny: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))  # 预估成本(CNY)
    actual_cost_cny: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))  # 实际成本(CNY)
    
    # 报关状态（清关流程）
    customs_status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING_CUSTOMS)
    # 购汇状态
    exchange_status: Mapped[ExchangeStatus] = mapped_column(Enum(ExchangeStatus), default=ExchangeStatus.NOT_EXCHANGED)
    # 是否锁定（批次结算后锁定）
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    processing_plant: Mapped["Company"] = relationship("Company", foreign_keys=[processing_plant_id])
    fish_farm: Mapped["Company"] = relationship("Company", foreign_keys=[fish_farm_id])
    exporter: Mapped["Company"] = relationship("Company", foreign_keys=[exporter_id])
    supplier: Mapped["Company"] = relationship("Company", foreign_keys=[supplier_id])
    products: Mapped[List["InvoiceProduct"]] = relationship("InvoiceProduct", back_populates="invoice", lazy="raise", uselist=True, cascade="all, delete-orphan")
    # 主从关系
    parent_invoice: Mapped[Optional["ImportInvoice"]] = relationship("ImportInvoice", remote_side=[id], foreign_keys=[parent_invoice_id], lazy="raise")
    sub_invoices: Mapped[List["ImportInvoice"]] = relationship("ImportInvoice", foreign_keys=[parent_invoice_id], lazy="raise", overlaps="parent_invoice")



class Shipment(Base, TimestampMixin):
    """发货批次（物流层）"""
    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shipment_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    shipment_date: Mapped[Date] = mapped_column(Date, nullable=False)
    logistics_company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    container_no: Mapped[Optional[str]] = mapped_column(String(50))
    vessel_name: Mapped[Optional[str]] = mapped_column(String(100))
    departure_port: Mapped[Optional[str]] = mapped_column(String(100))
    arrival_port: Mapped[Optional[str]] = mapped_column(String(100))
    eta: Mapped[Optional[Date]] = mapped_column(Date)
    ata: Mapped[Optional[Date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(50), default="in_transit")
    notes: Mapped[Optional[str]] = mapped_column(Text)



class ImportTax(Base, TimestampMixin):
    """进口税费"""
    __tablename__ = "import_taxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    tax_date: Mapped[Date] = mapped_column(Date, nullable=False)
    import_duty: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    import_vat: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    consumption_tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    other_taxes: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)



class ClearanceCost(Base, TimestampMixin):
    """清关运费"""
    __tablename__ = "clearance_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    cost_date: Mapped[Date] = mapped_column(Date, nullable=False)
    customs_broker_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True)  # 报关行ID
    customs_broker: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 报关行名称（冗余）
    gross_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 3), nullable=True)  # 海关出关毛重(kg)
    clearance_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    freight_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    inspection_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    quarantine_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    other_costs: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    customs_broker_company: Mapped[Optional["Company"]] = relationship("Company", foreign_keys=[customs_broker_id], lazy="raise")


# ==================== 销售层 ====================

