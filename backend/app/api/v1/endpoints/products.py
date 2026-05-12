from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import ProductCategory, Brand
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ProductBOMCreate,
    ProductBOMResponse,
    ProductPackagingCreate,
    ProductPackagingUpdate,
    ProductPackagingResponse,
    ProductAccessoryCreate,
    ProductAccessoryUpdate,
    ProductAccessoryResponse,
)
from app.services.product_service import ProductService


async def _build_product_response(db, product):
    """构建产品响应（带品牌名称）"""
    brand_name = None
    if product.brand_id:
        brand = await db.get(Brand, product.brand_id)
        brand_name = brand.name if brand else None
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
        cost_price=product.cost_price,
        suggested_retail_price=product.suggested_retail_price,
        wholesale_price=product.wholesale_price,
        min_price=product.min_price,
        stock_quantity=product.stock_quantity,
        safety_stock=product.safety_stock,
        brand_id=product.brand_id,
        brand_name=brand_name,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )

router = APIRouter()


@router.get("/", response_model=ProductListResponse)
async def list_products(
    category: Optional[str] = Query(None, description="产品分类"),
    categories: Optional[str] = Query(None, description="产品分类列表，逗号分隔"),
    search: Optional[str] = Query(None, description="搜索"),
    is_active: Optional[bool] = Query(None, description="是否启用"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """产品列表"""
    cat_enum = None
    cat_enums = None
    if categories:
        cat_enums = []
        for cat in categories.split(","):
            cat_lower = cat.strip().lower()
            try:
                cat_enums.append(ProductCategory(cat_lower))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无效的产品分类: {cat}",
                )
    elif category:
        cat_lower = category.strip().lower()
        try:
            cat_enum = ProductCategory(cat_lower)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的产品分类: {category}",
            )
    
    items, total = await ProductService.list_products(
        db, category=cat_enum, categories=cat_enums, search=search, is_active=is_active, skip=skip, limit=limit
    )

    result_items = []
    for item in items:
        result_items.append(await _build_product_response(db, item))

    return ProductListResponse(total=total, items=result_items, skip=skip, limit=limit)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建产品"""
    product = await ProductService.create(db, data)
    return await _build_product_response(db, product)


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
    return await _build_product_response(db, product)


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
    return await _build_product_response(db, product)


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


@router.get("/{product_id}/cost")
async def get_product_cost(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """自动计算成品成本"""
    cost = await ProductService.calculate_cost(db, product_id)
    return {"product_id": product_id, "cost_price": cost}


@router.get("/low-stock")
async def get_low_stock_products(
    db: AsyncSession = Depends(get_db),
):
    """获取低库存成品列表"""
    products = await ProductService.check_low_stock(db)
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "stock_quantity": p.stock_quantity,
            "safety_stock": p.safety_stock,
        }
        for p in products
    ]


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
    brand_id: Optional[int] = Query(None, description="品牌变体ID，筛选特定品牌的包装物"),
    db: AsyncSession = Depends(get_db),
):
    """获取成品包装物清单
    
    支持按 brand_id 筛选：
    - brand_id=1: 返回品牌1的包装物 + 通用包装物(brand_id=NULL)
    - brand_id=NULL: 返回所有包装物
    """
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )
    
    packagings = await ProductService.get_packagings(db, product_id, brand_id=brand_id)
    
    # 获取品牌名称
    brand_ids = [p.brand_id for p in packagings if p.brand_id]
    brand_names = {}
    if brand_ids:
        from app.models import Brand
        brand_result = await db.execute(
            select(Brand).where(Brand.id.in_(brand_ids))
        )
        brand_names = {b.id: b.name for b in brand_result.scalars().all()}
    
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
            brand_id=p.brand_id,
            material_name=material_name,
            brand_name=brand_names.get(p.brand_id) if p.brand_id else None,
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


# ==================== 配套产品管理 ====================

@router.get("/{product_id}/accessories", response_model=List[ProductAccessoryResponse])
async def get_product_accessories(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取成品配套产品列表"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )

    accessories = await ProductService.get_accessories(db, product_id)

    result = []
    for acc in accessories:
        accessory_name = None
        if acc.accessory:
            accessory_name = acc.accessory.name

        result.append(ProductAccessoryResponse(
            id=acc.id,
            product_id=acc.product_id,
            accessory_id=acc.accessory_id,
            accessory_name=accessory_name,
            quantity=acc.quantity,
            unit=acc.unit,
            notes=acc.notes,
            created_at=acc.created_at,
            updated_at=acc.updated_at,
        ))

    return result


@router.post("/{product_id}/accessories", response_model=ProductAccessoryResponse, status_code=status.HTTP_201_CREATED)
async def create_product_accessory(
    product_id: int,
    data: ProductAccessoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建配套产品"""
    product = await ProductService.get_by_id(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"产品 ID={product_id} 不存在",
        )

    if product.category != ProductCategory.FINISHED_PRODUCT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有成品才能配置配套产品",
        )

    accessory = await ProductService.create_accessory(db, product_id, data)

    accessory_name = None
    if accessory.accessory:
        accessory_name = accessory.accessory.name

    return ProductAccessoryResponse(
        id=accessory.id,
        product_id=accessory.product_id,
        accessory_id=accessory.accessory_id,
        accessory_name=accessory_name,
        quantity=accessory.quantity,
        unit=accessory.unit,
        notes=accessory.notes,
        created_at=accessory.created_at,
        updated_at=accessory.updated_at,
    )


