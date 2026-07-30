"""
国内采购与成品销售模块 API (迁移自 salmon-finance-v4)
使用现有 Company 表作为供应商（type=supplier）
"""
from datetime import date as _date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import require_warehouse, require_sales, require_admin
from app.models import (
    Company,
    CompanyType,
    FinishedProductAftersales,
    FinishedProductReceipt,
    FinishedProductSaleV2,
    FinishedSaleProductV2,
    Product,
    PurchaseOrderProductV2,
    PurchaseOrderV2,
    ReturnOrder,
    Stock,
    StockInbound,
    StockOutbound,
    StockStatus,
    TransactionRecord,
    Warehouse,
)
from app.models.enums import StockMovementType

router = APIRouter()


def round2dec(n):
    """保留2位小数的Decimal"""
    from decimal import ROUND_HALF_UP
    return Decimal(n).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _parse_date(date_str):
    """解析日期字符串"""
    if not date_str:
        return None
    if isinstance(date_str, _date):
        return date_str
    try:
        from datetime import datetime
        return datetime.strptime(str(date_str), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ==================== 辅助函数：仓库联通 ====================

async def _get_warehouse_id(db: AsyncSession, code: str) -> int:
    """根据仓库代码获取ID"""
    result = await db.execute(select(Warehouse).where(Warehouse.code == code))
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(status_code=500, detail=f"仓库 {code} 不存在，请联系管理员")
    return wh.id


async def _get_or_create_product(db: AsyncSession, name: str, spec: str, unit: str = "kg", category: str = "raw_material") -> int:
    """查找或创建产品"""
    # 同时按名称 + 规格查找（name 不唯一）
    result = await db.execute(select(Product).where(Product.name == name, Product.spec == spec))
    product = result.scalar_one_or_none()
    if product:
        return product.id

    # 创建新产品
    from datetime import datetime
    code = f"{category.upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}-{name[:10]}"
    product = Product(
        category=category,
        code=code,
        name=name,
        spec=spec,
        unit=unit,
        is_active=True,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product.id


async def _update_stock_inbound(db: AsyncSession, warehouse_id: int, product_id: int, qty: Decimal, unit_cost: Decimal = None, total_cost: Decimal = None, ref_type: str = None, ref_no: str = None, ref_id: int = None, notes: str = None) -> None:
    """更新库存：入库时增加数量"""
    from app.models import StockMovement
    result = await db.execute(
        select(Stock).where(Stock.warehouse_id == warehouse_id, Stock.product_id == product_id)
    )
    stock = result.scalar_one_or_none()
    if not stock:
        stock = Stock(
            warehouse_id=warehouse_id,
            product_id=product_id,
            current_qty=qty,
            available_qty=qty,
            unit="kg",
        )
        db.add(stock)
    else:
        stock.current_qty = stock.current_qty + qty
        stock.available_qty = stock.available_qty + qty
    if unit_cost:
        stock.unit_cost = unit_cost
    if total_cost:
        stock.total_cost = (stock.total_cost or Decimal("0")) + total_cost
    stock.last_in_date = _date.today()

    # 创建库存变动记录
    movement = StockMovement(
        warehouse_id=warehouse_id,
        product_id=product_id,
        movement_type=StockMovementType.INBOUND,
        movement_date=_date.today(),
        qty_change=qty,
        qty_before=(stock.current_qty or Decimal("0")) - qty,
        qty_after=stock.current_qty,
        unit="kg",
        ref_type=ref_type or "purchase_order",
        ref_id=ref_id,
        ref_no=ref_no,
        notes=notes,
    )
    db.add(movement)

async def _update_stock_outbound(db: AsyncSession, warehouse_id: int, product_id: int, qty: Decimal, batch_no: str | None = None, ref_type: str = None, ref_no: str = None, ref_id: int = None, notes: str = None) -> None:
    """更新库存：出库时减少数量（支持按销售单指定批次严格扣减）"""
    from app.models import StockMovement

    # 指定了批次号时，严格按该批次查找库存；未指定时按可用量最多取一条
    if batch_no:
        result = await db.execute(
            select(Stock).where(
                Stock.warehouse_id == warehouse_id,
                Stock.product_id == product_id,
                Stock.batch_no == batch_no,
            )
        )
        stock = result.scalar_one_or_none()
        if not stock:
            raise HTTPException(status_code=400, detail=f"仓库中不存在批次 {batch_no} 的库存")
        if stock.available_qty < qty:
            raise HTTPException(status_code=400, detail=f"批次 {batch_no} 库存不足：可用 {stock.available_qty}，需要 {qty}")
    else:
        result = await db.execute(
            select(Stock)
            .where(Stock.warehouse_id == warehouse_id, Stock.product_id == product_id)
            .order_by(Stock.available_qty.desc())
        )
        stock = result.scalar_one_or_none()
        if not stock:
            raise HTTPException(status_code=500, detail=f"仓库 {warehouse_id} 中没有该产品库存")
        if stock.available_qty < qty:
            raise HTTPException(status_code=400, detail=f"库存不足：可用 {stock.available_qty}，需要 {qty}")

    qty_before = stock.current_qty
    stock.current_qty = stock.current_qty - qty
    stock.available_qty = stock.available_qty - qty
    stock.last_out_date = _date.today()

    # 扣减入库批次剩余量（指定批次时只扣该批次，未指定时按先进先出）
    from app.models.warehouse import StockInbound
    inbound_query = (
        select(StockInbound)
        .where(StockInbound.warehouse_id == warehouse_id)
        .where(StockInbound.product_id == product_id)
    )
    if batch_no:
        inbound_query = inbound_query.where(StockInbound.batch_no == batch_no).order_by(StockInbound.inbound_date.asc())
    else:
        inbound_query = inbound_query.where(
            (StockInbound.remaining_qty > 0) | (StockInbound.remaining_qty == None)
        ).order_by(StockInbound.inbound_date.asc())
    inbound_result = await db.execute(inbound_query)
    inbounds = inbound_result.scalars().all()
    remaining_to_deduct = qty
    for inbound in inbounds:
        if remaining_to_deduct <= 0:
            break
        # remaining_qty 为空时视为完整数量（兼容旧数据）
        inbound_remaining = inbound.remaining_qty if inbound.remaining_qty is not None else inbound.qty
        if inbound_remaining >= remaining_to_deduct:
            inbound.remaining_qty = inbound_remaining - remaining_to_deduct
            if inbound.remaining_box_count is not None and inbound.original_box_count and inbound.original_weight:
                ratio = remaining_to_deduct / inbound.original_weight
                inbound.remaining_box_count = max(0, inbound.remaining_box_count - round(inbound.original_box_count * ratio))
            remaining_to_deduct = Decimal("0")
        else:
            remaining_to_deduct = remaining_to_deduct - inbound_remaining
            inbound.remaining_qty = Decimal("0")
            inbound.remaining_box_count = 0

    # 创建库存变动记录
    movement = StockMovement(
        warehouse_id=warehouse_id,
        product_id=product_id,
        batch_no=batch_no,
        movement_type=StockMovementType.OUTBOUND,
        movement_date=_date.today(),
        qty_change=-qty,
        qty_before=qty_before,
        qty_after=stock.current_qty,
        unit=stock.unit or "kg",
        ref_type=ref_type or "sale",
        ref_id=ref_id,
        ref_no=ref_no,
        notes=notes,
    )
    db.add(movement)

async def _auto_inbound_from_purchase(db: AsyncSession, order: PurchaseOrderV2) -> list:
    """采购入库后自动推仓库入库记录 + 更新库存

    以销定采（sale_id 有值）不走仓库入库流程，直接返回空列表。
    """
    # 以销定采：采购后直接发货给客户，不经过仓库存储
    if order.sale_id:
        return []

    # 根据采购类型决定仓库
    warehouse_code = "ZB-DOMESTIC" if order.order_type == "raw_material" else "FL-MATERIAL"
    warehouse_id = await _get_warehouse_id(db, warehouse_code)
    supplier_id = order.supplier_id

    inbounds = []

    # 预查询当天最大入库单号，避免循环内单号冲突
    today = order.purchase_date or _date.today()
    prefix = f"RK{today.strftime('%Y%m%d')}"
    last_result = await db.execute(
        select(StockInbound.inbound_no)
        .where(StockInbound.inbound_no.like(f"{prefix}-%"))
        .order_by(StockInbound.inbound_no.desc())
        .limit(1)
    )
    last_inbound = last_result.scalar()
    last_num = int(last_inbound.split('-')[-1]) if last_inbound else 0

    for i, product in enumerate(order.products):
        # 优先用 product_name 查找，和出库逻辑保持一致
        product_name = product.product_name or product.product_spec or "未命名产品"
        product_id = await _get_or_create_product(
            db,
            name=product_name,
            spec=product.product_spec or "",
            unit="kg",
            category="raw_material"
        )

        qty = Decimal(str(product.weight_kg or 0))
        unit_cost_val = Decimal(str(product.unit_price or 0))
        total_cost_val = Decimal(str(product.total_amount or 0))

        # 生成入库单号（预分配，避免冲突）
        next_num = last_num + i + 1
        inbound_no = f"{prefix}-{next_num:03d}"

        # 生成批次号：MMDD-加工厂缩写-NNN
        slaughter_date = order.slaughter_date or order.purchase_date or _date.today()
        factory_abbr = (product.factory or "")[:4] if product.factory else ""
        batch_no = f"{slaughter_date.strftime('%m%d')}-{factory_abbr}-{i+1:03d}" if order.order_type == "raw_material" else ""

        inbound = StockInbound(
            inbound_no=inbound_no,
            source_type="purchase_order",
            source_id=order.id,
            source_no=order.purchase_no,
            warehouse_id=warehouse_id,
            product_id=product_id,
            qty=qty,
            unit="kg",
            unit_cost=unit_cost_val,
            total_cost=total_cost_val,
            supplier_id=supplier_id,
            detail={"box_count": product.box_count, "spec": product.product_spec, "batch_no": batch_no, "product_name": product.product_name or product.product_spec},
            inbound_date=order.purchase_date or _date.today(),
            status=StockStatus.COMPLETED,
            notes=f"采购入库单 {order.purchase_no} 自动入库",
            slaughter_date=order.slaughter_date,
            factory=product.factory,
            original_box_count=product.box_count,
            original_weight=qty,
            remaining_qty=qty,
            remaining_box_count=product.box_count,
        )
        db.add(inbound)

        # 更新库存数量
        await _update_stock_inbound(db, warehouse_id, product_id, qty, unit_cost_val, total_cost_val, ref_type="purchase_order", ref_no=order.purchase_no, ref_id=order.id, notes=f"采购入库单 {order.purchase_no} 自动入库")

        inbounds.append(inbound_no)

    await db.commit()
    return inbounds


async def _auto_outbound_from_sale(db: AsyncSession, sale: FinishedProductSaleV2) -> list:
    """销售后自动推仓库出库记录"""
    outbounds = []
    for product in sale.products:
        # 查找产品（同时匹配 product_name + product_spec，因为 name 不唯一）
        p = None
        if product.product_id:
            result = await db.execute(select(Product).where(Product.id == product.product_id))
            p = result.scalar_one_or_none()
        if not p and product.product_name and product.product_spec:
            result = await db.execute(
                select(Product).where(Product.name == product.product_name, Product.spec == product.product_spec)
            )
            p = result.scalar_one_or_none()
        if not p and product.product_name:
            result = await db.execute(select(Product).where(Product.name == product.product_name))
            p = result.scalar_one_or_none()
        if not p and product.product_spec:
            result = await db.execute(select(Product).where(Product.name == product.product_spec))
            p = result.scalar_one_or_none()
        if not p:
            # 仍找不到，跳过该明细（避免库存流失）
            continue

        # 判断单位销售模式
        is_unit_sale = product.sale_unit and product.sale_unit.strip() and product.box_count
        qty = Decimal(str(product.box_count or 0)) if is_unit_sale else Decimal(str(product.weight_kg or 0))
        unit = product.sale_unit if is_unit_sale else (p.unit or "kg")
        if qty <= 0:
            continue

        # 根据产品分类决定仓库：BOM物料走国内整包仓，成品走成品分拣仓
        warehouse_code = "ZB-DOMESTIC" if (p.category == "bom_material" or sale.sale_type == "whole_fish") else "FB-FISH"
        warehouse_id = await _get_warehouse_id(db, warehouse_code)

        # 生成出库单号
        today = _date.today()
        prefix = f"CK{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.count()).select_from(
                select(StockOutbound).where(StockOutbound.outbound_no.like(f"{prefix}-%")).subquery()
            )
        )
        count = result.scalar() or 0
        outbound_no = f"{prefix}-{count + len(outbounds) + 1:03d}"

        outbound = StockOutbound(
            outbound_no=outbound_no,
            dest_type="sale",
            dest_id=sale.id,
            dest_no=sale.sale_no,
            warehouse_id=warehouse_id,
            product_id=p.id,
            qty=qty,
            unit=unit,
            unit_cost=Decimal(str(product.unit_price or 0)),
            total_cost=Decimal(str(product.total_amount or 0)),
            outbound_date=today,
            status=StockStatus.COMPLETED,  # 直接完成
            notes=f"销售单 {sale.sale_no} 自动出库",
        )
        db.add(outbound)

        # 扣减库存
        await _update_stock_outbound(db, warehouse_id, p.id, qty, batch_no=product.batch, ref_type="finished_product_sale", ref_no=sale.sale_no, ref_id=sale.id, notes=f"销售单 {sale.sale_no} 自动出库")

        outbounds.append(outbound_no)

    await db.commit()
    return outbounds


