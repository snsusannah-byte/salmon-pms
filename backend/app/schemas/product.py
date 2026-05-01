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
    is_active: bool = Field(True, description="是否启用")
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
    is_active: Optional[bool] = Field(None)
    notes: Optional[str] = None


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
