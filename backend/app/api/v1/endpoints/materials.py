"""
物料管理独立 API
基于 products 表（category=bom_material）的专用接口
提供物料消耗追踪、采购汇总、库存预警
"""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import (
    Company,
    MaterialCategory,
    MaterialSupplier,
    Product,
    ProductCategory,
)
from app.models.finished_product_v2 import WarehousePurchaseOrder, WarehouseStock

router = APIRouter()


# ==================== 响应模型 ====================

class MaterialCategoryBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str


class MaterialCreate(BaseModel):
    code: str | None = None
    name: str
    spec: str | None = None
    unit: str = "个"
    cost_price: float | None = None
    category_id: int | None = None
    is_active: bool = True
    items_per_box: int | None = None  # 每箱数量


class MaterialUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    spec: str | None = None
    unit: str | None = None
    cost_price: float | None = None
    category_id: int | None = None
    is_active: bool | None = None
    items_per_box: int | None = None


class MaterialSupplierItem(BaseModel):
    """物料供应商项"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    supplier_id: int
    supplier_name: str | None = None
    unit_price: Decimal | None = None
    min_order_qty: Decimal | None = None
    lead_time_days: int | None = None
    is_preferred: bool = False
    notes: str | None = None


class MaterialItem(BaseModel):
    """物料列表项"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    spec: str | None = None
    unit: str
    supplier_id: int | None = None  # 兼容旧字段
    supplier_name: str | None = None
    stock_quantity: Decimal
    lead_time_days: int | None = None
    last_purchase_price: Decimal | None = None
    cost_price: Decimal | None = None
    is_active: bool
    category_id: int | None = None  # 新增：分类ID
    category: MaterialCategoryBrief | None = None  # 物料分类
    suppliers: list[MaterialSupplierItem] = []  # 新增：多供应商
    items_per_box: int | None = None  # 每箱数量
    material_type: str | None = "standalone"
    parent_id: int | None = None
    variants: list["MaterialItem"] = []  # 嵌套变体


class MaterialListResponse(BaseModel):
    total: int
    items: list[MaterialItem]
    skip: int
    limit: int


class MaterialConsumptionRecord(BaseModel):
    """物料消耗记录"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    record_date: date
    material_id: int
    material_name: str
    quantity_used: Decimal
    unit: str
    related_slaughter_id: int | None = None
    related_slaughter_date: date | None = None
    notes: str | None = None


class MaterialConsumptionListResponse(BaseModel):
    total: int
    items: list[MaterialConsumptionRecord]
    skip: int
    limit: int


class MaterialSummary(BaseModel):
    """物料汇总统计"""
    total_materials: int
    active_materials: int
    total_stock_value: Decimal  # 库存总价值
    low_stock_count: int  # 低于安全库存的数量
    recent_purchase_count: int  # 最近30天采购次数
    recent_purchase_amount: Decimal  # 最近30天采购金额
    top_consumption: list[dict] = []  # 消耗最多的物料


class MaterialMovementRecord(BaseModel):
    """物料出入库流水"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    movement_date: date
    movement_type: str  # in / out
    material_id: int
    material_name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal | None = None
    total_amount: Decimal | None = None
    reason: str
    related_order_id: int | None = None


class MaterialMovementListResponse(BaseModel):
    total: int
    items: list[MaterialMovementRecord]
    skip: int
    limit: int


# ==================== 列表查询 ====================