# ==================== 产品列表（级联：名称 → 规格）====================

@router.get("/products-by-name")
async def api_get_products_by_name(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """获取产品列表，按名称分组返回规格选项"""
    query = select(Product).where(Product.is_active.is_(True))
    if category:
        query = query.where(Product.category == category)
    else:
        # 默认只返回整鱼和成品产品（排除原料、辅料等）
        query = query.where(Product.category.in_(["whole_fish", "finished_product"]))
    result = await db.execute(query.order_by(Product.name, Product.spec))
    products = result.scalars().all()

    # 按名称分组
    name_map: dict = {}
    for p in products:
        if p.name not in name_map:
            name_map[p.name] = {"id": p.id, "name": p.name, "unit": p.unit, "specs": []}
        name_map[p.name]["specs"].append({"id": p.id, "spec": p.spec, "code": p.code, "unit": p.unit})

    return {"success": True, "data": list(name_map.values())}


# ==================== 客户列表（简化 API）====================

@router.get("/customers")
async def api_get_customers(
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_sales),
):
    """获取所有客户（简化版）"""
    result = await db.execute(
        select(Company)
        .where(Company.type == CompanyType.CUSTOMER)
        .order_by(Company.name)
        .limit(limit)
    )
    customers = result.scalars().all()
    return {
        "success": True,
        "data": [
            {"id": c.id, "name": c.name, "code": c.code, "contact_person": c.contact_person, "phone": c.phone, "address": c.address, "logistics_info": c.logistics_info, "customer_level": c.customer_level, "prepaid_balance": float(c.prepaid_balance or 0)}
            for c in customers
        ]
    }


# ==================== 供应商列表（简化 API）====================

@router.get("/suppliers")
async def api_get_suppliers(
    company_type: str | None = Query(None, description="公司类型过滤，如 supplier"),
    supplier_category: str | None = Query(None, description="供应商分类过滤，如 material_supply"),
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """获取公司列表（支持既是客户又是供应商的场景）"""
    from app.models.company import Company
    from app.models.enums import CompanyType

    query = select(Company).order_by(Company.name)

    if company_type:
        try:
            ct = CompanyType(company_type)
            query = query.where(Company.type == ct)
        except ValueError:
            pass

    if supplier_category:
        query = query.where(Company.supplier_category == supplier_category)

    query = query.limit(limit)
    result = await db.execute(query)
    suppliers = result.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "code": s.code,
                "contact_person": s.contact_person,
                "phone": s.phone,
                "address": s.address,
                "notes": s.notes,
                "company_type": s.type.value if s.type else None,
                "supplier_category": s.supplier_category,
            }
            for s in suppliers
        ]
    }


# ==================== 采购入库管理 ====================

