"""
物料采购与批次管理 API
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Company
from app.schemas.material_purchase import (
    MaterialCreate,
    MaterialListItem,
    MaterialPurchaseOrderCreate,
    MaterialPurchaseOrderList,
    MaterialPurchaseOrderResponse,
    MaterialPurchaseItemResponse,
    MaterialInboundRequest,
    MaterialOutboundRequest,
    MaterialStockResponse,
    MaterialUpdate,
)
from app.services.material_purchase_service import MaterialPurchaseService

router = APIRouter()


# ==================== 物料管理 ====================

@router.get("/materials", response_model=List[MaterialListItem])
async def list_materials(
    category_id: Optional[int] = Query(None),
    keyword: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """物料列表（含库存汇总）"""
    items = await MaterialPurchaseService.list_materials_with_stock(
        db, category_id=category_id, keyword=keyword
    )
    return items


@router.post("/materials", status_code=status.HTTP_201_CREATED)
async def create_material(
    data: MaterialCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建物料"""
    from app.models import Product
    product = Product(
        code=data.code,
        name=data.name,
        spec=data.spec,
        unit=data.unit,
        category="bom_material",
        material_category_id=data.material_category_id,
        items_per_box=data.items_per_box,
        cost_price=data.cost_price,
        is_active=True,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return {"id": product.id, "message": "物料创建成功"}


@router.get("/materials/{material_id}")
async def get_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
):
    """物料详情（含库存和批次）"""
    stock = await MaterialPurchaseService.get_stock(db, material_id)
    return stock


