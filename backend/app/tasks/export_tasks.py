"""
数据导出异步任务

CSV/Excel 大数据导出转为 Celery 异步执行
"""
import asyncio
import csv
import io

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2)
def export_sales_to_csv_task(self, start_date: str = None, end_date: str = None, filters: dict = None):
    """异步导出销售数据为 CSV"""
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models import WholeFishSale, Company

        async def _run():
            async with AsyncSessionLocal() as db:
                query = select(WholeFishSale).order_by(WholeFishSale.sale_date.desc())

                # 应用过滤条件
                if start_date:
                    query = query.where(WholeFishSale.sale_date >= start_date)
                if end_date:
                    query = query.where(WholeFishSale.sale_date <= end_date)

                result = await db.execute(query)
                sales = result.scalars().all()

                # 预加载客户名称
                customer_ids = [s.customer_id for s in sales if s.customer_id]
                customers = {}
                if customer_ids:
                    c_result = await db.execute(
                        select(Company.id, Company.name).where(Company.id.in_(customer_ids))
                    )
                    customers = {r[0]: r[1] for r in c_result.all()}

                # 生成 CSV
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    "销售日期", "客户", "规格", "箱数", "重量(kg)",
                    "单价", "金额", "净额", "状态"
                ])

                for sale in sales:
                    writer.writerow([
                        sale.sale_date,
                        customers.get(sale.customer_id, "-"),
                        sale.spec or "-",
                        sale.box_count,
                        sale.weight_kg,
                        sale.unit_price,
                        sale.gross_amount,
                        sale.net_amount,
                        sale.status,
                    ])

                return {
                    "status": "completed",
                    "record_count": len(sales),
                    "csv_content": output.getvalue(),
                    "filename": f"sales_export_{start_date or 'all'}_{end_date or 'all'}.csv",
                }

        return asyncio.run(_run())

    except Exception as exc:
        self.retry(countdown=30, exc=exc)


@celery_app.task(bind=True, max_retries=2)
def export_finance_transactions_task(self, start_date: str = None, end_date: str = None):
    """异步导出交易流水"""
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models import TransactionRecord

        async def _run():
            async with AsyncSessionLocal() as db:
                query = select(TransactionRecord).order_by(TransactionRecord.transaction_date.desc())

                if start_date:
                    query = query.where(TransactionRecord.transaction_date >= start_date)
                if end_date:
                    query = query.where(TransactionRecord.transaction_date <= end_date)

                result = await db.execute(query)
                records = result.scalars().all()

                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow([
                    "日期", "类型", "分类", "金额", "币种",
                    "对方", "备注", "确认状态"
                ])

                for r in records:
                    writer.writerow([
                        r.transaction_date,
                        r.type,
                        r.category,
                        r.amount,
                        r.currency,
                        r.counterparty_name or "-",
                        r.description or "-",
                        "已确认" if r.is_confirmed else "未确认",
                    ])

                return {
                    "status": "completed",
                    "record_count": len(records),
                    "csv_content": output.getvalue(),
                    "filename": f"transactions_{start_date or 'all'}_{end_date or 'all'}.csv",
                }

        return asyncio.run(_run())

    except Exception as exc:
        self.retry(countdown=30, exc=exc)
