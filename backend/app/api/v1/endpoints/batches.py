from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.models import BatchStatus
from app.schemas.batch import (
    BatchCreate,
    BatchUpdate,
    BatchResponse,
    BatchListResponse,
    BatchInvoiceInfo,
    AddInvoiceToBatch,
    BatchSummary,
)
from app.services.batch_service import BatchService
from app.services.invoice_service import InvoiceService

router = APIRouter()


async def _build_batch_response(db: AsyncSession, batch) -> BatchResponse:
    """构建批次响应（含关联发票详情）"""
    from sqlalchemy import select
    from app.models import BatchInvoice, ImportInvoice, Company

    bi_result = await db.execute(
        select(BatchInvoice, ImportInvoice)
        .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
        .where(BatchInvoice.batch_id == batch.id)
        .order_by(BatchInvoice.sort_order)
    )
    invoices_data = bi_result.all()

    invoices = []
    invoice_nos = []
    for bi, inv in invoices_data:
        invoice_nos.append(inv.invoice_no)
        plant_name = None
        exporter_name = None
        if inv.processing_plant_id:
            r = await db.execute(select(Company.name).where(Company.id == inv.processing_plant_id))
            plant_name = r.scalar()
        if inv.exporter_id:
            r = await db.execute(select(Company.name).where(Company.id == inv.exporter_id))
            exporter_name = r.scalar()

        invoices.append(BatchInvoiceInfo(
            invoice_id=inv.id,
            invoice_no=inv.invoice_no,
            invoice_date=inv.invoice_date,
            processing_plant_name=plant_name,
            exporter_name=exporter_name,
            total_amount_usd=inv.total_amount_usd,
            total_boxes=inv.total_boxes,
            total_weight_kg=inv.total_weight_kg,
        ))

    # 计算已售箱数
    from app.models import WholeFishSale
    from sqlalchemy import func as sa_func
    sold_result = await db.execute(
        select(sa_func.coalesce(sa_func.sum(WholeFishSale.box_count), 0))
        .where(WholeFishSale.batch_id == batch.id)
    )
    sold_boxes = sold_result.scalar() or 0
    remaining_boxes = max(0, (batch.total_boxes or 0) - sold_boxes)

    return BatchResponse(
        id=batch.id,
        batch_code=batch.batch_code,
        batch_name=batch.batch_name,
        invoice_nos="&".join(invoice_nos),
        batch_date=batch.batch_date,
        status=batch.status,
        total_amount_usd=batch.total_amount_usd,
        total_boxes=batch.total_boxes,
        total_weight_kg=batch.total_weight_kg,
        remaining_boxes=remaining_boxes,
        notes=batch.notes,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
        invoice_count=len(invoices),
        invoices=invoices,
    )


