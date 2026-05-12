"""
品牌管理 API
支持自有品牌 + OEM代工客户品牌
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Brand, Company

router = APIRouter()


# ==================== Schema ====================

class BrandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="品牌名称")
    code: Optional[str] = Field(None, max_length=50, description="品牌编码")
    company_id: Optional[int] = Field(None, description="关联公司ID（OEM客户）")
    is_oem: bool = Field(False, description="是否为代工品牌")
    notes: Optional[str] = Field(None, description="备注")


class BrandUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, max_length=50)
    company_id: Optional[int] = None
    is_oem: Optional[bool] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    is_oem: bool = False
    is_active: bool = True
    notes: Optional[str] = None


class BrandListResponse(BaseModel):
    total: int
    items: List[BrandResponse]


# ==================== API ====================

@router.get("/", response_model=BrandListResponse)
async def list_brands(
    is_oem: Optional[bool] = Query(None, description="是否为代工品牌"),
    is_active: Optional[bool] = Query(True, description="是否启用"),
    search: Optional[str] = Query(None, description="搜索品牌名称/编码"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """品牌列表"""
    query = select(Brand)
    count_query = select(func.count(Brand.id))

    if is_oem is not None:
        query = query.where(Brand.is_oem == is_oem)
        count_query = count_query.where(Brand.is_oem == is_oem)

    if is_active is not None:
        query = query.where(Brand.is_active == is_active)
        count_query = count_query.where(Brand.is_active == is_active)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            Brand.name.ilike(search_term) | Brand.code.ilike(search_term)
        )
        count_query = count_query.where(
            Brand.name.ilike(search_term) | Brand.code.ilike(search_term)
        )

    query = query.order_by(Brand.created_at.desc())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit))
    brands = result.scalars().all()

    # 获取公司名称
    company_ids = [b.company_id for b in brands if b.company_id]
    company_names = {}
    if company_ids:
        company_result = await db.execute(
            select(Company).where(Company.id.in_(company_ids))
        )
        company_names = {c.id: c.name for c in company_result.scalars().all()}

    items = [
        BrandResponse(
            id=b.id,
            name=b.name,
            code=b.code,
            company_id=b.company_id,
            company_name=company_names.get(b.company_id) if b.company_id else None,
            is_oem=b.is_oem,
            is_active=b.is_active,
            notes=b.notes,
        )
        for b in brands
    ]

    return BrandListResponse(total=total, items=items)


@router.post("/", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(
    data: BrandCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建品牌"""
    # 检查公司是否存在
    if data.company_id:
        company = await db.get(Company, data.company_id)
        if not company:
            raise HTTPException(status_code=404, detail="关联公司不存在")

    # 检查编码是否重复
    if data.code:
        existing = await db.execute(
            select(Brand).where(Brand.code == data.code)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="品牌编码已存在")

    brand = Brand(
        name=data.name.strip(),
        code=data.code.strip() if data.code else None,
        company_id=data.company_id,
        is_oem=data.is_oem,
        notes=data.notes,
    )
    db.add(brand)
    await db.commit()
    await db.refresh(brand)

    company_name = None
    if brand.company_id:
        company = await db.get(Company, brand.company_id)
        company_name = company.name if company else None

    return BrandResponse(
        id=brand.id,
        name=brand.name,
        code=brand.code,
        company_id=brand.company_id,
        company_name=company_name,
        is_oem=brand.is_oem,
        is_active=brand.is_active,
        notes=brand.notes,
    )


@router.put("/{brand_id}", response_model=BrandResponse)
async def update_brand(
    brand_id: int,
    data: BrandUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新品牌"""
    brand = await db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")

    if data.company_id is not None:
        company = await db.get(Company, data.company_id)
        if not company:
            raise HTTPException(status_code=404, detail="关联公司不存在")
        brand.company_id = data.company_id

    if data.name is not None:
        brand.name = data.name.strip()
    if data.code is not None:
        brand.code = data.code.strip() if data.code else None
    if data.is_oem is not None:
        brand.is_oem = data.is_oem
    if data.is_active is not None:
        brand.is_active = data.is_active
    if data.notes is not None:
        brand.notes = data.notes

    await db.commit()
    await db.refresh(brand)

    company_name = None
    if brand.company_id:
        company = await db.get(Company, brand.company_id)
        company_name = company.name if company else None

    return BrandResponse(
        id=brand.id,
        name=brand.name,
        code=brand.code,
        company_id=brand.company_id,
        company_name=company_name,
        is_oem=brand.is_oem,
        is_active=brand.is_active,
        notes=brand.notes,
    )


@router.delete("/{brand_id}")
async def delete_brand(
    brand_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除品牌"""
    brand = await db.get(Brand, brand_id)
    if not brand:
        raise HTTPException(status_code=404, detail="品牌不存在")

    await db.delete(brand)
    await db.commit()
    return {"detail": "品牌已删除"}
