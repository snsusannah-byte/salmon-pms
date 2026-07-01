# ruff: noqa: F821
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import (
    InventoryStatus,
    MovementType,
    StockMovementType,
    StockStatus,
    WarehouseBusinessScope,
    WarehouseType,
)


class Warehouse(Base, TimestampMixin):
    """仓库定义"""
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)   # 仓库编码
    name: Mapped[str] = mapped_column(String(50), nullable=False)               # 仓库名称
    type: Mapped[WarehouseType] = mapped_column(Enum(WarehouseType), nullable=False)  # 仓库类型
    business_scope: Mapped[WarehouseBusinessScope] = mapped_column(
        Enum(WarehouseBusinessScope), default=WarehouseBusinessScope.ALL, nullable=False
    )  # 业务范围
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    stocks: Mapped[list["Stock"]] = relationship("Stock", back_populates="warehouse")
    movements: Mapped[list["StockMovement"]] = relationship("StockMovement", back_populates="warehouse")



class Stock(Base, TimestampMixin):
    """库存记录（按仓库+产品+批次）"""
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"), nullable=True)

    current_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=Decimal("0"))
    reserved_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    available_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=Decimal("0"))

    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")

    warning_threshold: Mapped[int] = mapped_column(Integer, default=0)
    is_below_warning: Mapped[bool] = mapped_column(Boolean, default=False)

    last_in_date: Mapped[Date | None] = mapped_column(Date)
    last_out_date: Mapped[Date | None] = mapped_column(Date)
    location: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)

    warehouse: Mapped[Warehouse] = relationship("Warehouse", back_populates="stocks")
    product: Mapped["Product"] = relationship("Product")
    batch: Mapped[Optional["Batch"]] = relationship("Batch")

    __table_args__ = (
        UniqueConstraint("warehouse_id", "product_id", "batch_id", name="uq_stock_warehouse_product_batch"),
    )



class StockInbound(Base, TimestampMixin):
    """入库记录（统一入口）"""
    __tablename__ = "stock_inbounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inbound_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[int | None] = mapped_column(Integer)
    source_no: Mapped[str | None] = mapped_column(String(100))

    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))

    qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))

    detail: Mapped[dict | None] = mapped_column(JSON)

    status: Mapped[StockStatus] = mapped_column(Enum(StockStatus), default=StockStatus.PENDING)
    inbound_date: Mapped[Date] = mapped_column(Date, nullable=False)
    confirmed_at: Mapped[DateTime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)

    # 国内整包仓专用字段
    slaughter_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    factory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_box_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_weight: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)

    # 批次级剩余量（用于先进先出扣减）
    remaining_qty: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    remaining_box_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class StockOutbound(Base, TimestampMixin):
    """出库记录"""
    __tablename__ = "stock_outbounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outbound_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    dest_type: Mapped[str] = mapped_column(String(50), nullable=False)
    dest_id: Mapped[int | None] = mapped_column(Integer)
    dest_no: Mapped[str | None] = mapped_column(String(100))

    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))

    qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    outbound_date: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[StockStatus] = mapped_column(Enum(StockStatus), default=StockStatus.PENDING)
    confirmed_at: Mapped[DateTime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)



class StockTransfer(Base, TimestampMixin):
    """调拨记录（整包仓 → 分包仓）"""
    __tablename__ = "stock_transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transfer_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    from_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    to_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))

    from_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    from_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    to_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    to_unit: Mapped[str] = mapped_column(String(20), nullable=False)

    conversion_ratio: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    detail: Mapped[dict | None] = mapped_column(JSON)

    status: Mapped[StockStatus] = mapped_column(Enum(StockStatus), default=StockStatus.PENDING)
    transfer_date: Mapped[Date] = mapped_column(Date, nullable=False)
    confirmed_at: Mapped[DateTime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)

    from_warehouse: Mapped[Warehouse] = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse: Mapped[Warehouse] = relationship("Warehouse", foreign_keys=[to_warehouse_id])



class StockMovement(Base, TimestampMixin):
    """库存变动记录（每一笔异动都记录）"""
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))

    movement_type: Mapped[StockMovementType] = mapped_column(Enum(StockMovementType), nullable=False)
    movement_date: Mapped[Date] = mapped_column(Date, nullable=False)

    qty_change: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    qty_before: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    qty_after: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)

    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))

    ref_type: Mapped[str] = mapped_column(String(50), nullable=False)
    ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ref_no: Mapped[str | None] = mapped_column(String(100))

    notes: Mapped[str | None] = mapped_column(Text)

    warehouse: Mapped[Warehouse] = relationship("Warehouse", back_populates="movements")



class ProductUnitConversion(Base, TimestampMixin):
    """产品单位转换规则"""
    __tablename__ = "product_unit_conversions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    from_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    to_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    ratio: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)

    is_default: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    product: Mapped["Product"] = relationship("Product")

    __table_args__ = (
        UniqueConstraint("product_id", "from_unit", "to_unit", name="uq_conversion_product_from_to"),
    )


# ==================== 库存层 ====================


class Inventory(Base, TimestampMixin):
    """库存实时查询"""
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)
    product_spec: Mapped[str] = mapped_column(String(100), nullable=False)
    current_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    reserved_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    available_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    status: Mapped[InventoryStatus] = mapped_column(Enum(InventoryStatus), default=InventoryStatus.IN_STOCK)
    warehouse_location: Mapped[str | None] = mapped_column(String(100))
    last_movement_date: Mapped[Date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)



class InventoryMovement(Base, TimestampMixin):
    """库存变动"""
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inventory_id: Mapped[int] = mapped_column(ForeignKey("inventory.id"), nullable=False)
    movement_date: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    type: Mapped[MovementType] = mapped_column(Enum(MovementType), nullable=False)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    reference_type: Mapped[str | None] = mapped_column(String(50))  # sale, processing, adjustment
    reference_id: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


# ==================== 审计日志 ====================

