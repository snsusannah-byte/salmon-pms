from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import cast, select, func, and_, text, or_
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ExchangeRecord, ImportTax, ClearanceCost,
    TransactionRecord, TransactionType, TransactionCategory,
    ImportInvoice, BatchInvoice, Batch,
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
        
        # 更新发票购汇状态（支持按发票ID或批次ID）
        await FinanceService._update_invoice_exchange_status(
            db, 
            invoice_id=data.get("invoice_id"), 
            batch_id=data.get("batch_id")
        )
        
        return record

    @staticmethod
    async def _update_invoice_exchange_status(db: AsyncSession, invoice_id: Optional[int], batch_id: Optional[int] = None) -> None:
        """更新发票购汇状态：按实际购汇金额判断，支持发票级和批次级购汇"""
        from app.models import ImportInvoice, ExchangeStatus, BatchInvoice
        from sqlalchemy import func
        from decimal import Decimal

        invoice_ids = []
        if invoice_id:
            invoice_ids.append(invoice_id)
        elif batch_id:
            result = await db.execute(
                select(BatchInvoice.invoice_id).where(BatchInvoice.batch_id == batch_id)
            )
            invoice_ids = [r[0] for r in result.all()]

        if not invoice_ids:
            return

        for inv_id in invoice_ids:
            result = await db.execute(select(ImportInvoice).where(ImportInvoice.id == inv_id))
            inv = result.scalar_one_or_none()
            if not inv:
                continue

            # 1. 直接关联该发票的购汇金额
            direct_ex = await db.execute(
                select(func.sum(ExchangeRecord.amount_usd))
                .where(ExchangeRecord.invoice_id == inv_id)
            )
            direct_total = direct_ex.scalar() or Decimal("0")

            # 2. 批次级购汇（未指定具体发票的）— 仅在批量更新时按金额比例分摊
            batch_share = Decimal("0")
            if not invoice_id and batch_id:
                # 获取该发票在该批次中的金额占比
                batch_purchase_result = await db.execute(
                    select(func.sum(ImportInvoice.total_amount_usd))
                    .join(BatchInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
                    .where(BatchInvoice.batch_id == batch_id)
                )
                batch_purchase_total = batch_purchase_result.scalar() or Decimal("0")

                batch_ex_result = await db.execute(
                    select(func.sum(ExchangeRecord.amount_usd))
                    .where(ExchangeRecord.batch_id == batch_id)
                    .where(ExchangeRecord.invoice_id.is_(None))
                )
                batch_ex_total = batch_ex_result.scalar() or Decimal("0")

                inv_amount = inv.total_amount_usd or Decimal("0")
                if batch_purchase_total > 0 and inv_amount > 0:
                    proportion = inv_amount / batch_purchase_total
                    batch_share = batch_ex_total * proportion

            total_exchanged = direct_total + batch_share
            invoice_total = inv.total_amount_usd or Decimal("0")

            # 判断购汇状态
            if total_exchanged >= invoice_total and invoice_total > 0:
                status = ExchangeStatus.COMPLETED
            elif total_exchanged > 0:
                status = ExchangeStatus.PARTIAL
            else:
                status = ExchangeStatus.NOT_EXCHANGED

            inv.exchange_status = status

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
        invoice_id = record.invoice_id
        batch_id = record.batch_id
        await db.delete(record)
        await db.commit()
        
        # 更新发票购汇状态
        await FinanceService._update_invoice_exchange_status(db, invoice_id=invoice_id, batch_id=batch_id)

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
            c.gross_weight_kg,
            COALESCE(t.tax_date, c.cost_date) AS expense_date,
            c.customs_broker_id,
            co.name AS customs_broker_name,
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
        LEFT JOIN companies co ON co.id = c.customs_broker_id
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
                "gross_weight_kg": row["gross_weight_kg"],
                "expense_date": row["expense_date"],
                "customs_broker_id": row["customs_broker_id"],
                "customs_broker_name": row["customs_broker_name"],
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
            "customs_broker_id": data.get("customs_broker_id") or 15,
            "customs_broker": "威揽",  # 冗余文本，保持兼容
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
        
        # 海关出关毛重（如果传了）
        gross_weight = data.get("gross_weight_kg")
        if gross_weight is not None:
            clearance_data["gross_weight_kg"] = Decimal(str(gross_weight))
        
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
        
        # 3. 更新发票报关状态为"已报关"（主票+所有从票同步更新）
        from app.models import InvoiceStatus
        invoice_result = await db.execute(select(ImportInvoice).where(ImportInvoice.id == invoice_id))
        invoice = invoice_result.scalar_one_or_none()
        
        # 收集需要更新的发票ID列表
        invoice_ids_to_update = [invoice_id]
        
        if invoice:
            if invoice.is_master:
                # 主票：找到所有从票
                sub_result = await db.execute(
                    select(ImportInvoice.id).where(ImportInvoice.parent_invoice_id == invoice_id)
                )
                for row in sub_result.all():
                    invoice_ids_to_update.append(row[0])
            elif invoice.parent_invoice_id:
                # 从票：找到主票和所有其他从票
                invoice_ids_to_update.append(invoice.parent_invoice_id)
                sibling_result = await db.execute(
                    select(ImportInvoice.id).where(
                        ImportInvoice.parent_invoice_id == invoice.parent_invoice_id,
                        ImportInvoice.id != invoice_id
                    )
                )
                for row in sibling_result.all():
                    invoice_ids_to_update.append(row[0])
        
        # 批量更新所有关联发票为"已报关"
        for inv_id in set(invoice_ids_to_update):
            inv_result = await db.execute(select(ImportInvoice).where(ImportInvoice.id == inv_id))
            inv = inv_result.scalar_one_or_none()
            if inv and inv.customs_status == InvoiceStatus.PENDING_CUSTOMS:
                inv.customs_status = InvoiceStatus.CUSTOMS_PROCESSING
        
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
        """获取批次采购总额（汇总该批次下所有发票的 total_amount_usd）及已购汇金额"""
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
                "exchanged_usd": Decimal("0"),
                "remaining_usd": Decimal("0"),
                "invoice_count": 0,
                "invoices": [],
            }
        
        # 获取该批次已购汇金额
        exchange_result = await db.execute(
            select(func.sum(ExchangeRecord.amount_usd))
            .where(ExchangeRecord.batch_id == batch_id)
        )
        exchanged_usd = exchange_result.scalar() or Decimal("0")
        
        total_usd = row["total_usd"] or Decimal("0")
        remaining_usd = total_usd - exchanged_usd
        if remaining_usd < 0:
            remaining_usd = Decimal("0")
        
        # 获取每张发票明细及各自购汇情况
        invoice_result = await db.execute(
            select(ImportInvoice.id, ImportInvoice.invoice_no, ImportInvoice.total_amount_usd)
            .join(BatchInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
            .where(BatchInvoice.batch_id == batch_id)
        )
        invoices = []
        for r in invoice_result.all():
            # 查该发票已购汇金额
            inv_ex_result = await db.execute(
                select(func.sum(ExchangeRecord.amount_usd))
                .where(ExchangeRecord.invoice_id == r.id)
            )
            inv_exchanged = inv_ex_result.scalar() or Decimal("0")
            inv_remaining = r.total_amount_usd - inv_exchanged
            if inv_remaining < 0:
                inv_remaining = Decimal("0")
            invoices.append({
                "id": r.id,
                "invoice_no": r.invoice_no,
                "total_amount_usd": r.total_amount_usd,
                "exchanged_usd": inv_exchanged,
                "remaining_usd": inv_remaining,
            })
        
        return {
            "batch_id": row["id"],
            "batch_code": row["batch_code"],
            "batch_name": row["batch_name"],
            "total_usd": total_usd,
            "exchanged_usd": exchanged_usd,
            "remaining_usd": remaining_usd,
            "invoice_count": row["invoice_count"] or 0,
            "invoices": invoices,
        }

    # ============== 交易流水 ==============

    @staticmethod
    async def list_transactions(
        db: AsyncSession,
        type: Optional[str] = None,
        category: Optional[str] = None,
        related_sale_id: Optional[int] = None,
        sale_no: Optional[str] = None,
        is_locked: Optional[bool] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        search: Optional[str] = None,
        bank_account_id: Optional[int] = None,
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
        if related_sale_id is not None:
            # PostgreSQL JSONB: 使用 @> 操作符检查数组是否包含指定 sale_id
            filters.append(
                TransactionRecord.related_sale_ids.op('@>')(
                    cast(f"[{related_sale_id}]", JSONB)
                )
            )
        if sale_no:
            # 模糊匹配关联销售单号：先查 sale_no 包含关键词的销售单 ID，再筛选 related_sale_ids
            from app.models import WholeFishSale
            sale_result = await db.execute(
                select(WholeFishSale.id).where(WholeFishSale.sale_no.ilike(f"%{sale_no}%"))
            )
            sale_ids = [row[0] for row in sale_result.all()]
            if sale_ids:
                # 使用 JSONB @> 操作符检查数组是否包含任一 sale_id
                json_conditions = [
                    TransactionRecord.related_sale_ids.op('@>')(cast(f"[{sid}]", JSONB))
                    for sid in sale_ids
                ]
                filters.append(or_(*json_conditions))
            else:
                # 没有匹配的销售单，返回空结果
                filters.append(TransactionRecord.id == -1)
        if is_locked is not None:
            filters.append(TransactionRecord.is_locked == is_locked)
        if start_date:
            filters.append(TransactionRecord.transaction_date >= start_date)
        if end_date:
            filters.append(TransactionRecord.transaction_date <= end_date)
        if bank_account_id is not None:
            filters.append(or_(
                TransactionRecord.from_account_id == bank_account_id,
                TransactionRecord.to_account_id == bank_account_id,
            ))
        if search:
            # 支持金额搜索（精确匹配或部分匹配）
            try:
                search_amount = Decimal(str(search))
                amount_filter = TransactionRecord.amount == search_amount
            except Exception:
                amount_filter = None
            
            search_conditions = [
                TransactionRecord.counterparty_name.ilike(f"%{search}%"),
                TransactionRecord.description.ilike(f"%{search}%"),
                TransactionRecord.reference_no.ilike(f"%{search}%"),
                TransactionRecord.transaction_date.cast(str).ilike(f"%{search}%"),
            ]
            if amount_filter is not None:
                search_conditions.append(amount_filter)
            
            # 如果搜索关键词像销售单号，也搜索关联销售单
            if search and len(search) >= 4:
                from app.models import WholeFishSale
                sale_result = await db.execute(
                    select(WholeFishSale.id, WholeFishSale.sale_no).where(
                        or_(
                            WholeFishSale.sale_no.ilike(f"%{search}%"),
                            WholeFishSale.customer_name.ilike(f"%{search}%") if hasattr(WholeFishSale, 'customer_name') else False,
                        )
                    )
                )
                sale_rows = sale_result.all()
                if sale_rows:
                    for row in sale_rows:
                        search_conditions.append(
                            TransactionRecord.related_sale_ids.op('@>')(cast(f"[{row[0]}]", JSONB))
                        )
            
            search_filter = or_(*search_conditions)
            filters.append(search_filter)
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        query = query.order_by(TransactionRecord.transaction_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        count_result = await db.execute(count_query)
        return list(result.scalars().all()), count_result.scalar()

    @staticmethod
    async def create_transaction(db: AsyncSession, data: dict) -> TransactionRecord:
        from app.models import WholeFishSale  # 提前导入
        from datetime import date
        
        # 日期字符串转 date 对象
        if isinstance(data.get("transaction_date"), str):
            data["transaction_date"] = date.fromisoformat(data["transaction_date"])
        
        # 提取关联销售单列表（合并收款或多笔付款支持多选）
        related_sale_ids = data.pop("related_sale_ids", None)
        
        # 去重关联销售单列表
        if related_sale_ids:
            seen = set()
            unique_ids = []
            for sale_id in related_sale_ids:
                if sale_id not in seen:
                    seen.add(sale_id)
                    unique_ids.append(sale_id)
            data["related_sale_ids"] = unique_ids
        
        # 如果关联了销售单，检查是否全部已收款
        if related_sale_ids:
            # 查询这些销售单的已收款总额
            sale_result = await db.execute(
                select(WholeFishSale).where(WholeFishSale.id.in_(related_sale_ids))
            )
            sales = sale_result.scalars().all()
            total_remaining = sum(
                max(Decimal("0"), Decimal(str(s.net_amount or 0)) - Decimal(str(s.paid_amount or 0)))
                for s in sales
            )
            # 如果所有销售单都已全额收款，才拒绝
            if total_remaining <= 0:
                from fastapi import HTTPException
                sale_nos = [s.sale_no or f"#{s.id}" for s in sales]
                raise HTTPException(
                    status_code=400,
                    detail=f"销售单 {', '.join(sale_nos)} 已全部收款，无需再次录入。"
                )
        
        record = TransactionRecord(**data)
        db.add(record)
        await db.flush()  # 获取 record.id
        
        # 如果关联了销售单，处理收款记录（FIFO：先填日期久的单）
        if related_sale_ids:
            from app.models import SalesReceipt
            from app.services.sales_service import SalesService
            
            remaining_amount = Decimal(str(data.get("amount", 0)))
            
            # 查询所有关联销售单，按日期从旧到新排序（FIFO）
            sale_result = await db.execute(
                select(WholeFishSale).where(WholeFishSale.id.in_(related_sale_ids)).order_by(WholeFishSale.sale_date.asc(), WholeFishSale.id.asc())
            )
            sales = sale_result.scalars().all()
            
            for sale in sales:
                if remaining_amount <= 0:
                    break
                
                # 检查是否已为此 transaction + sale 创建过收款记录
                existing_receipt = await db.execute(
                    select(SalesReceipt).where(
                        SalesReceipt.transaction_id == record.id,
                        SalesReceipt.sale_id == sale.id
                    )
                )
                if existing_receipt.scalar_one_or_none():
                    continue  # 已存在，跳过
                
                # 检查该销售单是否有"未关联 transaction"的收款记录（从销售单页面创建的）
                orphan_result = await db.execute(
                    select(SalesReceipt).where(
                        SalesReceipt.sale_id == sale.id,
                        SalesReceipt.transaction_id.is_(None)
                    )
                )
                orphans = orphan_result.scalars().all()
                
                if orphans:
                    # 把已有的 orphan receipt 关联到当前 transaction，不创建新的
                    for orphan in orphans:
                        orphan.transaction_id = record.id
                    # 更新销售单已付金额
                    await SalesService._update_paid_amount(db, sale)
                    # 减少剩余金额（但不能超过交易金额）
                    orphan_total = sum(Decimal(str(o.amount)) for o in orphans)
                    remaining_amount -= min(orphan_total, remaining_amount)
                else:
                    # 没有 orphan receipt，创建新的
                    sale_remaining = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))
                    if sale_remaining <= 0:
                        continue
                    
                    allocate = min(sale_remaining, remaining_amount)
                    
                    receipt = SalesReceipt(
                        sale_id=sale.id,
                        receipt_date=data.get("transaction_date"),
                        amount=allocate,
                        payment_method="transfer",
                        bank_account_id=data.get("to_account_id") or data.get("from_account_id"),
                        reference_no=data.get("reference_no"),
                        notes=data.get("notes"),
                        transaction_id=record.id,
                    )
                    db.add(receipt)
                    await db.flush()
                    await SalesService._update_paid_amount(db, sale)
                    
                    remaining_amount -= allocate
        
        # 客户预付款：更新客户余额
        if data.get("category") == TransactionCategory.CUSTOMER_DEPOSIT and data.get("counterparty_id"):
            from app.models import Company
            company_result = await db.execute(
                select(Company).where(Company.id == data["counterparty_id"])
            )
            company = company_result.scalar_one_or_none()
            if company:
                deposit = Decimal(str(data.get("amount", 0)))
                company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) + deposit
        
        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_transaction(db: AsyncSession, record: TransactionRecord, data: dict) -> TransactionRecord:
        related_sale_ids = data.pop("related_sale_ids", None)
        if related_sale_ids is not None:
            record.related_sale_ids = related_sale_ids if related_sale_ids else None
        
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)
        
        # 如果交易金额变更，同步更新关联的销售收款并重新计算销售单状态
        if "amount" in data and record.id:
            from app.models import SalesReceipt, WholeFishSale
            from sqlalchemy import select
            from app.services.sales_service import SalesService
            from decimal import Decimal
            
            result = await db.execute(
                select(SalesReceipt).where(SalesReceipt.transaction_id == record.id)
            )
            receipts = result.scalars().all()
            affected_sale_ids = set()
            
            for receipt in receipts:
                # 更新收款记录金额
                receipt.amount = Decimal(str(data["amount"]))
                affected_sale_ids.add(receipt.sale_id)
            
            if affected_sale_ids:
                await db.flush()
                # 重新计算对应销售单的收款状态
                for sale_id in affected_sale_ids:
                    sale_result = await db.execute(
                        select(WholeFishSale).where(WholeFishSale.id == sale_id)
                    )
                    sale = sale_result.scalar_one_or_none()
                    if sale:
                        await SalesService._update_paid_amount(db, sale)
        
        return record

    @staticmethod
    async def delete_transaction(db: AsyncSession, record: TransactionRecord) -> None:
        # 如果关联了销售收款，同步删除并重新计算销售单状态
        if record.id:
            from app.models import SalesReceipt, WholeFishSale
            from sqlalchemy import select
            from app.services.sales_service import SalesService

            result = await db.execute(
                select(SalesReceipt).where(SalesReceipt.transaction_id == record.id)
            )
            receipts = result.scalars().all()
            affected_sale_ids = set()
            for receipt in receipts:
                affected_sale_ids.add(receipt.sale_id)
                await db.delete(receipt)
            
            await db.flush()
            
            # 重新计算对应销售单的收款状态
            for sale_id in affected_sale_ids:
                sale_result = await db.execute(
                    select(WholeFishSale).where(WholeFishSale.id == sale_id)
                )
                sale = sale_result.scalar_one_or_none()
                if sale:
                    await SalesService._update_paid_amount(db, sale)
                    # 如果已全额清零，同步清零因收款产生的抹零
                    if Decimal(str(sale.paid_amount or 0)) == 0:
                        sale.rounding_adjustment = Decimal("0")
                        await db.commit()

        # 客户预付款删除：恢复客户余额
        if record.category == TransactionCategory.CUSTOMER_DEPOSIT and record.counterparty_id:
            from app.models import Company
            company_result = await db.execute(
                select(Company).where(Company.id == record.counterparty_id)
            )
            company = company_result.scalar_one_or_none()
            if company:
                deposit = Decimal(str(record.amount or 0))
                company.prepaid_balance = max(
                    Decimal("0"),
                    Decimal(str(company.prepaid_balance or 0)) - deposit
                )

        await db.delete(record)
        await db.commit()

    @staticmethod
    async def delete_transactions_batch(db: AsyncSession, ids: List[int]) -> dict:
        """批量删除交易记录，返回统计信息"""
        from app.models import SalesReceipt, WholeFishSale
        from sqlalchemy import select
        from app.services.sales_service import SalesService

        # 查询所有要删除的记录
        result = await db.execute(
            select(TransactionRecord).where(TransactionRecord.id.in_(ids))
        )
        records = result.scalars().all()

        if not records:
            return {"deleted": 0, "not_found": len(ids)}

        deleted_count = 0
        not_found = len(ids) - len(records)
        affected_sale_ids = set()

        # 收集所有关联的 SalesReceipt
        record_ids = [r.id for r in records]
        receipts_result = await db.execute(
            select(SalesReceipt).where(SalesReceipt.transaction_id.in_(record_ids))
        )
        receipts = receipts_result.scalars().all()

        for receipt in receipts:
            affected_sale_ids.add(receipt.sale_id)
            await db.delete(receipt)

        await db.flush()

        # 删除所有交易记录
        for record in records:
            await db.delete(record)
            deleted_count += 1

        await db.flush()

        # 重新计算受影响销售单的收款状态
        for sale_id in affected_sale_ids:
            sale_result = await db.execute(
                select(WholeFishSale).where(WholeFishSale.id == sale_id)
            )
            sale = sale_result.scalar_one_or_none()
            if sale:
                await SalesService._update_paid_amount(db, sale)
                # 如果已全额清零，同步清零因收款产生的抹零
                if Decimal(str(sale.paid_amount or 0)) == 0:
                    sale.rounding_adjustment = Decimal("0")

        await db.commit()

        return {"deleted": deleted_count, "not_found": not_found}

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
