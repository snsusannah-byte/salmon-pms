from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from app.core.database import get_db
from app.models import Salesperson, CommissionRecord
from app.schemas.company import (
    SalespersonCreate,
    SalespersonUpdate,
    SalespersonResponse,
    CommissionResponse,
)
from app.services.company_service import CompanyService

router = APIRouter()


# ==================== 业务员管理 ====================

@router.get("/", response_model=dict)
async def list_salespersons(
    search: Optional[str] = Query(None, description="搜索名称"),
    is_active: Optional[bool] = Query(None, description="是否在职"),
    db: AsyncSession = Depends(get_db),
):
    """业务员列表"""
    query = select(Salesperson)
    count_query = select(func.count(Salesperson.id))

    if search:
        query = query.where(Salesperson.name.ilike(f"%{search}%"))
        count_query = count_query.where(Salesperson.name.ilike(f"%{search}%"))

    if is_active is not None:
        query = query.where(Salesperson.is_active == is_active)
        count_query = count_query.where(Salesperson.is_active == is_active)

    query = query.order_by(Salesperson.name)

    result = await db.execute(query)
    items = result.scalars().all()

    count_result = await db.execute(count_query)
    total = count_result.scalar()

    return {
        "total": total,
        "items": [
            {
                "id": sp.id,
                "name": sp.name,
                "phone": sp.phone,
                "email": sp.email,
                "commission_rate": float(sp.commission_rate) if sp.commission_rate else 0,
                "is_active": sp.is_active,
                "notes": sp.notes,
                "created_at": sp.created_at,
                "updated_at": sp.updated_at,
            }
            for sp in items
        ],
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_salesperson(
    data: SalespersonCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建业务员"""
    sp = Salesperson(
        name=data.name,
        phone=data.phone,
        email=data.email,
        commission_rate=data.commission_rate,
        is_active=data.is_active,
        notes=data.notes,
    )
    db.add(sp)
    await db.commit()
    await db.refresh(sp)
    return {
        "id": sp.id,
        "name": sp.name,
        "phone": sp.phone,
        "email": sp.email,
        "commission_rate": float(sp.commission_rate),
        "is_active": sp.is_active,
        "notes": sp.notes,
        "created_at": sp.created_at,
        "updated_at": sp.updated_at,
    }


@router.get("/{sp_id}")
async def get_salesperson(
    sp_id: int,
    db: AsyncSession = Depends(get_db),
):
    """业务员详情"""
    result = await db.execute(select(Salesperson).where(Salesperson.id == sp_id))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=404, detail="业务员不存在")
    return {
        "id": sp.id,
        "name": sp.name,
        "phone": sp.phone,
        "email": sp.email,
        "commission_rate": float(sp.commission_rate),
        "is_active": sp.is_active,
        "notes": sp.notes,
        "created_at": sp.created_at,
        "updated_at": sp.updated_at,
    }


@router.put("/{sp_id}")
async def update_salesperson(
    sp_id: int,
    data: SalespersonUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新业务员"""
    result = await db.execute(select(Salesperson).where(Salesperson.id == sp_id))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=404, detail="业务员不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(sp, field, value)

    await db.commit()
    await db.refresh(sp)
    return {
        "id": sp.id,
        "name": sp.name,
        "phone": sp.phone,
        "email": sp.email,
        "commission_rate": float(sp.commission_rate),
        "is_active": sp.is_active,
        "notes": sp.notes,
        "created_at": sp.created_at,
        "updated_at": sp.updated_at,
    }


@router.delete("/{sp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_salesperson(
    sp_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除业务员（软删除：标记停用）"""
    result = await db.execute(select(Salesperson).where(Salesperson.id == sp_id))
    sp = result.scalar_one_or_none()
    if not sp:
        raise HTTPException(status_code=404, detail="业务员不存在")
    sp.is_active = False
    await db.commit()
    return None


# ==================== 提成管理 ====================

@router.get("/commissions/")
async def list_commissions(
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    salesperson_id: Optional[int] = Query(None, description="业务员ID"),
    status: Optional[str] = Query(None, description="状态 pending/paid"),
    batch_id: Optional[int] = Query(None, description="批次ID"),
    db: AsyncSession = Depends(get_db),
):
    """提成记录列表"""
    from app.models import WholeFishSale, Company
    from sqlalchemy.orm import joinedload
    
    query = select(CommissionRecord).options(joinedload(CommissionRecord.salesperson))
    
    if month:
        from datetime import datetime
        start = datetime.strptime(month, "%Y-%m")
        import calendar
        _, last_day = calendar.monthrange(start.year, start.month)
        from datetime import date
        query = query.where(
            CommissionRecord.sale_date >= date(start.year, start.month, 1),
            CommissionRecord.sale_date <= date(start.year, start.month, last_day),
        )

    if salesperson_id:
        query = query.where(CommissionRecord.salesperson_id == salesperson_id)

    if status:
        query = query.where(CommissionRecord.status == status)
    
    # 如果按批次筛选，先查该批次的销售单ID
    sale_ids = None
    if batch_id:
        result = await db.execute(select(WholeFishSale.id).where(WholeFishSale.batch_id == batch_id))
        sale_ids = [r[0] for r in result.all()]
        if sale_ids:
            query = query.where(CommissionRecord.sale_id.in_(sale_ids))
        else:
            # 该批次没有销售单，返回空
            return {
                "items": [],
                "summary": {"total_pending": 0, "total_paid": 0, "total_amount": 0},
            }

    query = query.order_by(CommissionRecord.sale_date.desc())

    result = await db.execute(query)
    items = result.scalars().all()
    
    # 预加载客户信息
    sale_ids_all = [r.sale_id for r in items]
    customers_map = {}
    if sale_ids_all:
        result = await db.execute(
            select(WholeFishSale.id, Company.name).join(Company, WholeFishSale.customer_id == Company.id).where(WholeFishSale.id.in_(sale_ids_all))
        )
        customers_map = {r[0]: r[1] for r in result.all()}
    
    # 预加载批次信息
    batches_map = {}
    if sale_ids_all:
        result = await db.execute(
            select(WholeFishSale.id, WholeFishSale.batch_id).where(WholeFishSale.id.in_(sale_ids_all))
        )
        batch_ids = [r[1] for r in result.all() if r[1]]
        if batch_ids:
            from app.models import Batch
            result = await db.execute(select(Batch.id, Batch.batch_name).where(Batch.id.in_(batch_ids)))
            batch_name_map = {r[0]: r[1] for r in result.all()}
            
            result = await db.execute(select(WholeFishSale.id, WholeFishSale.batch_id).where(WholeFishSale.id.in_(sale_ids_all)))
            batches_map = {r[0]: batch_name_map.get(r[1], "-") for r in result.all()}

    total_pending = sum(float(r.commission_amount) for r in items if r.status == "pending")
    total_paid = sum(float(r.commission_amount) for r in items if r.status == "paid")
    total_amount = total_pending + total_paid

    return {
        "items": [
            {
                "id": r.id,
                "salesperson_id": r.salesperson_id,
                "salesperson_name": r.salesperson.name if r.salesperson else "-",
                "sale_id": r.sale_id,
                "sale_date": r.sale_date.isoformat() if r.sale_date else None,
                "customer_name": customers_map.get(r.sale_id, "-"),
                "batch_name": batches_map.get(r.sale_id, "-"),
                "sale_amount": float(r.sale_amount),
                "weight_kg": float(r.weight_kg),
                "commission_rate": float(r.commission_rate),
                "commission_amount": float(r.commission_amount),
                "status": r.status,
                "paid_date": r.paid_date.isoformat() if r.paid_date else None,
                "notes": r.notes,
            }
            for r in items
        ],
        "summary": {
            "total_pending": total_pending,
            "total_paid": total_paid,
            "total_amount": total_amount,
        },
    }


@router.post("/{sp_id}/pay-commission", status_code=status.HTTP_200_OK)
async def pay_commission(
    sp_id: int,
    record_ids: List[int],
    db: AsyncSession = Depends(get_db),
):
    """发放提成"""
    from datetime import date
    result = await db.execute(
        select(CommissionRecord).where(
            CommissionRecord.salesperson_id == sp_id,
            CommissionRecord.id.in_(record_ids),
            CommissionRecord.status == "pending",
        )
    )
    records = result.scalars().all()

    for r in records:
        r.status = "paid"
        r.paid_date = date.today()

    await db.commit()
    return {"paid_count": len(records)}
