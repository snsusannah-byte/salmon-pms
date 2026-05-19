"""
国内采购与成品销售模块 API (迁移自 salmon-finance-v4)
使用现有 Company 表作为供应商（type=supplier）
"""
from datetime import date as _date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import (
    Company,
    CompanyType,
    PurchaseOrderV2,
    PurchaseOrderProductV2,
    FinishedProductSaleV2,
    FinishedSaleProductV2,
    Product,
    Warehouse,
    StockInbound,
    StockOutbound,
    StockStatus,
)

router = APIRouter()


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
    # 先按名称查找
    result = await db.execute(select(Product).where(Product.name == name))
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


async def _auto_inbound_from_purchase(db: AsyncSession, order: PurchaseOrderV2) -> list:
    """采购入库后自动推仓库入库记录"""
    # 根据采购类型决定仓库
    warehouse_code = "ZB-DOMESTIC" if order.order_type == "raw_material" else "FL-MATERIAL"
    warehouse_id = await _get_warehouse_id(db, warehouse_code)
    supplier_id = order.supplier_id
    
    inbounds = []
    for product in order.products:
        product_id = await _get_or_create_product(
            db,
            name=product.product_spec,
            spec=product.product_spec,
            unit="kg",
            category="raw_material"
        )
        
        # 生成入库单号
        today = order.purchase_date or _date.today()
        prefix = f"RK{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(func.count()).select_from(
                select(StockInbound).where(StockInbound.inbound_no.like(f"{prefix}-%")).subquery()
            )
        )
        count = result.scalar() or 0
        inbound_no = f"{prefix}-{count + len(inbounds) + 1:03d}"
        
        inbound = StockInbound(
            inbound_no=inbound_no,
            source_type="purchase_order",
            source_id=order.id,
            source_no=order.purchase_no,
            warehouse_id=warehouse_id,
            product_id=product_id,
            qty=Decimal(str(product.weight_kg or 0)),
            unit="kg",
            unit_cost=Decimal(str(product.unit_price or 0)),
            total_cost=Decimal(str(product.total_amount or 0)),
            supplier_id=supplier_id,
            detail={"box_count": product.box_count, "spec": product.product_spec},
            inbound_date=order.purchase_date or _date.today(),
            status=StockStatus.COMPLETED,  # 直接完成
            notes=f"采购入库单 {order.purchase_no} 自动入库",
        )
        db.add(inbound)
        inbounds.append(inbound_no)
    
    return inbounds


async def _auto_outbound_from_sale(db: AsyncSession, sale: FinishedProductSaleV2) -> list:
    """销售后自动推仓库出库记录"""
    # 整鱼出 ZB-DOMESTIC，成品出 FB-FISH
    warehouse_code = "ZB-DOMESTIC" if sale.sale_type == "whole_fish" else "FB-FISH"
    warehouse_id = await _get_warehouse_id(db, warehouse_code)
    
    outbounds = []
    for product in sale.products:
        # 查找产品
        result = await db.execute(select(Product).where(Product.name == product.product_spec))
        p = result.scalar_one_or_none()
        if not p:
            # 找不到产品，跳过
            continue
        
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
            qty=Decimal(str(product.weight_kg or 0)),
            unit="kg",
            unit_cost=Decimal(str(product.unit_price or 0)),
            total_cost=Decimal(str(product.total_amount or 0)),
            outbound_date=today,
            status=StockStatus.COMPLETED,  # 直接完成
            notes=f"销售单 {sale.sale_no} 自动出库",
        )
        db.add(outbound)
        outbounds.append(outbound_no)
    
    return outbounds


# ==================== 产品列表（级联：名称 → 规格）====================

@router.get("/products-by-name")
async def api_get_products_by_name(category: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """获取产品列表，按名称分组返回规格选项"""
    query = select(Product).where(Product.is_active == True)
    if category:
        query = query.where(Product.category == category)
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
    db: AsyncSession = Depends(get_db)
):
    """获取所有客户（简化版）"""
    from app.models import CompanyType
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
            {"id": c.id, "name": c.name, "code": c.code, "contact_person": c.contact_person, "phone": c.phone}
            for c in customers
        ]
    }


