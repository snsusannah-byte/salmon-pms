"""
成品定义模块（重构版本 v2）

四级结构：
  系列(ProductSeries) → SPU(ProductTemplate) → 规格(ProductSpec) → SKU(ProductVariant×Brand)

核心改进：
1. 系列层：纯享装/拼盘装/即食装/团购装/副产品
2. SPU：产品概念（三文鱼刺身/海鲜拼盘），不再含规格
3. 规格：从SPU分离，支持同一SPU多规格组合
4. SKU：规格×品牌，可交易最小单位
5. BOM打通：支持关联任意品类（三文鱼/甜虾/希鲮鱼籽/配料/包装）
6. 价格层级：客户分级价/渠道价/阶梯价
7. 配套类型：accessory(配套)/gift(赠品)/sample(试吃)

向后兼容：
- 保留 template_id 字段，现有数据继续可用
- 新增 spec_id 关联规格，渐进式迁移
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


# ==================== 新增：产品系列 ====================

class ProductSeries(Base, TimestampMixin):
    """产品系列
    
    纯享装：高端零售，礼盒腰封
    拼盘装：组合搭配，聚会场景
    即食装：现切现发，即时消费
    团购装：大份量实惠，聚餐场景
    副产品：鱼头鱼骨，低价引流/赠品
    """
    __tablename__ = "product_series"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    templates: Mapped[List["ProductTemplate"]] = relationship(
        "ProductTemplate", back_populates="series", lazy="raise"
    )


# ==================== 新增：产品规格 ====================

class ProductSpec(Base, TimestampMixin):
    """产品规格（从模板分离）
    
    同一SPU可以有多个规格：
    - 三文鱼刺身(SPU) → 鱼腩200g+中段200g / 中段400g / 鱼腩400g
    - 海鲜拼盘(SPU) → 中段130g+甜虾15只 / 中段200g+甜虾+希鲮鱼籽
    """
    __tablename__ = "product_specs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parts_config: Mapped[Optional[str]] = mapped_column(Text)
    total_weight_g: Mapped[Optional[int]] = mapped_column(Integer)
    portion_count: Mapped[int] = mapped_column(Integer, default=1)
    box_count: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    template: Mapped["ProductTemplate"] = relationship("ProductTemplate", back_populates="specs")
    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="spec", lazy="raise",
        cascade="all, delete-orphan"
    )


# ==================== 新增：价格层级 ====================

class VariantPriceTier(Base, TimestampMixin):
    """SKU价格层级
    
    支持：
    - 客户分级价：大客户/VIP/普通
    - 渠道价：线上/线下/团购
    - 阶梯价：起量折扣
    """
    __tablename__ = "variant_price_tiers"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    tier_type: Mapped[str] = mapped_column(String(20), nullable=False)
    tier_key: Mapped[str] = mapped_column(String(50), nullable=False)
    tier_name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_qty: Mapped[int] = mapped_column(Integer, default=1)
    max_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    valid_from: Mapped[Optional[str]] = mapped_column(String(10))
    valid_to: Mapped[Optional[str]] = mapped_column(String(10))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="price_tiers")


# ==================== 改造：产品模板（SPU）====================

class ProductTemplate(Base, TimestampMixin):
    """成品模板（SPU）
    
    存固定信息：规格、部位、通用BOM/包装
    不包含品牌、价格、库存
    """
    __tablename__ = "product_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 新增：关联系列
    series_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product_series.id"), nullable=True
    )
    
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 如：三文鱼刺身
    spec: Mapped[Optional[str]] = mapped_column(String(100))        # 规格描述（废弃，迁移到 ProductSpec）
    unit: Mapped[str] = mapped_column(String(20), default="kg")
    unit_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 3))
    portion_weight_g: Mapped[Optional[int]] = mapped_column(Integer)
    portion_boxes: Mapped[Optional[int]] = mapped_column(Integer)
    series_code: Mapped[Optional[str]] = mapped_column(String(10))  # 保留兼容
    series_name: Mapped[Optional[str]] = mapped_column(String(100))  # 保留兼容
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    series: Mapped[Optional["ProductSeries"]] = relationship(
        "ProductSeries", back_populates="templates", lazy="raise"
    )
    specs: Mapped[List["ProductSpec"]] = relationship(
        "ProductSpec", back_populates="template", lazy="raise",
        cascade="all, delete-orphan"
    )
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
    
    # 新增：物料类型（salmon/seafood/sauce/packaging/accessory）
    material_type: Mapped[str] = mapped_column(String(20), default="salmon")
    
    # 新增：是否核心主料
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
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
    
    # 新增：关联规格
    spec_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product_specs.id", ondelete="CASCADE"), nullable=True
    )
    
    # 保留：兼容旧数据
    template_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=True
    )
    
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.id"))
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    suggested_retail_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    wholesale_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    stock_quantity: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    safety_stock: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    spec: Mapped[Optional["ProductSpec"]] = relationship(
        "ProductSpec", back_populates="variants", lazy="raise"
    )
    template: Mapped[Optional["ProductTemplate"]] = relationship("ProductTemplate", back_populates="variants")
    brand: Mapped[Optional["Brand"]] = relationship("Brand", foreign_keys=[brand_id], lazy="raise")
    packagings: Mapped[List["VariantPackaging"]] = relationship(
        "VariantPackaging", back_populates="variant", lazy="raise",
        cascade="all, delete-orphan"
    )
    accessories: Mapped[List["VariantAccessory"]] = relationship(
        "VariantAccessory", back_populates="variant", lazy="raise",
        cascade="all, delete-orphan"
    )
    price_tiers: Mapped[List["VariantPriceTier"]] = relationship(
        "VariantPriceTier", back_populates="variant", lazy="raise",
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
    
    # 新增：配套类型（accessory配套/gift赠品/sample试吃）
    accessory_type: Mapped[str] = mapped_column(String(20), default="accessory")
    
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="accessories")
    accessory: Mapped["Product"] = relationship("Product", foreign_keys=[accessory_id], lazy="raise")
