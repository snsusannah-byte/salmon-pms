from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.daily_slaughter import (
    DailySlaughterRecordCreate,
    DailySlaughterRecordUpdate,
    DailySlaughterRecordResponse,
    DailySlaughterSummary,
)
from app.services.daily_slaughter_service import DailySlaughterService

router = APIRouter()


@router.get("/", response_model=List[DailySlaughterRecordResponse])
async def list_daily_slaughter_records(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """每日宰杀记录列表（支持日期范围过滤）"""
    items, total = await DailySlaughterService.list_records(
        db, start_date=start_date, end_date=end_date, skip=skip, limit=limit
    )
    return [DailySlaughterRecordResponse.model_validate(item) for item in items]


@router.post("/", response_model=DailySlaughterRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_slaughter_record(
    data: DailySlaughterRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建每日宰杀记录（自动计算出肉率）"""
    record = await DailySlaughterService.create(db, data.model_dump())
    return DailySlaughterRecordResponse.model_validate(record)


@router.get("/{record_id}", response_model=DailySlaughterRecordResponse)
async def get_daily_slaughter_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """每日宰杀记录详情"""
    record = await DailySlaughterService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"宰杀记录 ID={record_id} 不存在",
        )
    return DailySlaughterRecordResponse.model_validate(record)


@router.put("/{record_id}", response_model=DailySlaughterRecordResponse)
async def update_daily_slaughter_record(
    record_id: int,
    data: DailySlaughterRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新每日宰杀记录（重新计算出肉率）"""
    update_data = data.model_dump(exclude_unset=True)
    record = await DailySlaughterService.update(db, record_id, update_data)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"宰杀记录 ID={record_id} 不存在",
        )
    return DailySlaughterRecordResponse.model_validate(record)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_daily_slaughter_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除每日宰杀记录"""
    success = await DailySlaughterService.delete(db, record_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"宰杀记录 ID={record_id} 不存在",
        )
    return None


@router.get("/summary/stats", response_model=DailySlaughterSummary)
async def get_daily_slaughter_summary(
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
):
    """汇总统计"""
    summary = await DailySlaughterService.get_summary(db, start_date=start_date, end_date=end_date)
    return DailySlaughterSummary(**summary)
