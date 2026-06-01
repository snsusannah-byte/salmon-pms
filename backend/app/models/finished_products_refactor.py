"""
成品定义模块 - 重构版本

设计目标：
1. 系列层(product_series)：纯享装/拼盘装/即食装/团购装/副产品
2. SPU(product_templates)：产品概念，不再包含规格
3. 规格(product_specs)：从模板分离，支持同一SPU多规格
4. SKU(product_variants)：规格×品牌，可交易单位
5. BOM打通：支持关联任意品类物料（三文鱼/甜虾/希鲮鱼籽/配料）

向后兼容：
- 现有 product_templates 保留，新增 series_id 字段
- 现有 product_variants 保留，新增 spec_id 字段（渐进式迁移）
- 新增表不影响现有API，通过 migration 逐步切换
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
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)  # CX/PP/JS/TG/FB
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # 纯享装/拼盘装/即食装/团购装/副产品
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 关联
    templates: Mapped[List["ProductTemplate"]] = relationship(
        "ProductTemplate", back_populates="series", lazy="raise"
    )


# ==================== 改造：产品模板（SPU）====================

class ProductTemplate(Base, TimestampMixin):
    """成品模板（SPU）
    
    存产品概念：三文鱼刺身、海鲜拼盘、即食三文鱼
    不包含规格、价格、库存
    """
    __tablename__ = "product_templates"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 新增：关联系列
    series_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product_series.id"), nullable=True
    )
    
    # 编码规范化：系列代码-产品代码-序号
    # 如：SP-CW-001 = 三文鱼(SP) 刺身(CW) 第1款
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 产品名称（不再包含规格）
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 三文鱼刺身、海鲜拼盘
    
    # 显示名称自动生成："{品牌} {系列} {产品名} {规格}"
    # 如：海兴悦 纯享装 三文鱼刺身 鱼腩200g+中段200g
    
    unit: Mapped[str] = mapped_column(String(20), default="kg")
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
    boms: Mapped[List["TemplateBOM"]] = relationship(
        "TemplateBOM", back_populates="template", lazy="raise",
        cascade="all, delete-orphan"
    )
    packagings: Mapped[List["TemplatePackaging"]] = relationship(
        "TemplatePackaging", back_populates="template", lazy="raise",
        cascade="all, delete-orphan"
    )


# ==================== 新增：产品规格（从模板分离）====================

class ProductSpec(Base, TimestampMixin):
    """产品规格
    
    同一SPU可以有多个规格组合：
    - 三文鱼刺身(SPU) → 鱼腩200g+中段200g / 中段400g / 鱼腩400g
    - 海鲜拼盘(SPU) → 中段130g+甜虾15只 / 中段200g+甜虾+希鲮鱼籽
    
    规格描述自动拼接部位和重量：
    display_spec = "鱼腩200g+中段200g"
    """
    __tablename__ = "product_specs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False
    )
    
    # 规格编码：系列代码-规格代码-序号
    # 如：CX-FN200-ZD200-001 = 纯享装-鱼腩200g-中段200g
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 规格名称（可自动生成）
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # 部位组合（JSON或关联表）
    # 如：[{"part": "鱼腩", "weight_g": 200}, {"part": "中段", "weight_g": 200}]
    parts_config: Mapped[Optional[str]] = mapped_column(Text)  # JSON格式
    
    # 总重量
    total_weight_g: Mapped[Optional[int]] = mapped_column(Integer)
    
    # 份数/盒数
    portion_count: Mapped[int] = mapped_column(Integer, default=1)  # 几份
    box_count: Mapped[int] = mapped_column(Integer, default=1)      # 几盒
    
    # 排序
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    template: Mapped["ProductTemplate"] = relationship(
        "ProductTemplate", back_populates="specs"
    )
    variants: Mapped[List["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="spec", lazy="raise",
        cascade="all, delete-orphan"
    )


# ==================== 改造：品牌变体（SKU）====================

class ProductVariant(Base, TimestampMixin):
    """品牌变体（SKU）= 规格 × 品牌
    
    可交易的最小单位：
    - 规格：鱼腩200g+中段200g
    - 品牌：海兴悦 / 中挪 / 北辰 / 无品牌
    - SKU：海兴悦 纯享装 鱼腩200g+中段200g
    """
    __tablename__ = "product_variants"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # 新增：关联规格（渐进式迁移，保留 template_id 兼容）
    spec_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product_specs.id", ondelete="CASCADE"), nullable=True
    )
    
    # 保留：兼容旧数据
    template_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=True
    )
    
    brand_id: Mapped[Optional[int]] = mapped_column(ForeignKey("brands.id"))
    
    # SKU编码：品牌代码-规格代码-序号
    # 如：HX-CX-FN200-ZD200-001 = 海兴悦-纯享装-鱼腩200g-中段200g
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 显示名称自动生成
    # "{品牌} {系列} {产品名} {规格}"
    # 如：海兴悦 纯享装 三文鱼刺身 鱼腩200g+中段200g
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    
    # 价格体系（基础价格，实际销售价格走 PriceTier）
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    suggested_retail_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    wholesale_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    min_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # 库存（废弃，统一走 WarehouseStock）
    stock_quantity: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    safety_stock: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    spec: Mapped[Optional["ProductSpec"]] = relationship(
        "ProductSpec", back_populates="variants", lazy="raise"
    )
    brand: Mapped[Optional["Brand"]] = relationship("Brand", lazy="raise")
    packagings: Mapped[List["VariantPackaging"]] = relationship(
        "VariantPackaging", back_populates="variant", lazy="raise",
        cascade="all, delete-orphan"
    )
    accessories: Mapped[List["VariantAccessory"]] = relationship(
        "VariantAccessory", back_populates="variant", lazy="raise",
        cascade="all, delete-orphan"
    )
    # 价格层级
    price_tiers: Mapped[List["VariantPriceTier"]] = relationship(
        "VariantPriceTier", back_populates="variant", lazy="raise",
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
    
    # 价格类型
    tier_type: Mapped[str] = mapped_column(String(20), nullable=False)  # customer_level / channel / volume
    tier_key: Mapped[str] = mapped_column(String(50), nullable=False)    # VIP / online / 100+
    tier_name: Mapped[str] = mapped_column(String(100), nullable=False)  # VIP客户 / 线上渠道 / 100件起
    
    # 阶梯
    min_qty: Mapped[int] = mapped_column(Integer, default=1)
    max_qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # 价格
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    
    # 有效期
    valid_from: Mapped[Optional[str]] = mapped_column(String(10))  # YYYY-MM-DD
    valid_to: Mapped[Optional[str]] = mapped_column(String(10))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["ProductVariant"] = relationship(
        "ProductVariant", back_populates="price_tiers"
    )


# ==================== 改造：BOM物料（支持全品类）====================

class TemplateBOM(Base, TimestampMixin):
    """成品模板BOM物料
    
    支持关联任意品类：
    - 三文鱼部位（鱼腩/中段）
    - 其他海鲜（去尾甜虾/希鲮鱼籽）
    - 配料（酱油/芥末/姜片）
    - 包装物（盒子/腰封/冰袋）
    """
    __tablename__ = "template_boms"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False
    )
    
    # 物料类型：salmon / seafood / sauce / packaging / accessory
    material_type: Mapped[str] = mapped_column(String(20), default="salmon")
    
    # 关联物料（不限定三文鱼，支持全品类products）
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    
    # 用量
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="个")
    
    # 是否是核心主料（三文鱼部位）
    is_main: Mapped[bool] = mapped_column(Boolean, default=False)
    
    notes: Mapped[Optional[str]] = mapped_column(Text)

    template: Mapped["ProductTemplate"] = relationship("ProductTemplate", back_populates="boms")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


# ==================== 保留：模板部位（用于规格自动生成）====================

class TemplatePart(Base, TimestampMixin):
    """成品模板部位定义
    
    用于自动生成规格描述：
    鱼腩200g + 中段200g → "鱼腩200g+中段200g"
    """
    __tablename__ = "template_parts"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False
    )
    part_name: Mapped[str] = mapped_column(String(50), nullable=False)  # 鱼腩、中段、鱼块
    weight_g: Mapped[int] = mapped_column(Integer, nullable=False)     # 200
    boxes: Mapped[int] = mapped_column(Integer, default=1)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped["ProductTemplate"] = relationship("ProductTemplate")


# ==================== 保留：通用包装 ====================

class TemplatePackaging(Base, TimestampMixin):
    """成品模板通用包装物"""
    __tablename__ = "template_packagings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("product_templates.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)  # box / portion
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="个")
    notes: Mapped[Optional[str]] = mapped_column(Text)

    template: Mapped["ProductTemplate"] = relationship("ProductTemplate", back_populates="packagings")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


# ==================== 保留：变体专属包装 ====================

class VariantPackaging(Base, TimestampMixin):
    """品牌变体专属包装物"""
    __tablename__ = "variant_packagings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    material_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="个")
    is_override: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="packagings")
    material: Mapped["Product"] = relationship("Product", foreign_keys=[material_id], lazy="raise")


# ==================== 保留：变体专属配套 ====================

class VariantAccessory(Base, TimestampMixin):
    """品牌变体专属配套产品"""
    __tablename__ = "variant_accessories"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    accessory_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), default="个")
    
    # 配套类型：accessory(配套) / gift(赠品) / sample(试吃)
    accessory_type: Mapped[str] = mapped_column(String(20), default="accessory")
    
    notes: Mapped[Optional[str]] = mapped_column(Text)

    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="accessories")
    accessory: Mapped["Product"] = relationship("Product", foreign_keys=[accessory_id], lazy="raise")


# ==================== 保留：产品模板（向后兼容）====================
# 旧的 TemplatePart, TemplateBOM, TemplatePackaging 表保留
# 新增 ProductSeries, ProductSpec, VariantPriceTier 表
# ProductTemplate 新增 series_id 字段
# ProductVariant 新增 spec_id 字段