# ==================== 供应商列表（简化 API）====================

@router.get("/suppliers")
async def api_get_suppliers(
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """获取所有供应商（Company.type = supplier）"""
    from app.models import CompanyType
    result = await db.execute(
        select(Company)
        .where(Company.type == CompanyType.SUPPLIER)
        .order_by(Company.name)
        .limit(limit)
    )
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
            }
            for s in suppliers
        ]
    }


# ==================== 采购入库管理 ====================

@router.get("/purchase-orders")
async def api_get_purchase_orders(db: AsyncSession = Depends(get_db)):
    """获取所有采购入库单"""
    result = await db.execute(select(PurchaseOrderV2).order_by(PurchaseOrderV2.created_at.desc()))
    orders = result.scalars().all()
    data = []
    for o in orders:
        data.append({
            "id": o.id,
            "purchase_no": o.purchase_no,
            "purchase_date": o.purchase_date.isoformat() if o.purchase_date else None,
            "supplier_id": o.supplier_id,
            "supplier_name": o.supplier_name,
            "order_type": o.order_type,
            "total_amount": float(o.total_amount) if o.total_amount else 0,
            "total_weight": float(o.total_weight) if o.total_weight else 0,
            "total_boxes": o.total_boxes,
            "remark": o.remark,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
    return {"success": True, "data": data}


@router.get("/purchase-orders/{order_id}")
async def api_get_purchase_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """获取采购入库单详情"""
    result = await db.execute(select(PurchaseOrderV2).where(PurchaseOrderV2.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="采购入库单不存在")
    
    products_result = await db.execute(
        select(PurchaseOrderProductV2).where(PurchaseOrderProductV2.purchase_order_id == order_id)
    )
    products = products_result.scalars().all()
    
    return {
        "success": True,
        "data": {
            "id": order.id,
            "purchase_no": order.purchase_no,
            "purchase_date": order.purchase_date.isoformat() if order.purchase_date else None,
            "supplier_id": order.supplier_id,
            "supplier_name": order.supplier_name,
            "order_type": order.order_type,
            "total_amount": float(order.total_amount) if order.total_amount else 0,
            "total_weight": float(order.total_weight) if order.total_weight else 0,
            "total_boxes": order.total_boxes,
            "remark": order.remark,
            "status": order.status,
            "products": [
                {
                    "id": p.id,
                    "product_name": p.product_name,
                    "product_spec": p.product_spec,
                    "factory": p.factory,
                    "box_count": p.box_count,
                    "weight_kg": float(p.weight_kg) if p.weight_kg else 0,
                    "unit_price": float(p.unit_price) if p.unit_price else 0,
                    "total_amount": float(p.total_amount) if p.total_amount else 0,
                }
                for p in products
            ],
        }
    }


@router.post("/purchase-orders")
async def api_create_purchase_order(data: dict, db: AsyncSession = Depends(get_db)):
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
            except:
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
        remark=data.get("remark"),
        status=data.get("status", "completed"),
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
            unit_price=Decimal(str(p.get("unit_price", 0))),
            total_amount=Decimal(str(p.get("total_amount", 0))),
        )
        db.add(product)
    
    await db.commit()
    await db.refresh(order)
    
    # 自动推仓库入库
    try:
        inbounds = await _auto_inbound_from_purchase(db, order)
    except Exception as e:
        print(f"[WARN] 自动入库失败: {e}")
        inbounds = []
    
    return {"success": True, "data": {"id": order.id, "purchase_no": purchase_no, "inbounds": inbounds}}


@router.put("/purchase-orders/{order_id}")
async def api_update_purchase_order(order_id: int, data: dict, db: AsyncSession = Depends(get_db)):
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
    order.remark = data.get("remark", order.remark)
    order.status = data.get("status", order.status)
    
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
            product_spec=p.get("product_spec", ""),
            box_count=p.get("box_count", 0),
            weight_kg=Decimal(str(p.get("weight_kg", 0))),
            unit_price=Decimal(str(p.get("unit_price", 0))),
            total_amount=Decimal(str(p.get("total_amount", 0))),
        )
        db.add(product)
    
    await db.commit()
    return {"success": True}


@router.delete("/purchase-orders/{order_id}")
async def api_delete_purchase_order(order_id: int, db: AsyncSession = Depends(get_db)):
    """删除采购入库单"""
    result = await db.execute(select(PurchaseOrderV2).where(PurchaseOrderV2.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="采购入库单不存在")
    await db.delete(order)
    await db.commit()
    return {"success": True}


# ==================== 成品销售管理 ====================

@router.get("/finished-product-sales")
async def api_get_finished_sales(db: AsyncSession = Depends(get_db)):
    """获取所有成品销售记录"""
    result = await db.execute(select(FinishedProductSaleV2).order_by(FinishedProductSaleV2.created_at.desc()))
    sales = result.scalars().all()
    data = []
    for s in sales:
        data.append({
            "id": s.id,
            "sale_no": s.sale_no,
            "sale_type": s.sale_type,
            "source_id": s.source_id,
            "source_no": s.source_no,
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
            "rounding": float(s.rounding) if s.rounding else 0,
            "after_sales_adjustment": float(s.after_sales_adjustment) if s.after_sales_adjustment else 0,
            "commission": float(s.commission) if s.commission else 0,
            "actual_amount": float(s.actual_amount) if s.actual_amount else 0,
            "net_amount": float(s.net_amount) if s.net_amount else 0,
            "paid": s.paid,
            "remark": s.remark,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })
    return {"success": True, "data": data}


@router.get("/finished-product-sales/{sale_id}")
async def api_get_finished_sale(sale_id: int, db: AsyncSession = Depends(get_db)):
    """获取成品销售记录详情"""
    result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = result.scalar_one_or_none()
    if not sale:
        raise HTTPException(status_code=404, detail="销售记录不存在")
    
    products_result = await db.execute(
        select(FinishedSaleProductV2).where(FinishedSaleProductV2.sale_id == sale_id)
    )
    products = products_result.scalars().all()
    
    return {
        "success": True,
        "data": {
            "id": sale.id,
            "sale_no": sale.sale_no,
            "sale_type": sale.sale_type,
            "source_id": sale.source_id,
            "source_no": sale.source_no,
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
            "rounding": float(sale.rounding) if sale.rounding else 0,
            "after_sales_adjustment": float(sale.after_sales_adjustment) if sale.after_sales_adjustment else 0,
            "commission": float(sale.commission) if sale.commission else 0,
            "actual_amount": float(sale.actual_amount) if sale.actual_amount else 0,
            "net_amount": float(sale.net_amount) if sale.net_amount else 0,
            "paid": sale.paid,
            "remark": sale.remark,
            "products": [
                {
                    "id": p.id,
                    "product_spec": p.product_spec,
                    "box_count": p.box_count,
                    "weight_kg": float(p.weight_kg) if p.weight_kg else 0,
                    "unit_price": float(p.unit_price) if p.unit_price else 0,
                    "total_amount": float(p.total_amount) if p.total_amount else 0,
                    "commission_rate": float(p.commission_rate) if p.commission_rate else 0,
                    "commission_amount": float(p.commission_amount) if p.commission_amount else 0,
                    "after_sales_adjustment": float(p.after_sales_adjustment) if p.after_sales_adjustment else 0,
                }
                for p in products
            ],
        }
    }


@router.post("/finished-product-sales")
async def api_create_finished_sale(data: dict, db: AsyncSession = Depends(get_db)):
    """创建成品销售记录，单号自动生成"""
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
            except:
                pass
        sale_no = f"{prefix}{date_str}-{str(max_seq + 1).zfill(3)}"
    
    sale = FinishedProductSaleV2(
        sale_no=sale_no,
        sale_type=data.get("sale_type", "whole_fish"),
        source_id=data.get("source_id"),
        source_no=data.get("source_no"),
        customer=data.get("customer"),
        salesperson=data.get("salesperson"),
        product_name=data.get("product_name"),
        quantity=Decimal(str(data.get("quantity", 0))) if data.get("quantity") else None,
        weight=Decimal(str(data.get("weight", 0))) if data.get("weight") else None,
        unit_price=Decimal(str(data.get("unit_price", 0))) if data.get("unit_price") else None,
        total_amount=Decimal(str(data.get("total_amount", 0))) if data.get("total_amount") else None,
        sale_date=_parse_date(data.get("sale_date")),
        discount=Decimal(str(data.get("discount", 0))),
        scan_fee=Decimal(str(data.get("scan_fee", 0))),
        rounding=Decimal(str(data.get("rounding", 0))),
        after_sales_adjustment=Decimal(str(data.get("after_sales_adjustment", 0))),
        commission=Decimal(str(data.get("commission", 0))),
        actual_amount=Decimal(str(data.get("actual_amount", 0))),
        net_amount=Decimal(str(data.get("net_amount", 0))) if data.get("net_amount") else None,
        paid=1 if data.get("paid") else 0,
        remark=data.get("remark"),
    )
    db.add(sale)
    await db.flush()
    
    for p in data.get("products", []):
        product = FinishedSaleProductV2(
            sale_id=sale.id,
            product_spec=p.get("product_spec", ""),
            box_count=p.get("box_count", 0),
            weight_kg=Decimal(str(p.get("weight_kg", 0))),
            unit_price=Decimal(str(p.get("unit_price", 0))),
            total_amount=Decimal(str(p.get("total_amount", 0))),
            commission_rate=Decimal(str(p.get("commission_rate", 0))),
            commission_amount=Decimal(str(p.get("commission_amount", 0))),
            after_sales_adjustment=Decimal(str(p.get("after_sales_adjustment", 0))),
        )
        db.add(product)
    
    await db.commit()
    await db.refresh(sale)
    
    # 自动推仓库出库
    try:
        outbounds = await _auto_outbound_from_sale(db, sale)
    except Exception as e:
        print(f"[WARN] 自动出库失败: {e}")
        outbounds = []
    
    return {"success": True, "data": {"id": sale.id, "sale_no": sale_no, "outbounds": outbounds}}


@router.put("/finished-product-sales/{sale_id}")
async def api_update_finished_sale(sale_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    """更新成品销售记录"""
    result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = result.scalar_one_or_none()
    if not sale:
        raise HTTPException(status_code=404, detail="销售记录不存在")
    
    for field in ["sale_no", "sale_type", "source_id", "source_no", "customer", "salesperson",
                  "product_name", "remark"]:
        if field in data:
            setattr(sale, field, data[field])
    
    if "sale_date" in data:
        sale.sale_date = _parse_date(data["sale_date"])
    
    for field in ["quantity", "weight", "unit_price", "total_amount", "discount", "scan_fee",
                  "rounding", "after_sales_adjustment", "commission", "actual_amount", "net_amount"]:
        if field in data:
            val = data[field]
            setattr(sale, field, Decimal(str(val)) if val is not None else None)
    
    if "paid" in data:
        sale.paid = 1 if data["paid"] else 0
    
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
            product_spec=p.get("product_spec", ""),
            box_count=p.get("box_count", 0),
            weight_kg=Decimal(str(p.get("weight_kg", 0))),
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
async def api_delete_finished_sale(sale_id: int, db: AsyncSession = Depends(get_db)):
    """删除成品销售记录"""
    result = await db.execute(select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id))
    sale = result.scalar_one_or_none()
    if not sale:
        raise HTTPException(status_code=404, detail="销售记录不存在")
    await db.delete(sale)
    await db.commit()
    return {"success": True}
