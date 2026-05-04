"""
三文鱼PMS - 成品销售模块V2模型扩展
基于现有模型向后兼容添加
"""
from datetime import date
from decimal import Decimal
from enum import Enum as PyEnum
from typing import List, Optional

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


# ==================== 新增枚举 ====================

class SlaughterType(str, PyEnum):
    """宰杀类型"""
    WHOLE_FISH = "whole_fish"   # 整鱼宰杀
    FILLET = "fillet"           # 鱼柳（外购已切分）


class LossType(str, PyEnum):
    """损耗类型"""
    SPOILAGE = "spoilage"           # 变质报废
    INVENTORY_DIFF = "inventory_diff"  # 盘点差异
    EXPIRED = "expired"             # 过期处理
    OTHER = "other"                 # 其他


class SaleItemType(str, PyEnum):
    """销售子项类型"""
    MAIN = "main"           # 正品（三文鱼部位，按重量）
    GIFT = "gift"           # 赠品（按件数）
    ACCESSORY = "accessory" # 配套产品（按件数）


class WarehouseType(str, PyEnum):
    """仓库类型"""
    WHOLE_FISH = "whole_fish"   # 整鱼仓库
    FINISHED = "finished"       # 成品仓库


class InboundType(str, PyEnum):
    """入库类型"""
    PURCHASE = "purchase"   # 外部采购
    TRANSFER = "transfer"   # 内部调拨


# ==================== 扩展 Product 表（仅新增字段）====================
# 注意：以下字段通过 Alembic migration 添加到 products 表
# lead_time_days: int (nullable, default=0) - 供货周期(天)
# avg_daily_consumption: Decimal (nullable, default=0) - 日均消耗(件/重量)
# safety_buffer: int (nullable, default=0) - 安全缓冲(件)


# ==================== 新增：每日宰杀记录 ====================

class DailySlaughterRecord(Base, TimestampMixin):
    """每日宰杀记录（整鱼/鱼柳）
    
    业务规则：
    - 整鱼：必须填写 fish_count（宰杀条数），副产品按条数自动计算
    - 鱼柳：fish_count 为0或不填，副产品全部为0，只填写总重量和成品肉产出
    - 自动计算：出肉率%、损耗率%、当日成本单价、总成本
    - 重量平衡校验：总重 ≈ 成品肉 + 损耗 + 边角料 + 副产品重量（估算）
    """
    __tablename__ = "daily_slaughter_records"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slaughter_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)  # 宰杀日期
    slaughter_type: Mapped[SlaughterType] = mapped_column(String(20), nullable=False, default=SlaughterType.WHOLE_FISH)  # 宰杀类型
    
    # 投入
    fish_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)  # 宰杀条数（整鱼必填，鱼柳为0）
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)  # 鱼总重(kg)
    
    # 产出
    meat_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)  # 成品肉产出(kg)
    byproduct_head_count: Mapped[int] = mapped_column(Integer, default=0)  # 副产品-鱼头数量
    byproduct_tail_count: Mapped[int] = mapped_column(Integer, default=0)  # 副产品-鱼尾数量
    byproduct_bone_count: Mapped[int] = mapped_column(Integer, default=0)  # 副产品-鱼骨数量
    byproduct_trim_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 边角料重量(kg)
    
    # 损耗
    loss_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 损耗重量(kg)
    loss_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))  # 损耗率%
    
    # 成本（自动计算）
    meat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0"))  # 出肉率%
    cost_price_per_kg: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("0"))  # 当日成本单价(元/kg)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))  # 当日总成本(元)
    
    # 成本来源说明
    cost_source: Mapped[str] = mapped_column(String(50), default="auto")  # auto:自动计算, manual:手动输入
    
    # 当日可用肉（前期累计 + 当日产出 - 边角料 - 损耗 - 已售）
    available_meat_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 当日可用肉(kg)
    sold_meat_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 已售出肉重(kg)
    
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)  # 锁定后不可修改
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ==================== 新增：成品仓库采购入库 ====================

class WarehousePurchaseOrder(Base, TimestampMixin):
    """成品仓库采购入库单
    
    存放内容：整鱼、鱼柳、包装物料、副产品、配套产品
    整鱼和鱼柳采购回来入库，宰杀登记时自动扣减库存
    """
    __tablename__ = "warehouse_purchase_orders"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)  # 入库日期
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)  # 采购的产品
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"))  # 供应商
    
    batch_no: Mapped[Optional[str]] = mapped_column(String(100))  # 采购批次号
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)  # 数量（重量kg或件数）
    unit: Mapped[str] = mapped_column(String(20), default="kg")  # 单位 kg/件/个
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)  # 成本单价
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)  # 总金额
    
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0)  # 供货周期(天)
    warehouse_type: Mapped[WarehouseType] = mapped_column(String(20), default=WarehouseType.FINISHED)  # 所在仓库
    inbound_type: Mapped[InboundType] = mapped_column(String(20), default=InboundType.PURCHASE)  # 入库类型
    warehouse_location: Mapped[Optional[str]] = mapped_column(String(100))  # 存放位置
    
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id], lazy="raise")
    supplier: Mapped[Optional["Company"]] = relationship("Company", foreign_keys=[supplier_id], lazy="raise")


