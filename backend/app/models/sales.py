# ruff: noqa: F821
from decimal import Decimal
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
from app.models.enums import SalesStatus


class WholeFishSale(Base, TimestampMixin):
    """整鱼销售"""
    __tablename__ = "whole_fish_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_no: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    sale_date: Mapped[Date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    spec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    box_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    scan_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    rounding_adjustment: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    after_sales_adjustment: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    status: Mapped[SalesStatus] = mapped_column(Enum(SalesStatus), default=SalesStatus.PENDING)
    salesperson_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    is_internal_sale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否内部销售（加工厂流转）
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

    receipts: Mapped[list["SalesReceipt"]] = relationship("SalesReceipt", back_populates="sale", lazy="selectin", cascade="all, delete-orphan")
    aftersales: Mapped[list["AftersalesRecord"]] = relationship("AftersalesRecord", back_populates="sale", lazy="selectin", cascade="all, delete-orphan")
    items: Mapped[list["WholeFishSaleItem"]] = relationship("WholeFishSaleItem", back_populates="sale", lazy="selectin", cascade="all, delete-orphan")
    return_orders: Mapped[list["ReturnOrder"]] = relationship(
        "ReturnOrder",
        foreign_keys="ReturnOrder.whole_fish_sale_id",
        lazy="selectin",
        cascade="all, delete-orphan",
    )



class WholeFishSaleItem(Base, TimestampMixin):
    """整鱼销售子项（支持多条规格明细）"""
    __tablename__ = "whole_fish_sale_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=False)
    spec: Mapped[str] = mapped_column(String(100), nullable=False)  # 规格
    box_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 箱数
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)  # 重量(kg)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)  # 单价
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # 金额 = weight_kg * unit_price
    sort_order: Mapped[int] = mapped_column(Integer, default=0)  # 排序
    notes: Mapped[str | None] = mapped_column(Text)

    sale: Mapped["WholeFishSale"] = relationship("WholeFishSale", back_populates="items", lazy="raise")



class SalesReceipt(Base, TimestampMixin):
    """收款记录"""
    __tablename__ = "sales_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=False)
    receipt_date: Mapped[Date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50))  # cash, transfer, check, scan
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"))
    reference_no: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transaction_records.id"), nullable=True)

    sale: Mapped["WholeFishSale"] = relationship("WholeFishSale", back_populates="receipts")
    transaction: Mapped[Optional["TransactionRecord"]] = relationship("TransactionRecord", foreign_keys=[transaction_id])



class AftersalesRecord(Base, TimestampMixin):
    """售后记录"""
    __tablename__ = "aftersales_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=False)
    record_date: Mapped[Date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(50))  # return, refund, discount, compensation
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    notes: Mapped[str | None] = mapped_column(Text)

    sale: Mapped["WholeFishSale"] = relationship("WholeFishSale", back_populates="aftersales")


# ==================== 统一交易流水 ====================

