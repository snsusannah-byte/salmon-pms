"""
成品定义模块（独立模块，不改动现有产品管理）
- 产品模板（SPU）：规格、部位、通用BOM/包装
- 品牌变体（SKU）：品牌、价格、库存、专属包装/配套
"""
# ruff: noqa: F821
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ProductTemplate(Base, TimestampMixin):
    """成品模板（SPU）
    
    存固定信息：规格、部位、通用BOM/包装
    不包含品牌、价格、库存
    """
    __tablename__ = "product_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 如：鱼腩200g+中段200g
    spec: Mapped[Optional[str]] = mapped_column(String(100))        # 规格描述
    unit: Mapped[str] = mapped_column(String(20), default="kg")
    unit_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))  # 单盒重量
    portion_weight_g: Mapped[Optional[int]] = mapped_column(Integer)           # 单份重量
    portion_boxes: Mapped[Optional[int]] = mapped_column(Integer)                # 份内盒数
    series_code: Mapped[Optional[str]] = mapped_column(String(10))               # 系列代号
    series_name: Mapped[Optional[str]] = mapped_column(String(100))              # 系列名称
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    parts: Mapped[List["TemplatePart"]] = relationship(
        "TemplatePart", back_populates="template", lazy="raise",
        cascade="all, delete-orphan"
    )
    boms: Mapped[List["TemplateBOM"]] = relationship(
        "TemplateBOM", back_populates="template", lazy="raise",
        cascade="all, delete-orphan"
    )
    packagings: Mapped[List["TemplatePackaging"]] = relationship(
        "TemplatePackaging", back_populates="template", lazy="raise",
        cascade="all, delete-orphan"
    )
    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="template", lazy="raise",
        cascade="all, delete-orphan"
    )


class TemplatePart(Base, TimestampMixin):
    """成品模板部位（BOM）"""
    __tablename__ = "template_parts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False)
    part_name: Mapped[str] = mapped_column(String(50), nullable=False)  # 鱼腩、中段
    weight_g: Mapped[int] = mapped_column(Integer, nullable=False)     # 200
    boxes: Mapped[int] = mapped_column(Integer, default=1)             # 每份几盒
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped["ProductTemplate"] = relationship("ProductTemplate", back_populates="parts")


class TemplateBOM(Base, TimestampMixin):
    """成品模板通用BOM物料"""
    __tablename__ = "template_boms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False)
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)  # 关联物料管理
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="个")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    template: Mapped["ProductTemplate"] = relationship("ProductTemplate", back_populates="boms")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


class TemplatePackaging(Base, TimestampMixin):
    """成品模板通用包装物"""
    __tablename__ = "template_packagings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # box / portion
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="个")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    template: Mapped["ProductTemplate"] = relationship("ProductTemplate", back_populates="packagings")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


class ProductVariant(Base, TimestampMixin):
    """品牌变体（SKU）
    
    存可变信息：品牌、价格、库存、专属包装/配套
    继承模板的规格、部位、通用BOM
    """
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False)
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.id"))
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # 品牌编码+序号
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 品牌名 + 模板名
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    suggested_retail_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    wholesale_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    stock_quantity: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    safety_stock: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    template: Mapped["ProductTemplate"] = relationship("ProductTemplate", back_populates="variants")
    brand: Mapped[Optional["Brand"]] = relationship("Brand", foreign_keys=[brand_id], lazy="raise")
    packagings: Mapped[List["VariantPackaging"]] = relationship(
        "VariantPackaging", back_populates="variant", lazy="raise",
        cascade="all, delete-orphan"
    )
    accessories: Mapped[List["VariantAccessory"]] = relationship(
        "VariantAccessory", back_populates="variant", lazy="raise",
        cascade="all, delete-orphan"
    )


class VariantPackaging(Base, TimestampMixin):
    """品牌变体专属包装物
    
    is_override=True: 覆盖模板通用包装（如：用品牌专属腰封替换通用腰封）
    is_override=False: 追加到模板通用包装（如：品牌额外赠品）
    """
    __tablename__ = "variant_packagings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # box / portion
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="个")
    is_override: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="packagings")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


class VariantAccessory(Base, TimestampMixin):
    """品牌变体专属配套产品"""
    __tablename__ = "variant_accessories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    accessory_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="个")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="accessories")
    accessory: Mapped["Product"] = relationship("Product", foreign_keys=[accessory_id], lazy="raise")
