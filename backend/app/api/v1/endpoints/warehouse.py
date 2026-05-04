"""
成品仓库管理 API
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.finished_product_v2 import (
    WarehousePurchaseOrderCreate,
    WarehousePurchaseOrderUpdate,
    WarehousePurchaseOrderResponse,
    WarehousePurchaseOrderListResponse,
    WarehouseStockResponse,
    WarehouseStockListResponse,
    WarehouseStockWarningResponse,
    WarehouseStockWarningListResponse,
    StockInRequest,
    StockOutRequest,
)
from app.services.warehouse_service import WarehouseService

router = APIRouter()


# ==================== 采购入库 ====================

@router.post("/purchase-orders", response_model=WarehousePurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    data: WarehousePurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建采购入库单
    
    支持：整鱼、鱼柳、包装物料、配套产品的采购入库
    自动更新库存和计算加权平均成本
    """
    order = await WarehouseService.create_purchase_order(db, data.model_dump())
    return WarehousePurchaseOrderResponse.model_validate(order)


@router.get("/purchase-orders", response_model=WarehousePurchaseOrderListResponse)
async def list_purchase_orders(
    product_id: Optional[int] = Query(None),
    supplier_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """采购入库列表"""
    items, total = await WarehouseService.list_purchase_orders(
        db=db,
        product_id=product_id,
        supplier_id=supplier_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return WarehousePurchaseOrderListResponse(
        total=total,
        items=[WarehousePurchaseOrderResponse.model_validate(i) for i in items],
        skip=skip,
        limit=limit,
    )


@router.get("/purchase-orders/{order_id}", response_model=WarehousePurchaseOrderResponse)
async def get_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """采购入库详情"""
    order = await WarehouseService.get_purchase_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="采购入库单不存在")
    return WarehousePurchaseOrderResponse.model_validate(order)


@router.delete("/purchase-orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除采购入库单（同时回滚库存）"""
    from app.models.finished_product_v2 import WarehousePurchaseOrder
    from sqlalchemy import select
    
    result = await db.execute(select(WarehousePurchaseOrder).where(WarehousePurchaseOrder.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="采购入库单不存在")
    
    await WarehouseService.delete_purchase_order(db, order)
    return None


# ==================== 库存查询 ====================

@router.get("/stocks", response_model=WarehouseStockListResponse)
async def list_stocks(
    category: Optional[str] = Query(None, description="产品分类: whole_fish/finished_product/byproduct/bom_material"),
    is_below_warning: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """成品仓库库存列表"""
    items, total = await WarehouseService.list_stocks(
        db=db,
        category=category,
        is_below_warning=is_below_warning,
        skip=skip,
        limit=limit,
    )
    return WarehouseStockListResponse(
        total=total,
        items=[WarehouseStockResponse.model_validate(i) for i in items],
    )


@router.get("/stocks/warnings", response_model=WarehouseStockWarningListResponse)
async def get_stock_warnings(
    db: AsyncSession = Depends(get_db),
):
    """库存预警列表
    
    预警线 = 供货周期(天) × 日均消耗 + 安全缓冲(件)
    副产品不做预警
    """
    items = await WarehouseService.get_warning_list(db)
    return WarehouseStockWarningListResponse(
        total=len(items),
        items=[WarehouseStockWarningResponse.model_validate(i) for i in items],
    )


@router.post("/stocks/in", response_model=WarehouseStockResponse)
async def stock_in(
    data: StockInRequest,
    db: AsyncSession = Depends(get_db),
):
    """直接入库（无采购单）"""
    stock = await WarehouseService.stock_in(
        db,
        product_id=data.product_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
    )
    # 构建响应
    return {
        "id": stock.id,
        "product_id": stock.product_id,
        "current_quantity": stock.current_quantity,
        "available_quantity": stock.available_quantity,
        "unit_cost": stock.unit_cost,
    }


@router.post("/stocks/out", response_model=WarehouseStockResponse)
async def stock_out(
    data: StockOutRequest,
    db: AsyncSession = Depends(get_db),
):
    """直接出库"""
    try:
        stock = await WarehouseService.stock_out(
            db,
            product_id=data.product_id,
            quantity=data.quantity,
            reason=data.reason or "manual",
        )
        return {
            "id": stock.id,
            "product_id": stock.product_id,
            "current_quantity": stock.current_quantity,
            "available_quantity": stock.available_quantity,
            "unit_cost": stock.unit_cost,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
