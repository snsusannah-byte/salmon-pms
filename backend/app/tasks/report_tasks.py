"""
报表异步生成任务

耗时操作（大数据量报表）转为 Celery 异步执行
"""
import asyncio
from decimal import Decimal

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def generate_batch_report_task(self, batch_id: int):
    """异步生成批次财报"""
    try:
        # 由于 Celery 是同步的，需要用 asyncio.run 调用异步代码
        # 实际项目中应使用 celery-pool-asyncio 或 asgiref
        from app.core.database import AsyncSessionLocal
        from app.api.v1.endpoints.reports import _calc_batch_financials
        from app.models import Batch, WholeFishSale, ImportInvoice

        async def _run():
            async with AsyncSessionLocal() as db:
                # 查询批次数据
                from sqlalchemy import select
                result = await db.execute(select(Batch).where(Batch.id == batch_id))
                batch = result.scalar_one_or_none()
                if not batch:
                    return {"error": "批次不存在"}

                # 获取批次关联的销售和发票
                sales_result = await db.execute(
                    select(WholeFishSale).where(WholeFishSale.batch_id == batch_id)
                )
                sales_list = sales_result.scalars().all()

                inv_result = await db.execute(
                    select(ImportInvoice).where(ImportInvoice.batch_id == batch_id)
                )
                invoices = inv_result.scalars().all()

                return {
                    "batch_id": batch_id,
                    "batch_name": batch.batch_name,
                    "sales_count": len(sales_list),
                    "invoice_count": len(invoices),
                    "status": "completed",
                }

        return asyncio.run(_run())

    except Exception as exc:
        # 重试逻辑
        self.retry(countdown=60, exc=exc)


@celery_app.task(bind=True, max_retries=2)
def generate_payable_statement_task(self, supplier_id: int, start_date: str = None, end_date: str = None):
    """异步生成应付对账单"""
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models import Company

        async def _run():
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Company).where(Company.id == supplier_id))
                supplier = result.scalar_one_or_none()
                if not supplier:
                    return {"error": "供应商不存在"}

                # 模拟耗时计算...
                import time
                time.sleep(1)  # 实际应用中替换为真实计算

                return {
                    "supplier_id": supplier_id,
                    "supplier_name": supplier.name,
                    "period": f"{start_date} ~ {end_date}",
                    "status": "completed",
                }

        return asyncio.run(_run())

    except Exception as exc:
        self.retry(countdown=30, exc=exc)
