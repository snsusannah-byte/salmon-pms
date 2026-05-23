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


# ==================== 国内整包仓明细 ====================

@router.get("/domestic-stocks")
async def list_domestic_stocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """国内整包仓明细列表：按入库批次展示，含宰杀日期、加工厂、规格等"""
    from app.models.warehouse import StockInbound, Warehouse, Stock
    from app.models import Product, StockMovement
    from sqlalchemy import func

    # 查国内整包仓ID
    wh_result = await db.execute(select(Warehouse.id).where(Warehouse.code == "ZB-DOMESTIC"))
    wh_id = wh_result.scalar()
    if not wh_id:
        return {"total": 0, "items": []}

    # 查入库记录 + 关联产品
    inbound_result = await db.execute(
        select(
            StockInbound.id,
            StockInbound.inbound_no,
            StockInbound.source_no,
            StockInbound.qty,
            StockInbound.unit_cost,
            StockInbound.total_cost,
            StockInbound.inbound_date,
            StockInbound.slaughter_date,
            StockInbound.factory,
            StockInbound.original_box_count,
            StockInbound.original_weight,
            StockInbound.remaining_qty,
            StockInbound.remaining_box_count,
            StockInbound.detail,
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.spec.label("product_spec"),
        )
        .join(Product, StockInbound.product_id == Product.id)
        .where(StockInbound.warehouse_id == wh_id)
        .where(StockInbound.source_type == "purchase_order")
        .order_by(StockInbound.inbound_date.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = inbound_result.all()

    # 查总数
    count_result = await db.execute(
        select(func.count()).select_from(
            select(StockInbound).where(StockInbound.warehouse_id == wh_id).where(StockInbound.source_type == "purchase_order").subquery()
        )
    )
    total = count_result.scalar() or 0

    items = []
    for r in rows:
        detail = r.detail or {}
        batch_no = detail.get("batch_no", "")
        # 优先用采购单里的产品名称
        display_product_name = detail.get("product_name") or r.product_name or "-"

        # 查当前库存（从 stocks 表查聚合库存）
        stock_result = await db.execute(
            select(Stock.current_qty, Stock.available_qty)
            .where(Stock.warehouse_id == wh_id)
            .where(Stock.product_id == r.product_id)
        )
        stock_row = stock_result.one_or_none()
        current_qty = float(stock_row.current_qty) if stock_row else 0
        available_qty = float(stock_row.available_qty) if stock_row else 0

        # 计算库存箱数（优先用剩余箱数字段，旧记录 fallback 到原始箱数）
        if r.remaining_box_count is not None:
            stock_box_count = r.remaining_box_count
        else:
            stock_box_count = r.original_box_count or detail.get("box_count", 0)

        # 查当前库存（批次级：用 remaining_qty，旧记录 fallback 到 original_weight）
        if r.remaining_qty is not None:
            current_qty = float(r.remaining_qty)
        else:
            current_qty = float(r.original_weight or r.qty or 0)
        available_qty = current_qty

        # 查该产品的操作记录（包含关联单据信息）
        from app.models.finance import PurchaseOrderV2
        from app.models.finished_product import FinishedProductSaleV2
        
        move_result = await db.execute(
            select(
                StockMovement.id,
                StockMovement.movement_type,
                StockMovement.movement_date,
                StockMovement.qty_change,
                StockMovement.qty_before,
                StockMovement.qty_after,
                StockMovement.unit,
                StockMovement.ref_type,
                StockMovement.ref_no,
                StockMovement.notes,
            )
            .where(StockMovement.warehouse_id == wh_id)
            .where(StockMovement.product_id == r.product_id)
            .order_by(StockMovement.movement_date.desc())
        )
        movements_raw = move_result.all()
        
        movements = []
        for m in movements_raw:
            # 反查关联单据获取供应商/客户
            related_party = "-"
            if m.ref_type == "purchase_order" and m.ref_no:
                po_result = await db.execute(
                    select(PurchaseOrderV2.supplier_name).where(PurchaseOrderV2.purchase_no == m.ref_no)
                )
                related_party = po_result.scalar() or "-"
            elif m.ref_type == "finished_product_sale" and m.ref_no:
                sale_result = await db.execute(
                    select(FinishedProductSaleV2.customer).where(FinishedProductSaleV2.sale_no == m.ref_no)
                )
                related_party = sale_result.scalar() or "-"
            
            # 业务类型中文映射
            business_type_map = {
                "purchase_order": "采购入库",
                "finished_product_sale": "成品销售",
                "sale": "成品销售",
                "transfer": "调拨",
                "adjustment": "库存盘点",
                "StockOutbound": "销售出库",
            }
            
            movements.append({
                "id": m.id,
                "movement_type": m.movement_type,
                "movement_date": m.movement_date.isoformat() if m.movement_date else None,
                "qty_change": float(m.qty_change),
                "qty_before": float(m.qty_before),
                "qty_after": float(m.qty_after),
                "unit": m.unit,
                "ref_type": m.ref_type,
                "ref_no": m.ref_no,
                "notes": m.notes,
                "business_type": business_type_map.get(m.ref_type, m.ref_type),
                "related_party": related_party,
            })

        items.append({
            "id": r.id,
            "inbound_no": r.inbound_no,
            "batch_no": batch_no,
            "product_name": display_product_name,
            "product_spec": r.product_spec or detail.get("spec", ""),
            "slaughter_date": r.slaughter_date.isoformat() if r.slaughter_date else None,
            "factory": r.factory,
            "box_count": stock_box_count,
            "current_weight": current_qty,
            "available_weight": available_qty,
            "original_box_count": r.original_box_count or detail.get("box_count", 0),
            "original_weight": float(r.original_weight or r.qty or 0),
            "unit_cost": float(r.unit_cost) if r.unit_cost else 0,
            "total_cost": float(r.total_cost) if r.total_cost else 0,
            "inbound_date": r.inbound_date.isoformat() if r.inbound_date else None,
            "source_no": r.source_no,
            "movement_count": len(movements),
            "movements": movements,
        })

    return {"total": total, "items": items, "skip": skip, "limit": limit}
