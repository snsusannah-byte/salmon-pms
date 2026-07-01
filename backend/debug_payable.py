#!/usr/bin/env python3
"""调试脚本：测试进口采购应付查询逻辑"""

import asyncio
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

async def debug():
    engine = create_async_engine('postgresql+asyncpg://salmon:001978@localhost:5432/salmon_pms')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # 1. 检查 ICE SEAFOOD AS 的 ID
        from app.models import Company
        result = await db.execute(select(Company.id, Company.name, Company.currency).where(Company.name == 'ICE SEAFOOD AS'))
        supplier = result.first()
        print(f"供应商: {supplier}")
        
        if not supplier:
            print("未找到 ICE SEAFOOD AS")
            return
        
        supplier_id = supplier.id
        
        # 2. 检查该供应商的发票（带 importer_id）
        from app.models import ImportInvoice
        result = await db.execute(
            select(ImportInvoice.id, ImportInvoice.invoice_no, ImportInvoice.importer_id, ImportInvoice.invoice_date, ImportInvoice.total_amount_usd)
            .where(ImportInvoice.supplier_id == supplier_id)
            .where(ImportInvoice.importer_id == 80)
            .order_by(ImportInvoice.invoice_date)
        )
        invoices = result.all()
        print(f"\n发票数量: {len(invoices)}")
        for inv in invoices[:5]:
            print(f"  ID={inv.id}, NO={inv.invoice_no}, importer_id={inv.importer_id}, date={inv.invoice_date}")
        
        # 3. 检查发票的购汇记录
        from app.models.batch import ExchangeRecord
        invoice_ids = [inv.id for inv in invoices]
        print(f"\n发票ID列表: {invoice_ids[:10]}...")
        
        # 检查单张发票购汇
        result = await db.execute(
            select(ExchangeRecord).where(ExchangeRecord.invoice_id.in_(invoice_ids))
        )
        single_ex = list(result.scalars().all())
        print(f"单张发票购汇记录: {len(single_ex)}")
        
        # 检查合并购汇
        result = await db.execute(
            select(ExchangeRecord).where(ExchangeRecord.related_invoice_ids.isnot(None))
        )
        batch_ex = list(result.scalars().all())
        print(f"合并购汇记录总数: {len(batch_ex)}")
        
        # 检查哪些合并购汇关联到这些发票
        matched = 0
        for ex in batch_ex:
            if ex.related_invoice_ids:
                related = ex.related_invoice_ids if isinstance(ex.related_invoice_ids, list) else []
                if any(iid in invoice_ids for iid in related):
                    matched += 1
                    print(f"  匹配: {ex.exchange_no}, related={related}, date={ex.exchange_date}")
        
        print(f"\n匹配到当前供应商的合并购汇: {matched}")
        
        # 4. 检查日期范围
        from datetime import date
        start = date(2025, 1, 1)
        end = date(2026, 6, 30)
        print(f"\n查询日期范围: {start} ~ {end}")
        
        # 检查购汇记录日期
        for ex in batch_ex[:5]:
            in_range = start <= ex.exchange_date <= end
            print(f"  {ex.exchange_no}: date={ex.exchange_date}, in_range={in_range}")

if __name__ == "__main__":
    asyncio.run(debug())
