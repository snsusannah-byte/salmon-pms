"""
损耗处理 API
"""
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.finished_product_v2 import (
    LossRecordCreate,
    LossRecordUpdate,
    LossRecordResponse,
    LossRecordListResponse,
    LossRecordSummary,
)
from app.services.loss_record_service import LossRecordService

router = APIRouter()


@router.get("/", response_model=LossRecordListResponse)
async def list_loss_records(
    loss_type: Optional[str] = Query(None, description="损耗类型: spoilage/inventory_diff/expired/other"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    product_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """损耗处理记录列表"""
    items, total = await LossRecordService.list_records(
        db=db,
        loss_type=loss_type,
        start_date=start_date,
        end_date=end_date,
        product_id=product_id,
        skip=skip,
        limit=limit,
    )
    return LossRecordListResponse(
        total=total,
        items=[LossRecordResponse.model_validate(i) for i in items],
        skip=skip,
        limit=limit,
    )


@router.post("/", response_model=LossRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_loss_record(
    data: LossRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建损耗处理记录
    
    业务规则：
    - 变质报废：扣减当日可用肉或仓库库存
    - 盘点差异：调整仓库库存
    - 过期处理：扣减仓库库存
    
    如果填写了slaughter_date，会扣减对应宰杀日期的可用肉；
    如果填写了product_id，会扣减对应产品的仓库库存。
    """
    record = await LossRecordService.create_record(db, data.model_dump())
    return LossRecordResponse.model_validate(record)


@router.get("/{record_id}", response_model=LossRecordResponse)
async def get_loss_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """损耗记录详情"""
    record = await LossRecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return LossRecordResponse.model_validate(record)


@router.put("/{record_id}", response_model=LossRecordResponse)
async def update_loss_record(
    record_id: int,
    data: LossRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新损耗记录"""
    record = await LossRecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    updated = await LossRecordService.update_record(db, record, data.model_dump(exclude_unset=True))
    return LossRecordResponse.model_validate(updated)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loss_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除损耗记录"""
    record = await LossRecordService.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    await LossRecordService.delete_record(db, record)
    return None


@router.get("/summary/stats", response_model=LossRecordSummary)
async def get_loss_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """损耗汇总统计"""
    summary = await LossRecordService.get_summary(db, start_date, end_date)
    return LossRecordSummary(**summary)
