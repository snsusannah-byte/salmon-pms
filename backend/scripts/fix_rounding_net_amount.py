"""
修复以销定采销售单：rounding 变化后 net_amount 未同步更新的问题

运行方式：
    cd /path/to/backend && python -m scripts.fix_rounding_net_amount

或者直接执行 SQL:
    UPDATE finished_product_sales_v2 SET
        actual_amount = COALESCE(total_amount, 0) - COALESCE(discount, 0) - COALESCE(scan_fee, 0) - COALESCE(rounding, 0),
        net_amount = actual_amount - COALESCE(after_sales_adjustment, 0) - COALESCE(commission, 0)
    WHERE actual_amount != total_amount - discount - scan_fee - rounding
       OR net_amount != actual_amount - after_sales_adjustment - commission;
"""
import asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import async_session_maker
from app.models.finished_product import FinishedProductSaleV2


async def fix_all():
    async with async_session_maker() as db:
        result = await db.execute(
            select(FinishedProductSaleV2).where(
                FinishedProductSaleV2.id.isnot(None)
            )
        )
        sales = result.scalars().all()

        fixed = 0
        for sale in sales:
            total = sale.total_amount or Decimal("0")
            discount = sale.discount or Decimal("0")
            scan_fee = sale.scan_fee or Decimal("0")
            rounding = sale.rounding or Decimal("0")
            after_sales = sale.after_sales_adjustment or Decimal("0")
            commission = sale.commission or Decimal("0")

            expected_actual = total - discount - scan_fee - rounding
            expected_net = expected_actual - after_sales - commission

            if sale.actual_amount != expected_actual or sale.net_amount != expected_net:
                sale.actual_amount = expected_actual
                sale.net_amount = expected_net
                fixed += 1

        await db.commit()
        print(f"Fixed {fixed} sales records")


if __name__ == "__main__":
    asyncio.run(fix_all())
