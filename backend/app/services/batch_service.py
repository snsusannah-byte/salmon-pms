from typing import List, Optional, Tuple
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_, exists
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Batch, BatchInvoice, ImportInvoice, BatchStatus, ExchangeStatus


class BatchService:
    """批次管理服务"""

    @staticmethod
    async def get_by_id(db: AsyncSession, batch_id: int) -> Optional[Batch]:
        result = await db.execute(
            select(Batch)
            .options(selectinload(Batch.batch_invoices))
            .where(Batch.id == batch_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_batches(
        db: AsyncSession,
        status: Optional[BatchStatus] = None,
        search: Optional[str] = None,
        exclude_fully_exchanged: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Batch], int]:
        query = select(Batch)
        count_query = select(func.count(Batch.id))

        filters = []
        if status:
            filters.append(Batch.status == status)
        if search:
            search_pattern = f"%{search}%"
            filters.append(Batch.batch_name.ilike(search_pattern))

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # 排除已全部购汇的批次
        if exclude_fully_exchanged:
            # 获取还有未购汇发票的批次ID
            not_completed_result = await db.execute(
                select(BatchInvoice.batch_id).distinct()
                .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
                .where(ImportInvoice.exchange_status != ExchangeStatus.COMPLETED)
            )
            not_completed_ids = {r[0] for r in not_completed_result.all()}
            
            # 获取没有关联发票的批次ID（也需要显示，因为可能是新批次）
            no_invoice_result = await db.execute(
                select(Batch.id).where(
                    ~exists(
                        select(1).select_from(BatchInvoice).where(BatchInvoice.batch_id == Batch.id)
                    )
                )
            )
            no_invoice_ids = {r[0] for r in no_invoice_result.all()}
            
            include_ids = not_completed_ids | no_invoice_ids
            if include_ids:
                query = query.where(Batch.id.in_(include_ids))
                count_query = count_query.where(Batch.id.in_(include_ids))
            else:
                # 所有批次都已购汇，返回空
                return [], 0

        query = query.order_by(Batch.batch_code.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        return list(items), total

    @staticmethod
    async def generate_batch_name(db: AsyncSession) -> str:
        """自动生成批次名称: B + 年月日 + 序号"""
        from datetime import datetime
        today = datetime.now().strftime("%Y%m%d")
        prefix = f"B{today}"
        
        # 查询今天已有的批次数量
        result = await db.execute(
            select(func.count(Batch.id)).where(Batch.batch_name.like(f"{prefix}%"))
        )
        count = result.scalar() or 0
        
        # 序号从001开始
        sequence = str(count + 1).zfill(3)
        return f"{prefix}{sequence}"

    @staticmethod
    async def generate_batch_code(db: AsyncSession, batch_date: date) -> str:
        """生成批次编号: YYYYMMDD-NNN, 按日期内递增"""
        date_str = batch_date.strftime("%Y%m%d")
        prefix = f"{date_str}-"

        # 查询当天已有的最大序号
        result = await db.execute(
            select(Batch.batch_code)
            .where(Batch.batch_code.like(f"{prefix}%"))
            .order_by(Batch.batch_code.desc())
        )
        codes = result.scalars().all()

        max_num = 0
        for code in codes:
            try:
                num = int(code.split("-")[-1])
                if num > max_num:
                    max_num = num
            except (ValueError, IndexError):
                continue

        new_num = max_num + 1
        return f"{prefix}{new_num:03d}"

    @staticmethod
    async def create(db: AsyncSession, data: dict, invoice_ids: Optional[List[int]] = None) -> Batch:
        # 如果提供了 batch_code，直接使用；否则根据发票日期或当前日期生成
        batch_code = data.get("batch_code")
        batch_date = None
        
        if not batch_code:
            # 没有提供批号，根据关联发票的日期生成
            if invoice_ids:
                from app.models import ImportInvoice
                from sqlalchemy import select
                result = await db.execute(
                    select(ImportInvoice.invoice_date)
                    .where(ImportInvoice.id.in_(invoice_ids))
                    .order_by(ImportInvoice.invoice_date)
                )
                invoice_dates = result.scalars().all()
                if invoice_dates:
                    batch_date = invoice_dates[0]  # 使用最早的发票日期
            
            if not batch_date:
                batch_date = date.today()
            
            batch_code = await BatchService.generate_batch_code(db, batch_date)
        else:
            # 提供了批号，从批号提取日期
            try:
                date_str = batch_code.split("-")[0]
                batch_date = date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:]))
            except (ValueError, IndexError):
                batch_date = date.today()

        # 获取关联的发票号（用于自动生成批次名称）
        invoice_nos = []
        if invoice_ids:
            from app.models import ImportInvoice
            from sqlalchemy import select
            result = await db.execute(
                select(ImportInvoice.invoice_no).where(ImportInvoice.id.in_(invoice_ids)).order_by(ImportInvoice.id)
            )
            invoice_nos = result.scalars().all()

        # 如果没有提供批次名称，自动生成
        batch_name = data.get("batch_name")
        if not batch_name:
            if invoice_nos:
                batch_name = "&".join(invoice_nos)
            else:
                batch_name = f"{batch_code} 批次"

        batch = Batch(
            batch_code=batch_code,
            batch_name=batch_name,
            batch_date=batch_date,
            notes=data.get("notes"),
            status=BatchStatus.OPEN,
        )
        db.add(batch)
        await db.flush()  # 获取 batch.id

        # 关联发票
        if invoice_ids:
            for idx, inv_id in enumerate(invoice_ids):
                bi = BatchInvoice(batch_id=batch.id, invoice_id=inv_id, sort_order=idx)
                db.add(bi)
            
            # 更新关联发票的报关状态为"已结关"
            from app.models import ImportInvoice, InvoiceStatus
            invoice_result = await db.execute(
                select(ImportInvoice).where(ImportInvoice.id.in_(invoice_ids))
            )
            invoices = invoice_result.scalars().all()
            for inv in invoices:
                inv.customs_status = InvoiceStatus.CLEARED

        await db.commit()
        await db.refresh(batch)
        return batch

    @staticmethod
    async def update(db: AsyncSession, batch: Batch, data: dict) -> Batch:
        for field, value in data.items():
            if value is not None:
                setattr(batch, field, value)
        await db.commit()
        await db.refresh(batch)
        return batch

    @staticmethod
    async def delete(db: AsyncSession, batch: Batch) -> None:
        await db.delete(batch)
        await db.commit()

    @staticmethod
    async def add_invoice(db: AsyncSession, batch_id: int, invoice_id: int) -> Optional[BatchInvoice]:
        # 检查发票是否已存在于其他批次
        existing = await db.execute(
            select(BatchInvoice).where(BatchInvoice.invoice_id == invoice_id)
        )
        if existing.scalar_one_or_none():
            return None

        bi = BatchInvoice(batch_id=batch_id, invoice_id=invoice_id)
        db.add(bi)
        
        # 更新发票报关状态为"已结关"
        from app.models import ImportInvoice, InvoiceStatus
        invoice_result = await db.execute(
            select(ImportInvoice).where(ImportInvoice.id == invoice_id)
        )
        invoice = invoice_result.scalar_one_or_none()
        if invoice:
            invoice.customs_status = InvoiceStatus.CLEARED
        
        await db.commit()
        await db.refresh(bi)
        return bi

    @staticmethod
    async def remove_invoice(db: AsyncSession, batch_id: int, invoice_id: int) -> bool:
        result = await db.execute(
            select(BatchInvoice).where(
                BatchInvoice.batch_id == batch_id,
                BatchInvoice.invoice_id == invoice_id,
            )
        )
        bi = result.scalar_one_or_none()
        if not bi:
            return False
        await db.delete(bi)
        await db.commit()
        return True

    @staticmethod
    async def recalculate_totals(db: AsyncSession, batch: Batch) -> None:
        """重新计算批次汇总数据"""
        result = await db.execute(
            select(
                func.sum(ImportInvoice.total_amount_usd),
                func.sum(ImportInvoice.total_boxes),
                func.sum(ImportInvoice.total_weight_kg),
                func.count(ImportInvoice.id),
            )
            .select_from(BatchInvoice)
            .join(ImportInvoice, BatchInvoice.invoice_id == ImportInvoice.id)
            .where(BatchInvoice.batch_id == batch.id)
        )
        totals = result.one()
        batch.total_amount_usd = totals[0] or Decimal("0")
        batch.total_boxes = totals[1] or 0
        batch.total_weight_kg = totals[2] or Decimal("0")
        await db.commit()

    @staticmethod
    async def get_summary(db: AsyncSession) -> dict:
        result = await db.execute(
            select(
                func.count(Batch.id),
                func.sum(func.case((Batch.status == BatchStatus.OPEN, 1), else_=0)),
                func.sum(func.case((Batch.status == BatchStatus.LOCKED, 1), else_=0)),
                func.sum(func.case((Batch.status == BatchStatus.SETTLED, 1), else_=0)),
            )
        )
        total, open_c, locked_c, settled_c = result.one()
        return {
            "total_batches": total or 0,
            "open_count": open_c or 0,
            "locked_count": locked_c or 0,
            "settled_count": settled_c or 0,
        }
