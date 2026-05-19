"""
销售单批量合并收款 API
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import (
    BankAccount,
    Company,
    SalesReceipt,
    SalesStatus,
    TransactionRecord,
    WholeFishSale,
)

router = APIRouter()


class BatchCollectRequest(BaseModel):
    sale_ids: List[int]
    bank_account_id: int
    collect_date: date
    amount: Optional[float] = None  # 用户指定的实收金额，不传则按应收总额自动计算


@router.post("/batch-collect", status_code=status.HTTP_200_OK)
async def batch_collect_sales(
    data: BatchCollectRequest,
    db: AsyncSession = Depends(get_db),
):
    """合并收款：勾选多个销售单，一键收款"""
    
    # 1. 查询所有销售单
    result = await db.execute(
        select(WholeFishSale).where(WholeFishSale.id.in_(data.sale_ids))
    )
    sales = list(result.scalars().all())
    
    if len(sales) != len(data.sale_ids):
        missing = set(data.sale_ids) - {s.id for s in sales}
        raise HTTPException(status_code=404, detail=f"销售单不存在: {missing}")
    
    # 2. 检查销售单状态
    for sale in sales:
        if sale.is_locked:
            raise HTTPException(status_code=400, detail=f"销售单 {sale.sale_no} 已锁定，不能收款")
    
    # 3. 计算各自应收金额（用于显示，实际收款按分配逻辑）
    sale_receivables = {}
    total_receivable = Decimal("0")
    customer_names = []
    customer_ids = set()
    
    for sale in sales:
        receivable = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))
        if receivable < 0:
            receivable = Decimal("0")
        sale_receivables[sale.id] = receivable
        total_receivable += receivable
        
        if sale.customer_id:
            customer_ids.add(sale.customer_id)
    
    # 获取客户名称
    if customer_ids:
        company_result = await db.execute(
            select(Company).where(Company.id.in_(customer_ids))
        )
        companies = company_result.scalars().all()
        customer_names = [c.name for c in companies if c.name]
    
    if total_receivable <= 0:
        raise HTTPException(status_code=400, detail="所选销售单均已收齐，无需收款")
    
    # 4. 确定本次实收金额
    user_amount = Decimal(str(data.amount)) if data.amount is not None else None
    if user_amount is not None:
        if user_amount <= 0:
            raise HTTPException(status_code=400, detail="收款金额必须大于0")
        collect_amount = user_amount
    else:
        collect_amount = total_receivable
    
    # 5. 验证银行账户
    bank_result = await db.execute(select(BankAccount).where(BankAccount.id == data.bank_account_id))
    bank = bank_result.scalar_one_or_none()
    if not bank:
        raise HTTPException(status_code=404, detail="银行账户不存在")
    
    # 6. 按FIFO（销售日期从早到晚）分配收款金额
    sorted_sales = sorted(sales, key=lambda s: (s.sale_date, s.id))
    remaining = collect_amount
    sale_amounts = {}  # 实际分配给每个销售单的金额
    
    for sale in sorted_sales:
        receivable = sale_receivables[sale.id]
        if receivable <= 0:
            sale_amounts[sale.id] = Decimal("0")
            continue
        allocate = min(receivable, remaining)
        sale_amounts[sale.id] = allocate
        remaining -= allocate
        if remaining <= 0:
            break
    
    actual_total = sum(sale_amounts.values())
    
    # 7. 创建交易流水（金额为实际分配总额）
    counterparty_name = ", ".join(customer_names) if customer_names else "多个客户"
    
    transaction = TransactionRecord(
        type="income",
        category="main_business_revenue",
        amount=actual_total,
        to_account_id=data.bank_account_id,
        transaction_date=data.collect_date,
        counterparty_name=counterparty_name[:100],
        description=f"合并收款：{len(sales)} 个销售单",
        reference_no=f"HK{data.collect_date.strftime('%Y%m%d')}",
    )
    db.add(transaction)
    await db.flush()
    
    # 设置关联销售单
    transaction.related_sale_ids = data.sale_ids
    
    # 8. 为每个分配了金额的销售单创建 SalesReceipt
    for sale in sorted_sales:
        allocated = sale_amounts.get(sale.id, Decimal("0"))
        if allocated <= 0:
            continue
        
        receipt = SalesReceipt(
            sale_id=sale.id,
            receipt_date=data.collect_date,
            amount=allocated,
            payment_method="transfer",
            bank_account_id=data.bank_account_id,
            notes="合并收款",
            transaction_id=transaction.id,
        )
        db.add(receipt)
        
        # 更新销售单 paid_amount
        sale.paid_amount = Decimal(str(sale.paid_amount or 0)) + allocated
        
        # 更新付款状态（使用 Enum）
        net = Decimal(str(sale.net_amount or 0))
        paid = Decimal(str(sale.paid_amount or 0))
        if paid >= net:
            sale.status = SalesStatus.FULLY_PAID
        elif paid > 0:
            sale.status = SalesStatus.PARTIAL_PAID
    
    await db.commit()
    
    return {
        "transaction_id": transaction.id,
        "total_amount": float(actual_total),
        "collect_amount": float(collect_amount),
        "sale_count": len(sales),
        "message": "合并收款成功",
    }
