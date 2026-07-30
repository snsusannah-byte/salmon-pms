"""
成品定义 API（独立模块）
- 产品模板（SPU）：规格、部位、通用BOM/包装
- 品牌变体（SKU）：品牌、价格、库存、专属包装/配套
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Brand, Product
from app.models.finished_products import (
    # 重构新增
    ProductSeries,
    ProductSpec,
    ProductTemplate,
    ProductVariant,
    TemplateBOM,
    TemplatePackaging,
    TemplatePart,
    VariantAccessory,
    VariantPackaging,
    VariantPriceTier,
)

router = APIRouter()


# ==================== Schemas ====================

class TemplatePartCreate(BaseModel):
    part_name: str
    weight_g: int
    boxes: int = 1
    sort_order: int = 0


class TemplateBOMCreate(BaseModel):
    material_id: int
    quantity: float
    unit: str = "个"
    notes: str | None = None


class TemplatePackagingCreate(BaseModel):
    level: str  # box / portion
    material_id: int
    quantity: float
    unit: str = "个"
    notes: str | None = None


class ProductTemplateCreate(BaseModel):
    code: str | None = None
    name: str
    spec: str | None = None
    unit: str = "kg"
    unit_weight_kg: float | None = None
    portion_weight_g: int | None = None
    portion_boxes: int | None = None
    series_id: int | None = None
    series_code: str | None = None
    series_name: str | None = None
    notes: str | None = None
    parts: list[TemplatePartCreate] = []
    boms: list[TemplateBOMCreate] = []
    packagings: list[TemplatePackagingCreate] = []


class ProductTemplateUpdate(BaseModel):
    name: str | None = None
    spec: str | None = None
    unit: str | None = None
    unit_weight_kg: float | None = None
    portion_weight_g: int | None = None
    portion_boxes: int | None = None
    series_id: int | None = None
    series_code: str | None = None
    series_name: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class TemplatePartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    part_name: str
    weight_g: int
    boxes: int
    sort_order: int


class TemplateBOMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    material_id: int
    material_name: str | None = None
    quantity: float
    unit: str
    notes: str | None = None


class TemplatePackagingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    level: str
    material_id: int
    material_name: str | None = None
    quantity: float
    unit: str
    notes: str | None = None


class ProductTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    spec: str | None = None
    unit: str
    unit_weight_kg: float | None = None
    portion_weight_g: int | None = None
    portion_boxes: int | None = None
    series_id: int | None = None
    series_code: str | None = None
    series_name: str | None = None
    is_active: bool
    notes: str | None = None
    parts: list[TemplatePartResponse] = []
    boms: list[TemplateBOMResponse] = []
    packagings: list[TemplatePackagingResponse] = []
    variant_count: int = 0
    created_at: str
    updated_at: str


class TemplateListResponse(BaseModel):
    total: int
    items: list[ProductTemplateResponse]


# --- Variant Schemas ---

class VariantPackagingCreate(BaseModel):
    level: str
    material_id: int
    quantity: float
    unit: str = "个"
    is_override: bool = False
    notes: str | None = None


class VariantAccessoryCreate(BaseModel):
    accessory_id: int
    quantity: float
    unit: str = "个"
    notes: str | None = None


class ProductVariantCreate(BaseModel):
    brand_id: int | None = None
    code: str | None = None
    cost_price: float | None = None
    suggested_retail_price: float | None = None
    wholesale_price: float | None = None
    min_price: float | None = None
    stock_quantity: int = 0
    safety_stock: int = 0
    notes: str | None = None
    packagings: list[VariantPackagingCreate] = []
    accessories: list[VariantAccessoryCreate] = []


class ProductVariantUpdate(BaseModel):
    brand_id: int | None = None
    code: str | None = None
    cost_price: float | None = None
    suggested_retail_price: float | None = None
    wholesale_price: float | None = None
    min_price: float | None = None
    stock_quantity: int | None = None
    safety_stock: int | None = None
    is_active: bool | None = None
    notes: str | None = None


class VariantPackagingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    level: str
    material_id: int
    material_name: str | None = None
    quantity: float
    unit: str
    is_override: bool
    notes: str | None = None


class VariantAccessoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    accessory_id: int
    accessory_name: str | None = None
    quantity: float
    unit: str
    notes: str | None = None


class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    template_name: str
    spec_id: int | None = None
    spec_name: str | None = None
    brand_id: int | None = None
    brand_name: str | None = None
    brand_is_oem: bool = False
    code: str
    name: str
    cost_price: float | None = None
    suggested_retail_price: float | None = None
    wholesale_price: float | None = None
    min_price: float | None = None
    stock_quantity: int
    safety_stock: int
    is_active: bool
    notes: str | None = None
    packagings: list[VariantPackagingResponse] = []
    accessories: list[VariantAccessoryResponse] = []
    created_at: str
    updated_at: str


class VariantListResponse(BaseModel):
    total: int
    items: list[ProductVariantResponse]


# ==================== Template APIs ====================

@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    search: str | None = Query(None),
    is_active: bool | None = Query(True),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """获取成品模板列表"""
    query = select(ProductTemplate)
    count_query = select(func.count(ProductTemplate.id))

    # FastAPI Query 默认值处理
    is_active_bool = True if is_active is None else bool(is_active)
    query = query.where(ProductTemplate.is_active == is_active_bool)
    count_query = count_query.where(ProductTemplate.is_active == is_active_bool)

    if search:
        search_term = f"%{search}%"
        query = query.where(
            ProductTemplate.name.ilike(search_term) |
            ProductTemplate.code.ilike(search_term)
        )
        count_query = count_query.where(
            ProductTemplate.name.ilike(search_term) |
            ProductTemplate.code.ilike(search_term)
        )

    query = query.order_by(ProductTemplate.created_at.desc())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit))
    templates = result.scalars().all()

    # 获取变体数量
    template_ids = [t.id for t in templates]
    variant_counts = {}
    if template_ids:
        count_result = await db.execute(
            select(ProductVariant.template_id, func.count(ProductVariant.id))
            .where(ProductVariant.template_id.in_(template_ids))
            .group_by(ProductVariant.template_id)
        )
        variant_counts = {tid: c for tid, c in count_result.all()}

    # 批量查询部位（列表显示用）
    parts_result = await db.execute(
        select(TemplatePart).where(TemplatePart.template_id.in_(template_ids)).order_by(TemplatePart.sort_order)
    )
    parts_map = {}
    for p in parts_result.scalars().all():
        if p.template_id not in parts_map:
            parts_map[p.template_id] = []
        parts_map[p.template_id].append(p)

    items = []
    for t in templates:
        parts = parts_map.get(t.id, [])
        items.append(ProductTemplateResponse(
            id=t.id,
            code=t.code,
            name=t.name,
            spec=t.spec,
            unit=t.unit,
            unit_weight_kg=float(t.unit_weight_kg) if t.unit_weight_kg else None,
            portion_weight_g=t.portion_weight_g,
            portion_boxes=t.portion_boxes,
            series_id=t.series_id,
            series_code=t.series_code,
            series_name=t.series_name,
            is_active=t.is_active,
            notes=t.notes,
            parts=[TemplatePartResponse(id=p.id, part_name=p.part_name, weight_g=p.weight_g, boxes=p.boxes, sort_order=p.sort_order) for p in parts],
            boms=[],
            packagings=[],
            variant_count=variant_counts.get(t.id, 0),
            created_at=str(t.created_at),
            updated_at=str(t.updated_at),
        ))

    return TemplateListResponse(total=total, items=items)


@router.post("/templates", response_model=ProductTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: ProductTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建成品模板（SPU）"""
    # 生成编码
    code = data.code
    if not code:
        # 查询当前最大序号
        result = await db.execute(
            select(ProductTemplate.code)
            .where(ProductTemplate.code.like("TP-%"))
            .order_by(ProductTemplate.code.desc())
        )
        codes = result.scalars().all()
        max_num = 0
        for c in codes:
            try:
                num = int(c.split("-")[-1])
                if num > max_num:
                    max_num = num
            except Exception:
                pass
        code = f"TP-{max_num + 1:03d}"

    template = ProductTemplate(
        code=code,
        name=data.name.strip(),
        spec=data.spec.strip() if data.spec else None,
        unit=data.unit,
        unit_weight_kg=Decimal(str(data.unit_weight_kg)) if data.unit_weight_kg else None,
        portion_weight_g=data.portion_weight_g,
        portion_boxes=data.portion_boxes,
        series_id=data.series_id,
        series_code=data.series_code.strip() if data.series_code else None,
        series_name=data.series_name.strip() if data.series_name else None,
        notes=data.notes,
    )
    db.add(template)
    await db.flush()  # 获取 template.id

    # 创建部位
    for p in data.parts:
        part = TemplatePart(
            template_id=template.id,
            part_name=p.part_name.strip(),
            weight_g=p.weight_g,
            boxes=p.boxes,
            sort_order=p.sort_order,
        )
        db.add(part)

    # 创建BOM
    for b in data.boms:
        bom = TemplateBOM(
            template_id=template.id,
            material_id=b.material_id,
            quantity=Decimal(str(b.quantity)),
            unit=b.unit,
            notes=b.notes,
        )
        db.add(bom)

    # 创建包装物
    for p in data.packagings:
        pkg = TemplatePackaging(
            template_id=template.id,
            level=p.level,
            material_id=p.material_id,
            quantity=Decimal(str(p.quantity)),
            unit=p.unit,
            notes=p.notes,
        )
        db.add(pkg)

    await db.commit()
    await db.refresh(template)

    # 手动查询关联数据（避免 lazy="raise" 问题）
    parts_result = await db.execute(
        select(TemplatePart).where(TemplatePart.template_id == template.id)
    )
    parts = parts_result.scalars().all()

    boms_result = await db.execute(
        select(TemplateBOM).where(TemplateBOM.template_id == template.id)
    )
    boms = boms_result.scalars().all()
    bom_material_ids = [b.material_id for b in boms]
    bom_material_names = {}
    if bom_material_ids:
        mat_result = await db.execute(select(Product).where(Product.id.in_(bom_material_ids)))
        bom_material_names = {m.id: m.name for m in mat_result.scalars().all()}

    pkgs_result = await db.execute(
        select(TemplatePackaging).where(TemplatePackaging.template_id == template.id)
    )
    pkgs = pkgs_result.scalars().all()
    pkg_material_ids = [p.material_id for p in pkgs]
    pkg_material_names = {}
    if pkg_material_ids:
        mat_result = await db.execute(select(Product).where(Product.id.in_(pkg_material_ids)))
        pkg_material_names = {m.id: m.name for m in mat_result.scalars().all()}

    return ProductTemplateResponse(
        id=template.id,
        code=template.code,
        name=template.name,
        spec=template.spec,
        unit=template.unit,
        unit_weight_kg=float(template.unit_weight_kg) if template.unit_weight_kg else None,
        portion_weight_g=template.portion_weight_g,
        portion_boxes=template.portion_boxes,
        series_id=template.series_id,
        series_code=template.series_code,
        series_name=template.series_name,
        is_active=template.is_active,
        notes=template.notes,
        parts=[TemplatePartResponse(id=p.id, part_name=p.part_name, weight_g=p.weight_g, boxes=p.boxes, sort_order=p.sort_order) for p in parts],
        boms=[TemplateBOMResponse(
            id=b.id, material_id=b.material_id, material_name=bom_material_names.get(b.material_id),
            quantity=float(b.quantity), unit=b.unit, notes=b.notes
        ) for b in boms],
        packagings=[TemplatePackagingResponse(
            id=p.id, level=p.level, material_id=p.material_id,
            material_name=pkg_material_names.get(p.material_id),
            quantity=float(p.quantity), unit=p.unit, notes=p.notes
        ) for p in pkgs],
        variant_count=0,
        created_at=str(template.created_at),
        updated_at=str(template.updated_at),
    )


