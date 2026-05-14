"""
每日宰杀记录 API
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.finished_product_v2 import (
    DailySlaughterRecordCreate,
    DailySlaughterRecordUpdate,
    DailySlaughterRecordResponse,
    DailySlaughterListResponse,
    DailySlaughterSummary,
    SlaughterDateOption,
)
from app.services.daily_slaughter_service import DailySlaughterService

router = APIRouter()


@router.get("/", response_model=DailySlaughterListResponse)
async def list_slaughter_records(
    slaughter_type: Optional[str] = Query(None, description="宰杀类型: whole_fish/fillet"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """宰杀记录列表"""
    if not start_date and not end_date:
        # 默认最近30天
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
    
    items, total = await DailySlaughterService.list_records(
        db=db,
        slaughter_type=slaughter_type,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return DailySlaughterListResponse(
        total=total,
        items=[DailySlaughterRecordResponse.model_validate(i) for i in items],
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=DailySlaughterRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_slaughter_record(
    data: DailySlaughterRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建宰杀记录
    
    业务规则：
    - 整鱼：fish_count必填（宰杀条数），副产品按条数登记
    - 鱼柳：fish_count为0，副产品全部为0，只填总重量和成品肉产出
    - 自动计算：出肉率%、损耗率%、当日成本
    """
    # 检查是否已存在
    existing = await DailySlaughterService.get_by_date(db, data.slaughter_date)
    if existing:
        raise HTTPException(status_code=400, detail=f"日期 {data.slaughter_date} 已存在宰杀记录")
    
    record = await DailySlaughterService.create_record(db, data.model_dump())
    return DailySlaughterRecordResponse.model_validate(record)


@router.get("/{record_id}", response_model=DailySlaughterRecordResponse)
async def get_slaughter_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """宰杀记录详情"""
    record = await DailySlaughterService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return DailySlaughterRecordResponse.model_validate(record)


@router.put("/{record_id}", response_model=DailySlaughterRecordResponse)
async def update_slaughter_record(
    record_id: int,
    data: DailySlaughterRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新宰杀记录（仅未锁定时可更新）"""
    record = await DailySlaughterService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    try:
        updated = await DailySlaughterService.update_record(db, record, data.model_dump(exclude_unset=True))
        return DailySlaughterRecordResponse.model_validate(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slaughter_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除宰杀记录"""
    record = await DailySlaughterService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    try:
        await DailySlaughterService.delete_record(db, record)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None


@router.post("/{record_id}/lock", response_model=DailySlaughterRecordResponse)
async def lock_slaughter_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """锁定宰杀记录（成本确认后锁定，锁定后不可修改）"""
    record = await DailySlaughterService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    updated = await DailySlaughterService.lock_record(db, record)
    return DailySlaughterRecordResponse.model_validate(updated)


@router.get("/summary/stats", response_model=DailySlaughterSummary)
async def get_slaughter_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """宰杀记录汇总统计"""
    summary = await DailySlaughterService.get_summary(db, start_date, end_date)
    return DailySlaughterSummary(**summary)


@router.get("/options/slaughter-dates", response_model=List[SlaughterDateOption])
async def get_available_slaughter_dates(
    min_available_kg: Optional[Decimal] = Query(Decimal("0"), description="最小可用肉量(kg)"),
    db: AsyncSession = Depends(get_db),
):
    """获取可供销售的宰杀日期列表（销售时关联用）"""
    dates = await DailySlaughterService.get_available_slaughter_dates(db, min_available_kg)
    return [SlaughterDateOption(**d) for d in dates]