@router.get("/purchase-orders")
async def api_get_purchase_orders(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """获取所有采购入库单（以订单为单位聚合返回）"""
    result = await db.execute(select(PurchaseOrderV2).order_by(PurchaseOrderV2.created_at.desc()))
    orders = result.scalars().all()
    data = []
    for o in orders:
        # 查产品明细
        products_result = await db.execute(
            select(PurchaseOrderProductV2)
            .where(PurchaseOrderProductV2.purchase_order_id == o.id)
        )
        products = products_result.scalars().all()

        # 查关联入库记录
        inbound_result = await db.execute(
            select(StockInbound)
            .where(StockInbound.source_type == "purchase_order", StockInbound.source_id == o.id)
        )
        inbounds = inbound_result.scalars().all()

        # 汇总
        factories = list({p.factory for p in products if p.factory})
        total_boxes = sum(p.box_count or 0 for p in products)
        total_weight = sum(float(p.weight_kg or 0) for p in products)
        total_amount = sum(float(p.total_amount or 0) for p in products)

        data.append({
            "id": o.id,
            "purchase_no": o.purchase_no,
            "purchase_date": o.purchase_date.isoformat() if o.purchase_date else None,
            "supplier_id": o.supplier_id,
            "supplier_name": o.supplier_name,
            "order_type": o.order_type,
            "total_amount": total_amount,
            "after_sales_adjustment": float(o.after_sales_adjustment or 0),
            "net_amount": total_amount - float(o.after_sales_adjustment or 0),
            "paid_amount": float(o.paid_amount or 0),
            "payment_status": o.payment_status or "unpaid",
            "total_weight": round(total_weight, 2),
            "total_boxes": total_boxes,
            "slaughter_date": o.slaughter_date.isoformat() if o.slaughter_date else None,
            "remark": o.remark,
            "status": o.status,
            "sale_id": o.sale_id,
            "factories": factories,
            "products": [
                {
                    "id": p.id,
                    "product_name": p.product_name,
                    "product_spec": p.product_spec,
                    "factory": p.factory,
                    "box_count": p.box_count,
                    "weight_kg": float(p.weight_kg) if p.weight_kg else 0,
                    "batch": p.batch,
                    "unit_price": float(p.unit_price) if p.unit_price else 0,
                    "total_amount": float(p.total_amount) if p.total_amount else 0,
                    "unit": p.unit or "kg",
                }
                for p in products
            ],
            "inbounds": [
                {
                    "inbound_no": ib.inbound_no,
                    "batch_no": (ib.detail or {}).get("batch_no", ""),
                    "inbound_date": ib.inbound_date.isoformat() if ib.inbound_date else None,
                    "remaining_weight_kg": float(ib.remaining_qty or 0),
                    "remaining_box_count": ib.remaining_box_count or 0,
                }
                for ib in inbounds
            ],
        })
    return {"success": True, "data": data}


@router.get("/purchase-orders/{order_id}")
async def api_get_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """获取采购入库单详情"""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(PurchaseOrderV2)
        .options(selectinload(PurchaseOrderV2.products))
        .where(PurchaseOrderV2.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="采购入库单不存在")

    products = order.products
    factories = list({p.factory for p in products if p.factory})
    total_boxes = sum(p.box_count or 0 for p in products)
    total_weight = sum(float(p.weight_kg or 0) for p in products)
    total_amount = sum(float(p.total_amount or 0) for p in products)

    # 查关联销售单单号
    sale_no = None
    if order.sale_id:
        sale_result = await db.execute(
            select(FinishedProductSaleV2.sale_no).where(FinishedProductSaleV2.id == order.sale_id)
        )
        sale_row = sale_result.scalar_one_or_none()
        sale_no = sale_row

    return {
        "success": True,
        "data": {
            "id": order.id,
            "purchase_no": order.purchase_no,
            "purchase_date": order.purchase_date.isoformat() if order.purchase_date else None,
            "supplier_id": order.supplier_id,
            "supplier_name": order.supplier_name,
            "order_type": order.order_type,
            "total_amount": total_amount,
            "after_sales_adjustment": float(order.after_sales_adjustment or 0),
            "net_amount": total_amount - float(order.after_sales_adjustment or 0),
            "paid_amount": float(order.paid_amount or 0),
            "payment_status": order.payment_status or "unpaid",
            "total_weight": round(total_weight, 2),
            "total_boxes": total_boxes,
            "slaughter_date": order.slaughter_date.isoformat() if order.slaughter_date else None,
            "remark": order.remark,
            "status": order.status,
            "sale_id": order.sale_id,
            "sale_no": sale_no,
            "factory": factories[0] if factories else "",
            "factories": factories,
            "products": [
                {
                    "id": p.id,
                    "product_name": p.product_name,
                    "product_spec": p.product_spec,
                    "factory": p.factory,
                    "box_count": p.box_count,
                    "weight_kg": float(p.weight_kg) if p.weight_kg else 0,
                    "batch": p.batch,
                    "unit_price": float(p.unit_price) if p.unit_price else 0,
                    "total_amount": float(p.total_amount) if p.total_amount else 0,
                }
                for p in products
            ],
        }
    }


@router.post("/purchase-orders")
async def api_create_purchase_order(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """创建采购入库单，单号自动生成"""
    # 自动生成采购单号
    purchase_no = data.get("purchase_no")
    if not purchase_no:
        from datetime import datetime as _dt
        date_str = _dt.now().strftime("%Y%m%d")
        # 查询当天最大序号
        result = await db.execute(
            select(PurchaseOrderV2).where(PurchaseOrderV2.purchase_no.like(f"CG{date_str}-%"))
        )
        existing = result.scalars().all()
        max_seq = 0
        for o in existing:
            try:
                seq = int(o.purchase_no.split("-")[-1])
                max_seq = max(max_seq, seq)
            except Exception:
                pass
        purchase_no = f"CG{date_str}-{str(max_seq + 1).zfill(3)}"

    order = PurchaseOrderV2(
        purchase_no=purchase_no,
        purchase_date=_parse_date(data.get("purchase_date")),
        supplier_id=data.get("supplier_id"),
        supplier_name=data.get("supplier_name"),
        order_type=data.get("order_type", "raw_material"),
        total_amount=Decimal(str(data.get("total_amount", 0))),
        total_weight=Decimal(str(data.get("total_weight", 0))),
        total_boxes=data.get("total_boxes", 0),
        slaughter_date=_parse_date(data.get("slaughter_date")),
        remark=data.get("remark"),
        status=data.get("status", "completed"),
        sale_id=data.get("sale_id"),  # 以销定采：关联销售单
    )
    db.add(order)
    await db.flush()

    for p in data.get("products", []):
        product = PurchaseOrderProductV2(
            purchase_order_id=order.id,
            product_name=p.get("product_name"),
            product_spec=p.get("product_spec", ""),
            factory=p.get("factory"),
            box_count=p.get("box_count", 0),
            weight_kg=Decimal(str(p.get("weight_kg", 0))),
            batch=p.get("batch"),
            unit=p.get("unit"),
            unit_price=Decimal(str(p.get("unit_price", 0))),
            total_amount=Decimal(str(p.get("total_amount", 0))),
        )
        db.add(product)

    await db.commit()

    # 重新加载 order 及其 products（async SQLAlchemy 不支持懒加载）
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(PurchaseOrderV2)
        .options(selectinload(PurchaseOrderV2.products))
        .where(PurchaseOrderV2.id == order.id)
    )
    order = result.scalar_one()

    # 以销定采：一对一校验 + 更新销售单状态
    if order.sale_id:
        existing = await db.execute(
            select(PurchaseOrderV2).where(
                PurchaseOrderV2.sale_id == order.sale_id,
                PurchaseOrderV2.id != order.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该销售单已有关联采购单，一个销售单只能对应一次采购")

        sale_result = await db.execute(
            select(FinishedProductSaleV2)
            .options(selectinload(FinishedProductSaleV2.products))
            .where(FinishedProductSaleV2.id == order.sale_id)
        )
        sale = sale_result.scalar_one_or_none()
        if sale:
            # 更新销售单的重量、箱数（采购实际到货数据）
            sale.status = "ordered"
            if order.total_weight and (sale.weight is None or sale.weight == 0):
                sale.weight = order.total_weight
            if order.total_boxes and (sale.quantity is None or sale.quantity == 0):
                sale.quantity = order.total_boxes

            # 按规格+工厂+箱数匹配，把采购明细实际重量复制到销售单对应明细
            # 避免同规格同工厂的多行采购明细互相覆盖
            purchase_map = {}
            for p in order.products:
                key = (p.product_spec or "", p.factory or "", p.box_count or 0)
                purchase_map[key] = p
            for sp in sale.products:
                key = (sp.product_spec or "", sp.factory or "", sp.box_count or 0)
                pp = purchase_map.get(key)
                if pp and pp.weight_kg and pp.weight_kg > 0:
                    sp.weight_kg = pp.weight_kg
                    sp.total_amount = round2dec(sp.weight_kg * sp.unit_price)
            # 重新汇总销售单
            sale.weight = sum(p.weight_kg or Decimal("0") for p in sale.products)
            sale.total_amount = sum(p.total_amount or Decimal("0") for p in sale.products)
            sale.actual_amount = sale.total_amount - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - (sale.rounding or Decimal("0"))
            sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0"))
            await db.commit()

    # 自动推仓库入库
    try:
        inbounds = await _auto_inbound_from_purchase(db, order)
    except Exception:
        import traceback
        traceback.print_exc()
        inbounds = []

    return {"success": True, "data": {"id": order.id, "purchase_no": purchase_no, "inbounds": inbounds}}


@router.put("/purchase-orders/{order_id}")
async def api_update_purchase_order(
    order_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_warehouse),
):
    """更新采购入库单"""
    result = await db.execute(select(PurchaseOrderV2).where(PurchaseOrderV2.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="采购入库单不存在")

    order.purchase_no = data.get("purchase_no", order.purchase_no)
    order.purchase_date = _parse_date(data.get("purchase_date")) or order.purchase_date
    order.supplier_id = data.get("supplier_id", order.supplier_id)
    order.supplier_name = data.get("supplier_name", order.supplier_name)
    order.total_amount = Decimal(str(data.get("total_amount", order.total_amount)))
    order.total_weight = Decimal(str(data.get("total_weight", order.total_weight)))
    order.total_boxes = data.get("total_boxes", order.total_boxes)
    order.slaughter_date = _parse_date(data.get("slaughter_date")) or order.slaughter_date
    order.remark = data.get("remark", order.remark)
    new_sale_id = data.get("sale_id", order.sale_id)
    old_sale_id = order.sale_id

    # 以销定采：一对一校验
    if new_sale_id and new_sale_id != old_sale_id:
        existing = await db.execute(
            select(PurchaseOrderV2).where(
                PurchaseOrderV2.sale_id == new_sale_id,
                PurchaseOrderV2.id != order.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="该销售单已有关联采购单，一个销售单只能对应一次采购")

    order.sale_id = new_sale_id

    # 删除旧明细
    await db.execute(
        select(PurchaseOrderProductV2).where(PurchaseOrderProductV2.purchase_order_id == order_id)
    )
    old_products = await db.execute(
        select(PurchaseOrderProductV2).where(PurchaseOrderProductV2.purchase_order_id == order_id)
    )
    for p in old_products.scalars().all():
        await db.delete(p)

    # 创建新明细
    for p in data.get("products", []):
        product = PurchaseOrderProductV2(
            purchase_order_id=order.id,
            product_name=p.get("product_name"),
            product_spec=p.get("product_spec", ""),
            factory=p.get("factory"),
            box_count=p.get("box_count", 0),
            weight_kg=Decimal(str(p.get("weight_kg", 0))),
            batch=p.get("batch"),
            unit=p.get("unit"),
            unit_price=Decimal(str(p.get("unit_price", 0))),
            total_amount=Decimal(str(p.get("total_amount", 0))),
        )
        db.add(product)

    await db.commit()

    # 重新加载 order 及其 products
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(PurchaseOrderV2)
        .options(selectinload(PurchaseOrderV2.products))
        .where(PurchaseOrderV2.id == order.id)
    )
    order = result.scalar_one()

    # 以销定采：处理新旧销售单状态切换
    if old_sale_id and old_sale_id != new_sale_id:
        old_sale_result = await db.execute(
            select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == old_sale_id)
        )
        old_sale = old_sale_result.scalar_one_or_none()
        if old_sale:
            old_sale.status = "pending"

    if order.sale_id:
        sale_result = await db.execute(
            select(FinishedProductSaleV2)
            .options(selectinload(FinishedProductSaleV2.products))
            .where(FinishedProductSaleV2.id == order.sale_id)
        )
        sale = sale_result.scalar_one_or_none()
        if sale:
            sale.status = "ordered"
            sale.weight = order.total_weight
            sale.quantity = order.total_boxes
            # 按规格+工厂+箱数匹配，把采购明细实际重量复制到销售单对应明细
            purchase_map = {}
            for p in order.products:
                key = (p.product_spec or "", p.factory or "", p.box_count or 0)
                purchase_map[key] = p
            for sp in sale.products:
                key = (sp.product_spec or "", sp.factory or "", sp.box_count or 0)
                pp = purchase_map.get(key)
                if pp and pp.weight_kg and pp.weight_kg > 0:
                    sp.weight_kg = pp.weight_kg
                    sp.total_amount = round2dec(sp.weight_kg * sp.unit_price)
            sale.weight = sum(p.weight_kg or Decimal("0") for p in sale.products)
            sale.total_amount = sum(p.total_amount or Decimal("0") for p in sale.products)
            sale.actual_amount = sale.total_amount - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - (sale.rounding or Decimal("0"))
            sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0"))
            await db.commit()

    return {"success": True}


@router.delete("/purchase-orders/{order_id}")
async def api_delete_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    """删除采购入库单，同步回退库存"""
    from sqlalchemy import delete as sa_delete

    from app.models.warehouse import Stock, StockInbound, StockMovement

    result = await db.execute(select(PurchaseOrderV2).where(PurchaseOrderV2.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="采购入库单不存在")

    # 1. 查关联的入库记录
    inbound_result = await db.execute(
        select(StockInbound).where(StockInbound.source_type == "purchase_order", StockInbound.source_id == order_id)
    )
    inbounds = inbound_result.scalars().all()

    for inbound in inbounds:
        # 回退库存数量
        if inbound.qty and inbound.warehouse_id and inbound.product_id:
            stock_result = await db.execute(
                select(Stock).where(Stock.warehouse_id == inbound.warehouse_id, Stock.product_id == inbound.product_id)
            )
            stock = stock_result.scalar_one_or_none()
            if stock:
                stock.current_qty = (stock.current_qty or Decimal("0")) - inbound.qty
                if stock.current_qty < 0:
                    stock.current_qty = Decimal("0")
                # 回退总成本
                if inbound.total_cost and stock.total_cost:
                    stock.total_cost = stock.total_cost - inbound.total_cost
                    if stock.total_cost < 0:
                        stock.total_cost = Decimal("0")
                    # 重新计算单位成本
                    if stock.current_qty > 0:
                        stock.unit_cost = stock.total_cost / stock.current_qty
                    else:
                        stock.unit_cost = None
                # available_qty 必须始终等于 current_qty - reserved_qty
                stock.available_qty = stock.current_qty - (stock.reserved_qty or Decimal("0"))
                if stock.available_qty < 0:
                    stock.available_qty = Decimal("0")

        # 删除关联的库存变动记录
        await db.execute(
            sa_delete(StockMovement).where(
                StockMovement.warehouse_id == inbound.warehouse_id,
                StockMovement.product_id == inbound.product_id,
                StockMovement.ref_type == "purchase_order",
                StockMovement.ref_no == order.purchase_no
            )
        )

        # 删除入库记录
        await db.delete(inbound)

    # 2. 删除前记录关联销售单（如有）
    sale_id = order.sale_id

    # 3. 删除采购单（级联删除 products）
    await db.delete(order)
    await db.commit()

    # 4. 恢复关联销售单状态为待采购
    if sale_id:
        sale_result = await db.execute(
            select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id)
        )
        sale = sale_result.scalar_one_or_none()
        if sale:
            sale.status = "pending"
            await db.commit()

    return {"success": True}


# ==================== 成品销售管理 ====================

@router.get("/finished-product-sales")
async def api_get_finished_sales(
    sale_type: str | None = Query(None, description="销售类型: whole_fish/finished_product"),
    ids: str | None = Query(None, description="按ID列表过滤，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_sales),
):
    """获取所有成品销售记录（以销定采：包含关联采购单信息）"""
    from sqlalchemy import func

    from app.models.finished_product import FinishedProductReceipt

    query = select(FinishedProductSaleV2)
    if ids:
        try:
            id_list = [int(x.strip()) for x in ids.split(",") if x.strip()]
            if id_list:
                query = query.where(FinishedProductSaleV2.id.in_(id_list))
        except ValueError:
            pass
    result = await db.execute(query.order_by(FinishedProductSaleV2.created_at.desc()))
    sales = result.scalars().all()

    # 按 sale_type 过滤
    if sale_type:
        sales = [s for s in sales if s.sale_type == sale_type]

    # 批量查询关联采购单（以销定采）
    sale_ids = [s.id for s in sales]
    purchase_map = {}
    if sale_ids:
        purchase_result = await db.execute(
            select(PurchaseOrderV2).where(PurchaseOrderV2.sale_id.in_(sale_ids))
        )
        for po in purchase_result.scalars().all():
            if po.sale_id not in purchase_map:
                purchase_map[po.sale_id] = []
            purchase_map[po.sale_id].append(po)

    data = []
    for s in sales:
        # 查询该销售单的第一个产品
        products_result = await db.execute(
            select(FinishedSaleProductV2)
            .where(FinishedSaleProductV2.sale_id == s.id)
            .order_by(FinishedSaleProductV2.id)
            .limit(1)
        )
        first_product = products_result.scalar_one_or_none()

        # 查已收金额（支持 sale_v2_id）
        receipt_result = await db.execute(
            select(func.sum(FinishedProductReceipt.amount))
            .where(
                (FinishedProductReceipt.sale_id == s.id) |
                (FinishedProductReceipt.sale_v2_id == s.id)
            )
        )
        paid_amount = float(receipt_result.scalar() or 0)

        # 计算付款状态
        net_amount = float(s.net_amount or 0)
        if paid_amount >= net_amount and net_amount > 0:
            payment_status = "fully_paid"
        elif paid_amount > 0:
            payment_status = "partial_paid"
        else:
            payment_status = "pending"

        # 以销定采：批次号直接取销售单上的
        batch_no = s.batch_no or ""

        # 以销定采状态流转（独立于销售单的 status/paid 状态）
        related_purchases = purchase_map.get(s.id, [])
        purchase_count = len(related_purchases)
        purchase_total_weight = sum(float(po.total_weight or 0) for po in related_purchases)
        purchase_total_amount = sum(float(po.total_amount or 0) for po in related_purchases)

        # 采购状态：只看采购单，不看收款状态
        procurement_status = "pending"
        if purchase_count > 0:
            procurement_status = "ordered"
            # 检查是否全部到货
            all_arrived = all(po.status in ["completed", "arrived"] for po in related_purchases)
            if all_arrived:
                procurement_status = "arrived"

        data.append({
            "id": s.id,
            "sale_no": s.sale_no,
            "sale_type": s.sale_type,
            "status": s.status,
            "procurement_status": procurement_status,
            "customer": s.customer,
            "salesperson": s.salesperson,
            "product_name": s.product_name,
            "quantity": float(s.quantity) if s.quantity else 0,
            "weight": float(s.weight) if s.weight else 0,
            "unit_price": float(s.unit_price) if s.unit_price else 0,
            "total_amount": float(s.total_amount) if s.total_amount else 0,
            "sale_date": s.sale_date.isoformat() if s.sale_date else None,
            "discount": float(s.discount) if s.discount else 0,
            "scan_fee": float(s.scan_fee) if s.scan_fee else 0,
            "freight": float(s.freight) if s.freight else 0,
            "rounding": float(s.rounding) if s.rounding else 0,
            "after_sales_adjustment": float(s.after_sales_adjustment) if s.after_sales_adjustment else 0,
            "commission": float(s.commission) if s.commission else 0,
            "actual_amount": float(s.actual_amount) if s.actual_amount else 0,
            "net_amount": net_amount,
            "paid": s.paid,
            "paid_amount": paid_amount,
            "payment_status": payment_status,
            "remark": s.remark,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "first_product_name": first_product.product_name if first_product else None,
            "first_product_spec": first_product.product_spec if first_product else None,
            "first_product_factory": first_product.factory if first_product else None,
            "batch_no": batch_no,
            "slaughter_date": s.slaughter_date.isoformat() if s.slaughter_date else None,
            "delivery_address": s.delivery_address,
            "logistics_info": s.logistics_info,
            "factory": s.factory,
            "products": [
                {
                    "variant_id": p.variant_id,
                    "product_id": p.product_id,
                    "product_name": p.product_name,
                    "product_spec": p.product_spec,
                    "factory": p.factory,
                    "batch": p.batch,
                    "slaughter_date": p.slaughter_date.isoformat() if p.slaughter_date else None,
                    "box_count": p.box_count,
                    "sale_unit": p.sale_unit,
                    "weight_kg": float(p.weight_kg) if p.weight_kg else 0,
                    "unit_price": float(p.unit_price) if p.unit_price else 0,
                    "total_amount": float(p.total_amount) if p.total_amount else 0,
                }
                for p in s.products
            ] if s.products else [],
            "purchase_count": purchase_count,
            "purchase_total_weight": purchase_total_weight,
            "purchase_total_amount": purchase_total_amount,
            "receipts": [],
        })
    return {"success": True, "data": data}


@router.get("/finished-product-sales/{sale_id}")
async def api_get_finished_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_sales),
):
    """获取成品销售记录详情（以销定采：包含关联采购单）"""
    result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = result.scalar_one_or_none()
    if not sale:
        raise HTTPException(status_code=404, detail="销售记录不存在")

    products_result = await db.execute(
        select(FinishedSaleProductV2).where(FinishedSaleProductV2.sale_id == sale_id)
    )
    products = products_result.scalars().all()

    # 旧数据修复：如果明细重量全为0但订单级有值，按实际采购重量或箱数比例分摊
    sale_weight = float(sale.weight) if sale.weight else 0
    if sale_weight > 0 and products and all(not p.weight_kg or p.weight_kg == 0 for p in products):
        # 优先查关联采购单的实际重量（按规格匹配）
        purchase_result = await db.execute(
            select(PurchaseOrderV2)
            .options(selectinload(PurchaseOrderV2.products))
            .where(PurchaseOrderV2.sale_id == sale_id)
        )
        purchases = purchase_result.scalars().all()
        if purchases:
            # 收集所有采购明细，按规格+工厂+箱数分组（多个采购单累加）
            purchase_map = {}
            for purchase in purchases:
                for p in purchase.products or []:
                    key = (p.product_spec or "", p.factory or "", p.box_count or 0)
                    if key not in purchase_map:
                        purchase_map[key] = Decimal("0")
                    purchase_map[key] += (p.weight_kg or Decimal("0"))
            for p in products:
                key = (p.product_spec or "", p.factory or "", p.box_count or 0)
                purchase_weight = purchase_map.get(key)
                if purchase_weight and purchase_weight > 0:
                    p.weight_kg = purchase_weight
                    p.total_amount = round2dec(p.weight_kg * p.unit_price)
        else:
            # 无采购单则按箱数比例分摊
            total_boxes = sum(p.box_count or 0 for p in products)
            if total_boxes > 0:
                for p in products:
                    ratio = Decimal(str(p.box_count or 0)) / Decimal(str(total_boxes))
                    p.weight_kg = round2dec(sale.weight * ratio)
                    p.total_amount = round2dec(p.weight_kg * p.unit_price)
        # 重新汇总销售单
        sale.weight = sum(p.weight_kg or Decimal("0") for p in products)
        sale.total_amount = sum(p.total_amount or Decimal("0") for p in products)
        sale.actual_amount = sale.total_amount - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - (sale.rounding or Decimal("0"))
        sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0"))
        await db.commit()

    # 以销定采：查询关联的采购单
    purchase_result = await db.execute(
        select(PurchaseOrderV2).where(PurchaseOrderV2.sale_id == sale_id)
    )
    purchases = purchase_result.scalars().all()

    # 查收款记录
    receipt_result = await db.execute(
        select(FinishedProductReceipt).where(FinishedProductReceipt.sale_v2_id == sale_id)
    )
    receipts = receipt_result.scalars().all()

    # 查售后记录
    aftersales_result = await db.execute(
        select(FinishedProductAftersales).where(FinishedProductAftersales.sale_id == sale_id)
    )
    aftersales = aftersales_result.scalars().all()

    # 查退货单（关联 finished_product_sale_v2_id）
    return_result = await db.execute(
        select(ReturnOrder).where(ReturnOrder.finished_product_sale_v2_id == sale_id)
    )
    return_orders = return_result.scalars().all()

    return {
        "success": True,
        "data": {
            "id": sale.id,
            "sale_no": sale.sale_no,
            "sale_type": sale.sale_type,
            "customer": sale.customer,
            "salesperson": sale.salesperson,
            "product_name": sale.product_name,
            "quantity": float(sale.quantity) if sale.quantity else 0,
            "weight": float(sale.weight) if sale.weight else 0,
            "unit_price": float(sale.unit_price) if sale.unit_price else 0,
            "total_amount": float(sale.total_amount) if sale.total_amount else 0,
            "sale_date": sale.sale_date.isoformat() if sale.sale_date else None,
            "discount": float(sale.discount) if sale.discount else 0,
            "scan_fee": float(sale.scan_fee) if sale.scan_fee else 0,
            "freight": float(sale.freight) if sale.freight else 0,
            "rounding": float(sale.rounding) if sale.rounding else 0,
            "after_sales_adjustment": float(sale.after_sales_adjustment) if sale.after_sales_adjustment else 0,
            "commission": float(sale.commission) if sale.commission else 0,
            "actual_amount": float(sale.actual_amount) if sale.actual_amount else 0,
            "net_amount": float(sale.net_amount) if sale.net_amount else 0,
            "paid": sale.paid,
            "remark": sale.remark,
            "status": sale.status,
            "batch_no": sale.batch_no,
            "slaughter_date": sale.slaughter_date.isoformat() if sale.slaughter_date else None,
            "delivery_address": sale.delivery_address,
            "logistics_info": sale.logistics_info,
            "factory": sale.factory,
            "products": [
                {
                    "id": p.id,
                    "variant_id": p.variant_id,
                    "product_id": p.product_id,
                    "product_name": p.product_name,
                    "product_spec": p.product_spec,
                    "factory": p.factory,
                    "batch": p.batch,
                    "slaughter_date": p.slaughter_date.isoformat() if p.slaughter_date else None,
                    "box_count": p.box_count,
                    "sale_unit": p.sale_unit,
                    "weight_kg": float(p.weight_kg) if p.weight_kg else 0,
                    "unit_price": float(p.unit_price) if p.unit_price else 0,
                    "total_amount": float(p.total_amount) if p.total_amount else 0,
                    "commission_rate": float(p.commission_rate) if p.commission_rate else 0,
                    "commission_amount": float(p.commission_amount) if p.commission_amount else 0,
                    "after_sales_adjustment": float(p.after_sales_adjustment) if p.after_sales_adjustment else 0,
                }
                for p in products
            ],
            "purchases": [
                {
                    "id": po.id,
                    "purchase_no": po.purchase_no,
                    "purchase_date": po.purchase_date.isoformat() if po.purchase_date else None,
                    "supplier_name": po.supplier_name,
                    "total_weight": float(po.total_weight) if po.total_weight else 0,
                    "total_amount": float(po.total_amount) if po.total_amount else 0,
                    "total_boxes": po.total_boxes,
                    "status": po.status,
                    "slaughter_date": po.slaughter_date.isoformat() if po.slaughter_date else None,
                }
                for po in purchases
            ],
            "receipts": [
                {
                    "id": r.id,
                    "sale_id": r.sale_v2_id,
                    "receipt_date": r.receipt_date.isoformat() if r.receipt_date else None,
                    "amount": float(r.amount) if r.amount else 0,
                    "payment_method": r.payment_method or "bank_transfer",
                    "bank_account_id": r.bank_account_id,
                    "reference_no": r.reference_no,
                    "notes": r.notes,
                }
                for r in receipts
            ],
            "aftersales": [
                {
                    "id": a.id,
                    "sale_id": a.sale_id,
                    "record_date": a.record_date.isoformat() if a.record_date else None,
                    "type": a.type,
                    "amount": float(a.amount) if a.amount else 0,
                    "reason": a.reason,
                    "status": a.status,
                    "notes": a.notes,
                }
                for a in aftersales
            ],
            "return_orders": [
                {
                    "id": ro.id,
                    "return_no": ro.return_no,
                    "return_date": ro.return_date.isoformat() if ro.return_date else None,
                    "status": ro.status.value if ro.status else "draft",
                    "total_weight_kg": float(ro.total_weight_kg) if ro.total_weight_kg else 0,
                    "total_amount": float(ro.total_amount) if ro.total_amount else 0,
                    "refund_amount": float(ro.refund_amount) if ro.refund_amount else 0,
                    "problem_description": ro.problem_description,
                    "customer_feedback": ro.customer_feedback,
                }
                for ro in return_orders
            ],
        }
    }


@router.post("/finished-product-sales")
async def api_create_finished_sale(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_sales),
):
    """创建成品销售记录（以销定采，单号自动生成）"""
    # 自动生成销售单号
    sale_no = data.get("sale_no")
    if not sale_no:
        from datetime import datetime as _dt
        prefix = "WF" if data.get("sale_type") == "whole_fish" else "CP"
        date_str = _dt.now().strftime("%Y%m%d")
        result = await db.execute(
            select(FinishedProductSaleV2).where(FinishedProductSaleV2.sale_no.like(f"{prefix}{date_str}-%"))
        )
        existing = result.scalars().all()
        max_seq = 0
        for s in existing:
            try:
                seq = int(s.sale_no.split("-")[-1])
                max_seq = max(max_seq, seq)
            except Exception:
                pass
        sale_no = f"{prefix}{date_str}-{str(max_seq + 1).zfill(3)}"

    # 以销定采：汇总产品明细
    products = data.get("products", [])
    total_amount = sum(Decimal(str(p.get("total_amount", 0))) for p in products)
    total_weight = sum(float(p.get("weight_kg", 0)) for p in products)
    total_boxes = sum(p.get("box_count", 0) for p in products)

    # 费用
    discount = Decimal(str(data.get("discount", 0)))
    scan_fee = Decimal(str(data.get("scan_fee", 0)))
    freight = Decimal(str(data.get("freight", 0)))
    rounding = Decimal(str(data.get("rounding", 0)))
    after_sales_adjustment = Decimal(str(data.get("after_sales_adjustment", 0)))
    commission = Decimal(str(data.get("commission", 0)))
    net_amount = total_amount + freight - discount - scan_fee - rounding - after_sales_adjustment - commission

    # 以销定采：生成批次号（MMDD-加工厂缩写-NNN）
    from datetime import date as _date
    today = _date.today()
    order_factory = data.get("factory", "")
    batch_no = f"{today.strftime('%m%d')}-{order_factory[:4] if order_factory else 'UNK'}-{sale_no.split('-')[-1]}"

    sale = FinishedProductSaleV2(
        sale_no=sale_no,
        sale_type=data.get("sale_type", "whole_fish"),
        customer=data.get("customer"),
        salesperson=data.get("salesperson"),
        product_name=data.get("product_name"),
        quantity=Decimal(str(total_boxes)) if total_boxes else None,
        weight=Decimal(str(total_weight)) if total_weight else None,
        unit_price=Decimal(str(products[0].get("unit_price", 0))) if products else None,
        total_amount=total_amount,
        sale_date=_parse_date(data.get("sale_date")),
        discount=discount,
        scan_fee=scan_fee,
        freight=freight,
        rounding=rounding,
        after_sales_adjustment=after_sales_adjustment,
        commission=commission,
        actual_amount=total_amount + freight - discount - scan_fee - rounding,
        net_amount=net_amount,
        paid=1 if data.get("paid") else 0,
        remark=data.get("remark"),
        status="pending",  # 以销定采：初始状态待采购
        batch_no=batch_no,
        factory=data.get("factory"),
        slaughter_date=_parse_date(data.get("slaughter_date")),
        delivery_address=data.get("delivery_address"),
        logistics_info=data.get("logistics_info"),
    )
    db.add(sale)
    await db.flush()

    for p in products:
        product = FinishedSaleProductV2(
            sale_id=sale.id,
            variant_id=p.get("variant_id"),
            product_id=p.get("product_id"),
            product_name=p.get("product_name"),
            product_spec=p.get("product_spec", ""),
            factory=p.get("factory"),
            batch=p.get("batch"),
            slaughter_date=_parse_date(p.get("slaughter_date")),
            box_count=p.get("box_count", 0),
            weight_kg=Decimal(str(p.get("weight_kg", 0))),
            sale_unit=p.get("sale_unit"),
            unit_price=Decimal(str(p.get("unit_price", 0))),
            total_amount=Decimal(str(p.get("total_amount", 0))),
            commission_rate=Decimal(str(p.get("commission_rate", 0))),
            commission_amount=Decimal(str(p.get("commission_amount", 0))),
            after_sales_adjustment=Decimal(str(p.get("after_sales_adjustment", 0))),
        )
        db.add(product)

    await db.commit()

    # 成品销售自动出库
    if sale.sale_type == "finished_product":
        try:
            # 重新加载销售单及产品明细（commit 后对象可能已过期）
            result = await db.execute(
                select(FinishedProductSaleV2)
                .options(selectinload(FinishedProductSaleV2.products))
                .where(FinishedProductSaleV2.id == sale.id)
            )
            fresh_sale = result.scalar_one()
            await _auto_outbound_from_sale(db, fresh_sale)
        except Exception as e:
            # 出库失败不影响销售单创建，但记录日志
            import logging
            logging.getLogger(__name__).warning(f"销售单 {sale.sale_no} 自动出库失败: {e}")

    return {"success": True, "data": {"id": sale.id, "sale_no": sale.sale_no, "batch_no": batch_no}}



