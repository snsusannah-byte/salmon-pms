#!/usr/bin/env python3
"""
清理亘昌贸易残留的 SalesReceipt 并重新计算收款状态

使用方式:
  cd backend
  source .venv/bin/activate
  python clear_genchang_receipts.py
"""

import asyncio
import sys
from decimal import Decimal
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, '.')

from app.core.database import AsyncSessionLocal
from app.models import WholeFishSale, SalesReceipt, Company, SalesStatus


async def clear_genchang_receipts():
    """清理亘昌贸易的 SalesReceipt 并重新计算状态"""
    async with AsyncSessionLocal() as db:
        # 1. 找到亘昌贸易
        result = await db.execute(
            select(Company).where(Company.name.like("%亘昌%"))
        )
        company = result.scalar_one_or_none()
        
        if not company:
            print("❌ 未找到亘昌贸易公司记录")
            return
        
        print(f"✅ 找到亘昌贸易: ID={company.id}, 名称={company.name}")
        
        # 2. 找到所有销售单
        result = await db.execute(
            select(WholeFishSale).where(WholeFishSale.customer_id == company.id)
        )
        sales = result.scalars().all()
        sale_ids = [s.id for s in sales]
        
        print(f"📋 找到 {len(sales)} 条销售记录")
        
        # 3. 查找并删除关联的 SalesReceipt
        result = await db.execute(
            select(SalesReceipt).where(SalesReceipt.sale_id.in_(sale_ids))
        )
        receipts = result.scalars().all()
        
        if not receipts:
            print("✅ 没有残留的 SalesReceipt，无需清理")
            return
        
        print(f"🗑️  将删除 {len(receipts)} 条 SalesReceipt:")
        for r in receipts:
            print(f"   - ID={r.id}, sale_id={r.sale_id}, amount={r.amount}, transaction_id={r.transaction_id}")
        
        # 确认删除（注释掉下面这行可以跳过确认）
        # confirm = input("\n确认删除以上 SalesReceipt 并重新计算状态? [y/N]: ")
        # if confirm.lower() != 'y':
        #     print("已取消")
        #     return
        print("\n⚡ 自动执行删除...")
        
        # 删除 SalesReceipt
        for r in receipts:
            await db.delete(r)
        
        await db.flush()
        
        # 4. 重新计算所有销售单状态
        updated = 0
        for sale in sales:
            old_status = sale.status
            old_paid = Decimal(str(sale.paid_amount or 0))
            
            # 重新计算（已没有 SalesReceipt，所以 paid_amount = 0）
            sale.paid_amount = Decimal("0")
            sale.net_amount = max(
                Decimal("0"),
                Decimal(str(sale.gross_amount or 0))
                - Decimal(str(sale.scan_fee or 0))
                - Decimal(str(sale.rounding_adjustment or 0))
                - Decimal(str(sale.after_sales_adjustment or 0))
                - Decimal(str(sale.discount or 0))
                - Decimal(str(sale.commission or 0))
            )
            
            # 状态归零
            sale.status = SalesStatus.PENDING
            sale.rounding_adjustment = Decimal("0")  # 清零抹零
            
            if old_status != sale.status or old_paid != sale.paid_amount:
                updated += 1
                print(f"  📝 {sale.sale_no}: 状态 {old_status} → {sale.status}, 已收 ¥{old_paid} → ¥{sale.paid_amount}")
        
        await db.commit()
        print(f"\n✅ 完成: 删除 {len(receipts)} 条收款记录, 更新 {updated} 条销售单状态")


if __name__ == "__main__":
    asyncio.run(clear_genchang_receipts())
