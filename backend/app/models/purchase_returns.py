"""采购售后/退货模块模型 — 三文鱼PMS

参考销售退货单（ReturnOrder）结构，但方向相反：
- 销售退货：退给客户
- 采购售后：退给供应商 / 抵扣货款
"""
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
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


class PurchaseReturnStatus(StrEnum):
    """采购售后单状态"""
    DRAFT = "draft"                         # 草稿
    PENDING_APPROVAL = "pending_approval"   # 待审批
    APPROVED = "approved"                   # 已批准
    COMPLETED = "completed"                 # 已完成
    REJECTED = "rejected"                   # 已拒绝
    CANCELLED = "cancelled"                 # 已取消


class PurchaseRefundMethod(StrEnum):
    """采购退款方式"""
    DEDUCT_PAYABLE = "deduct_payable"       # 抵扣应付款（最常用）
    DIRECT_REFUND = "direct_refund"         # 直接退款（供应商退钱）
    DEFERRED = "deferred"                   # 挂账/延期处理


class PurchaseReturnAttachmentType(StrEnum):
    """附件类型"""
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


class PurchaseReturnOrder(Base, TimestampMixin):
    """采购售后/退货单

    关联 purchase_orders_v2（整鱼/以销定采采购单）或 material_purchase_orders（辅料采购单）
    """
    __tablename__ = "purchase_return_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    # 关联采购单（二选一）
    purchase_order_type: Mapped[str] = mapped_column(String(20), nullable=False)  # purchase_v2 / material_purchase
    purchase_order_v2_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_orders_v2.id"), nullable=True)
    material_purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("material_purchase_orders.id"), nullable=True)

    # 基本信息
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    supplier_name: Mapped[str | None] = mapped_column(String(200))

    # 售后汇总
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    # 退款信息
    refund_method: Mapped[PurchaseRefundMethod | None] = mapped_column(Enum(PurchaseRefundMethod), nullable=True)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    refund_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)

    # 状态
    status: Mapped[PurchaseReturnStatus] = mapped_column(Enum(PurchaseReturnStatus), default=PurchaseReturnStatus.DRAFT)

    # 问题描述
    problem_description: Mapped[str | None] = mapped_column(Text)
    supplier_feedback: Mapped[str | None] = mapped_column(Text)  # 供应商反馈
    internal_notes: Mapped[str | None] = mapped_column(Text)

    # 处理人
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 关联
    items: Mapped[list["PurchaseReturnItem"]] = relationship(
        "PurchaseReturnItem",
        back_populates="return_order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list["PurchaseReturnAttachment"]] = relationship(
        "PurchaseReturnAttachment",
        back_populates="return_order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class PurchaseReturnItem(Base, TimestampMixin):
    """采购售后明细

    核心字段：重量(kg)、单价、金额、备注/问题描述
    单价自动从采购单明细读取，金额 = 重量 × 单价
    """
    __tablename__ = "purchase_return_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_return_orders.id"), nullable=False)

    # 售后明细
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)  # 明细备注/问题描述

    # 关联采购明细（可选，用于追溯）
    purchase_order_product_v2_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_order_products_v2.id"), nullable=True
    )
    material_purchase_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("material_purchase_items.id"), nullable=True
    )

    return_order: Mapped["PurchaseReturnOrder"] = relationship("PurchaseReturnOrder", back_populates="items")


class PurchaseReturnAttachment(Base, TimestampMixin):
    """采购售后附件"""
    __tablename__ = "purchase_return_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_return_orders.id"), nullable=False)

    file_type: Mapped[PurchaseReturnAttachmentType] = mapped_column(Enum(PurchaseReturnAttachmentType), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    return_order: Mapped["PurchaseReturnOrder"] = relationship("PurchaseReturnOrder", back_populates="attachments")
