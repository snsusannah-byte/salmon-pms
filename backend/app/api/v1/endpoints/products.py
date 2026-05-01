from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import ProductCategory
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ProductBOMCreate,
    ProductBOMUpdate,
    ProductBOMResponse,
    ProductPackagingCreate,
    ProductPackagingUpdate,
    ProductPackagingResponse,
)
from app.services.product_service import ProductService

router = APIRouter()


@router.get("/", response_model=ProductListResponse)
async def list_products(
    category: Optional[str] = Query(None, description="产品分类"),
    search: Optional[str] = Query(None, description="搜索"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """产品列表"""
    cat_enum = None
    if category:
        try:
            cat_enum = ProductCategory(category)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的产品分类: {category}",
            )
    
    items, total = await ProductService.list_products(
        db, category=cat_enum, search=search, is_active=is_active, skip=skip, limit=limit
    )
    
    result_items = []
    for item in items:
        item_dict = {
            "id": item.id,
            "category": item.category,
            "code": item.code,
            "name": item.name,
            "spec": item.spec,
            "unit": item.unit,
            "unit_weight_kg": item.unit_weight_kg,
            "series_code": item.series_code,
            "series_name": item.series_name,
            "portion_weight_g": item.portion_weight_g,
            "portion_boxes": item.portion_boxes,
            "is_active": item.is_active,
            "notes": item.notes,
            "created_at": item.created_at,
            "updated_at": item.updated_at,
        }
        result_items.append(ProductResponse(**item_dict))
    
    return ProductListResponse(total=total, items=result_items, skip=skip, limit=limit)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建产品"""
    product = await ProductService.create(db, data)
    
    return ProductResponse(
        id=product.id,
        category=product.category,
        code=product.code,
        name=product.name,
        spec=product.spec,
        unit=product.unit,
        unit_weight_kg=product.unit_weight_kg,
        series_code=product.series_code,
        series_name=product.series_name,
        portion_weight_g=product.portion_weight_g,
        portion_boxes=product.portion_boxes,
        is_active=product.is_active,
        notes=product.notes,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """产品详情"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )
    
    return ProductResponse(
        id=product.id,
        category=product.category,
        code=product.code,
        name=product.name,
        spec=product.spec,
        unit=product.unit,
        unit_weight_kg=product.unit_weight_kg,
        series_code=product.series_code,
        series_name=product.series_name,
        portion_weight_g=product.portion_weight_g,
        portion_boxes=product.portion_boxes,
        is_active=product.is_active,
        notes=product.notes,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新产品"""
    product = await ProductService.update(db, product_id, data)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )
    
    return ProductResponse(
        id=product.id,
        category=product.category,
        code=product.code,
        name=product.name,
        spec=product.spec,
        unit=product.unit,
        unit_weight_kg=product.unit_weight_kg,
        series_code=product.series_code,
        series_name=product.series_name,
        portion_weight_g=product.portion_weight_g,
        portion_boxes=product.portion_boxes,
        is_active=product.is_active,
        notes=product.notes,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除产品"""
    success = await ProductService.delete(db, product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )
    return None


@router.get("/series-codes")
async def get_series_codes(
    db: AsyncSession = Depends(get_db),
):
    """获取成品系列选项（系列代号+系列名称），用于下拉选择"""
    options = await ProductService.get_series_options(db)
    return options


# ==================== BOM管理 ====================

@router.get("/{product_id}/boms", response_model=List[ProductBOMResponse])
async def get_product_boms(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取成品BOM列表"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )
    
    boms = await ProductService.get_boms(db, product_id)
    
    result = []
    for bom in boms:
        material_name = None
        if bom.material:
            material_name = bom.material.name
        
        result.append(ProductBOMResponse(
            id=bom.id,
            finished_product_id=bom.finished_product_id,
            material_id=bom.material_id,
            material_name=material_name,
            quantity=bom.quantity,
            unit=bom.unit,
            notes=bom.notes,
            created_at=bom.created_at,
            updated_at=bom.updated_at,
        ))
    
    return result


@router.post("/{product_id}/boms", response_model=ProductBOMResponse, status_code=status.HTTP_201_CREATED)
async def create_product_bom(
    product_id: int,
    data: ProductBOMCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建BOM"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )
    
    if product.category != ProductCategory.FINISHED_PRODUCT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有成品才能配置BOM",
        )
    
    bom = await ProductService.create_bom(db, product_id, data)
    
    material_name = None
    if bom.material:
        material_name = bom.material.name
    
    return ProductBOMResponse(
        id=bom.id,
        finished_product_id=bom.finished_product_id,
        material_id=bom.material_id,
        material_name=material_name,
        quantity=bom.quantity,
        unit=bom.unit,
        notes=bom.notes,
        created_at=bom.created_at,
        updated_at=bom.updated_at,
    )


@router.delete("/{product_id}/boms/{bom_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_bom(
    product_id: int,
    bom_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除BOM"""
    success = await ProductService.delete_bom(db, bom_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"BOM ID={bom_id} 不存在",
        )
    return None


# ==================== 包装物管理 ====================

@router.get("/{product_id}/packagings", response_model=List[ProductPackagingResponse])
async def get_product_packagings(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取成品包装物清单"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )
    
    packagings = await ProductService.get_packagings(db, product_id)
    
    result = []
    for p in packagings:
        material_name = None
        if p.material:
            material_name = p.material.name
        
        result.append(ProductPackagingResponse(
            id=p.id,
            product_id=p.product_id,
            level=p.level,
            material_id=p.material_id,
            material_name=material_name,
            quantity=p.quantity,
            unit=p.unit,
            notes=p.notes,
            created_at=p.created_at,
            updated_at=p.updated_at,
        ))
    
    return result


@router.post("/{product_id}/packagings", response_model=ProductPackagingResponse, status_code=status.HTTP_201_CREATED)
async def create_product_packaging(
    product_id: int,
    data: ProductPackagingCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建包装物"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )
    
    if product.category != ProductCategory.FINISHED_PRODUCT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有成品才能配置包装物",
        )
    
    packaging = await ProductService.create_packaging(db, product_id, data)
    
    material_name = None
    if packaging.material:
        material_name = packaging.material.name
    
    return ProductPackagingResponse(
        id=packaging.id,
        product_id=packaging.product_id,
        level=packaging.level,
        material_id=packaging.material_id,
        material_name=material_name,
        quantity=packaging.quantity,
        unit=packaging.unit,
        notes=packaging.notes,
        created_at=packaging.created_at,
        updated_at=packaging.updated_at,
    )


@router.put("/{product_id}/packagings/{packaging_id}", response_model=ProductPackagingResponse)
async def update_product_packaging(
    product_id: int,
    packaging_id: int,
    data: ProductPackagingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新包装物"""
    packaging = await ProductService.update_packaging(db, packaging_id, data)
    if not packaging:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"包装物 ID={packaging_id} 不存在",
        )
    
    material_name = None
    if packaging.material:
        material_name = packaging.material.name
    
    return ProductPackagingResponse(
        id=packaging.id,
        product_id=packaging.product_id,
        level=packaging.level,
        material_id=packaging.material_id,
        material_name=material_name,
        quantity=packaging.quantity,
        unit=packaging.unit,
        notes=packaging.notes,
        created_at=packaging.created_at,
        updated_at=packaging.updated_at,
    )


@router.delete("/{product_id}/packagings/{packaging_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_packaging(
    product_id: int,
    packaging_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除包装物"""
    success = await ProductService.delete_packaging(db, packaging_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"包装物 ID={packaging_id} 不存在",
        )
    return None
