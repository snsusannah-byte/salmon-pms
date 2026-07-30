# ruff: noqa: F821
from decimal import Decimal
from typing import Optional

from enum import Enum as PyEnum
from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ProductCategory(str, PyEnum):
    """产品分类"""
    WHOLE_FISH = "whole_fish"           # 进口规格（整鱼）
    FILLET = "fillet"                   # 进口规格（鱼柳）
    FINISHED_PRODUCT = "finished_product"  # 成品定义
    BYPRODUCT = "byproduct"              # 副产品
    PACKAGING = "packaging"             # 包装物料
    ACCESSORY = "accessory"             # 配套
    BOM_MATERIAL = "bom_material"      # BOM物料/包材（兼容旧数据）


class MaterialCategory(Base, TimestampMixin):
    """物料分类"""
    __tablename__ = "material_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Product(Base, TimestampMixin):
    """产品档案（统一产品管理）"""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[ProductCategory] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)   # 产品编码
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 产品名称
    spec: Mapped[str | None] = mapped_column(String(100))        # 规格描述 / 规格编码
    unit: Mapped[str] = mapped_column(String(20), default="kg")   # 单位
    unit_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))  # 单位重量(kg)
    # 成品规格专用字段
    series_code: Mapped[str | None] = mapped_column(String(10))      # 系列代号 如A
    series_name: Mapped[str | None] = mapped_column(String(100))    # 系列名称 如三文鱼纯享
    portion_weight_g: Mapped[int | None] = mapped_column(Integer)     # 单份重量(g)
    portion_boxes: Mapped[int | None] = mapped_column(Integer)        # 份内盒数
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)
    
    # V3: 品牌（关联公司名称）
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"))  # 品牌ID（SKU变体用）
    template_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))  # 产品模板ID（NULL=模板/SPU，有值=变体/SKU）
    cost_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # 成本价（自动计算：BOM成本+包装物成本）

    # V3: 物料管理专用字段（仅 bom_material 使用）
    supplier_id: Mapped[int | None] = mapped_column(Integer)  # 供应商ID
    lead_time_days: Mapped[int | None] = mapped_column(Integer)  # 供货周期(天)
    last_purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 4))  # 最近采购价
    suggested_retail_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # 建议零售价
    wholesale_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # 批发价
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))  # 最低价
    
    # 成品库存管理（仅成品使用）
    stock_quantity: Mapped[int | None] = mapped_column(Integer, default=0)  # 库存数量
    safety_stock: Mapped[int | None] = mapped_column(Integer, default=0)  # 安全库存线

    # 物料分类关联（仅 bom_material 使用）
    material_category_id: Mapped[int | None] = mapped_column(ForeignKey("material_categories.id", ondelete="SET NULL"))
    material_category: Mapped[Optional["MaterialCategory"]] = relationship("MaterialCategory", foreign_keys=[material_category_id], lazy="raise")
    
    # 每箱数量（用于按箱采购入库时自动换算）
    items_per_box: Mapped[int | None] = mapped_column(Integer)
    
    # 物料层级（基础物料/规格变体/独立物料）
    material_type: Mapped[str | None] = mapped_column(String(20), default="standalone")
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    
    # 自关联：基础物料的变体列表
    variants: Mapped[list["Product"]] = relationship(
        "Product",
        foreign_keys=[parent_id],
        remote_side=[id],
        lazy="raise",
        collection_class=list,
    )
    
    # 成品特有的BOM关系
    boms: Mapped[list["ProductBOM"]] = relationship("ProductBOM", 
                                                       foreign_keys="ProductBOM.finished_product_id",
                                                       back_populates="finished_product",
                                                       lazy="raise",
                                                       cascade="all, delete-orphan")


class Brand(Base, TimestampMixin):
    """品牌定义（自有品牌 + OEM代工客户品牌）"""
    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 品牌名称
    code: Mapped[str | None] = mapped_column(String(50), unique=True)  # 品牌编码
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))  # 关联公司（OEM客户）
    is_oem: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否为代工品牌
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

    company: Mapped[Optional["Company"]] = relationship("Company", foreign_keys=[company_id], lazy="raise")


class ProductBOM(Base, TimestampMixin):
    """成品BOM物料清单"""
    __tablename__ = "product_boms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finished_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)  # 用量
    unit: Mapped[str] = mapped_column(String(20), default="个")  # 用量单位
    notes: Mapped[str | None] = mapped_column(Text)

    finished_product: Mapped["Product"] = relationship("Product",
                                                        foreign_keys=[finished_product_id],
                                                        back_populates="boms")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


class ProductPackaging(Base, TimestampMixin):
    """成品包装物清单（盒级/份级）"""
    __tablename__ = "product_packagings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"))  # 品牌变体：不同品牌不同包装
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # box:盒级, portion:份级
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)  # 用量
    unit: Mapped[str] = mapped_column(String(20), default="个")
    notes: Mapped[str | None] = mapped_column(Text)

    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id], lazy="raise")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


class ProductAccessory(Base, TimestampMixin):
    """成品配套产品（拼盘/附加产品）如：去尾甜虾、配菜"""
    __tablename__ = "product_accessories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    accessory_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)  # 配套产品ID
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("brands.id"))  # 品牌变体：不同品牌不同配套
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)  # 每份用量
    unit: Mapped[str] = mapped_column(String(20), default="个")
    notes: Mapped[str | None] = mapped_column(Text)

    product: Mapped["Product"] = relationship("Product", foreign_keys=[product_id], lazy="raise")
    accessory: Mapped["Product"] = relationship("Product", foreign_keys=[accessory_id], lazy="raise")


class InvoiceProduct(Base, TimestampMixin):
    """发票产品明细"""
    __tablename__ = "invoice_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("import_invoices.id"), nullable=False)
    product_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 产品名称
    product_spec: Mapped[str] = mapped_column(String(100), nullable=False)  # 规格
    box_count: Mapped[int] = mapped_column(Integer, nullable=False)
    net_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    
    invoice: Mapped["ImportInvoice"] = relationship("ImportInvoice", back_populates="products", lazy="raise")
