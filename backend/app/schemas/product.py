from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    """产品基础"""
    category: str = Field(..., description="产品分类: whole_fish/finished_product/byproduct/bom_material")
    code: str = Field(..., max_length=50, description="产品编码")
    name: str = Field(..., max_length=100, description="产品名称")
    spec: Optional[str] = Field(None, max_length=100, description="规格描述 / 规格编码")
    unit: str = Field("kg", max_length=20, description="单位")
    unit_weight_kg: Optional[Decimal] = Field(None, description="单位重量(kg)，成品为单盒重量")
    # 成品规格专用
    series_code: Optional[str] = Field(None, max_length=10, description="系列代号 如A")
    series_name: Optional[str] = Field(None, max_length=100, description="系列名称 如三文鱼纯享")
    portion_weight_g: Optional[int] = Field(None, description="单份重量(g)")
    portion_boxes: Optional[int] = Field(None, description="份内盒数")
    # 成品价格策略与库存
    cost_price: Optional[Decimal] = Field(None, description="成本价")
    suggested_retail_price: Optional[Decimal] = Field(None, description="建议零售价")
    wholesale_price: Optional[Decimal] = Field(None, description="批发价")
    min_price: Optional[Decimal] = Field(None, description="最低价")
    is_active: bool = Field(True, description="是否启用")
    notes: Optional[str] = Field(None, description="备注")
    # V3: 品牌
    brand: Optional[str] = Field(None, max_length=100, description="品牌名称：无品牌/中挪三文鱼/海兴悦三文鱼/北辰海选汇")
    # V3: 物料管理专用字段
    supplier_id: Optional[int] = Field(None, description="供应商ID")
    lead_time_days: Optional[int] = Field(None, description="供货周期(天)")
    last_purchase_price: Optional[Decimal] = Field(None, description="最近采购价")
    
    stock_quantity: Optional[int] = Field(0, description="库存数量（件数，包装物/副产品/配套）")
    stock_weight_kg: Optional[Decimal] = Field(Decimal("0"), description="库存重量(kg)，成品肉专用")
    safety_stock: Optional[int] = Field(0, description="安全库存线")
    stock_quantity: Optional[int] = Field(0, description="是否启用")
    notes: Optional[str] = Field(None, description="备注")


class ProductCreate(ProductBase):
    """创建产品"""
    code: Optional[str] = Field(None, max_length=50, description="产品编码，留空自动生成")


class ProductUpdate(BaseModel):
    """更新产品"""
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    spec: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=20)
    unit_weight_kg: Optional[Decimal] = Field(None)
    series_code: Optional[str] = Field(None, max_length=10)
    series_name: Optional[str] = Field(None, max_length=100)
    portion_weight_g: Optional[int] = Field(None)
    portion_boxes: Optional[int] = Field(None)
    cost_price: Optional[Decimal] = Field(None)
    suggested_retail_price: Optional[Decimal] = Field(None)
    wholesale_price: Optional[Decimal] = Field(None)
    min_price: Optional[Decimal] = Field(None)
    stock_quantity: Optional[int] = Field(None)
    stock_weight_kg: Optional[Decimal] = Field(None)
    safety_stock: Optional[int] = Field(None)
    is_active: Optional[bool] = Field(None)
    notes: Optional[str] = None
    brand: Optional[str] = Field(None, max_length=100)  # V3: 品牌
    supplier_id: Optional[int] = Field(None)  # V3: 物料-供应商
    lead_time_days: Optional[int] = Field(None)  # V3: 物料-供货周期
    last_purchase_price: Optional[Decimal] = Field(None)  # V3: 物料-最近采购价


class ProductResponse(ProductBase):
    """产品响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    """产品列表响应"""
    total: int
    items: List[ProductResponse]
    skip: int
    limit: int


# BOM Schemas
class ProductBOMBase(BaseModel):
    """BOM基础"""
    material_id: int = Field(..., description="物料ID")
    quantity: Decimal = Field(..., gt=0, description="用量")
    unit: str = Field("个", max_length=20, description="用量单位")
    notes: Optional[str] = Field(None, description="备注")


class ProductBOMCreate(ProductBOMBase):
    """创建BOM"""
    pass


class ProductBOMUpdate(BaseModel):
    """更新BOM"""
    material_id: Optional[int] = Field(None)
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class ProductBOMResponse(ProductBOMBase):
    """BOM响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    finished_product_id: int
    material_name: Optional[str] = Field(None, description="物料名称")
    created_at: datetime
    updated_at: datetime


# 包装物 Schemas
class ProductPackagingBase(BaseModel):
    """包装物基础"""
    level: str = Field(..., description="包装层级: box盒级 / portion份级")
    material_id: int = Field(..., description="包材物料ID")
    quantity: Decimal = Field(..., gt=0, description="用量")
    unit: str = Field("个", max_length=20, description="用量单位")
    notes: Optional[str] = Field(None, description="备注")


class ProductPackagingCreate(ProductPackagingBase):
    """创建包装物"""
    pass


class ProductPackagingUpdate(BaseModel):
    """更新包装物"""
    level: Optional[str] = Field(None, max_length=20)
    material_id: Optional[int] = Field(None)
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class ProductPackagingResponse(ProductPackagingBase):
    """包装物响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    product_id: int
    material_name: Optional[str] = Field(None, description="物料名称")
    created_at: datetime
    updated_at: datetime


# 配套产品 Schemas
class ProductAccessoryBase(BaseModel):
    """配套产品基础"""
    accessory_id: int = Field(..., description="配套产品ID")
    quantity: Decimal = Field(..., gt=0, description="每份用量")
    unit: str = Field("个", max_length=20, description="用量单位")
    notes: Optional[str] = Field(None, description="备注")


class ProductAccessoryCreate(ProductAccessoryBase):
    """创建配套产品"""
    pass


class ProductAccessoryUpdate(BaseModel):
    """更新配套产品"""
    accessory_id: Optional[int] = Field(None)
    quantity: Optional[Decimal] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class ProductAccessoryResponse(ProductAccessoryBase):
    """配套产品响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    product_id: int
    accessory_name: Optional[str] = Field(None, description="配套产品名称")
    created_at: datetime
    updated_at: datetime


# 成本与库存响应 Schemas
class ProductCostResponse(BaseModel):
    """成品成本计算响应"""
    product_id: int
    product_name: str
    bom_cost: Decimal
    packaging_cost: Decimal
    total_cost: Decimal
    model_config = ConfigDict(from_attributes=True)


class ProductLowStockResponse(BaseModel):
    """低库存响应"""
    id: int
    code: str
    name: str
    category: str
    stock_quantity: int
    safety_stock: int
    model_config = ConfigDict(from_attributes=True)
