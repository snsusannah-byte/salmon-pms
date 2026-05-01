from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.schemas.finance import (
    ExchangeRecordCreate, ExchangeRecordUpdate, ExchangeRecordResponse,
    ImportTaxCreate, ImportTaxUpdate, ImportTaxResponse,
    ClearanceCostCreate, ClearanceCostUpdate, ClearanceCostResponse,
    TransactionRecordCreate, TransactionRecordUpdate, TransactionRecordResponse,
    FinanceSummary,
)
from app.services.finance_service import FinanceService

router = APIRouter()


# ==================== 购汇记录 ====================

@router.get("/exchange", response_model=List[ExchangeRecordResponse])
async def list_exchange_records(
    invoice_id: Optional[int] = Query(None, description="发票ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """购汇记录列表"""
    items, total = await FinanceService.list_exchange_records(db, invoice_id=invoice_id, skip=skip, limit=limit)
    return [ExchangeRecordResponse.model_validate(r) for r in items]


@router.post("/exchange", response_model=ExchangeRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange_record(
    data: ExchangeRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建购汇记录"""
    record = await FinanceService.create_exchange_record(db, data.model_dump())
    return ExchangeRecordResponse.model_validate(record)


@router.put("/exchange/{record_id}", response_model=ExchangeRecordResponse)
async def update_exchange_record(
    record_id: int,
    data: ExchangeRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新购汇记录"""
    from sqlalchemy import select
    from app.models import ExchangeRecord
    result = await db.execute(select(ExchangeRecord).where(ExchangeRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="购汇记录不存在")
    updated = await FinanceService.update_exchange_record(db, record, data.model_dump(exclude_unset=True))
    return ExchangeRecordResponse.model_validate(updated)


@router.delete("/exchange/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exchange_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除购汇记录"""
    from sqlalchemy import select
    from app.models import ExchangeRecord
    result = await db.execute(select(ExchangeRecord).where(ExchangeRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="购汇记录不存在")
    await FinanceService.delete_exchange_record(db, record)
    return None


# ==================== 进口税费 ====================

@router.get("/taxes", response_model=List[ImportTaxResponse])
async def list_import_taxes(
    invoice_id: Optional[int] = Query(None, description="发票ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """进口税费列表"""
    items, total = await FinanceService.list_import_taxes(db, invoice_id=invoice_id, skip=skip, limit=limit)
    return [ImportTaxResponse.model_validate(r) for r in items]


@router.post("/taxes", response_model=ImportTaxResponse, status_code=status.HTTP_201_CREATED)
async def create_import_tax(
    data: ImportTaxCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建进口税费"""
    record = await FinanceService.create_import_tax(db, data.model_dump())
    return ImportTaxResponse.model_validate(record)


@router.put("/taxes/{record_id}", response_model=ImportTaxResponse)
async def update_import_tax(
    record_id: int,
    data: ImportTaxUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新进口税费"""
    from sqlalchemy import select
    from app.models import ImportTax
    result = await db.execute(select(ImportTax).where(ImportTax.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="税费记录不存在")
    updated = await FinanceService.update_import_tax(db, record, data.model_dump(exclude_unset=True))
    return ImportTaxResponse.model_validate(updated)


@router.delete("/taxes/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_import_tax(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除进口税费"""
    from sqlalchemy import select
    from app.models import ImportTax
    result = await db.execute(select(ImportTax).where(ImportTax.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="税费记录不存在")
    await FinanceService.delete_import_tax(db, record)
    return None


# ==================== 清关运费 ====================

@router.get("/clearance", response_model=List[ClearanceCostResponse])
async def list_clearance_costs(
    invoice_id: Optional[int] = Query(None, description="发票ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """清关运费列表"""
    items, total = await FinanceService.list_clearance_costs(db, invoice_id=invoice_id, skip=skip, limit=limit)
    return [ClearanceCostResponse.model_validate(r) for r in items]


@router.post("/clearance", response_model=ClearanceCostResponse, status_code=status.HTTP_201_CREATED)
async def create_clearance_cost(
    data: ClearanceCostCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建清关运费"""
    record = await FinanceService.create_clearance_cost(db, data.model_dump())
    return ClearanceCostResponse.model_validate(record)


@router.put("/clearance/{record_id}", response_model=ClearanceCostResponse)
async def update_clearance_cost(
    record_id: int,
    data: ClearanceCostUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新清关运费"""
    from sqlalchemy import select
    from app.models import ClearanceCost
    result = await db.execute(select(ClearanceCost).where(ClearanceCost.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="费用记录不存在")
    updated = await FinanceService.update_clearance_cost(db, record, data.model_dump(exclude_unset=True))
    return ClearanceCostResponse.model_validate(updated)


@router.delete("/clearance/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_clearance_cost(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除清关运费"""
    from sqlalchemy import select
    from app.models import ClearanceCost
    result = await db.execute(select(ClearanceCost).where(ClearanceCost.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="费用记录不存在")
    await FinanceService.delete_clearance_cost(db, record)
    return None


# ==================== 统一交易流水 ====================

@router.get("/transactions", response_model=List[TransactionRecordResponse])
async def list_transactions(
    type: Optional[str] = Query(None, description="类型"),
    category: Optional[str] = Query(None, description="分类"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """交易流水列表"""
    from datetime import date
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    items, total = await FinanceService.list_transactions(db, type=type, category=category, start_date=sd, end_date=ed, skip=skip, limit=limit)
    return [TransactionRecordResponse.model_validate(r) for r in items]


@router.post("/transactions", response_model=TransactionRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    data: TransactionRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建交易记录"""
    record = await FinanceService.create_transaction(db, data.model_dump())
    return TransactionRecordResponse.model_validate(record)


@router.put("/transactions/{record_id}", response_model=TransactionRecordResponse)
async def update_transaction(
    record_id: int,
    data: TransactionRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新交易记录"""
    from sqlalchemy import select
    from app.models import TransactionRecord
    result = await db.execute(select(TransactionRecord).where(TransactionRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="交易记录不存在")
    updated = await FinanceService.update_transaction(db, record, data.model_dump(exclude_unset=True))
    return TransactionRecordResponse.model_validate(updated)


@router.delete("/transactions/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除交易记录"""
    from sqlalchemy import select
    from app.models import TransactionRecord
    result = await db.execute(select(TransactionRecord).where(TransactionRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="交易记录不存在")
    await FinanceService.delete_transaction(db, record)
    return None


# ==================== 汇总 ====================

@router.get("/summary", response_model=FinanceSummary)
async def get_finance_summary(
    db: AsyncSession = Depends(get_db),
):
    """财务汇总统计"""
    summary = await FinanceService.get_summary(db)
    return FinanceSummary(**summary)
