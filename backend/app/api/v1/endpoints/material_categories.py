"""
物料分类管理 API
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import MaterialCategory

router = APIRouter()


# ==================== 辅助函数 ====================

def generate_category_code(name: str) -> str:
    """根据名称生成编码：取每个字拼音首字母，如包装物→BZW"""
    # 简单实现：取名称中每个汉字/词的拼音首字母
    import re
    # 去除非字母数字字符，保留中文和英文
    clean_name = re.sub(r'[^\w\u4e00-\u9fff]', '', name)
    
    # 尝试用 pypinyin，如果没有则简单处理
    try:
        from pypinyin import lazy_pinyin
        pinyin_list = lazy_pinyin(clean_name)
        code = "".join([p[0].upper() for p in pinyin_list if p])
        return code[:6]  # 限制长度
    except ImportError:
        # 降级方案：取名称前3个字符的大写
        return clean_name[:3].upper() if clean_name else "CAT"


async def generate_unique_code(db: AsyncSession, base_code: str) -> str:
    """生成唯一编码，如果重复则加序号"""
    # 检查是否已存在
    result = await db.execute(
        select(MaterialCategory).where(MaterialCategory.code == base_code)
    )
    if not result.scalar_one_or_none():
        return base_code
    
    # 尝试加序号
    for i in range(1, 100):
        new_code = f"{base_code}{i}"
        result = await db.execute(
            select(MaterialCategory).where(MaterialCategory.code == new_code)
        )
        if not result.scalar_one_or_none():
            return new_code
    return f"{base_code}99"


# ==================== 请求/响应模型 ====================

class MaterialCategoryCreate(BaseModel):
    name: str
    code: str | None = None  # 可选，为空时自动生成
    sort_order: int = 0
    is_active: bool = True


class MaterialCategoryUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class MaterialCategoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    sort_order: int
    is_active: bool


class MaterialCategoryListResponse(BaseModel):
    total: int
    items: list[MaterialCategoryItem]


# ==================== CRUD ====================

@router.get("/", response_model=MaterialCategoryListResponse)
async def list_material_categories(
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
):
    """物料分类列表"""
    query = select(MaterialCategory)
    count_query = select(func.count(MaterialCategory.id))

    if is_active is not None:
        query = query.where(MaterialCategory.is_active == is_active)
        count_query = count_query.where(MaterialCategory.is_active == is_active)

    query = query.order_by(MaterialCategory.sort_order, MaterialCategory.id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query)
    items = result.scalars().all()

    return MaterialCategoryListResponse(
        total=total,
        items=[MaterialCategoryItem.model_validate(i) for i in items],
    )


@router.get("/{category_id}", response_model=MaterialCategoryItem)
async def get_material_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """物料分类详情"""
    result = await db.execute(
        select(MaterialCategory).where(MaterialCategory.id == category_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="物料分类不存在")
    return MaterialCategoryItem.model_validate(item)


@router.post("/", response_model=MaterialCategoryItem, status_code=201)
async def create_material_category(
    data: MaterialCategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建物料分类"""
    code = data.code
    if not code:
        # 自动生成编码
        base_code = generate_category_code(data.name)
        code = await generate_unique_code(db, base_code)
    
    # 检查code是否已存在
    existing = await db.execute(
        select(MaterialCategory).where(MaterialCategory.code == code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="分类编码已存在")

    item = MaterialCategory(
        name=data.name,
        code=code,
        sort_order=data.sort_order,
        is_active=data.is_active,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return MaterialCategoryItem.model_validate(item)


@router.put("/{category_id}", response_model=MaterialCategoryItem)
async def update_material_category(
    category_id: int,
    data: MaterialCategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新物料分类"""
    result = await db.execute(
        select(MaterialCategory).where(MaterialCategory.id == category_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="物料分类不存在")

    if data.name is not None:
        item.name = data.name
    if data.code is not None:
        item.code = data.code
    if data.sort_order is not None:
        item.sort_order = data.sort_order
    if data.is_active is not None:
        item.is_active = data.is_active

    await db.commit()
    await db.refresh(item)
    return MaterialCategoryItem.model_validate(item)


@router.delete("/{category_id}", status_code=204)
async def delete_material_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除物料分类（仅当没有关联物料时）"""
    from app.models import Product

    # 检查是否有关联物料
    linked = await db.execute(
        select(func.count(Product.id)).where(Product.material_category_id == category_id)
    )
    linked_count = linked.scalar() or 0
    if linked_count > 0:
        raise HTTPException(status_code=400, detail=f"该分类下还有 {linked_count} 个物料，无法删除")

    result = await db.execute(
        select(MaterialCategory).where(MaterialCategory.id == category_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="物料分类不存在")

    await db.delete(item)
    await db.commit()
    return {"detail": "已删除"}
