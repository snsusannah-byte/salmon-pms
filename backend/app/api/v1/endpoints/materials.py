"""
物料管理独立 API
基于 products 表（category=bom_material）的专用接口
提供物料消耗追踪、采购汇总、库存预警
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Product, ProductCategory, Company, CompanyType
from app.models.finished_product_v2 import WarehousePurchaseOrder, WarehouseStock, WarehouseType

router = APIRouter()


# ==================== 响应模型 ====================

class MaterialItem(BaseModel):
    """物料列表项"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    spec: Optional[str] = None
    unit: str
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    stock_quantity: float
    lead_time_days: Optional[int] = None
    last_purchase_price: Optional[float] = None
    is_active: bool


class MaterialListResponse(BaseModel):
    total: int
    items: List[MaterialItem]
    skip: int
    limit: int


class MaterialConsumptionRecord(BaseModel):
    """物料消耗记录"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    record_date: date
    material_id: int
    material_name: str
    quantity_used: float
    unit: str
    related_slaughter_id: Optional[int] = None
    related_slaughter_date: Optional[date] = None
    notes: Optional[str] = None


class MaterialConsumptionListResponse(BaseModel):
    total: int
    items: List[MaterialConsumptionRecord]
    skip: int
    limit: int


class MaterialSummary(BaseModel):
    """物料汇总统计"""
    total_materials: int
    active_materials: int
    total_stock_value: float  # 库存总价值
    low_stock_count: int  # 低于安全库存的数量
    recent_purchase_count: int  # 最近30天采购次数
    recent_purchase_amount: float  # 最近30天采购金额
    top_consumption: List[dict] = []  # 消耗最多的物料


class MaterialMovementRecord(BaseModel):
    """物料出入库流水"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    movement_date: date
    movement_type: str  # in / out
    material_id: int
    material_name: str
    quantity: float
    unit: str
    unit_price: Optional[float] = None
    total_amount: Optional[float] = None
    reason: str
    related_order_id: Optional[int] = None


class MaterialMovementListResponse(BaseModel):
    total: int
    items: List[MaterialMovementRecord]
    skip: int
    limit: int


# ==================== 列表查询 ====================

@router.get("/", response_model=MaterialListResponse)
async def list_materials(
    search: Optional[str] = Query(None),
    supplier_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_low_stock: Optional[bool] = Query(None),
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

    if is_active is not None:
        query = query.where(Product.is_active == is_active)
        count_query = count_query.where(Product.is_active == is_active)

    query = query.order_by(Product.name)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.offset(skip).limit(limit))
    products = result.scalars().all()

    # 获取库存信息
    product_ids = [p.id for p in products]
    stock_result = await db.execute(
        select(WarehouseStock).where(WarehouseStock.product_id.in_(product_ids))
    )
    stock_map = {s.product_id: s for s in stock_result.scalars().all()}

    # 获取供应商名称
    supplier_ids = [p.supplier_id for p in products if p.supplier_id]
    supplier_names = {}
    if supplier_ids:
        supplier_result = await db.execute(
            select(Company).where(Company.id.in_(supplier_ids))
        )
        supplier_names = {c.id: c.name for c in supplier_result.scalars().all()}

    items = []
    for p in products:
        stock = stock_map.get(p.id)
        items.append(MaterialItem(
            id=p.id,
            code=p.code,
            name=p.name,
            spec=p.spec,
            unit=p.unit or "个",
            supplier_id=p.supplier_id,
            supplier_name=supplier_names.get(p.supplier_id) if p.supplier_id else None,
            stock_quantity=float(stock.current_quantity) if stock else 0,
            lead_time_days=p.lead_time_days,
            last_purchase_price=float(p.last_purchase_price) if p.last_purchase_price else None,
            is_active=p.is_active,
        ))

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

    return MaterialItem(
        id=product.id,
        code=product.code,
        name=product.name,
        spec=product.spec,
        unit=product.unit or "个",
        supplier_id=product.supplier_id,
        supplier_name=supplier_name,
        stock_quantity=float(stock.current_quantity) if stock else 0,
        lead_time_days=product.lead_time_days,
        last_purchase_price=float(product.last_purchase_price) if product.last_purchase_price else None,
        is_active=product.is_active,
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
            Product.is_active == True,
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
    recent_purchase_amount = float(row[1] or 0)

    return MaterialSummary(
        total_materials=total_materials,
        active_materials=active_materials,
        total_stock_value=float(total_stock_value.quantize(Decimal("0.01"))),
        low_stock_count=low_stock_count,
        recent_purchase_count=recent_purchase_count,
        recent_purchase_amount=recent_purchase_amount,
    )


# ==================== 出入库流水 ====================

@router.get("/movements", response_model=MaterialMovementListResponse)
async def list_material_movements(
    material_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None, description="in / out"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
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
            quantity=float(order.quantity),
            unit=order.unit,
            unit_price=float(order.unit_price) if order.unit_price else None,
            total_amount=float(order.total_amount) if order.total_amount else None,
            reason=order.notes or "采购入库",
        ))

    return MaterialMovementListResponse(total=total, items=items, skip=skip, limit=limit)