@router.put("/{product_id}/accessories/{accessory_id}", response_model=ProductAccessoryResponse)
async def update_product_accessory(
    product_id: int,
    accessory_id: int,
    data: ProductAccessoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新配套产品"""
    accessory = await ProductService.update_accessory(db, accessory_id, data)
    if not accessory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配套产品 ID={accessory_id} 不存在",
        )

    accessory_name = None
    if accessory.accessory:
        accessory_name = accessory.accessory.name

    return ProductAccessoryResponse(
        id=accessory.id,
        product_id=accessory.product_id,
        accessory_id=accessory.accessory_id,
        accessory_name=accessory_name,
        quantity=accessory.quantity,
        unit=accessory.unit,
        notes=accessory.notes,
        created_at=accessory.created_at,
        updated_at=accessory.updated_at,
    )


@router.delete("/{product_id}/accessories/{accessory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_accessory(
    product_id: int,
    accessory_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除配套产品"""
    success = await ProductService.delete_accessory(db, accessory_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"配套产品 ID={accessory_id} 不存在",
        )
    return None


# ==================== 跨品牌产品统计 ====================

class ProductNameStatItem(BaseModel):
    """按产品名称统计的单个品牌变体"""
    model_config = ConfigDict(from_attributes=True)
    product_id: int
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    code: str
    is_oem: bool = False
    stock_quantity: int
    safety_stock: int
    cost_price: Optional[float] = None
    suggested_retail_price: Optional[float] = None


class ProductNameAggregate(BaseModel):
    """按产品名称聚合统计"""
    model_config = ConfigDict(from_attributes=True)
    product_name: str
    spec: Optional[str] = None
    category: str
    unit: str
    total_stock: int
    total_safety_stock: int
    brand_variants: int
    items: List[ProductNameStatItem]


@router.get("/stats/by-name", response_model=List[ProductNameAggregate])
async def stats_by_product_name(
    category: Optional[str] = Query(None, description="产品分类: finished_product"),
    search: Optional[str] = Query(None, description="搜索产品名称"),
    db: AsyncSession = Depends(get_db),
):
    """按产品名称聚合统计（跨品牌）
    
    用于查看同一规格产品在不同品牌下的分布：
    - 鱼腩200g+中段200g:
      - 林深见鹿: 库存 100, 成本 ¥45
      - XX公司(OEM): 库存 50, 成本 ¥42
      - 总计: 库存 150
    """
    from app.models import Brand
    from sqlalchemy import func
    
    # 1. 查询所有成品
    query = select(Product)
    if category:
        cat_enum = ProductCategory(category.lower())
        query = query.where(Product.category == cat_enum)
    else:
        query = query.where(Product.category == ProductCategory.FINISHED_PRODUCT)
    
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
    
    query = query.where(Product.is_active == True)
    query = query.order_by(Product.name, Product.brand_id)
    
    result = await db.execute(query)
    products = result.scalars().all()
    
    if not products:
        return []
    
    # 2. 获取品牌名称
    brand_ids = [p.brand_id for p in products if p.brand_id]
    brand_map = {}
    if brand_ids:
        brand_result = await db.execute(
            select(Brand).where(Brand.id.in_(brand_ids))
        )
        brand_map = {b.id: b for b in brand_result.scalars().all()}
    
    # 3. 按名称分组聚合
    from collections import defaultdict
    name_groups = defaultdict(list)
    for p in products:
        name_groups[p.name].append(p)
    
    aggregates = []
    for name, items in name_groups.items():
        total_stock = sum(p.stock_quantity or 0 for p in items)
        total_safety = sum(p.safety_stock or 0 for p in items)
        
        variants = []
        for p in items:
            brand = brand_map.get(p.brand_id) if p.brand_id else None
            variants.append(ProductNameStatItem(
                product_id=p.id,
                brand_id=p.brand_id,
                brand_name=brand.name if brand else None,
                code=p.code,
                is_oem=brand.is_oem if brand else False,
                stock_quantity=p.stock_quantity or 0,
                safety_stock=p.safety_stock or 0,
                cost_price=float(p.cost_price) if p.cost_price else None,
                suggested_retail_price=float(p.suggested_retail_price) if p.suggested_retail_price else None,
            ))
        
        aggregates.append(ProductNameAggregate(
            product_name=name,
            spec=items[0].spec,
            category=items[0].category,
            unit=items[0].unit,
            total_stock=total_stock,
            total_safety_stock=total_safety,
            brand_variants=len(items),
            items=variants,
        ))
    
    # 按总库存倒序
    aggregates.sort(key=lambda x: x.total_stock, reverse=True)
    return aggregates