@router.put("/finished-product-sales/{sale_id}")
async def api_update_finished_sale(
    sale_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_sales),
):
    """更新成品销售记录（自动重算 actual_amount / net_amount）"""
    result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = result.scalar_one_or_none()
    if not sale:
        raise HTTPException(status_code=404, detail="销售记录不存在")

    # 直接字段更新
    for field in ["sale_no", "sale_type", "source_id", "source_no", "customer", "salesperson",
                  "product_name", "factory", "delivery_address", "logistics_info", "remark"]:
        if field in data:
            setattr(sale, field, data[field])

    if "sale_date" in data:
        sale.sale_date = _parse_date(data["sale_date"])

    if "slaughter_date" in data:
        sale.slaughter_date = _parse_date(data["slaughter_date"])

    for field in ["quantity", "weight", "unit_price", "total_amount"]:
        if field in data:
            val = data[field]
            setattr(sale, field, Decimal(str(val)) if val is not None else None)

    if "paid" in data:
        sale.paid = 1 if data["paid"] else 0

    # 费用/调整字段（触发自动重算）
    cost_fields = ["discount", "scan_fee", "freight", "rounding", "after_sales_adjustment", "commission", "balance_adjustment"]
    recalc_needed = any(field in data for field in cost_fields)
    for field in cost_fields:
        if field in data:
            val = data[field]
            setattr(sale, field, Decimal(str(val)) if val is not None else Decimal("0"))

    # 自动重算 actual_amount / net_amount
    if recalc_needed:
        total = sale.total_amount or Decimal("0")
        freight = Decimal(str(data.get("freight", sale.freight or 0)))
        sale.freight = freight
        sale.actual_amount = total + freight - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - (sale.rounding or Decimal("0"))
        sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0")) - (sale.balance_adjustment or Decimal("0"))

    # 更新明细（仅在编辑时传入 products 才重建）
    if "products" in data:
        # 删除旧明细
        old_products = await db.execute(
            select(FinishedSaleProductV2).where(FinishedSaleProductV2.sale_id == sale_id)
        )
        for p in old_products.scalars().all():
            await db.delete(p)

        # 创建新明细
        for p in data.get("products", []):
            product = FinishedSaleProductV2(
                sale_id=sale.id,
                variant_id=p.get("variant_id"),
                product_id=p.get("product_id"),
                product_name=p.get("product_name"),
                product_spec=p.get("product_spec", ""),
                factory=p.get("factory"),
                batch=p.get("batch"),
                slaughter_date=_parse_date(p.get("slaughter_date")),
                box_count=p.get("box_count", 0),
                weight_kg=Decimal(str(p.get("weight_kg", 0))),
                sale_unit=p.get("sale_unit"),
                unit_price=Decimal(str(p.get("unit_price", 0))),
                total_amount=Decimal(str(p.get("total_amount", 0))),
                commission_rate=Decimal(str(p.get("commission_rate", 0))),
                commission_amount=Decimal(str(p.get("commission_amount", 0))),
                after_sales_adjustment=Decimal(str(p.get("after_sales_adjustment", 0))),
            )
            db.add(product)

    await db.commit()
    return {"success": True}


