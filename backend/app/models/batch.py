# ruff: noqa: F821
from decimal import Decimal
from app.models.enums import BatchStatus
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

class Batch(Base, TimestampMixin):
    """批次管理"""
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # 批次编号: YYYYMMDD-NNN
    batch_name: Mapped[str] = mapped_column(String(100), nullable=False)
    batch_date: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[BatchStatus] = mapped_column(Enum(BatchStatus), default=BatchStatus.OPEN)
    total_amount_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    total_boxes: Mapped[int] = mapped_column(Integer, default=0)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    batch_invoices: Mapped[List["BatchInvoice"]] = relationship("BatchInvoice", back_populates="batch", lazy="raise", cascade="all, delete-orphan")



class BatchInvoice(Base, TimestampMixin):
    """批次-发票关联"""
    __tablename__ = "batch_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    batch: Mapped["Batch"] = relationship("Batch", back_populates="batch_invoices", lazy="raise")


# ==================== 财务层 ====================


class ExchangeRecord(Base, TimestampMixin):
    """购汇记录（1张发票支持N条，新增批次关联）"""
    __tablename__ = "exchange_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("import_invoices.id"), nullable=True)
    batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("batches.id"), nullable=True)
    exchange_date: Mapped[Date] = mapped_column(Date, nullable=False)
    amount_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    amount_cny: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    fee_cny: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    bank_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    related_invoice_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    exchange_no: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)