@router.get("/", response_model=MaterialListResponse)
async def list_materials(
    search: str | None = Query(None),
    supplier_id: int | None = Query(None),
    material_category_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    is_low_stock: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    物料列表（独立API）
    
    底层查询 products 表中 category=bom_material 的记录，
    但返回物料专用的字段结构。
    """
    query = select(Product).where(Product.category == ProductCategory.BOM_MATERIAL)
    count_query = select(func.count(Product.id)).where(Product.category == ProductCategory.BOM_MATERIAL)

    if search:
        query = query.where(
            Product.name.ilike(f"%{search}%") | Product.code.ilike(f"%{search}%")
        )
        count_query = count_query.where(
            Product.name.ilike(f"%{search}%") | Product.code.ilike(f"%{search}%")
        )

    if supplier_id:
        query = query.where(Product.supplier_id == supplier_id)
        count_query = count_query.where(Product.supplier_id == supplier_id)

    if material_category_id is not None:
        query = query.where(Product.material_category_id == material_category_id)
        count_query = count_query.where(Product.material_category_id == material_category_id)

    if is_active is not None:
        query = query.where(Product.is_active == is_active)
        count_query = count_query.where(Product.is_active == is_active)

    # 只查询基础物料和独立物料（变体作为嵌套）
    query = query.where(Product.material_type.in_(["basic", "standalone"]))
    count_query = count_query.where(Product.material_type.in_(["basic", "standalone"]))

    query = query.order_by(Product.created_at.desc())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit))
    products = result.scalars().all()

    # 获取所有相关物料ID（基础物料 + 它们的变体）
    all_product_ids = [p.id for p in products]
    variant_map: dict[int, list[Product]] = {}
    for p in products:
        if p.material_type == "basic":
            variant_result = await db.execute(
                select(Product).where(Product.parent_id == p.id).where(Product.is_active)
            )
            variants = variant_result.scalars().all()
            variant_map[p.id] = variants
            all_product_ids.extend([v.id for v in variants])

    # 获取库存信息
    stock_result = await db.execute(
        select(WarehouseStock).where(WarehouseStock.product_id.in_(all_product_ids))
    )
    stock_map = {s.product_id: s for s in stock_result.scalars().all()}

    # 获取供应商信息（多供应商关联表）
    ms_result = await db.execute(
        select(MaterialSupplier, Company)
        .join(Company, MaterialSupplier.supplier_id == Company.id)
        .where(MaterialSupplier.material_id.in_(all_product_ids))
    )
    supplier_map: dict[int, list[MaterialSupplierItem]] = {}
    for ms, company in ms_result.all():
        if ms.material_id not in supplier_map:
            supplier_map[ms.material_id] = []
        supplier_map[ms.material_id].append(MaterialSupplierItem(
            id=ms.id,
            supplier_id=ms.supplier_id,
            supplier_name=company.name,
            unit_price=ms.unit_price,
            min_order_qty=ms.min_order_qty,
            lead_time_days=ms.lead_time_days,
            is_preferred=ms.is_preferred,
            notes=ms.notes,
        ))

    # 获取旧版单供应商名称（兼容）
    old_supplier_ids = [p.supplier_id for p in products if p.supplier_id]
    for variants in variant_map.values():
        old_supplier_ids.extend([v.supplier_id for v in variants if v.supplier_id])
    old_supplier_names = {}
    if old_supplier_ids:
        supplier_result = await db.execute(
            select(Company).where(Company.id.in_(set(old_supplier_ids)))
        )
        old_supplier_names = {c.id: c.name for c in supplier_result.scalars().all()}

    # 获取物料分类信息
    category_ids = [p.material_category_id for p in products if p.material_category_id]
    for variants in variant_map.values():
        category_ids.extend([v.material_category_id for v in variants if v.material_category_id])
    category_map = {}
    if category_ids:
        cat_result = await db.execute(
            select(MaterialCategory).where(MaterialCategory.id.in_(set(category_ids)))
        )
        category_map = {c.id: MaterialCategoryBrief(id=c.id, name=c.name, code=c.code) for c in cat_result.scalars().all()}

    def build_item(p: Product) -> MaterialItem:
        stock = stock_map.get(p.id)
        suppliers = supplier_map.get(p.id, [])
        category = category_map.get(p.material_category_id) if p.material_category_id else None
        return MaterialItem(
            id=p.id,
            code=p.code,
            name=p.name,
            spec=p.spec,
            unit=p.unit or "个",
            supplier_id=p.supplier_id,
            supplier_name=old_supplier_names.get(p.supplier_id) if p.supplier_id else None,
            stock_quantity=stock.current_quantity if stock else 0,
            lead_time_days=p.lead_time_days,
            last_purchase_price=p.last_purchase_price if p.last_purchase_price else None,
            cost_price=p.cost_price if p.cost_price else None,
            is_active=p.is_active,
            category_id=p.material_category_id,
            category=category,
            suppliers=suppliers,
            items_per_box=p.items_per_box,
            material_type=p.material_type,
            parent_id=p.parent_id,
        )

    items = []
    for p in products:
        item = build_item(p)
        # 加载变体
        if p.id in variant_map:
            item.variants = [build_item(v) for v in variant_map[p.id]]
        items.append(item)

    # 低库存筛选
    if is_low_stock:
        items = [i for i in items if i.stock_quantity < (i.lead_time_days or 0)]
        total = len(items)

    return MaterialListResponse(total=total, items=items, skip=skip, limit=limit)


# ==================== 详情 ====================

@router.get("/{material_id}", response_model=MaterialItem)
async def get_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
):
    """物料详情"""
    result = await db.execute(
        select(Product).where(
            Product.id == material_id,
            Product.category == ProductCategory.BOM_MATERIAL,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="物料不存在")

    # 库存
    stock_result = await db.execute(
        select(WarehouseStock).where(WarehouseStock.product_id == material_id)
    )
    stock = stock_result.scalar_one_or_none()

    # 供应商
    supplier_name = None
    if product.supplier_id:
        supplier_result = await db.execute(
            select(Company).where(Company.id == product.supplier_id)
        )
        supplier = supplier_result.scalar_one_or_none()
        supplier_name = supplier.name if supplier else None

    # 分类
    category = None
    if product.material_category_id:
        cat_result = await db.execute(
            select(MaterialCategory).where(MaterialCategory.id == product.material_category_id)
        )
        cat = cat_result.scalar_one_or_none()
        if cat:
            category = MaterialCategoryBrief(id=cat.id, name=cat.name, code=cat.code)

    return MaterialItem(
        id=product.id,
        code=product.code,
        name=product.name,
        spec=product.spec,
        unit=product.unit or "个",
        supplier_id=product.supplier_id,
        supplier_name=supplier_name,
        stock_quantity=stock.current_quantity if stock else 0,
        lead_time_days=product.lead_time_days,
        last_purchase_price=product.last_purchase_price if product.last_purchase_price else None,
        cost_price=product.cost_price if product.cost_price else None,
        is_active=product.is_active,
        category_id=product.material_category_id,
        category=category,
        items_per_box=product.items_per_box,
    )


# ==================== 汇总统计 ====================

@router.get("/summary/stats", response_model=MaterialSummary)
async def get_material_summary(
    db: AsyncSession = Depends(get_db),
):
    """物料汇总统计"""
    # 总物料数
    total_result = await db.execute(
        select(func.count(Product.id)).where(Product.category == ProductCategory.BOM_MATERIAL)
    )
    total_materials = total_result.scalar() or 0

    active_result = await db.execute(
        select(func.count(Product.id)).where(
            Product.category == ProductCategory.BOM_MATERIAL,
            Product.is_active,
        )
    )
    active_materials = active_result.scalar() or 0

    # 库存总价值
    stock_result = await db.execute(
        select(WarehouseStock, Product)
        .join(Product, WarehouseStock.product_id == Product.id)
        .where(Product.category == ProductCategory.BOM_MATERIAL)
    )
    total_stock_value = Decimal("0")
    low_stock_count = 0
    for stock, product in stock_result.all():
        if stock.unit_cost:
            total_stock_value += stock.current_quantity * stock.unit_cost
        if product.safety_buffer and stock.current_quantity < product.safety_buffer:
            low_stock_count += 1

    # 最近30天采购
    thirty_days_ago = date.today() - timedelta(days=30)
    purchase_result = await db.execute(
        select(
            func.count(WarehousePurchaseOrder.id),
            func.sum(WarehousePurchaseOrder.total_amount),
        )
        .join(Product, WarehousePurchaseOrder.product_id == Product.id)
        .where(
            Product.category == ProductCategory.BOM_MATERIAL,
            WarehousePurchaseOrder.order_date >= thirty_days_ago,
        )
    )
    row = purchase_result.first()
    recent_purchase_count = row[0] or 0
    recent_purchase_amount = row[1] or 0

    return MaterialSummary(
        total_materials=total_materials,
        active_materials=active_materials,
        total_stock_value=total_stock_value.quantize(Decimal("0.01")),
        low_stock_count=low_stock_count,
        recent_purchase_count=recent_purchase_count,
        recent_purchase_amount=recent_purchase_amount,
    )


# ==================== 出入库流水 ====================

@router.get("/movements", response_model=MaterialMovementListResponse)
async def list_material_movements(
    material_id: int | None = Query(None),
    movement_type: str | None = Query(None, description="in / out"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """物料出入库流水"""
    query = select(WarehousePurchaseOrder, Product).join(
        Product, WarehousePurchaseOrder.product_id == Product.id
    ).where(Product.category == ProductCategory.BOM_MATERIAL)

    if material_id:
        query = query.where(WarehousePurchaseOrder.product_id == material_id)
    if start_date:
        query = query.where(WarehousePurchaseOrder.order_date >= start_date)
    if end_date:
        query = query.where(WarehousePurchaseOrder.order_date <= end_date)

    query = query.order_by(WarehousePurchaseOrder.order_date.desc())

    total_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = total_result.scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit))
    rows = result.all()

    items = []
    for order, product in rows:
        items.append(MaterialMovementRecord(
            id=order.id,
            movement_date=order.order_date,
            movement_type="in",
            material_id=product.id,
            material_name=product.name,
            quantity=order.quantity,
            unit=order.unit,
            unit_price=order.unit_price if order.unit_price else None,
            total_amount=order.total_amount if order.total_amount else None,
            reason=order.notes or "采购入库",
        ))

    return MaterialMovementListResponse(total=total, items=items, skip=skip, limit=limit)


# ==================== 物料供应商关联 ====================

class MaterialSupplierCreate(BaseModel):
    """添加物料供应商"""
    supplier_id: int
    unit_price: float | None = None
    min_order_qty: float | None = None
    lead_time_days: int | None = None
    is_preferred: bool = False
    notes: str | None = None


class MaterialSupplierUpdate(BaseModel):
    """更新物料供应商"""
    unit_price: float | None = None
    min_order_qty: float | None = None
    lead_time_days: int | None = None
    is_preferred: bool | None = None
    notes: str | None = None


@router.get("/{material_id}/suppliers", response_model=list[MaterialSupplierItem])
async def list_material_suppliers(
    material_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取物料的所有供应商"""
    result = await db.execute(
        select(MaterialSupplier, Company)
        .join(Company, MaterialSupplier.supplier_id == Company.id)
        .where(MaterialSupplier.material_id == material_id)
    )
    items = []
    for ms, company in result.all():
        items.append(MaterialSupplierItem(
            id=ms.id,
            supplier_id=ms.supplier_id,
            supplier_name=company.name,
            unit_price=ms.unit_price if ms.unit_price else None,
            min_order_qty=ms.min_order_qty if ms.min_order_qty else None,
            lead_time_days=ms.lead_time_days,
            is_preferred=ms.is_preferred,
            notes=ms.notes,
        ))
    return items


@router.post("/{material_id}/suppliers", response_model=MaterialSupplierItem)
async def add_material_supplier(
    material_id: int,
    data: MaterialSupplierCreate,
    db: AsyncSession = Depends(get_db),
):
    """为物料添加供应商"""
    # 检查物料是否存在
    product_result = await db.execute(
        select(Product).where(Product.id == material_id)
    )
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="物料不存在")
    
    # 检查供应商是否存在
    supplier_result = await db.execute(
        select(Company).where(Company.id == data.supplier_id)
    )
    supplier = supplier_result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="供应商不存在")
    
    # 检查是否已存在
    existing = await db.execute(
        select(MaterialSupplier).where(
            MaterialSupplier.material_id == material_id,
            MaterialSupplier.supplier_id == data.supplier_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该供应商已关联此物料")
    
    ms = MaterialSupplier(
        material_id=material_id,
        supplier_id=data.supplier_id,
        unit_price=Decimal(str(data.unit_price)) if data.unit_price is not None else None,
        min_order_qty=Decimal(str(data.min_order_qty)) if data.min_order_qty is not None else Decimal("0"),
        lead_time_days=data.lead_time_days or 0,
        is_preferred=data.is_preferred,
        notes=data.notes,
    )
    db.add(ms)
    await db.commit()
    await db.refresh(ms)
    
    return MaterialSupplierItem(
        id=ms.id,
        supplier_id=ms.supplier_id,
        supplier_name=supplier.name,
        unit_price=ms.unit_price if ms.unit_price else None,
        min_order_qty=ms.min_order_qty if ms.min_order_qty else None,
        lead_time_days=ms.lead_time_days,
        is_preferred=ms.is_preferred,
        notes=ms.notes,
    )


@router.put("/{material_id}/suppliers/{supplier_link_id}", response_model=MaterialSupplierItem)
async def update_material_supplier(
    material_id: int,
    supplier_link_id: int,
    data: MaterialSupplierUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新物料供应商信息"""
    result = await db.execute(
        select(MaterialSupplier).where(
            MaterialSupplier.id == supplier_link_id,
            MaterialSupplier.material_id == material_id,
        )
    )
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="供应商关联不存在")
    
    if data.unit_price is not None:
        ms.unit_price = Decimal(str(data.unit_price))
    if data.min_order_qty is not None:
        ms.min_order_qty = Decimal(str(data.min_order_qty))
    if data.lead_time_days is not None:
        ms.lead_time_days = data.lead_time_days
    if data.is_preferred is not None:
        ms.is_preferred = data.is_preferred
    if data.notes is not None:
        ms.notes = data.notes
    
    await db.commit()
    await db.refresh(ms)
    
    # 获取供应商名称
    supplier_result = await db.execute(
        select(Company).where(Company.id == ms.supplier_id)
    )
    supplier = supplier_result.scalar_one_or_none()
    
    return MaterialSupplierItem(
        id=ms.id,
        supplier_id=ms.supplier_id,
        supplier_name=supplier.name if supplier else None,
        unit_price=ms.unit_price if ms.unit_price else None,
        min_order_qty=ms.min_order_qty if ms.min_order_qty else None,
        lead_time_days=ms.lead_time_days,
        is_preferred=ms.is_preferred,
        notes=ms.notes,
    )


@router.delete("/{material_id}/suppliers/{supplier_link_id}")
async def delete_material_supplier(
    material_id: int,
    supplier_link_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除物料供应商关联"""
    result = await db.execute(
        select(MaterialSupplier).where(
            MaterialSupplier.id == supplier_link_id,
            MaterialSupplier.material_id == material_id,
        )
    )
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="供应商关联不存在")
    
    await db.delete(ms)
    await db.commit()
    return {"detail": "已删除"}


# ==================== 物料 CRUD ====================

@router.post("/", response_model=MaterialItem, status_code=201)
async def create_material(
    data: MaterialCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建物料"""
    product = Product(
        category=ProductCategory.BOM_MATERIAL,
        code=data.code or "",
        name=data.name,
        spec=data.spec,
        unit=data.unit,
        cost_price=Decimal(str(data.cost_price)) if data.cost_price is not None else None,
        material_category_id=data.category_id,
        is_active=data.is_active,
        items_per_box=data.items_per_box,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return MaterialItem(
        id=product.id,
        code=product.code,
        name=product.name,
        spec=product.spec,
        unit=product.unit or "个",
        stock_quantity=0,
        cost_price=product.cost_price if product.cost_price else None,
        is_active=product.is_active,
        category_id=product.material_category_id,
        items_per_box=product.items_per_box,
    )


@router.put("/{material_id}", response_model=MaterialItem)
async def update_material(
    material_id: int,
    data: MaterialUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新物料"""
    result = await db.execute(
        select(Product).where(
            Product.id == material_id,
            Product.category == ProductCategory.BOM_MATERIAL,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="物料不存在")

    if data.code is not None:
        product.code = data.code
    if data.name is not None:
        product.name = data.name
    if data.spec is not None:
        product.spec = data.spec
    if data.unit is not None:
        product.unit = data.unit
    if data.cost_price is not None:
        product.cost_price = Decimal(str(data.cost_price))
    if data.category_id is not None:
        product.material_category_id = data.category_id
    if data.is_active is not None:
        product.is_active = data.is_active
    if data.items_per_box is not None:
        product.items_per_box = data.items_per_box

    await db.commit()
    await db.refresh(product)

    # 获取库存
    stock_result = await db.execute(
        select(WarehouseStock).where(WarehouseStock.product_id == material_id)
    )
    stock = stock_result.scalar_one_or_none()

    # 获取分类
    category = None
    if product.material_category_id:
        cat_result = await db.execute(
            select(MaterialCategory).where(MaterialCategory.id == product.material_category_id)
        )
        cat = cat_result.scalar_one_or_none()
        if cat:
            category = MaterialCategoryBrief(id=cat.id, name=cat.name, code=cat.code)

    return MaterialItem(
        id=product.id,
        code=product.code,
        name=product.name,
        spec=product.spec,
        unit=product.unit or "个",
        stock_quantity=stock.current_quantity if stock else 0,
        lead_time_days=product.lead_time_days,
        last_purchase_price=product.last_purchase_price if product.last_purchase_price else None,
        cost_price=product.cost_price if product.cost_price else None,
        is_active=product.is_active,
        category_id=product.material_category_id,
        category=category,
        items_per_box=product.items_per_box,
    )


@router.delete("/{material_id}", status_code=204)
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除物料"""
    result = await db.execute(
        select(Product).where(
            Product.id == material_id,
            Product.category == ProductCategory.BOM_MATERIAL,
        )
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="物料不存在")

    # 检查是否有关联库存
    stock_result = await db.execute(
        select(WarehouseStock).where(WarehouseStock.product_id == material_id)
    )
    stock = stock_result.scalar_one_or_none()
    if stock and stock.current_quantity > 0:
        raise HTTPException(status_code=400, detail="该物料还有库存，无法删除")

    # 检查是否有关联供应商
    ms_result = await db.execute(
        select(func.count(MaterialSupplier.id)).where(MaterialSupplier.material_id == material_id)
    )
    ms_count = ms_result.scalar() or 0
    if ms_count > 0:
        raise HTTPException(status_code=400, detail=f"该物料还有 {ms_count} 个供应商关联，无法删除")

    await db.delete(product)
    await db.commit()
    return {"detail": "已删除"}


# ==================== 供应商视角：查看某供应商供应的所有物料 ====================

@router.get("/by-supplier/{supplier_id}", response_model=MaterialListResponse)
async def list_materials_by_supplier(
    supplier_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """获取某供应商供应的所有物料"""
    # 查询该供应商关联的所有物料
    query = (
        select(Product, MaterialSupplier)
        .join(MaterialSupplier, Product.id == MaterialSupplier.material_id)
        .where(
            MaterialSupplier.supplier_id == supplier_id,
            Product.category == ProductCategory.BOM_MATERIAL,
        )
    )
    
    count_query = (
        select(func.count(Product.id))
        .join(MaterialSupplier, Product.id == MaterialSupplier.material_id)
        .where(
            MaterialSupplier.supplier_id == supplier_id,
            Product.category == ProductCategory.BOM_MATERIAL,
        )
    )
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    result = await db.execute(query.offset(skip).limit(limit))
    rows = result.all()
    
    # 获取库存
    product_ids = [p.id for p, _ in rows]
    stock_result = await db.execute(
        select(WarehouseStock).where(WarehouseStock.product_id.in_(product_ids))
    )
    stock_map = {s.product_id: s for s in stock_result.scalars().all()}
    
    # 获取供应商名称
    supplier_result = await db.execute(
        select(Company).where(Company.id == supplier_id)
    )
    supplier = supplier_result.scalar_one_or_none()
    supplier_name = supplier.name if supplier else None
    
    items = []
    for p, ms in rows:
        stock = stock_map.get(p.id)
        items.append(MaterialItem(
            id=p.id,
            code=p.code,
            name=p.name,
            spec=p.spec,
            unit=p.unit or "个",
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            stock_quantity=stock.current_quantity if stock else 0,
            lead_time_days=ms.lead_time_days,
            last_purchase_price=ms.unit_price if ms.unit_price else None,
            is_active=p.is_active,
            category_id=p.material_category_id,
            suppliers=[MaterialSupplierItem(
                id=ms.id,
                supplier_id=ms.supplier_id,
                supplier_name=supplier_name,
                unit_price=ms.unit_price if ms.unit_price else None,
                min_order_qty=ms.min_order_qty if ms.min_order_qty else None,
                lead_time_days=ms.lead_time_days,
                is_preferred=ms.is_preferred,
                notes=ms.notes,
            )],
        ))
    
    return MaterialListResponse(total=total, items=items, skip=skip, limit=limit)