@router.delete("/finished-product-sales/{sale_id}")
async def api_delete_finished_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    """删除成品销售记录（以销定采：不需要回退库存）"""
    from sqlalchemy import delete as sa_delete
    from sqlalchemy.orm import selectinload

    from app.models.finished_product import FinishedSaleProductV2

    result = await db.execute(
        select(FinishedProductSaleV2)
        .options(selectinload(FinishedProductSaleV2.products))
        .where(FinishedProductSaleV2.id == sale_id)
    )
    sale = result.scalar_one_or_none()
    if not sale:
        raise HTTPException(status_code=404, detail="销售记录不存在")

    # 先查出所有收款记录（用于删除关联交易流水 & 恢复余额抵扣）
    receipt_result = await db.execute(
        select(FinishedProductReceipt).where(FinishedProductReceipt.sale_v2_id == sale_id)
    )
    receipts = receipt_result.scalars().all()

    # 1. 同步删除关联交易流水
    for receipt in receipts:
        if receipt.transaction_id:
            trans_result = await db.execute(
                select(TransactionRecord).where(TransactionRecord.id == receipt.transaction_id)
            )
            transaction = trans_result.scalar_one_or_none()
            if transaction:
                await db.delete(transaction)

    # 2. 余额抵扣：恢复客户预付余额
    for receipt in receipts:
        if receipt.payment_method == "balance" and receipt.amount and receipt.amount > 0 and sale.customer:
            company_result = await db.execute(
                select(Company).where(Company.name == sale.customer, Company.type == CompanyType.CUSTOMER)
            )
            company = company_result.scalar_one_or_none()
            if company:
                company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) + receipt.amount

    # 3. 删除收款记录
    await db.execute(
        sa_delete(FinishedProductReceipt).where(FinishedProductReceipt.sale_v2_id == sale_id)
    )

    # 4. 删除售后记录
    await db.execute(
        sa_delete(FinishedProductAftersales).where(FinishedProductAftersales.sale_id == sale_id)
    )

    # 5. 成品销售删除时回退库存（删除出库记录并恢复库存）
    if sale.sale_type == "finished_product":
        outbound_result = await db.execute(
            select(StockOutbound).where(StockOutbound.dest_id == sale.id, StockOutbound.dest_type == "sale")
        )
        outbounds = outbound_result.scalars().all()
        for outbound in outbounds:
            # 恢复库存（优先匹配批次）
            product = next((p for p in sale.products if p.product_id == outbound.product_id), None)
            batch_no = product.batch if product else None
            stock_query = select(Stock).where(Stock.warehouse_id == outbound.warehouse_id, Stock.product_id == outbound.product_id)
            if batch_no:
                stock_query = stock_query.where(Stock.batch_no == batch_no)
            stock_result = await db.execute(stock_query)
            stock = stock_result.scalar_one_or_none()
            if stock:
                stock.current_qty = stock.current_qty + outbound.qty
                stock.available_qty = stock.available_qty + outbound.qty
                stock.last_out_date = _date.today()

            # 恢复入库记录剩余量（按批次匹配）
            inbound_query = (
                select(StockInbound)
                .where(StockInbound.warehouse_id == outbound.warehouse_id)
                .where(StockInbound.product_id == outbound.product_id)
                .where(StockInbound.remaining_qty >= 0)
            )
            if batch_no:
                inbound_query = inbound_query.where(StockInbound.batch_no == batch_no)
            inbound_query = inbound_query.order_by(StockInbound.inbound_date.desc())
            inbound_result = await db.execute(inbound_query)
            inbounds = inbound_result.scalars().all()
            remaining_to_restore = outbound.qty
            for inbound in inbounds:
                if remaining_to_restore <= 0:
                    break
                max_restore = (inbound.qty or Decimal("0")) - (inbound.remaining_qty or Decimal("0"))
                if max_restore <= 0:
                    continue
                restore_qty = min(remaining_to_restore, max_restore)
                inbound.remaining_qty = (inbound.remaining_qty or Decimal("0")) + restore_qty
                remaining_to_restore = remaining_to_restore - restore_qty

        # 删除该销售单关联的出库记录和库存变动记录
        await db.execute(
            sa_delete(StockOutbound).where(StockOutbound.dest_id == sale.id, StockOutbound.dest_type == "sale")
        )
        await db.execute(
            sa_delete(StockMovement).where(StockMovement.ref_id == sale.id, StockMovement.ref_type == "finished_product_sale")
        )

    # 6. 删除产品明细
    await db.execute(
        sa_delete(FinishedSaleProductV2).where(FinishedSaleProductV2.sale_id == sale_id)
    )

    # 7. 删除销售单
    await db.delete(sale)
    await db.commit()
    return {"success": True}


