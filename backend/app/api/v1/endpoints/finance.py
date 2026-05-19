from decimal import Decimal
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
    ImportFeeCreate, ImportFeeUpdate,
)
from app.services.finance_service import FinanceService
from app.models import BatchInvoice, Batch
from sqlalchemy import select

router = APIRouter()


# ==================== 批次锁定检查 ====================

async def _check_batch_locked_by_invoice(db: AsyncSession, invoice_id: int):
    """通过发票ID检查批次是否已锁定"""
    bi = await db.execute(
        select(BatchInvoice).where(BatchInvoice.invoice_id == invoice_id)
    )
    row = bi.scalar_one_or_none()
    if row:
        batch = await db.get(Batch, row.batch_id)
        if batch and batch.is_locked:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该批次已锁定，禁止修改")


async def _check_batch_locked(db: AsyncSession, batch_id: int):
    """直接检查批次是否已锁定"""
    batch = await db.get(Batch, batch_id)
    if batch and batch.is_locked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该批次已锁定，禁止修改")


# ==================== 银行账户 ====================

@router.get("/bank-accounts", response_model=list[dict])
async def list_bank_accounts(
    db: AsyncSession = Depends(get_db),
):
    """银行账户列表 - 余额根据交易流水实时计算"""
    from sqlalchemy import select, func
    from app.models import BankAccount, Company, TransactionRecord
    
    result = await db.execute(
        select(BankAccount).where(BankAccount.is_active).order_by(BankAccount.bank_name)
    )
    accounts = result.scalars().all()
    
    # 实时计算每个账户的余额
    for account in accounts:
        # 转入金额 (to_account_id)
        income_result = await db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                TransactionRecord.to_account_id == account.id,
                TransactionRecord.is_confirmed,
            )
        )
        total_income = income_result.scalar() or 0
        
        # 转出金额 (from_account_id)
        expense_result = await db.execute(
            select(func.sum(TransactionRecord.amount)).where(
                TransactionRecord.from_account_id == account.id,
                TransactionRecord.is_confirmed,
            )
        )
        total_expense = expense_result.scalar() or 0
        
        # 余额 = 期初余额 + 转入 - 转出
        actual_balance = Decimal(str(account.opening_balance or 0)) + Decimal(str(total_income)) - Decimal(str(total_expense))
        account.current_balance = actual_balance
    
    # Fetch company names
    company_ids = [a.company_id for a in accounts if a.company_id]
    company_map = {}
    if company_ids:
        result2 = await db.execute(select(Company.id, Company.name).where(Company.id.in_(company_ids)))
        company_map = {r[0]: r[1] for r in result2.all()}
    
    return [
        {
            "id": a.id,
            "code": a.code,
            "account_name": a.account_name,
            "bank_name": a.bank_name,
            "account_number": a.account_number,
            "type": a.type,
            "currency": a.currency,
            "current_balance": str(a.current_balance) if a.current_balance else "0",
            "company_id": a.company_id,
            "company_name": company_map.get(a.company_id) if a.company_id else None,
            "is_active": a.is_active,
        }
        for a in accounts
    ]


