# ruff: noqa: F821
from datetime import datetime
from app.models.enums import PurchaseOrderStatus
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
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

class TransactionRecord(Base, TimestampMixin):
    """统一交易流水（合并日常收支+扫码手续费+付款）"""
    __tablename__ = "transaction_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_date: Mapped[Date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    
    from_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"))
    to_account_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bank_accounts.id"))
    
    counterparty_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"))
    counterparty_name: Mapped[Optional[str]] = mapped_column(String(200))
    
    reference_no: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    related_invoice_id: Mapped[Optional[int]] = mapped_column(ForeignKey("import_invoices.id"))
    related_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("batches.id"))
    related_sale_ids: Mapped[Optional[list]] = mapped_column(JSON)  # JSON array of sale IDs
    
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    confirmed_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ==================== 采购入库模块 ====================


class PurchaseOrder(Base, TimestampMixin):
    """采购单"""
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    order_date: Mapped[Date] = mapped_column(Date, nullable=False)
    
    supplier_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    main_product_type: Mapped[str] = mapped_column(String(50), nullable=False)  # import_whole_fish / domestic_whole_fish / packaging / shrimp_whole
    main_warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    
    has_accessories: Mapped[bool] = mapped_column(Boolean, default=False)
    
    total_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    status: Mapped[PurchaseOrderStatus] = mapped_column(Enum(PurchaseOrderStatus), default=PurchaseOrderStatus.PENDING)
    
    notes: Mapped[Optional[str]] = mapped_column(Text)



class PurchaseOrderItem(Base, TimestampMixin):
    """采购单项"""
    __tablename__ = "purchase_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("batches.id"))
    
    item_type: Mapped[str] = mapped_column(String(20), default="main")  # main / accessory / material
    
    qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    received_qty: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))
    warehouse_id: Mapped[Optional[int]] = mapped_column(ForeignKey("warehouses.id"))
    
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ==================== 仓库模块V2 ====================


class DomesticSupplier(Base, TimestampMixin):
    """国内供应商"""
    __tablename__ = "domestic_suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")



class PurchaseOrderV2(Base, TimestampMixin):
    """采购入库单 (v2 - 迁移自 salmon-finance-v4)"""
    __tablename__ = "purchase_orders_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_no: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    purchase_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    supplier_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))
    total_weight: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_boxes: Mapped[int] = mapped_column(Integer, default=0)
    order_type: Mapped[Optional[str]] = mapped_column(String(20), default="raw_material")  # raw_material=整鱼, accessories=辅料
    slaughter_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)  # 宰杀日期
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    # 以销定采：采购单反向关联销售单（一个销售单可分多个采购单）
    sale_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    products: Mapped[List["PurchaseOrderProductV2"]] = relationship(
        "PurchaseOrderProductV2",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )



class PurchaseOrderProductV2(Base, TimestampMixin):
    """采购入库产品明细 (v2)"""
    __tablename__ = "purchase_order_products_v2"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders_v2.id"), nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    product_spec: Mapped[str] = mapped_column(String(100), nullable=False)
    factory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    box_count: Mapped[int] = mapped_column(Integer, default=0)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    order: Mapped["PurchaseOrderV2"] = relationship("PurchaseOrderV2", back_populates="products")