@router.get("/", response_model=BatchListResponse)
async def list_batches(
    status: Optional[BatchStatus] = Query(None, description="批次状态"),
    search: Optional[str] = Query(None, description="搜索批次名称"),
    exclude_fully_exchanged: bool = Query(False, description="排除已全部购汇的批次"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """批次列表"""
    items, total = await BatchService.list_batches(
        db=db, status=status, search=search, exclude_fully_exchanged=exclude_fully_exchanged, skip=skip, limit=limit
    )

    result_items = []
    for batch in items:
        result_items.append(await _build_batch_response(db, batch))

    return BatchListResponse(total=total, items=result_items, skip=skip, limit=limit)


@router.post("/", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    data: BatchCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建批次"""
    batch = await BatchService.create(
        db=db,
        data=data.model_dump(exclude={"invoice_ids"}),
        invoice_ids=data.invoice_ids,
    )
    # 计算汇总
    await BatchService.recalculate_totals(db, batch)
    await db.refresh(batch)
    return await _build_batch_response(db, batch)


@router.get("/{batch_id}", response_model=BatchResponse)
async def get_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """批次详情"""
    batch = await BatchService.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    return await _build_batch_response(db, batch)


@router.put("/{batch_id}", response_model=BatchResponse)
async def update_batch(
    batch_id: int,
    data: BatchUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新批次"""
    batch = await BatchService.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")

    if batch.status == BatchStatus.LOCKED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="批次已锁定，不能修改")

    update_data = data.model_dump(exclude_unset=True)
    updated = await BatchService.update(db, batch, update_data)
    return await _build_batch_response(db, updated)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除批次"""
    batch = await BatchService.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    await BatchService.delete(db, batch)
    return None


@router.post("/{batch_id}/lock", response_model=BatchResponse)
async def lock_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """锁定批次（级联锁定关联发票）
    
    **前置检查：** 批次下所有销售单必须已结清（状态为 fully_paid 或已锁定），否则不能锁定
    """
    from app.models import WholeFishSale, SalesStatus
    from sqlalchemy import select as sa_select, func
    
    batch = await BatchService.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    
    # 检查是否有未结清的销售单
    pending_sales_result = await db.execute(
        sa_select(WholeFishSale.id, WholeFishSale.sale_no, WholeFishSale.status, WholeFishSale.net_amount, WholeFishSale.paid_amount)
        .where(WholeFishSale.batch_id == batch_id)
        .where(WholeFishSale.status.in_([SalesStatus.PENDING, SalesStatus.PARTIAL_PAID, SalesStatus.AFTER_SALES]))
    )
    pending_sales = pending_sales_result.all()
    
    if pending_sales:
        # 构建错误信息
        sale_list = ", ".join([f"{s.sale_no}({s.status.value})" for s in pending_sales[:5]])
        if len(pending_sales) > 5:
            sale_list += f" 等共{len(pending_sales)}条"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该批次有未结清的销售单，请先完成收款后再锁定: {sale_list}"
        )
    
    batch.status = BatchStatus.LOCKED
    batch.is_locked = True
    
    # 级联锁定关联的发票
    from app.models import ImportInvoice, BatchInvoice
    batch_invoice_result = await db.execute(
        sa_select(ImportInvoice)
        .join(BatchInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
        .where(BatchInvoice.batch_id == batch_id)
    )
    for inv in batch_invoice_result.scalars().all():
        inv.is_locked = True
    
    await db.commit()
    await db.refresh(batch)
    return await _build_batch_response(db, batch)


@router.post("/{batch_id}/unlock", response_model=BatchResponse)
async def unlock_batch(
    batch_id: int,
    db: AsyncSession = Depends(get_db),
):
    """解锁批次（级联解锁关联发票）"""
    batch = await BatchService.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    batch.status = BatchStatus.OPEN
    batch.is_locked = False
    
    # 级联解锁关联的发票
    from app.models import ImportInvoice, BatchInvoice
    from sqlalchemy import select as sa_select
    batch_invoice_result = await db.execute(
        sa_select(ImportInvoice)
        .join(BatchInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
        .where(BatchInvoice.batch_id == batch_id)
    )
    for inv in batch_invoice_result.scalars().all():
        inv.is_locked = False
    
    await db.commit()
    await db.refresh(batch)
    return await _build_batch_response(db, batch)


@router.post("/{batch_id}/invoices", status_code=status.HTTP_201_CREATED)
async def add_invoice_to_batch(
    batch_id: int,
    data: AddInvoiceToBatch,
    db: AsyncSession = Depends(get_db),
):
    """添加发票到批次"""
    batch = await BatchService.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    if batch.status != BatchStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="批次已锁定，不能添加发票")

    invoice = await InvoiceService.get_by_id(db, data.invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发票不存在")

    bi = await BatchService.add_invoice(db, batch_id, data.invoice_id)
    if not bi:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="发票已存在于其他批次")

    # 重新计算汇总
    await BatchService.recalculate_totals(db, batch)
    return {"message": "发票已添加到批次"}


@router.delete("/{batch_id}/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_invoice_from_batch(
    batch_id: int,
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """从批次移除发票"""
    batch = await BatchService.get_by_id(db, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批次不存在")
    if batch.status != BatchStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="批次已锁定，不能移除发票")

    success = await BatchService.remove_invoice(db, batch_id, invoice_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="发票不在此批次中")

    await BatchService.recalculate_totals(db, batch)
    return None


@router.get("/summary", response_model=BatchSummary)
async def get_batch_summary(
    db: AsyncSession = Depends(get_db),
):
    """批次汇总统计"""
    summary = await BatchService.get_summary(db)
    return BatchSummary(**summary)
