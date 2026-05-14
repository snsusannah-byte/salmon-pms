"""
物料-供应商关联模型
支持多供应商供应该物料，每个供应商有不同价格
"""
# ruff: noqa: F821
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MaterialSupplier(Base, TimestampMixin):
    """物料供应商关联
    
    一个物料可以有多个供应商，每个供应商有各自的采购价格。
    同时记录供货周期、最小起订量、是否首选供应商。
    """
    __tablename__ = "material_suppliers"
    __table_args__ = (
        UniqueConstraint("material_id", "supplier_id", name="uix_material_supplier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))  # 采购单价
    min_order_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 最小起订量
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0)  # 供货周期(天)
    is_preferred: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否首选供应商
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")
    supplier: Mapped["Company"] = relationship("Company", foreign_keys=[supplier_id], lazy="raise")
