"""
追溯系统 Service
"""
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Batch,
    Company,
    DailySlaughterRecord,
    FinishedProductSale,
    ImportInvoice,
    MaterialTraceability,
    Product,
    WholeFishSale,
)


class TraceabilityService:
    """原料追溯系统服务"""

    # ==================== 追溯链创建 ====================

    @staticmethod
    async def create_trace_from_invoice(
        db: AsyncSession,
        invoice_id: int,
        product_id: int,
        weight_kg: Decimal,
    ) -> MaterialTraceability:
        """进口发票到货时，创建追溯链起点"""
        trace = MaterialTraceability(
            source_type="import",
            source_invoice_id=invoice_id,
            source_product_id=product_id,
            source_weight_kg=weight_kg,
            trace_status="in_progress",
        )
        db.add(trace)
        await db.commit()
        await db.refresh(trace)
        return trace

    @staticmethod
    async def link_internal_sale(
        db: AsyncSession,
        trace_id: int,
        sale_id: int,
    ) -> MaterialTraceability:
        """内部销售单创建时，关联到追溯链"""
        trace = await db.get(MaterialTraceability, trace_id)
        if not trace:
            raise ValueError("追溯记录不存在")
        
        trace.internal_sale_id = sale_id
        await db.commit()
        await db.refresh(trace)
        return trace

    @staticmethod
    async def link_slaughter(
        db: AsyncSession,
        trace_id: int,
        slaughter_record_id: int,
        finished_weight_kg: Decimal,
    ) -> MaterialTraceability:
        """宰杀记录创建时，关联到追溯链"""
        trace = await db.get(MaterialTraceability, trace_id)
        if not trace:
            raise ValueError("追溯记录不存在")
        
        trace.slaughter_record_id = slaughter_record_id
        trace.finished_weight_kg = finished_weight_kg
        await db.commit()
        await db.refresh(trace)
        return trace

    @staticmethod
    async def link_finished_product_sale(
        db: AsyncSession,
        trace_id: int,
        finished_product_sale_id: int,
        sold_weight_kg: Decimal,
    ) -> MaterialTraceability:
        """成品销售时，关联到追溯链"""
        trace = await db.get(MaterialTraceability, trace_id)
        if not trace:
            raise ValueError("追溯记录不存在")
        
        trace.finished_product_sale_id = finished_product_sale_id
        trace.sold_weight_kg = sold_weight_kg
        
        # 如果成品销售重量 >= 分切产出重量，标记为已完成
        if trace.finished_weight_kg > 0 and trace.sold_weight_kg >= trace.finished_weight_kg:
            trace.trace_status = "completed"
        
        await db.commit()
        await db.refresh(trace)
        return trace

    # ==================== 追溯查询 ====================

    @staticmethod
    async def trace_by_invoice(db: AsyncSession, invoice_id: int) -> List[dict]:
        """按进口发票追溯：这批鱼最终卖给了谁"""
        result = await db.execute(
            select(MaterialTraceability)
            .where(MaterialTraceability.source_invoice_id == invoice_id)
            .order_by(desc(MaterialTraceability.id))
        )
        traces = list(result.scalars().all())
        return [await TraceabilityService._build_trace_detail(db, t) for t in traces]

    @staticmethod
    async def trace_by_batch(db: AsyncSession, batch_id: int) -> List[dict]:
        """按批次追溯"""
        result = await db.execute(
            select(MaterialTraceability)
            .where(MaterialTraceability.source_batch_id == batch_id)
            .order_by(desc(MaterialTraceability.id))
        )
        traces = list(result.scalars().all())
        return [await TraceabilityService._build_trace_detail(db, t) for t in traces]

    @staticmethod
    async def trace_by_finished_sale(db: AsyncSession, sale_id: int) -> Optional[dict]:
        """按成品销售单追溯：这批成品来自哪条进口鱼"""
        result = await db.execute(
            select(MaterialTraceability)
            .where(MaterialTraceability.finished_product_sale_id == sale_id)
        )
        trace = result.scalar_one_or_none()
        if not trace:
            return None
        return await TraceabilityService._build_trace_detail(db, trace)

    @staticmethod
    async def list_traces(
        db: AsyncSession,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[dict], int]:
        query = select(MaterialTraceability)
        if status:
            query = query.where(MaterialTraceability.trace_status == status)
        if source_type:
            query = query.where(MaterialTraceability.source_type == source_type)
        query = query.order_by(desc(MaterialTraceability.id))

        total_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar()

        result = await db.execute(query.offset(skip).limit(limit))
        traces = list(result.scalars().all())
        
        items = []
        for t in traces:
            items.append(await TraceabilityService._build_trace_detail(db, t))
        return items, total

    @staticmethod
    async def _build_trace_detail(db: AsyncSession, trace: MaterialTraceability) -> dict:
        """构建完整的追溯详情"""
        # 原料端
        invoice = None
        batch = None
        source_product = None
        if trace.source_invoice_id:
            invoice = await db.get(ImportInvoice, trace.source_invoice_id)
        if trace.source_batch_id:
            batch = await db.get(Batch, trace.source_batch_id)
        if trace.source_product_id:
            source_product = await db.get(Product, trace.source_product_id)

        # 中间环节
        internal_sale = None
        slaughter = None
        if trace.internal_sale_id:
            internal_sale = await db.get(WholeFishSale, trace.internal_sale_id)
        if trace.slaughter_record_id:
            slaughter = await db.get(DailySlaughterRecord, trace.slaughter_record_id)

        # 成品端
        finished_sale = None
        if trace.finished_product_sale_id:
            finished_sale = await db.get(FinishedProductSale, trace.finished_product_sale_id)

        # 成品客户
        finished_customer = None
        if finished_sale and finished_sale.customer_id:
            result = await db.execute(select(Company.name).where(Company.id == finished_sale.customer_id))
            finished_customer = result.scalar()

        # 加工厂
        processor_name = None
        if internal_sale and internal_sale.customer_id:
            result = await db.execute(select(Company.name).where(Company.id == internal_sale.customer_id))
            processor_name = result.scalar()

        return {
            "id": trace.id,
            "trace_status": trace.trace_status,
            "source_type": trace.source_type,
            # 原料
            "source_invoice_id": trace.source_invoice_id,
            "source_invoice_no": invoice.invoice_no if invoice else None,
            "source_batch_id": trace.source_batch_id,
            "source_batch_no": batch.batch_no if batch else None,
            "source_product_id": trace.source_product_id,
            "source_product_name": source_product.name if source_product else None,
            "source_weight_kg": trace.source_weight_kg,
            # 中间
            "internal_sale_id": trace.internal_sale_id,
            "processor_name": processor_name,
            "slaughter_record_id": trace.slaughter_record_id,
            "slaughter_date": slaughter.slaughter_date if slaughter else None,
            # 成品
            "finished_product_sale_id": trace.finished_product_sale_id,
            "finished_customer_name": finished_customer,
            "finished_weight_kg": trace.finished_weight_kg,
            "sold_weight_kg": trace.sold_weight_kg,
            "created_at": trace.created_at,
            "updated_at": trace.updated_at,
        }

    # ==================== 统计 ====================

    @staticmethod
    async def get_trace_summary(db: AsyncSession) -> dict:
        """追溯统计"""
        total_result = await db.execute(select(func.count()).select_from(MaterialTraceability))
        total = total_result.scalar()

        in_progress_result = await db.execute(
            select(func.count())
            .select_from(MaterialTraceability)
            .where(MaterialTraceability.trace_status == "in_progress")
        )
        in_progress = in_progress_result.scalar()

        completed_result = await db.execute(
            select(func.count())
            .select_from(MaterialTraceability)
            .where(MaterialTraceability.trace_status == "completed")
        )
        completed = completed_result.scalar()

        total_source_weight_result = await db.execute(
            select(func.coalesce(func.sum(MaterialTraceability.source_weight_kg), Decimal("0")))
        )
        total_source_weight = total_source_weight_result.scalar()

        total_sold_weight_result = await db.execute(
            select(func.coalesce(func.sum(MaterialTraceability.sold_weight_kg), Decimal("0")))
        )
        total_sold_weight = total_sold_weight_result.scalar()

        return {
            "total": total,
            "in_progress": in_progress,
            "completed": completed,
            "total_source_weight_kg": total_source_weight,
            "total_sold_weight_kg": total_sold_weight,
        }