@router.post("/bank-accounts", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """创建银行账户（编号自动生成）"""
    from sqlalchemy import select, func
    from app.models import BankAccount
    
    # 自动生成编号: BA + 6位自增序号
    result = await db.execute(
        select(func.max(BankAccount.id))
    )
    max_id = result.scalar() or 0
    auto_code = f"BA{max_id + 1:06d}"
    
    # 如果用户传了code且不为空，用用户的；否则用自动生成的
    code = data.get("code", "").strip()
    if not code:
        code = auto_code
    
    account = BankAccount(
        code=code,
        account_name=data.get("account_name", ""),
        bank_name=data.get("bank_name", ""),
        account_number=data.get("account_number") or "",
        type=data.get("type", "public"),
        currency=data.get("currency", "CNY"),
        opening_balance=data.get("opening_balance", 0),
        current_balance=data.get("opening_balance", 0),
        company_id=data.get("company_id"),
        notes=data.get("notes"),
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return {"id": account.id, "code": account.code, "message": "创建成功"}


@router.put("/bank-accounts/{account_id}", response_model=dict)
async def update_bank_account(
    account_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """更新银行账户"""
    from sqlalchemy import select
    from app.models import BankAccount
    
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="银行账户不存在")
    
    for field in ["code", "account_name", "bank_name", "account_number", "type", "currency", "company_id", "notes", "is_active"]:
        if field in data:
            setattr(account, field, data[field])
    if "opening_balance" in data:
        account.opening_balance = data["opening_balance"]
    if "current_balance" in data:
        account.current_balance = data["current_balance"]
    
    await db.commit()
    await db.refresh(account)
    return {"id": account.id, "code": account.code, "message": "更新成功"}


@router.delete("/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除银行账户（软删除）"""
    from sqlalchemy import select
    from app.models import BankAccount
    
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="银行账户不存在")
    
    account.is_active = False
    await db.commit()
    return None


# ==================== 购汇记录 ====================

@router.get("/exchange", response_model=List[ExchangeRecordResponse])
async def list_exchange_records(
    invoice_id: Optional[int] = Query(None, description="发票ID"),
    batch_id: Optional[int] = Query(None, description="批次ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """购汇记录列表（支持按发票或批次筛选）"""
    items, total = await FinanceService.list_exchange_records(db, invoice_id=invoice_id, batch_id=batch_id, skip=skip, limit=limit)
    
    # 收集所有需要查询的发票ID
    all_invoice_ids = set()
    for r in items:
        if r.related_invoice_ids:
            all_invoice_ids.update(r.related_invoice_ids)
    
    # 查询发票号映射
    invoice_no_map = {}
    if all_invoice_ids:
        from app.models import ImportInvoice
        from sqlalchemy import select
        result = await db.execute(
            select(ImportInvoice.id, ImportInvoice.invoice_no).where(ImportInvoice.id.in_(list(all_invoice_ids)))
        )
        invoice_no_map = {row[0]: row[1] for row in result.all()}
    
    # 构建响应
    responses = []
    for r in items:
        resp_data = {
            **r.__dict__,
            "related_invoice_nos": [invoice_no_map.get(iid, str(iid)) for iid in (r.related_invoice_ids or [])] if r.related_invoice_ids else None,
        }
        responses.append(ExchangeRecordResponse.model_validate(resp_data))
    
    return responses


@router.post("/exchange", response_model=ExchangeRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange_record(
    data: ExchangeRecordCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建购汇记录"""
    if data.batch_id:
        await _check_batch_locked(db, data.batch_id)
    record = await FinanceService.create_exchange_record(db, data.model_dump())
    return ExchangeRecordResponse.model_validate(record)


@router.put("/exchange/{record_id}", response_model=ExchangeRecordResponse)
async def update_exchange_record(
    record_id: int,
    data: ExchangeRecordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新购汇记录"""
    from app.models import ExchangeRecord
    result = await db.execute(select(ExchangeRecord).where(ExchangeRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="购汇记录不存在")
    if record.batch_id:
        await _check_batch_locked(db, record.batch_id)
    updated = await FinanceService.update_exchange_record(db, record, data.model_dump(exclude_unset=True))
    return ExchangeRecordResponse.model_validate(updated)


@router.delete("/exchange/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exchange_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除购汇记录"""
    from app.models import ExchangeRecord
    result = await db.execute(select(ExchangeRecord).where(ExchangeRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="购汇记录不存在")
    if record.batch_id:
        await _check_batch_locked(db, record.batch_id)
    await FinanceService.delete_exchange_record(db, record)
    return None


# ==================== 统一进口费用 ====================

@router.get("/import-fees")
async def list_import_fees(
    invoice_id: Optional[int] = Query(None, description="发票ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """统一进口费用列表（合并税费+清关）"""
    items, total = await FinanceService.list_import_fees(db, invoice_id=invoice_id, skip=skip, limit=limit)
    return {
        "items": items,
        "total": total,
    }


@router.post("/import-fees", status_code=status.HTTP_201_CREATED)
async def create_import_fee(
    data: ImportFeeCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建统一进口费用（同时写入税费+清关表）"""
    if data.invoice_id:
        await _check_batch_locked_by_invoice(db, data.invoice_id)
    result = await FinanceService.create_import_fee(db, data.model_dump())
    return {"success": True, "data": result}


@router.put("/import-fees/{invoice_id}")
async def update_import_fee(
    invoice_id: int,
    data: ImportFeeUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新统一进口费用（复用 create 逻辑，已存在则更新）"""
    await _check_batch_locked_by_invoice(db, invoice_id)
    result = await FinanceService.create_import_fee(db, {**data.model_dump(), "invoice_id": invoice_id})
    return {"success": True, "data": result}


@router.delete("/import-fees/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_import_fee(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除统一进口费用（同时删除税费+清关记录）"""
    await _check_batch_locked_by_invoice(db, invoice_id)
    await FinanceService.delete_import_fee(db, invoice_id)
    return None


# ==================== 批次采购总额 ====================

@router.get("/batch-purchase-total")
async def get_batch_purchase_total(
    batch_id: int = Query(..., description="批次ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取批次采购总额（汇总该批次下所有发票的USD金额）"""
    result = await FinanceService.get_batch_purchase_total(db, batch_id)
    return {"success": True, "data": result}


# ==================== 进口税费 (保留旧接口兼容) ====================

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


# ==================== 清关运费 (保留旧接口兼容) ====================

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

@router.get("/transactions")
async def list_transactions(
    type: Optional[str] = Query(None, description="类型"),
    category: Optional[str] = Query(None, description="分类"),
    related_sale_id: Optional[int] = Query(None, description="关联销售单ID"),
    sale_no: Optional[str] = Query(None, description="关联销售单号（模糊匹配，如20260106匹配XS20260106-XXX）"),
    is_locked: Optional[bool] = Query(None, description="锁定状态筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    search: Optional[str] = Query(None, description="搜索关键词（日期/对方名称/描述/参考号）"),
    bank_account_id: Optional[int] = Query(None, description="银行账户ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """交易流水列表（分页）"""
    from datetime import date
    sd = date.fromisoformat(start_date) if start_date else None
    ed = date.fromisoformat(end_date) if end_date else None
    items, total = await FinanceService.list_transactions(db, type=type, category=category, related_sale_id=related_sale_id, sale_no=sale_no, is_locked=is_locked, start_date=sd, end_date=ed, search=search, bank_account_id=bank_account_id, skip=skip, limit=limit)
    return {
        "total": total,
        "items": [TransactionRecordResponse.model_validate(r).model_dump() for r in items],
        "skip": skip,
        "limit": limit,
    }


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
    if record.is_locked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="交易记录已锁定，不能修改")
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
    if record.is_locked:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="交易记录已锁定，不能删除")
    await FinanceService.delete_transaction(db, record)
    return None


@router.post("/transactions/batch-lock", response_model=dict)
async def batch_lock_transactions(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """批量锁定交易记录

    请求体: {"ids": [1, 2, 3]}
    返回: {"locked": 3, "not_found": 0, "already_locked": 0}
    """
    from sqlalchemy import select
    from app.models import TransactionRecord

    ids = data.get("ids", [])
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids 不能为空且必须是数组")

    valid_ids = [int(i) for i in ids if isinstance(i, int) or (isinstance(i, str) and i.isdigit())]
    if not valid_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids 中无有效整数")

    result = await db.execute(select(TransactionRecord).where(TransactionRecord.id.in_(valid_ids)))
    records = result.scalars().all()

    locked = 0
    already_locked = 0
    found_ids = {r.id for r in records}
    not_found = len(valid_ids) - len(found_ids)

    for r in records:
        if r.is_locked:
            already_locked += 1
        else:
            r.is_locked = True
            locked += 1

    if locked > 0:
        await db.commit()

    return {"locked": locked, "not_found": not_found, "already_locked": already_locked}


@router.post("/transactions/batch-unlock", response_model=dict)
async def batch_unlock_transactions(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """批量解锁交易记录

    请求体: {"ids": [1, 2, 3]}
    返回: {"unlocked": 3, "not_found": 0, "not_locked": 0}
    """
    from sqlalchemy import select
    from app.models import TransactionRecord

    ids = data.get("ids", [])
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids 不能为空且必须是数组")

    valid_ids = [int(i) for i in ids if isinstance(i, int) or (isinstance(i, str) and i.isdigit())]
    if not valid_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids 中无有效整数")

    result = await db.execute(select(TransactionRecord).where(TransactionRecord.id.in_(valid_ids)))
    records = result.scalars().all()

    unlocked = 0
    not_locked = 0
    found_ids = {r.id for r in records}
    not_found = len(valid_ids) - len(found_ids)

    for r in records:
        if not r.is_locked:
            not_locked += 1
        else:
            r.is_locked = False
            unlocked += 1

    if unlocked > 0:
        await db.commit()

    return {"unlocked": unlocked, "not_found": not_found, "not_locked": not_locked}


@router.post("/transactions/{record_id}/lock", response_model=TransactionRecordResponse)
async def lock_transaction(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """锁定交易记录"""
    from sqlalchemy import select
    from app.models import TransactionRecord
    result = await db.execute(select(TransactionRecord).where(TransactionRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="交易记录不存在")
    record.is_locked = True
    await db.commit()
    await db.refresh(record)
    return TransactionRecordResponse.model_validate(record)


@router.post("/transactions/{record_id}/unlock", response_model=TransactionRecordResponse)
async def unlock_transaction(
    record_id: int,
    db: AsyncSession = Depends(get_db),
):
    """解锁交易记录"""
    from sqlalchemy import select
    from app.models import TransactionRecord
    result = await db.execute(select(TransactionRecord).where(TransactionRecord.id == record_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="交易记录不存在")
    record.is_locked = False
    await db.commit()
    await db.refresh(record)
    return TransactionRecordResponse.model_validate(record)


@router.post("/transactions/batch-delete", response_model=dict)
async def batch_delete_transactions(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """批量删除交易记录
    
    请求体: {"ids": [1, 2, 3]}
    返回: {"deleted": 3, "not_found": 0}
    """
    ids = data.get("ids", [])
    if not ids or not isinstance(ids, list):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids 不能为空且必须是数组")
    
    # 过滤非整数项
    valid_ids = [int(i) for i in ids if isinstance(i, int) or (isinstance(i, str) and i.isdigit())]
    if not valid_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ids 中无有效整数")
    
    result = await FinanceService.delete_transactions_batch(db, valid_ids)
    return result


# ==================== 汇总 ====================

@router.get("/summary", response_model=FinanceSummary)
async def get_finance_summary(
    db: AsyncSession = Depends(get_db),
):
    """财务汇总统计"""
    summary = await FinanceService.get_summary(db)
    return FinanceSummary(**summary)


# ==================== 批量导入 ====================

@router.post("/batch-import", status_code=status.HTTP_201_CREATED)
async def batch_import_finance(
    records: List[dict],
    db: AsyncSession = Depends(get_db),
):
    """批量导入财务记录
    
    支持导入: 购汇记录 / 税费 / 清关费
    返回: {created: 新增数, errors: 错误列表}
    """
    from decimal import Decimal
    from datetime import datetime
    from app.models import ImportInvoice
    
    created_count = 0
    errors = []
    
    for idx, record in enumerate(records):
        try:
            record_type = record.get("type", "").strip().lower()
            invoice_no = record.get("invoice_no", "").strip()
            
            # 查找发票ID
            invoice_id = None
            if invoice_no:
                result = await db.execute(select(ImportInvoice.id).where(ImportInvoice.invoice_no == invoice_no))
                invoice_id = result.scalar_one_or_none()
            
            if record_type in ["exchange", "购汇"]:
                data = {
                    "invoice_id": invoice_id,
                    "exchange_date": datetime.strptime(record.get("date", ""), "%Y-%m-%d").date(),
                    "amount_usd": Decimal(str(record.get("amount_usd", 0))),
                    "exchange_rate": Decimal(str(record.get("exchange_rate", 0))),
                    "amount_cny": Decimal(str(record.get("amount_cny", 0))),
                    "fee_cny": Decimal(str(record.get("fee_cny", 0))),
                    "bank_account_id": record.get("bank_account_id"),
                    "status": "completed",
                    "notes": record.get("notes", ""),
                }
                await FinanceService.create_exchange_record(db, data)
                created_count += 1
                
            elif record_type in ["tax", "税费"]:
                data = {
                    "invoice_id": invoice_id,
                    "tax_date": datetime.strptime(record.get("date", ""), "%Y-%m-%d").date(),
                    "customs_declaration_no": record.get("customs_declaration_no", ""),
                    "total_tax": Decimal(str(record.get("total_tax", 0))),
                    "notes": record.get("notes", ""),
                }
                await FinanceService.create_import_tax(db, data)
                created_count += 1
                
            elif record_type in ["clearance", "清关费"]:
                data = {
                    "invoice_id": invoice_id,
                    "cost_date": datetime.strptime(record.get("date", ""), "%Y-%m-%d").date(),
                    "customs_declaration_no": record.get("customs_declaration_no", ""),
                    "customs_broker_id": record.get("customs_broker_id"),
                    "total_cost": Decimal(str(record.get("total_cost", 0))),
                    "notes": record.get("notes", ""),
                }
                await FinanceService.create_clearance_cost(db, data)
                created_count += 1
                
            else:
                errors.append({"row": idx + 1, "error": f"未知的记录类型: {record_type}"})
                
        except Exception as e:
            errors.append({"row": idx + 1, "error": str(e)})
    
    return {
        "created": created_count,
        "errors": errors,
    }


@router.post("/transactions/batch-import", status_code=status.HTTP_201_CREATED)
async def batch_import_transactions(
    records: List[dict],
    db: AsyncSession = Depends(get_db),
):
    """批量导入交易流水记录
    
    支持导入: 交易流水
    返回: {created: 新增数, errors: 错误列表}
    """
    from decimal import Decimal
    from datetime import datetime
    
    created_count = 0
    errors = []
    
    for idx, record in enumerate(records):
        try:
            transaction_date = record.get("transaction_date", "").strip()
            if not transaction_date:
                errors.append({"row": idx + 1, "error": "交易日期不能为空"})
                continue
            
            type_str = record.get("type", "").strip().lower()
            if type_str not in ["income", "expense", "transfer", "exchange", "收入", "支出", "转账", "购汇"]:
                errors.append({"row": idx + 1, "error": f"未知的交易类型: {type_str}"})
                continue
            
            # Normalize type
            type_map = {
                "收入": "income", "支出": "expense", "转账": "transfer", "购汇": "exchange",
            }
            normalized_type = type_map.get(type_str, type_str)
            
            amount = Decimal(str(record.get("amount", 0)))
            if amount <= 0:
                errors.append({"row": idx + 1, "error": "金额必须大于0"})
                continue
            
            data = {
                "transaction_date": datetime.strptime(transaction_date, "%Y-%m-%d").date(),
                "type": normalized_type,
                "category": record.get("category", "other").strip(),
                "amount": amount,
                "currency": "CNY",
                "counterparty_name": record.get("counterparty_name", "").strip() or None,
                "reference_no": record.get("reference_no", "").strip() or None,
                "description": record.get("description", "").strip() or None,
            }
            
            await FinanceService.create_transaction(db, data)
            created_count += 1
                
        except Exception as e:
            errors.append({"row": idx + 1, "error": str(e)})
    
    return {
        "created": created_count,
        "errors": errors,
    }
