"""
退货模块模型 — 三文鱼PMS
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional, List

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# ==================== 枚举定义 ====================

class ReturnReason(str, PyEnum):
    """退货原因"""
    QUALITY_ISSUE = "quality_issue"           # 质量问题（变质/异味/色泽异常）
    LOGISTICS_DAMAGE = "logistics_damage"     # 物流损坏（包装破损/挤压）
    SPEC_MISMATCH = "spec_mismatch"         # 规格不符（大小/重量不达标）
    TEMPERATURE_ISSUE = "temperature_issue" # 温控问题（解冻/温度不达标）
    FOREIGN_MATTER = "foreign_matter"         # 异物混入
    CUSTOMER_REASON = "customer_reason"     # 客户原因（订单错误/临时取消）
    EXPIRED = "expired"                     # 临期/过期
    OTHER = "other"                         # 其他


class ReturnStatus(str, PyEnum):
    """退货单状态（简化版）"""
    DRAFT = "draft"                         # 草稿
    PENDING_APPROVAL = "pending_approval"   # 待审批
    APPROVED = "approved"                   # 已批准（可执行退款）
    COMPLETED = "completed"                 # 已完成
    REJECTED = "rejected"                   # 已拒绝
    CANCELLED = "cancelled"                 # 已取消


class RefundMethod(str, PyEnum):
    """退款方式"""
    DIRECT_REFUND = "direct_refund"         # 直接退款（银行转账/扫码）
    BALANCE_DEDUCTION = "balance_deduction" # 抵扣货款
    PREPAYMENT = "prepayment"               # 转为预付款
    DEFERRED = "deferred"                   # 挂账/延期处理


class ReturnAttachmentType(str, PyEnum):
    """附件类型"""
    IMAGE = "image"                         # 图片
    VIDEO = "video"                         # 视频
    DOCUMENT = "document"                   # 文档


# ==================== 模型定义 ====================

class ReturnOrder(Base, TimestampMixin):
    """退货单（统一整鱼+成品销售退货）"""
    __tablename__ = "return_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_no: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)

    # 关联销售单（二选一）
    sale_type: Mapped[str] = mapped_column(String(20), nullable=False)  # whole_fish / finished_product
    whole_fish_sale_id: Mapped[Optional[int]] = mapped_column(ForeignKey("whole_fish_sales.id"), nullable=True)
    finished_product_sale_id: Mapped[Optional[int]] = mapped_column(ForeignKey("finished_product_sales.id"), nullable=True)

    # 基本信息
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)

    # 加工厂追溯
    processing_plant_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True)
    processing_plant_name: Mapped[Optional[str]] = mapped_column(String(200))
    processing_plant_eu_no: Mapped[Optional[str]] = mapped_column(String(100))  # 加工厂EU注册号

    # 退货汇总
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    total_quantity: Mapped[int] = mapped_column(Integer, default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    # 退款信息
    refund_method: Mapped[Optional[RefundMethod]] = mapped_column(Enum(RefundMethod), nullable=True)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    refund_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    bank_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    transaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transaction_records.id"), nullable=True)

    # 状态与审批
    status: Mapped[ReturnStatus] = mapped_column(Enum(ReturnStatus), default=ReturnStatus.DRAFT)

    # 问题描述
    problem_description: Mapped[Optional[str]] = mapped_column(Text)
    customer_feedback: Mapped[Optional[str]] = mapped_column(Text)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)

    # 处理人
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 关联
    items: Mapped[List["ReturnItem"]] = relationship(
        "ReturnItem",
        back_populates="return_order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[List["ReturnAttachment"]] = relationship(
        "ReturnAttachment",
        back_populates="return_order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ReturnItem(Base, TimestampMixin):
    """退货明细（简化版：只保留重量、单价、金额）"""
    __tablename__ = "return_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_order_id: Mapped[int] = mapped_column(ForeignKey("return_orders.id"), nullable=False)

    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 明细备注/问题描述

    return_order: Mapped["ReturnOrder"] = relationship("ReturnOrder", back_populates="items")


class ReturnAttachment(Base, TimestampMixin):
    """退货附件（图片/视频/文档）"""
    __tablename__ = "return_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_order_id: Mapped[int] = mapped_column(ForeignKey("return_orders.id"), nullable=False)

    file_type: Mapped[ReturnAttachmentType] = mapped_column(Enum(ReturnAttachmentType), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)

    return_order: Mapped["ReturnOrder"] = relationship("ReturnOrder", back_populates="attachments")