@router.post("/finished-product-sales/batch-delete")
async def api_batch_delete_finished_sales(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
):
    """批量删除成品销售记录"""
    from sqlalchemy import delete as sa_delete
    from sqlalchemy.orm import selectinload

    from app.models.finished_product import FinishedSaleProductV2

    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="未提供删除ID列表")

    deleted = 0
    errors = []
    for sale_id in ids:
        try:
            result = await db.execute(
                select(FinishedProductSaleV2)
                .options(selectinload(FinishedProductSaleV2.products))
                .where(FinishedProductSaleV2.id == sale_id)
            )
            sale = result.scalar_one_or_none()
            if not sale:
                errors.append(f"销售记录 #{sale_id} 不存在")
                continue

            # 先查出所有收款记录（用于删除关联交易流水 & 恢复余额抵扣）
            receipt_result = await db.execute(
                select(FinishedProductReceipt).where(FinishedProductReceipt.sale_v2_id == sale_id)
            )
            receipts = receipt_result.scalars().all()

            # 同步删除关联交易流水
            for receipt in receipts:
                if receipt.transaction_id:
                    trans_result = await db.execute(
                        select(TransactionRecord).where(TransactionRecord.id == receipt.transaction_id)
                    )
                    transaction = trans_result.scalar_one_or_none()
                    if transaction:
                        await db.delete(transaction)

            # 余额抵扣：恢复客户预付余额
            for receipt in receipts:
                if receipt.payment_method == "balance" and receipt.amount and receipt.amount > 0 and sale.customer:
                    company_result = await db.execute(
                        select(Company).where(Company.name == sale.customer, Company.type == CompanyType.CUSTOMER)
                    )
                    company = company_result.scalar_one_or_none()
                    if company:
                        company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) + receipt.amount

            # 删除关联记录
            await db.execute(
                sa_delete(FinishedProductReceipt).where(FinishedProductReceipt.sale_v2_id == sale_id)
            )
            await db.execute(
                sa_delete(FinishedProductAftersales).where(FinishedProductAftersales.sale_id == sale_id)
            )

            # 成品销售批量删除时回退库存
            if sale.sale_type == "finished_product":
                outbound_result = await db.execute(
                    select(StockOutbound).where(StockOutbound.dest_id == sale.id, StockOutbound.dest_type == "sale")
                )
                outbounds = outbound_result.scalars().all()
                for outbound in outbounds:
                    product = next((p for p in sale.products if p.product_id == outbound.product_id), None)
                    batch_no = product.batch if product else None
                    stock_query = select(Stock).where(Stock.warehouse_id == outbound.warehouse_id, Stock.product_id == outbound.product_id)
                    if batch_no:
                        stock_query = stock_query.where(Stock.batch_no == batch_no)
                    stock_result = await db.execute(stock_query)
                    stock = stock_result.scalar_one_or_none()
                    if stock:
                        stock.current_qty = stock.current_qty + outbound.qty
                        stock.available_qty = stock.available_qty + outbound.qty
                        stock.last_out_date = _date.today()

                    inbound_query = (
                        select(StockInbound)
                        .where(StockInbound.warehouse_id == outbound.warehouse_id)
                        .where(StockInbound.product_id == outbound.product_id)
                    )
                    if batch_no:
                        inbound_query = inbound_query.where(StockInbound.batch_no == batch_no)
                    inbound_query = inbound_query.order_by(StockInbound.inbound_date.desc())
                    inbound_result = await db.execute(inbound_query)
                    inbounds = inbound_result.scalars().all()
                    remaining_to_restore = outbound.qty
                    for inbound in inbounds:
                        if remaining_to_restore <= 0:
                            break
                        max_restore = (inbound.qty or Decimal("0")) - (inbound.remaining_qty if inbound.remaining_qty is not None else (inbound.qty or Decimal("0")))
                        if max_restore <= 0:
                            continue
                        restore_qty = min(remaining_to_restore, max_restore)
                        inbound.remaining_qty = (inbound.remaining_qty if inbound.remaining_qty is not None else inbound.qty) + restore_qty
                        remaining_to_restore = remaining_to_restore - restore_qty

                await db.execute(
                    sa_delete(StockOutbound).where(StockOutbound.dest_id == sale.id, StockOutbound.dest_type == "sale")
                )
                await db.execute(
                    sa_delete(StockMovement).where(StockMovement.ref_id == sale.id, StockMovement.ref_type == "finished_product_sale")
                )

            await db.execute(
                sa_delete(FinishedSaleProductV2).where(FinishedSaleProductV2.sale_id == sale_id)
            )
            await db.delete(sale)
            deleted += 1
        except Exception as e:
            errors.append(f"销售记录 #{sale_id} 删除失败: {str(e)}")

    await db.commit()
    return {"success": True, "deleted": deleted, "errors": errors}



