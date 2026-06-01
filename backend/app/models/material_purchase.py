"""
物料采购与批次管理模型
"""
from datetime import date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MaterialPurchaseOrder(Base, TimestampMixin):
    """物料采购单"""
    __tablename__ = "material_purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    
    quoted_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    actual_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payment_status: Mapped[str] = mapped_column(String(20), default="unpaid")
    
    # 入库日期（用于计算到货周期）
    inbound_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # 关系
    items: Mapped[List["MaterialPurchaseItem"]] = relationship(
        "MaterialPurchaseItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    supplier: Mapped["Company"] = relationship("Company", lazy="joined")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", lazy="joined")


class MaterialPurchaseItem(Base, TimestampMixin):
    """物料采购明细"""
    __tablename__ = "material_purchase_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id: Mapped[int] = mapped_column(
        ForeignKey("material_purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    
    # 数量
    box_count: Mapped[int] = mapped_column(Integer, nullable=False)
    items_per_box: Mapped[int] = mapped_column(Integer, nullable=False)
    total_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # 价格（双轨）
    quoted_unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))
    quoted_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    actual_unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    
    # 入库状态
    received_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    is_fully_received: Mapped[bool] = mapped_column(Boolean, default=False)
    
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # 关系
    order: Mapped["MaterialPurchaseOrder"] = relationship("MaterialPurchaseOrder", back_populates="items")
    product: Mapped["Product"] = relationship("Product", lazy="joined")


class MaterialBatch(Base, TimestampMixin):
    """物料批次库存"""
    __tablename__ = "material_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_no: Mapped[str] = mapped_column(String(100), nullable=False)
    
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    
    # 来源（快照）
    supplier_name: Mapped[Optional[str]] = mapped_column(String(200))
    purchase_order_item_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("material_purchase_items.id"),
    )
    
    # 数量
    inbound_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    remaining_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(20))
    
    # 成本
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # 时间
    inbound_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date)
    
    # 仓库
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"))
    location: Mapped[Optional[str]] = mapped_column(String(100))
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="active")
    
    # 关系
    product: Mapped["Product"] = relationship("Product", lazy="joined")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", lazy="joined")
