"""
追溯系统 API
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.traceability_service import TraceabilityService

router = APIRouter()


@router.get("/traces")
async def list_traces(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """追溯链列表"""
    items, total = await TraceabilityService.list_traces(
        db, status=status, source_type=source_type, skip=skip, limit=limit,
    )
    return {"total": total, "items": items, "skip": skip, "limit": limit}


@router.get("/traces/summary")
async def trace_summary(
    db: AsyncSession = Depends(get_db),
):
    """追溯统计"""
    return await TraceabilityService.get_trace_summary(db)


@router.get("/traces/by-invoice/{invoice_id}")
async def trace_by_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """按进口发票追溯：这批鱼最终卖给了谁"""
    items = await TraceabilityService.trace_by_invoice(db, invoice_id)
    return {"items": items}


@router.get("/traces/by-batch/{batch_id}")
async def trace_by_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """按批次追溯"""
    items = await TraceabilityService.trace_by_batch(db, batch_id)
    return {"items": items}


@router.get("/traces/by-finished-sale/{sale_id}")
async def trace_by_finished_sale(
    sale_id: int,
    db: AsyncSession = Depends(get_db),
):
    """按成品销售单追溯：这批成品来自哪条进口鱼"""
    item = await TraceabilityService.trace_by_finished_sale(db, sale_id)
    if not item:
        raise HTTPException(status_code=404, detail="未找到追溯记录")
    return item