# ==================== 新增：成品仓库实时库存 ====================

class WarehouseStock(Base, TimestampMixin):
    """成品仓库实时库存
    
    独立库存表，与现有 inventory（整鱼进口库存）区分
    成品仓库存放：整鱼、鱼柳、包装物料、副产品、配套产品
    """
    __tablename__ = "warehouse_stocks"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, unique=True)  # 产品ID（一对一）
    warehouse_type: Mapped[WarehouseType] = mapped_column(String(20), default=WarehouseType.FINISHED)  # 所在仓库
    
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 当前库存数量
    reserved_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 预留数量（已销售未出库）
    available_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 可用数量 = 当前 - 预留
    
    unit_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))  # 成本单价（加权平均）
    warehouse_location: Mapped[Optional[str]] = mapped_column(String(100))  # 存放位置
    
    last_in_date: Mapped[Optional[date]] = mapped_column(Date)  # 最后入库日期
    last_out_date: Mapped[Optional[date]] = mapped_column(Date)  # 最后出库日期
    
    # 预警状态（动态计算，非持久化）
    warning_threshold: Mapped[Optional[int]] = mapped_column(Integer, default=0)  # 预警线（件/kg）
    is_below_warning: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否低于预警线
    
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id], lazy="raise")


# ==================== 新增：成品销售子项 ====================

class FinishedProductSaleItem(Base, TimestampMixin):
    """成品销售子项
    
    一条销售记录包含多个子项：
    - 正品（三文鱼部位）：按重量(kg)销售，不计件数库存
    - 配套产品：按件数销售，扣减库存
    - 赠品：按件数赠送，扣减库存
    """
    __tablename__ = "finished_product_sale_items"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("finished_product_sales.id"), nullable=False)
    item_type: Mapped[SaleItemType] = mapped_column(String(20), nullable=False)  # main/gift/accessory
    
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)  # 关联的产品
    
    # 正品用重量，配套/赠品用件数
    weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))  # 重量(kg) - 正品用
    quantity: Mapped[Optional[int]] = mapped_column(Integer)  # 件数 - 配套/赠品用
    
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))  # 单价
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))  # 金额
    
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    sale: Mapped["FinishedProductSale"] = relationship("FinishedProductSale", foreign_keys=[sale_id], lazy="raise")
    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id], lazy="raise")


# ==================== 新增：损耗处理记录 ====================

class LossRecord(Base, TimestampMixin):
    """损耗处理记录
    
    非加工损耗：变质报废、盘点差异、过期处理等
    扣减当日可用肉或仓库库存
    """
    __tablename__ = "loss_records"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    loss_date: Mapped[date] = mapped_column(Date, nullable=False)  # 损耗登记日期
    loss_type: Mapped[LossType] = mapped_column(String(20), nullable=False)  # 损耗类型
    
    # 关联宰杀日期（扣减当日可用肉）
    slaughter_date: Mapped[Optional[date]] = mapped_column(Date)  # 关联的宰杀日期
    
    # 关联产品（扣减仓库库存）
    product_id: Mapped[Optional[int]] = mapped_column(ForeignKey("products.id"))
    
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=Decimal("0"))  # 损耗重量(kg)
    quantity: Mapped[int] = mapped_column(Integer, default=0)  # 损耗数量（件/个）
    
    reason: Mapped[Optional[str]] = mapped_column(Text)  # 损耗原因
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    product: Mapped[Optional["Product"]] = relationship("Product", foreign_keys=[product_id], lazy="raise")


# ==================== 扩展 FinishedProductSale（仅新增字段说明）====================
# 注意：以下字段通过 Alembic migration 添加到 finished_product_sales 表
# slaughter_date: Date (nullable) - 关联的宰杀日期（销售必须关联宰杀批次）
# total_weight_kg: Decimal(Numeric(12,3), nullable) - 销售总重量(kg)
# 
# 关系：新增 items 关系到 FinishedProductSaleItem
# items: Mapped[List["FinishedProductSaleItem"]] = relationship(...)

class FinishedProductCommission(Base, TimestampMixin):
    """成品销售提成记录"""
    __tablename__ = "finished_product_commissions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    salesperson_id: Mapped[int] = mapped_column(ForeignKey("salespersons.id"), nullable=False)
    sale_id: Mapped[int] = mapped_column(ForeignKey("finished_product_sales.id"), nullable=False)
    sale_date: Mapped[Date] = mapped_column(Date, nullable=False)
    sale_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    commission_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    paid_date: Mapped[Optional[Date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    salesperson: Mapped["Salesperson"] = relationship("Salesperson", lazy="raise")
