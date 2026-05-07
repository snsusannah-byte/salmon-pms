from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timedelta
from typing import List, Optional

from app.core.database import get_db
from app.models import (
    Batch, BatchStatus, ImportInvoice, Company, CompanyType,
    WholeFishSale, Inventory, TransactionRecord, TransactionType,
)

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """数据看板汇总 - 实时统计"""
    now = datetime.now()
    this_month_start = date(now.year, now.month, 1)

    # 1. 批次统计
    batch_result = await db.execute(
        select(
            func.count(Batch.id),
            func.sum(case((Batch.status == BatchStatus.OPEN, 1), else_=0)),
            func.sum(case((Batch.status == BatchStatus.LOCKED, 1), else_=0)),
            func.sum(case((Batch.status == BatchStatus.SETTLED, 1), else_=0)),
        )
    )
    total_batches, open_batches, locked_batches, settled_batches = batch_result.one()

    # 2. 发票统计
    invoice_result = await db.execute(
        select(
            func.count(ImportInvoice.id),
            func.sum(ImportInvoice.total_amount_usd),
            func.sum(ImportInvoice.total_boxes),
            func.sum(ImportInvoice.total_weight_kg),
        )
    )
    total_invoices, total_invoice_amount, total_boxes, total_weight = invoice_result.one()

    # 3. 本月发票
    month_invoice_result = await db.execute(
        select(
            func.count(ImportInvoice.id),
            func.sum(ImportInvoice.total_amount_usd),
        ).where(ImportInvoice.invoice_date >= this_month_start)
    )
    month_invoices, month_amount = month_invoice_result.one()

    # 4. 客户数
    customer_result = await db.execute(
        select(func.count(Company.id)).where(
            and_(Company.type == CompanyType.CUSTOMER, Company.is_active == True)
        )
    )
    total_customers = customer_result.scalar()

    # 5. 公司总数（各类型）
    company_types_result = await db.execute(
        select(Company.type, func.count(Company.id))
        .where(Company.is_active == True)
        .group_by(Company.type)
    )
    company_breakdown = {row[0]: row[1] for row in company_types_result.all()}

    # 6. 库存总重
    inventory_result = await db.execute(
        select(func.sum(Inventory.current_weight_kg))
    )
    total_inventory = inventory_result.scalar()

    return {
        "batches": {
            "total": total_batches or 0,
            "open": open_batches or 0,
            "locked": locked_batches or 0,
            "settled": settled_batches or 0,
        },
        "invoices": {
            "total": total_invoices or 0,
            "total_amount_usd": total_invoice_amount or 0,
            "total_boxes": total_boxes or 0,
            "total_weight_kg": total_weight or 0,
            "this_month_count": month_invoices or 0,
            "this_month_amount": month_amount or 0,
        },
        "companies": {
            "total_customers": total_customers or 0,
            "breakdown": company_breakdown,
        },
        "inventory": {
            "total_weight_kg": total_inventory or 0,
        },
    }


@router.get("/recent-invoices")
async def get_recent_invoices(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """最近发票"""
    result = await db.execute(
        select(ImportInvoice)
        .order_by(ImportInvoice.created_at.desc())
        .limit(limit)
    )
    invoices = result.scalars().all()
    return [
        {
            "id": inv.id,
            "invoice_no": inv.invoice_no,
            "invoice_date": inv.invoice_date,
            "total_amount_usd": inv.total_amount_usd,
            "total_boxes": inv.total_boxes,
            "customs_status": inv.customs_status.value if hasattr(inv.customs_status, "value") else inv.customs_status,
            "exchange_status": inv.exchange_status.value if hasattr(inv.exchange_status, "value") else inv.exchange_status,
        }
        for inv in invoices
    ]


@router.get("/recent-batches")
async def get_recent_batches(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """最近批次"""
    result = await db.execute(
        select(Batch)
        .order_by(Batch.created_at.desc())
        .limit(limit)
    )
    batches = result.scalars().all()
    return [
        {
            "id": b.id,
            "batch_code": b.batch_code,
            "batch_name": b.batch_name,
            "batch_date": b.batch_date,
            "status": b.status.value if hasattr(b.status, "value") else b.status,
            "invoice_count": b.total_boxes,  # placeholder - would need actual count
        }
        for b in batches
    ]


@router.get("/customs-status-breakdown")
async def get_customs_status_breakdown(db: AsyncSession = Depends(get_db)):
    """报关状态分布"""
    result = await db.execute(
        select(ImportInvoice.customs_status, func.count(ImportInvoice.id))
        .group_by(ImportInvoice.customs_status)
    )
    return [
        {"status": row[0].value if hasattr(row[0], "value") else row[0], "count": row[1]}
        for row in result.all()
    ]


@router.get("/invoice-monthly-trend")
async def get_invoice_monthly_trend(
    months: int = 12,
    db: AsyncSession = Depends(get_db),
):
    """发票月度趋势（金额 + 数量）"""
    now = datetime.now()
    data = []
    for i in range(months - 1, -1, -1):
        month_date = date(now.year, now.month, 1) - timedelta(days=i * 30)
        month_start = date(month_date.year, month_date.month, 1)
        if month_date.month == 12:
            month_end = date(month_date.year + 1, 1, 1)
        else:
            month_end = date(month_date.year, month_date.month + 1, 1)

        result = await db.execute(
            select(
                func.count(ImportInvoice.id),
                func.sum(ImportInvoice.total_amount_usd),
            ).where(
                ImportInvoice.invoice_date >= month_start,
                ImportInvoice.invoice_date < month_end,
            )
        )
        count, amount = result.one()
        data.append({
            "month": f"{month_date.year}-{str(month_date.month).zfill(2)}",
            "count": count or 0,
            "amount": float(amount or 0),
        })
    return data
