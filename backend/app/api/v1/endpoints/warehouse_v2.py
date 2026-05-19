"""
仓库模块V2 API
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.warehouse_v2 import (
    WarehouseCreate,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseUpdate,
    StockInboundCreate,
    StockInboundListResponse,
    StockInboundResponse,
    StockListResponse,
    StockOutboundCreate,
    StockOutboundListResponse,
    StockOutboundResponse,
    StockSummaryResponse,
    StockTransferCreate,
    StockTransferListResponse,
    StockTransferResponse,
    StockMovementListResponse,
)
from app.services.warehouse_v2_service import WarehouseV2Service
from app.models import Product, ImportInvoice, WholeFishSale
from sqlalchemy import select

router = APIRouter()


# ==================== 业务集成 ====================

@router.post("/inbounds/from-invoice", response_model=dict)
async def create_inbound_from_invoice(
    invoice_id: int,
    product_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """根据进口发票创建入库单（自动入库到 ZB-IMPORT）"""
    invoice = await db.get(ImportInvoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="发票不存在")
    
    # 如果未指定 product_id，尝试查找
    if not product_id and invoice.products:
        ip = invoice.products[0] if invoice.products else None
        if ip:
            product_id = ip.product_id
    
    if not product_id:
        raise HTTPException(status_code=400, detail="无法确定产品ID")
    
    try:
        inbound = await WarehouseV2Service.auto_inbound_from_invoice(
            db=db,
            invoice_id=invoice.id,
            invoice_no=invoice.invoice_no,
            product_id=product_id,
            qty=Decimal(str(invoice.total_boxes)),
            unit="box",
            unit_cost=Decimal(str(invoice.actual_cost_cny or invoice.estimated_cost_cny or 0)) / Decimal(str(invoice.total_boxes or 1)),
            detail={
                "total_boxes": invoice.total_boxes,
                "total_weight_kg": str(invoice.total_weight_kg),
                "invoice_date": str(invoice.invoice_date),
            },
        )
        return {"message": "入库成功", "inbound_no": inbound.inbound_no}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/outbounds/from-sale", response_model=dict)
async def create_outbound_from_sale(
    sale_id: int,
    warehouse_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """根据整鱼销售单创建出库单"""
    sale = await db.get(WholeFishSale, sale_id)
    if not sale:
        raise HTTPException(status_code=404, detail="销售单不存在")
    
    # 如果未指定仓库，默认使用进口整包仓
    if not warehouse_id:
        wh = await WarehouseV2Service.get_warehouse_by_code(db, "ZB-IMPORT")
        if wh:
            warehouse_id = wh.id
    
    if not warehouse_id:
        raise HTTPException(status_code=400, detail="无法确定仓库")
    
    # 根据 spec 查找 product
    product = None
    if sale.spec:
        result = await db.execute(select(Product).where(Product.spec == sale.spec).limit(1))
        product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=400, detail=f"找不到规格 '{sale.spec}' 对应的产品")
    
    try:
        outbound = await WarehouseV2Service.auto_outbound_from_sale(
            db=db,
            sale_id=sale.id,
            sale_no=sale.sale_no,
            warehouse_id=warehouse_id,
            product_id=product.id,
            qty=Decimal(str(sale.weight_kg)),
            unit="kg",
        )
        return {"message": "出库成功", "outbound_no": outbound.outbound_no}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 仓库管理 ====================

@router.get("/warehouses", response_model=WarehouseListResponse)
async def list_warehouses(
    type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await WarehouseV2Service.list_warehouses(db, type=type, is_active=is_active, skip=skip, limit=limit)
    return WarehouseListResponse(
        total=total,
        items=[WarehouseResponse.model_validate(i) for i in items],
        skip=skip,
        limit=limit,
    )


@router.post("/warehouses", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    data: WarehouseCreate,
    db: AsyncSession = Depends(get_db),
):
    wh = await WarehouseV2Service.create_warehouse(db, data.model_dump())
    return WarehouseResponse.model_validate(wh)


@router.get("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
async def get_warehouse(
    warehouse_id: int,
    db: AsyncSession = Depends(get_db),
):
    wh = await WarehouseV2Service.get_warehouse(db, warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="仓库不存在")
    return WarehouseResponse.model_validate(wh)


@router.put("/warehouses/{warehouse_id}", response_model=WarehouseResponse)
async def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    db: AsyncSession = Depends(get_db),
):
    wh = await WarehouseV2Service.get_warehouse(db, warehouse_id)
    if not wh:
        raise HTTPException(status_code=404, detail="仓库不存在")
    wh = await WarehouseV2Service.update_warehouse(db, wh, data.model_dump(exclude_unset=True))
    return WarehouseResponse.model_validate(wh)


# ==================== 库存查询 ====================

@router.get("/stocks", response_model=StockListResponse)
async def list_stocks(
    warehouse_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    batch_id: Optional[int] = Query(None),
    is_below_warning: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await WarehouseV2Service.list_stocks(
        db, warehouse_id=warehouse_id, product_id=product_id, batch_id=batch_id,
        is_below_warning=is_below_warning, skip=skip, limit=limit,
    )
    return StockListResponse(total=total, items=items, skip=skip, limit=limit)


@router.get("/stocks/summary", response_model=StockSummaryResponse)
async def stock_summary(
    db: AsyncSession = Depends(get_db),
):
    items = await WarehouseV2Service.stock_summary(db)
    return StockSummaryResponse(items=items)


# ==================== 入库管理 ====================

@router.post("/inbounds", response_model=StockInboundResponse, status_code=status.HTTP_201_CREATED)
async def create_inbound(
    data: StockInboundCreate,
    db: AsyncSession = Depends(get_db),
):
    inbound = await WarehouseV2Service.create_inbound(db, data.model_dump())
    return StockInboundResponse.model_validate(inbound)


@router.get("/inbounds", response_model=StockInboundListResponse)
async def list_inbounds(
    warehouse_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await WarehouseV2Service.list_inbounds(
        db, warehouse_id=warehouse_id, product_id=product_id, status=status,
        start_date=start_date, end_date=end_date, skip=skip, limit=limit,
    )
    return StockInboundListResponse(total=total, items=items, skip=skip, limit=limit)


@router.get("/inbounds/{inbound_id}", response_model=StockInboundResponse)
async def get_inbound(
    inbound_id: int,
    db: AsyncSession = Depends(get_db),
):
    inbound = await WarehouseV2Service.get_inbound(db, inbound_id)
    if not inbound:
        raise HTTPException(status_code=404, detail="入库单不存在")
    return StockInboundResponse.model_validate(inbound)


@router.post("/inbounds/{inbound_id}/confirm", response_model=dict)
async def confirm_inbound(
    inbound_id: int,
    db: AsyncSession = Depends(get_db),
):
    inbound = await WarehouseV2Service.get_inbound(db, inbound_id)
    if not inbound:
        raise HTTPException(status_code=404, detail="入库单不存在")
    try:
        stock = await WarehouseV2Service.confirm_inbound(db, inbound)
        return {"message": "入库确认成功", "stock_id": stock.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/inbounds/{inbound_id}/cancel", response_model=dict)
async def cancel_inbound(
    inbound_id: int,
    db: AsyncSession = Depends(get_db),
):
    inbound = await WarehouseV2Service.get_inbound(db, inbound_id)
    if not inbound:
        raise HTTPException(status_code=404, detail="入库单不存在")
    inbound.status = "cancelled"
    await db.commit()
    return {"message": "入库单已取消"}


# ==================== 出库管理 ====================

@router.post("/outbounds", response_model=StockOutboundResponse, status_code=status.HTTP_201_CREATED)
async def create_outbound(
    data: StockOutboundCreate,
    db: AsyncSession = Depends(get_db),
):
    outbound = await WarehouseV2Service.create_outbound(db, data.model_dump())
    return StockOutboundResponse.model_validate(outbound)


@router.get("/outbounds", response_model=StockOutboundListResponse)
async def list_outbounds(
    warehouse_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await WarehouseV2Service.list_outbounds(
        db, warehouse_id=warehouse_id, product_id=product_id, status=status,
        start_date=start_date, end_date=end_date, skip=skip, limit=limit,
    )
    return StockOutboundListResponse(total=total, items=items, skip=skip, limit=limit)


@router.get("/outbounds/{outbound_id}", response_model=StockOutboundResponse)
async def get_outbound(
    outbound_id: int,
    db: AsyncSession = Depends(get_db),
):
    outbound = await WarehouseV2Service.get_outbound(db, outbound_id)
    if not outbound:
        raise HTTPException(status_code=404, detail="出库单不存在")
    return StockOutboundResponse.model_validate(outbound)


@router.post("/outbounds/{outbound_id}/confirm", response_model=dict)
async def confirm_outbound(
    outbound_id: int,
    db: AsyncSession = Depends(get_db),
):
    outbound = await WarehouseV2Service.get_outbound(db, outbound_id)
    if not outbound:
        raise HTTPException(status_code=404, detail="出库单不存在")
    try:
        stock = await WarehouseV2Service.confirm_outbound(db, outbound)
        return {"message": "出库确认成功", "stock_id": stock.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/outbounds/{outbound_id}/cancel", response_model=dict)
async def cancel_outbound(
    outbound_id: int,
    db: AsyncSession = Depends(get_db),
):
    outbound = await WarehouseV2Service.get_outbound(db, outbound_id)
    if not outbound:
        raise HTTPException(status_code=404, detail="出库单不存在")
    outbound.status = "cancelled"
    await db.commit()
    return {"message": "出库单已取消"}


# ==================== 调拨管理 ====================

@router.post("/transfers", response_model=StockTransferResponse, status_code=status.HTTP_201_CREATED)
async def create_transfer(
    data: StockTransferCreate,
    db: AsyncSession = Depends(get_db),
):
    transfer = await WarehouseV2Service.create_transfer(db, data.model_dump())
    return StockTransferResponse.model_validate(transfer)


@router.get("/transfers", response_model=StockTransferListResponse)
async def list_transfers(
    from_warehouse_id: Optional[int] = Query(None),
    to_warehouse_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await WarehouseV2Service.list_transfers(
        db, from_warehouse_id=from_warehouse_id, to_warehouse_id=to_warehouse_id,
        product_id=product_id, status=status, skip=skip, limit=limit,
    )
    return StockTransferListResponse(total=total, items=items, skip=skip, limit=limit)


@router.get("/transfers/{transfer_id}", response_model=StockTransferResponse)
async def get_transfer(
    transfer_id: int,
    db: AsyncSession = Depends(get_db),
):
    transfer = await WarehouseV2Service.get_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="调拨单不存在")
    return StockTransferResponse.model_validate(transfer)


@router.post("/transfers/{transfer_id}/confirm", response_model=dict)
async def confirm_transfer(
    transfer_id: int,
    db: AsyncSession = Depends(get_db),
):
    transfer = await WarehouseV2Service.get_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="调拨单不存在")
    try:
        from_stock, to_stock = await WarehouseV2Service.confirm_transfer(db, transfer)
        return {
            "message": "调拨确认成功",
            "from_stock_id": from_stock.id,
            "to_stock_id": to_stock.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfers/{transfer_id}/cancel", response_model=dict)
async def cancel_transfer(
    transfer_id: int,
    db: AsyncSession = Depends(get_db),
):
    transfer = await WarehouseV2Service.get_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="调拨单不存在")
    transfer.status = "cancelled"
    await db.commit()
    return {"message": "调拨单已取消"}


# ==================== 库存变动查询 ====================

@router.get("/movements", response_model=StockMovementListResponse)
async def list_movements(
    warehouse_id: Optional[int] = Query(None),
    product_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    items, total = await WarehouseV2Service.list_movements(
        db, warehouse_id=warehouse_id, product_id=product_id, movement_type=movement_type,
        start_date=start_date, end_date=end_date, skip=skip, limit=limit,
    )
    return StockMovementListResponse(total=total, items=items, skip=skip, limit=limit)
