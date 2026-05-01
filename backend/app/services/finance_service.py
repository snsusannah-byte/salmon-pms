from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ExchangeRecord, ImportTax, ClearanceCost,
    TransactionRecord, TransactionType, TransactionCategory,
    ImportInvoice, WholeFishSale, ExchangeStatus, BatchInvoice,
)


class FinanceService:
    """财务管理服务"""

    # ============== 购汇记录 ==============

    @staticmethod
    async def list_exchange_records(
        db: AsyncSession,
        invoice_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ExchangeRecord], int]:
        query = select(ExchangeRecord)
        count_query = select(func.count(ExchangeRecord.id))
        if invoice_id:
            query = query.where(ExchangeRecord.invoice_id == invoice_id)
            count_query = count_query.where(ExchangeRecord.invoice_id == invoice_id)
        query = query.order_by(ExchangeRecord.exchange_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        count_result = await db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar()

    @staticmethod
    async def create_exchange_record(db: AsyncSession, data: dict) -> ExchangeRecord:
        record = ExchangeRecord(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        # 检查发票是否全部购汇完成，如果完成则锁定该发票下所有销售记录
        await FinanceService._check_invoice_exchange_complete(db, data.get("invoice_id"))
        
        return record

    @staticmethod
    async def _check_invoice_exchange_complete(db: AsyncSession, invoice_id: Optional[int]) -> None:
        """检查发票购汇是否完成，如果完成则更新发票状态并锁定销售记录"""
        if not invoice_id:
            return
        
        from app.models import ImportInvoice, WholeFishSale, ExchangeStatus
        
        # 查询发票信息
        result = await db.execute(select(ImportInvoice).where(ImportInvoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            return
        
        # 计算已购汇总额
        exchange_result = await db.execute(
            select(func.sum(ExchangeRecord.amount_usd)).where(ExchangeRecord.invoice_id == invoice_id)
        )
        total_exchanged = exchange_result.scalar() or Decimal("0")
        
        # 如果已购汇 >= 发票金额，标记为已购汇完成
        if total_exchanged >= invoice.total_amount_usd:
            invoice.exchange_status = ExchangeStatus.EXCHANGED
            await db.commit()
            
            # 锁定该发票下所有未锁定的销售记录
            sales_result = await db.execute(
                select(WholeFishSale).where(
                    WholeFishSale.batch_id.in_(
                        select(BatchInvoice.batch_id).where(BatchInvoice.invoice_id == invoice_id)
                    ),
                    WholeFishSale.is_locked == False
                )
            )
            sales = sales_result.scalars().all()
            for sale in sales:
                sale.is_locked = True
            await db.commit()

    @staticmethod
    async def update_exchange_record(db: AsyncSession, record: ExchangeRecord, data: dict) -> ExchangeRecord:
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_exchange_record(db: AsyncSession, record: ExchangeRecord) -> None:
        await db.delete(record)
        await db.commit()

    # ============== 进口税费 ==============

    @staticmethod
    async def list_import_taxes(
        db: AsyncSession,
        invoice_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ImportTax], int]:
        query = select(ImportTax)
        count_query = select(func.count(ImportTax.id))
        if invoice_id:
            query = query.where(ImportTax.invoice_id == invoice_id)
            count_query = count_query.where(ImportTax.invoice_id == invoice_id)
        query = query.order_by(ImportTax.tax_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        count_result = await db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar()

    @staticmethod
    async def create_import_tax(db: AsyncSession, data: dict) -> ImportTax:
        record = ImportTax(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_import_tax(db: AsyncSession, record: ImportTax, data: dict) -> ImportTax:
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_import_tax(db: AsyncSession, record: ImportTax) -> None:
        await db.delete(record)
        await db.commit()

    # ============== 清关运费 ==============

    @staticmethod
    async def list_clearance_costs(
        db: AsyncSession,
        invoice_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ClearanceCost], int]:
        query = select(ClearanceCost)
        count_query = select(func.count(ClearanceCost.id))
        if invoice_id:
            query = query.where(ClearanceCost.invoice_id == invoice_id)
            count_query = count_query.where(ClearanceCost.invoice_id == invoice_id)
        query = query.order_by(ClearanceCost.cost_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        count_result = await db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar()

    @staticmethod
    async def create_clearance_cost(db: AsyncSession, data: dict) -> ClearanceCost:
        record = ClearanceCost(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_clearance_cost(db: AsyncSession, record: ClearanceCost, data: dict) -> ClearanceCost:
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_clearance_cost(db: AsyncSession, record: ClearanceCost) -> None:
        await db.delete(record)
        await db.commit()

    # ============== 交易流水 ==============

    @staticmethod
    async def list_transactions(
        db: AsyncSession,
        type: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[TransactionRecord], int]:
        query = select(TransactionRecord)
        count_query = select(func.count(TransactionRecord.id))
        filters = []
        if type:
            filters.append(TransactionRecord.type == type)
        if category:
            filters.append(TransactionRecord.category == category)
        if start_date:
            filters.append(TransactionRecord.transaction_date >= start_date)
        if end_date:
            filters.append(TransactionRecord.transaction_date <= end_date)
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        query = query.order_by(TransactionRecord.transaction_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        count_result = await db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar()

    @staticmethod
    async def create_transaction(db: AsyncSession, data: dict) -> TransactionRecord:
        record = TransactionRecord(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_transaction(db: AsyncSession, record: TransactionRecord, data: dict) -> TransactionRecord:
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def delete_transaction(db: AsyncSession, record: TransactionRecord) -> None:
        await db.delete(record)
        await db.commit()

    # ============== 汇总 ==============

    @staticmethod
    async def get_summary(db: AsyncSession) -> dict:
        exchange_result = await db.execute(
            select(
                func.sum(ExchangeRecord.amount_usd),
                func.sum(ExchangeRecord.amount_cny),
            )
        )
        total_exchange_usd, total_exchange_cny = exchange_result.one()

        tax_result = await db.execute(select(func.sum(ImportTax.total_tax)))
        total_tax = tax_result.scalar()

        clearance_result = await db.execute(select(func.sum(ClearanceCost.total_cost)))
        total_clearance = clearance_result.scalar()

        income_result = await db.execute(
            select(func.sum(TransactionRecord.amount))
            .where(TransactionRecord.type == TransactionType.INCOME)
        )
        total_income = income_result.scalar()

        expense_result = await db.execute(
            select(func.sum(TransactionRecord.amount))
            .where(TransactionRecord.type == TransactionType.EXPENSE)
        )
        total_expense = expense_result.scalar()

        return {
            "total_exchange_usd": total_exchange_usd or Decimal("0"),
            "total_exchange_cny": total_exchange_cny or Decimal("0"),
            "total_tax": total_tax or Decimal("0"),
            "total_clearance_cost": total_clearance or Decimal("0"),
            "total_income": total_income or Decimal("0"),
            "total_expense": total_expense or Decimal("0"),
            "net_flow": (total_income or Decimal("0")) - (total_expense or Decimal("0")),
        }