@router.get("/templates/{template_id}", response_model=ProductTemplateResponse)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取模板详情"""
    template = await db.get(ProductTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 变体数量
    count_result = await db.execute(
        select(func.count(ProductVariant.id)).where(ProductVariant.template_id == template_id)
    )
    variant_count = count_result.scalar() or 0

    # 手动查询关联数据
    parts_result = await db.execute(select(TemplatePart).where(TemplatePart.template_id == template_id))
    parts = parts_result.scalars().all()

    boms_result = await db.execute(select(TemplateBOM).where(TemplateBOM.template_id == template_id))
    boms = boms_result.scalars().all()
    bom_material_ids = [b.material_id for b in boms]
    bom_material_names = {}
    if bom_material_ids:
        mat_result = await db.execute(select(Product).where(Product.id.in_(bom_material_ids)))
        bom_material_names = {m.id: m.name for m in mat_result.scalars().all()}

    pkgs_result = await db.execute(select(TemplatePackaging).where(TemplatePackaging.template_id == template_id))
    pkgs = pkgs_result.scalars().all()
    pkg_material_ids = [p.material_id for p in pkgs]
    pkg_material_names = {}
    if pkg_material_ids:
        mat_result = await db.execute(select(Product).where(Product.id.in_(pkg_material_ids)))
        pkg_material_names = {m.id: m.name for m in mat_result.scalars().all()}

    return ProductTemplateResponse(
        id=template.id,
        code=template.code,
        name=template.name,
        spec=template.spec,
        unit=template.unit,
        unit_weight_kg=float(template.unit_weight_kg) if template.unit_weight_kg else None,
        portion_weight_g=template.portion_weight_g,
        portion_boxes=template.portion_boxes,
        series_id=template.series_id,
        series_code=template.series_code,
        series_name=template.series_name,
        is_active=template.is_active,
        notes=template.notes,
        parts=[TemplatePartResponse(id=p.id, part_name=p.part_name, weight_g=p.weight_g, boxes=p.boxes, sort_order=p.sort_order) for p in parts],
        boms=[TemplateBOMResponse(
            id=b.id, material_id=b.material_id, material_name=bom_material_names.get(b.material_id),
            quantity=float(b.quantity), unit=b.unit, notes=b.notes
        ) for b in boms],
        packagings=[TemplatePackagingResponse(
            id=p.id, level=p.level, material_id=p.material_id,
            material_name=pkg_material_names.get(p.material_id),
            quantity=float(p.quantity), unit=p.unit, notes=p.notes
        ) for p in pkgs],
        variant_count=variant_count,
        created_at=str(template.created_at),
        updated_at=str(template.updated_at),
    )


@router.put("/templates/{template_id}", response_model=ProductTemplateResponse)
async def update_template(
    template_id: int,
    data: ProductTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新模板（只更新基本信息，不更新部位/BOM/包装）"""
    template = await db.get(ProductTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if data.name is not None:
        template.name = data.name.strip()
    if data.spec is not None:
        template.spec = data.spec.strip() if data.spec else None
    if data.unit is not None:
        template.unit = data.unit
    if data.unit_weight_kg is not None:
        template.unit_weight_kg = Decimal(str(data.unit_weight_kg))
    if data.portion_weight_g is not None:
        template.portion_weight_g = data.portion_weight_g
    if data.portion_boxes is not None:
        template.portion_boxes = data.portion_boxes
    if data.series_id is not None:
        template.series_id = data.series_id
        # 自动填充 series_code / series_name
        if data.series_id:
            from app.models.finished_products import ProductSeries
            series = await db.get(ProductSeries, data.series_id)
            if series:
                template.series_code = series.code
                template.series_name = series.name
            else:
                template.series_code = None
                template.series_name = None
        else:
            template.series_code = None
            template.series_name = None
    if data.series_code is not None:
        template.series_code = data.series_code.strip() if data.series_code else None
    if data.series_name is not None:
        template.series_name = data.series_name.strip() if data.series_name else None
    if data.is_active is not None:
        template.is_active = data.is_active
    if data.notes is not None:
        template.notes = data.notes

    await db.commit()
    await db.refresh(template)

    return await get_template(template_id, db)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除模板（级联删除变体）"""
    template = await db.get(ProductTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    await db.delete(template)
    await db.commit()
    return {"detail": "模板已删除"}


# ==================== Variant APIs ====================

@router.get("/templates/{template_id}/variants", response_model=VariantListResponse)
async def list_variants(
    template_id: int,
    brand_id: int | None = Query(None),
    is_active: bool | None = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """获取模板的品牌变体列表"""
    # 验证模板存在
    template = await db.get(ProductTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    query = select(ProductVariant).where(ProductVariant.template_id == template_id)
    count_query = select(func.count(ProductVariant.id)).where(ProductVariant.template_id == template_id)

    if brand_id is not None:
        query = query.where(ProductVariant.brand_id == brand_id)
        count_query = count_query.where(ProductVariant.brand_id == brand_id)

    if is_active is not None:
        query = query.where(ProductVariant.is_active == is_active)
        count_query = count_query.where(ProductVariant.is_active == is_active)

    query = query.order_by(ProductVariant.created_at.desc())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit))
    variants = result.scalars().all()

    # 获取品牌信息
    brand_ids = [v.brand_id for v in variants if v.brand_id]
    brand_map = {}
    if brand_ids:
        brand_result = await db.execute(
            select(Brand).where(Brand.id.in_(brand_ids))
        )
        brand_map = {b.id: b for b in brand_result.scalars().all()}

    # 批量查询变体包装物
    variant_ids = [v.id for v in variants]
    vp_map = {}
    if variant_ids:
        vp_result = await db.execute(
            select(VariantPackaging).where(VariantPackaging.variant_id.in_(variant_ids))
        )
        for vp in vp_result.scalars().all():
            if vp.variant_id not in vp_map:
                vp_map[vp.variant_id] = []
            vp_map[vp.variant_id].append(vp)
    # 查询物料名称
    vp_material_ids = [vp.material_id for vps in vp_map.values() for vp in vps]
    vp_mat_names = {}
    if vp_material_ids:
        mat_result = await db.execute(select(Product).where(Product.id.in_(vp_material_ids)))
        vp_mat_names = {m.id: m.name for m in mat_result.scalars().all()}

    # 批量查询变体配套
    va_map = {}
    if variant_ids:
        va_result = await db.execute(
            select(VariantAccessory).where(VariantAccessory.variant_id.in_(variant_ids))
        )
        for va in va_result.scalars().all():
            if va.variant_id not in va_map:
                va_map[va.variant_id] = []
            va_map[va.variant_id].append(va)
    # 查询配套名称
    va_accessory_ids = [va.accessory_id for vas in va_map.values() for va in vas]
    va_acc_names = {}
    if va_accessory_ids:
        acc_result = await db.execute(select(Product).where(Product.id.in_(va_accessory_ids)))
        va_acc_names = {a.id: a.name for a in acc_result.scalars().all()}

    items = []
    for v in variants:
        brand = brand_map.get(v.brand_id) if v.brand_id else None
        vps = vp_map.get(v.id, [])
        vas = va_map.get(v.id, [])
        spec = await db.get(ProductSpec, v.spec_id) if v.spec_id else None
        items.append(ProductVariantResponse(
            id=v.id,
            template_id=v.template_id,
            template_name=template.name,
            spec_id=v.spec_id,
            spec_name=spec.name if spec else None,
            brand_id=v.brand_id,
            brand_name=brand.name if brand else None,
            brand_is_oem=brand.is_oem if brand else False,
            code=v.code,
            name=v.name,
            cost_price=float(v.cost_price) if v.cost_price else None,
            suggested_retail_price=float(v.suggested_retail_price) if v.suggested_retail_price else None,
            wholesale_price=float(v.wholesale_price) if v.wholesale_price else None,
            min_price=float(v.min_price) if v.min_price else None,
            stock_quantity=v.stock_quantity or 0,
            safety_stock=v.safety_stock or 0,
            is_active=v.is_active,
            notes=v.notes,
            packagings=[VariantPackagingResponse(
                id=p.id, level=p.level, material_id=p.material_id,
                material_name=vp_mat_names.get(p.material_id),
                quantity=float(p.quantity), unit=p.unit, is_override=p.is_override, notes=p.notes
            ) for p in vps],
            accessories=[VariantAccessoryResponse(
                id=a.id, accessory_id=a.accessory_id,
                accessory_name=va_acc_names.get(a.accessory_id),
                quantity=float(a.quantity), unit=a.unit, notes=a.notes
            ) for a in vas],
            created_at=str(v.created_at),
            updated_at=str(v.updated_at),
        ))

    return VariantListResponse(total=total, items=items)


@router.post("/templates/{template_id}/variants", response_model=ProductVariantResponse, status_code=status.HTTP_201_CREATED)
async def create_variant(
    template_id: int,
    data: ProductVariantCreate,
    db: AsyncSession = Depends(get_db),
):
    """为模板添加品牌变体（SKU）"""
    template = await db.get(ProductTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 验证品牌
    brand = None
    if data.brand_id:
        brand = await db.get(Brand, data.brand_id)
        if not brand:
            raise HTTPException(status_code=404, detail="品牌不存在")

    # 生成编码
    code = data.code
    if not code:
        prefix = "VAR"
        if brand and brand.code:
            prefix = brand.code.upper()
        # 查询当前最大序号
        result = await db.execute(
            select(ProductVariant.code)
            .where(ProductVariant.template_id == template_id)
            .where(ProductVariant.code.like(f"{prefix}-%"))
            .order_by(ProductVariant.code.desc())
        )
        codes = result.scalars().all()
        max_num = 0
        for c in codes:
            try:
                num = int(c.split("-")[-1])
                if num > max_num:
                    max_num = num
            except Exception:
                pass
        code = f"{prefix}-{max_num + 1:03d}"

    # 生成名称：品牌名 + 模板名
    name = template.name
    if brand:
        name = f"{brand.name}-{template.name}"

    # 检查重复
    existing = await db.execute(
        select(ProductVariant).where(
            ProductVariant.template_id == template_id,
            ProductVariant.brand_id == data.brand_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该品牌已存在变体")

    variant = ProductVariant(
        template_id=template_id,
        brand_id=data.brand_id,
        code=code,
        name=name,
        cost_price=Decimal(str(data.cost_price)) if data.cost_price else None,
        suggested_retail_price=Decimal(str(data.suggested_retail_price)) if data.suggested_retail_price else None,
        wholesale_price=Decimal(str(data.wholesale_price)) if data.wholesale_price else None,
        min_price=Decimal(str(data.min_price)) if data.min_price else None,
        stock_quantity=data.stock_quantity,
        safety_stock=data.safety_stock,
        notes=data.notes,
    )
    db.add(variant)
    await db.flush()

    # 创建专属包装
    for p in data.packagings:
        pkg = VariantPackaging(
            variant_id=variant.id,
            level=p.level,
            material_id=p.material_id,
            quantity=Decimal(str(p.quantity)),
            unit=p.unit,
            is_override=p.is_override,
            notes=p.notes,
        )
        db.add(pkg)

    # 创建专属配套
    for a in data.accessories:
        acc = VariantAccessory(
            variant_id=variant.id,
            accessory_id=a.accessory_id,
            quantity=Decimal(str(a.quantity)),
            unit=a.unit,
            notes=a.notes,
        )
        db.add(acc)

    await db.commit()
    await db.refresh(variant)

    return ProductVariantResponse(
        id=variant.id,
        template_id=variant.template_id,
        template_name=template.name,
        brand_id=variant.brand_id,
        brand_name=brand.name if brand else None,
        brand_is_oem=brand.is_oem if brand else False,
        code=variant.code,
        name=variant.name,
        cost_price=float(variant.cost_price) if variant.cost_price else None,
        suggested_retail_price=float(variant.suggested_retail_price) if variant.suggested_retail_price else None,
        wholesale_price=float(variant.wholesale_price) if variant.wholesale_price else None,
        min_price=float(variant.min_price) if variant.min_price else None,
        stock_quantity=variant.stock_quantity or 0,
        safety_stock=variant.safety_stock or 0,
        is_active=variant.is_active,
        notes=variant.notes,
        packagings=[VariantPackagingResponse(
            id=p.id, level=p.level, material_id=p.material_id,
            material_name=p.material.name if p.material else None,
            quantity=float(p.quantity), unit=p.unit, is_override=p.is_override, notes=p.notes
        ) for p in variant.packagings],
        accessories=[VariantAccessoryResponse(
            id=a.id, accessory_id=a.accessory_id,
            accessory_name=a.accessory.name if a.accessory else None,
            quantity=float(a.quantity), unit=a.unit, notes=a.notes
        ) for a in variant.accessories],
        created_at=str(variant.created_at),
        updated_at=str(variant.updated_at),
    )


@router.put("/templates/{template_id}/variants/{variant_id}", response_model=ProductVariantResponse)
async def update_variant(
    template_id: int,
    variant_id: int,
    data: ProductVariantUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新品牌变体"""
    variant = await db.get(ProductVariant, variant_id)
    if not variant or variant.template_id != template_id:
        raise HTTPException(status_code=404, detail="变体不存在")

    if data.brand_id is not None:
        variant.brand_id = data.brand_id
    if data.code is not None:
        variant.code = data.code.strip()
    if data.cost_price is not None:
        variant.cost_price = Decimal(str(data.cost_price))
    if data.suggested_retail_price is not None:
        variant.suggested_retail_price = Decimal(str(data.suggested_retail_price))
    if data.wholesale_price is not None:
        variant.wholesale_price = Decimal(str(data.wholesale_price))
    if data.min_price is not None:
        variant.min_price = Decimal(str(data.min_price))
    if data.stock_quantity is not None:
        variant.stock_quantity = data.stock_quantity
    if data.safety_stock is not None:
        variant.safety_stock = data.safety_stock
    if data.is_active is not None:
        variant.is_active = data.is_active
    if data.notes is not None:
        variant.notes = data.notes

    # 更新名称
    template = await db.get(ProductTemplate, template_id)
    brand = await db.get(Brand, variant.brand_id) if variant.brand_id else None
    variant.name = f"{brand.name}-{template.name}" if brand else template.name

    await db.commit()
    await db.refresh(variant)

    # 返回完整响应
    brand_obj = await db.get(Brand, variant.brand_id) if variant.brand_id else None
    return ProductVariantResponse(
        id=variant.id,
        template_id=variant.template_id,
        template_name=template.name,
        brand_id=variant.brand_id,
        brand_name=brand_obj.name if brand_obj else None,
        brand_is_oem=brand_obj.is_oem if brand_obj else False,
        code=variant.code,
        name=variant.name,
        cost_price=float(variant.cost_price) if variant.cost_price else None,
        suggested_retail_price=float(variant.suggested_retail_price) if variant.suggested_retail_price else None,
        wholesale_price=float(variant.wholesale_price) if variant.wholesale_price else None,
        min_price=float(variant.min_price) if variant.min_price else None,
        stock_quantity=variant.stock_quantity or 0,
        safety_stock=variant.safety_stock or 0,
        is_active=variant.is_active,
        notes=variant.notes,
        packagings=[VariantPackagingResponse(
            id=p.id, level=p.level, material_id=p.material_id,
            material_name=p.material.name if p.material else None,
            quantity=float(p.quantity), unit=p.unit, is_override=p.is_override, notes=p.notes
        ) for p in variant.packagings],
        accessories=[VariantAccessoryResponse(
            id=a.id, accessory_id=a.accessory_id,
            accessory_name=a.accessory.name if a.accessory else None,
            quantity=float(a.quantity), unit=a.unit, notes=a.notes
        ) for a in variant.accessories],
        created_at=str(variant.created_at),
        updated_at=str(variant.updated_at),
    )


@router.delete("/templates/{template_id}/variants/{variant_id}")
async def delete_variant(
    template_id: int,
    variant_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除品牌变体"""
    variant = await db.get(ProductVariant, variant_id)
    if not variant or variant.template_id != template_id:
        raise HTTPException(status_code=404, detail="变体不存在")

    await db.delete(variant)
    await db.commit()
    return {"detail": "变体已删除"}


# ==================== 重构新增：Schemas ====================

class ProductSeriesCreate(BaseModel):
    code: str | None = None  # 为空时自动生成
    name: str
    sort_order: int | None = None  # 为空时取最大值+1
    notes: str | None = None


class ProductSeriesUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    notes: str | None = None


class ProductSeriesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    sort_order: int
    is_active: bool
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProductSpecCreate(BaseModel):
    code: str | None = None  # 为空时自动生成
    name: str
    parts_config: str | None = None
    total_weight_g: int | None = None
    portion_count: int = 1
    box_count: int = 1
    sort_order: int = 0
    notes: str | None = None


class ProductSpecUpdate(BaseModel):
    name: str | None = None
    parts_config: str | None = None
    total_weight_g: int | None = None
    portion_count: int | None = None
    box_count: int | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    notes: str | None = None


class ProductSpecResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    template_id: int
    code: str
    name: str
    parts_config: str | None = None
    total_weight_g: int | None = None
    portion_count: int | None = 1
    box_count: int | None = 1
    sort_order: int | None = 0
    is_active: bool | None = True
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class VariantPriceTierCreate(BaseModel):
    tier_type: str
    tier_key: str
    tier_name: str
    min_qty: int = 1
    max_qty: int | None = None
    price: float
    valid_from: str | None = None
    valid_to: str | None = None
    notes: str | None = None


class VariantPriceTierUpdate(BaseModel):
    tier_type: str | None = None
    tier_key: str | None = None
    tier_name: str | None = None
    min_qty: int | None = None
    max_qty: int | None = None
    price: float | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    is_active: bool | None = None
    notes: str | None = None


class VariantPriceTierResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    variant_id: int
    tier_type: str
    tier_key: str
    tier_name: str
    min_qty: int
    max_qty: int | None = None
    price: float
    valid_from: str | None = None
    valid_to: str | None = None
    is_active: bool
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


# ==================== 重构新增：系列 API ====================

@router.get("/series", response_model=list[ProductSeriesResponse])
async def list_series(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """获取所有产品系列"""
    result = await db.execute(
        select(ProductSeries).order_by(ProductSeries.sort_order).offset(skip).limit(limit)
    )
    series = result.scalars().all()
    return [
        ProductSeriesResponse(
            id=s.id, code=s.code, name=s.name, sort_order=s.sort_order,
            is_active=s.is_active, notes=s.notes,
            created_at=str(s.created_at) if s.created_at else None,
            updated_at=str(s.updated_at) if s.updated_at else None,
        ) for s in series
    ]


@router.post("/series", response_model=ProductSeriesResponse)
async def create_series(
    data: ProductSeriesCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建产品系列"""
    # 自动编码：取现有系列中最大 id，生成 S{n}；若用户已填则校验唯一性
    series_code = data.code
    if not series_code:
        max_id_result = await db.execute(select(func.max(ProductSeries.id)))
        max_id = max_id_result.scalar() or 0
        series_code = f"S{max_id + 1}"

    existing = await db.execute(select(ProductSeries).where(ProductSeries.code == series_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"系列编码 {series_code} 已存在")

    # 自动排序：取最大值+1
    sort_order = data.sort_order
    if sort_order is None:
        max_sort_result = await db.execute(select(func.max(ProductSeries.sort_order)))
        max_sort = max_sort_result.scalar() or 0
        sort_order = int(max_sort) + 1

    create_data = data.model_dump(exclude={"code", "sort_order"})
    create_data["code"] = series_code
    create_data["sort_order"] = sort_order
    series = ProductSeries(**create_data)
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return ProductSeriesResponse(
        id=series.id, code=series.code, name=series.name,
        sort_order=series.sort_order, is_active=series.is_active,
        notes=series.notes,
        created_at=str(series.created_at) if series.created_at else None,
        updated_at=str(series.updated_at) if series.updated_at else None,
    )


@router.get("/series/{series_id}", response_model=ProductSeriesResponse)
async def get_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取系列详情"""
    series = await db.get(ProductSeries, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="系列不存在")
    return ProductSeriesResponse(
        id=series.id, code=series.code, name=series.name,
        sort_order=series.sort_order, is_active=series.is_active,
        notes=series.notes,
        created_at=str(series.created_at) if series.created_at else None,
        updated_at=str(series.updated_at) if series.updated_at else None,
    )


@router.put("/series/{series_id}", response_model=ProductSeriesResponse)
async def update_series(
    series_id: int,
    data: ProductSeriesUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新系列"""
    series = await db.get(ProductSeries, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="系列不存在")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(series, field, value)

    await db.commit()
    await db.refresh(series)
    return ProductSeriesResponse(
        id=series.id, code=series.code, name=series.name,
        sort_order=series.sort_order, is_active=series.is_active,
        notes=series.notes,
        created_at=str(series.created_at) if series.created_at else None,
        updated_at=str(series.updated_at) if series.updated_at else None,
    )


@router.delete("/series/{series_id}")
async def delete_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除系列（仅当无关联模板时）"""
    series = await db.get(ProductSeries, series_id)
    if not series:
        raise HTTPException(status_code=404, detail="系列不存在")

    templates = await db.execute(
        select(func.count()).where(ProductTemplate.series_id == series_id)
    )
    if templates.scalar() > 0:
        raise HTTPException(status_code=400, detail="该系列下存在产品模板，无法删除")

    await db.delete(series)
    await db.commit()
    return {"detail": "系列已删除"}


# ==================== 重构新增：规格 API ====================

@router.get("/templates/{template_id}/specs", response_model=list[ProductSpecResponse])
async def list_specs(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取模板下的所有规格"""
    template = await db.get(ProductTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    result = await db.execute(
        select(ProductSpec)
        .where(ProductSpec.template_id == template_id)
        .order_by(ProductSpec.sort_order)
    )
    specs = result.scalars().all()
    return [
        ProductSpecResponse(
            id=s.id, template_id=s.template_id, code=s.code, name=s.name,
            parts_config=s.parts_config, total_weight_g=s.total_weight_g,
            portion_count=s.portion_count, box_count=s.box_count,
            sort_order=s.sort_order, is_active=s.is_active, notes=s.notes,
            created_at=str(s.created_at) if s.created_at else None,
            updated_at=str(s.updated_at) if s.updated_at else None,
        ) for s in specs
    ]


@router.post("/templates/{template_id}/specs", response_model=ProductSpecResponse)
async def create_spec(
    template_id: int,
    data: ProductSpecCreate,
    db: AsyncSession = Depends(get_db),
):
    """为模板创建规格"""
    template = await db.get(ProductTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 自动生成规格编码：优先使用模板编码，冲突时追加 -1/-2...
    spec_code = data.code
    if not spec_code:
        base = template.code or f"T{template_id}"
        candidate = base
        suffix = 0
        existing_codes = {
            c for c in (
                await db.execute(
                    select(ProductSpec.code).where(ProductSpec.template_id == template_id)
                )
            ).scalars().all()
        }
        while candidate in existing_codes:
            suffix += 1
            candidate = f"{base}-{suffix}"
        spec_code = candidate

    create_data = data.model_dump(exclude={"code"})
    create_data["code"] = spec_code
    spec = ProductSpec(template_id=template_id, **create_data)
    db.add(spec)
    await db.commit()
    await db.refresh(spec)
    return ProductSpecResponse(
        id=spec.id, template_id=spec.template_id, code=spec.code, name=spec.name,
        parts_config=spec.parts_config, total_weight_g=spec.total_weight_g,
        portion_count=spec.portion_count, box_count=spec.box_count,
        sort_order=spec.sort_order, is_active=spec.is_active, notes=spec.notes,
        created_at=str(spec.created_at) if spec.created_at else None,
        updated_at=str(spec.updated_at) if spec.updated_at else None,
    )


@router.get("/templates/{template_id}/specs/{spec_id}", response_model=ProductSpecResponse)
async def get_spec(
    template_id: int,
    spec_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取规格详情"""
    spec = await db.get(ProductSpec, spec_id)
    if not spec or spec.template_id != template_id:
        raise HTTPException(status_code=404, detail="规格不存在")
    return ProductSpecResponse(
        id=spec.id, template_id=spec.template_id, code=spec.code, name=spec.name,
        parts_config=spec.parts_config, total_weight_g=spec.total_weight_g,
        portion_count=spec.portion_count, box_count=spec.box_count,
        sort_order=spec.sort_order, is_active=spec.is_active, notes=spec.notes,
        created_at=str(spec.created_at) if spec.created_at else None,
        updated_at=str(spec.updated_at) if spec.updated_at else None,
    )


@router.put("/templates/{template_id}/specs/{spec_id}", response_model=ProductSpecResponse)
async def update_spec(
    template_id: int,
    spec_id: int,
    data: ProductSpecUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新规格"""
    spec = await db.get(ProductSpec, spec_id)
    if not spec or spec.template_id != template_id:
        raise HTTPException(status_code=404, detail="规格不存在")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(spec, field, value)

    await db.commit()
    await db.refresh(spec)
    return ProductSpecResponse(
        id=spec.id, template_id=spec.template_id, code=spec.code, name=spec.name,
        parts_config=spec.parts_config, total_weight_g=spec.total_weight_g,
        portion_count=spec.portion_count, box_count=spec.box_count,
        sort_order=spec.sort_order, is_active=spec.is_active, notes=spec.notes,
        created_at=str(spec.created_at) if spec.created_at else None,
        updated_at=str(spec.updated_at) if spec.updated_at else None,
    )


@router.delete("/templates/{template_id}/specs/{spec_id}")
async def delete_spec(
    template_id: int,
    spec_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除规格（仅当无关联SKU时）"""
    spec = await db.get(ProductSpec, spec_id)
    if not spec or spec.template_id != template_id:
        raise HTTPException(status_code=404, detail="规格不存在")

    variants = await db.execute(
        select(func.count()).where(ProductVariant.spec_id == spec_id)
    )
    if variants.scalar() > 0:
        raise HTTPException(status_code=400, detail="该规格下存在品牌变体，无法删除")

    await db.delete(spec)
    await db.commit()
    return {"detail": "规格已删除"}


# ==================== 重构新增：价格层级 API ====================

@router.get("/variants", response_model=VariantListResponse)
async def list_all_variants(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """获取所有品牌变体（SKU）"""
    result = await db.execute(
        select(ProductVariant)
        .order_by(ProductVariant.id.desc())
        .offset(skip)
        .limit(limit)
    )
    variants = result.scalars().all()

    items = []
    for v in variants:
        template = await db.get(ProductTemplate, v.template_id)
        brand = await db.get(Brand, v.brand_id)
        spec = await db.get(ProductSpec, v.spec_id) if v.spec_id else None
        items.append({
            "id": v.id,
            "template_id": v.template_id,
            "brand_id": v.brand_id,
            "spec_id": v.spec_id,
            "code": v.code,
            "name": v.name,
            "cost_price": float(v.cost_price) if v.cost_price else None,
            "suggested_retail_price": float(v.suggested_retail_price) if v.suggested_retail_price else None,
            "wholesale_price": float(v.wholesale_price) if v.wholesale_price else None,
            "min_price": float(v.min_price) if v.min_price else None,
            "stock_quantity": v.stock_quantity,
            "safety_stock": v.safety_stock,
            "is_active": v.is_active,
            "notes": v.notes,
            "created_at": str(v.created_at) if v.created_at else None,
            "updated_at": str(v.updated_at) if v.updated_at else None,
            "template_name": template.name if template else None,
            "brand_name": brand.name if brand else None,
            "spec_name": spec.name if spec else None,
        })

    total_result = await db.execute(select(func.count()).select_from(ProductVariant))
    total = total_result.scalar()

    return {"items": items, "total": total}


@router.get("/variants/{variant_id}/price-tiers", response_model=list[VariantPriceTierResponse])
async def list_price_tiers(
    variant_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取SKU的所有价格层级"""
    variant = await db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="变体不存在")

    result = await db.execute(
        select(VariantPriceTier)
        .where(VariantPriceTier.variant_id == variant_id)
        .order_by(VariantPriceTier.min_qty)
    )
    tiers = result.scalars().all()
    return [
        VariantPriceTierResponse(
            id=t.id, variant_id=t.variant_id,
            tier_type=t.tier_type, tier_key=t.tier_key, tier_name=t.tier_name,
            min_qty=t.min_qty, max_qty=t.max_qty,
            price=float(t.price), valid_from=t.valid_from, valid_to=t.valid_to,
            is_active=t.is_active, notes=t.notes,
            created_at=str(t.created_at) if t.created_at else None,
            updated_at=str(t.updated_at) if t.updated_at else None,
        ) for t in tiers
    ]


@router.post("/variants/{variant_id}/price-tiers", response_model=VariantPriceTierResponse)
async def create_price_tier(
    variant_id: int,
    data: VariantPriceTierCreate,
    db: AsyncSession = Depends(get_db),
):
    """为SKU创建价格层级"""
    variant = await db.get(ProductVariant, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="变体不存在")

    tier = VariantPriceTier(variant_id=variant_id, **data.model_dump())
    db.add(tier)
    await db.commit()
    await db.refresh(tier)
    return VariantPriceTierResponse(
        id=tier.id, variant_id=tier.variant_id,
        tier_type=tier.tier_type, tier_key=tier.tier_key, tier_name=tier.tier_name,
        min_qty=tier.min_qty, max_qty=tier.max_qty,
        price=float(tier.price), valid_from=tier.valid_from, valid_to=tier.valid_to,
        is_active=tier.is_active, notes=tier.notes,
        created_at=str(tier.created_at) if tier.created_at else None,
        updated_at=str(tier.updated_at) if tier.updated_at else None,
    )


@router.get("/variants/{variant_id}/price-tiers/{tier_id}", response_model=VariantPriceTierResponse)
async def get_price_tier(
    variant_id: int,
    tier_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取价格层级详情"""
    tier = await db.get(VariantPriceTier, tier_id)
    if not tier or tier.variant_id != variant_id:
        raise HTTPException(status_code=404, detail="价格层级不存在")
    return VariantPriceTierResponse(
        id=tier.id, variant_id=tier.variant_id,
        tier_type=tier.tier_type, tier_key=tier.tier_key, tier_name=tier.tier_name,
        min_qty=tier.min_qty, max_qty=tier.max_qty,
        price=float(tier.price), valid_from=tier.valid_from, valid_to=tier.valid_to,
        is_active=tier.is_active, notes=tier.notes,
        created_at=str(tier.created_at) if tier.created_at else None,
        updated_at=str(tier.updated_at) if tier.updated_at else None,
    )


@router.put("/variants/{variant_id}/price-tiers/{tier_id}", response_model=VariantPriceTierResponse)
async def update_price_tier(
    variant_id: int,
    tier_id: int,
    data: VariantPriceTierUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新价格层级"""
    tier = await db.get(VariantPriceTier, tier_id)
    if not tier or tier.variant_id != variant_id:
        raise HTTPException(status_code=404, detail="价格层级不存在")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(tier, field, value)

    await db.commit()
    await db.refresh(tier)
    return VariantPriceTierResponse(
        id=tier.id, variant_id=tier.variant_id,
        tier_type=tier.tier_type, tier_key=tier.tier_key, tier_name=tier.tier_name,
        min_qty=tier.min_qty, max_qty=tier.max_qty,
        price=float(tier.price), valid_from=tier.valid_from, valid_to=tier.valid_to,
        is_active=tier.is_active, notes=tier.notes,
        created_at=str(tier.created_at) if tier.created_at else None,
        updated_at=str(tier.updated_at) if tier.updated_at else None,
    )


@router.delete("/variants/{variant_id}/price-tiers/{tier_id}")
async def delete_price_tier(
    variant_id: int,
    tier_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除价格层级"""
    tier = await db.get(VariantPriceTier, tier_id)
    if not tier or tier.variant_id != variant_id:
        raise HTTPException(status_code=404, detail="价格层级不存在")

    await db.delete(tier)
    await db.commit()
    return {"detail": "价格层级已删除"}