@router.put("/materials/{material_id}")
async def update_material(
    material_id: int,
    data: MaterialUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新物料"""
    from app.models import Product
    from sqlalchemy import select
    result = await db.execute(select(Product).where(Product.id == material_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="物料不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    await db.commit()
    await db.refresh(product)
    return {"id": product.id, "message": "物料更新成功"}


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除物料（检查无活跃批次）"""
    from app.models import Product, MaterialBatch
    from sqlalchemy import select, and_
    result = await db.execute(select(Product).where(Product.id == material_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="物料不存在")

    batch_result = await db.execute(
        select(MaterialBatch).where(
            and_(
                MaterialBatch.product_id == material_id,
                MaterialBatch.status == "active",
                MaterialBatch.remaining_qty > 0,
            )
        )
    )
    if batch_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="物料有活跃库存，无法删除")

    await db.delete(product)
    await db.commit()


# ==================== 采购单管理 ====================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_material_purchase_order(
    data: MaterialPurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建物料采购单"""
    try:
        order = await MaterialPurchaseService.create_order(db, data.model_dump())
        return {"id": order.id, "order_no": order.order_no, "message": "采购单创建成功"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=List[MaterialPurchaseOrderList])
async def list_material_purchase_orders(
    supplier_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """物料采购单列表"""
    items, total = await MaterialPurchaseService.list_orders(
        db,
        supplier_id=supplier_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return items


@router.get("/{order_id}")
async def get_material_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """采购单详情"""
    from app.models import MaterialPurchaseOrder, MaterialPurchaseItem, Product, Company, Warehouse
    from sqlalchemy import select
    result = await db.execute(
        select(MaterialPurchaseOrder).where(MaterialPurchaseOrder.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")

    # 查询明细
    items_result = await db.execute(
        select(MaterialPurchaseItem, Product)
        .join(Product, MaterialPurchaseItem.product_id == Product.id)
        .where(MaterialPurchaseItem.purchase_order_id == order_id)
    )
    items = []
    for item, product in items_result.all():
        items.append({
            "id": item.id,
            "product_id": item.product_id,
            "product_name": product.name,
            "product_code": product.code,
            "box_count": item.box_count,
            "items_per_box": item.items_per_box,
            "total_qty": item.total_qty,
            "unit": item.unit,
            "quoted_unit_price": item.quoted_unit_price,
            "quoted_amount": item.quoted_amount,
            "actual_amount": item.actual_amount,
            "actual_unit_price": item.actual_unit_price,
            "received_qty": item.received_qty,
            "is_fully_received": item.is_fully_received,
            "notes": item.notes,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })

    supplier_result = await db.execute(select(Company).where(Company.id == order.supplier_id))
    supplier = supplier_result.scalar_one_or_none()

    warehouse_name = None
    if order.warehouse_id:
        wh_result = await db.execute(select(Warehouse).where(Warehouse.id == order.warehouse_id))
        wh = wh_result.scalar_one_or_none()
        warehouse_name = wh.name if wh else None

    return {
        "id": order.id,
        "order_no": order.order_no,
        "order_date": order.order_date,
        "supplier_id": order.supplier_id,
        "supplier_name": supplier.name if supplier else "",
        "quoted_total": order.quoted_total,
        "actual_total": order.actual_total,
        "paid_amount": order.paid_amount,
        "status": order.status,
        "payment_status": order.payment_status,
        "warehouse_id": order.warehouse_id,
        "warehouse_name": warehouse_name,
        "notes": order.notes,
        "items": items,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
    }


@router.post("/{order_id}/cancel")
async def cancel_material_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """取消采购单"""
    order = await MaterialPurchaseService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    try:
        order = await MaterialPurchaseService.cancel_order(db, order)
        return {"id": order.id, "status": order.status, "message": "已取消"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除采购单（仅待入库状态）"""
    order = await MaterialPurchaseService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail="只有待入库状态的采购单可以删除")
    try:
        await MaterialPurchaseService.delete_order(db, order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 批量删除 ====================

@router.post("/batch-delete")
async def batch_delete_material_purchase_orders(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """批量删除采购单（仅待入库状态）"""
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="未提供删除ID列表")
    
    deleted = 0
    failed = []
    for order_id in ids:
        order = await MaterialPurchaseService.get_order(db, order_id)
        if not order:
            failed.append({"id": order_id, "reason": "采购单不存在"})
            continue
        if order.status != "pending":
            failed.append({"id": order_id, "reason": "只有待入库状态可删除"})
            continue
        try:
            await db.delete(order)
            deleted += 1
        except Exception as e:
            failed.append({"id": order_id, "reason": str(e)})
    
    await db.commit()
    return {"success": True, "deleted": deleted, "failed": failed}


# ==================== 收款 ====================

@router.post("/{order_id}/payment")
async def material_purchase_payment(
    order_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """采购单收款 — 同时创建交易流水，更新供应商期末欠款"""
    order = await MaterialPurchaseService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    
    amount = Decimal(str(data.get("amount", 0)))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="收款金额必须大于0")
    
    order.paid_amount = (order.paid_amount or Decimal("0")) + amount
    
    # 更新付款状态
    if order.paid_amount >= order.actual_total:
        order.payment_status = "paid"
    elif order.paid_amount > 0:
        order.payment_status = "partial"
    else:
        order.payment_status = "unpaid"
    
    # 创建交易流水（支出：包装物及低值易耗品）
    from app.services.finance_service import FinanceService
    from app.models.enums import TransactionType, TransactionCategory
    from datetime import date
    from app.models import Company
    
    # 查询供应商名称
    supplier_result = await db.execute(select(Company).where(Company.id == order.supplier_id))
    supplier = supplier_result.scalar_one_or_none()
    
    transaction = await FinanceService.create_transaction(db, {
        "transaction_date": date.today(),
        "type": TransactionType.EXPENSE,
        "category": TransactionCategory.PACKAGING_CONSUMABLES,
        "amount": amount,
        "counterparty_id": order.supplier_id,
        "counterparty_name": supplier.name if supplier else "",
        "from_account_id": data.get("bank_account_id") if data.get("bank_account_id") else None,
        "reference_no": order.order_no,
        "description": f"辅料采购付款：{order.order_no}",
    })
    
    await db.commit()
    await db.refresh(order)
    return {
        "id": order.id,
        "paid_amount": float(order.paid_amount),
        "payment_status": order.payment_status,
        "transaction_id": transaction.id,
        "message": "收款成功",
    }


# ==================== 入库 ====================

@router.post("/{order_id}/inbound")
async def confirm_material_inbound(
    order_id: int,
    data: List[MaterialInboundRequest],
    db: AsyncSession = Depends(get_db),
):
    """采购单入库确认"""
    try:
        inbound_data = [d.model_dump() for d in data]
        result = await MaterialPurchaseService.confirm_inbound(db, order_id, inbound_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 出库 ====================

@router.post("/outbound")
async def material_outbound(
    data: MaterialOutboundRequest,
    db: AsyncSession = Depends(get_db),
):
    """物料出库"""
    try:
        if data.strategy == "fifo":
            allocations = await MaterialPurchaseService.fifo_outbound(
                db, data.product_id, Decimal(str(data.qty))
            )
        else:
            if not data.batch_id:
                raise HTTPException(status_code=400, detail="指定批次出库需提供 batch_id")
            alloc = await MaterialPurchaseService.specific_batch_outbound(
                db, data.batch_id, Decimal(str(data.qty))
            )
            allocations = [alloc]

        # 确认出库并更新仓库
        from app.models import Product
        from sqlalchemy import select
        prod_result = await db.execute(select(Product).where(Product.id == data.product_id))
        product = prod_result.scalar_one_or_none()
        warehouse_id = 1  # 默认仓库，实际应从库存查询获取

        result = await MaterialPurchaseService.confirm_outbound(
            db, data.product_id, Decimal(str(data.qty)), allocations, warehouse_id, data.reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 库存 ====================

@router.get("/warehouse/material-stocks")
async def get_material_stock(
    product_id: int = Query(...),
    include_batches: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """物料库存（总库存 + 批次明细）"""
    stock = await MaterialPurchaseService.get_stock(db, product_id)
    return stock