# ==================== 收款记录 ====================

@router.get("/finished-product-sales/{sale_id}/receipts")
async def api_list_finished_sale_receipts(sale_id: int, db: AsyncSession = Depends(get_db)):
    """成品销售收款记录列表"""
    receipt_result = await db.execute(
        select(FinishedProductReceipt).where(FinishedProductReceipt.sale_v2_id == sale_id)
    )
    receipts = receipt_result.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "sale_id": r.sale_v2_id,
                "receipt_date": r.receipt_date.isoformat() if r.receipt_date else None,
                "amount": float(r.amount) if r.amount else 0,
                "payment_method": r.payment_method or "bank_transfer",
                "bank_account_id": r.bank_account_id,
                "reference_no": r.reference_no,
                "notes": r.notes,
            }
            for r in receipts
        ],
    }


@router.post("/finished-product-sales/{sale_id}/receipts")
async def api_create_finished_sale_receipt(sale_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """创建成品销售收款记录（同步创建交易流水）"""
    from app.models.enums import TransactionCategory, TransactionType

    sale_result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise HTTPException(status_code=404, detail="销售记录不存在")

    received_amount = Decimal(str(data.get("amount", 0)))
    if received_amount <= 0:
        raise HTTPException(status_code=400, detail="收款金额必须大于0")

    # 余额抵扣：校验客户余额
    is_balance_payment = data.get("payment_method") == "balance"
    company = None
    if is_balance_payment:
        company_result = await db.execute(
            select(Company).where(
                Company.name == sale.customer,
                Company.type == CompanyType.CUSTOMER
            )
        )
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="客户不存在，无法使用余额抵扣")
        available_balance = Decimal(str(company.prepaid_balance or 0))
        if available_balance < received_amount:
            raise HTTPException(
                status_code=400,
                detail=f"客户预付款余额不足（当前余额 ¥{available_balance}，需扣款 ¥{received_amount}）"
            )
        data["bank_account_id"] = None

    # 抹零处理
    user_rounding = Decimal(str(data.pop("rounding_adjustment", 0) or 0))
    if user_rounding > 0:
        sale.rounding = (sale.rounding or Decimal("0")) + user_rounding
        # 抹零变化后重算 actual_amount / net_amount
        sale.actual_amount = sale.total_amount - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - (sale.rounding or Decimal("0"))
        sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0")) - (sale.balance_adjustment or Decimal("0"))
        await db.flush()

    receipt = FinishedProductReceipt(
        sale_v2_id=sale_id,
        receipt_date=_parse_date(data.get("receipt_date")),
        amount=received_amount,
        payment_method=data.get("payment_method", "bank_transfer"),
        bank_account_id=data.get("bank_account_id"),
        reference_no=data.get("reference_no"),
        notes=data.get("notes"),
    )
    db.add(receipt)
    await db.flush()

    # 非余额抵扣：同步创建交易流水
    if not is_balance_payment:
        bank_account_id = data.get("bank_account_id")
        user_notes = data.get("notes")
        desc = "销售收款"
        if user_notes:
            desc = f"{desc} - {user_notes}"

        transaction = TransactionRecord(
            transaction_date=_parse_date(data.get("receipt_date")),
            type=TransactionType.INCOME,
            category=TransactionCategory.MAIN_BUSINESS_REVENUE,
            amount=received_amount,
            currency="CNY",
            to_account_id=bank_account_id,
            counterparty_name=sale.customer,
            reference_no=data.get("reference_no") or sale.sale_no or f"#{sale.id}",
            description=desc,
            notes=user_notes,
            is_confirmed=True,
        )
        transaction.related_sale_ids = [sale.id]
        db.add(transaction)
        await db.flush()
        receipt.transaction_id = transaction.id

    # 余额抵扣：扣减客户预付余额
    if is_balance_payment and company:
        company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) - received_amount

    # 重新计算已收金额
    receipt_result = await db.execute(
        select(func.sum(FinishedProductReceipt.amount))
        .where(FinishedProductReceipt.sale_v2_id == sale_id)
    )
    paid_amount = receipt_result.scalar() or Decimal("0")
    sale.paid_amount = paid_amount

    # 更新付款状态
    net_amount = sale.net_amount or Decimal("0")
    status_net = net_amount + (sale.balance_adjustment or Decimal("0"))
    if paid_amount >= status_net and status_net > 0:
        sale.status = "paid"
        sale.paid = 1
    elif paid_amount > 0:
        sale.paid = 1
    else:
        sale.paid = 0

    await db.commit()
    return {
        "success": True,
        "data": {
            "id": receipt.id,
            "sale_id": receipt.sale_v2_id,
            "receipt_date": receipt.receipt_date.isoformat() if receipt.receipt_date else None,
            "amount": float(receipt.amount) if receipt.amount else 0,
            "payment_method": receipt.payment_method or "bank_transfer",
            "bank_account_id": receipt.bank_account_id,
            "reference_no": receipt.reference_no,
            "notes": receipt.notes,
        },
    }


@router.delete("/finished-product-sales/{sale_id}/receipts/{receipt_id}")
async def api_delete_finished_sale_receipt(sale_id: int, receipt_id: int, db: AsyncSession = Depends(get_db)):
    """删除成品销售收款记录（同步删除关联交易流水）"""
    receipt_result = await db.execute(
        select(FinishedProductReceipt)
        .where(FinishedProductReceipt.id == receipt_id, FinishedProductReceipt.sale_v2_id == sale_id)
    )
    receipt = receipt_result.scalar_one_or_none()
    if not receipt:
        # 兼容旧数据：尝试按 sale_id（V1 成品销售）匹配
        receipt_result = await db.execute(
            select(FinishedProductReceipt)
            .where(FinishedProductReceipt.id == receipt_id, FinishedProductReceipt.sale_id == sale_id)
        )
        receipt = receipt_result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="收款记录不存在")

    # 同步删除关联的交易流水
    if receipt.transaction_id:
        trans_result = await db.execute(
            select(TransactionRecord).where(TransactionRecord.id == receipt.transaction_id)
        )
        transaction = trans_result.scalar_one_or_none()
        if transaction:
            await db.delete(transaction)

    # 余额抵扣：恢复客户预付余额
    if receipt.payment_method == "balance" and receipt.amount and receipt.amount > 0:
        sale_result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
        sale = sale_result.scalar_one_or_none()
        if sale and sale.customer:
            company_result = await db.execute(
                select(Company).where(Company.name == sale.customer, Company.type == CompanyType.CUSTOMER)
            )
            company = company_result.scalar_one_or_none()
            if company:
                company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) + receipt.amount

    await db.delete(receipt)
    await db.flush()

    # 重新计算已收金额
    receipt_result = await db.execute(
        select(func.sum(FinishedProductReceipt.amount))
        .where(FinishedProductReceipt.sale_v2_id == sale_id)
    )
    paid_amount = receipt_result.scalar() or Decimal("0")

    sale_result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = sale_result.scalar_one_or_none()
    if sale:
        sale.paid_amount = paid_amount
        net_amount = sale.net_amount or Decimal("0")
        status_net = net_amount + (sale.balance_adjustment or Decimal("0"))
        if paid_amount >= status_net and status_net > 0:
            sale.status = "paid"
            sale.paid = 1
        elif paid_amount > 0:
            sale.status = "partial_paid"
            sale.paid = 1
        else:
            sale.status = "pending"
            sale.paid = 0

    await db.commit()
    return {"success": True}


