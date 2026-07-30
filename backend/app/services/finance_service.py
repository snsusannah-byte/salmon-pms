import json
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, cast, func, or_, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Batch,
    BatchInvoice,
    ClearanceCost,
    ExchangeRecord,
    ImportInvoice,
    ImportTax,
    InvoiceProduct,
    Product,
    SalesStatus,
    StockInbound,
    TransactionCategory,
    TransactionRecord,
    TransactionType,
)


class FinanceService:
    """财务管理服务"""

    # ============== 购汇记录 ==============

    @staticmethod
    async def list_exchange_records(
        db: AsyncSession,
        invoice_id: int | None = None,
        batch_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[ExchangeRecord], int]:
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
    async def _generate_exchange_no(db: AsyncSession, exchange_date: str) -> str:
        """生成购汇单号: GHYYYYMMDD-NNN"""
        from datetime import date
        d = date.fromisoformat(exchange_date)
        prefix = f"GH{d.strftime('%Y%m%d')}"
        
        # 查询当天最大序号
        from sqlalchemy import func
        result = await db.execute(
            select(func.max(ExchangeRecord.exchange_no)).where(ExchangeRecord.exchange_no.like(f"{prefix}-%"))
        )
        max_no = result.scalar() or f"{prefix}-000"
        
        try:
            seq = int(max_no.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
        
        return f"{prefix}-{seq:03d}"

    @staticmethod
    async def create_exchange_record(db: AsyncSession, data: dict) -> ExchangeRecord:
        from datetime import date
        
        # 日期字符串转 date 对象
        if isinstance(data.get("exchange_date"), str):
            data["exchange_date"] = date.fromisoformat(data["exchange_date"])
        
        # 生成购汇单号
        if not data.get("exchange_no") and isinstance(data.get("exchange_date"), (date, str)):
            exchange_date_str = str(data["exchange_date"]) if isinstance(data["exchange_date"], date) else data["exchange_date"]
            data["exchange_no"] = await FinanceService._generate_exchange_no(db, exchange_date_str)
        
        record = ExchangeRecord(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        
        # 更新发票购汇状态（支持单张发票、批次级、或跨批次合并购汇）
        related_invoice_ids = data.get("related_invoice_ids")
        if related_invoice_ids:
            # 合并购汇：按金额比例分摊，更新所有关联发票状态
            await FinanceService._update_multi_invoice_exchange_status(
                db, related_invoice_ids
            )
        else:
            await FinanceService._update_invoice_exchange_status(
                db, 
                invoice_id=data.get("invoice_id"), 
                batch_id=data.get("batch_id")
            )
        
        # 如果指定了扣款银行，自动创建交易流水（购汇金额 + 手续费各一条）
        bank_account_id = data.get("bank_account_id")
        if bank_account_id:
            amount_cny = Decimal(str(data.get("amount_cny", 0)))
            fee_cny = Decimal(str(data.get("fee_cny", 0)))
            exchange_date = data.get("exchange_date")
            exchange_no = data.get("exchange_no") or record.exchange_no
            
            # 解析关联发票：invoice_id -> related_invoice_ids -> batch_id
            invoice_id = data.get("invoice_id")
            related_invoice_ids = data.get("related_invoice_ids")
            batch_id = data.get("batch_id")
            related_invoice_no = None
            
            if not invoice_id and related_invoice_ids:
                # 合并购汇：取第一张用于外键，全部拼接用于展示
                invoice_id = related_invoice_ids[0]
                from app.models import ImportInvoice
                inv_result = await db.execute(
                    select(ImportInvoice).where(ImportInvoice.id.in_(related_invoice_ids))
                )
                invs = list(inv_result.scalars().all())
                related_invoice_no = ", ".join([inv.invoice_no for inv in invs]) if invs else None
            elif not invoice_id and batch_id:
                # 全批次购汇：取批次下第一张发票
                from app.models import BatchInvoice, ImportInvoice
                bi_result = await db.execute(
                    select(BatchInvoice.invoice_id)
                    .where(BatchInvoice.batch_id == batch_id)
                    .order_by(BatchInvoice.id.asc())
                    .limit(1)
                )
                row = bi_result.first()
                if row:
                    invoice_id = row[0]
                    inv_result = await db.execute(
                        select(ImportInvoice.invoice_no).where(ImportInvoice.id == invoice_id)
                    )
                    related_invoice_no = inv_result.scalar()
            
            # 购汇金额支出
            if amount_cny > 0:
                tx_exchange = TransactionRecord(
                    transaction_date=exchange_date,
                    type="expense",
                    category="exchange",
                    amount=amount_cny,
                    currency="CNY",
                    from_account_id=bank_account_id,
                    description="购汇",
                    related_invoice_id=invoice_id,
                    related_invoice_no=related_invoice_no,
                    related_exchange_id=record.id,
                    reference_no=exchange_no,
                    is_confirmed=True,
                )
                db.add(tx_exchange)
            
            # 手续费支出
            if fee_cny > 0:
                tx_fee = TransactionRecord(
                    transaction_date=exchange_date,
                    type="expense",
                    category="exchange_fee",
                    amount=fee_cny,
                    currency="CNY",
                    from_account_id=bank_account_id,
                    description="购汇手续费",
                    related_invoice_id=invoice_id,
                    related_invoice_no=related_invoice_no,
                    related_exchange_id=record.id,
                    reference_no=exchange_no,
                    is_confirmed=True,
                )
                db.add(tx_fee)
            
            await db.commit()
        
        return record

    @staticmethod
    async def _update_multi_invoice_exchange_status(db: AsyncSession, invoice_ids: list) -> None:
        """合并购汇状态更新：按发票金额比例分摊购汇金额，更新所有关联发票状态"""
        from decimal import Decimal

        from sqlalchemy import func

        from app.models import ExchangeStatus, ImportInvoice

        # 查询所有关联发票
        result = await db.execute(
            select(ImportInvoice).where(ImportInvoice.id.in_(invoice_ids))
        )
        invoices = list(result.scalars().all())
        if not invoices:
            return

        # 计算各发票金额及总金额
        total_invoice_amount = sum(Decimal(str(inv.total_amount_usd or 0)) for inv in invoices)
        if total_invoice_amount <= 0:
            return

        # 遍历每张发票，计算其累计购汇金额（直接关联 + 合并购汇分摊）
        for inv in invoices:
            inv_amount = Decimal(str(inv.total_amount_usd or 0))
            inv_id = inv.id

            # 1. 直接关联该发票的购汇金额
            direct_ex = await db.execute(
                select(func.sum(ExchangeRecord.amount_usd))
                .where(ExchangeRecord.invoice_id == inv_id)
            )
            direct_total = direct_ex.scalar() or Decimal("0")

            # 2. 通过合并购汇关联到该发票的金额（按比例分摊）
            batch_share = Decimal("0")
            batch_ex_result = await db.execute(
                select(ExchangeRecord)
                .where(ExchangeRecord.related_invoice_ids.isnot(None))
            )
            batch_records = batch_ex_result.scalars().all()
            for br in batch_records:
                if inv_id in (br.related_invoice_ids or []):
                    # 获取该记录关联的所有发票总金额
                    br_result = await db.execute(
                        select(func.sum(ImportInvoice.total_amount_usd))
                        .where(ImportInvoice.id.in_(br.related_invoice_ids))
                    )
                    br_total = br_result.scalar() or Decimal("0")
                    if br_total > 0:
                        proportion = inv_amount / br_total
                        batch_share += Decimal(str(br.amount_usd or 0)) * proportion

            total_exchanged = direct_total + batch_share

            # 购汇状态二元判断：业务上不存在部分购汇
            # 只要有购汇记录（> 0）就是已购汇，否则未购汇
            if total_exchanged > 0:
                status = ExchangeStatus.COMPLETED
            else:
                status = ExchangeStatus.NOT_EXCHANGED

            inv.exchange_status = status

        await db.commit()

    @staticmethod
    async def _update_invoice_exchange_status(db: AsyncSession, invoice_id: int | None, batch_id: int | None = None) -> None:
        """更新发票购汇状态：按实际购汇金额判断，支持发票级和批次级购汇"""
        from decimal import Decimal

        from sqlalchemy import func

        from app.models import BatchInvoice, ExchangeStatus, ImportInvoice

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

            # 购汇状态二元判断：业务上不存在部分购汇
            # 只要有购汇记录（> 0）就是已购汇，否则未购汇
            if total_exchanged > 0:
                status = ExchangeStatus.COMPLETED
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
        
        # 同步更新关联的交易流水：先删除旧的，再根据当前数据重建
        exchange_id = record.id
        tx_result = await db.execute(
            select(TransactionRecord).where(TransactionRecord.related_exchange_id == exchange_id)
        )
        for tx in tx_result.scalars().all():
            await db.delete(tx)
        
        # 使用更新后的数据重新创建交易流水
        bank_account_id = record.bank_account_id
        if bank_account_id:
            amount_cny = Decimal(str(record.amount_cny or 0))
            fee_cny = Decimal(str(record.fee_cny or 0))
            exchange_date = record.exchange_date
            exchange_no = record.exchange_no
            
            # 解析关联发票：invoice_id -> related_invoice_ids -> batch_id
            invoice_id = record.invoice_id
            related_invoice_ids = record.related_invoice_ids
            batch_id = record.batch_id
            related_invoice_no = None
            
            if not invoice_id and related_invoice_ids:
                # 合并购汇：取第一张用于外键，全部拼接用于展示
                invoice_id = related_invoice_ids[0]
                from app.models import ImportInvoice
                inv_result = await db.execute(
                    select(ImportInvoice).where(ImportInvoice.id.in_(related_invoice_ids))
                )
                invs = list(inv_result.scalars().all())
                related_invoice_no = ", ".join([inv.invoice_no for inv in invs]) if invs else None
            elif not invoice_id and batch_id:
                # 全批次购汇：取批次下第一张发票
                from app.models import BatchInvoice, ImportInvoice
                bi_result = await db.execute(
                    select(BatchInvoice.invoice_id)
                    .where(BatchInvoice.batch_id == batch_id)
                    .order_by(BatchInvoice.id.asc())
                    .limit(1)
                )
                row = bi_result.first()
                if row:
                    invoice_id = row[0]
                    inv_result = await db.execute(
                        select(ImportInvoice.invoice_no).where(ImportInvoice.id == invoice_id)
                    )
                    related_invoice_no = inv_result.scalar()
            
            # 购汇金额支出
            if amount_cny > 0:
                tx_exchange = TransactionRecord(
                    transaction_date=exchange_date,
                    type="expense",
                    category="exchange",
                    amount=amount_cny,
                    currency="CNY",
                    from_account_id=bank_account_id,
                    description="购汇",
                    related_invoice_id=invoice_id,
                    related_invoice_no=related_invoice_no,
                    related_exchange_id=record.id,
                    reference_no=exchange_no,
                    is_confirmed=True,
                )
                db.add(tx_exchange)
            
            # 手续费支出
            if fee_cny > 0:
                tx_fee = TransactionRecord(
                    transaction_date=exchange_date,
                    type="expense",
                    category="exchange_fee",
                    amount=fee_cny,
                    currency="CNY",
                    from_account_id=bank_account_id,
                    description="购汇手续费",
                    related_invoice_id=invoice_id,
                    related_invoice_no=related_invoice_no,
                    related_exchange_id=record.id,
                    reference_no=exchange_no,
                    is_confirmed=True,
                )
                db.add(tx_fee)
            
            await db.commit()
        
        return record

    @staticmethod
    async def delete_exchange_record(db: AsyncSession, record: ExchangeRecord) -> None:
        related_invoice_ids = record.related_invoice_ids
        invoice_id = record.invoice_id
        batch_id = record.batch_id
        exchange_id = record.id
        
        # 先删除关联的交易流水
        tx_result = await db.execute(
            select(TransactionRecord).where(TransactionRecord.related_exchange_id == exchange_id)
        )
        for tx in tx_result.scalars().all():
            await db.delete(tx)
        
        await db.delete(record)
        await db.commit()
        
        # 更新发票购汇状态
        if related_invoice_ids:
            await FinanceService._update_multi_invoice_exchange_status(db, related_invoice_ids)
        else:
            await FinanceService._update_invoice_exchange_status(db, invoice_id=invoice_id, batch_id=batch_id)

    # ============== 进口税费 ==============

    @staticmethod
    async def list_import_taxes(
        db: AsyncSession,
        invoice_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[ImportTax], int]:
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
        invoice_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[ClearanceCost], int]:
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
        invoice_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[dict], int]:
        """合并 import_taxes + clearance_costs 视图"""
        sql = """
        SELECT
            i.id AS invoice_id,
            i.invoice_no,
            i.importer_id,
            c.gross_weight_kg,
            COALESCE(t.tax_date, c.cost_date) AS expense_date,
            c.customs_broker_id,
            co.name AS customs_broker_name,
            COALESCE(t.import_duty, 0) AS import_duty,
            COALESCE(t.import_vat, 0) AS import_vat,
            t.bank_account_id,
            ba.account_name AS bank_account_name,
            COALESCE(t.total_tax, 0) AS tax_total,
            COALESCE(c.clearance_fee, 0) AS clearance_fee,
            COALESCE(c.freight_fee, 0) AS freight_fee,
            COALESCE(c.inspection_fee, 0) AS inspection_fee,
            COALESCE(c.quarantine_fee, 0) AS quarantine_fee,
            COALESCE(c.other_costs, 0) AS other_costs,
            COALESCE(c.total_cost, 0) AS clearance_total,
            COALESCE(c.payment_type, 'monthly') AS payment_type
        FROM import_invoices i
        LEFT JOIN import_taxes t ON t.invoice_id = i.id
        LEFT JOIN clearance_costs c ON c.invoice_id = i.id
        LEFT JOIN companies co ON co.id = c.customs_broker_id
        LEFT JOIN bank_accounts ba ON ba.id = t.bank_account_id
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
                "importer_id": row["importer_id"],
                "gross_weight_kg": row["gross_weight_kg"],
                "expense_date": row["expense_date"],
                "customs_broker_id": row["customs_broker_id"],
                "customs_broker_name": row["customs_broker_name"],
                "import_duty": row["import_duty"],
                "import_vat": row["import_vat"],
                "bank_account_id": row["bank_account_id"],
                "bank_account_name": row["bank_account_name"],
                "tax_total": row["tax_total"],
                "pickup_fee": row["clearance_fee"],  # 映射到前端字段
                "freight": row["freight_fee"],
                "yard_fee": row["inspection_fee"],
                "cold_storage_fee": row["quarantine_fee"],
                "clearance_service_fee": row["other_costs"],
                "payment_type": row["payment_type"],
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
            "bank_account_id": data.get("bank_account_id"),
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
            "payment_type": data.get("payment_type", "monthly"),
        }
        
        # 海关出关毛重（必填，用于计算提货费）
        gross_weight = data.get("gross_weight_kg")
        if gross_weight is None or gross_weight == "":
            raise ValueError("出关毛重不能为空，请先填写出关毛重")
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
        status_changed_invoices = []
        for inv_id in set(invoice_ids_to_update):
            inv_result = await db.execute(select(ImportInvoice).where(ImportInvoice.id == inv_id))
            inv = inv_result.scalar_one_or_none()
            if inv and inv.customs_status == InvoiceStatus.PENDING_CUSTOMS:
                inv.customs_status = InvoiceStatus.CUSTOMS_PROCESSING
                status_changed_invoices.append(inv)
        
        # 4. 为状态变为"已报关"的发票创建入库记录（按产品类型自动选择仓库，绑定批次）
        if status_changed_invoices:
            from app.services.warehouse_v2_service import WarehouseV2Service
            from app.models.batch import BatchInvoice
            
            for inv in status_changed_invoices:
                # 获取发票产品明细
                products_result = await db.execute(
                    select(InvoiceProduct).where(InvoiceProduct.invoice_id == inv.id)
                )
                products = products_result.scalars().all()
                
                # 查找该发票关联的批次
                batch_result = await db.execute(
                    select(BatchInvoice).where(BatchInvoice.invoice_id == inv.id)
                )
                batch_invoice = batch_result.scalar_one_or_none()
                batch_id = batch_invoice.batch_id if batch_invoice else None
                
                # 查询批次号
                batch_no = None
                if batch_id:
                    from app.models.batch import Batch
                    batch_info = await db.execute(select(Batch).where(Batch.id == batch_id))
                    batch = batch_info.scalar_one_or_none()
                    if batch:
                        batch_no = batch.batch_name  # 使用批次名称（如 8863&8862）
                
                for product in products:
                    # 查找对应的产品ID（如果不存在则跳过）
                    product_result = await db.execute(
                        select(Product.id, Product.category, Product.name).where(Product.name == product.product_name).limit(1)
                    )
                    product_row = product_result.one_or_none()
                    
                    if not product_row or product.box_count <= 0:
                        continue
                    
                    product_id = product_row.id
                    
                    # 根据产品类型自动选择仓库
                    warehouse = await WarehouseV2Service.get_default_warehouse_for_product(
                        db, product_id, scope="import"
                    )
                    if not warehouse:
                        # 兜底：如果没有匹配的仓库，跳过
                        continue
                    
                    warehouse_id = warehouse.id
                    
                    await WarehouseV2Service.create_inbound(db, {
                        "source_type": "import_clearance",
                        "source_id": inv.id,
                        "source_no": inv.invoice_no,
                        "warehouse_id": warehouse_id,
                        "product_id": product_id,
                        "batch_id": batch_id,  # 绑定批次
                        "batch_no": batch_no or inv.invoice_no,  # 使用批次名称或发票号
                        "qty": float(product.net_weight_kg),
                        "unit": "kg",
                        "unit_cost": float(inv.unit_price_usd or 0),
                        "original_box_count": product.box_count,
                        "inbound_date": inv.invoice_date,
                        "notes": f"规格：{product.product_spec}",
                    })
                    
                    # 自动确认入库
                    inbound_result = await db.execute(
                        select(StockInbound).where(
                            StockInbound.source_type == "import_clearance",
                            StockInbound.source_id == inv.id
                        ).order_by(StockInbound.id.desc()).limit(1)
                    )
                    latest_inbound = inbound_result.scalar_one_or_none()
                    if latest_inbound:
                        await WarehouseV2Service.confirm_inbound(db, latest_inbound)
        
        # 5. 如果有指定扣款银行，自动创建交易流水（进口关税 + 进口增值税各一条）
        bank_account_id = data.get("bank_account_id")
        if bank_account_id:
            import_duty = Decimal(str(data.get("import_duty", 0)))
            import_vat = Decimal(str(data.get("import_vat", 0)))
            
            # 删除旧的交易流水
            old_tx_result = await db.execute(
                select(TransactionRecord).where(
                    TransactionRecord.related_invoice_id == invoice_id,
                    TransactionRecord.category == "import_tax"
                )
            )
            for tx in old_tx_result.scalars().all():
                await db.delete(tx)
            
            # 进口关税交易流水
            if import_duty > 0:
                tx_duty = TransactionRecord(
                    transaction_date=expense_date,
                    type="expense",
                    category="import_tax",
                    amount=import_duty,
                    currency="CNY",
                    from_account_id=bank_account_id,
                    counterparty_name="上海海关",
                    description="进口关税",
                    related_invoice_id=invoice_id,
                    is_confirmed=True,
                )
                db.add(tx_duty)
            
            # 进口增值税交易流水
            if import_vat > 0:
                tx_vat = TransactionRecord(
                    transaction_date=expense_date,
                    type="expense",
                    category="import_tax",
                    amount=import_vat,
                    currency="CNY",
                    from_account_id=bank_account_id,
                    counterparty_name="上海海关",
                    description="进口增值税",
                    related_invoice_id=invoice_id,
                    is_confirmed=True,
                )
                db.add(tx_vat)
            
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
        
        # 获取每张发票明细及各自购汇情况，同时获取批次进口商（取第一张发票的进口商）
        invoice_result = await db.execute(
            select(ImportInvoice.id, ImportInvoice.invoice_no, ImportInvoice.total_amount_usd, ImportInvoice.importer_id)
            .join(BatchInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
            .where(BatchInvoice.batch_id == batch_id)
        )
        invoices = []
        batch_importer_id = None
        for r in invoice_result.all():
            if batch_importer_id is None:
                batch_importer_id = r.importer_id
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
            "importer_id": batch_importer_id,
            "invoices": invoices,
        }

    # ============== 交易流水 ==============

    @staticmethod
    async def list_transactions(
        db: AsyncSession,
        type: str | None = None,
        category: str | None = None,
        related_sale_id: int | None = None,
        sale_no: str | None = None,
        invoice_no: str | None = None,
        is_locked: bool | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        search: str | None = None,
        bank_account_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[TransactionRecord], int]:
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
        if invoice_no:
            # 模糊匹配关联发票号
            filters.append(TransactionRecord.related_invoice_no.ilike(f"%{invoice_no}%"))
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
            ]
            if amount_filter is not None:
                search_conditions.append(amount_filter)
            
            # 如果搜索关键词像销售单号，也搜索关联销售单
            if search and len(search) >= 4:
                from app.models import WholeFishSale
                sale_conditions = [WholeFishSale.sale_no.ilike(f"%{search}%")]
                if hasattr(WholeFishSale, 'customer_name'):
                    sale_conditions.append(WholeFishSale.customer_name.ilike(f"%{search}%"))
                sale_result = await db.execute(
                    select(WholeFishSale.id, WholeFishSale.sale_no).where(or_(*sale_conditions))
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
    async def _generate_transaction_no(db: AsyncSession, transaction_date: str) -> str:
        """生成交易流水单号: LSYYYYMMDD-NNN"""
        from datetime import date
        d = date.fromisoformat(transaction_date)
        prefix = f"LS{d.strftime('%Y%m%d')}"
        
        result = await db.execute(
            select(func.max(TransactionRecord.reference_no)).where(TransactionRecord.reference_no.like(f"{prefix}-%"))
        )
        max_no = result.scalar() or f"{prefix}-000"
        
        try:
            seq = int(max_no.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
        
        return f"{prefix}-{seq:03d}"

    @staticmethod
    async def create_transaction(db: AsyncSession, data: dict) -> TransactionRecord:
        from datetime import date

        from app.models import WholeFishSale  # 提前导入
        
        # 日期字符串转 date 对象
        if isinstance(data.get("transaction_date"), str):
            data["transaction_date"] = date.fromisoformat(data["transaction_date"])
        
        # 自动生成流水单号
        if not data.get("reference_no") and isinstance(data.get("transaction_date"), (date, str)):
            date_str = str(data["transaction_date"]) if isinstance(data["transaction_date"], date) else data["transaction_date"]
            data["reference_no"] = await FinanceService._generate_transaction_no(db, date_str)
        
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
        
        # 处理关联发票号（related_invoice_no → related_invoice_id + 保留原始字符串）
        related_invoice_no = data.pop("related_invoice_no", None)
        if related_invoice_no:
            from app.models import ImportInvoice
            # 保留原始字符串（支持多个逗号分隔）
            data["related_invoice_no"] = str(related_invoice_no).strip()
            # 尝试解析第一个发票号用于外键关联
            first_no = str(related_invoice_no).split(",")[0].strip()
            if first_no:
                inv_result = await db.execute(
                    select(ImportInvoice).where(ImportInvoice.invoice_no == first_no)
                )
                inv = inv_result.scalar_one_or_none()
                if inv:
                    data["related_invoice_id"] = inv.id
        
        # 如果关联了销售单，检查是否全部已收款（同时检查 WholeFishSale 和 FinishedProductSaleV2）
        if related_sale_ids:
            from app.models.finished_product import FinishedProductSaleV2
            # 查询两种销售单的已收款总额
            wf_result = await db.execute(
                select(WholeFishSale).where(WholeFishSale.id.in_(related_sale_ids))
            )
            wf_sales = wf_result.scalars().all()
            v2_result = await db.execute(
                select(FinishedProductSaleV2).where(FinishedProductSaleV2.id.in_(related_sale_ids))
            )
            v2_sales = v2_result.scalars().all()
            total_remaining = sum(
                max(Decimal("0"), Decimal(str(s.net_amount or 0)) - Decimal(str(s.paid_amount or 0)))
                for s in wf_sales
            )
            total_remaining += sum(
                max(Decimal("0"), Decimal(str(s.net_amount or 0)) - Decimal(str(s.paid_amount or 0)))
                for s in v2_sales
            )
            # 如果所有销售单都已全额收款，才拒绝
            if total_remaining <= 0:
                from fastapi import HTTPException
                sale_nos = [s.sale_no or f"#{s.id}" for s in wf_sales + v2_sales]
                raise HTTPException(
                    status_code=400,
                    detail=f"销售单 {', '.join(sale_nos)} 已全部收款，无需再次录入。"
                )
        
        record = TransactionRecord(**data)
        db.add(record)
        await db.flush()  # 获取 record.id
        
        # 如果关联了销售单且分类不是客户预付款/对冲结算，处理收款记录（FIFO：先填日期久的单）
        if related_sale_ids and data.get("category") not in [TransactionCategory.CUSTOMER_DEPOSIT, TransactionCategory.NETTING_SETTLEMENT]:
            from app.models import SalesReceipt
            from app.models.finished_product import FinishedProductReceipt, FinishedProductSaleV2
            from app.services.sales_service import SalesService
            
            remaining_amount = Decimal(str(data.get("amount", 0)))
            
            # 1. 先处理以销定采 V2 销售单（FinishedProductSaleV2）
            v2_result = await db.execute(
                select(FinishedProductSaleV2)
                .where(FinishedProductSaleV2.id.in_(related_sale_ids))
                .order_by(FinishedProductSaleV2.sale_date.asc(), FinishedProductSaleV2.id.asc())
            )
            v2_sales = v2_result.scalars().all()
            
            for sale in v2_sales:
                if remaining_amount <= 0:
                    break
                
                # 检查是否已为此 transaction + sale 创建过收款记录
                existing_receipt = await db.execute(
                    select(FinishedProductReceipt).where(
                        FinishedProductReceipt.transaction_id == record.id,
                        FinishedProductReceipt.sale_v2_id == sale.id
                    )
                )
                if existing_receipt.scalar_one_or_none():
                    continue  # 已存在，跳过
                
                # 检查该销售单是否有"未关联 transaction"的收款记录
                orphan_result = await db.execute(
                    select(FinishedProductReceipt).where(
                        FinishedProductReceipt.sale_v2_id == sale.id,
                        FinishedProductReceipt.transaction_id.is_(None)
                    )
                )
                orphans = orphan_result.scalars().all()
                
                if orphans:
                    # 把已有的 orphan receipt 关联到当前 transaction
                    for orphan in orphans:
                        orphan.transaction_id = record.id
                    # 更新销售单已付金额
                    receipt_result = await db.execute(
                        select(func.sum(FinishedProductReceipt.amount))
                        .where(FinishedProductReceipt.sale_v2_id == sale.id)
                    )
                    paid = receipt_result.scalar() or Decimal("0")
                    sale.paid_amount = paid
                    net = Decimal(str(sale.net_amount or 0))
                    if paid >= net and net > 0:
                        sale.status = "paid"
                        sale.paid = 1
                    elif paid > 0:
                        sale.status = "partial_paid"
                        sale.paid = 1
                    else:
                        sale.status = "pending"
                        sale.paid = 0
                    # 减少剩余金额
                    orphan_total = sum(Decimal(str(o.amount)) for o in orphans)
                    remaining_amount -= min(orphan_total, remaining_amount)
                else:
                    # 没有 orphan receipt，创建新的
                    sale_remaining = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))
                    if sale_remaining <= 0:
                        continue
                    
                    allocate = min(sale_remaining, remaining_amount)
                    
                    receipt = FinishedProductReceipt(
                        sale_v2_id=sale.id,
                        receipt_date=data.get("transaction_date"),
                        amount=allocate,
                        payable_amount=sale_remaining,  # 记录创建时单据的应付/待付金额
                        payment_method="transfer",
                        bank_account_id=data.get("to_account_id") or data.get("from_account_id"),
                        reference_no=data.get("reference_no"),
                        notes=data.get("notes"),
                        transaction_id=record.id,
                    )
                    db.add(receipt)
                    await db.flush()
                    # 更新销售单已付金额
                    receipt_result = await db.execute(
                        select(func.sum(FinishedProductReceipt.amount))
                        .where(FinishedProductReceipt.sale_v2_id == sale.id)
                    )
                    paid = receipt_result.scalar() or Decimal("0")
                    sale.paid_amount = paid
                    net = Decimal(str(sale.net_amount or 0))
                    if paid >= net and net > 0:
                        sale.status = "paid"
                        sale.paid = 1
                    elif paid > 0:
                        sale.status = "partial_paid"
                        sale.paid = 1
                    else:
                        sale.status = "pending"
                        sale.paid = 0
                    
                    remaining_amount -= allocate
            
            # 2. 再处理进口销售单（WholeFishSale）
            wf_result = await db.execute(
                select(WholeFishSale).where(WholeFishSale.id.in_(related_sale_ids)).order_by(WholeFishSale.sale_date.asc(), WholeFishSale.id.asc())
            )
            wf_sales = wf_result.scalars().all()
            
            for sale in wf_sales:
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
                        payable_amount=sale_remaining,  # 记录创建时单据的应付/待付金额
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
        
        # 客户预付款：更新客户余额，同时冲减关联销售单的应收
        if data.get("category") == TransactionCategory.CUSTOMER_DEPOSIT and data.get("counterparty_id"):
            from app.models import Company
            company_result = await db.execute(
                select(Company).where(Company.id == data["counterparty_id"])
            )
            company = company_result.scalar_one_or_none()
            if company:
                deposit = Decimal(str(data.get("amount", 0)))
                company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) + deposit

            # 同时冲减关联销售单的应收（相当于自动余额抵扣）
            if related_sale_ids:
                await FinanceService._apply_prepayment_to_sales(db, record, related_sale_ids, Decimal(str(data.get("amount", 0))))
        
        # ========== 对冲结算：应收应付互抵（差额模式）==========
        if data.get("category") == TransactionCategory.NETTING_SETTLEMENT:
            from app.models import MaterialPurchaseOrder, SalesReceipt
            from app.models.finished_product import FinishedProductReceipt, FinishedProductSaleV2
            from app.services.sales_service import SalesService

            related_purchase_ids = data.get("related_purchase_ids", [])
            related_purchase_inbound_ids = data.get("related_purchase_inbound_ids", [])
            sale_ids = related_sale_ids or []
            purchase_ids = related_purchase_ids or []
            inbound_ids = related_purchase_inbound_ids or []

            # 差额模式：全额结清采购单和销售单，交易金额 = 差额
            # 1. 全额结清辅料采购单
            if purchase_ids:
                po_result = await db.execute(
                    select(MaterialPurchaseOrder).where(MaterialPurchaseOrder.id.in_(purchase_ids))
                )
                for po in po_result.scalars().all():
                    po.paid_amount = Decimal(str(po.actual_total or 0))
                    po.payment_status = "paid"

            # 2. 全额结清采购入库单
            if inbound_ids:
                from app.models.finance import PurchaseOrderV2
                inbound_result = await db.execute(
                    select(PurchaseOrderV2).where(PurchaseOrderV2.id.in_(inbound_ids))
                )
                for po in inbound_result.scalars().all():
                    net = Decimal(str(po.total_amount or 0)) - Decimal(str(po.after_sales_adjustment or 0))
                    po.paid_amount = net
                    po.payment_status = "paid"

            # 3. 全额结清销售单（创建 netting receipt）
            if sale_ids:
                # V2 销售单
                v2_result = await db.execute(
                    select(FinishedProductSaleV2).where(FinishedProductSaleV2.id.in_(sale_ids))
                    .order_by(FinishedProductSaleV2.sale_date.asc(), FinishedProductSaleV2.id.asc())
                )
                v2_sales = list(v2_result.scalars().all())
                for sale in v2_sales:
                    sale_remaining = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))
                    if sale_remaining <= 0:
                        continue
                    receipt = FinishedProductReceipt(
                        sale_v2_id=sale.id,
                        receipt_date=data.get("transaction_date"),
                        amount=sale_remaining,
                        payable_amount=sale_remaining,  # 对冲结清时应付等于实收
                        payment_method="netting",
                        transaction_id=record.id,
                        notes="对冲结算收款",
                    )
                    db.add(receipt)

                # 进口销售单
                wf_result = await db.execute(
                    select(WholeFishSale).where(WholeFishSale.id.in_(sale_ids))
                    .order_by(WholeFishSale.sale_date.asc(), WholeFishSale.id.asc())
                )
                wf_sales = list(wf_result.scalars().all())
                for sale in wf_sales:
                    sale_remaining = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))
                    if sale_remaining <= 0:
                        continue
                    sr = SalesReceipt(
                        sale_id=sale.id,
                        receipt_date=data.get("transaction_date"),
                        amount=sale_remaining,
                        payable_amount=sale_remaining,  # 对冲结清时应付等于实收
                        payment_method="netting",
                        transaction_id=record.id,
                        notes="对冲结算收款",
                    )
                    db.add(sr)

                await db.flush()

                # 更新 V2 销售单状态
                for sale in v2_sales:
                    receipt_result = await db.execute(
                        select(func.sum(FinishedProductReceipt.amount)).where(FinishedProductReceipt.sale_v2_id == sale.id)
                    )
                    paid = receipt_result.scalar() or Decimal("0")
                    sale.paid_amount = paid
                    net = Decimal(str(sale.net_amount or 0))
                    if paid >= net and net > 0:
                        sale.status = "paid"
                        sale.paid = 1
                    elif paid > 0:
                        sale.status = "partial_paid"
                        sale.paid = 1
                    else:
                        sale.status = "pending"
                        sale.paid = 0

                # 更新进口销售单状态
                for sale in wf_sales:
                    await SalesService._update_paid_amount(db, sale)

        await db.commit()
        await db.refresh(record)
        return record

    @staticmethod
    async def update_transaction(db: AsyncSession, record: TransactionRecord, data: dict) -> TransactionRecord:
        from datetime import date

        # 日期字符串转 date 对象
        if isinstance(data.get("transaction_date"), str):
            data["transaction_date"] = date.fromisoformat(data["transaction_date"])

        related_sale_ids = data.pop("related_sale_ids", None)
        if related_sale_ids is not None:
            record.related_sale_ids = related_sale_ids if related_sale_ids else None
        
        # 处理关联发票号更新
        related_invoice_no = data.pop("related_invoice_no", None)
        if related_invoice_no is not None:
            record.related_invoice_no = str(related_invoice_no).strip() if str(related_invoice_no).strip() else None
            # 尝试解析第一个发票号用于外键关联
            first_no = str(related_invoice_no).split(",")[0].strip()
            if first_no:
                from app.models import ImportInvoice
                inv_result = await db.execute(
                    select(ImportInvoice).where(ImportInvoice.invoice_no == first_no)
                )
                inv = inv_result.scalar_one_or_none()
                record.related_invoice_id = inv.id if inv else None
            else:
                record.related_invoice_id = None
        
        for field, value in data.items():
            if value is not None:
                setattr(record, field, value)
        await db.commit()
        await db.refresh(record)
        
        # 如果交易金额变更，同步更新关联的销售收款并重新计算销售单状态（同时支持 WholeFishSale 和 FinishedProductSaleV2）
        if "amount" in data and record.id:
            from decimal import Decimal

            from app.models import SalesReceipt, WholeFishSale
            from app.models.finished_product import FinishedProductReceipt, FinishedProductSaleV2
            from app.services.sales_service import SalesService
            
            # 1. 更新整鱼销售收款记录
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
            
            # 2. 更新以销定采 V2 收款记录
            v2_result = await db.execute(
                select(FinishedProductReceipt).where(FinishedProductReceipt.transaction_id == record.id)
            )
            v2_receipts = v2_result.scalars().all()
            affected_v2_sale_ids = set()
            
            for receipt in v2_receipts:
                receipt.amount = Decimal(str(data["amount"]))
                affected_v2_sale_ids.add(receipt.sale_v2_id)
            
            if affected_v2_sale_ids:
                await db.flush()
                for sale_id in affected_v2_sale_ids:
                    sale_result = await db.execute(
                        select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id)
                    )
                    sale = sale_result.scalar_one_or_none()
                    if sale:
                        receipt_result = await db.execute(
                            select(func.sum(FinishedProductReceipt.amount))
                            .where(FinishedProductReceipt.sale_v2_id == sale_id)
                        )
                        paid = receipt_result.scalar() or Decimal("0")
                        sale.paid_amount = paid
                        net = Decimal(str(sale.net_amount or 0))
                        if paid >= net and net > 0:
                            sale.status = "paid"
                            sale.paid = 1
                        elif paid > 0:
                            sale.status = "partial_paid"
                            sale.paid = 1
                        else:
                            sale.status = "pending"
                            sale.paid = 0
        
        return record

    @staticmethod
    async def delete_transaction(db: AsyncSession, record: TransactionRecord) -> None:
        # 如果关联了辅料采购付款，同步更新采购单状态
        if record.id and record.reference_no and record.reference_no.startswith("CG"):
            from sqlalchemy import select

            from app.models import MaterialPurchaseOrder
            from app.models.finance import PurchaseOrderV2
            
            # 查找关联的辅料采购单
            po_result = await db.execute(
                select(MaterialPurchaseOrder).where(MaterialPurchaseOrder.order_no == record.reference_no)
            )
            po = po_result.scalar_one_or_none()
            if po:
                # 扣除已付款金额
                amount = Decimal(str(record.amount or 0))
                po.paid_amount = max(Decimal("0"), Decimal(str(po.paid_amount or 0)) - amount)
                
                # 更新付款状态
                if po.paid_amount >= po.actual_total:
                    po.payment_status = "paid"
                elif po.paid_amount > 0:
                    po.payment_status = "partial"
                else:
                    po.payment_status = "unpaid"
            else:
                # 尝试匹配采购入库单
                inbound_result = await db.execute(
                    select(PurchaseOrderV2).where(PurchaseOrderV2.purchase_no == record.reference_no)
                )
                inbound = inbound_result.scalar_one_or_none()
                if inbound:
                    amount = Decimal(str(record.amount or 0))
                    inbound.paid_amount = max(Decimal("0"), Decimal(str(inbound.paid_amount or 0)) - amount)
                    net = Decimal(str(inbound.total_amount or 0)) - Decimal(str(inbound.after_sales_adjustment or 0))
                    if inbound.paid_amount >= net:
                        inbound.payment_status = "paid"
                    elif inbound.paid_amount > 0:
                        inbound.payment_status = "partial"
                    else:
                        inbound.payment_status = "unpaid"

        # 如果关联了整鱼销售收款，同步删除并重新计算销售单状态
        if record.id:
            from sqlalchemy import select

            from app.models import SalesReceipt, WholeFishSale
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
                    # 如果已全额清零，先同步清零因收款产生的抹零，再重新计算净额
                    if Decimal(str(sale.paid_amount or 0)) == 0:
                        sale.rounding_adjustment = Decimal("0")
                    await SalesService._update_paid_amount(db, sale)

        # 如果关联了成品销售/以销定采收款，同步删除并重新计算
        if record.id:
            from sqlalchemy import func

            from app.models.enums import TransactionCategory
            from app.models.finished_product import (
                FinishedProductReceipt,
                FinishedProductSaleV2,
            )

            result = await db.execute(
                select(FinishedProductReceipt).where(FinishedProductReceipt.transaction_id == record.id)
            )
            fp_receipts = result.scalars().all()
            affected_v2_sale_ids = set()
            for receipt in fp_receipts:
                affected_v2_sale_ids.add(receipt.sale_v2_id)
                await db.delete(receipt)
            
            await db.flush()
            
            # 重新计算对应成品销售单的收款状态
            for sale_id in affected_v2_sale_ids:
                if not sale_id:
                    continue
                sale_result = await db.execute(
                    select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id)
                )
                sale = sale_result.scalar_one_or_none()
                if sale:
                    # 重新计算已收金额
                    receipt_result = await db.execute(
                        select(func.sum(FinishedProductReceipt.amount))
                        .where(FinishedProductReceipt.sale_v2_id == sale_id)
                    )
                    paid_amount = receipt_result.scalar() or Decimal("0")
                    sale.paid_amount = paid_amount
                    
                    net_amount = sale.net_amount or Decimal("0")
                    if paid_amount >= net_amount and net_amount > 0:
                        sale.status = "paid"
                        sale.paid = 1
                    elif paid_amount > 0:
                        sale.status = "partial_paid"
                        sale.paid = 1
                    else:
                        sale.status = "pending"
                        sale.paid = 0
                        # 已全额清零，同步清零抹零
                        sale.rounding = Decimal("0")
                        # 抹零清零后重算净金额
                        sale.actual_amount = (sale.total_amount or Decimal("0")) - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - sale.rounding
                        sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0"))
                    await db.flush()

        # 客户预付款删除：恢复客户余额，并删除关联的收款记录
        if record.category == TransactionCategory.CUSTOMER_DEPOSIT and record.counterparty_id:
            from app.models import Company
            # 1. 扣减客户余额
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
            
            # 2. 删除这条预付款创建的收款记录（通过 transaction_id 关联）
            # 2a. 删除以销定采 V2 的收款记录
            from app.models.finished_product import FinishedProductReceipt, FinishedProductSaleV2
            fp_v2_receipt_result = await db.execute(
                select(FinishedProductReceipt).where(FinishedProductReceipt.transaction_id == record.id)
            )
            fp_v2_receipts = fp_v2_receipt_result.scalars().all()
            affected_v2_sale_ids = set()
            for receipt in fp_v2_receipts:
                affected_v2_sale_ids.add(receipt.sale_v2_id)
                await db.delete(receipt)
            
            # 2b. 删除进口销售的收款记录
            wf_receipt_result = await db.execute(
                select(SalesReceipt).where(SalesReceipt.transaction_id == record.id)
            )
            wf_receipts = wf_receipt_result.scalars().all()
            affected_wf_sale_ids = set()
            for receipt in wf_receipts:
                affected_wf_sale_ids.add(receipt.sale_id)
                await db.delete(receipt)
            
            await db.flush()
            
            # 2c. 余额抵扣收款没有关联 transaction_id，但资金来源于客户预付款；
            # 删除预付款时一并回退这些收款，并恢复客户余额。
            if company:
                from app.models import WholeFishSale
                from app.models.finished_product import FinishedProductReceipt, FinishedProductSaleV2
                
                # 以销定采 V2
                fp_balance_receipts_result = await db.execute(
                    select(FinishedProductReceipt)
                    .join(FinishedProductSaleV2, FinishedProductReceipt.sale_v2_id == FinishedProductSaleV2.id)
                    .where(
                        FinishedProductSaleV2.customer == company.name,
                        FinishedProductReceipt.payment_method == "balance",
                        FinishedProductReceipt.transaction_id.is_(None),
                    )
                )
                for receipt in fp_balance_receipts_result.scalars().all():
                    affected_v2_sale_ids.add(receipt.sale_v2_id)
                    company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) + Decimal(str(receipt.amount or 0))
                    await db.delete(receipt)
                
                # 进口销售
                wf_balance_receipts_result = await db.execute(
                    select(SalesReceipt)
                    .join(WholeFishSale, SalesReceipt.sale_id == WholeFishSale.id)
                    .where(
                        WholeFishSale.customer_id == record.counterparty_id,
                        SalesReceipt.payment_method == "balance",
                        SalesReceipt.transaction_id.is_(None),
                    )
                )
                for receipt in wf_balance_receipts_result.scalars().all():
                    affected_wf_sale_ids.add(receipt.sale_id)
                    company.prepaid_balance = Decimal(str(company.prepaid_balance or 0)) + Decimal(str(receipt.amount or 0))
                    await db.delete(receipt)
                
                await db.flush()
            
            # 3. 重新计算受影响销售单的收款状态
            # 3a. 以销定采 V2
            for sale_id in affected_v2_sale_ids:
                if not sale_id:
                    continue
                sale_result = await db.execute(
                    select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id)
                )
                sale = sale_result.scalar_one_or_none()
                if sale:
                    receipt_result = await db.execute(
                        select(func.sum(FinishedProductReceipt.amount)).where(FinishedProductReceipt.sale_v2_id == sale_id)
                    )
                    paid = receipt_result.scalar() or Decimal("0")
                    sale.paid_amount = paid
                    net = Decimal(str(sale.net_amount or 0))
                    if paid >= net and net > 0:
                        sale.status = "paid"
                        sale.paid = 1
                    elif paid > 0:
                        sale.status = "partial_paid"
                        sale.paid = 1
                    else:
                        sale.status = "pending"
                        sale.paid = 0
                        sale.rounding = Decimal("0")
                        sale.actual_amount = (sale.total_amount or Decimal("0")) - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - sale.rounding
                        sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0"))
            
            # 3b. 进口销售
            for sale_id in affected_wf_sale_ids:
                sale_result = await db.execute(
                    select(WholeFishSale).where(WholeFishSale.id == sale_id)
                )
                sale = sale_result.scalar_one_or_none()
                if sale:
                    paid_result = await db.execute(
                        select(func.sum(SalesReceipt.amount)).where(SalesReceipt.sale_id == sale_id)
                    )
                    total_paid = paid_result.scalar() or Decimal("0")
                    sale.paid_amount = total_paid
                    status_net = Decimal(str(sale.net_amount or 0)) + Decimal(str(sale.balance_adjustment or 0))
                    if sale.paid_amount >= status_net and status_net > 0:
                        sale.status = SalesStatus.FULLY_PAID
                    elif sale.paid_amount > 0:
                        sale.status = SalesStatus.PARTIAL_PAID
                    else:
                        sale.status = SalesStatus.PENDING
                        sale.rounding_adjustment = Decimal("0")

        # ========== 对冲结算删除：恢复销售单和采购单状态 ==========
        if record.category == TransactionCategory.NETTING_SETTLEMENT:
            from app.models import MaterialPurchaseOrder
            from app.models.finished_product import FinishedProductReceipt, FinishedProductSaleV2
            from app.services.sales_service import SalesService

            # 1. 删除关联收款记录并恢复销售单
            # 1a. V2 销售单
            fp_v2_receipt_result = await db.execute(
                select(FinishedProductReceipt).where(FinishedProductReceipt.transaction_id == record.id)
            )
            fp_v2_receipts = fp_v2_receipt_result.scalars().all()
            affected_v2_sale_ids = set()
            for receipt in fp_v2_receipts:
                affected_v2_sale_ids.add(receipt.sale_v2_id)
                await db.delete(receipt)
            
            # 1b. 进口销售单
            wf_receipt_result = await db.execute(
                select(SalesReceipt).where(SalesReceipt.transaction_id == record.id)
            )
            wf_receipts = wf_receipt_result.scalars().all()
            affected_wf_sale_ids = set()
            for receipt in wf_receipts:
                affected_wf_sale_ids.add(receipt.sale_id)
                await db.delete(receipt)
            
            await db.flush()
            
            # 2. 恢复销售单状态
            for sale_id in affected_v2_sale_ids:
                if not sale_id:
                    continue
                sale_result = await db.execute(
                    select(FinishedProductSaleV2).where(FinishedProductSaleV2.id == sale_id)
                )
                sale = sale_result.scalar_one_or_none()
                if sale:
                    receipt_result = await db.execute(
                        select(func.sum(FinishedProductReceipt.amount)).where(FinishedProductReceipt.sale_v2_id == sale_id)
                    )
                    paid = receipt_result.scalar() or Decimal("0")
                    sale.paid_amount = paid
                    net = Decimal(str(sale.net_amount or 0))
                    if paid >= net and net > 0:
                        sale.status = "paid"
                        sale.paid = 1
                    elif paid > 0:
                        sale.status = "partial_paid"
                        sale.paid = 1
                    else:
                        sale.status = "pending"
                        sale.paid = 0
                        sale.rounding = Decimal("0")
                        sale.actual_amount = (sale.total_amount or Decimal("0")) - (sale.discount or Decimal("0")) - (sale.scan_fee or Decimal("0")) - sale.rounding
                        sale.net_amount = sale.actual_amount - (sale.after_sales_adjustment or Decimal("0")) - (sale.commission or Decimal("0"))
            
            for sale_id in affected_wf_sale_ids:
                sale_result = await db.execute(
                    select(WholeFishSale).where(WholeFishSale.id == sale_id)
                )
                sale = sale_result.scalar_one_or_none()
                if sale:
                    paid_result = await db.execute(
                        select(func.sum(SalesReceipt.amount)).where(SalesReceipt.sale_id == sale_id)
                    )
                    total_paid = paid_result.scalar() or Decimal("0")
                    sale.paid_amount = total_paid
                    status_net = Decimal(str(sale.net_amount or 0)) + Decimal(str(sale.balance_adjustment or 0))
                    if sale.paid_amount >= status_net and status_net > 0:
                        sale.status = SalesStatus.FULLY_PAID
                    elif sale.paid_amount > 0:
                        sale.status = SalesStatus.PARTIAL_PAID
                    else:
                        sale.status = SalesStatus.PENDING
                        sale.rounding_adjustment = Decimal("0")

            # 3. 恢复采购单已付金额
            if record.related_purchase_ids:
                purchase_ids = record.related_purchase_ids if isinstance(record.related_purchase_ids, list) else json.loads(record.related_purchase_ids)
                txn_amount = Decimal(str(record.amount or 0))
                # 按 FIFO 倒序扣减（和创建时顺序相反）
                po_result = await db.execute(
                    select(MaterialPurchaseOrder).where(MaterialPurchaseOrder.id.in_(purchase_ids))
                    .order_by(MaterialPurchaseOrder.order_date.desc(), MaterialPurchaseOrder.id.desc())
                )
                remaining_deduct = txn_amount
                for po in po_result.scalars().all():
                    if remaining_deduct <= 0:
                        break
                    # 计算该采购单被本次对冲结算贡献了多少已付金额
                    # 简单处理：按剩余金额扣减，直到扣完 txn_amount
                    deduct = min(Decimal(str(po.paid_amount or 0)), remaining_deduct)
                    po.paid_amount = max(Decimal("0"), Decimal(str(po.paid_amount or 0)) - deduct)
                    remaining_deduct -= deduct
                    if po.paid_amount >= po.actual_total:
                        po.payment_status = "paid"
                    elif po.paid_amount > 0:
                        po.payment_status = "partial"
                    else:
                        po.payment_status = "unpaid"
                await db.flush()

            # 4. 恢复采购入库单已付金额
            if record.related_purchase_inbound_ids:
                inbound_ids = record.related_purchase_inbound_ids if isinstance(record.related_purchase_inbound_ids, list) else json.loads(record.related_purchase_inbound_ids)
                txn_amount = Decimal(str(record.amount or 0))
                from app.models.finance import PurchaseOrderV2
                inbound_result = await db.execute(
                    select(PurchaseOrderV2).where(PurchaseOrderV2.id.in_(inbound_ids))
                    .order_by(PurchaseOrderV2.purchase_date.desc(), PurchaseOrderV2.id.desc())
                )
                remaining_deduct = txn_amount
                for po in inbound_result.scalars().all():
                    if remaining_deduct <= 0:
                        break
                    deduct = min(Decimal(str(po.paid_amount or 0)), remaining_deduct)
                    po.paid_amount = max(Decimal("0"), Decimal(str(po.paid_amount or 0)) - deduct)
                    remaining_deduct -= deduct
                    net = Decimal(str(po.total_amount or 0)) - Decimal(str(po.after_sales_adjustment or 0))
                    if po.paid_amount >= net:
                        po.payment_status = "paid"
                    elif po.paid_amount > 0:
                        po.payment_status = "partial"
                    else:
                        po.payment_status = "unpaid"
                await db.flush()

        await db.delete(record)
        await db.commit()

    @staticmethod
    async def delete_transactions_batch(db: AsyncSession, ids: list[int]) -> dict:
        """批量删除交易记录，返回统计信息"""
        from sqlalchemy import select

        from app.models import SalesReceipt, WholeFishSale
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
                # 如果已全额清零，先同步清零因收款产生的抹零，再重新计算净额
                if Decimal(str(sale.paid_amount or 0)) == 0:
                    sale.rounding_adjustment = Decimal("0")
                await SalesService._update_paid_amount(db, sale)

        await db.commit()

        return {"deleted": deleted_count, "not_found": not_found}

    # ============== 预付款冲减销售单 ==============

    @staticmethod
    async def _apply_prepayment_to_sales(db: AsyncSession, record: TransactionRecord, related_sale_ids: list, amount: Decimal) -> None:
        """预付款冲减关联销售单的应收（支持进口销售、以销定采、预包装销售）"""
        from app.models import SalesReceipt, WholeFishSale
        from app.models.finished_product import FinishedProductReceipt, FinishedProductSaleV2
        from app.services.sales_service import SalesService

        remaining = amount

        # 1. 冲减以销定采 V2 销售单
        fp_v2_result = await db.execute(
            select(FinishedProductSaleV2).where(FinishedProductSaleV2.id.in_(related_sale_ids))
        )
        fp_v2_sales = fp_v2_result.scalars().all()
        for sale in sorted(fp_v2_sales, key=lambda s: (s.sale_date, s.id)):
            if remaining <= 0:
                break
            sale_remaining = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))
            if sale_remaining <= 0:
                continue
            allocate = min(sale_remaining, remaining)
            receipt = FinishedProductReceipt(
                sale_v2_id=sale.id,
                receipt_date=record.transaction_date,
                amount=allocate,
                payable_amount=sale_remaining,  # 记录创建时单据的应付/待付金额
                payment_method="balance",  # 预付款抵扣标记为 balance
                transaction_id=record.id,
                notes="客户预付款抵扣",
            )
            db.add(receipt)
            remaining -= allocate

        # 2. 冲减进口销售单
        if remaining > 0:
            wf_result = await db.execute(
                select(WholeFishSale).where(WholeFishSale.id.in_(related_sale_ids)).order_by(WholeFishSale.sale_date.asc(), WholeFishSale.id.asc())
            )
            wf_sales = wf_result.scalars().all()
            for sale in wf_sales:
                if remaining <= 0:
                    break
                sale_remaining = Decimal(str(sale.net_amount or 0)) - Decimal(str(sale.paid_amount or 0))
                if sale_remaining <= 0:
                    continue
                allocate = min(sale_remaining, remaining)
                sr = SalesReceipt(
                    sale_id=sale.id,
                    receipt_date=record.transaction_date,
                    amount=allocate,
                    payable_amount=sale_remaining,  # 记录创建时单据的应付/待付金额
                    payment_method="balance",
                    transaction_id=record.id,
                    notes="客户预付款抵扣",
                )
                db.add(sr)
                remaining -= allocate

        await db.flush()

        # 更新所有受影响的销售单状态
        for sale in fp_v2_sales:
            receipt_result = await db.execute(
                select(func.sum(FinishedProductReceipt.amount)).where(FinishedProductReceipt.sale_v2_id == sale.id)
            )
            paid = receipt_result.scalar() or Decimal("0")
            sale.paid_amount = paid
            net = Decimal(str(sale.net_amount or 0))
            if paid >= net and net > 0:
                sale.status = "paid"
                sale.paid = 1
            elif paid > 0:
                sale.status = "partial_paid"
                sale.paid = 1
            else:
                sale.status = "pending"
                sale.paid = 0

        for sale in wf_sales:
            await SalesService._update_paid_amount(db, sale)

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
