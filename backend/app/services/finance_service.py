from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ExchangeRecord, ImportTax, ClearanceCost,
    TransactionRecord, TransactionType, TransactionCategory,
    ImportInvoice, WholeFishSale, ExchangeStatus, BatchInvoice, Batch,
)


class FinanceService:
    """财务管理服务"""

    # ============== 购汇记录 ==============

    @staticmethod
    async def list_exchange_records(
        db: AsyncSession,
        invoice_id: Optional[int] = None,
        batch_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[ExchangeRecord], int]:
        query = select(ExchangeRecord)
        count_query = select(func.count(ExchangeRecord.id))
        if invoice_id:
            query = query.where(ExchangeRecord.invoice_id == invoice_id)
            count_query = count_query.where(ExchangeRecord.invoice_id == invoice_id)
        if batch_id:
            query = query.where(ExchangeRecord.batch_id == batch_id)
            count_query = count_query.where(ExchangeRecord.batch_id == batch_id)
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
        
        # 检查发票是否全部购汇完成
        await FinanceService._check_invoice_exchange_complete(db, data.get("invoice_id"))
        
        return record

    @staticmethod
    async def _check_invoice_exchange_complete(db: AsyncSession, invoice_id: Optional[int]) -> None:
        """检查发票购汇是否完成"""
        if not invoice_id:
            return
        
        from app.models import ImportInvoice, WholeFishSale, ExchangeStatus
        
        result = await db.execute(select(ImportInvoice).where(ImportInvoice.id == invoice_id))
        invoice = result.scalar_one_or_none()
        if not invoice:
            return
        
        exchange_result = await db.execute(
            select(func.sum(ExchangeRecord.amount_usd)).where(ExchangeRecord.invoice_id == invoice_id)
        )
        total_exchanged = exchange_result.scalar() or Decimal("0")
        
        if total_exchanged >= invoice.total_amount_usd:
            invoice.exchange_status = ExchangeStatus.EXCHANGED
            await db.commit()
            
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

    # ============== 统一进口费用 (税费+清关合并视图) ==============

    @staticmethod
    async def list_import_fees(
        db: AsyncSession,
        invoice_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[dict], int]:
        """合并 import_taxes + clearance_costs 视图"""
        sql = """
        SELECT
            i.id AS invoice_id,
            i.invoice_no,
            COALESCE(t.tax_date, c.cost_date) AS expense_date,
            COALESCE(t.import_duty, 0) AS import_duty,
            COALESCE(t.import_vat, 0) AS import_vat,
            COALESCE(t.total_tax, 0) AS tax_total,
            COALESCE(c.clearance_fee, 0) AS clearance_fee,
            COALESCE(c.freight_fee, 0) AS freight_fee,
            COALESCE(c.inspection_fee, 0) AS inspection_fee,
            COALESCE(c.quarantine_fee, 0) AS quarantine_fee,
            COALESCE(c.other_costs, 0) AS other_costs,
            COALESCE(c.total_cost, 0) AS clearance_total
        FROM import_invoices i
        LEFT JOIN import_taxes t ON t.invoice_id = i.id
        LEFT JOIN clearance_costs c ON c.invoice_id = i.id
        WHERE (t.id IS NOT NULL OR c.id IS NOT NULL)
        """
        count_sql = """
        SELECT COUNT(*) FROM (
            SELECT i.id
            FROM import_invoices i
            LEFT JOIN import_taxes t ON t.invoice_id = i.id
            LEFT JOIN clearance_costs c ON c.invoice_id = i.id
            WHERE (t.id IS NOT NULL OR c.id IS NOT NULL)
        ) sub
        """
        
        params = {}
        if invoice_id:
            sql += " AND i.id = :invoice_id"
            count_sql = count_sql.replace("WHERE (t.id IS NOT NULL OR c.id IS NOT NULL)", 
                "WHERE (t.id IS NOT NULL OR c.id IS NOT NULL) AND i.id = :invoice_id")
            params["invoice_id"] = invoice_id
        
        sql += " ORDER BY COALESCE(t.tax_date, c.cost_date) DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = await db.execute(text(sql), params)
        rows = result.mappings().all()
        
        count_result = await db.execute(text(count_sql), {"invoice_id": invoice_id} if invoice_id else {})
        total = count_result.scalar()
        
        items = []
        for row in rows:
            items.append({
                "invoice_id": row["invoice_id"],
                "invoice_no": row["invoice_no"],
                "expense_date": row["expense_date"],
                "import_duty": row["import_duty"],
                "import_vat": row["import_vat"],
                "tax_total": row["tax_total"],
                "pickup_fee": row["clearance_fee"],  # 映射到前端字段
                "freight": row["freight_fee"],
                "yard_fee": row["inspection_fee"],
                "cold_storage_fee": row["quarantine_fee"],
                "clearance_service_fee": row["other_costs"],
                "clearance_total": row["clearance_total"],
                "grand_total": row["tax_total"] + row["clearance_total"],
            })
        
        return items, total

    @staticmethod
    async def create_import_fee(db: AsyncSession, data: dict) -> dict:
        """创建统一进口费用：同时写入 import_taxes + clearance_costs"""
        invoice_id = data["invoice_id"]
        expense_date = data["expense_date"]
        
        # 1. 写入税费
        tax_data = {
            "invoice_id": invoice_id,
            "tax_date": expense_date,
            "import_duty": Decimal(str(data.get("import_duty", 0))),
            "import_vat": Decimal(str(data.get("import_vat", 0))),
            "total_tax": Decimal(str(data.get("import_duty", 0))) + Decimal(str(data.get("import_vat", 0))),
        }
        
        # 检查是否已存在税费记录
        existing_tax = await db.execute(
            select(ImportTax).where(ImportTax.invoice_id == invoice_id)
        )
        tax_record = existing_tax.scalar_one_or_none()
        if tax_record:
            for k, v in tax_data.items():
                if k != "invoice_id":
                    setattr(tax_record, k, v)
        else:
            tax_record = ImportTax(**tax_data)
            db.add(tax_record)
        
        # 2. 写入清关费用
        clearance_data = {
            "invoice_id": invoice_id,
            "cost_date": expense_date,
            "clearance_fee": Decimal(str(data.get("pickup_fee", 0))),
            "freight_fee": Decimal(str(data.get("freight", 0))),
            "inspection_fee": Decimal(str(data.get("yard_fee", 0))),
            "quarantine_fee": Decimal(str(data.get("cold_storage_fee", 0))),
            "other_costs": Decimal(str(data.get("clearance_service_fee", 0))),
            "total_cost": (
                Decimal(str(data.get("pickup_fee", 0))) +
                Decimal(str(data.get("freight", 0))) +
                Decimal(str(data.get("yard_fee", 0))) +
                Decimal(str(data.get("cold_storage_fee", 0))) +
                Decimal(str(data.get("clearance_service_fee", 0)))
            ),
        }
        
        existing_clearance = await db.execute(
            select(ClearanceCost).where(ClearanceCost.invoice_id == invoice_id)
        )
        clearance_record = existing_clearance.scalar_one_or_none()
        if clearance_record:
            for k, v in clearance_data.items():
                if k != "invoice_id":
                    setattr(clearance_record, k, v)
        else:
            clearance_record = ClearanceCost(**clearance_data)
            db.add(clearance_record)
        
        await db.commit()
        await db.refresh(tax_record)
        await db.refresh(clearance_record)
        
        # 3. 更新发票报关状态为"已报关"
        from app.models import InvoiceStatus
        invoice_result = await db.execute(select(ImportInvoice).where(ImportInvoice.id == invoice_id))
        invoice = invoice_result.scalar_one_or_none()
        if invoice and invoice.customs_status == InvoiceStatus.PENDING_CUSTOMS:
            invoice.customs_status = InvoiceStatus.CUSTOMS_PROCESSING
            await db.commit()
        
        return {
            "invoice_id": invoice_id,
            "tax_record_id": tax_record.id,
            "clearance_record_id": clearance_record.id,
        }

    @staticmethod
    async def delete_import_fee(db: AsyncSession, invoice_id: int) -> None:
        """删除统一进口费用：同时删除税费和清关记录"""
        tax_result = await db.execute(select(ImportTax).where(ImportTax.invoice_id == invoice_id))
        tax = tax_result.scalar_one_or_none()
        if tax:
            await db.delete(tax)
        
        clearance_result = await db.execute(select(ClearanceCost).where(ClearanceCost.invoice_id == invoice_id))
        clearance = clearance_result.scalar_one_or_none()
        if clearance:
            await db.delete(clearance)
        
        await db.commit()

    # ============== 批次采购总额 ==============

    @staticmethod
    async def get_batch_purchase_total(db: AsyncSession, batch_id: int) -> dict:
        """获取批次采购总额（汇总该批次下所有发票的 total_amount_usd）"""
        result = await db.execute(
            select(
                Batch.id,
                Batch.batch_code,
                Batch.batch_name,
                func.sum(ImportInvoice.total_amount_usd).label("total_usd"),
                func.count(ImportInvoice.id).label("invoice_count"),
            )
            .select_from(Batch)
            .join(BatchInvoice, BatchInvoice.batch_id == Batch.id)
            .join(ImportInvoice, ImportInvoice.id == BatchInvoice.invoice_id)
            .where(Batch.id == batch_id)
            .group_by(Batch.id, Batch.batch_code, Batch.batch_name)
        )
        row = result.mappings().one_or_none()
        
        if not row:
            return {
                "batch_id": batch_id,
                "batch_code": None,
                "batch_name": None,
                "total_usd": Decimal("0"),
                "invoice_count": 0,
                "invoices": [],
            }
        
        # 获取每张发票明细
        invoice_result = await db.execute(
            select(ImportInvoice.id, ImportInvoice.invoice_no, ImportInvoice.total_amount_usd)
            .join(BatchInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
            .where(BatchInvoice.batch_id == batch_id)
        )
        invoices = [
            {"id": r.id, "invoice_no": r.invoice_no, "total_amount_usd": r.total_amount_usd}
            for r in invoice_result.all()
        ]
        
        return {
            "batch_id": row["id"],
            "batch_code": row["batch_code"],
            "batch_name": row["batch_name"],
            "total_usd": row["total_usd"] or Decimal("0"),
            "invoice_count": row["invoice_count"] or 0,
            "invoices": invoices,
        }

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
