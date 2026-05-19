"""
采购入库模块 API
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.purchase_order_service import PurchaseOrderService

router = APIRouter()


# ==================== 采购单管理 ====================

@router.post("/purchase-orders", status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """创建采购单"""
    order = await PurchaseOrderService.create_order(db, data)
    return {"id": order.id, "order_no": order.order_no, "message": "采购单创建成功"}


@router.get("/purchase-orders")
async def list_purchase_orders(
    status: Optional[str] = Query(None),
    supplier_id: Optional[int] = Query(None),
    main_product_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """采购单列表"""
    items, total = await PurchaseOrderService.list_orders(
        db, status=status, supplier_id=supplier_id, main_product_type=main_product_type,
        skip=skip, limit=limit,
    )
    return {"total": total, "items": items, "skip": skip, "limit": limit}


@router.get("/purchase-orders/{order_id}")
async def get_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """采购单详情"""
    order = await PurchaseOrderService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    # TODO: 返回完整详情
    return {"id": order.id, "order_no": order.order_no}


@router.put("/purchase-orders/{order_id}")
async def update_purchase_order(
    order_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """修改采购单（仅待入库状态）"""
    order = await PurchaseOrderService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    try:
        order = await PurchaseOrderService.update_order(db, order, data)
        return {"message": "修改成功", "id": order.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/purchase-orders/{order_id}/cancel")
async def cancel_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """取消采购单"""
    order = await PurchaseOrderService.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购单不存在")
    try:
        order = await PurchaseOrderService.cancel_order(db, order)
        return {"message": "已取消", "id": order.id, "status": order.status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 入库确认 ====================

@router.post("/purchase-orders/{order_id}/inbound", status_code=status.HTTP_200_OK)
async def confirm_purchase_inbound(
    order_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """采购单入库确认"""
    inbound_items = data.get("items", [])
    try:
        result = await PurchaseOrderService.confirm_inbound(db, order_id, inbound_items)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 统计 ====================

@router.get("/purchase-orders/summary")
async def purchase_order_summary(
    db: AsyncSession = Depends(get_db),
):
    """采购统计"""
    return await PurchaseOrderService.get_summary(db)