@router.post("/finished-product-sales/batch-receipts")
async def api_batch_create_finished_sale_receipts(data: dict, db: AsyncSession = Depends(get_db)):
    """合并收款：多个销售单一次性收款（创建多条收款记录，共享一条交易流水）"""
    from app.models.enums import TransactionCategory, TransactionType

    sale_receipts = data.get("sale_receipts", [])
    if not sale_receipts:
        raise HTTPException(status_code=400, detail="未提供收款明细")

    # 校验所有金额 > 0
    for item in sale_receipts:
        amount = Decimal(str(item.get("amount", 0)))
        if amount <= 0:
            raise HTTPException(status_code=400, detail="每笔收款金额必须大于0")

    # 查询所有销售单
    sale_ids = [item["sale_id"] for item in sale_receipts]
    sale_result = await db.execute(
        select(FinishedProductSaleV2).where(FinishedProductSaleV2.id.in_(sale_ids))
    )
    sales = {s.id: s for s in sale_result.scalars().all()}

    for sid in sale_ids:
        if sid not in sales:
            raise HTTPException(status_code=404, detail=f"销售记录 #{sid} 不存在")

    # 校验同一客户（可选但建议）
    customers = list(set(s.customer for s in sales.values() if s.customer))
    if len(customers) > 1:
        raise HTTPException(status_code=400, detail=f"合并收款只能针对同一客户，当前涉及客户: {', '.join(customers)}")

    customer_name = customers[0] if customers else None
    total_amount = sum(Decimal(str(item["amount"])) for item in sale_receipts)

    # 余额抵扣：校验客户总余额
    is_balance_payment = data.get("payment_method") == "balance"
    company = None
    if is_balance_payment and customer_name:
        company_result = await db.execute(
            select(Company).where(
                Company.name == customer_name,
                Company.type == CompanyType.CUSTOMER
            )
        )
        company = company_result.scalar_one_or_none()
        if not company:
            raise HTTPException(status_code=404, detail="客户不存在，无法使用余额抵扣")
        available_balance = Decimal(str(company.prepaid_balance or 0))
        if available_balance < total_amount:
            raise HTTPException(
                status_code=400,
                detail=f"客户预付款余额不足（当前余额 ¥{available_balance}，需扣款 ¥{total_amount}）"
            )

    receipt_date = _parse_date(data.get("receipt_date"))
    payment_method = data.get("payment_method", "bank_transfer")
    bank_account_id = data.get("bank_account_id")
    reference_no = data.get("reference_no")
    notes = data.get("notes")

    # 非余额抵扣：创建一条共享交易流水
    transaction_id = None
    if not is_balance_payment and total_amount > 0:
        user_notes = notes
        desc = "销售合并收款"
        sale_nos = ", ".join([f"#{sid}" for sid in sale_ids[:3]])
        if len(sale_ids) > 3:
            sale_nos += f" 等共{len(sale_ids)}单"
        desc = f"{desc} {sale_nos}"
        if user_notes:
            desc = f"{desc} - {user_notes}"

        transaction = TransactionRecord(
            transaction_date=receipt_date,
            type=TransactionType.INCOME,
            category=TransactionCategory.MAIN_BUSINESS_REVENUE,
            amount=total_amount,
            currency="CNY",
            to_account_id=bank_account_id,
            counterparty_name=customer_name,
            reference_no=reference_no or sale_nos,
            description=desc,
            notes=user_notes,
            is_confirmed=True,
        )
        transaction.related_sale_ids = sale_ids
        db.add(transaction)
        await db.flush()
        transaction_id = transaction.id

    # 为每个销售单创建收款记录 + 处理抹零
    created_receipts = []
    for item in sale_receipts:
        sale_id = item["sale_id"]
        amount = Decimal(str(item["amount"]))
        rounding_adj = Decimal(str(item.get("rounding_adjustment", 0) or 0))
        sale = sales[sale_id]

        # 抹零处理：更新销售单的 rounding 并重算 net_amount
        if rounding_adj > 0:
            sale.rounding = (sale.rounding or Decimal("0")) + rounding_adj
            sale.actual_amount = sale.total_amount - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - (sale.rounding or Decimal("0"))
            sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0"))
            await db.flush()

        # 只创建 amount > 0 的收款记录
        if amount > 0:
            receipt = FinishedProductReceipt(
                sale_v2_id=sale_id,
                receipt_date=receipt_date,
                amount=amount,
                payment_method=payment_method,
                bank_account_id=bank_account_id if not is_balance_payment else None,
                reference_no=reference_no,
                notes=notes,
                transaction_id=transaction_id,
            )
            db.add(receipt)
            created_receipts.append({"sale_id": sale_id, "amount": float(amount), "rounding": float(rounding_adj)})

    # 余额抵扣：扣减客户预付余额（包含抹零）
    total_rounding = sum(Decimal(str(item.get("rounding_adjustment", 0) or 0)) for item in sale_receipts)
    if is_balance_payment and company:
        company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) - total_amount - total_rounding

    await db.flush()

    # 更新每个销售单的已收金额和状态
    for sale_id in sale_ids:
        receipt_result = await db.execute(
            select(func.sum(FinishedProductReceipt.amount))
            .where(FinishedProductReceipt.sale_v2_id == sale_id)
        )
        paid_amount = receipt_result.scalar() or Decimal("0")
        sale = sales[sale_id]
        sale.paid_amount = paid_amount
        net_amount = sale.net_amount or Decimal("0")
        if paid_amount >= net_amount and net_amount > 0:
            sale.status = "paid"
            sale.paid = 1
        elif paid_amount > 0:
            sale.paid = 1
        else:
            sale.paid = 0

    await db.commit()
    return {
        "success": True,
        "data": {
            "total_amount": float(total_amount),
            "sale_count": len(sale_receipts),
            "receipts": created_receipts,
            "transaction_id": transaction_id,
        }
    }


# ==================== 售后记录 ====================

@router.get("/finished-product-sales/{sale_id}/aftersales")
async def api_list_finished_sale_aftersales(sale_id: int, db: AsyncSession = Depends(get_db)):
    """成品销售售后记录列表"""
    result = await db.execute(
        select(FinishedProductAftersales).where(FinishedProductAftersales.sale_id == sale_id)
    )
    records = result.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "sale_id": r.sale_id,
                "record_date": r.record_date.isoformat() if r.record_date else None,
                "type": r.type,
                "amount": float(r.amount) if r.amount else 0,
                "reason": r.reason,
                "status": r.status,
                "notes": r.notes,
            }
            for r in records
        ],
    }


@router.post("/finished-product-sales/{sale_id}/aftersales")
async def api_create_finished_sale_aftersales(sale_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """创建成品销售售后记录（同步更新销售单 after_sales_adjustment 和 net_amount）"""
    sale_result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = sale_result.scalar_one_or_none()
    if not sale:
        raise HTTPException(status_code=404, detail="销售记录不存在")

    record = FinishedProductAftersales(
        sale_id=sale_id,
        record_date=_parse_date(data.get("record_date")),
        type=data.get("type", "refund"),
        amount=Decimal(str(data.get("amount", 0))),
        reason=data.get("reason"),
        status=data.get("status", "pending"),
        notes=data.get("notes"),
    )
    db.add(record)
    await db.flush()

    # 重新汇总售后调整金额
    agg_result = await db.execute(
        select(func.sum(FinishedProductAftersales.amount))
        .where(FinishedProductAftersales.sale_id == sale_id)
    )
    total_aftersales = agg_result.scalar() or Decimal("0")
    sale.after_sales_adjustment = total_aftersales

    # 重算 net_amount
    total = sale.total_amount or Decimal("0")
    sale.actual_amount = total - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - (sale.rounding or Decimal("0"))
    sale.net_amount = sale.actual_amount - total_aftersales - (sale.commission or Decimal("0"))

    await db.commit()
    return {
        "success": True,
        "data": {
            "id": record.id,
            "sale_id": record.sale_id,
            "record_date": record.record_date.isoformat() if record.record_date else None,
            "type": record.type,
            "amount": float(record.amount) if record.amount else 0,
            "reason": record.reason,
            "status": record.status,
            "notes": record.notes,
        },
    }


@router.delete("/finished-product-sales/{sale_id}/aftersales/{record_id}")
async def api_delete_finished_sale_aftersales(sale_id: int, record_id: int, db: AsyncSession = Depends(get_db)):
    """删除成品销售售后记录（同步更新销售单 after_sales_adjustment 和 net_amount）"""
    result = await db.execute(
        select(FinishedProductAftersales)
        .where(FinishedProductAftersales.id == record_id, FinishedProductAftersales.sale_id == sale_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="售后记录不存在")

    await db.delete(record)
    await db.flush()

    # 重新汇总售后调整金额
    agg_result = await db.execute(
        select(func.sum(FinishedProductAftersales.amount))
        .where(FinishedProductAftersales.sale_id == sale_id)
    )
    total_aftersales = agg_result.scalar() or Decimal("0")

    sale_result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = sale_result.scalar_one_or_none()
    if sale:
        sale.after_sales_adjustment = total_aftersales
        total = sale.total_amount or Decimal("0")
        sale.actual_amount = total - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - (sale.rounding or Decimal("0"))
        sale.net_amount = sale.actual_amount - total_aftersales - (sale.commission or Decimal("0"))

    await db.commit()
    return {"success": True}


# ==================== 库存操作记录 ====================

@router.get("/stock-operations")
async def api_get_stock_operations(
    product_name: str,
    batch_no: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    """查询某个产品+批次的所有库存操作记录（出入库、销售出库）"""
    from app.models.finished_product import FinishedProductSaleV2
    from app.models.warehouse import StockMovement

    # 1. 查产品ID（name 不唯一，limit 1）
    product_result = await db.execute(select(Product).where(Product.name == product_name).limit(1))
    product = product_result.scalar_one_or_none()
    if not product:
        return {"success": True, "data": []}

    # 2. 查所有该产品的 stock_movements（按时间倒序）
    movements_result = await db.execute(
        select(StockMovement)
        .where(StockMovement.product_id == product.id)
        .order_by(StockMovement.movement_date.desc(), StockMovement.id.desc())
    )
    movements = movements_result.scalars().all()

    # 3. 查关联单据信息（批量查询，减少数据库往返）
    purchase_nos = []
    sale_nos = []
    for m in movements:
        if m.ref_type == "purchase_order" and m.ref_no:
            purchase_nos.append(m.ref_no)
        elif m.ref_type == "finished_product_sale" and m.ref_no:
            sale_nos.append(m.ref_no)

    # 批量查采购单
    purchase_map = {}
    if purchase_nos:
        purchase_result = await db.execute(
            select(PurchaseOrderV2).where(PurchaseOrderV2.purchase_no.in_(purchase_nos))
        )
        for po in purchase_result.scalars().all():
            purchase_map[po.purchase_no] = po

    # 批量查销售单
    sale_map = {}
    if sale_nos:
        sale_result = await db.execute(
            select(FinishedProductSaleV2).where(FinishedProductSaleV2.sale_no.in_(sale_nos))
        )
        for s in sale_result.scalars().all():
            sale_map[s.sale_no] = s

    # 4. 拼接操作记录
    data = []
    for m in movements:
        record = {
            "id": m.id,
            "operation_time": m.movement_date.isoformat() if m.movement_date else None,
            "doc_no": m.ref_no or "",
            "business_type": "采购入库" if m.ref_type == "purchase_order" else ("成品销售" if m.ref_type == "finished_product_sale" else m.ref_type),
            "qty_change": float(m.qty_change) if m.qty_change else 0,
            "unit": m.unit or "kg",
            "notes": m.notes or "",
            "operator": "-",
            "supplier_customer": "",
            "qty_before": float(m.qty_before) if m.qty_before else 0,
            "qty_after": float(m.qty_after) if m.qty_after else 0,
        }

        if m.ref_type == "purchase_order" and m.ref_no in purchase_map:
            po = purchase_map[m.ref_no]
            record["supplier_customer"] = po.supplier_name or ""
            if not record["notes"] and po.remark:
                record["notes"] = po.remark
        elif m.ref_type == "finished_product_sale" and m.ref_no in sale_map:
            sale = sale_map[m.ref_no]
            record["supplier_customer"] = sale.customer or ""
            if not record["notes"] and sale.remark:
                record["notes"] = sale.remark

        data.append(record)

    return {"success": True, "data": data}
