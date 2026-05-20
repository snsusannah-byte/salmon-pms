# ruff: noqa: F821
from decimal import Decimal
from app.models.enums import SalesStatus
from typing import List, Optional

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

class FinishedProductSale(Base, TimestampMixin):
    """成品销售"""
    __tablename__ = "finished_product_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_date: Mapped[Date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # 份数
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    scan_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    status: Mapped[SalesStatus] = mapped_column(Enum(SalesStatus), default=SalesStatus.PENDING)
    salesperson_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    # V3: 新增总重量（份数 × 每份重量(g) / 1000）
    total_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3), default=Decimal("0"))

    receipts: Mapped[List["FinishedProductReceipt"]] = relationship(
        "FinishedProductReceipt",
        foreign_keys="FinishedProductReceipt.sale_id",
        lazy="raise",
        cascade="all, delete-orphan",
    )
    aftersales_records: Mapped[List["FinishedProductAftersales"]] = relationship(
        "FinishedProductAftersales",
        foreign_keys="FinishedProductAftersales.sale_id",
        lazy="raise",
        cascade="all, delete-orphan",
    )
    items: Mapped[List["FinishedProductSaleItem"]] = relationship(
        "FinishedProductSaleItem",
        foreign_keys="FinishedProductSaleItem.sale_id",
        lazy="raise",
        cascade="all, delete-orphan",
    )
    return_orders: Mapped[List["ReturnOrder"]] = relationship(
        "ReturnOrder",
        foreign_keys="ReturnOrder.finished_product_sale_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )



class FinishedProductReceipt(Base, TimestampMixin):
    """成品销售收款记录"""
    __tablename__ = "finished_product_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("finished_product_sales.id"), nullable=False)
    receipt_date: Mapped[Date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50))
    bank_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"))
    reference_no: Mapped[Optional[str]] = mapped_column(String(100))
    notes: Mapped[Optional[str]] = mapped_column(Text)



class FinishedProductAftersales(Base, TimestampMixin):
    """成品销售售后记录"""
    __tablename__ = "finished_product_aftersales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("finished_product_sales.id"), nullable=False)
    record_date: Mapped[Date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(50))  # return, refund, discount, compensation
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[Optional[str]] = mapped_column(Text)


class FinishedProductSaleV2(Base, TimestampMixin):
    """成品销售记录 (v2 - 迁移自 salmon-finance-v4)"""
    __tablename__ = "finished_product_sales_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_no: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    sale_type: Mapped[Optional[str]] = mapped_column(String(20), default="whole_fish")
    source_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    customer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    salesperson: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    weight: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    sale_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    scan_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    rounding: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    after_sales_adjustment: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    net_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    paid: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    products: Mapped[List["FinishedSaleProductV2"]] = relationship(
        "FinishedSaleProductV2",
        back_populates="sale",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class FinishedSaleProductV2(Base, TimestampMixin):
    """成品销售产品明细 (v2)"""
    __tablename__ = "finished_sale_products_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("finished_product_sales_v2.id"), nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    product_spec: Mapped[str] = mapped_column(String(100), nullable=False)
    factory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    box_count: Mapped[int] = mapped_column(Integer, default=0)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=Decimal("0"))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    after_sales_adjustment: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))

    sale: Mapped["FinishedProductSaleV2"] = relationship("FinishedProductSaleV2", back_populates="products")



